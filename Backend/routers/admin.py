"""Admin utility routes."""

import csv
import io
import zipfile
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session


def _prepare_insert_row_for_new_primary_key(table, current_row: Dict[str, Any], existing_row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if existing_row is None:
        return dict(current_row)

    pk_columns = [column for column in table.columns if column.primary_key]
    if not pk_columns:
        return dict(current_row)

    comparison_row = {
        column.name: current_row.get(column.name)
        for column in table.columns
        if not column.primary_key
    }
    existing_comparison = {
        column.name: existing_row.get(column.name)
        for column in table.columns
        if not column.primary_key
    }

    if comparison_row == existing_comparison:
        return {}

    prepared = dict(current_row)
    for column in pk_columns:
        prepared.pop(column.name, None)
    return prepared

from database import get_db
import models, schemas, auth
from services.nfc_service import genereer_unieke_nfc_uid
from config import Config

router = APIRouter(prefix="/admin", tags=["Admin"])


def check_csv_import_export_enabled():
    """Dependency to check if CSV import/export is enabled."""
    if not Config.CSV_IMPORT_EXPORT_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSV import/export functionality is disabled."
        )
    return True


def _resolve_table(table_name: str):
    if table_name is None or str(table_name).strip() == "":
        raise ValueError("Table name is required.")

    normalized = str(table_name).strip()
    table_map = {table.name.lower(): table for table in models.Base.metadata.tables.values()}
    if normalized.lower() in table_map:
        return table_map[normalized.lower()]

    for table in models.Base.metadata.tables.values():
        if table.name.lower() == normalized.lower():
            return table

    for model_name, model in inspect.getmembers(models, inspect.isclass):
        if model.__module__ != models.__name__:
            continue
        table = getattr(model, "__table__", None)
        if table is None:
            continue
        if model_name.lower() == normalized.lower() or table.name.lower() == normalized.lower():
            return table

    raise ValueError(f"Unknown table '{table_name}'.")


def _coerce_csv_value(column_type, value: Any):
    if value is None:
        return None

    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned == "":
            return None
        value = cleaned

    if column_type is None:
        return value

    python_type = getattr(column_type, "python_type", None)
    if python_type is int and not isinstance(value, int):
        return int(value)
    if python_type is bool:
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}
    if python_type is float:
        return float(value)
    if python_type is datetime:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return value


def parse_csv_rows(table_name: str, csv_text: str) -> List[Dict[str, Any]]:
    table = _resolve_table(table_name)
    text = (csv_text or "").strip()
    if not text:
        return []

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []

    field_lookup = {
        key.strip().lower(): key.strip()
        for key in reader.fieldnames
        if key is not None
    }
    rows: List[Dict[str, Any]] = []

    for raw_row in reader:
        cleaned_row: Dict[str, Any] = {}
        for column in table.columns:
            csv_key = field_lookup.get(column.name.lower())
            if csv_key is None:
                csv_key = next(
                    (actual_key for actual_key in raw_row.keys() if actual_key and actual_key.lower() == column.name.lower()),
                    None,
                )
            if csv_key is None:
                continue
            cleaned_row[column.name] = _coerce_csv_value(column.type, raw_row.get(csv_key))
        rows.append(cleaned_row)

    return rows


def export_table_csv_text(table_name: str, rows: Sequence[Dict[str, Any]]) -> str:
    table = _resolve_table(table_name)
    columns = [column.name for column in table.columns]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()

    for row in rows:
        normalized = {}
        for key in columns:
            if key in row:
                normalized[key] = row.get(key)
        writer.writerow(normalized)

    return output.getvalue()


def get_available_tables() -> List[str]:
    return [table.name for table in models.Base.metadata.tables.values()]


def _build_dependency_graph() -> Dict[str, Set[str]]:
    """Build a directed graph of table dependencies from FK relationships.
    Returns: {table_name: set_of_dependent_table_names} (edges: parent -> child)
    """
    graph: Dict[str, Set[str]] = {table.name: set() for table in models.Base.metadata.tables.values()}
    
    for table in models.Base.metadata.tables.values():
        for fk in table.foreign_keys:
            parent_table = fk.column.table.name
            child_table = table.name
            if parent_table != child_table:
                graph[parent_table].add(child_table)
    
    return graph


def _topological_sort(graph: Dict[str, Set[str]]) -> List[str]:
    """Kahn's algorithm for topological sorting.
    Returns tables in dependency order (parents before children).
    """
    # Calculate in-degrees
    in_degree: Dict[str, int] = {node: 0 for node in graph}
    for node, deps in graph.items():
        for dep in deps:
            in_degree[dep] = in_degree.get(dep, 0) + 1
    
    # Queue nodes with no dependencies
    queue = [node for node, deg in in_degree.items() if deg == 0]
    result = []
    
    while queue:
        node = queue.pop(0)
        result.append(node)
        for dep in graph.get(node, set()):
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                queue.append(dep)
    
    # If there are cycles, append remaining nodes (shouldn't happen with FKs)
    if len(result) < len(graph):
        remaining = [n for n in graph if n not in result]
        result.extend(remaining)
    
    return result


def _get_import_order() -> List[str]:
    """Get tables sorted by FK dependency order for import."""
    graph = _build_dependency_graph()
    return _topological_sort(graph)


def _create_export_zip(db: Session) -> io.BytesIO:
    """Create a ZIP file containing CSV exports of all tables."""
    zip_buffer = io.BytesIO()
    table_order = _get_import_order()  # Same order for consistency
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for table_name in table_order:
            try:
                rows = _table_rows_for_export(db, table_name)
                csv_text = export_table_csv_text(table_name, rows)
                zip_file.writestr(f"{table_name}.csv", csv_text)
            except Exception as e:
                # Include error info in a separate file
                zip_file.writestr(f"{table_name}.error.txt", f"Export failed: {str(e)}")
    
    zip_buffer.seek(0)
    return zip_buffer


def _import_from_zip(db: Session, zip_file: UploadFile, mode: str = 'merge') -> Dict[str, Any]:
    """Import all tables from a ZIP file containing CSVs."""
    import_mode = _normalize_import_mode(mode)
    results = {"imported": {}, "errors": {}, "skipped": []}
    
    # Read ZIP into memory
    zip_content = zip_file.file.read()
    zip_buffer = io.BytesIO(zip_content)
    
    with zipfile.ZipFile(zip_buffer, 'r') as zf:
        # Get list of CSV files in ZIP
        csv_files = [name for name in zf.namelist() if name.endswith('.csv')]
        
        # Map filename to table name
        table_files = {}
        for csv_name in csv_files:
            table_name = csv_name[:-4]  # Remove .csv
            try:
                _resolve_table(table_name)  # Validate table exists
                table_files[table_name] = csv_name
            except ValueError:
                results["skipped"].append(f"{csv_name}: unknown table")
        
        # Import in dependency order
        import_order = _get_import_order()
        for table_name in import_order:
            if table_name not in table_files:
                continue
            
            csv_name = table_files[table_name]
            try:
                with zf.open(csv_name) as csv_file:
                    csv_text = csv_file.read().decode('utf-8-sig')
                
                rows = parse_csv_rows(table_name, csv_text)
                if not rows:
                    results["skipped"].append(f"{table_name}: no rows")
                    continue
                
                inserted = _insert_csv_rows(db, table_name, rows, mode=import_mode)
                results["imported"][table_name] = inserted
                
            except Exception as e:
                results["errors"][table_name] = str(e)
                # Continue with other tables
    
    return results


def _table_rows_for_export(db: Session, table_name: str) -> List[Dict[str, Any]]:
    table = _resolve_table(table_name)
    result = db.execute(select(*table.columns)).fetchall()
    return [dict(zip(table.columns.keys(), row)) for row in result]


def _normalize_insert_row(table, row: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}

    for column in table.columns:
        if column.name not in row:
            if column.nullable:
                normalized[column.name] = None
            continue

        if row.get(column.name) is not None:
            normalized[column.name] = row[column.name]
            continue

        if column.nullable:
            normalized[column.name] = None

    return normalized


def _normalize_import_mode(mode: Optional[str]) -> str:
    value = (mode or 'merge').strip().lower()
    if value not in {'merge', 'replace'}:
        raise ValueError("Import mode must be either 'merge' or 'replace'.")
    return value


def _insert_csv_rows(db: Session, table_name: str, rows: Iterable[Dict[str, Any]], mode: str = 'merge') -> int:
    table = _resolve_table(table_name)
    mode_name = _normalize_import_mode(mode)
    pk_columns = [column for column in table.columns if column.primary_key]
    conflict_columns = {column.name for column in pk_columns}
    insert_rows = []
    update_rows = []

    for row in rows:
        sanitized = _normalize_insert_row(table, row)

        if conflict_columns:
            matched_values = []
            for column_name in sorted(conflict_columns):
                if column_name in sanitized:
                    matched_values.append((column_name, sanitized[column_name]))
            if matched_values:
                conditions = []
                for column_name, value in matched_values:
                    conditions.append(getattr(table.c, column_name) == value)
                existing_row = db.execute(table.select().where(*conditions)).first()
                if existing_row is not None:
                    existing_data = dict(existing_row._mapping)
                    if mode_name == 'replace':
                        update_values = {
                            column.name: sanitized[column.name]
                            for column in table.columns
                            if column.name in sanitized
                        }
                        update_rows.append((conditions, update_values))
                        continue

                    comparison_row = {
                        column.name: sanitized.get(column.name)
                        for column in table.columns
                        if column.name not in conflict_columns
                    }
                    existing_comparison = {
                        column.name: existing_data.get(column.name)
                        for column in table.columns
                        if column.name not in conflict_columns
                    }
                    if comparison_row == existing_comparison:
                        continue

                    prepared_row = _prepare_insert_row_for_new_primary_key(table, sanitized, existing_data)
                    if not prepared_row:
                        continue
                    sanitized = prepared_row

        insertable = {
            column.name: sanitized[column.name]
            for column in table.columns
            if column.name in sanitized
        }

        missing_required = [
            column.name
            for column in table.columns
            if not column.primary_key
            and column.name not in insertable
            and not column.nullable
            and column.default is None
            and column.server_default is None
        ]

        if missing_required:
            continue

        if insertable:
            insert_rows.append(insertable)

    for conditions, values in update_rows:
        db.execute(table.update().where(*conditions).values(**values))

    if not insert_rows and not update_rows:
        return 0

    if insert_rows:
        db.execute(table.insert(), insert_rows)
    db.commit()
    return len(insert_rows) + len(update_rows)


@router.get("/csv/tables")
def list_csv_tables(
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
    _csv_enabled: bool = Depends(check_csv_import_export_enabled),
):
    return schemas.APIResponse(sukses=True, data={"tables": get_available_tables()})


@router.get("/csv/export")
def export_table_csv(
    table: str = Query(..., description="Table name or model name to export"),
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
    _csv_enabled: bool = Depends(check_csv_import_export_enabled),
):
    try:
        actual_table = _resolve_table(table)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    rows = _table_rows_for_export(db, actual_table.name)
    filename = f"{actual_table.name}.csv"
    csv_payload = export_table_csv_text(actual_table.name, rows)

    return PlainTextResponse(
        csv_payload,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/csv/import")
async def import_table_csv(
    table: str = Form(..., description="Table name or model name to import into"),
    file: Optional[UploadFile] = File(default=None),
    text: Optional[str] = Form(default=None),
    mode: str = Form(default="merge", description="Import strategy: merge or replace"),
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
    _csv_enabled: bool = Depends(check_csv_import_export_enabled),
):
    try:
        _resolve_table(table)
        import_mode = _normalize_import_mode(mode)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    csv_payload = text
    if file is not None:
        raw = await file.read()
        if raw:
            csv_payload = raw.decode("utf-8-sig")

    if not csv_payload or not csv_payload.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide CSV content as text or upload a CSV file.",
        )

    rows = parse_csv_rows(table, csv_payload)
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No CSV rows were found to import.",
        )

    inserted = _insert_csv_rows(db, table, rows, mode=import_mode)
    return schemas.APIResponse(
        sukses=True,
        data={"table": _resolve_table(table).name, "imported_rows": inserted, "mode": import_mode},
    )


@router.get("/csv/export-all")
def export_all_tables_csv(
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
    _csv_enabled: bool = Depends(check_csv_import_export_enabled),
):
    """Export all tables as a ZIP file containing one CSV per table."""
    try:
        zip_buffer = _create_export_zip(db)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"moon_export_{timestamp}.zip"
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(exc)}",
        ) from exc


@router.post("/csv/import-all")
async def import_all_tables_csv(
    file: UploadFile = File(..., description="ZIP file containing CSV files named after tables"),
    mode: str = Form(default="merge", description="Import strategy: merge or replace"),
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
    _csv_enabled: bool = Depends(check_csv_import_export_enabled),
):
    """Import all tables from a ZIP file containing CSVs.
    
    The ZIP should contain CSV files named after tables (e.g., 'kampus.csv', 'gebruikers.csv').
    Tables are imported in dependency order (parents before children) to respect FK constraints.
    """
    if not file.filename or not file.filename.endswith('.zip'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a ZIP file containing CSV files.",
        )
    
    try:
        results = _import_from_zip(db, file, mode)
        return schemas.APIResponse(sukses=True, data=results)
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ZIP file.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(exc)}",
        ) from exc


@router.post("/lokasies/genereer-missing-uids")
def genereer_missing_lokasie_uids(
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    lokasies = db.query(models.Lokasie).all()
    geskep = []

    for l in lokasies:
        bestaande_tag = db.query(models.NFC_Tags).filter(
            models.NFC_Tags.Lokasie_ID == l.Lokasie_ID,
            models.NFC_Tags.NFC_Is_Aktief == True
        ).first()

        if bestaande_tag:
            continue

        uid = genereer_unieke_nfc_uid(db)

        nuwe_tag = models.NFC_Tags(
            NFC_UID=uid,
            Lokasie_ID=l.Lokasie_ID,
            Gebruiker_ID=None,
            NFC_Tipe="Lokasie",
            NFC_Is_Aktief=True
        )

        db.add(nuwe_tag)

        geskep.append({
            "Lokasie_ID": l.Lokasie_ID,
            "LOK_Naam": l.LOK_Naam,
            "NFC_UID": uid
        })

    db.commit()

    return schemas.APIResponse(
        sukses=True,
        data={"geskep_count": len(geskep), "geskep": geskep}
    )

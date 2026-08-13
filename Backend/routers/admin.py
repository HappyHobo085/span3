"""Admin utility routes."""

import csv
import io
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import PlainTextResponse
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

router = APIRouter(prefix="/admin", tags=["Admin"])


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
    valid_rows = []
    pk_columns = [column for column in table.columns if column.primary_key]

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

<<<<<<< HEAD
=======
    for conditions, values in update_rows:
        db.execute(table.update().where(*conditions).values(**values))

>>>>>>> f173f36 (Add CSV import mode selection and handling for merge/replace strategies)
    if not valid_rows:
        return 0

    db.execute(table.insert(), valid_rows)
    db.commit()
    return len(valid_rows)


@router.get("/csv/tables")
def list_csv_tables(
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    return schemas.APIResponse(sukses=True, data={"tables": get_available_tables()})


@router.get("/csv/export")
def export_table_csv(
    table: str = Query(..., description="Table name or model name to export"),
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
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

    inserted = _insert_csv_rows(db, table, rows)
    return schemas.APIResponse(
        sukses=True,
        data={"table": _resolve_table(table).name, "imported_rows": inserted, "mode": import_mode},
    )


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

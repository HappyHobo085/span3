"""Kampus (Campus) CRUD + status routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from database import get_db
import models, schemas, auth
from services.status_service import haal_laatste_logs_per_gebruiker

router = APIRouter(prefix="/kampusse", tags=["Kampus"])


@router.get("", response_model=schemas.APIResponse[List[schemas.Kampus]])
def lees_kampusse(db: Session = Depends(get_db)):
    kampusse = db.query(models.Kampus).all()
    return schemas.APIResponse(sukses=True, data=kampusse)


@router.post("", response_model=schemas.APIResponse[schemas.Kampus], status_code=status.HTTP_201_CREATED)
def skep_kampus(
    kampus_in: schemas.KampusCreate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    naam = kampus_in.KAM_Naam.strip()
    if not naam:
        raise HTTPException(status_code=400, detail="Kampusnaam is verpligtend")

    bestaande = db.query(models.Kampus).filter(
        func.lower(models.Kampus.KAM_Naam) == naam.lower()
    ).first()
    if bestaande:
        raise HTTPException(status_code=400, detail="Kampusnaam reeds in gebruik")

    kampus = models.Kampus(KAM_Naam=naam, KAM_Adres=kampus_in.KAM_Adres)
    db.add(kampus)
    db.commit()
    db.refresh(kampus)

    hek = models.Lokasie(
        LOK_Naam=f"{kampus.KAM_Naam}-Hek",
        LOK_Tipe="Kampus",
        Kampus_ID=kampus.Kampus_ID,
    )
    db.add(hek)
    db.commit()

    return schemas.APIResponse(sukses=True, data=kampus)


@router.put("/{kampus_id}", response_model=schemas.APIResponse[schemas.Kampus])
def opdateer_kampus(
    kampus_id: int,
    kampus_in: schemas.KampusUpdate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    kampus = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == kampus_id).first()
    if not kampus:
        raise HTTPException(status_code=404, detail="Kampus nie gevind nie")

    update_data = kampus_in.dict(exclude_unset=True)
    if "KAM_Naam" in update_data:
        naam = update_data["KAM_Naam"].strip()
        if not naam:
            raise HTTPException(status_code=400, detail="Kampusnaam is verpligtend")
        bestaande = db.query(models.Kampus).filter(
            func.lower(models.Kampus.KAM_Naam) == naam.lower(),
            models.Kampus.Kampus_ID != kampus_id,
        ).first()
        if bestaande:
            raise HTTPException(status_code=400, detail="Kampusnaam reeds in gebruik")
        kampus.KAM_Naam = naam

    if "KAM_Adres" in update_data:
        kampus.KAM_Adres = update_data["KAM_Adres"]

    db.commit()
    db.refresh(kampus)
    return schemas.APIResponse(sukses=True, data=kampus)


@router.delete("/{kampus_id}", response_model=schemas.APIResponse[dict])
def verwyder_kampus(
    kampus_id: int,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    kampus = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == kampus_id).first()
    if not kampus:
        raise HTTPException(status_code=404, detail="Kampus nie gevind nie")

    if db.query(models.Lokasie).filter(models.Lokasie.Kampus_ID == kampus_id).first():
        raise HTTPException(status_code=400, detail="Kan nie kampus verwyder nie: daar is nog lokale aan hierdie kampus gekoppel")
    if db.query(models.Koshuis).filter(models.Koshuis.Kampus_ID == kampus_id).first():
        raise HTTPException(status_code=400, detail="Kan nie kampus verwyder nie: daar is nog koshuise aan hierdie kampus gekoppel")
    if db.query(models.Funksie).filter(models.Funksie.Kampus_ID == kampus_id).first():
        raise HTTPException(status_code=400, detail="Kan nie kampus verwyder nie: daar is nog funksies aan hierdie kampus gekoppel")
    if db.query(models.Kampus_Opsigter).filter(models.Kampus_Opsigter.Kampus_ID == kampus_id).first():
        raise HTTPException(status_code=400, detail="Kan nie kampus verwyder nie: daar is nog opsigters aan hierdie kampus gekoppel")

    db.delete(kampus)
    db.commit()
    return schemas.APIResponse(sukses=True, data={"boodskap": "Kampus suksesvol verwyder"})


@router.get("/status", response_model=schemas.APIResponse[List[schemas.KampusSummaryStatus]])
def kry_kampus_status_opsomming(db: Session = Depends(get_db)):
    kampusse = db.query(models.Kampus).all()
    resultate = []
    for k in kampusse:
        scanned_in, scanned_out = haal_laatste_logs_per_gebruiker(db, kampus_id=k.Kampus_ID)
        resultate.append(schemas.KampusSummaryStatus(
            Kampus_ID=k.Kampus_ID,
            KAM_Naam=k.KAM_Naam,
            KAM_Adres=k.KAM_Adres,
            scanned_in_count=len(scanned_in),
            scanned_out_count=len(scanned_out)
        ))
    return schemas.APIResponse(sukses=True, data=resultate)


@router.get("/{kampus_id}/status", response_model=schemas.APIResponse[schemas.KampusDetailStatus])
def kry_kampus_status_detail(kampus_id: int, db: Session = Depends(get_db)):
    kampus = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == kampus_id).first()
    if not kampus:
        raise HTTPException(status_code=404, detail="Kampus nie gevind nie")

    scanned_in, scanned_out = haal_laatste_logs_per_gebruiker(db, kampus_id=kampus_id)

    return schemas.APIResponse(
        sukses=True,
        data=schemas.KampusDetailStatus(
            Kampus_ID=kampus.Kampus_ID,
            KAM_Naam=kampus.KAM_Naam,
            scanned_in_count=len(scanned_in),
            scanned_out_count=len(scanned_out),
            scanned_in=scanned_in,
            scanned_out=scanned_out
        )
    )

import json
from pathlib import Path

@router.get("/{kampus_id}/lokaalgebruik", response_model=schemas.APIResponse[List[schemas.LokaalGebruikGleuf]])
def kry_lokaalgebruik(
    kampus_id: int, 
    week: int = 14, 
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user)
):
    # Trek lokale
    lokasies = db.query(models.Lokasie).filter(
        models.Lokasie.Kampus_ID == kampus_id,
        models.Lokasie.LOK_Tipe == 'klaskamer'
    ).all()
    
    lokasie_ids = [l.Lokasie_ID for l in lokasies]
    lokasie_map = {l.Lokasie_ID: l for l in lokasies}
    
    if not lokasie_ids:
        return schemas.APIResponse(sukses=True, data=[])

    # Trek klasse vir hierdie lokale
    klasse = db.query(models.Klas, models.Module).join(
        models.Module, models.Klas.Module_ID == models.Module.Module_ID
    ).filter(models.Klas.Lokasie_ID.in_(lokasie_ids)).all()
    
    # Inskrywings (studente in module/klas)
    inskrywings = db.query(
        models.Student_Klas.Klas_ID, 
        func.count(models.Student_Klas.Gebruiker_ID).label('totaal')
    ).group_by(models.Student_Klas.Klas_ID).all()
    inskrywing_map = {r.Klas_ID: r.totaal for r in inskrywings}
    
    # Lees voorspellings
    voorspelling_pad = Path(__file__).parent.parent / "ml_data" / "huidige_voorspelling.json"
    voorspellings = {}
    if voorspelling_pad.exists():
        with open(voorspelling_pad, "r", encoding="utf-8") as f:
            data = json.load(f)
            voorspellings = data.get(str(week), {})
            
    # Bou response data en spoor konflikte op
    # Oorvleueling in dieselfde lokaal en dag:
    tye_per_lokaal_dag = {}
    
    uitset = []
    
    for klas, mod in klasse:
        lokaal = lokasie_map[klas.Lokasie_ID]
        inskrywing = inskrywing_map.get(klas.Klas_ID, 0)
        
        # Sleutel soos in ML skrip
        key = f"{mod.MOD_Kode}_{lokaal.LOK_Naam}_{klas.KLA_Dag}_{klas.KLA_Begin_Tyd}"
        
        v_data = voorspellings.get(key, {})
        koers = v_data.get("koers", 1.0) # Verval na 1.0 (Rooster) as geen data is nie
        bron = v_data.get("bron", "ROOSTER (Verstek)")
        
        verwagte_skanderings = int(inskrywing * koers)
        vulgraad = None
        if lokaal.LOK_Kapasiteit and lokaal.LOK_Kapasiteit > 0:
            vulgraad = verwagte_skanderings / lokaal.LOK_Kapasiteit
            
        gleuf = schemas.LokaalGebruikGleuf(
            Vak=mod.MOD_Kode,
            Lokaal=lokaal.LOK_Naam,
            Dag=klas.KLA_Dag,
            Begin=klas.KLA_Begin_Tyd,
            Einde=klas.KLA_Eind_Tyd,
            Inskrywing=inskrywing,
            Kapasiteit=lokaal.LOK_Kapasiteit,
            Verwagte_Skanderings=verwagte_skanderings,
            Vulgraad=vulgraad,
            Bron=bron,
            Konflik=False
        )
        
        # Konflik spoor
        lok_dag_key = (klas.Lokasie_ID, klas.KLA_Dag)
        if lok_dag_key not in tye_per_lokaal_dag:
            tye_per_lokaal_dag[lok_dag_key] = []
        tye_per_lokaal_dag[lok_dag_key].append(gleuf)
        
        uitset.append(gleuf)
        
    # Vlag konflikte in O(N^2) per lokaal per dag (gewoonlik baie klein getal N)
    for lok_dag, gleuwe in tye_per_lokaal_dag.items():
        for i, g1 in enumerate(gleuwe):
            for j, g2 in enumerate(gleuwe):
                if i != j:
                    # Simpel tyd oorvleueling tjeks (as strings, veronderstel '08:00' format)
                    if g1.Begin < g2.Einde and g1.Einde > g2.Begin:
                        g1.Konflik = True
                        g2.Konflik = True

    return schemas.APIResponse(sukses=True, data=uitset)

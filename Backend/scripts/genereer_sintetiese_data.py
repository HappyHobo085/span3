import sys
import os
import json
import csv
import random
import math
from datetime import datetime, timedelta
from pathlib import Path

# Maak seker ons kan Backend modules invoer
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import SessionLocal
from models import Klas, Lokasie, Kampus, Student_Klas, Module
from sqlalchemy import func

def laai_konfigurasie():
    config_pad = Path(__file__).parent / "synth_config.json"
    with open(config_pad, "r", encoding="utf-8") as f:
        return json.load(f)

def bereken_sessie_bywoning(sessie_basis, week, dag, begin_tyd, config):
    # Vervalfaktor oor 14 weke (bv. 2% drop per week)
    verval = 1.0 - (week * config.get("semester_verval_faktor", 0.02))
    
    # Dag verstellings (Vrydae is laer)
    dag_faktor = config.get("daaglikse_verstellings", {}).get(dag, 1.0)
    
    # Tyd verstellings (08:00 is laer)
    tyd_faktor = config.get("tyd_verstellings", {}).get(begin_tyd, 1.0)
    
    verwagte_koers = sessie_basis * verval * dag_faktor * tyd_faktor
    
    # Voeg swaar-stert ruis by (vir toetsweke, siektes, reën)
    if random.random() < config.get("ruis_swaar_stert_kans", 0.1):
        ruis = random.uniform(-config.get("ruis_swaar_stert_skaal", 0.3), 0.1)
    else:
        ruis = random.gauss(0, 0.05)
        
    finale_koers = min(max(verwagte_koers + ruis, 0.0), 1.0)
    return finale_koers

def genereer_data():
    config = laai_konfigurasie()
    random.seed(config.get("seed", 42))
    weke = config.get("weke", 14)
    
    db = SessionLocal()
    uitset_rye = []
    
    try:
        # Soek Leriba L2 tot L7
        lokasies = db.query(Lokasie).join(Kampus).filter(
            func.lower(Kampus.KAM_Naam) == 'leriba',
            Lokasie.LOK_Naam.in_(['L2', 'L3', 'L4', 'L5', 'L6', 'L7'])
        ).all()
        
        lokasie_ids = [l.Lokasie_ID for l in lokasies]
        lokasie_map = {l.Lokasie_ID: l for l in lokasies}
        
        # Trek sessies vir hierdie lokale
        klasse = db.query(Klas, Module).join(Module).filter(Klas.Lokasie_ID.in_(lokasie_ids)).all()
        
        # Bereken gewoonte-faktor per vak-sessie vooruit sodat dit konstant bly oor die semester
        sessie_gewoonte = {}
        for klas, mod in klasse:
            # Hoeveel studente is geregistreer vir hierdie klas (sessie)
            inskrywing = db.query(func.count(Student_Klas.Gebruiker_ID)).filter(
                Student_Klas.Klas_ID == klas.Klas_ID
            ).scalar()
            
            # Basis bywoning gewoonte vir hierdie vak/groep combo
            basis = random.gauss(config.get("gewoonte_basis_gemiddeld", 0.8), config.get("gewoonte_basis_std", 0.1))
            sessie_gewoonte[klas.Klas_ID] = min(max(basis, 0.3), 1.0)
            
            # Gegenereerde data oor 14 weke loop
            for week in range(1, weke + 1):
                koers = bereken_sessie_bywoning(
                    sessie_basis=sessie_gewoonte[klas.Klas_ID],
                    week=week,
                    dag=klas.KLA_Dag,
                    begin_tyd=klas.KLA_Begin_Tyd,
                    config=config
                )
                
                skanderings = int(inskrywing * koers)
                lokaal_obj = lokasie_map[klas.Lokasie_ID]
                
                uitset_rye.append({
                    "Week": week,
                    "Vak": mod.MOD_Kode,
                    "Lokaal": lokaal_obj.LOK_Naam,
                    "Dag": klas.KLA_Dag,
                    "Begin": klas.KLA_Begin_Tyd,
                    "Einde": klas.KLA_Eind_Tyd,
                    "Inskrywing": inskrywing,
                    "Kapasiteit": lokaal_obj.LOK_Kapasiteit or 0,
                    "Skanderings": skanderings
                })

    finally:
        db.close()
        
    # Skryf CSV
    uitset_pad = Path(__file__).parent.parent / "ml_data" / "sintetiese_lokaalgebruik.csv"
    os.makedirs(uitset_pad.parent, exist_ok=True)
    
    with open(uitset_pad, "w", newline="", encoding="utf-8") as f:
        skrywer = csv.DictWriter(f, fieldnames=[
            "Week", "Vak", "Lokaal", "Dag", "Begin", "Einde", "Inskrywing", "Kapasiteit", "Skanderings"
        ])
        skrywer.writeheader()
        skrywer.writerows(uitset_rye)
        
    print(f"Suksesvol gegenereer: {len(uitset_rye)} rye sintetiese data na {uitset_pad.name}.")

if __name__ == "__main__":
    genereer_data()

import sys
import os
import csv
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import func

# Maak seker ons kan Backend modules invoer
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import SessionLocal
from models import Lokasie, Kampus

def vul_lokasies():
    csv_pad = Path(__file__).parent.parent / "ml_data" / "lokale.csv"
    if not csv_pad.exists():
        print(f"Fout: Kan nie {csv_pad} vind nie.")
        return

    db = SessionLocal()
    opgedateer_aantal = 0
    foute = []

    try:
        with open(csv_pad, mode='r', encoding='utf-8', errors='replace') as f:
            leser = csv.DictReader(f)
            # Normaliseer kolomme se hoofletters sodat dit makliker pas (if needed)
            headers = [h.strip().lower() for h in leser.fieldnames or []]
            leser.fieldnames = headers

            for ry_nommer, ry in enumerate(leser, start=2):
                lokaal_kode = ry.get('lokaal', '').strip()
                kampus_naam = ry.get('kampus', '').strip()
                kapasiteit_str = ry.get('kapasiteit', '').strip()

                if not lokaal_kode or not kapasiteit_str:
                    continue
                
                try:
                    kapasiteit = int(kapasiteit_str)
                except ValueError:
                    foute.append(f"Ry {ry_nommer}: Ongeldige kapasiteit '{kapasiteit_str}' vir {lokaal_kode}")
                    continue

                # Soek die kampus (ignore case)
                kampus = db.query(Kampus).filter(func.lower(Kampus.KAM_Naam) == kampus_naam.lower()).first()
                if not kampus:
                    foute.append(f"Ry {ry_nommer}: Kampus nie gevind nie - '{kampus_naam}'")
                    continue

                # Soek die lokaal (ignore case) binne die kampus
                lokasie = db.query(Lokasie).filter(
                    func.lower(Lokasie.LOK_Naam) == lokaal_kode.lower(),
                    Lokasie.Kampus_ID == kampus.Kampus_ID,
                    Lokasie.LOK_Tipe == 'klaskamer'
                ).first()

                if lokasie:
                    lokasie.LOK_Kapasiteit = kapasiteit
                    opgedateer_aantal += 1
                else:
                    foute.append(f"Ry {ry_nommer}: Klaskamer nie gevind nie - '{lokaal_kode}' op kampus '{kampus_naam}'")

        db.commit()
        print(f"Suksesvol: {opgedateer_aantal} lokale opgedateer met nuwe kapasiteite.")
        
        if foute:
            print("\nDie volgende lokale uit die CSV kon nie suksesvol gekarteer word nie:")
            for fout in foute:
                print(f" - {fout}")

    except Exception as e:
        db.rollback()
        print(f"Fout tydens uitvoering: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    vul_lokasies()

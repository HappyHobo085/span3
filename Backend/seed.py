from database import SessionLocal
from models import Rolle, Kampus, Lokasie, NFC_Tags

def seed():
    db = SessionLocal()
    try:
        # --- Rolle ---
        if not db.query(Rolle).first():
            db.add_all([
                Rolle(ROL_Naam="Admin"),
                Rolle(ROL_Naam="Kampus_Opsigter"),
                Rolle(ROL_Naam="Sekuriteit_Wag"),
                Rolle(ROL_Naam="Personeel"),
                Rolle(ROL_Naam="Student"),
            ])
            db.commit()
            print("✅ Rolle gesaai")

        # --- Kampusse ---
        if not db.query(Kampus).first():

            # Elke kampus apart sodat ons Kampus_ID kan kry na commit
            leriba = Kampus(KAM_Naam="Leriba", KAM_Adres="245 End St, Clubview, Centurion, 0157")
            paarl  = Kampus(KAM_Naam="Paarl",  KAM_Adres="1 Breda St, Esterville, Paarl, 7646")
            gerhard = Kampus(KAM_Naam="Gerhard", KAM_Adres="117 Gerhard St, Die Hoewes, Centurion, 0163")

            db.add_all([leriba, paarl, gerhard])
            db.commit()
            # Refresh om die outomatiese Kampus_ID te laai
            db.refresh(leriba)
            db.refresh(paarl)
            db.refresh(gerhard)
            print("✅ Kampusse gesaai")

        # --- Lokasies ---
        if not db.query(Lokasie).first():
            # Haal Kampus_ID's op uit die DB
            leriba  = db.query(Kampus).filter_by(KAM_Naam="Leriba").first()
            paarl   = db.query(Kampus).filter_by(KAM_Naam="Paarl").first()
            gerhard = db.query(Kampus).filter_by(KAM_Naam="Gerhard").first()

            db.add_all([
                # Leriba
                Lokasie(LOK_Naam="Koning Protea", LOK_Tipe="Lokaal", Kampus_ID=leriba.Kampus_ID),
                Lokasie(LOK_Naam="Studiesaal",    LOK_Tipe="Lokaal", Kampus_ID=leriba.Kampus_ID),
                Lokasie(LOK_Naam="Bosvy",         LOK_Tipe="Lokaal", Kampus_ID=leriba.Kampus_ID),
                Lokasie(LOK_Naam="Bitterbessie",  LOK_Tipe="Lokaal", Kampus_ID=leriba.Kampus_ID),
                Lokasie(LOK_Naam="Sitkamer",      LOK_Tipe="Lokaal", Kampus_ID=leriba.Kampus_ID),
                Lokasie(LOK_Naam="Jakkalsbessie", LOK_Tipe="Lokaal", Kampus_ID=leriba.Kampus_ID),
                Lokasie(LOK_Naam="Huilboom",      LOK_Tipe="Lokaal", Kampus_ID=leriba.Kampus_ID),
                Lokasie(LOK_Naam="Broodboom",     LOK_Tipe="Lokaal", Kampus_ID=leriba.Kampus_ID),
                Lokasie(LOK_Naam="Boardroom",     LOK_Tipe="Lokaal", Kampus_ID=leriba.Kampus_ID),
                Lokasie(LOK_Naam="Hardekool",     LOK_Tipe="Lokaal", Kampus_ID=leriba.Kampus_ID),
                # Paarl
                Lokasie(LOK_Naam="L1", LOK_Tipe="Lokaal", Kampus_ID=paarl.Kampus_ID),
                Lokasie(LOK_Naam="L2", LOK_Tipe="Lokaal", Kampus_ID=paarl.Kampus_ID),
                Lokasie(LOK_Naam="L3", LOK_Tipe="Lokaal", Kampus_ID=paarl.Kampus_ID),
                Lokasie(LOK_Naam="L4", LOK_Tipe="Lokaal", Kampus_ID=paarl.Kampus_ID),
                Lokasie(LOK_Naam="L5", LOK_Tipe="Lokaal", Kampus_ID=paarl.Kampus_ID),
                Lokasie(LOK_Naam="L6", LOK_Tipe="Lokaal", Kampus_ID=paarl.Kampus_ID),
                Lokasie(LOK_Naam="L7", LOK_Tipe="Lokaal", Kampus_ID=paarl.Kampus_ID),
                # Gerhard
                Lokasie(LOK_Naam="Lokaal A", LOK_Tipe="Lokaal", Kampus_ID=gerhard.Kampus_ID),
                Lokasie(LOK_Naam="Lokaal B", LOK_Tipe="Lokaal", Kampus_ID=gerhard.Kampus_ID),
                Lokasie(LOK_Naam="Lokaal C", LOK_Tipe="Lokaal", Kampus_ID=gerhard.Kampus_ID),
                Lokasie(LOK_Naam="Lokaal D", LOK_Tipe="Lokaal", Kampus_ID=gerhard.Kampus_ID),
                Lokasie(LOK_Naam="Lokaal E", LOK_Tipe="Lokaal", Kampus_ID=gerhard.Kampus_ID),
            ])
            db.commit()
            print("✅ Lokasies gesaai")

    finally:
        db.close()

if __name__ == "__main__":
    seed()
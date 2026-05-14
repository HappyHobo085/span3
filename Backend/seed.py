from database import Base, engine, SessionLocal
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
                Rolle(ROL_Naam="Student"),
            ])
            db.commit()
            print("✅ Rolle gesaai")

        # --- Kampus ---
        if not db.query(Kampus).first():
            kampus = Kampus(KAM_Naam="Hoofkampus", KAM_Adres="123 Universiteitsweg")
            db.add(kampus)
            db.commit()
            db.refresh(kampus)
            print("✅ Kampus gesaai")

            # --- Lokasie ---
            lok = Lokasie(LOK_Naam="Saal A101", LOK_Tipe="Klaskamer", Kampus_ID=kampus.Kampus_ID)
            db.add(lok)
            db.commit()
            db.refresh(lok)
            print("✅ Lokasie gesaai")

            # --- NFC Tag ---
            db.add(NFC_Tags(NFC_UID="AA:BB:CC:DD", Lokasie_ID=lok.Lokasie_ID, NFC_Tipe="SAAL"))
            db.commit()
            print("✅ NFC Tag gesaai")

    finally:
        db.close()

if __name__ == "__main__":
    seed()
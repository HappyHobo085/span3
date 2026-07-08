from database import SessionLocal
from models import Rolle, Kampus, Lokasie, NFC_Tags, Gebruikers, Sekuriteit_Wag, Student, ToegangsLogs
import auth

def seed():
    db = SessionLocal()
    try:
        # --- Rolle ---
        rol_name_lys = ["Administrateur", "Kampus_Opsigter", "Sekuriteit_Wag", "Personeel", "Student"]
        for r_naam in rol_name_lys:
            bestaande = db.query(Rolle).filter_by(ROL_Naam=r_naam).first()
            if not bestaande:
                # As daar 'n ou "Admin" rol is, verander dit na "Administrateur"
                if r_naam == "Administrateur":
                    ou_admin = db.query(Rolle).filter_by(ROL_Naam="Admin").first()
                    if ou_admin:
                        ou_admin.ROL_Naam = "Administrateur"
                        db.commit()
                        print("✅ Rol 'Admin' opgedateer na 'Administrateur'")
                        continue
                
                db.add(Rolle(ROL_Naam=r_naam))
                db.commit()
                print(f"✅ Rol '{r_naam}' bygevoeg")

        # --- Kampusse ---
        if not db.query(Kampus).first():
            leriba = Kampus(KAM_Naam="Leriba", KAM_Adres="245 End St, Clubview, Centurion, 0157")
            paarl  = Kampus(KAM_Naam="Paarl",  KAM_Adres="1 Breda St, Esterville, Paarl, 7646")
            gerhard = Kampus(KAM_Naam="Gerhard", KAM_Adres="117 Gerhard St, Die Hoewes, Centurion, 0163")

            db.add_all([leriba, paarl, gerhard])
            db.commit()
            db.refresh(leriba)
            db.refresh(paarl)
            db.refresh(gerhard)
            print("✅ Kampusse gesaai")

        # --- Lokasies ---
        if not db.query(Lokasie).first():
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

    # --- Kampus Hek Lokasies ---
        kampusse = db.query(Kampus).all()

        for kampus in kampusse:
            bestaande_hek = db.query(Lokasie).filter(
                Lokasie.Kampus_ID == kampus.Kampus_ID,
                Lokasie.LOK_Tipe == "Kampus"
            ).first()

            if not bestaande_hek:
                db.add(
                    Lokasie(
                        LOK_Naam=f"{kampus.KAM_Naam} Hek",
                        LOK_Tipe="Kampus",
                        Kampus_ID=kampus.Kampus_ID
                    )
                )
                print(f"✅ Kampus hek geskep vir {kampus.KAM_Naam}")

        db.commit()

        # --- Gebruikers ---
        if not db.query(Gebruikers).first():
            admin_rol = db.query(Rolle).filter_by(ROL_Naam="Administrateur").first()
            wag_rol = db.query(Rolle).filter_by(ROL_Naam="Sekuriteit_Wag").first()
            stud_rol = db.query(Rolle).filter_by(ROL_Naam="Student").first()

            # Admin
            admin_user = Gebruikers(
                GEB_Naam="Admin",
                GEB_Van="Moon",
                GEB_ID_Nommer="9001015000081",
                GEB_Epos="admin@moon.com",
                GEB_Wagwoord=auth.get_password_hash("admin123"),
                GEB_Selfoon_Nr="0821234567",
                GEB_Profiel_Foto="https://placehold.co/150",
                Rol_ID=admin_rol.Rol_ID,
                Is_Aktief=True
            )

            # Sekuriteit Wag
            wag_user = Gebruikers(
                GEB_Naam="Wag",
                GEB_Van="Een",
                GEB_ID_Nommer="9505055000082",
                GEB_Epos="wag@moon.com",
                GEB_Wagwoord=auth.get_password_hash("wag123"),
                GEB_Selfoon_Nr="0827654321",
                GEB_Profiel_Foto="https://placehold.co/150",
                Rol_ID=wag_rol.Rol_ID,
                Is_Aktief=True
            )

            # Studente (Jan - Aktief, Piet - Inaktief)
            student_jan = Gebruikers(
                GEB_Naam="Jan",
                GEB_Van="Smit",
                GEB_ID_Nommer="0203045000083",
                GEB_Epos="jan.smit@student.com",
                GEB_Wagwoord=auth.get_password_hash("jan123"),
                GEB_Selfoon_Nr="0831112222",
                GEB_Profiel_Foto="https://placehold.co/150",
                Rol_ID=stud_rol.Rol_ID,
                Is_Aktief=True
            )

            student_piet = Gebruikers(
                GEB_Naam="Piet",
                GEB_Van="Pompies",
                GEB_ID_Nommer="0304055000084",
                GEB_Epos="piet.pompies@student.com",
                GEB_Wagwoord=auth.get_password_hash("piet123"),
                GEB_Selfoon_Nr="0833334444",
                GEB_Profiel_Foto="https://placehold.co/150",
                Rol_ID=stud_rol.Rol_ID,
                Is_Aktief=False
            )

            # Add more students to seed scanned in / scanned out status for each campus
            # Leriba (scanned out): Sannie
            student_sannie = Gebruikers(
                GEB_Naam="Sannie",
                GEB_Van="Smit",
                GEB_ID_Nommer="0405065000085",
                GEB_Epos="sannie.smit@student.com",
                GEB_Wagwoord=auth.get_password_hash("sannie123"),
                GEB_Selfoon_Nr="0835556666",
                GEB_Profiel_Foto="https://placehold.co/150",
                Rol_ID=stud_rol.Rol_ID,
                Is_Aktief=True
            )

            # Paarl (scanned in): Fanie
            student_fanie = Gebruikers(
                GEB_Naam="Fanie",
                GEB_Van="Botha",
                GEB_ID_Nommer="0506075000086",
                GEB_Epos="fanie.botha@student.com",
                GEB_Wagwoord=auth.get_password_hash("fanie123"),
                GEB_Selfoon_Nr="0837778888",
                GEB_Profiel_Foto="https://placehold.co/150",
                Rol_ID=stud_rol.Rol_ID,
                Is_Aktief=True
            )

            # Paarl (scanned out): Koos
            student_koos = Gebruikers(
                GEB_Naam="Koos",
                GEB_Van="van der Merwe",
                GEB_ID_Nommer="0607085000087",
                GEB_Epos="koos.vdm@student.com",
                GEB_Wagwoord=auth.get_password_hash("koos123"),
                GEB_Selfoon_Nr="0839990000",
                GEB_Profiel_Foto="https://placehold.co/150",
                Rol_ID=stud_rol.Rol_ID,
                Is_Aktief=True
            )

            # Gerhard (scanned in): Miena
            student_miena = Gebruikers(
                GEB_Naam="Miena",
                GEB_Van="Louw",
                GEB_ID_Nommer="0708095000088",
                GEB_Epos="miena.louw@student.com",
                GEB_Wagwoord=auth.get_password_hash("miena123"),
                GEB_Selfoon_Nr="0832223333",
                GEB_Profiel_Foto="https://placehold.co/150",
                Rol_ID=stud_rol.Rol_ID,
                Is_Aktief=True
            )

            db.add_all([
                admin_user, wag_user, student_jan, student_piet,
                student_sannie, student_fanie, student_koos, student_miena
            ])
            db.commit()

            db.refresh(admin_user)
            db.refresh(wag_user)
            db.refresh(student_jan)
            db.refresh(student_piet)
            db.refresh(student_sannie)
            db.refresh(student_fanie)
            db.refresh(student_koos)
            db.refresh(student_miena)

            # Saai sub-tabel vir Sekuriteit Wag
            wag_profiel = Sekuriteit_Wag(
                Gebruiker_ID=wag_user.Gebruiker_ID,
                SEK_Nommer="SEK001"
            )
            db.add(wag_profiel)

            # Saai sub-tabel vir Studente
            db.add_all([
                Student(Gebruiker_ID=student_jan.Gebruiker_ID, STU_Nommer="STU001"),
                Student(Gebruiker_ID=student_piet.Gebruiker_ID, STU_Nommer="STU002"),
                Student(Gebruiker_ID=student_sannie.Gebruiker_ID, STU_Nommer="STU003"),
                Student(Gebruiker_ID=student_fanie.Gebruiker_ID, STU_Nommer="STU005"),
                Student(Gebruiker_ID=student_koos.Gebruiker_ID, STU_Nommer="STU004"),
                Student(Gebruiker_ID=student_miena.Gebruiker_ID, STU_Nommer="STU006"),
            ])
            db.commit()

            # Nou saai ons ToegangsLogs vir ingeklokte/uitgeklokte statusse per kampus
            # Leriba lokasies
            l_koning = db.query(Lokasie).filter_by(LOK_Naam="Koning Protea").first()
            l_studie = db.query(Lokasie).filter_by(LOK_Naam="Studiesaal").first()
            # Paarl lokasies
            l_l1 = db.query(Lokasie).filter_by(LOK_Naam="L1").first()
            l_l2 = db.query(Lokasie).filter_by(LOK_Naam="L2").first()
            # Gerhard lokasies
            l_a = db.query(Lokasie).filter_by(LOK_Naam="Lokaal A").first()
            l_b = db.query(Lokasie).filter_by(LOK_Naam="Lokaal B").first()

            # Saai ToegangsLogs
            db.add_all([
                # Leriba: Jan is IN, Sannie is UIT
                ToegangsLogs(Gebruiker_ID=student_jan.Gebruiker_ID, Lokasie_ID=l_koning.Lokasie_ID, TOE_Rigting="IN", TOE_Metode="NFC"),
                ToegangsLogs(Gebruiker_ID=student_sannie.Gebruiker_ID, Lokasie_ID=l_studie.Lokasie_ID, TOE_Rigting="IN", TOE_Metode="NFC"),
                ToegangsLogs(Gebruiker_ID=student_sannie.Gebruiker_ID, Lokasie_ID=l_studie.Lokasie_ID, TOE_Rigting="UIT", TOE_Metode="NFC"),

                # Paarl: Fanie is IN, Koos is UIT
                ToegangsLogs(Gebruiker_ID=student_fanie.Gebruiker_ID, Lokasie_ID=l_l1.Lokasie_ID, TOE_Rigting="IN", TOE_Metode="NFC"),
                ToegangsLogs(Gebruiker_ID=student_koos.Gebruiker_ID, Lokasie_ID=l_l2.Lokasie_ID, TOE_Rigting="IN", TOE_Metode="NFC"),
                ToegangsLogs(Gebruiker_ID=student_koos.Gebruiker_ID, Lokasie_ID=l_l2.Lokasie_ID, TOE_Rigting="UIT", TOE_Metode="NFC"),

                # Gerhard: Miena is IN, Piet is UIT
                ToegangsLogs(Gebruiker_ID=student_miena.Gebruiker_ID, Lokasie_ID=l_a.Lokasie_ID, TOE_Rigting="IN", TOE_Metode="NFC"),
                ToegangsLogs(Gebruiker_ID=student_piet.Gebruiker_ID, Lokasie_ID=l_b.Lokasie_ID, TOE_Rigting="IN", TOE_Metode="NFC"),
                ToegangsLogs(Gebruiker_ID=student_piet.Gebruiker_ID, Lokasie_ID=l_b.Lokasie_ID, TOE_Rigting="UIT", TOE_Metode="NFC")
            ])
            db.commit()
            print("✅ Gebruikers en sub-rolle gesaai")

    finally:
        db.close()

if __name__ == "__main__":
    seed()
"""Idempotent startup migrations — extracted from main.py."""

from sqlalchemy import text


def run_migrations(engine):
    """Run idempotent schema migrations at startup."""
    # Migrasie 006: Maak koshuis.Kampus_ID nullable (create_all verander nie bestaande tabelle nie)
    try:
        with engine.connect() as _conn:
            _conn.execute(text('ALTER TABLE koshuis ALTER COLUMN "Kampus_ID" DROP NOT NULL'))
            _conn.execute(text('ALTER TABLE koshuis ALTER COLUMN "KOS_Kapasiteit" DROP DEFAULT'))
            _conn.commit()
    except Exception as _migrasie_fout:
        print(f"Waarskuwing: migrasie 006 (koshuis.Kampus_ID nullable) het misluk: {_migrasie_fout}")

    # Migrasie 007: Koppel student aan 'n spesifieke koshuis
    try:
        with engine.connect() as _conn:
            _conn.execute(text('ALTER TABLE student ADD COLUMN IF NOT EXISTS "Koshuis_ID" INT'))
            _conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'fk_student_koshuis'
                    ) THEN
                        ALTER TABLE student
                        ADD CONSTRAINT fk_student_koshuis
                        FOREIGN KEY ("Koshuis_ID") REFERENCES koshuis("Koshuis_ID");
                    END IF;
                END $$;
            """))
            _conn.commit()
    except Exception as _migrasie_fout:
        print(f"Waarskuwing: migrasie 007 (student.Koshuis_ID) het misluk: {_migrasie_fout}")

    # Migrasie 008: Saamry-vriende, groepe en groep-lede
    try:
        with engine.connect() as _conn:
            _conn.execute(text("""
                CREATE TABLE IF NOT EXISTS saamry_vriendskap (
                    "Vriendskap_ID" SERIAL PRIMARY KEY,
                    "Versoeker_ID" INT NOT NULL REFERENCES gebruikers("Gebruiker_ID"),
                    "Ontvanger_ID" INT NOT NULL REFERENCES gebruikers("Gebruiker_ID"),
                    "SAA_Status" VARCHAR(20) NOT NULL DEFAULT 'HANGEND',
                    "Geskep_Op" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    "Gewysig_Op" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_saamry_vriendskap_rigting
                        UNIQUE ("Versoeker_ID", "Ontvanger_ID"),
                    CONSTRAINT ck_saamry_vriendskap_nie_self
                        CHECK ("Versoeker_ID" <> "Ontvanger_ID"),
                    CONSTRAINT ck_saamry_vriendskap_status
                        CHECK ("SAA_Status" IN ('HANGEND', 'AANVAAR', 'GEWEIER'))
                )
            """))

            _conn.execute(text("""
                CREATE TABLE IF NOT EXISTS saamry_groep (
                    "Groep_ID" SERIAL PRIMARY KEY,
                    "Bestuurder_ID" INT NOT NULL REFERENCES gebruikers("Gebruiker_ID"),
                    "SAA_Naam" VARCHAR(120) NOT NULL,
                    "SAA_Vertrekpunt" VARCHAR(200) NOT NULL,
                    "SAA_Bestemming" VARCHAR(200) NOT NULL,
                    "SAA_Vertrek_Tyd" TIMESTAMP NOT NULL,
                    "SAA_Sitplekke" INT NOT NULL DEFAULT 1,
                    "SAA_Status" VARCHAR(20) NOT NULL DEFAULT 'AKTIEF',
                    "Geskep_Op" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    "Gewysig_Op" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT ck_saamry_groep_sitplekke
                        CHECK ("SAA_Sitplekke" BETWEEN 1 AND 8),
                    CONSTRAINT ck_saamry_groep_status
                        CHECK ("SAA_Status" IN ('AKTIEF', 'GESLUIT', 'GEKANSELLEER'))
                )
            """))

            _conn.execute(text("""
                CREATE TABLE IF NOT EXISTS saamry_groep_lid (
                    "Groep_ID" INT NOT NULL REFERENCES saamry_groep("Groep_ID"),
                    "Gebruiker_ID" INT NOT NULL REFERENCES gebruikers("Gebruiker_ID"),
                    "Genooi_Deur_ID" INT NOT NULL REFERENCES gebruikers("Gebruiker_ID"),
                    "SAA_Status" VARCHAR(20) NOT NULL DEFAULT 'HANGEND',
                    "Geskep_Op" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    "Gewysig_Op" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY ("Groep_ID", "Gebruiker_ID"),
                    CONSTRAINT ck_saamry_groep_lid_status
                        CHECK ("SAA_Status" IN ('HANGEND', 'AANVAAR', 'GEWEIER', 'VERLAAT'))
                )
            """))

            _conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_saamry_vriendskap_versoeker '
                'ON saamry_vriendskap ("Versoeker_ID")'
            ))
            _conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_saamry_vriendskap_ontvanger '
                'ON saamry_vriendskap ("Ontvanger_ID")'
            ))
            _conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_saamry_groep_bestuurder '
                'ON saamry_groep ("Bestuurder_ID")'
            ))
            _conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_saamry_groep_status '
                'ON saamry_groep ("SAA_Status")'
            ))
            _conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_saamry_groep_lid_gebruiker '
                'ON saamry_groep_lid ("Gebruiker_ID")'
            ))
            _conn.commit()
    except Exception as _migrasie_fout:
        print(f"Waarskuwing: migrasie 008 (Saamry) het misluk: {_migrasie_fout}")


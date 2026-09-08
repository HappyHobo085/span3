"""Idempotent startup migrations — extracted from main.py."""

from sqlalchemy import text


def run_pre_migrations(engine):
    """Rename legacy misspelled event tables before SQLAlchemy create_all()."""
    try:
        with engine.begin() as _conn:
            _conn.execute(text("""
                DO $$
                BEGIN
                    -- If only the old misspelled table exists, rename it.
                    IF to_regclass('public.funksie') IS NULL
                       AND to_regclass('public.funskie') IS NOT NULL THEN
                        ALTER TABLE public.funskie RENAME TO funksie;
                    END IF;

                    -- Same for the old event/visitor link table.
                    IF to_regclass('public.funksie_besoekers') IS NULL
                       AND to_regclass('public.funskie_besoekers') IS NOT NULL THEN
                        ALTER TABLE public.funskie_besoekers RENAME TO funksie_besoekers;
                    END IF;
                END $$;
            """))
    except Exception as _migrasie_fout:
        print(
            "Waarskuwing: pre-migrasie (funskie -> funksie) het misluk: "
            f"{_migrasie_fout}"
        )
        raise


def run_migrations(engine):
    """Run idempotent schema migrations at startup."""
    # Herstel die ou NFC-lokasie-FK wat na die vorige `lokasies(id)`-tabel gewys het.
    try:
        with engine.begin() as _conn:
            _conn.execute(text("""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'nfc_tags_Lokasie_ID_fkey'
                          AND conrelid = 'nfc_tags'::regclass
                    ) THEN
                        ALTER TABLE nfc_tags
                        DROP CONSTRAINT "nfc_tags_Lokasie_ID_fkey";
                    END IF;

                    ALTER TABLE nfc_tags
                    ADD CONSTRAINT "nfc_tags_Lokasie_ID_fkey"
                    FOREIGN KEY ("Lokasie_ID") REFERENCES lokasie("Lokasie_ID");
                END $$;
            """))
    except Exception as _migrasie_fout:
        print(f"Waarskuwing: migrasie NFC-lokasie-FK het misluk: {_migrasie_fout}")

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



    # Migrasie 009: Besoeker-OTP uitnodigings
    try:
        with engine.connect() as _conn:
            _conn.execute(text("""
                CREATE TABLE IF NOT EXISTS besoeker_uitnodiging (
                    "Uitnodiging_ID" SERIAL PRIMARY KEY,
                    "Gasheer_ID" INT NOT NULL REFERENCES gebruikers("Gebruiker_ID"),
                    "BES_Naam" VARCHAR(100) NOT NULL,
                    "BES_Van" VARCHAR(100) NOT NULL,
                    "BES_Selfoon_Nr" VARCHAR(20) NOT NULL,
                    "BES_Rede" VARCHAR(250) NOT NULL DEFAULT 'Besoek',
                    "BES_OTP" VARCHAR(6) NOT NULL,
                    "BES_Aktief_Sleutel" VARCHAR(6) NULL,
                    "BES_Status" VARCHAR(20) NOT NULL DEFAULT 'HANGEND',
                    "BES_Geskep_Op" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    "BES_Verval_Op" TIMESTAMP NOT NULL,
                    "BES_Besluit_Op" TIMESTAMP NULL,
                    "Verwerk_Deur_ID" INT NULL REFERENCES gebruikers("Gebruiker_ID"),
                    "Kampus_ID" INT NULL REFERENCES kampus("Kampus_ID"),
                    CONSTRAINT ck_besoeker_uitnodiging_status
                        CHECK ("BES_Status" IN (
                            'HANGEND', 'TOEGELAAT', 'GEWEIER',
                            'GEKANSELLEER', 'VERVAL'
                        ))
                )
            """))

            _conn.execute(text(
                'CREATE UNIQUE INDEX IF NOT EXISTS '
                'ux_besoeker_uitnodiging_aktief_sleutel '
                'ON besoeker_uitnodiging ("BES_Aktief_Sleutel")'
            ))
            _conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_besoeker_uitnodiging_gasheer '
                'ON besoeker_uitnodiging ("Gasheer_ID")'
            ))
            _conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_besoeker_uitnodiging_status '
                'ON besoeker_uitnodiging ("BES_Status")'
            ))
            _conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_besoeker_uitnodiging_otp '
                'ON besoeker_uitnodiging ("BES_OTP")'
            ))
            _conn.commit()
    except Exception as _migrasie_fout:
        print(
            "Waarskuwing: migrasie 009 "
            f"(Besoeker OTP-uitnodigings) het misluk: {_migrasie_fout}"
        )

    # Migrasie 010: Koppel toegangslogs aan Saamry-groep en bestuurder se heklog
    try:
        with engine.connect() as _conn:
            _conn.execute(text(
                'ALTER TABLE toegangs_logs '
                'ADD COLUMN IF NOT EXISTS "Saamry_Groep_ID" INT NULL'
            ))
            _conn.execute(text(
                'ALTER TABLE toegangs_logs '
                'ADD COLUMN IF NOT EXISTS "Saamry_Bestuurder_Log_ID" INT NULL'
            ))

            _conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint c
                        JOIN pg_attribute a
                          ON a.attrelid = c.conrelid
                         AND a.attnum = ANY(c.conkey)
                        WHERE c.conrelid = 'toegangs_logs'::regclass
                          AND c.contype = 'f'
                          AND a.attname = 'Saamry_Groep_ID'
                    ) THEN
                        ALTER TABLE toegangs_logs
                        ADD CONSTRAINT fk_toegangs_logs_saamry_groep
                        FOREIGN KEY ("Saamry_Groep_ID")
                        REFERENCES saamry_groep("Groep_ID");
                    END IF;
                END $$;
            """))

            _conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint c
                        JOIN pg_attribute a
                          ON a.attrelid = c.conrelid
                         AND a.attnum = ANY(c.conkey)
                        WHERE c.conrelid = 'toegangs_logs'::regclass
                          AND c.contype = 'f'
                          AND a.attname = 'Saamry_Bestuurder_Log_ID'
                    ) THEN
                        ALTER TABLE toegangs_logs
                        ADD CONSTRAINT fk_toegangs_logs_saamry_bestuurder_log
                        FOREIGN KEY ("Saamry_Bestuurder_Log_ID")
                        REFERENCES toegangs_logs("Log_ID");
                    END IF;
                END $$;
            """))

            _conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_toegangs_logs_saamry_groep '
                'ON toegangs_logs ("Saamry_Groep_ID")'
            ))
            _conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_toegangs_logs_saamry_bestuurder_log '
                'ON toegangs_logs ("Saamry_Bestuurder_Log_ID")'
            ))
            _conn.commit()
    except Exception as _migrasie_fout:
        print(
            "Waarskuwing: migrasie 010 "
            f"(Saamry-hek toegangslogs) het misluk: {_migrasie_fout}"
        )

    # Migrasie 011: Events / Funksie RSVP
    try:
        with engine.connect() as _conn:
            # Canonical event table is now "funksie".
            _conn.execute(text(
                'ALTER TABLE funksie ADD COLUMN IF NOT EXISTS "Lokasie_ID" INT NULL'
            ))
            _conn.execute(text(
                'ALTER TABLE funksie ADD COLUMN IF NOT EXISTS "Geskep_Deur_ID" INT NULL'
            ))
            _conn.execute(text(
                'ALTER TABLE funksie ADD COLUMN IF NOT EXISTS "FUN_Kapasiteit" INT NOT NULL DEFAULT 100'
            ))
            _conn.execute(text(
                'ALTER TABLE funksie ADD COLUMN IF NOT EXISTS "FUN_Status" VARCHAR(20) NOT NULL DEFAULT \'AKTIEF\''
            ))
            _conn.execute(text(
                'ALTER TABLE funksie ADD COLUMN IF NOT EXISTS "Geskep_Op" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP'
            ))
            _conn.execute(text(
                'ALTER TABLE funksie ADD COLUMN IF NOT EXISTS "Gewysig_Op" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP'
            ))

            _conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'fk_funksie_lokasie'
                    ) THEN
                        ALTER TABLE funksie
                        ADD CONSTRAINT fk_funksie_lokasie
                        FOREIGN KEY ("Lokasie_ID") REFERENCES lokasie("Lokasie_ID");
                    END IF;
                END $$;
            """))

            _conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'fk_funksie_geskep_deur'
                    ) THEN
                        ALTER TABLE funksie
                        ADD CONSTRAINT fk_funksie_geskep_deur
                        FOREIGN KEY ("Geskep_Deur_ID") REFERENCES gebruikers("Gebruiker_ID");
                    END IF;
                END $$;
            """))

            _conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'ck_funksie_kapasiteit'
                    ) THEN
                        ALTER TABLE funksie
                        ADD CONSTRAINT ck_funksie_kapasiteit CHECK ("FUN_Kapasiteit" > 0);
                    END IF;
                END $$;
            """))

            _conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'ck_funksie_status'
                    ) THEN
                        ALTER TABLE funksie
                        ADD CONSTRAINT ck_funksie_status
                        CHECK ("FUN_Status" IN ('AKTIEF', 'GEKANSELLEER'));
                    END IF;
                END $$;
            """))

            # If the old "funskie" table still exists as well as "funksie",
            # preserve its old event rows by copying the common columns across.
            _conn.execute(text("""
                DO $$
                BEGIN
                    IF to_regclass('public.funksie') IS NOT NULL
                       AND to_regclass('public.funskie') IS NOT NULL THEN
                        INSERT INTO funksie (
                            "Funksie_ID",
                            "Kampus_ID",
                            "FUN_Naam",
                            "FUN_Begin_Tyd",
                            "FUN_Eind_Tyd",
                            "FUN_Beskrywing",
                            "FUN_Is_Aktief"
                        )
                        SELECT
                            "Funksie_ID",
                            "Kampus_ID",
                            "FUN_Naam",
                            "FUN_Begin_Tyd",
                            "FUN_Eind_Tyd",
                            "FUN_Beskrywing",
                            "FUN_Is_Aktief"
                        FROM funskie
                        ON CONFLICT ("Funksie_ID") DO NOTHING;
                    END IF;
                END $$;
            """))

            # Create RSVP table if it does not yet exist.
            _conn.execute(text("""
                CREATE TABLE IF NOT EXISTS funksie_rsvp (
                    "Funksie_ID" INT NOT NULL,
                    "Gebruiker_ID" INT NOT NULL REFERENCES gebruikers("Gebruiker_ID"),
                    "RSVP_Status" VARCHAR(20) NOT NULL DEFAULT 'GAAN',
                    "RSVP_Tyd" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    "Gewysig_Op" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY ("Funksie_ID", "Gebruiker_ID"),
                    CONSTRAINT ck_funksie_rsvp_status
                        CHECK ("RSVP_Status" IN ('GAAN', 'KAN_NIE', 'GEKANSELLEER'))
                )
            """))

            # IMPORTANT: Earlier versions created this FK against the old "funskie"
            # table. Drop whichever FK is currently attached to Funksie_ID and recreate
            # it against the canonical "funksie" table.
            _conn.execute(text("""
                DO $$
                DECLARE
                    _fk RECORD;
                BEGIN
                    FOR _fk IN
                        SELECT c.conname
                        FROM pg_constraint c
                        JOIN pg_attribute a
                          ON a.attrelid = c.conrelid
                         AND a.attnum = ANY(c.conkey)
                        WHERE c.conrelid = 'funksie_rsvp'::regclass
                          AND c.contype = 'f'
                          AND a.attname = 'Funksie_ID'
                    LOOP
                        EXECUTE format(
                            'ALTER TABLE funksie_rsvp DROP CONSTRAINT %I',
                            _fk.conname
                        );
                    END LOOP;

                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conrelid = 'funksie_rsvp'::regclass
                          AND conname = 'fk_funksie_rsvp_funksie'
                    ) THEN
                        ALTER TABLE funksie_rsvp
                        ADD CONSTRAINT fk_funksie_rsvp_funksie
                        FOREIGN KEY ("Funksie_ID")
                        REFERENCES funksie("Funksie_ID")
                        ON DELETE CASCADE;
                    END IF;
                END $$;
            """))

            # If both visitor-link tables exist, copy legacy links to the canonical one.
            _conn.execute(text("""
                DO $$
                BEGIN
                    IF to_regclass('public.funksie_besoekers') IS NOT NULL
                       AND to_regclass('public.funskie_besoekers') IS NOT NULL THEN
                        INSERT INTO funksie_besoekers (
                            "Besoekers_Groep_ID",
                            "Funksie_ID",
                            "FUNB_Status"
                        )
                        SELECT
                            "Besoekers_Groep_ID",
                            "Funksie_ID",
                            "FUNB_Status"
                        FROM funskie_besoekers
                        ON CONFLICT ("Besoekers_Groep_ID", "Funksie_ID") DO NOTHING;
                    END IF;
                END $$;
            """))

            # Also guarantee the canonical visitor link points to canonical "funksie".
            _conn.execute(text("""
                DO $$
                DECLARE
                    _fk RECORD;
                BEGIN
                    IF to_regclass('public.funksie_besoekers') IS NOT NULL THEN
                        FOR _fk IN
                            SELECT c.conname
                            FROM pg_constraint c
                            JOIN pg_attribute a
                              ON a.attrelid = c.conrelid
                             AND a.attnum = ANY(c.conkey)
                            WHERE c.conrelid = 'funksie_besoekers'::regclass
                              AND c.contype = 'f'
                              AND a.attname = 'Funksie_ID'
                        LOOP
                            EXECUTE format(
                                'ALTER TABLE funksie_besoekers DROP CONSTRAINT %I',
                                _fk.conname
                            );
                        END LOOP;

                        IF NOT EXISTS (
                            SELECT 1
                            FROM pg_constraint
                            WHERE conrelid = 'funksie_besoekers'::regclass
                              AND conname = 'fk_funksie_besoekers_funksie'
                        ) THEN
                            ALTER TABLE funksie_besoekers
                            ADD CONSTRAINT fk_funksie_besoekers_funksie
                            FOREIGN KEY ("Funksie_ID")
                            REFERENCES funksie("Funksie_ID")
                            ON DELETE CASCADE;
                        END IF;
                    END IF;
                END $$;
            """))

            _conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_funksie_begin_tyd ON funksie ("FUN_Begin_Tyd")'
            ))
            _conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_funksie_kampus ON funksie ("Kampus_ID")'
            ))
            _conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_funksie_rsvp_gebruiker ON funksie_rsvp ("Gebruiker_ID")'
            ))
            _conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_funksie_rsvp_status ON funksie_rsvp ("RSVP_Status")'
            ))

            _conn.commit()
    except Exception as _migrasie_fout:
        print(
            "Waarskuwing: migrasie 011 "
            f"(Events / Funksie RSVP) het misluk: {_migrasie_fout}"
        )

    # Migrasie 012: Publieke Event Deel-skakels + eksterne RSVP's
    try:
        with engine.connect() as _conn:
            _conn.execute(text('''
                ALTER TABLE funksie
                ADD COLUMN IF NOT EXISTS "FUN_Deel_Token" VARCHAR(80)
            '''))

            _conn.execute(text('''
                CREATE UNIQUE INDEX IF NOT EXISTS uq_funksie_deel_token
                ON funksie ("FUN_Deel_Token")
                WHERE "FUN_Deel_Token" IS NOT NULL
            '''))

            _conn.execute(text('''
                CREATE TABLE IF NOT EXISTS funksie_publiek_rsvp (
                    "Publiek_RSVP_ID" SERIAL PRIMARY KEY,
                    "Funksie_ID" INT NOT NULL,
                    "Naam" VARCHAR(100) NOT NULL,
                    "Van" VARCHAR(100) NOT NULL,
                    "Selfoon" VARCHAR(30) NOT NULL,
                    "Epos" VARCHAR(255),
                    "QR_Token" VARCHAR(120) NOT NULL UNIQUE,
                    "RSVP_Status" VARCHAR(20) NOT NULL DEFAULT 'GAAN',
                    "RSVP_Tyd" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    "Gewysig_Op" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_funksie_publiek_rsvp_funksie
                        FOREIGN KEY ("Funksie_ID")
                        REFERENCES funksie("Funksie_ID")
                        ON DELETE CASCADE,
                    CONSTRAINT ck_funksie_publiek_rsvp_status
                        CHECK ("RSVP_Status" IN ('GAAN', 'GEKANSELLEER'))
                )
            '''))

            _conn.execute(text('''
                CREATE INDEX IF NOT EXISTS ix_funksie_publiek_rsvp_funksie
                ON funksie_publiek_rsvp ("Funksie_ID")
            '''))
            _conn.execute(text('''
                CREATE INDEX IF NOT EXISTS ix_funksie_publiek_rsvp_status
                ON funksie_publiek_rsvp ("RSVP_Status")
            '''))
            _conn.execute(text('''
                CREATE UNIQUE INDEX IF NOT EXISTS uq_funksie_publiek_rsvp_qr
                ON funksie_publiek_rsvp ("QR_Token")
            '''))

            _conn.commit()
    except Exception as _migrasie_fout:
        print(
            "Waarskuwing: migrasie 012 "
            f"(Publieke Event RSVP) het misluk: {_migrasie_fout}"
        )



    # Migrasie 013: Event Live Attendance + eksterne Event hektoegang
    try:
        with engine.connect() as _conn:
            # Maak bestaande aktiewe duplicate publieke RSVP's skoon voordat die
            # databasis-unique index bygevoeg word. Hou die oudste aktiewe RSVP.
            _conn.execute(text('''
                WITH ranked AS (
                    SELECT
                        "Publiek_RSVP_ID",
                        ROW_NUMBER() OVER (
                            PARTITION BY
                                "Funksie_ID",
                                lower(trim("Naam")),
                                lower(trim("Van")),
                                "Selfoon"
                            ORDER BY "RSVP_Tyd" ASC, "Publiek_RSVP_ID" ASC
                        ) AS rn
                    FROM funksie_publiek_rsvp
                    WHERE "RSVP_Status" = 'GAAN'
                )
                UPDATE funksie_publiek_rsvp p
                SET "RSVP_Status" = 'GEKANSELLEER',
                    "Gewysig_Op" = CURRENT_TIMESTAMP
                FROM ranked r
                WHERE p."Publiek_RSVP_ID" = r."Publiek_RSVP_ID"
                  AND r.rn > 1
            '''))

            _conn.execute(text('''
                CREATE UNIQUE INDEX IF NOT EXISTS uq_funksie_publiek_rsvp_aktiewe_identiteit
                ON funksie_publiek_rsvp (
                    "Funksie_ID",
                    lower(trim("Naam")),
                    lower(trim("Van")),
                    "Selfoon"
                )
                WHERE "RSVP_Status" = 'GAAN'
            '''))

            _conn.execute(text('''
                CREATE TABLE IF NOT EXISTS funksie_publiek_toegang (
                    "Toegang_ID" SERIAL PRIMARY KEY,
                    "Publiek_RSVP_ID" INT NOT NULL,
                    "Funksie_ID" INT NOT NULL,
                    "Kampus_ID" INT NOT NULL,
                    "Wag_ID" INT,
                    "Rigting" VARCHAR(16) NOT NULL,
                    "Metode" VARCHAR(32) NOT NULL DEFAULT 'QR',
                    "Tydstempel" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_funksie_publiek_toegang_rsvp
                        FOREIGN KEY ("Publiek_RSVP_ID")
                        REFERENCES funksie_publiek_rsvp("Publiek_RSVP_ID")
                        ON DELETE CASCADE,
                    CONSTRAINT fk_funksie_publiek_toegang_funksie
                        FOREIGN KEY ("Funksie_ID")
                        REFERENCES funksie("Funksie_ID")
                        ON DELETE CASCADE,
                    CONSTRAINT fk_funksie_publiek_toegang_kampus
                        FOREIGN KEY ("Kampus_ID")
                        REFERENCES kampus("Kampus_ID"),
                    CONSTRAINT fk_funksie_publiek_toegang_wag
                        FOREIGN KEY ("Wag_ID")
                        REFERENCES gebruikers("Gebruiker_ID"),
                    CONSTRAINT ck_funksie_publiek_toegang_rigting
                        CHECK ("Rigting" IN ('IN', 'UIT', 'GEWEIER')),
                    CONSTRAINT ck_funksie_publiek_toegang_metode
                        CHECK ("Metode" IN ('QR', 'HANDMATIG'))
                )
            '''))

            _conn.execute(text('''
                CREATE INDEX IF NOT EXISTS ix_funksie_publiek_toegang_event
                ON funksie_publiek_toegang ("Funksie_ID")
            '''))
            _conn.execute(text('''
                CREATE INDEX IF NOT EXISTS ix_funksie_publiek_toegang_rsvp
                ON funksie_publiek_toegang ("Publiek_RSVP_ID")
            '''))
            _conn.execute(text('''
                CREATE INDEX IF NOT EXISTS ix_funksie_publiek_toegang_kampus
                ON funksie_publiek_toegang ("Kampus_ID")
            '''))
            _conn.execute(text('''
                CREATE INDEX IF NOT EXISTS ix_funksie_publiek_toegang_tyd
                ON funksie_publiek_toegang ("Tydstempel")
            '''))

            _conn.commit()
    except Exception as _migrasie_fout:
        print(
            "Waarskuwing: migrasie 013 "
            f"(Event Live Attendance / publieke hektoegang) het misluk: {_migrasie_fout}"
        )

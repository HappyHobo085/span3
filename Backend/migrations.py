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

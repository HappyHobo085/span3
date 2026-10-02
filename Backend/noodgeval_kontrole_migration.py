"""MOON Step 7 database migration for emergency people verification.

Kept separate from the project's older migrations.py so Step 7 can be added without
replacing or risking the existing migration history.
"""

from sqlalchemy import text


def run_noodgeval_kontrole_migration(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS noodgeval_kontrole (
                "Kontrole_ID" SERIAL PRIMARY KEY,
                "Noodgeval_ID" INTEGER NOT NULL
                    REFERENCES noodgeval("Noodgeval_ID") ON DELETE CASCADE,
                "Gebruiker_ID" INTEGER NOT NULL
                    REFERENCES gebruikers("Gebruiker_ID") ON DELETE CASCADE,
                "Gemerk_Deur_ID" INTEGER NOT NULL
                    REFERENCES gebruikers("Gebruiker_ID"),
                "NKK_Status" VARCHAR(20) NOT NULL,
                "NKK_Gemerk_Op" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                "Gewysig_Op" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_noodgeval_kontrole_gebruiker
                    UNIQUE ("Noodgeval_ID", "Gebruiker_ID"),
                CONSTRAINT ck_noodgeval_kontrole_status
                    CHECK ("NKK_Status" IN ('DAAR', 'NIE_DAAR'))
            )
        '''))

        conn.execute(text('''
            CREATE INDEX IF NOT EXISTS ix_noodgeval_kontrole_noodgeval_status
            ON noodgeval_kontrole ("Noodgeval_ID", "NKK_Status")
        '''))
        conn.execute(text('''
            CREATE INDEX IF NOT EXISTS ix_noodgeval_kontrole_gebruiker
            ON noodgeval_kontrole ("Gebruiker_ID")
        '''))

"""MOON Noodgeval Step 10 — scoped long-lived device auth migration."""

from sqlalchemy import text


def run_noodgeval_device_migration(engine) -> None:
    """Create/update the device credential table idempotently."""
    with engine.begin() as conn:
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS noodgeval_device_auth (
                "DeviceAuth_ID" SERIAL PRIMARY KEY,
                "Gebruiker_ID" INTEGER NOT NULL REFERENCES gebruikers("Gebruiker_ID") ON DELETE CASCADE,
                "NDA_Device_ID" VARCHAR(255) NOT NULL,
                "NDA_Device_Name" VARCHAR(255),
                "NDA_Token_Hash" VARCHAR(64) NOT NULL UNIQUE,
                "NDA_Is_Aktief" BOOLEAN NOT NULL DEFAULT TRUE,
                "NDA_Geskep_Op" TIMESTAMP NOT NULL DEFAULT NOW(),
                "NDA_Laas_Gebruik_Op" TIMESTAMP NULL,
                "NDA_Verval_Op" TIMESTAMP NOT NULL,
                CONSTRAINT uq_noodgeval_device_user_device UNIQUE ("Gebruiker_ID", "NDA_Device_ID")
            )
        '''))

        conn.execute(text('''
            CREATE INDEX IF NOT EXISTS ix_noodgeval_device_auth_user
            ON noodgeval_device_auth ("Gebruiker_ID")
        '''))
        conn.execute(text('''
            CREATE INDEX IF NOT EXISTS ix_noodgeval_device_auth_token_hash
            ON noodgeval_device_auth ("NDA_Token_Hash")
        '''))
        conn.execute(text('''
            CREATE INDEX IF NOT EXISTS ix_noodgeval_device_auth_active_expiry
            ON noodgeval_device_auth ("NDA_Is_Aktief", "NDA_Verval_Op")
        '''))

import os
import sys
from pathlib import Path

import pytest

# Die toetse oefen die werklike auth-paaie uit. 'n Plaaslike .env met
# DISABLE_AUTH=1 (span-toetsing/Docker) mag nie die toetsgedrag verander nie —
# load_dotenv() oorskryf nie reeds-gestelde omgewingsveranderlikes nie.
os.environ["DISABLE_AUTH"] = "0"
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Die backend gebruik plat top-vlak imports (bv. `import models`)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import models  # noqa: E402
from database import Base  # noqa: E402


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def maak_gebruiker(db):
    """Skep 'n gebruiker met 'n gegewe rol en gee dit terug."""
    teller = {"n": 0}

    def _maak(rol_naam: str) -> models.Gebruikers:
        rol = db.query(models.Rolle).filter(models.Rolle.ROL_Naam == rol_naam).first()
        if not rol:
            rol = models.Rolle(ROL_Naam=rol_naam)
            db.add(rol)
            db.flush()

        teller["n"] += 1
        n = teller["n"]
        gebruiker = models.Gebruikers(
            GEB_Naam="Toets",
            GEB_Van=f"Gebruiker{n}",
            GEB_ID_Nommer=f"900101000000{n}",
            GEB_Epos=f"toets{n}@voorbeeld.co.za",
            GEB_Wagwoord="hashed",
            Rol_ID=rol.Rol_ID,
        )
        db.add(gebruiker)
        db.flush()
        return gebruiker

    return _maak

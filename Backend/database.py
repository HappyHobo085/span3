from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}"
    f"@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
)

# --- Connection pool tuning ---
# pool_pre_ping: verify connections before use (survives idle timeouts / restarts)
# pool_size: persistent connections in the pool (default is 5 — same here, explicit)
# max_overflow: extra connections allowed beyond pool_size under burst load
# pool_timeout: seconds to wait for a connection from the pool before raising
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
    pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
    pool_recycle=1800,  # recycle connections after 30 min to avoid stale DB connections
)

# Redacteer wagwoord vir veilige logging
_db_pass = os.getenv('DB_PASS', '')
if _db_pass:
    DATABASE_URL = DATABASE_URL.replace(f":{_db_pass}@", ":***@")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Gebruik hierdie in elke roete as 'n afhanklikheid
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
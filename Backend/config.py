import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # PostgreSQL verbinding string:
    SQLALCHEMY_DATABASE_URI = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "jou-geheime-sleutel")
    
    # Enable/disable CSV import/export functionality (default: enabled)
    CSV_IMPORT_EXPORT_ENABLED = os.getenv("CSV_IMPORT_EXPORT_ENABLED", "true").lower() == "true"
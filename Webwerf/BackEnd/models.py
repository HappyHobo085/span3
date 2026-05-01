from database import db
from datetime import datetime

# ── 1. ROLLE (geen afhanklikhede) ─────────────────────────
class Rolle(db.Model):
    __tablename__ = 'rolle'
    Rol_ID   = db.Column(db.Integer, primary_key=True)
    ROL_Naam = db.Column(db.String(50), nullable=False, unique=True)

# ── 2. GEBRUIKERS (hang af van Rolle) ─────────────────────
class Gebruikers(db.Model):
    __tablename__ = 'gebruikers'
    Gebruiker_ID     = db.Column(db.Integer, primary_key=True)
    GEB_Naam         = db.Column(db.String(100), nullable=False)
    GEB_Van          = db.Column(db.String(100), nullable=False)
    GEB_ID_Nommer    = db.Column(db.String(13),  nullable=False, unique=True)
    GEB_Epos         = db.Column(db.String(255), nullable=False, unique=True)
    GEB_Wagwoord     = db.Column(db.String(255), nullable=False)
    GEB_Selfoon_Nr   = db.Column(db.String(15))
    GEB_Profiel_Foto = db.Column(db.String(500))
    Rol_ID           = db.Column(db.Integer, db.ForeignKey('rolle.Rol_ID'), nullable=False)
    Is_Aktief        = db.Column(db.Boolean, nullable=False, default=True)
    Geskep_Op        = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    Gewysig_Op       = db.Column(db.DateTime, nullable=False, default=datetime.utcnow,
                                 onupdate=datetime.utcnow)

# ── 3. NFC_TAGS (hang af van Gebruikers) ──────────────────
class NFC_Tags(db.Model):
    __tablename__ = 'nfc_tags'
    NFC_Tags_ID  = db.Column(db.Integer, primary_key=True)
    NFC_UID      = db.Column(db.String(64), nullable=False, unique=True)
    Gebruiker_ID = db.Column(db.Integer, db.ForeignKey('gebruikers.Gebruiker_ID'))
    NFC_Tipe     = db.Column(db.String(32), nullable=False)
    NFC_Is_Aktief = db.Column(db.Boolean, nullable=False, default=True)
    Geskep_Op    = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    Gewysig_Op   = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

# ── 4. WAARSKUWINGS (hang af van Gebruikers) ──────────────
class Waarskuwings(db.Model):
    __tablename__ = 'waarskuwings'
    Waarskuwing_ID  = db.Column(db.Integer, primary_key=True)
    Gebruiker_ID    = db.Column(db.Integer, db.ForeignKey('gebruikers.Gebruiker_ID'),
                                nullable=False)
    WAA_Beskrywing  = db.Column(db.Text, nullable=False)
    WAA_Status      = db.Column(db.String(32), nullable=False, default='OOP')
    WAA_Tydstempel  = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

# ── 5. SUBKLAS TABELLE ─────────────────────────────────────
class Kampus_Opsigter(db.Model):
    __tablename__ = 'kampus_opsigter'
    Gebruiker_ID = db.Column(db.Integer,
                             db.ForeignKey('gebruikers.Gebruiker_ID'),
                             primary_key=True)
    KAMO_Nommer  = db.Column(db.String(20), nullable=False, unique=True)

class Sekuriteit_Wag(db.Model):
    __tablename__ = 'sekuriteit_wag'
    Gebruiker_ID = db.Column(db.Integer,
                             db.ForeignKey('gebruikers.Gebruiker_ID'),
                             primary_key=True)
    SEK_Nommer   = db.Column(db.String(20), nullable=False, unique=True)
from pydantic import BaseModel, EmailStr
from typing import Optional, Generic, TypeVar
from datetime import datetime

T = TypeVar("T")

# --- Standaard Response Schema ---
class APIResponse(BaseModel, Generic[T]):
    sukses: bool
    data: Optional[T] = None
    fout: Optional[str] = None

# --- Rolle Schemas ---
# Model: Rol_ID, ROL_Naam
class RolBase(BaseModel):
    ROL_Naam: str

class RolCreate(RolBase):
    pass

class Rol(RolBase):
    Rol_ID: int

    class Config:
        from_attributes = True

# --- Gebruikers Schemas ---
# Model: Gebruiker_ID, GEB_Naam, GEB_Van, GEB_ID_Nommer, GEB_Epos,
#        GEB_Selfoon_Nr, GEB_Profiel_Foto, Rol_ID, Is_Aktief,
#        Geskep_Op, Gewysig_Op
class UserBase(BaseModel):
    GEB_Naam: str
    GEB_Van: str
    GEB_ID_Nommer: str
    GEB_Epos: EmailStr
    GEB_Selfoon_Nr: Optional[str] = None
    GEB_Profiel_Foto: Optional[str] = None
    Rol_ID: int
    Is_Aktief: bool = True

class UserCreate(UserBase):
    GEB_Wagwoord: str

class UserUpdate(BaseModel):
    GEB_Naam: Optional[str] = None
    GEB_Van: Optional[str] = None
    GEB_Selfoon_Nr: Optional[str] = None
    GEB_Profiel_Foto: Optional[str] = None
    Is_Aktief: Optional[bool] = None

class User(UserBase):
    Gebruiker_ID: int
    Geskep_Op: datetime
    Gewysig_Op: datetime

    class Config:
        from_attributes = True

class UserSecurityRead(BaseModel):
    """Beperkte data vir Sekuriteitswagte."""
    Gebruiker_ID: int
    GEB_Naam: str
    GEB_Van: str
    GEB_ID_Nommer: str
    GEB_Profiel_Foto: Optional[str] = None
    Is_Aktief: bool

    class Config:
        from_attributes = True

# --- GEBRUIKERS_ROLLE SCHEMAS ---
# Model: Gebruiker_ID (PK, FK), Rol_ID (PK, FK)

class GebruikersRolBase(BaseModel):
    Gebruiker_ID: int
    Rol_ID: int

class GebruikersRolCreate(GebruikersRolBase):
    pass

class GebruikersRol(GebruikersRolBase):
    class Config:
        from_attributes = True

# --- STUDENT SCHEMAS ---
# Model: Gebruiker_ID (PK, FK → Gebruikers), STU_Nommer

class StudentBase(BaseModel):
    Gebruiker_ID: int
    STU_Nommer: str

class StudentCreate(StudentBase):
    pass

class StudentUpdate(BaseModel):
    STU_Nommer: Optional[str] = None

class Student(StudentBase):
    class Config:
        from_attributes = True

class StudentRead(BaseModel):
    """Volledige student-profiel saam met basis gebruikersdata."""
    Gebruiker_ID: int
    GEB_Naam: str
    GEB_Van: str
    GEB_Epos: EmailStr
    GEB_Profiel_Foto: Optional[str] = None
    STU_Nommer: str
    Is_Aktief: bool

    class Config:
        from_attributes = True

# --- PERSONEEL SCHEMAS ---
# Model: Gebruiker_ID (PK, FK → Gebruikers), PER_Nommer, PER_Departement

class PersoneelBase(BaseModel):
    Gebruiker_ID: int
    PER_Nommer: str
    PER_Departement: Optional[str] = None

class PersoneelCreate(PersoneelBase):
    pass

class PersoneelUpdate(BaseModel):
    PER_Nommer: Optional[str] = None
    PER_Departement: Optional[str] = None

class Personeel(PersoneelBase):
    class Config:
        from_attributes = True

class PersoneelRead(BaseModel):
    """Volledige personeelprofiel saam met basis gebruikersdata."""
    Gebruiker_ID: int
    GEB_Naam: str
    GEB_Van: str
    GEB_Epos: EmailStr
    GEB_Profiel_Foto: Optional[str] = None
    PER_Nommer: str
    PER_Departement: Optional[str] = None
    Is_Aktief: bool

    class Config:
        from_attributes = True

# --- NFC Tags Schemas ---
# Model: NFC_Tags_ID, NFC_UID, Lokasie_ID, NFC_Tipe, NFC_Is_Aktief
class NFCTagBase(BaseModel):
    NFC_UID: str
    Lokasie_ID: Optional[int] = None   # verwys na lokasie.Lokasie_ID
    NFC_Tipe: str
    NFC_Is_Aktief: bool = True

class NFCTagCreate(NFCTagBase):
    pass

class NFCTag(NFCTagBase):
    NFC_Tags_ID: int

    class Config:
        from_attributes = True

# --- Kampus Schemas ---
# Model: Kampus_ID, KAM_Naam, KAM_Adres
class KampusBase(BaseModel):
    KAM_Naam: str
    KAM_Adres: Optional[str] = None

class KampusCreate(KampusBase):
    pass

class Kampus(KampusBase):
    Kampus_ID: int

    class Config:
        from_attributes = True

# --- Lokasie Schemas ---
# Model: Lokasie_ID, LOK_Naam, LOK_Tipe, Kampus_ID
class LokasieBase(BaseModel):
    LOK_Naam: str
    LOK_Tipe: str
    Kampus_ID: int

class LokasieCreate(LokasieBase):
    pass

class LokasieUpdate(BaseModel):
    LOK_Naam: Optional[str] = None
    LOK_Tipe: Optional[str] = None
    Kampus_ID: Optional[int] = None

class Lokasie(LokasieBase):
    Lokasie_ID: int

    class Config:
        from_attributes = True

# --- Klas Skep (Lokasie + NFC in een stap) ---
class KlasSkep(BaseModel):
    """Data om 'n nuwe klas (lokasie + NFC vir die saal) in een stap te skep."""
    LOK_Naam: str
    LOK_Tipe: str
    Kampus_ID: int
    NFC_UID: str
    NFC_Tipe: str

class KlasSkepResult(BaseModel):
    lokasie: Lokasie
    nfc_tag: NFCTag

    class Config:
        from_attributes = True

# --- TOEGANGS_LOGS SCHEMAS ---
# Model: Log_ID, NFC_Tags_ID, Gebruiker_ID, Lokasie_ID, LOG_Tydstempel, LOG_Status

class ToegangsLogBase(BaseModel):
    NFC_Tags_ID: int            # FK → NFC_Tags.NFC_Tags_ID
    Gebruiker_ID: int           # FK → Gebruikers.Gebruiker_ID
    Lokasie_ID: int             # FK → Lokasies.Lokasie_ID
    LOG_Status: str = "TOEGELAAT"   # "TOEGELAAT" | "GEWEIER" | "ONBEKEND"

class ToegangsLogCreate(ToegangsLogBase):
    pass

class ToegangsLog(ToegangsLogBase):
    Log_ID: int
    LOG_Tydstempel: datetime

    class Config:
        from_attributes = True

class ToegangsLogRead(BaseModel):
    """Uitgebreide log-lees met gebruiker- en lokasiebesonderhede."""
    Log_ID: int
    LOG_Tydstempel: datetime
    LOG_Status: str
    NFC_UID: str
    GEB_Naam: str
    GEB_Van: str
    LOK_Naam: str
    LOK_Tipe: str

    class Config:
        from_attributes = True

class HandmatigeToegangSoek(BaseModel):
    """
    Versoek vir handmatige toegangsvalidering (F22).
    Die sekuriteitswag soek 'n gebruiker op naam of ID-nommer
    sonder NFC-tag — bv. by die hoofhek.
    """
    soek_term: str              # Naam, Van, of GEB_ID_Nommer
    Lokasie_ID: int             # Hek / punt waar toegang gevra word

# --- Waarskuwings Schemas ---
# Model: Waarskuwing_ID, Gebruiker_ID, WAA_Beskrywing, WAA_Status, WAA_Tydstempel
class WaarskuwingBase(BaseModel):
    Gebruiker_ID: int
    WAA_Beskrywing: str
    WAA_Status: str = "OOP"

class WaarskuwingCreate(WaarskuwingBase):
    pass

class WaarskuwingUpdate(BaseModel):
    WAA_Beskrywing: Optional[str] = None
    WAA_Status: Optional[str] = None

class Waarskuwing(WaarskuwingBase):
    Waarskuwing_ID: int
    WAA_Tydstempel: datetime

    class Config:
        from_attributes = True

# --- Kampus Opsigter Schemas ---
# Model: Gebruiker_ID (PK, FK), KAMO_Nommer
class KampusOpsigterBase(BaseModel):
    Gebruiker_ID: int
    KAMO_Nommer: str

class KampusOpsigterCreate(KampusOpsigterBase):
    pass

class KampusOpsigter(KampusOpsigterBase):
    class Config:
        from_attributes = True

# --- Sekuriteit Wag Schemas ---
# Model: Gebruiker_ID (PK, FK), SEK_Nommer
class SekuriteitWagBase(BaseModel):
    Gebruiker_ID: int
    SEK_Nommer: str

class SekuriteitWagCreate(SekuriteitWagBase):
    pass

class SekuriteitWag(SekuriteitWagBase):
    class Config:
        from_attributes = True

# --- AUTH SCHEMAS ---
# Hierdie schemas word gebruik vir die login-eindpunt en token-respons.
class LoginVersoek(BaseModel):
    """Gebruiker stuur e-pos en wagwoord om 'n JWT-token te ontvang."""
    GEB_Epos: EmailStr
    GEB_Wagwoord: str
class TokenRespns(BaseModel):
    """JWT-token wat teruggestuur word na suksesvolle aanmelding."""
    toegangs_token: str
    token_tipe: str = "bearer"
    gebruiker_id: int
    rol: str                    # bv. "STUDENT" | "PERSONEEL" | "WAG" | "ADMIN"

# --- Handmatige Toegangsvalidering Schemas ---
class ToegangHandmatigRequest(BaseModel):
    soek_term: str

class ToegangHandmatigResult(BaseModel):
    Gebruiker_ID: int
    GEB_Naam: str
    GEB_Van: str
    GEB_ID_Nommer: str
    GEB_Profiel_Foto: Optional[str] = None
    Rol_Naam: str
    Is_Aktief: bool
    Toegang_Verleen: bool
    Boodskap: str

    class Config:
        from_attributes = True

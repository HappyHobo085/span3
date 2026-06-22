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
class RolBase(BaseModel):
    ROL_Naam: str

class RolCreate(RolBase):
    pass

class Rol(RolBase):
    Rol_ID: int

    class Config:
        from_attributes = True


# --- Gebruikers Schemas ---
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
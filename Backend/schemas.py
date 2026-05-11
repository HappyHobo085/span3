from pydantic import BaseModel, EmailStr
from typing import Optional, Generic, TypeVar, Any
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
    """
    F21: Beperkte data vir Sekuriteitswagte.
    """
    Gebruiker_ID: int
    GEB_Naam: str
    GEB_Van: str
    GEB_ID_Nommer: str
    GEB_Profiel_Foto: Optional[str] = None
    Is_Aktief: bool
    
    class Config:
        from_attributes = True

# --- NFC Tags Schemas ---
class NFCTagBase(BaseModel):
    NFC_UID: str
    Gebruiker_ID: Optional[int] = None
    Lokasie_ID: Optional[int] = None
    NFC_Tipe: str
    NFC_Is_Aktief: bool = True

class NFCTagCreate(NFCTagBase):
    pass

class NFCTag(NFCTagBase):
    NFC_Tags_ID: int
    Geskep_Op: datetime
    Gewysig_Op: datetime

    class Config:
        from_attributes = True

# --- Lokasies Schemas ---
class LokasieBase(BaseModel):
    naam: str
    beskrywing: Optional[str] = None
    kampus_id: Optional[int] = None

class LokasieCreate(LokasieBase):
    pass

class Lokasie(LokasieBase):
    id: int

    class Config:
        from_attributes = True

# --- Kampus Schemas ---
class KampusBase(BaseModel):
    KAM_Naam: str
    KAM_Adres: Optional[str] = None

class KampusCreate(KampusBase):
    pass

class Kampus(KampusBase):
    Kampus_ID: int

    class Config:
        from_attributes = True

# --- Waarskuwings Schemas ---
class WaarskuwingBase(BaseModel):
    Gebruiker_ID: int
    Lokasie_ID: Optional[int] = None
    WAA_Beskrywing: str
    WAA_Status: str = "OOP"

class WaarskuwingCreate(WaarskuwingBase):
    pass

class Waarskuwing(WaarskuwingBase):
    Waarskuwing_ID: int
    WAA_Tydstempel: datetime

    class Config:
        from_attributes = True

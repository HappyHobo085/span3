from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator
from typing import Optional, Generic, TypeVar, List
from datetime import datetime
import re

T = TypeVar("T")


def _valideer_wagwoord(w: str) -> str:
    """Verifieer wagwoord kompleksiteit — minstens 8 karakters, 1 syfer, 1 spesiaalteken."""
    if len(w) < 8:
        raise ValueError("Wagwoord moet ten minste 8 karakters lank wees")
    if not re.search(r"\d", w):
        raise ValueError("Wagwoord moet ten minste 1 syfer bevat")
    if not re.search(r"[^a-zA-Z0-9]", w):
        raise ValueError("Wagwoord moet ten minste 1 spesiaalteken bevat")
    return w

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
    # Die admin-blad stuur Rol_IDs (multi-rol) sonder Rol_ID, en die roete
    # genereer self 'n GEB_ID_Nommer as geen verskaf word nie — albei geërfde
    # velde moet dus hier opsioneel wees. Die roete vereis steeds ten minste
    # een rol (Rol_IDs óf Rol_ID).
    Rol_ID: Optional[int] = None
    GEB_ID_Nommer: Optional[str] = None
    Rol_IDs: Optional[List[int]] = None
    GEB_Wagwoord: str = Field(..., min_length=8)
    STU_Nommer: Optional[str] = None
    STU_Is_Koshuis: bool = False
    Koshuis_ID: Optional[int] = None
    PER_Nommer: Optional[str] = None
    PER_Departement: Optional[str] = None
    KAMO_Nommer: Optional[str] = None
    Kampus_ID: Optional[int] = None
    SEK_Nommer: Optional[str] = None
    NFC_UID: Optional[str] = None
    NFC_Tipe: str = "Gebruiker"
    NFC_Is_Aktief: bool = True

    @field_validator("GEB_Wagwoord")
    @classmethod
    def val_wagwoord(cls, v: str) -> str:
        return _valideer_wagwoord(v)

class UserUpdate(BaseModel):
    Rol_IDs: Optional[List[int]] = None
    GEB_Naam: Optional[str] = None
    GEB_Van: Optional[str] = None
    GEB_ID_Nommer: Optional[str] = None
    GEB_Epos: Optional[EmailStr] = None
    GEB_Wagwoord: Optional[str] = None
    GEB_Selfoon_Nr: Optional[str] = None
    GEB_Profiel_Foto: Optional[str] = None
    Rol_ID: Optional[int] = None
    Is_Aktief: Optional[bool] = None
    STU_Nommer: Optional[str] = None
    STU_Is_Koshuis: Optional[bool] = None
    Koshuis_ID: Optional[int] = None
    PER_Nommer: Optional[str] = None
    PER_Departement: Optional[str] = None
    KAMO_Nommer: Optional[str] = None
    Kampus_ID: Optional[int] = None
    SEK_Nommer: Optional[str] = None
    NFC_UID: Optional[str] = None
    NFC_Tipe: Optional[str] = None
    NFC_Is_Aktief: Optional[bool] = None

    @field_validator("GEB_Wagwoord")
    @classmethod
    def val_wagwoord(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _valideer_wagwoord(v)
        return v


# --- GEBRUIKER STATUS UPDATE ---
# Word deur routers/gebruikers.py gebruik.
# Pydantic v2: populate_by_name laat beide "is_aktief" en "Is_Aktief" toe.
class GebruikerStatusUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    is_aktief: bool = Field(alias="Is_Aktief")

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
    STU_Is_Koshuis: bool = False
    Koshuis_ID: Optional[int] = None

class StudentCreate(StudentBase):
    pass

class StudentUpdate(BaseModel):
    STU_Nommer: Optional[str] = None
    STU_Is_Koshuis: Optional[bool] = None
    Koshuis_ID: Optional[int] = None

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
    STU_Is_Koshuis: bool = False
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
    Gebruiker_ID: Optional[int] = None
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

class KampusUpdate(BaseModel):
    KAM_Naam: Optional[str] = None
    KAM_Adres: Optional[str] = None

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

class LokasieNFCTagUpdate(BaseModel):
    """Body vir PUT /lokasies/{id}/nfc-tag: die nuwe fisiese tag-UID."""
    NFC_UID: str

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

class ModuleBase(BaseModel):
    MOD_Kode: str
    MOD_Naam: Optional[str] = None

class ModuleCreate(ModuleBase):
    pass

class Module(ModuleBase):
    Module_ID: int

    class Config:
        from_attributes = True

class GroepBase(BaseModel):
    GRO_Naam: str

class GroepCreate(GroepBase):
    pass

class Groep(GroepBase):
    Groep_ID: int

    class Config:
        from_attributes = True

class KlasBase(BaseModel):
    Module_ID: int
    KLA_Lokaal: str
    KLA_Dag: str
    KLA_Begin_Tyd: str
    KLA_Eind_Tyd: str
    Lokasie_ID: Optional[int] = None

class KlasCreate(KlasBase):
    pass

class Klas(KlasBase):
    Klas_ID: int

    class Config:
        from_attributes = True

class KlasLokasieAssign(BaseModel):
    Lokasie_ID: int = Field(..., gt=0)

class RoosterLokaalKoppelingUpdate(BaseModel):
    KLA_Lokaal: str = Field(..., min_length=1, max_length=100)
    Lokasie_ID: Optional[int] = Field(default=None, gt=0)


class KlasGroepAssign(BaseModel):
    Groep_ID: int

class StudentGroepAssign(BaseModel):
    Groep_ID: int

class StudentModuleAssign(BaseModel):
    Module_ID: int

class StudentKlasAssign(BaseModel):
    Klas_ID: int

class PersoneelModuleAssign(BaseModel):
    Module_ID: int

class PersoneelKlasAssign(BaseModel):
    Klas_ID: int

class InstellingBase(BaseModel):
    Sleutel: str
    Waarde: str
    Beskrywing: Optional[str] = None

class InstellingCreate(InstellingBase):
    pass

class InstellingUpdate(BaseModel):
    Waarde: str
    Beskrywing: Optional[str] = None

class InstellingRead(InstellingBase):
    Instelling_ID: int

    class Config:
        from_attributes = True

class KlasImportResult(BaseModel):
    klasse_geskep: int = 0
    modules_geskep: int = 0
    groepe_geskep: int = 0
    foute: List[str] = []

    class Config:
        from_attributes = True

class StudentToewysingImportResult(BaseModel):
    studente_verwerk: int = 0
    groep_koppelings: int = 0
    module_koppelings: int = 0
    groepe_geskep: int = 0
    foute: List[str] = []

    class Config:
        from_attributes = True

# --- TOEGANGS_LOGS SCHEMAS ---
# Model: Log_ID, NFC_Tags_ID, Gebruiker_ID, Lokasie_ID, LOG_Tydstempel, LOG_Status

class ToegangsLogBase(BaseModel):
    Gebruiker_ID: int           # FK → Gebruikers.Gebruiker_ID
    Lokasie_ID: int             # FK → Lokasies.Lokasie_ID
    NFC_Tags_ID: Optional[int] = None
    TOE_Rigting:         str        # "IN" | "UIT"
    TOE_Metode:          str        # "NFC" | "HANDMATIG" | "QR"
    TOE_Auto_Uitgecheck: bool = False

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
    TOE_Tydstempel:      datetime
    TOE_Rigting:         str
    TOE_Metode:          str
    TOE_Auto_Uitgecheck: bool
    GEB_Naam:            str
    GEB_Van:             str
    LOK_Naam:            str
    LOK_Tipe:            str

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

# --- BESOEKERS_GROEP SCHEMAS ---
# Model: Besoekers_Groep_ID, BESG_Selfoon_Nr, BESG_Kode

class BesoekersGroepBase(BaseModel):
    BESG_Selfoon_Nr: str
    BESG_Kode: str

class BesoekersGroepCreate(BesoekersGroepBase):
    pass

class BesoekersGroepUpdate(BaseModel):
    BESG_Selfoon_Nr: Optional[str] = None
    BESG_Kode: Optional[str] = None

class BesoekersGroep(BesoekersGroepBase):
    Besoekers_Groep_ID: int

    class Config:
        from_attributes = True

# --- BESOEKER SCHEMAS ---
# Model: Besoeker_ID, BES_Naam, Besoekers_Groep_ID (FK)

class BesoekerBase(BaseModel):
    BES_Naam: str
    Besoekers_Groep_ID: int     # FK → Besoekers_Groep.Besoekers_Groep_ID

class BesoekerCreate(BesoekerBase):
    pass

class BesoekerUpdate(BaseModel):
    BES_Naam: Optional[str] = None
    Besoekers_Groep_ID: Optional[int] = None

class Besoeker(BesoekerBase):
    Besoeker_ID: int

    class Config:
        from_attributes = True

class BesoekersGroepRead(BaseModel):
    """Groep met sy volledige lys besoekers — vir die wag se besigtigingskerm."""
    Besoekers_Groep_ID: int
    BESG_Selfoon_Nr: str
    BESG_Kode: str
    besoekers: List[Besoeker] = []

    class Config:
        from_attributes = True

# --- ONVERWAGTE_BESOEKER SCHEMAS ---
# Model: Onverwagte_Besoeker_ID, ONV_Bestuurslisensie, ONV_Beskrywing,
#        ONV_Kode, Besoekers_Groep_ID (FK)

class OnverwagteBesoekBase(BaseModel):
    ONV_Bestuurslisensie: Optional[str] = None
    ONV_Beskrywing: Optional[str] = None
    ONV_Kode: Optional[str] = None
    Besoekers_Groep_ID: int             # FK → Besoekers_Groep.Besoekers_Groep_ID

class OnverwagteBesoekCreate(OnverwagteBesoekBase):
    pass

class OnverwagteBesoekUpdate(BaseModel):
    ONV_Bestuurslisensie: Optional[str] = None
    ONV_Beskrywing: Optional[str] = None
    ONV_Kode: Optional[str] = None

class OnverwagteBesoeker(OnverwagteBesoekBase):
    Onverwagte_Besoeker_ID: int

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
    Kampus_ID: Optional[int] = None

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


class HekScanRequest(BaseModel):
    nommer: str
    rigting: str = "IN"


# --- Kampus Status/Skandering Status Schemas ---
class KampusGebruikerStatus(BaseModel):
    Gebruiker_ID: int
    GEB_Naam: str
    GEB_Van: str
    GEB_Epos: str
    Rol_Naam: str
    Tydstempel: datetime
    Rigting: str  # "IN" | "UIT"
    Metode: str

    class Config:
        from_attributes = True

class KampusDetailStatus(BaseModel):
    Kampus_ID: int
    KAM_Naam: str
    scanned_in_count: int
    scanned_out_count: int
    scanned_in: List[KampusGebruikerStatus]
    scanned_out: List[KampusGebruikerStatus]

    class Config:
        from_attributes = True

class KampusSummaryStatus(BaseModel):
    Kampus_ID: int
    KAM_Naam: str
    KAM_Adres: Optional[str] = None
    scanned_in_count: int
    scanned_out_count: int

    class Config:
        from_attributes = True


# --- Koshuis Schemas ---
class KoshuisBase(BaseModel):
    KOS_Naam: str
    KOS_Adres: Optional[str] = None
    KOS_Kapasiteit: int
    Kampus_ID: Optional[int] = None

class KoshuisCreate(KoshuisBase):
    pass

class KoshuisUpdate(BaseModel):
    KOS_Naam: Optional[str] = None
    KOS_Adres: Optional[str] = None
    KOS_Kapasiteit: Optional[int] = None
    Kampus_ID: Optional[int] = None

class Koshuis(KoshuisBase):
    Koshuis_ID: int

    class Config:
        from_attributes = True

class KoshuisDetailStatus(BaseModel):
    Koshuis_ID: int
    KOS_Naam: str
    KOS_Kapasiteit: int
    inwoner_count: int
    scanned_in_count: int
    scanned_out_count: int
    scanned_in: List[KampusGebruikerStatus]
    scanned_out: List[KampusGebruikerStatus]

    class Config:
        from_attributes = True


# --- Funksie Schemas ---
class FunksieBase(BaseModel):
    Kampus_ID: int
    FUN_Naam: str
    FUN_Begin_Tyd: datetime
    FUN_Eind_Tyd: datetime
    FUN_Beskrywing: Optional[str] = None
    FUN_Is_Aktief: bool = True

class FunksieCreate(FunksieBase):
    pass

class Funksie(FunksieBase):
    Funksie_ID: int

    class Config:
        from_attributes = True


# --- Funksie_Besoekers Schemas ---
class FunksieBesoekerBase(BaseModel):
    Besoekers_Groep_ID: int
    Funksie_ID: int
    FUNB_Status: str

class FunksieBesoekerCreate(FunksieBesoekerBase):
    pass

class FunksieBesoeker(FunksieBesoekerBase):
    class Config:
        from_attributes = True


# --- Inline Request Models (extracted from main.py) ---

class StudentKlasScanRequest(BaseModel):
    nfc_uid: str
    rigting: str = "IN"

class WagteStudentScanRequest(BaseModel):
    student_nom_or_id: str
    lokasie_id: int
    rigting: str   # IN / UIT
    metode: str    # NFC / QR

class WagteProfileScanRequest(BaseModel):
    scan_kode: str
    # Nuwe Step 13-konteks. Opsioneel gehou sodat ou kliënte nie onmiddellik breek nie.
    lokasie_id: Optional[int] = None
    koshuis_id: Optional[int] = None

class WagteProfileVerifyRequest(BaseModel):
    gebruiker_id: int
    # kampus_id bly opsioneel vir backwards compatibility.
    kampus_id: Optional[int] = None
    lokasie_id: Optional[int] = None
    koshuis_id: Optional[int] = None
    rigting: str
    metode: str

class WagteProfileDeclineRequest(BaseModel):
    gebruiker_id: int
    kampus_id: Optional[int] = None
    lokasie_id: Optional[int] = None
    koshuis_id: Optional[int] = None
    metode: str = "QR"

# --- SAAMRY SCHEMAS ---

class SaamryVriendVersoekCreate(BaseModel):
    ontvanger_id: int


class SaamryGroepCreate(BaseModel):
    # Nuwe permanente groep: slegs naam + kapasiteit is nodig.
    naam: str
    sitplekke: int = Field(default=4, ge=1, le=8)
    # Legacy velde bly opsioneel sodat ouer kliënte nie onmiddellik breek nie.
    vertrekpunt: Optional[str] = None
    bestemming: Optional[str] = None
    vertrek_tyd: Optional[datetime] = None


class SaamryGroepNooiCreate(BaseModel):
    gebruiker_id: int


class SaamryBestuurderOordragRequest(BaseModel):
    nuwe_bestuurder_id: int


class SaamryPickupProfielUpdate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    beskrywing: str = Field(..., min_length=3, max_length=200)


class SaamryEventCreate(BaseModel):
    groep_id: int
    gebruiker_ids: List[int]
    # Driver kan 'n nuwe adres stuur, of die backend kan sy gewone pickup-profiel gebruik.
    driver_latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    driver_longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    driver_pickup_beskrywing: Optional[str] = Field(default=None, max_length=200)
    stoor_driver_as_verstek: bool = False


class SaamryPickupUpdate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    beskrywing: Optional[str] = Field(default=None, max_length=200)
    stoor_as_verstek: bool = False


class SaamryBoodskapCreate(BaseModel):
    boodskap: str = Field(..., min_length=1, max_length=1000)


class SaamryHekPreviewRequest(BaseModel):
    bestuurder_id: int
    kampus_id: int
    rigting: str


class SaamryHekBevestigRequest(BaseModel):
    groep_id: int
    kampus_id: int
    rigting: str
    metode: str
    gebruiker_ids: List[int]
    event_id: Optional[int] = None


class SaamryProfielUpdate(BaseModel):
    rol_tipe: Optional[str] = None
    voorstad: Optional[str] = None
    sone_kode: Optional[str] = None
    kampus_id: Optional[int] = None
    geslag: Optional[str] = None
    geslag_voorkeur: Optional[str] = None
    maks_ompad_minute: Optional[int] = None
    is_aktief_saamryer: Optional[bool] = None


class SaamryProfielOut(BaseModel):
    gebruiker_id: int
    rol_tipe: str
    voorstad: Optional[str] = None
    sone_kode: Optional[str] = None
    kampus_id: Optional[int] = None
    geslag: Optional[str] = None
    geslag_voorkeur: str
    maks_ompad_minute: int
    is_aktief_saamryer: bool

    class Config:
        from_attributes = True


# --- BESOEKER OTP SCHEMAS ---

class BesoekerUitnodigingCreate(BaseModel):
    naam: str
    van: str
    selfoon: str
    rede: Optional[str] = None


class BesoekerOtpVerifyRequest(BaseModel):
    otp: str


class BesoekerBesluitRequest(BaseModel):
    kampus_id: int

# --- EVENTS / FUNKSIE RSVP SCHEMAS ---

class EventCreateRequest(BaseModel):
    naam: str
    kampus_id: int
    lokasie_id: Optional[int] = None
    begin_tyd: datetime
    eind_tyd: datetime
    kapasiteit: int
    beskrywing: Optional[str] = None


class EventUpdateRequest(BaseModel):
    naam: Optional[str] = None
    kampus_id: Optional[int] = None
    lokasie_id: Optional[int] = None
    begin_tyd: Optional[datetime] = None
    eind_tyd: Optional[datetime] = None
    kapasiteit: Optional[int] = None
    beskrywing: Optional[str] = None


class EventRsvpRequest(BaseModel):
    status: str = "GAAN"


class PublicEventRsvpRequest(BaseModel):
    naam: str
    van: str
    selfoon: str
    epos: Optional[str] = None


# --- WAGTE: EKSTERNE EVENT-GASTE ---

class WagteEventGuestScanRequest(BaseModel):
    scan_kode: str
    kampus_id: int


class WagteEventGuestConfirmRequest(BaseModel):
    publiek_rsvp_id: int
    kampus_id: int
    rigting: str
    metode: str = "QR"


class WagteEventGuestDeclineRequest(BaseModel):
    publiek_rsvp_id: int
    kampus_id: int
    metode: str = "QR"

# --- NOODGEVAL SCHEMAS ---
class NoodgevalMqttToetsRequest(BaseModel):
    kampus_id: int = Field(..., gt=0)
    titel: str = Field(default="MQTT TOETS", min_length=1, max_length=150)
    boodskap: str = Field(default="MOON MQTT toets", min_length=1, max_length=1000)


class NoodgevalCreateRequest(BaseModel):
    kampus_id: int = Field(..., gt=0)
    tipe: str = Field(default="NOODGEVAL", min_length=1, max_length=50)
    titel: str = Field(..., min_length=1, max_length=150)
    boodskap: str = Field(..., min_length=1, max_length=2000)


class NoodgevalRead(BaseModel):
    Noodgeval_ID: int
    Kampus_ID: int
    Geskep_Deur_ID: int
    Gesluit_Deur_ID: Optional[int] = None
    NOO_Tipe: str
    NOO_Titel: str
    NOO_Boodskap: str
    NOO_Status: str
    NOO_Boodskap_ID: str
    NOO_Begin_Op: datetime
    NOO_Mqtt_Gestuur_Op: Optional[datetime] = None
    NOO_Gesluit_Op: Optional[datetime] = None

    class Config:
        from_attributes = True


class NoodgevalKennisnameRead(BaseModel):
    Kennisname_ID: int
    Noodgeval_ID: int
    Gebruiker_ID: int
    NOK_Status: str
    NOK_Ontvang_Op: Optional[datetime] = None
    NOK_Kennis_Geneem_Op: Optional[datetime] = None

    class Config:
        from_attributes = True

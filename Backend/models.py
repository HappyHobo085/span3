from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, CheckConstraint, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

# --- selectinload defaults for frequently-accessed relationships ---
# These prevent N+1 queries on the most common traversal patterns.
# Heavy collections (nfc_tags, toegangs_logs, waarskuwings) stay lazy.

class Rolle(Base):
    __tablename__ = 'rolle'
    Rol_ID   = Column(Integer, primary_key=True, index=True)
    ROL_Naam = Column(String(50), nullable=False, unique=True)

    gebruikers_rolle = relationship("GebruikersRolle", back_populates="rol", lazy="selectin")

class Gebruikers(Base):
    __tablename__ = 'gebruikers'
    Gebruiker_ID     = Column(Integer, primary_key=True, index=True)
    GEB_Naam         = Column(String(100), nullable=False)
    GEB_Van          = Column(String(100), nullable=False)
    GEB_ID_Nommer    = Column(String(13),  nullable=False, unique=True)
    GEB_Epos         = Column(String(255), nullable=False, unique=True)
    GEB_Wagwoord     = Column(String(255), nullable=False)
    GEB_Selfoon_Nr   = Column(String(15))
    GEB_Profiel_Foto = Column(String(500))
    Rol_ID           = Column(Integer, ForeignKey('rolle.Rol_ID'), nullable=False)
    Is_Aktief        = Column(Boolean, nullable=False, default=True)
    Geskep_Op        = Column(DateTime, default=datetime.utcnow)
    Gewysig_Op       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rol              = relationship("Rolle", lazy="selectin")
    gebruikers_rolle = relationship("GebruikersRolle", back_populates="gebruiker", lazy="selectin")
    student          = relationship("Student",         back_populates="gebruiker", uselist=False, lazy="selectin")
    personeel        = relationship("Personeel",       back_populates="gebruiker", uselist=False, lazy="selectin")
    kampus_opsigter  = relationship("Kampus_Opsigter", back_populates="gebruiker", uselist=False, lazy="selectin")
    sekuriteit_wag   = relationship("Sekuriteit_Wag",  back_populates="gebruiker", uselist=False, lazy="selectin")
    nfc_tags         = relationship("NFC_Tags", back_populates="gebruiker")
    toegangs_logs    = relationship("ToegangsLogs",    back_populates="gebruiker")
    waarskuwings     = relationship("Waarskuwings",    back_populates="gebruiker")
    saamry_profiel   = relationship("SaamryProfiel",   back_populates="gebruiker", uselist=False, lazy="selectin")

class GebruikersRolle(Base):
    __tablename__ = 'gebruikers_rolle'

    Gebruiker_ID = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), primary_key=True)
    Rol_ID       = Column(Integer, ForeignKey('rolle.Rol_ID'),            primary_key=True)

    gebruiker = relationship("Gebruikers", back_populates="gebruikers_rolle")
    rol       = relationship("Rolle",      back_populates="gebruikers_rolle", lazy="selectin")

class Instelling(Base):
    __tablename__ = 'instelling'

    Instelling_ID = Column(Integer, primary_key=True, index=True)
    Sleutel = Column(String(200), nullable=False, unique=True)
    Waarde = Column(String(500), nullable=False, default='')
    Beskrywing = Column(Text, nullable=True)

class Module(Base):
    __tablename__ = 'module'

    Module_ID = Column(Integer, primary_key=True, index=True)
    MOD_Kode = Column(String(50), nullable=False, unique=True)
    MOD_Naam = Column(String(200), nullable=True)

    klasse = relationship("Klas", back_populates="module")

class Groep(Base):
    __tablename__ = 'groep'

    Groep_ID = Column(Integer, primary_key=True, index=True)
    GRO_Naam = Column(String(100), nullable=False, unique=True)

class Klas(Base):
    __tablename__ = 'klas'

    Klas_ID = Column(Integer, primary_key=True, index=True)
    Module_ID = Column(Integer, ForeignKey('module.Module_ID'), nullable=False)
    # Fisiese klaskamer wat aan hierdie roosterperiode gekoppel is.
    # Nullable vir bestaande/imported klasse totdat 'n lokaal gematch of handmatig gekoppel is.
    Lokasie_ID = Column(Integer, ForeignKey('lokasie.Lokasie_ID', ondelete='SET NULL'), nullable=True, index=True)
    KLA_Lokaal = Column(String(100), nullable=False)
    KLA_Dag = Column(String(50), nullable=False)
    KLA_Begin_Tyd = Column(String(20), nullable=False)
    KLA_Eind_Tyd = Column(String(20), nullable=False)

    module = relationship("Module", back_populates="klasse")
    lokasie = relationship("Lokasie", lazy="selectin")

class Rooster_Lokaal_Koppeling(Base):
    __tablename__ = 'rooster_lokaal_koppeling'

    Koppeling_ID = Column(Integer, primary_key=True, index=True)
    KLA_Lokaal = Column(String(100), nullable=False, unique=True, index=True)
    Lokasie_ID = Column(
        Integer,
        ForeignKey('lokasie.Lokasie_ID', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    Geskep_Op = Column(DateTime, default=datetime.utcnow, nullable=False)
    Gewysig_Op = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    lokasie = relationship('Lokasie', lazy='selectin')


class Student_Groep(Base):
    __tablename__ = 'student_groep'

    Gebruiker_ID = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), primary_key=True)
    Groep_ID = Column(Integer, ForeignKey('groep.Groep_ID'), primary_key=True)

class Student_Module(Base):
    __tablename__ = 'student_module'

    Gebruiker_ID = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), primary_key=True)
    Module_ID = Column(Integer, ForeignKey('module.Module_ID'), primary_key=True)

class Student_Klas(Base):
    __tablename__ = 'student_klas'

    Gebruiker_ID = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), primary_key=True)
    Klas_ID = Column(Integer, ForeignKey('klas.Klas_ID'), primary_key=True)

class Personeel_Module(Base):
    __tablename__ = 'personeel_module'

    Gebruiker_ID = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), primary_key=True)
    Module_ID = Column(Integer, ForeignKey('module.Module_ID'), primary_key=True)

class Personeel_Klas(Base):
    __tablename__ = 'personeel_klas'

    Gebruiker_ID = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), primary_key=True)
    Klas_ID = Column(Integer, ForeignKey('klas.Klas_ID'), primary_key=True)

class Klas_Groep(Base):
    __tablename__ = 'klas_groep'

    Klas_ID = Column(Integer, ForeignKey('klas.Klas_ID'), primary_key=True)
    Groep_ID = Column(Integer, ForeignKey('groep.Groep_ID'), primary_key=True)

class Student(Base):
    __tablename__ = 'student'

    Gebruiker_ID = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), primary_key=True)
    STU_Nommer   = Column(String(20), nullable=False, unique=True)
    STU_Is_Koshuis = Column(Boolean, nullable=False, default=False)
    Koshuis_ID   = Column(Integer, ForeignKey('koshuis.Koshuis_ID'), nullable=True)

    gebruiker = relationship("Gebruikers", back_populates="student")
    koshuis   = relationship("Koshuis", back_populates="studente")

class Personeel(Base):
    __tablename__ = 'personeel'

    Gebruiker_ID    = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), primary_key=True)
    PER_Nommer      = Column(String(20),  nullable=False, unique=True)
    PER_Departement = Column(String(100))

    gebruiker = relationship("Gebruikers", back_populates="personeel")
class NFC_Tags(Base):
    __tablename__ = 'nfc_tags'
    NFC_Tags_ID   = Column(Integer, primary_key=True, index=True)
    NFC_UID       = Column(String(64), nullable=False, unique=True)
    Gebruiker_ID  = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), nullable=True)
    Lokasie_ID    = Column(Integer, ForeignKey('lokasie.Lokasie_ID'), nullable=True)
    NFC_Tipe      = Column(String(32), nullable=False)
    NFC_Is_Aktief = Column(Boolean, nullable=False, default=True)
                           
    gebruiker = relationship("Gebruikers", back_populates="nfc_tags", lazy="selectin")
    lokasie   = relationship("Lokasie", back_populates="nfc_tags", lazy="selectin")
    toegangs_logs = relationship("ToegangsLogs", back_populates="nfc_tag")
    
class Kampus(Base):
    __tablename__ = 'kampus'
    Kampus_ID  = Column(Integer, primary_key=True, index=True)
    KAM_Naam   = Column(String(100), nullable=False)
    KAM_Adres  = Column(String(255))

    lokasies  = relationship("Lokasie",  back_populates="kampus", lazy="selectin")
    koshuise  = relationship("Koshuis",  back_populates="kampus", lazy="selectin")
    funksies  = relationship("Funksie",  back_populates="kampus")


class Lokasie(Base):
    __tablename__ = 'lokasie'
    Lokasie_ID = Column(Integer, primary_key=True, index=True)
    LOK_Naam   = Column(String(100), nullable=False)
    LOK_Tipe   = Column(String(50),  nullable=False)
    Kampus_ID  = Column(Integer, ForeignKey('kampus.Kampus_ID'), nullable=False)
    LOK_Kapasiteit = Column(Integer, nullable=True)

    kampus    = relationship("Kampus", back_populates="lokasies", lazy="selectin")
    nfc_tags  = relationship("NFC_Tags", back_populates="lokasie", lazy="selectin")
    toegangs_logs = relationship("ToegangsLogs", back_populates="lokasie")

class ToegangsLogs(Base):
    __tablename__ = 'toegangs_logs'

    Log_ID              = Column(Integer,  primary_key=True, index=True)
    NFC_Tags_ID         = Column(Integer,  ForeignKey('nfc_tags.NFC_Tags_ID'), nullable=True)
    Gebruiker_ID        = Column(Integer,  ForeignKey('gebruikers.Gebruiker_ID'), nullable=False)
    Lokasie_ID          = Column(Integer,  ForeignKey('lokasie.Lokasie_ID'), nullable=False)
    TOE_Tydstempel      = Column(DateTime, default=datetime.utcnow, nullable=False)
    TOE_Rigting         = Column(String(16), nullable=False) # "IN" | "UIT"
    TOE_Metode          = Column(String(32), nullable=False) # "NFC" | "HANDMATIG" | "QR" | "SAAMRY"
    TOE_Auto_Uitgecheck = Column(Boolean, nullable=False, default=False)
    Saamry_Groep_ID     = Column(Integer, ForeignKey('saamry_groep.Groep_ID'), nullable=True)
    Saamry_Bestuurder_Log_ID = Column(Integer, ForeignKey('toegangs_logs.Log_ID'), nullable=True)

    nfc_tag   = relationship("NFC_Tags",    back_populates="toegangs_logs")
    gebruiker = relationship("Gebruikers", back_populates="toegangs_logs", lazy="selectin")
    lokasie   = relationship("Lokasie",    back_populates="toegangs_logs", lazy="selectin")

class Besoekers_Groep(Base):
    __tablename__ = 'besoekers_groep'

    Besoekers_Groep_ID = Column(Integer, primary_key=True, index=True)
    BESG_Selfoon_Nr    = Column(String(15),  nullable=False)
    BESG_Kode          = Column(String(20),  nullable=False, unique=True)
    # BESG_Kode is die unieke identifikasiekode wat aan die groep toegeken word
    # (bv. 'n QR-kode of voorafgegenereerde toegangskode)

    besoekers           = relationship("Besoeker",           back_populates="besoekers_groep")
    onverwagte_besoekers = relationship("Onverwagte_Besoeker", back_populates="besoekers_groep")
    funksie_besoekers    = relationship("Funksie_Besoekers",  back_populates="besoekers_groep")

class Besoeker(Base):
    __tablename__ = 'besoeker'

    Besoeker_ID        = Column(Integer, primary_key=True, index=True)
    BES_Naam           = Column(String(200), nullable=False)
    Besoekers_Groep_ID = Column(Integer, ForeignKey('besoekers_groep.Besoekers_Groep_ID'), nullable=False)

    besoekers_groep = relationship("Besoekers_Groep", back_populates="besoekers")

class Onverwagte_Besoeker(Base):
    __tablename__ = 'onverwagte_besoeker'

    Onverwagte_Besoeker_ID = Column(Integer, primary_key=True, index=True)
    ONV_Bestuurslisensie   = Column(String(20),  nullable=True)
    ONV_Beskrywing         = Column(Text,        nullable=True)
    ONV_Kode               = Column(String(20),  nullable=True)
    Besoekers_Groep_ID     = Column(Integer, ForeignKey('besoekers_groep.Besoekers_Groep_ID'), nullable=False)

    besoekers_groep = relationship("Besoekers_Groep", back_populates="onverwagte_besoekers")

class Waarskuwings(Base):
    __tablename__ = 'waarskuwings'
    Waarskuwing_ID = Column(Integer, primary_key=True, index=True)
    Gebruiker_ID   = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), nullable=False)
    WAA_Beskrywing = Column(Text, nullable=False)
    WAA_Status     = Column(String(32), nullable=False, default='OOP') # "OOP" | "ERKEN" | "GESLUIT"
    WAA_Tydstempel = Column(DateTime, default=datetime.utcnow)

    gebruiker = relationship("Gebruikers", back_populates="waarskuwings")

class Kampus_Opsigter(Base):
    __tablename__ = 'kampus_opsigter'
    Gebruiker_ID = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), primary_key=True)
    KAMO_Nommer  = Column(String(20), nullable=False, unique=True)
    Kampus_ID    = Column(Integer, ForeignKey('kampus.Kampus_ID'), nullable=True)

    gebruiker = relationship("Gebruikers", back_populates="kampus_opsigter")

class Sekuriteit_Wag(Base):
    __tablename__ = 'sekuriteit_wag'
    Gebruiker_ID = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), primary_key=True)
    SEK_Nommer   = Column(String(20), nullable=False, unique=True)

    gebruiker = relationship("Gebruikers", back_populates="sekuriteit_wag")

class Koshuis(Base):
    __tablename__ = 'koshuis'

    Koshuis_ID    = Column(Integer, primary_key=True, index=True)
    KOS_Naam      = Column(String(100), nullable=False)
    KOS_Adres     = Column(String(255))
    KOS_Kapasiteit = Column(Integer, nullable=False)
    Kampus_ID     = Column(Integer, ForeignKey('kampus.Kampus_ID'), nullable=True)

    kampus   = relationship("Kampus", back_populates="koshuise", lazy="selectin")
    studente = relationship("Student", back_populates="koshuis")

class Funksie(Base):
    __tablename__ = 'funksie'

    Funksie_ID      = Column(Integer, primary_key=True, index=True)
    Kampus_ID       = Column(Integer, ForeignKey('kampus.Kampus_ID'), nullable=False)
    Lokasie_ID      = Column(Integer, ForeignKey('lokasie.Lokasie_ID'), nullable=True)
    Geskep_Deur_ID  = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), nullable=True)
    FUN_Naam        = Column(String(100), nullable=False)
    FUN_Begin_Tyd   = Column(DateTime, nullable=False)
    FUN_Eind_Tyd    = Column(DateTime, nullable=False)
    FUN_Beskrywing  = Column(Text)
    FUN_Kapasiteit  = Column(Integer, nullable=False, default=100)
    FUN_Status      = Column(String(20), nullable=False, default='AKTIEF')
    FUN_Is_Aktief   = Column(Boolean, nullable=False, default=True)
    # Opaque token vir die publieke deel-skakel.
    FUN_Deel_Token  = Column(String(80), nullable=True, unique=True)
    Geskep_Op       = Column(DateTime, default=datetime.utcnow, nullable=False)
    Gewysig_Op      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    kampus            = relationship("Kampus", back_populates="funksies", lazy="selectin")
    lokasie           = relationship("Lokasie", foreign_keys=[Lokasie_ID], lazy="selectin")
    geskep_deur       = relationship("Gebruikers", foreign_keys=[Geskep_Deur_ID], lazy="selectin")
    funksie_besoekers = relationship("Funksie_Besoekers", back_populates="funksie")
    rsvps             = relationship(
        "FunksieRSVP",
        back_populates="funksie",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    publieke_rsvps    = relationship(
        "FunksiePubliekRSVP",
        back_populates="funksie",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    publieke_toegange = relationship(
        "FunksiePubliekToegang",
        back_populates="funksie",
    )

    __table_args__ = (
        CheckConstraint('"FUN_Kapasiteit" > 0', name='ck_funksie_kapasiteit'),
        CheckConstraint(
            '"FUN_Status" IN (\'AKTIEF\', \'GEKANSELLEER\')',
            name='ck_funksie_status',
        ),
    )


class FunksieRSVP(Base):
    __tablename__ = 'funksie_rsvp'

    Funksie_ID   = Column(Integer, ForeignKey('funksie.Funksie_ID'), primary_key=True)
    Gebruiker_ID = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), primary_key=True)
    RSVP_Status  = Column(String(20), nullable=False, default='GAAN')
    RSVP_Tyd     = Column(DateTime, default=datetime.utcnow, nullable=False)
    Gewysig_Op   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    funksie   = relationship("Funksie", back_populates="rsvps")
    gebruiker = relationship("Gebruikers", lazy="selectin")

    __table_args__ = (
        CheckConstraint(
            '"RSVP_Status" IN (\'GAAN\', \'KAN_NIE\', \'GEKANSELLEER\')',
            name='ck_funksie_rsvp_status',
        ),
    )

class FunksiePubliekRSVP(Base):
    __tablename__ = 'funksie_publiek_rsvp'

    Publiek_RSVP_ID = Column(Integer, primary_key=True, index=True)
    Funksie_ID       = Column(Integer, ForeignKey('funksie.Funksie_ID'), nullable=False, index=True)
    Naam              = Column(String(100), nullable=False)
    Van               = Column(String(100), nullable=False)
    Selfoon           = Column(String(30), nullable=False)
    Epos              = Column(String(255), nullable=True)
    # Die QR bevat net hierdie opaque token; geen PII word in die QR gesit nie.
    QR_Token          = Column(String(120), nullable=False, unique=True, index=True)
    RSVP_Status       = Column(String(20), nullable=False, default='GAAN')
    RSVP_Tyd          = Column(DateTime, default=datetime.utcnow, nullable=False)
    Gewysig_Op        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    funksie = relationship("Funksie", back_populates="publieke_rsvps")
    toegange = relationship(
        "FunksiePubliekToegang",
        back_populates="publieke_rsvp",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            '"RSVP_Status" IN (\'GAAN\', \'GEKANSELLEER\')',
            name='ck_funksie_publiek_rsvp_status',
        ),
    )


class FunksiePubliekToegang(Base):
    """IN/UIT/GEWEIER heklog vir eksterne Event-gaste."""
    __tablename__ = 'funksie_publiek_toegang'

    Toegang_ID       = Column(Integer, primary_key=True, index=True)
    Publiek_RSVP_ID  = Column(Integer, ForeignKey('funksie_publiek_rsvp.Publiek_RSVP_ID'), nullable=False, index=True)
    Funksie_ID       = Column(Integer, ForeignKey('funksie.Funksie_ID'), nullable=False, index=True)
    Kampus_ID        = Column(Integer, ForeignKey('kampus.Kampus_ID'), nullable=False, index=True)
    Wag_ID            = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), nullable=True)
    Rigting           = Column(String(16), nullable=False)
    Metode            = Column(String(32), nullable=False, default='QR')
    Tydstempel        = Column(DateTime, default=datetime.utcnow, nullable=False)

    publieke_rsvp = relationship("FunksiePubliekRSVP", back_populates="toegange")
    funksie = relationship("Funksie", back_populates="publieke_toegange")
    kampus = relationship("Kampus")
    wag = relationship("Gebruikers", foreign_keys=[Wag_ID])

    __table_args__ = (
        CheckConstraint(
            '"Rigting" IN (\'IN\', \'UIT\', \'GEWEIER\')',
            name='ck_funksie_publiek_toegang_rigting',
        ),
        CheckConstraint(
            '"Metode" IN (\'QR\', \'HANDMATIG\')',
            name='ck_funksie_publiek_toegang_metode',
        ),
    )


class Funksie_Besoekers(Base):
    __tablename__ = 'funksie_besoekers'

    Besoekers_Groep_ID = Column(Integer, ForeignKey('besoekers_groep.Besoekers_Groep_ID'), primary_key=True)
    Funksie_ID         = Column(Integer, ForeignKey('funksie.Funksie_ID'),                 primary_key=True)
    FUNB_Status        = Column(String(32), nullable=False)

    besoekers_groep = relationship("Besoekers_Groep", back_populates="funksie_besoekers")
    funksie         = relationship("Funksie",         back_populates="funksie_besoekers")

# --- SAAMRY MODELS ---

class SaamryVriendskap(Base):
    __tablename__ = 'saamry_vriendskap'

    Vriendskap_ID = Column(Integer, primary_key=True, index=True)
    Versoeker_ID  = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), nullable=False)
    Ontvanger_ID  = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), nullable=False)
    SAA_Status    = Column(String(20), nullable=False, default='HANGEND')
    Geskep_Op     = Column(DateTime, default=datetime.utcnow, nullable=False)
    Gewysig_Op    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    versoeker = relationship('Gebruikers', foreign_keys=[Versoeker_ID])
    ontvanger = relationship('Gebruikers', foreign_keys=[Ontvanger_ID])

    __table_args__ = (
        UniqueConstraint('Versoeker_ID', 'Ontvanger_ID', name='uq_saamry_vriendskap_rigting'),
        CheckConstraint('"Versoeker_ID" <> "Ontvanger_ID"', name='ck_saamry_vriendskap_nie_self'),
        CheckConstraint(
            '"SAA_Status" IN (\'HANGEND\', \'AANVAAR\', \'GEWEIER\')',
            name='ck_saamry_vriendskap_status',
        ),
    )


class SaamryPickupProfiel(Base):
    """Gebruiker se gewone/default Saamry opteladres.

    Hierdie profiel is apart van 'n spesifieke Saamry-rit. 'n Rit kopieer
    die adres as 'n voorstel; die gebruiker moet dit vir die event bevestig.
    """

    __tablename__ = 'saamry_pickup_profiel'

    Gebruiker_ID = Column(
        Integer,
        ForeignKey('gebruikers.Gebruiker_ID', ondelete='CASCADE'),
        primary_key=True,
    )
    Pickup_Latitude = Column(Float, nullable=False)
    Pickup_Longitude = Column(Float, nullable=False)
    Pickup_Beskrywing = Column(String(200), nullable=False)
    Geskep_Op = Column(DateTime, default=datetime.utcnow, nullable=False)
    Gewysig_Op = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    gebruiker = relationship('Gebruikers', foreign_keys=[Gebruiker_ID], lazy='selectin')


class SaamryGroep(Base):
    __tablename__ = 'saamry_groep'

    Groep_ID         = Column(Integer, primary_key=True, index=True)
    Bestuurder_ID    = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), nullable=False)
    SAA_Naam         = Column(String(120), nullable=False)
    SAA_Vertrekpunt  = Column(String(200), nullable=False)
    SAA_Bestemming   = Column(String(200), nullable=False)
    SAA_Vertrek_Tyd  = Column(DateTime, nullable=False)
    SAA_Sitplekke    = Column(Integer, nullable=False, default=1)
    SAA_Status       = Column(String(20), nullable=False, default='AKTIEF')
    Geskep_Op        = Column(DateTime, default=datetime.utcnow, nullable=False)
    Gewysig_Op       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    bestuurder = relationship('Gebruikers', foreign_keys=[Bestuurder_ID], lazy="selectin")
    lede = relationship(
        'SaamryGroepLid',
        back_populates='groep',
        cascade='all, delete-orphan',
    )
    events = relationship(
        'SaamryEvent',
        back_populates='groep',
        cascade='all, delete-orphan',
    )
    boodskappe = relationship(
        'SaamryBoodskap',
        back_populates='groep',
        cascade='all, delete-orphan',
    )

    __table_args__ = (
        CheckConstraint(
            '"SAA_Sitplekke" BETWEEN 1 AND 8',
            name='ck_saamry_groep_sitplekke',
        ),
        CheckConstraint(
            '"SAA_Status" IN (\'AKTIEF\', \'GESLUIT\', \'GEKANSELLEER\')',
            name='ck_saamry_groep_status',
        ),
    )


class SaamryGroepLid(Base):
    __tablename__ = 'saamry_groep_lid'

    Groep_ID       = Column(Integer, ForeignKey('saamry_groep.Groep_ID'), primary_key=True)
    Gebruiker_ID   = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), primary_key=True)
    Genooi_Deur_ID = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), nullable=False)
    SAA_Status     = Column(String(20), nullable=False, default='HANGEND')
    Geskep_Op      = Column(DateTime, default=datetime.utcnow, nullable=False)
    Gewysig_Op     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    groep = relationship('SaamryGroep', back_populates='lede')
    gebruiker = relationship('Gebruikers', foreign_keys=[Gebruiker_ID])
    genooi_deur = relationship('Gebruikers', foreign_keys=[Genooi_Deur_ID])

    __table_args__ = (
        CheckConstraint(
            '"SAA_Status" IN (\'HANGEND\', \'AANVAAR\', \'GEWEIER\', \'VERLAAT\')',
            name='ck_saamry_groep_lid_status',
        ),
    )


class SaamryProfiel(Base):
    __tablename__ = 'saamry_profiel'

    Profiel_ID         = Column(Integer, primary_key=True, index=True)
    Gebruiker_ID       = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), nullable=False, unique=True, index=True)
    Rol_Tipe           = Column(String(20), nullable=False, default='BEIDE')
    Voorstad           = Column(String(120), nullable=True)
    Sone_Kode          = Column(String(50), nullable=True)
    Kampus_ID          = Column(Integer, ForeignKey('kampus.Kampus_ID'), nullable=True)
    Maks_Ompad_Minute  = Column(Integer, nullable=False, default=15)
    Is_Aktief_Saamryer = Column(Boolean, nullable=False, default=True)
    Geskep_Op          = Column(DateTime, default=datetime.utcnow, nullable=False)
    Gewysig_Op         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    gebruiker = relationship('Gebruikers', back_populates='saamry_profiel')
    kampus    = relationship('Kampus', lazy="selectin")

    __table_args__ = (
        CheckConstraint(
            '"Rol_Tipe" IN (\'BESTUURDER\', \'PASSASIER\', \'BEIDE\')',
            name='ck_saamry_profiel_rol',
        ),
    )




class SaamryEvent(Base):
    """Eenmalige Saamry-rit wat uit 'n permanente groep geskep word.

    Die event het geen tydvenster nodig nie. Dit bly AKTIEF totdat die huidige
    bestuurder suksesvol by 'n kampushek as IN of UIT bevestig is.
    """

    __tablename__ = 'saamry_event'

    Event_ID = Column(Integer, primary_key=True, index=True)
    Groep_ID = Column(Integer, ForeignKey('saamry_groep.Groep_ID', ondelete='CASCADE'), nullable=False, index=True)
    Bestuurder_ID = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), nullable=False, index=True)
    SAA_Status = Column(String(20), nullable=False, default='AKTIEF')
    Voltooi_Rigting = Column(String(8), nullable=True)
    Voltooi_Kampus_ID = Column(Integer, ForeignKey('kampus.Kampus_ID'), nullable=True)
    Bestuurder_Log_ID = Column(Integer, ForeignKey('toegangs_logs.Log_ID'), nullable=True)
    Geskep_Op = Column(DateTime, default=datetime.utcnow, nullable=False)
    Voltooi_Op = Column(DateTime, nullable=True)
    Gewysig_Op = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    groep = relationship('SaamryGroep', back_populates='events')
    bestuurder = relationship('Gebruikers', foreign_keys=[Bestuurder_ID], lazy='selectin')
    lede = relationship(
        'SaamryEventLid',
        back_populates='event',
        cascade='all, delete-orphan',
        lazy='selectin',
    )
    voltooi_kampus = relationship('Kampus', foreign_keys=[Voltooi_Kampus_ID])
    bestuurder_log = relationship('ToegangsLogs', foreign_keys=[Bestuurder_Log_ID])

    __table_args__ = (
        CheckConstraint(
            '"SAA_Status" IN (\'AKTIEF\', \'VOLTOOI\', \'GEKANSELLEER\')',
            name='ck_saamry_event_status',
        ),
        CheckConstraint(
            '"Voltooi_Rigting" IS NULL OR "Voltooi_Rigting" IN (\'IN\', \'UIT\')',
            name='ck_saamry_event_rigting',
        ),
    )


class SaamryEventLid(Base):
    __tablename__ = 'saamry_event_lid'

    Event_ID = Column(Integer, ForeignKey('saamry_event.Event_ID', ondelete='CASCADE'), primary_key=True)
    Gebruiker_ID = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), primary_key=True)
    Pickup_Latitude = Column(Float, nullable=True)
    Pickup_Longitude = Column(Float, nullable=True)
    Pickup_Beskrywing = Column(String(200), nullable=True)
    Pickup_Gewysig_Op = Column(DateTime, nullable=True)
    Pickup_Bevestig = Column(Boolean, nullable=False, default=False)
    Geskep_Op = Column(DateTime, default=datetime.utcnow, nullable=False)

    event = relationship('SaamryEvent', back_populates='lede')
    gebruiker = relationship('Gebruikers', foreign_keys=[Gebruiker_ID], lazy='selectin')


class SaamryBoodskap(Base):
    """Privaat vriend-boodskap of permanente Saamrygroep-boodskap."""

    __tablename__ = 'saamry_boodskap'

    Boodskap_ID = Column(Integer, primary_key=True, index=True)
    Stuurder_ID = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), nullable=False, index=True)
    Ontvanger_ID = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), nullable=True, index=True)
    Groep_ID = Column(Integer, ForeignKey('saamry_groep.Groep_ID', ondelete='CASCADE'), nullable=True, index=True)
    SAA_Boodskap = Column(Text, nullable=False)
    Geskep_Op = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    stuurder = relationship('Gebruikers', foreign_keys=[Stuurder_ID], lazy='selectin')
    ontvanger = relationship('Gebruikers', foreign_keys=[Ontvanger_ID], lazy='selectin')
    groep = relationship('SaamryGroep', back_populates='boodskappe')
    gelees_deur = relationship(
        'SaamryBoodskapGelees',
        back_populates='boodskap',
        cascade='all, delete-orphan',
    )

    __table_args__ = (
        CheckConstraint(
            '(("Groep_ID" IS NOT NULL AND "Ontvanger_ID" IS NULL) OR '
            '("Groep_ID" IS NULL AND "Ontvanger_ID" IS NOT NULL))',
            name='ck_saamry_boodskap_teiken',
        ),
        CheckConstraint(
            'char_length(trim("SAA_Boodskap")) BETWEEN 1 AND 1000',
            name='ck_saamry_boodskap_lengte',
        ),
    )


class SaamryBoodskapGelees(Base):
    __tablename__ = 'saamry_boodskap_gelees'

    Boodskap_ID = Column(Integer, ForeignKey('saamry_boodskap.Boodskap_ID', ondelete='CASCADE'), primary_key=True)
    Gebruiker_ID = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID', ondelete='CASCADE'), primary_key=True)
    Gelees_Op = Column(DateTime, default=datetime.utcnow, nullable=False)

    boodskap = relationship('SaamryBoodskap', back_populates='gelees_deur')
    gebruiker = relationship('Gebruikers', foreign_keys=[Gebruiker_ID])


# --- BESOEKER OTP UITNODIGINGS ---

class BesoekerUitnodiging(Base):
    __tablename__ = 'besoeker_uitnodiging'

    Uitnodiging_ID   = Column(Integer, primary_key=True, index=True)
    Gasheer_ID       = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), nullable=False)
    BES_Naam         = Column(String(100), nullable=False)
    BES_Van          = Column(String(100), nullable=False)
    BES_Selfoon_Nr   = Column(String(20), nullable=False)
    BES_Rede         = Column(String(250), nullable=False, default='Besoek')
    BES_OTP          = Column(String(6), nullable=False)
    # Dieselfde as BES_OTP terwyl die OTP nog gebruik mag word.
    # Bly aktief ná die IN-scan sodat dieselfde OTP vir UIT gebruik kan word.
    # Word eers NULL ná UIT, WEIER, KANSELLEER of VERVAL.
    # PostgreSQL laat verskeie NULL-waardes in 'n UNIQUE kolom toe, sodat
    # ses-syfer OTP's later veilig hergebruik kan word.
    BES_Aktief_Sleutel = Column(String(6), nullable=True, unique=True)
    BES_Status       = Column(String(20), nullable=False, default='HANGEND')
    BES_Geskep_Op    = Column(DateTime, default=datetime.utcnow, nullable=False)
    BES_Verval_Op    = Column(DateTime, nullable=False)
    BES_Besluit_Op   = Column(DateTime, nullable=True)
    Verwerk_Deur_ID  = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), nullable=True)
    Kampus_ID        = Column(Integer, ForeignKey('kampus.Kampus_ID'), nullable=True)

    gasheer = relationship('Gebruikers', foreign_keys=[Gasheer_ID], lazy="selectin")
    verwerk_deur = relationship('Gebruikers', foreign_keys=[Verwerk_Deur_ID])
    kampus = relationship('Kampus', foreign_keys=[Kampus_ID], lazy="selectin")

    __table_args__ = (
        CheckConstraint(
            '"BES_Status" IN (\'HANGEND\', \'TOEGELAAT\', \'GEWEIER\', '
            '\'GEKANSELLEER\', \'VERVAL\', \'UIT\')',
            name='ck_besoeker_uitnodiging_status',
        ),
    )
# --- NOODGEVAL ---
class Noodgeval(Base):
    __tablename__ = 'noodgeval'
    __table_args__ = (
        CheckConstraint(
            '"NOO_Status" IN (\'AKTIEF\', \'GESLUIT\')',
            name='ck_noodgeval_status',
        ),
    )

    Noodgeval_ID         = Column(Integer, primary_key=True, index=True)
    Kampus_ID            = Column(Integer, ForeignKey('kampus.Kampus_ID'), nullable=False, index=True)
    Geskep_Deur_ID       = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), nullable=False)
    Gesluit_Deur_ID      = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), nullable=True)
    NOO_Tipe             = Column(String(50), nullable=False, default='NOODGEVAL')
    NOO_Titel            = Column(String(150), nullable=False)
    NOO_Boodskap         = Column(Text, nullable=False)
    NOO_Status           = Column(String(20), nullable=False, default='AKTIEF')
    NOO_Boodskap_ID      = Column(String(64), nullable=False, unique=True)
    NOO_Begin_Op         = Column(DateTime, nullable=False, default=datetime.utcnow)
    NOO_Mqtt_Gestuur_Op  = Column(DateTime, nullable=True)
    NOO_Gesluit_Op       = Column(DateTime, nullable=True)
    Geskep_Op            = Column(DateTime, nullable=False, default=datetime.utcnow)
    Gewysig_Op           = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class NoodgevalKennisname(Base):
    __tablename__ = 'noodgeval_kennisname'
    __table_args__ = (
        UniqueConstraint(
            'Noodgeval_ID', 'Gebruiker_ID',
            name='uq_noodgeval_kennisname_gebruiker',
        ),
        CheckConstraint(
            '"NOK_Status" IN (\'ONTVANG\', \'KENNIS_GENEEM\')',
            name='ck_noodgeval_kennisname_status',
        ),
    )

    Kennisname_ID         = Column(Integer, primary_key=True, index=True)
    Noodgeval_ID          = Column(Integer, ForeignKey('noodgeval.Noodgeval_ID', ondelete='CASCADE'), nullable=False, index=True)
    Gebruiker_ID          = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID', ondelete='CASCADE'), nullable=False, index=True)
    NOK_Status            = Column(String(20), nullable=False, default='ONTVANG')
    NOK_Ontvang_Op        = Column(DateTime, nullable=True)
    NOK_Kennis_Geneem_Op  = Column(DateTime, nullable=True)
    Gewysig_Op            = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class SaamryVoorstelLog(Base):
    __tablename__ = 'SaamryVoorstelLog'
    Log_ID = Column(Integer, primary_key=True, index=True)
    Gebruiker_ID = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), nullable=False)
    Kandidaat_ID = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), nullable=False)
    Voorspelde_Telling = Column(Float, nullable=False)
    Aksie = Column(String(50), nullable=False) # bv. GESIEN, GESTUUR
    Tydstempel = Column(DateTime, default=datetime.utcnow)

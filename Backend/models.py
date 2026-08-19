from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Rolle(Base):
    __tablename__ = 'rolle'
    Rol_ID   = Column(Integer, primary_key=True, index=True)
    ROL_Naam = Column(String(50), nullable=False, unique=True)

    gebruikers_rolle = relationship("GebruikersRolle", back_populates="rol")

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

    rol              = relationship("Rolle")
    gebruikers_rolle = relationship("GebruikersRolle", back_populates="gebruiker")
    student          = relationship("Student",         back_populates="gebruiker", uselist=False)
    personeel        = relationship("Personeel",       back_populates="gebruiker", uselist=False)
    kampus_opsigter  = relationship("Kampus_Opsigter", back_populates="gebruiker", uselist=False)
    sekuriteit_wag   = relationship("Sekuriteit_Wag",  back_populates="gebruiker", uselist=False)
    nfc_tags         = relationship("NFC_Tags", back_populates="gebruiker")
    toegangs_logs    = relationship("ToegangsLogs",    back_populates="gebruiker")
    waarskuwings     = relationship("Waarskuwings",    back_populates="gebruiker")

class GebruikersRolle(Base):
    __tablename__ = 'gebruikers_rolle'

    Gebruiker_ID = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), primary_key=True)
    Rol_ID       = Column(Integer, ForeignKey('rolle.Rol_ID'),            primary_key=True)

    gebruiker = relationship("Gebruikers", back_populates="gebruikers_rolle")
    rol       = relationship("Rolle",      back_populates="gebruikers_rolle")

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
                           
    gebruiker = relationship("Gebruikers", back_populates="nfc_tags")
    lokasie   = relationship("Lokasie", back_populates="nfc_tags")
    toegangs_logs = relationship("ToegangsLogs", back_populates="nfc_tag")
    
class Kampus(Base):
    __tablename__ = 'kampus'
    Kampus_ID  = Column(Integer, primary_key=True, index=True)
    KAM_Naam   = Column(String(100), nullable=False)
    KAM_Adres  = Column(String(255))

    lokasies  = relationship("Lokasie",  back_populates="kampus")
    koshuise  = relationship("Koshuis",  back_populates="kampus")
    funksies  = relationship("Funksie",  back_populates="kampus")


class Lokasie(Base):
    __tablename__ = 'lokasie'
    Lokasie_ID = Column(Integer, primary_key=True, index=True)
    LOK_Naam   = Column(String(100), nullable=False)
    LOK_Tipe   = Column(String(50),  nullable=False)
    Kampus_ID  = Column(Integer, ForeignKey('kampus.Kampus_ID'), nullable=False)

    kampus    = relationship("Kampus", back_populates="lokasies")
    nfc_tags  = relationship("NFC_Tags", back_populates="lokasie")
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
    gebruiker = relationship("Gebruikers", back_populates="toegangs_logs")
    lokasie   = relationship("Lokasie",    back_populates="toegangs_logs")

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

    kampus   = relationship("Kampus", back_populates="koshuise")
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

    kampus            = relationship("Kampus", back_populates="funksies")
    lokasie           = relationship("Lokasie", foreign_keys=[Lokasie_ID])
    geskep_deur       = relationship("Gebruikers", foreign_keys=[Geskep_Deur_ID])
    funksie_besoekers = relationship("Funksie_Besoekers", back_populates="funksie")
    rsvps             = relationship(
        "FunksieRSVP",
        back_populates="funksie",
        cascade="all, delete-orphan",
    )
    publieke_rsvps    = relationship(
        "FunksiePubliekRSVP",
        back_populates="funksie",
        cascade="all, delete-orphan",
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
    gebruiker = relationship("Gebruikers")

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

    __table_args__ = (
        CheckConstraint(
            '"RSVP_Status" IN (\'GAAN\', \'GEKANSELLEER\')',
            name='ck_funksie_publiek_rsvp_status',
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

    bestuurder = relationship('Gebruikers', foreign_keys=[Bestuurder_ID])
    lede = relationship(
        'SaamryGroepLid',
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
    # Dieselfde as BES_OTP terwyl die uitnodiging aktief is.
    # Word NULL wanneer dit gebruik, geweier, gekanselleer of verval het.
    # PostgreSQL laat verskeie NULL-waardes in 'n UNIQUE kolom toe, sodat
    # ses-syfer OTP's later veilig hergebruik kan word.
    BES_Aktief_Sleutel = Column(String(6), nullable=True, unique=True)
    BES_Status       = Column(String(20), nullable=False, default='HANGEND')
    BES_Geskep_Op    = Column(DateTime, default=datetime.utcnow, nullable=False)
    BES_Verval_Op    = Column(DateTime, nullable=False)
    BES_Besluit_Op   = Column(DateTime, nullable=True)
    Verwerk_Deur_ID  = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), nullable=True)
    Kampus_ID        = Column(Integer, ForeignKey('kampus.Kampus_ID'), nullable=True)

    gasheer = relationship('Gebruikers', foreign_keys=[Gasheer_ID])
    verwerk_deur = relationship('Gebruikers', foreign_keys=[Verwerk_Deur_ID])
    kampus = relationship('Kampus', foreign_keys=[Kampus_ID])

    __table_args__ = (
        CheckConstraint(
            '"BES_Status" IN (\'HANGEND\', \'TOEGELAAT\', \'GEWEIER\', '
            '\'GEKANSELLEER\', \'VERVAL\')',
            name='ck_besoeker_uitnodiging_status',
        ),
    )

# --- INSTELLING (APPLICATION SETTINGS) ---

class Instelling(Base):
    __tablename__ = 'instellings'

    Sleutel      = Column(String(100), primary_key=True)
    Waarde       = Column(String(255), nullable=False)
    Beskrywing   = Column(String(255), nullable=True)

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
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

    gebruiker = relationship("Gebruikers", back_populates="student")

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
    TOE_Metode          = Column(String(32), nullable=False) # "NFC" | "HANDMATIG" | "QR"
    TOE_Auto_Uitgecheck = Column(Boolean, nullable=False, default=False)

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
    funskie_besoekers    = relationship("Funksie_Besoekers",  back_populates="besoekers_groep")

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

    kampus = relationship("Kampus", back_populates="koshuise")

class Funksie(Base):
    __tablename__ = 'funskie'

    Funksie_ID    = Column(Integer, primary_key=True, index=True)
    Kampus_ID     = Column(Integer, ForeignKey('kampus.Kampus_ID'), nullable=False)
    FUN_Naam      = Column(String(100), nullable=False)
    FUN_Begin_Tyd = Column(DateTime, nullable=False)
    FUN_Eind_Tyd  = Column(DateTime, nullable=False)
    FUN_Beskrywing = Column(Text)
    FUN_Is_Aktief = Column(Boolean, nullable=False, default=True)

    kampus          = relationship("Kampus",         back_populates="funksies")
    funskie_besoekers = relationship("Funksie_Besoekers", back_populates="funskie")

class Funksie_Besoekers(Base):
    __tablename__ = 'funskie_besoekers'

    Besoekers_Groep_ID = Column(Integer, ForeignKey('besoekers_groep.Besoekers_Groep_ID'), primary_key=True)
    Funksie_ID         = Column(Integer, ForeignKey('funskie.Funksie_ID'),                 primary_key=True)
    FUNB_Status        = Column(String(32), nullable=False)

    besoekers_groep = relationship("Besoekers_Groep", back_populates="funskie_besoekers")
    funskie         = relationship("Funksie",         back_populates="funskie_besoekers")
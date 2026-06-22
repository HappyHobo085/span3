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
    Lokasie_ID    = Column(Integer, ForeignKey('lokasie.Lokasie_ID'))
    NFC_Tipe      = Column(String(32), nullable=False)
    NFC_Is_Aktief = Column(Boolean, nullable=False, default=True)
                           
    lokasie       = relationship("Lokasie", back_populates="nfc_tags")
    toegangs_logs = relationship("ToegangsLogs", back_populates="nfc_tag")

class Kampus(Base):
    __tablename__ = 'kampus'
    Kampus_ID  = Column(Integer, primary_key=True, index=True)
    KAM_Naam   = Column(String(100), nullable=False)
    KAM_Adres  = Column(String(255))

    lokasies = relationship("Lokasie", back_populates="kampus")


class Lokasie(Base):
    __tablename__ = 'lokasie'
    Lokasie_ID = Column(Integer, primary_key=True, index=True)
    LOK_Naam   = Column(String(100), nullable=False)
    LOK_Tipe   = Column(String(50),  nullable=False)
    Kampus_ID  = Column(Integer, ForeignKey('kampus.Kampus_ID'), nullable=False)

    kampus        = relationship("Kampus", back_populates="lokasies")
    nfc_tags      = relationship("NFC_Tags", back_populates="lokasie")
    toegangs_logs = relationship("ToegangsLogs", back_populates="lokasie")

class ToegangsLogs(Base):
    __tablename__ = 'toegangs_logs'

    Log_ID        = Column(Integer,  primary_key=True, index=True)
    NFC_Tags_ID   = Column(Integer,  ForeignKey('nfc_tags.NFC_Tags_ID'), nullable=False)
    Gebruiker_ID  = Column(Integer,  ForeignKey('gebruikers.Gebruiker_ID'), nullable=False)
    Lokasie_ID    = Column(Integer,  ForeignKey('lokasie.Lokasie_ID'), nullable=False)
    LOG_Status    = Column(String(32), nullable=False, default='TOEGELAAT')
    # "TOEGELAAT" | "GEWEIER" | "ONBEKEND"
    LOG_Tydstempel = Column(DateTime, default=datetime.utcnow, nullable=False)

    nfc_tag   = relationship("NFC_Tags",   back_populates="toegangs_logs")
    gebruiker = relationship("Gebruikers", back_populates="toegangs_logs")
    lokasie   = relationship("Lokasie",    back_populates="toegangs_logs")

class Waarskuwings(Base):
    __tablename__ = 'waarskuwings'
    Waarskuwing_ID = Column(Integer, primary_key=True, index=True)
    Gebruiker_ID   = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), nullable=False)
    WAA_Beskrywing = Column(Text, nullable=False)
    WAA_Status     = Column(String(32), nullable=False, default='OOP')
    WAA_Tydstempel = Column(DateTime, default=datetime.utcnow)

    gebruiker = relationship("Gebruikers", back_populates="waarskuwings")

class Kampus_Opsigter(Base):
    __tablename__ = 'kampus_opsigter'
    Gebruiker_ID = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), primary_key=True)
    KAMO_Nommer  = Column(String(20), nullable=False, unique=True)

    gebruiker = relationship("Gebruikers", back_populates="kampus_opsigter")

class Sekuriteit_Wag(Base):
    __tablename__ = 'sekuriteit_wag'
    Gebruiker_ID = Column(Integer, ForeignKey('gebruikers.Gebruiker_ID'), primary_key=True)
    SEK_Nommer   = Column(String(20), nullable=False, unique=True)

    gebruiker = relationship("Gebruikers", back_populates="sekuriteit_wag")
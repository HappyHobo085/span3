-- 005_koshuis_funksie.sql
-- Voeg Koshuis, Funksie en Funksie_Besoekers tabelle by

CREATE TABLE Koshuis (
    Koshuis_ID    SERIAL PRIMARY KEY,
    KOS_Naam      VARCHAR(100) NOT NULL,
    KOS_Adres     VARCHAR(255),
    KOS_Kapasiteit INTEGER NOT NULL,
    Kampus_ID     INT NOT NULL REFERENCES Kampus(Kampus_ID)
);

CREATE TABLE Funskie (
    Funksie_ID    SERIAL PRIMARY KEY,
    Kampus_ID     INT NOT NULL REFERENCES Kampus(Kampus_ID),
    FUN_Naam      VARCHAR(100) NOT NULL,
    FUN_Begin_Tyd TIMESTAMP NOT NULL,
    FUN_Eind_Tyd  TIMESTAMP NOT NULL,
    FUN_Beskrywing TEXT,
    FUN_Is_Aktief BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE Funskie_Besoekers (
    Besoekers_Groep_ID INT NOT NULL REFERENCES Besoekers_Groep(Besoekers_Groep_ID),
    Funksie_ID         INT NOT NULL REFERENCES Funskie(Funksie_ID),
    FUNB_Status        VARCHAR(32) NOT NULL,
    PRIMARY KEY (Besoekers_Groep_ID, Funksie_ID)
);

-- Indekse vir vinnige opsoek
CREATE INDEX idx_koshuis_kampus ON Koshuis(Kampus_ID);
CREATE INDEX idx_funksie_kampus ON Funskie(Kampus_ID);
CREATE INDEX idx_funksie_besoekers_funksie ON Funskie_Besoekers(Funksie_ID);

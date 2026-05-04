-- 002_gebruikers.sql
CREATE TABLE Gebruikers (
    Gebruiker_ID SERIAL PRIMARY KEY,
    GEB_Naam VARCHAR(100) NOT NULL,
    GEB_Van VARCHAR(100) NOT NULL,
    GEB_ID_Nommer VARCHAR(13) NOT NULL UNIQUE, -- SA ID: 13 syfers
    GEB_Epos VARCHAR(255) NOT NULL UNIQUE,
    GEB_Wagwoord VARCHAR(255) NOT NULL, -- gehash deur Steven
    GEB_Selfoon_Nr VARCHAR(15),
    GEB_Profiel_Foto VARCHAR(500), -- URL na lêer
    Rol_ID INT NOT NULL, -- REFERENCES Rolle(Rol_ID)
    Is_Aktief BOOLEAN NOT NULL DEFAULT TRUE,
    Geskep_Op TIMESTAMP NOT NULL DEFAULT NOW(),
    Gewysig_Op TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Voeg vreemde sleutel by NFC_Tags nou dat Gebruikers bestaan
ALTER TABLE NFC_Tags ADD CONSTRAINT fk_nfc_gebruiker FOREIGN KEY (Gebruiker_ID) REFERENCES Gebruikers(Gebruiker_ID);

-- 003_waarskuwings.sql
CREATE TABLE Waarskuwings (
    Waarskuwing_ID SERIAL PRIMARY KEY,
    Gebruiker_ID INT NOT NULL REFERENCES Gebruikers(Gebruiker_ID),
    Lokasie_ID INT, -- REFERENCES Lokasies(Lokasie_ID)
    WAA_Beskrywing TEXT NOT NULL,
    WAA_Status VARCHAR(32) NOT NULL DEFAULT 'OOP', -- 'OOP', 'ERKEN', 'GESLUIT'
    WAA_Tydstempel TIMESTAMP NOT NULL DEFAULT NOW()
);

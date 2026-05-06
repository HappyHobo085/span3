-- 004_rolle.sql
CREATE TABLE Rolle (
    Rol_ID SERIAL PRIMARY KEY,
    ROL_Naam VARCHAR(50) NOT NULL UNIQUE
);

-- Saai data
INSERT INTO Rolle (ROL_Naam) VALUES
('Administrateur'),
('Kampus_Opsigter'),
('Personeel'),
('Student'),
('Sekuriteit_Wag');

-- Voeg vreemde sleutel by Gebruikers nou dat Rolle bestaan
ALTER TABLE Gebruikers ADD CONSTRAINT fk_gebruiker_rol FOREIGN KEY (Rol_ID) REFERENCES Rolle(Rol_ID);

-- Subklastabelle vir Kampus_Opsigter en Sekuriteit_Wag
CREATE TABLE Kampus_Opsigter (
    Gebruiker_ID INT PRIMARY KEY REFERENCES Gebruikers(Gebruiker_ID),
    KAMO_Nommer VARCHAR(20) NOT NULL UNIQUE,
    Kampus_ID INT -- Sal later aan Kampus tabel gekoppel word
);

CREATE TABLE Sekuriteit_Wag (
    Gebruiker_ID INT PRIMARY KEY REFERENCES Gebruikers(Gebruiker_ID),
    SEK_Nommer VARCHAR(20) NOT NULL UNIQUE
);

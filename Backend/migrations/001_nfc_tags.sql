-- 001_nfc_tags.sql
CREATE TABLE NFC_Tags (
    NFC_Tags_ID SERIAL PRIMARY KEY,
    NFC_UID VARCHAR(64) NOT NULL UNIQUE, -- fisiese tag se ID
    Gebruiker_ID INT, -- REFERENCES Gebruikers(Gebruiker_ID) sal later bygevoeg word as Gebruikers bestaan
    NFC_Tipe VARCHAR(32) NOT NULL, -- 'STUDENT', 'VOERTUIG', 'LOKASIE'
    NFC_Is_Aktief BOOLEAN NOT NULL DEFAULT TRUE,
    -- Ouditspoor
    Geskep_Op TIMESTAMP NOT NULL DEFAULT NOW(),
    Gewysig_Op TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indeks vir vinnige opsoek tydens skandering
CREATE INDEX idx_nfc_uid ON NFC_Tags(NFC_UID);
CREATE INDEX idx_nfc_gebruiker ON NFC_Tags(Gebruiker_ID);

-- Unieke indeks vir aktiewe tags per gebruiker (F13)
CREATE UNIQUE INDEX idx_een_aktiewe_tag_per_gebruiker
ON NFC_Tags(Gebruiker_ID)
WHERE NFC_Is_Aktief = TRUE;

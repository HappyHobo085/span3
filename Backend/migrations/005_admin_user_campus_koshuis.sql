-- 005_admin_user_campus_koshuis.sql
-- Admin user editing additions:
--  - mark students as koshuis students
--  - assign campus to campus opsigters

ALTER TABLE Student
ADD COLUMN IF NOT EXISTS STU_Is_Koshuis BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE Kampus_Opsigter
ADD COLUMN IF NOT EXISTS Kampus_ID INT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_kampus_opsigter_kampus'
    ) THEN
        ALTER TABLE Kampus_Opsigter
        ADD CONSTRAINT fk_kampus_opsigter_kampus
        FOREIGN KEY (Kampus_ID) REFERENCES Kampus(Kampus_ID);
    END IF;
END $$;

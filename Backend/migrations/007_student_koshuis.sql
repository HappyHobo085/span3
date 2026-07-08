-- 007_student_koshuis.sql
-- Koppel 'n student aan 'n spesifieke koshuis sodat die Koshuis-bladsy
-- se dashboard per koshuis kan wys wie in- of uitgeteken is.

-- NB: die lewendige tabelle is deur SQLAlchemy geskep met aanhalings-sensitiewe kolomname.
ALTER TABLE student
ADD COLUMN IF NOT EXISTS "Koshuis_ID" INT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_student_koshuis'
    ) THEN
        ALTER TABLE student
        ADD CONSTRAINT fk_student_koshuis
        FOREIGN KEY ("Koshuis_ID") REFERENCES koshuis("Koshuis_ID");
    END IF;
END $$;

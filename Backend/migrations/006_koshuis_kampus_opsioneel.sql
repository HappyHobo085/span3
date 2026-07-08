-- 006_koshuis_kampus_opsioneel.sql
-- 'n Koshuis word geskep met slegs Naam, Adres en Kapasiteit,
-- dus is die kampus-koppeling nou opsioneel.

-- NB: die lewendige tabel is deur SQLAlchemy geskep met aanhalings-sensitiewe kolomname.
ALTER TABLE koshuis
ALTER COLUMN "Kampus_ID" DROP NOT NULL;

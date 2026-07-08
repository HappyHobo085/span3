-- 007_koshuis_kapasiteit_default.sql
-- Kapasiteit word nie meer by koshuis-skepping ingevoer nie ('n kampus word
-- eerder gekies), dus kry KOS_Kapasiteit 'n verstekwaarde van 0.

ALTER TABLE koshuis
ALTER COLUMN "KOS_Kapasiteit" SET DEFAULT 0;

import sys
sys.path.append(r"C:\Jaco Oosthuizen\Akademia\Derde Jaar (2026)\NSWIW370\Span3_Repo\span3\Backend")

from services.ml_service import voorspel_aankomstyd_offset

offset, sigma, bron = voorspel_aankomstyd_offset(480, "midrand", "BEIDE", 0)
print(f"Unknown cluster test: offset={offset}, sigma={sigma}, bron={bron}")

offset, sigma, bron = voorspel_aankomstyd_offset(480, None, "BEIDE", 0)
print(f"None cluster test: offset={offset}, sigma={sigma}, bron={bron}")

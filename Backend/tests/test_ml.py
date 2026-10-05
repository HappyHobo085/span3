import sys
import os

sys.path.append(r"C:\Jaco Oosthuizen\Akademia\Derde Jaar (2026)\NSWIW370\Span3_Repo\span3\Backend")

from services.ml_service import voorspel_aankomstyd_offset, _voorspel_met_kas

offset, sigma, bron = voorspel_aankomstyd_offset(480, "oos", "BEIDE", 0)
print(f"Voorspel: offset={offset}, sigma={sigma}, bron={bron}")
print(f"Cache info: {_voorspel_met_kas.cache_info()}")

# Do it again
offset, sigma, bron = voorspel_aankomstyd_offset(480, "oos", "BEIDE", 0)
print(f"Voorspel 2: offset={offset}, sigma={sigma}, bron={bron}")
print(f"Cache info: {_voorspel_met_kas.cache_info()}")

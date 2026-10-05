import sys
sys.path.append(r"C:\Jaco Oosthuizen\Akademia\Derde Jaar (2026)\NSWIW370\Span3_Repo\span3\Backend")

# We must reload module to clear cache
import importlib
import services.ml_service as ml
importlib.reload(ml)

offset, sigma, bron = ml.voorspel_aankomstyd_offset(480, "oos", "BEIDE", 0)
print(f"Fallback 1: offset={offset}, sigma={sigma}, bron={bron}")
print(f"Cache info: {ml._voorspel_met_kas.cache_info()}")

offset, sigma, bron = ml.voorspel_aankomstyd_offset(480, "oos", "BEIDE", 0)
print(f"Fallback 2: offset={offset}, sigma={sigma}, bron={bron}")
print(f"Cache info: {ml._voorspel_met_kas.cache_info()}")

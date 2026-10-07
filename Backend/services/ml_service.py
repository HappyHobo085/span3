import os
import joblib
import functools
from typing import Tuple, Optional, Any

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ml_models", "aankoms_model.joblib")

_model: Optional[Any] = None
_model_loaded: bool = False
_model_load_failed: bool = False

def _laai_model() -> None:
    global _model, _model_loaded, _model_load_failed
    if _model_loaded or _model_load_failed:
        return
    try:
        _model = joblib.load(MODEL_PATH)
        _model_loaded = True
    except Exception as e:
        print(f"Waarskuwing: Kon nie aankoms_model.joblib laai nie: {e}")
        _model_load_failed = True

@functools.lru_cache(maxsize=1024)
def _voorspel_met_kas(vroegste_klas_minuut: int, kluster: Optional[str], rol: str, is_koshuis: int) -> Tuple[int, float, str]:
    if not _model_loaded or _model is None:
        # Dit veronderstel _laai_model is reeds tevore geroep en het geslaag as ons hier kom
        # maar just in case
        return (30, 22.2, "MEDIAAN")

    model_type = _model.get("type", "MEDIAAN")
    known_clusters = _model.get("known_clusters", [])

    if kluster is None or kluster not in known_clusters:
        # Onbekende kluster: val terug op globale mediaan met bron MEDIAAN
        offset = int(_model.get("global_median", 30.0))
        sigma = float(_model.get("sigma", 22.2))
        return (offset, sigma, "MEDIAAN")

    if model_type == "ML":
        import pandas as pd
        df = pd.DataFrame([{
            "klas_begin_minuut": vroegste_klas_minuut,
            "kluster": kluster,
            "rol": rol,
            "is_koshuis": is_koshuis
        }])
        
        q50_model = _model["q50"]
        q10_model = _model["q10"]
        q90_model = _model["q90"]
        
        try:
            p_50 = float(q50_model.predict(df)[0])
            p_10 = float(q10_model.predict(df)[0])
            p_90 = float(q90_model.predict(df)[0])
            
            # Sorteer kwantiele
            qs = sorted([p_10, p_50, p_90])
            q10, q50, q90 = qs[0], qs[1], qs[2]
            
            offset = int(round(q50))
            sigma = (q90 - q10) / 2.56
            sigma = min(max(sigma, 5.0), 30.0)
            
            return (offset, sigma, "ML_MODEL")
        except Exception as e:
            print(f"ML voorspelling misluk: {e}")
            # Fallback op globale mediaan indien model uitsondering gooi (bv onverwagte tipe)
            offset = int(_model.get("global_median", 30.0))
            return (offset, float(_model.get("sigma", 22.2)), "MEDIAAN")

    else:
        # MEDIAAN TIPE
        rule = _model.get("rule", "GLOBAL")
        global_med = _model.get("global_median", 30.0)
        sigma = _model.get("sigma", 22.2)
        
        if rule == "CLUSTER":
            group_medians = _model.get("group_medians", {})
            cluster_medians = _model.get("cluster_medians", {})
            group_counts = _model.get("group_counts", {})
            cluster_counts = _model.get("cluster_counts", {})
            
            vroeg = 1 if vroegste_klas_minuut <= 480 else 0
            
            if group_counts.get((kluster, vroeg), 0) >= 8:
                offset = int(group_medians.get((kluster, vroeg), global_med))
            elif cluster_counts.get(kluster, 0) >= 8:
                offset = int(cluster_medians.get(kluster, global_med))
            else:
                offset = int(global_med)
        else:
            offset = int(global_med)
            
        return (offset, sigma, "MEDIAAN")

def voorspel_aankomstyd_offset(vroegste_klas_minuut: int, kluster: Optional[str], rol: str, is_koshuis: int) -> Tuple[int, float, str]:
    _laai_model()
    
    if _model_load_failed:
        # Gaan nie kas in as die model ontbreek nie
        return (30, 22.2, "MEDIAAN")
        
    return _voorspel_met_kas(vroegste_klas_minuut, kluster, rol, is_koshuis)


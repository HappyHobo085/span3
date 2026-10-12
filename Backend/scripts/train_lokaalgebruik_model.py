"""Lei die lokaalgebruik-model vanlyn op en stoor die wenner.

Lees die weeklikse kiekie (sessie, lokaal, ingeskryf, geskandeer), vergelyk die
HistGradientBoosting-model met 'n groeiende venster teen die basislyne, en stoor
die gekose metode saam met die geskiedenis wat die API nodig het om volgende
week te voorspel. Die logika self is in services/lokaalgebruik_model.py.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import joblib
import pandas as pd

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.lokaalgebruik_model import METODE_ETIKETTE, oplei  # noqa: E402

DATA_PATH = Path(os.getenv(
    "LOKAALGEBRUIK_DATA_PATH",
    str(BACKEND_ROOT / "ml_data" / "sintetiese_lokaalgebruik.csv"),
))
MODEL_PATH = Path(os.getenv(
    "LOKAALGEBRUIK_MODEL_PATH",
    str(BACKEND_ROOT / "ml_models" / "lokaalgebruik_model.joblib"),
))

NODIG = {"Week", "Vak", "Lokaal", "Dag", "Begin", "Inskrywing", "Kapasiteit", "Skanderings"}


def laai_kiekie(pad: Path = DATA_PATH) -> pd.DataFrame:
    if not pad.exists():
        raise FileNotFoundError(f"Geen opleidingsdata nie: {pad}")
    df = pd.read_csv(pad)
    ontbreek = sorted(NODIG.difference(df.columns))
    if ontbreek:
        raise RuntimeError(f"Opleidings-CSV ontbreek kolomme: {ontbreek}")
    if "Sessie" not in df.columns:
        if "Klas_ID" in df.columns:
            df["Sessie"] = df["Klas_ID"]
        else:
            df["Sessie"] = df["Vak"].astype(str) + "|" + df["Lokaal"].astype(str) + "|" \
                + df["Dag"].astype(str) + "|" + df["Begin"].astype(str)
    return df


def train() -> dict:
    df = laai_kiekie()
    databron = os.getenv("LOKAALGEBRUIK_DATABRON", "SINTETIES")
    bundel = oplei(df, databron=databron)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundel, MODEL_PATH)

    m = bundel.get("metrics") or {}
    print(f"✅ Lokaalgebruik: {bundel['rows']} rye, weke 1–{bundel['laaste_week']}, "
          f"voorspel week {bundel['voorspel_week']}")
    if m.get("mae"):
        for metode, mae in m["mae"].items():
            print(f"   MAE {METODE_ETIKETTE[metode]}: {mae}")
    print(f"✅ Gekies: {METODE_ETIKETTE[bundel['metode']]} — {bundel['keuse_rede']}")
    iv = bundel["interval"]
    if iv.get("dekking") is not None:
        print(f"   Reeks-dekking (doel ≈ 80%): {iv['dekking']:.0%} "
              f"→ {'gewys' if iv['wys'] else 'nie gewys nie'}")
    print(f"✅ Gestoor: {MODEL_PATH}")
    return bundel


if __name__ == "__main__":
    try:
        train()
    except Exception as exc:
        print(f"❌ Lokaalgebruik-opleiding het misluk: {exc}")
        raise SystemExit(1)

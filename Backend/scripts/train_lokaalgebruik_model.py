from __future__ import annotations

import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = BACKEND_ROOT / "ml_data" / "sintetiese_lokaalgebruik.csv"
MODEL_PATH = BACKEND_ROOT / "ml_models" / "lokaalgebruik_model.joblib"

CATEGORICAL = ["Kampus", "Vak", "Lokaal", "Dag"]
NUMERIC = ["Week", "BeginMinuut", "Inskrywing", "Kapasiteit"]
FEATURES = CATEGORICAL + NUMERIC


def _tyd_na_minute(value) -> int:
    text = str(value or "").strip().replace(".", ":")
    try:
        h, m = text.split(":", 1)
        return int(h) * 60 + int(m[:2])
    except Exception:
        return 0


def train() -> dict:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Geen training data: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)
    if len(df) < 20:
        raise RuntimeError(
            f"Te min training rye ({len(df)}). Minstens 20 word vereis."
        )

    nodig = {
        "Week", "Kampus", "Vak", "Lokaal", "Dag", "Begin",
        "Inskrywing", "Kapasiteit", "Skanderings",
    }
    ontbreek = sorted(nodig.difference(df.columns))
    if ontbreek:
        raise RuntimeError(f"Training CSV ontbreek kolomme: {ontbreek}")

    df = df.copy()
    df["BeginMinuut"] = df["Begin"].map(_tyd_na_minute)
    df["Inskrywing"] = pd.to_numeric(df["Inskrywing"], errors="coerce").fillna(0)
    df["Kapasiteit"] = pd.to_numeric(df["Kapasiteit"], errors="coerce").fillna(0)
    df["Skanderings"] = pd.to_numeric(df["Skanderings"], errors="coerce").fillna(0)
    df = df[df["Inskrywing"] > 0].copy()

    df["BywoningKoers"] = (
        df["Skanderings"] / df["Inskrywing"].clip(lower=1)
    ).clip(0.0, 1.0)

    if len(df) < 20:
        raise RuntimeError("Te min bruikbare training rye na skoonmaak.")

    # Reproduceerbare holdout oor die volledige semester. Week is self 'n
    # feature, sodat die semester-verval wat deur die sintetiese generator
    # geskep word deel van die prediction kan wees.
    test_df = df.sample(frac=0.20, random_state=42)
    train_df = df.drop(index=test_df.index)

    pre = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
            ("num", "passthrough", NUMERIC),
        ]
    )
    model = RandomForestRegressor(
        n_estimators=180,
        random_state=42,
        min_samples_leaf=2,
        n_jobs=-1,
    )
    pipeline = Pipeline([
        ("pre", pre),
        ("model", model),
    ])

    pipeline.fit(train_df[FEATURES], train_df["BywoningKoers"])

    pred = np.clip(pipeline.predict(test_df[FEATURES]), 0.0, 1.0)
    y = test_df["BywoningKoers"].to_numpy()

    metrics = {
        "mae_bywoning_koers": round(float(mean_absolute_error(y, pred)), 4),
        "r2": round(float(r2_score(y, pred)), 4) if len(test_df) > 1 else None,
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
    }

    bundle = {
        "type": "RANDOM_FOREST",
        "doel": "BYWONING_KOERS",
        "bron": "SINTETIES/ML",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "features": FEATURES,
        "model": pipeline,
        "metrics": metrics,
        "rows": int(len(df)),
    }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, MODEL_PATH)

    print(
        "✅ Lokaalgebruik-model opgelei: "
        f"{len(df)} rye | MAE={metrics['mae_bywoning_koers']} | "
        f"R²={metrics['r2']}"
    )
    print(f"✅ Model gestoor: {MODEL_PATH}")
    return bundle


if __name__ == "__main__":
    try:
        train()
    except Exception as exc:
        print(f"❌ Lokaalgebruik training het misluk: {exc}")
        raise SystemExit(1)

"""Suiwer ML-logika vir die lokaalgebruikvoorspelling (geen databasis nie).

Die model voorspel die *skanderingskoers* van 'n klassessie (geskandeer ÷
ingeskryf) vir die komende week. Die verwagte getal en vulgraad word daarna uit
die rooster (inskrywing) en die lokaalgrootte (kapasiteit) bereken.

Invoer is 'n weeklikse kiekie met een ry per sessie per week en die kolomme:
Week, Sessie, Vak, Lokaal, Dag, Begin, Inskrywing, Kapasiteit en (vir
geskiedenis) Skanderings.

Evaluasie gebruik 'n groeiende venster (oplei op weke 1..k, voorspel k+1) en
die model word net gekies as dit die sterkste basislyn met minstens een
standaardfout klop (gepaarde bootstrap op die per-sessie-foute).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd

DAG_MAP = {
    "monday": "Maandag", "maandag": "Maandag",
    "tuesday": "Dinsdag", "dinsdag": "Dinsdag",
    "wednesday": "Woensdag", "woensdag": "Woensdag",
    "thursday": "Donderdag", "donderdag": "Donderdag",
    "friday": "Vrydag", "vrydag": "Vrydag",
    "saturday": "Saterdag", "saterdag": "Saterdag",
    "sunday": "Sondag", "sondag": "Sondag",
}
DAE = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrydag", "Saterdag", "Sondag"]

FEATURES = ["Week", "DagIndeks", "BeginUur", "VakHistKoers", "GeskeduleerdeVulgraad"]
CATEGORICAL = [FEATURES.index("DagIndeks")]

# Tot daar minstens soveel weke data is, word die laaste-3-weke-gemiddelde gebruik.
MIN_WEKE_VIR_MODEL = 4
# Die interval word slegs gewys as die gemete dekking minstens hierdie waarde is.
MIN_DEKKING = 0.70
INTERVAL_KWANTIELE = (0.10, 0.90)
BOOTSTRAP_HERHALINGS = 2000

METODE_ROOSTER = "ROOSTER"
METODE_LAASTE3 = "BASISLYN_LAASTE_3_WEKE"
METODE_DAGUUR = "BASISLYN_DAG_UUR"
METODE_MODEL = "ML_MODEL"

METODE_ETIKETTE = {
    METODE_ROOSTER: "Rooster (geen skanderingsdata nie)",
    METODE_LAASTE3: "Basislyn: gemiddelde van laaste 3 weke",
    METODE_DAGUUR: "Basislyn: gemiddelde per dag en uur",
    METODE_MODEL: "ML-model (HistGradientBoosting)",
}


def normaliseer_dag(value) -> str:
    teks = str(value or "").strip()
    return DAG_MAP.get(teks.lower(), teks)


def normaliseer_tyd(value) -> str:
    teks = str(value or "").strip().replace(".", ":")
    m = re.match(r"^(\d{1,2}):(\d{2})", teks)
    if not m:
        return teks
    return f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"


def tyd_na_minute(value) -> int | None:
    m = re.match(r"^(\d{1,2}):(\d{2})", normaliseer_tyd(value))
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2))


# --------------------------------------------------------------------------
# Kenmerke
# --------------------------------------------------------------------------

def berei_voor(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliseer 'n kiekie en voeg die kenmerke by wat nie van ander weke afhang nie."""
    df = df.copy()
    df["Week"] = pd.to_numeric(df["Week"], errors="coerce").astype("Int64")
    df = df[df["Week"].notna()].copy()
    df["Week"] = df["Week"].astype(int)
    df["Sessie"] = df["Sessie"].astype(str)
    df["Vak"] = df["Vak"].astype(str)
    df["Dag"] = df["Dag"].map(normaliseer_dag)
    df["Begin"] = df["Begin"].map(normaliseer_tyd)
    df["Inskrywing"] = pd.to_numeric(df["Inskrywing"], errors="coerce").fillna(0)
    df["Kapasiteit"] = pd.to_numeric(df["Kapasiteit"], errors="coerce").fillna(0)
    df = df[df["Inskrywing"] > 0].copy()

    df["DagIndeks"] = df["Dag"].map(lambda d: DAE.index(d) if d in DAE else np.nan)
    df["BeginUur"] = df["Begin"].map(tyd_na_minute) / 60.0
    df["GeskeduleerdeVulgraad"] = np.where(
        df["Kapasiteit"] > 0, df["Inskrywing"] / df["Kapasiteit"].where(df["Kapasiteit"] > 0), np.nan
    )
    if "Skanderings" in df.columns:
        skan = pd.to_numeric(df["Skanderings"], errors="coerce").fillna(0)
        df["Koers"] = (skan / df["Inskrywing"]).clip(0.0, 1.0)
    return df


def voeg_vak_hist_koers_by(df: pd.DataFrame) -> pd.DataFrame:
    """Vak se historiese koers uit *slegs vorige* weke (geen lekkasie uit die toekoms nie)."""
    g = (
        df.groupby(["Vak", "Week"])["Koers"].agg(["sum", "count"])
        .reset_index().sort_values(["Vak", "Week"])
    )
    g["cum_som"] = g.groupby("Vak")["sum"].cumsum() - g["sum"]
    g["cum_n"] = g.groupby("Vak")["count"].cumsum() - g["count"]
    g["VakHistKoers"] = g["cum_som"] / g["cum_n"].where(g["cum_n"] > 0)
    df = df.drop(columns=["VakHistKoers"], errors="ignore")
    return df.merge(g[["Vak", "Week", "VakHistKoers"]], on=["Vak", "Week"], how="left")


def vak_hist_vir_teiken(hist: pd.DataFrame, teiken: pd.DataFrame) -> pd.Series:
    """VakHistKoers vir 'n toekomstige week: gemiddelde oor al die geskiedenis."""
    gem = hist.groupby("Vak")["Koers"].mean()
    return teiken["Vak"].map(gem).astype(float)


# --------------------------------------------------------------------------
# Basislyne
# --------------------------------------------------------------------------

def basislyn_laaste3(hist: pd.DataFrame, teiken: pd.DataFrame, laaste_week: int) -> np.ndarray:
    venster = hist[hist["Week"] > laaste_week - 3]
    if venster.empty:
        venster = hist
    globaal = float(venster["Koers"].mean()) if not venster.empty else 1.0
    per_sessie = venster.groupby("Sessie")["Koers"].mean()
    per_vak = venster.groupby("Vak")["Koers"].mean()
    p = teiken["Sessie"].map(per_sessie)
    p = p.fillna(teiken["Vak"].map(per_vak)).fillna(globaal)
    return p.to_numpy(dtype=float)


def basislyn_daguur(hist: pd.DataFrame, teiken: pd.DataFrame) -> np.ndarray:
    globaal = float(hist["Koers"].mean()) if not hist.empty else 1.0
    gem = hist.groupby(["DagIndeks", "BeginUur"])["Koers"].mean()
    sleutels = list(zip(teiken["DagIndeks"], teiken["BeginUur"]))
    return np.array([float(gem.get(k, globaal)) for k in sleutels], dtype=float)


def maak_model():
    from sklearn.ensemble import HistGradientBoostingRegressor

    return HistGradientBoostingRegressor(
        loss="absolute_error",
        learning_rate=0.05,
        max_iter=250,
        max_leaf_nodes=15,
        min_samples_leaf=10,
        l2_regularization=0.1,
        categorical_features=CATEGORICAL,
        random_state=42,
    )


def _voorspel_model(model, teiken: pd.DataFrame) -> np.ndarray:
    return np.clip(model.predict(teiken[FEATURES]), 0.0, 1.0)


# --------------------------------------------------------------------------
# Evaluasie en keuse
# --------------------------------------------------------------------------

def gepaarde_bootstrap(fout_basis: np.ndarray, fout_model: np.ndarray, seed: int = 42) -> dict:
    """Gemiddelde verskil (basislyn − model) in absolute fout, met bootstrap-SE.

    'n Positiewe verskil beteken die model se foute is kleiner.
    """
    d = np.abs(np.asarray(fout_basis, dtype=float)) - np.abs(np.asarray(fout_model, dtype=float))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(BOOTSTRAP_HERHALINGS, len(d)))
    gemiddeldes = d[idx].mean(axis=1)
    return {"verskil": float(d.mean()), "se": float(gemiddeldes.std(ddof=1))}


def groeiende_venster(df: pd.DataFrame) -> pd.DataFrame:
    """Uit-voue-voorspellings: oplei op weke 1..k, voorspel week k+1, vir elke k ≥ MIN."""
    weke = sorted(df["Week"].unique())
    voue = []
    for k in weke:
        if k < MIN_WEKE_VIR_MODEL or (k + 1) not in weke:
            continue
        oplei = df[df["Week"] <= k]
        toets = df[df["Week"] == k + 1]
        if toets.empty or len(oplei) < 20:
            continue
        model = maak_model().fit(oplei[FEATURES], oplei["Koers"])
        voue.append(pd.DataFrame({
            "Week": toets["Week"].to_numpy(),
            "y": toets["Koers"].to_numpy(),
            METODE_MODEL: _voorspel_model(model, toets),
            METODE_LAASTE3: basislyn_laaste3(oplei, toets, k),
            METODE_DAGUUR: basislyn_daguur(oplei, toets),
            METODE_ROOSTER: np.ones(len(toets)),
        }))
    if not voue:
        return pd.DataFrame()
    return pd.concat(voue, ignore_index=True)


def meet_dekking(oof: pd.DataFrame, metode: str) -> tuple[float | None, int]:
    """Meet eerlik of ~80% van werklike waardes in die reeks val.

    Die kwantiele vir week j kom slegs uit residue van vroeër voue, sodat die
    dekking nie op dieselfde data gemeet word as waarop die reeks bepaal is nie.
    """
    lo_q, hi_q = INTERVAL_KWANTIELE
    gedek = []
    for week in sorted(oof["Week"].unique()):
        vroeer = oof[oof["Week"] < week]
        if len(vroeer) < 20:
            continue
        res = vroeer["y"] - vroeer[metode]
        q_lo, q_hi = np.quantile(res, [lo_q, hi_q])
        hier = oof[oof["Week"] == week]
        r = hier["y"] - hier[metode]
        gedek.extend(((r >= q_lo) & (r <= q_hi)).tolist())
    if not gedek:
        return None, 0
    return float(np.mean(gedek)), len(gedek)


def oplei(kiekie: pd.DataFrame, databron: str = "SINTETIES") -> dict:
    """Lei op, vergelyk teen basislyne en gee 'n bundel terug wat gestoor kan word."""
    df = berei_voor(kiekie)
    if "Koers" not in df.columns:
        raise RuntimeError("Die kiekie het nie 'n Skanderings-kolom nie.")
    df = voeg_vak_hist_koers_by(df)

    laaste_week = int(df["Week"].max()) if not df.empty else 0
    bundel = {
        "weergawe": 2,
        "doel": "SKANDERINGSKOERS",
        "databron": databron,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "features": FEATURES,
        "laaste_week": laaste_week,
        "voorspel_week": laaste_week + 1,
        "rows": int(len(df)),
        "model": None,
        "interval": {"wys": False, "dekking": None, "q_lo": None, "q_hi": None},
        "metrics": {},
        "geskiedenis": df[["Week", "Sessie", "Vak", "Dag", "DagIndeks", "BeginUur", "Koers"]].copy(),
    }

    if laaste_week == 0:
        bundel["metode"] = METODE_ROOSTER
        bundel["keuse_rede"] = "Nog geen skanderingsdata nie; slegs die rooster word gewys."
        return bundel

    oof = groeiende_venster(df)
    if oof.empty:
        bundel["metode"] = METODE_LAASTE3
        bundel["keuse_rede"] = (
            f"Slegs {laaste_week} week/weke data; die model word eers vanaf "
            f"{MIN_WEKE_VIR_MODEL + 1} weke geëvalueer."
        )
        return bundel

    mae = {m: float(np.mean(np.abs(oof["y"] - oof[m])))
           for m in (METODE_MODEL, METODE_LAASTE3, METODE_DAGUUR, METODE_ROOSTER)}
    sterkste_basis = min((METODE_LAASTE3, METODE_DAGUUR), key=lambda m: mae[m])
    bs = gepaarde_bootstrap(oof["y"] - oof[sterkste_basis], oof["y"] - oof[METODE_MODEL])

    model_wen = bs["verskil"] > 0 and bs["verskil"] >= bs["se"]
    metode = METODE_MODEL if model_wen else sterkste_basis
    if model_wen:
        rede = (f"Model klop {METODE_ETIKETTE[sterkste_basis].lower()} met "
                f"{bs['verskil']:.4f} MAE (≥ 1 SE = {bs['se']:.4f}).")
    else:
        rede = (f"Model klop nie {METODE_ETIKETTE[sterkste_basis].lower()} met minstens "
                f"1 SE nie (verskil {bs['verskil']:.4f}, SE {bs['se']:.4f}); basislyn gekies.")

    dekking, n_dekking = meet_dekking(oof, metode)
    res = oof["y"] - oof[metode]
    q_lo, q_hi = (float(x) for x in np.quantile(res, INTERVAL_KWANTIELE))

    bundel.update({
        "metode": metode,
        "keuse_rede": rede,
        "interval": {
            "wys": dekking is not None and dekking >= MIN_DEKKING,
            "dekking": None if dekking is None else round(dekking, 3),
            "n_dekking": n_dekking,
            "q_lo": round(q_lo, 4),
            "q_hi": round(q_hi, 4),
        },
        "metrics": {
            "mae": {m: round(v, 4) for m, v in mae.items()},
            "sterkste_basislyn": sterkste_basis,
            "bootstrap_verskil": round(bs["verskil"], 4),
            "bootstrap_se": round(bs["se"], 4),
            "voue": int(oof["Week"].nunique()),
            "uit_voue_rye": int(len(oof)),
        },
    })

    if metode == METODE_MODEL:
        bundel["model"] = maak_model().fit(df[FEATURES], df["Koers"])
    return bundel


# --------------------------------------------------------------------------
# Voorspelling vir volgende week
# --------------------------------------------------------------------------

def voorspel_koers(bundel: dict | None, teiken: pd.DataFrame) -> tuple[np.ndarray, str]:
    """Voorspel die koers vir rooster-rye van die komende week.

    `teiken` moet reeds deur `berei_voor` gegaan het. Gee (koerse, metode) terug;
    as die model misluk val dit terug op die laaste-3-weke-basislyn.
    """
    if bundel is None or bundel.get("metode") == METODE_ROOSTER or teiken.empty:
        return np.ones(len(teiken)), METODE_ROOSTER

    hist = bundel["geskiedenis"]
    laaste_week = int(bundel["laaste_week"])
    teiken = teiken.copy()
    teiken["Week"] = laaste_week + 1
    teiken["VakHistKoers"] = vak_hist_vir_teiken(hist, teiken)

    metode = bundel.get("metode")
    if metode == METODE_MODEL and bundel.get("model") is not None:
        try:
            return _voorspel_model(bundel["model"], teiken), METODE_MODEL
        except Exception:
            metode = METODE_LAASTE3
    if metode == METODE_DAGUUR:
        return basislyn_daguur(hist, teiken), METODE_DAGUUR
    return basislyn_laaste3(hist, teiken, laaste_week), METODE_LAASTE3

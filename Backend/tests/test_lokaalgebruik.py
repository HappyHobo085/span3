"""Toetse vir die lokaalgebruikvoorspelling (skanderingskoers → vulgraad)."""

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn")

import models  # noqa: E402
from services import lokaalgebruik_model as lm  # noqa: E402
from services import lokaalgebruik_ml_service as svc  # noqa: E402


def _sintetiese_kiekie(weke=10, sessies=40, seed=0, dag_effek=0.85):
    """Sessies met 'n vaste gewoonte, semester-verval en 'n swakker Vrydag."""
    rng = np.random.default_rng(seed)
    dae = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrydag"]
    rye = []
    for s in range(sessies):
        gewoonte = float(np.clip(rng.normal(0.8, 0.1), 0.3, 1.0))
        dag = dae[s % 5]
        begin = f"{8 + (s % 8):02d}:00"
        insk = int(rng.integers(20, 120))
        for w in range(1, weke + 1):
            k = gewoonte * (1 - 0.02 * w) * (dag_effek if dag == "Vrydag" else 1.0)
            k = float(np.clip(k + rng.normal(0, 0.05), 0, 1))
            rye.append({
                "Week": w, "Sessie": s, "Vak": f"VAK{s % 12}", "Lokaal": f"L{s % 6}",
                "Dag": dag, "Begin": begin, "Inskrywing": insk, "Kapasiteit": 60,
                "Skanderings": round(insk * k),
            })
    return pd.DataFrame(rye)


def test_vak_hist_koers_gebruik_slegs_vorige_weke():
    df = lm.berei_voor(pd.DataFrame([
        {"Week": w, "Sessie": 1, "Vak": "A", "Lokaal": "L", "Dag": "Maandag",
         "Begin": "08:00", "Inskrywing": 10, "Kapasiteit": 20, "Skanderings": s}
        for w, s in [(1, 10), (2, 5), (3, 0)]
    ]))
    df = lm.voeg_vak_hist_koers_by(df).sort_values("Week")
    assert np.isnan(df["VakHistKoers"].iloc[0])           # week 1: geen verlede nie
    assert df["VakHistKoers"].iloc[1] == pytest.approx(1.0)  # slegs week 1
    assert df["VakHistKoers"].iloc[2] == pytest.approx(0.75)  # weke 1–2, nie week 3 nie


def test_engelse_dae_en_tye_word_genormaliseer():
    df = lm.berei_voor(pd.DataFrame([{
        "Week": 1, "Sessie": 1, "Vak": "A", "Lokaal": "L", "Dag": "Friday",
        "Begin": "8.30", "Inskrywing": 10, "Kapasiteit": 0,
    }]))
    assert df["Dag"].iloc[0] == "Vrydag"
    assert df["Begin"].iloc[0] == "08:30"
    assert df["BeginUur"].iloc[0] == pytest.approx(8.5)
    assert np.isnan(df["GeskeduleerdeVulgraad"].iloc[0])


def test_te_min_weke_gebruik_laaste3_en_geen_data_gebruik_rooster():
    b = lm.oplei(_sintetiese_kiekie(weke=3))
    assert b["metode"] == lm.METODE_LAASTE3
    assert b["model"] is None
    assert b["interval"]["wys"] is False
    assert b["voorspel_week"] == 4

    koerse, metode = lm.voorspel_koers(None, lm.berei_voor(_sintetiese_kiekie(weke=1)))
    assert metode == lm.METODE_ROOSTER
    assert np.all(koerse == 1.0)


def test_oplei_evalueer_teen_basislyne_en_meet_dekking():
    b = lm.oplei(_sintetiese_kiekie())
    m = b["metrics"]
    assert set(m["mae"]) == {lm.METODE_MODEL, lm.METODE_LAASTE3, lm.METODE_DAGUUR, lm.METODE_ROOSTER}
    assert m["voue"] == 10 - lm.MIN_WEKE_VIR_MODEL  # k = 4..9 voorspel 5..10
    # "Almal daag op" moet duidelik slegter wees as enige basislyn.
    assert m["mae"][lm.METODE_ROOSTER] > m["mae"][lm.METODE_LAASTE3]
    # Keuseregel: model slegs as dit ≥ 1 SE beter as die sterkste basislyn is.
    if b["metode"] == lm.METODE_MODEL:
        assert m["bootstrap_verskil"] > 0 and m["bootstrap_verskil"] >= m["bootstrap_se"]
        assert b["model"] is not None
    else:
        assert b["metode"] == m["sterkste_basislyn"]
    iv = b["interval"]
    assert iv["q_lo"] <= 0 <= iv["q_hi"]
    assert iv["dekking"] is not None and 0.5 <= iv["dekking"] <= 1.0
    assert iv["wys"] == (iv["dekking"] >= lm.MIN_DEKKING)


def test_bootstrap_kies_model_slegs_met_duidelike_voordeel():
    basis = np.full(200, 0.10)
    assert lm.gepaarde_bootstrap(basis, np.full(200, 0.05))["verskil"] == pytest.approx(0.05)
    gelyk = lm.gepaarde_bootstrap(basis, basis)
    assert gelyk["verskil"] == 0 and gelyk["se"] == 0


def _maak_rooster(db):
    kampus = models.Kampus(KAM_Naam="Leriba", KAM_Adres="x")
    db.add(kampus)
    db.flush()
    l4 = models.Lokasie(LOK_Naam="LERIBA L4", LOK_Tipe="Klaskamer", Kampus_ID=kampus.Kampus_ID, LOK_Kapasiteit=60)
    db.add(l4)
    db.flush()
    mod = models.Module(MOD_Kode="VAK1", MOD_Naam="Vak een")
    db.add(mod)
    db.flush()
    klasse = [
        models.Klas(Module_ID=mod.Module_ID, Lokasie_ID=l4.Lokasie_ID, KLA_Lokaal="LERIBA L4",
                    KLA_Dag="Maandag", KLA_Begin_Tyd="08:00", KLA_Eind_Tyd="08:50"),
        models.Klas(Module_ID=mod.Module_ID, Lokasie_ID=l4.Lokasie_ID, KLA_Lokaal="LERIBA L4",
                    KLA_Dag="Maandag", KLA_Begin_Tyd="08:30", KLA_Eind_Tyd="09:20"),
    ]
    db.add_all(klasse)
    db.flush()
    return kampus, klasse


def test_diens_sonder_model_wys_rooster_en_vlag_konflik(db, monkeypatch, tmp_path):
    monkeypatch.setattr(svc, "MODEL_PATH", tmp_path / "geen.joblib")
    monkeypatch.setattr(svc, "inskrywings_per_klas", lambda _db, ks: {k.Klas_ID: 72 for k in ks})
    kampus, _ = _maak_rooster(db)

    data = svc.voorspel_vir_kampus(db, kampus.Kampus_ID)
    assert data["metode"] == lm.METODE_ROOSTER
    g = data["gleuwe"][0]
    assert g["inskrywing"] == 72 and g["kapasiteit"] == 60
    assert g["geskeduleerde_vulgraad"] == pytest.approx(1.2)
    assert g["vulgraad"] == pytest.approx(1.2)      # nie afgekap nie
    assert g["oor_kapasiteit"] is True
    assert all(x["konflik"] for x in data["gleuwe"])  # 08:00–08:50 en 08:30–09:20
    assert svc.voorspel_vir_kampus(db, kampus.Kampus_ID, "Tuesday")["gleuwe"] == []


def test_diens_met_opgeleide_bundel(db, monkeypatch, tmp_path):
    import joblib

    kampus, klasse = _maak_rooster(db)
    kiekie = _sintetiese_kiekie()
    kiekie.loc[kiekie["Sessie"] == 0, "Sessie"] = klasse[0].Klas_ID
    pad = tmp_path / "m.joblib"
    joblib.dump(lm.oplei(kiekie), pad)
    monkeypatch.setattr(svc, "MODEL_PATH", pad)
    monkeypatch.setattr(svc, "_bundle", None)
    monkeypatch.setattr(svc, "inskrywings_per_klas", lambda _db, ks: {k.Klas_ID: 72 for k in ks})

    data = svc.voorspel_vir_kampus(db, kampus.Kampus_ID)
    assert data["voorspel_week"] == 11
    assert data["metode"] != lm.METODE_ROOSTER
    for g in data["gleuwe"]:
        assert 0 <= g["koers"] <= 1
        assert g["verwagte_getal"] == round(g["koers"] * 72)
        assert g["vulgraad"] == pytest.approx(round(g["koers"] * 72 / 60, 3))
        if data["interval"]["wys"]:
            assert g["reeks"]["koers_laag"] <= g["koers"] <= g["reeks"]["koers_hoog"]
            assert g["kan_oorloop"] == (g["reeks"]["vulgraad_hoog"] > 1)
        else:
            assert g["reeks"] is None

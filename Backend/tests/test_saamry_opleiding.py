"""Toetse vir die Saamry-model se opleiding uit kampushek-logs."""

from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn")

import models  # noqa: E402
from scripts import aankoms_data_uit_logs as onttrek  # noqa: E402
from scripts import train_aankoms_model as tam  # noqa: E402
from services import ml_service  # noqa: E402

NOU = datetime(2026, 10, 12, 12, 0)  # Maandag


def _gebruiker(db, rol, idx, voorstad, kampus_id=None, rol_tipe="BEIDE", koshuis=False):
    u = models.Gebruikers(
        GEB_Naam="Toets", GEB_Van=f"Ry{idx}", GEB_ID_Nommer=f"90010150000{idx:02d}"[-13:],
        GEB_Epos=f"ry{idx}@example.com", GEB_Wagwoord="hash", Rol_ID=rol.Rol_ID, Is_Aktief=True,
    )
    db.add(u)
    db.flush()
    db.add(models.Student(Gebruiker_ID=u.Gebruiker_ID, STU_Nommer=f"S{idx:03d}", STU_Is_Koshuis=koshuis))
    db.add(models.SaamryProfiel(Gebruiker_ID=u.Gebruiker_ID, Rol_Tipe=rol_tipe,
                                Voorstad=voorstad, Kampus_ID=kampus_id))
    db.flush()
    return u


def _log(db, gebruiker, lokasie, utc, rigting="IN"):
    db.add(models.ToegangsLogs(Gebruiker_ID=gebruiker.Gebruiker_ID, Lokasie_ID=lokasie.Lokasie_ID,
                               TOE_Tydstempel=utc, TOE_Rigting=rigting, TOE_Metode="NFC"))


def test_onttrekker_bou_offsets_uit_eerste_hekskandering(db):
    rol = models.Rolle(ROL_Naam="Student")
    db.add(rol)
    kampus, ander = models.Kampus(KAM_Naam="Pretoria"), models.Kampus(KAM_Naam="Ander")
    db.add_all([kampus, ander])
    db.flush()
    hek = models.Lokasie(LOK_Naam="Hoofhek", LOK_Tipe="Kampus", Kampus_ID=kampus.Kampus_ID)
    ander_hek = models.Lokasie(LOK_Naam="Anderhek", LOK_Tipe="Kampus", Kampus_ID=ander.Kampus_ID)
    koshuis = models.Lokasie(LOK_Naam="Koshuis", LOK_Tipe="Koshuis", Kampus_ID=kampus.Kampus_ID)
    klaslokaal = models.Lokasie(LOK_Naam="L1", LOK_Tipe="Klaskamer", Kampus_ID=kampus.Kampus_ID)
    mod = models.Module(MOD_Kode="SR101")
    db.add_all([hek, ander_hek, koshuis, klaslokaal, mod])
    db.flush()
    klas = models.Klas(Module_ID=mod.Module_ID, Lokasie_ID=klaslokaal.Lokasie_ID, KLA_Lokaal="L1",
                       KLA_Dag="Maandag", KLA_Begin_Tyd="08:00", KLA_Eind_Tyd="09:00")
    laat = models.Klas(Module_ID=mod.Module_ID, Lokasie_ID=klaslokaal.Lokasie_ID, KLA_Lokaal="L1",
                       KLA_Dag="Maandag", KLA_Begin_Tyd="10:00", KLA_Eind_Tyd="11:00")
    db.add_all([klas, laat])
    db.flush()

    anna = _gebruiker(db, rol, 1, "Brummeria", kampus.Kampus_ID, "BESTUURDER", koshuis=True)
    for k in (klas, laat):
        db.add(models.Student_Klas(Gebruiker_ID=anna.Gebruiker_ID, Klas_ID=k.Klas_ID))
    # SA = UTC+2. Twee Maandae: 07:40 en 07:30 eerste IN → offsets 20 en 30 → mediaan 25.
    _log(db, anna, hek, datetime(2026, 10, 5, 5, 40))
    _log(db, anna, hek, datetime(2026, 10, 5, 9, 0))          # later dieselfde dag: nie eerste nie
    _log(db, anna, hek, datetime(2026, 9, 28, 5, 30))
    _log(db, anna, koshuis, datetime(2026, 9, 21, 4, 0))      # nie 'n kampushek nie
    _log(db, anna, ander_hek, datetime(2026, 9, 14, 5, 0))    # ander kampus as Saamry-profiel
    _log(db, anna, hek, datetime(2026, 9, 7, 13, 0))          # 15:00: ver ná eerste klas, uitgesluit
    _log(db, anna, hek, datetime(2026, 10, 10, 5, 0))         # Saterdag
    _log(db, anna, hek, datetime(2026, 5, 4, 5, 0))           # buite die logvenster
    _log(db, anna, hek, datetime(2026, 10, 5, 4, 0), "UIT")   # UIT tel nie

    # Persoon sonder klasse lewer geen rye nie.
    piet = _gebruiker(db, rol, 2, "Annlin")
    _log(db, piet, hek, datetime(2026, 10, 5, 5, 0))
    db.commit()

    df = onttrek.bou_opleidingsdata(db, nou=NOU)
    assert len(df) == 1
    ry = df.iloc[0]
    assert ry["groep"] == anna.Gebruiker_ID
    assert ry["klas_begin_minuut"] == 480
    assert ry["offset_tipies"] == 25
    assert ry["rol"] == "BESTUURDER" and ry["is_koshuis"] == 1 and ry["voorstad"] == "Brummeria"

    voorbereid = tam.berei_voor(df)
    assert voorbereid["kluster"].iloc[0] == "oos"


def _sintetiese_logdata(persone=60, seed=0):
    """Oos kom ~35 min vroeg, ander klusters ~15; elke persoon het tot 5 weeksdae."""
    rng = np.random.default_rng(seed)
    voorstede = {"oos": "Brummeria", "noord": "Annlin", "centurion": "Amberfield"}
    rye = []
    for p in range(persone):
        kl = list(voorstede)[p % 3]
        for d in range(int(rng.integers(2, 6))):
            rye.append({
                "groep": p, "klas_begin_minuut": int(rng.choice([450, 480, 540, 600])),
                "voorstad": voorstede[kl], "rol": ["BESTUURDER", "PASSASIER", "BEIDE"][p % 3],
                "is_koshuis": 0,
                "offset_tipies": float(np.clip(rng.normal(35 if kl == "oos" else 15, 5), 0, 60)),
            })
    return pd.DataFrame(rye)


@pytest.fixture
def model_pad(tmp_path, monkeypatch):
    pad = tmp_path / "aankoms_model.joblib"
    joblib.dump({"type": "MEDIAAN", "rule": "GLOBAL", "global_median": 30.0, "sigma": 22.2,
                 "known_clusters": []}, pad)
    monkeypatch.setattr(tam, "MODEL_PATH", str(pad))
    monkeypatch.setattr(tam, "DATA_PATH", str(tmp_path / "bestaan_nie.csv"))
    werklike = Path(tam.__file__).resolve().parent.parent / "ml_models" / "aankoms_model.joblib"
    voor = werklike.read_bytes() if werklike.exists() else None
    yield pad
    # Die toetse mag nooit die gecommitte model oorskryf nie.
    assert (werklike.read_bytes() if werklike.exists() else None) == voor


def test_oplei_uit_logs_vervang_model_en_ml_service_gebruik_dit(model_pad, monkeypatch):
    monkeypatch.setattr(onttrek, "bou_opleidingsdata", lambda: _sintetiese_logdata())
    assert tam.main(["--van-logs"]) == 0

    nuut = joblib.load(model_pad)
    assert nuut["type"] in {"ML", "MEDIAAN"}
    assert "oos" in nuut["known_clusters"]
    # Geen persoonlike ID's in die gestoorde model nie.
    assert "groep" not in str({k: v for k, v in nuut.items() if k not in ("q10", "q50", "q90")})

    monkeypatch.setattr(ml_service, "MODEL_PATH", str(model_pad))
    monkeypatch.setattr(ml_service, "_model", None)
    monkeypatch.setattr(ml_service, "_model_loaded", False)
    monkeypatch.setattr(ml_service, "_model_load_failed", False)
    ml_service._voorspel_met_kas.cache_clear()
    try:
        oos, _, bron = ml_service.voorspel_aankomstyd_offset(480, "oos", "BEIDE", 0)
        noord, _, _ = ml_service.voorspel_aankomstyd_offset(480, "noord", "BEIDE", 0)
        assert bron in {"ML_MODEL", "MEDIAAN"}
        assert oos > noord  # die model het die verskil tussen klusters geleer
    finally:
        ml_service._voorspel_met_kas.cache_clear()


def test_te_min_data_hou_bestaande_model(model_pad, monkeypatch):
    voor = model_pad.read_bytes()
    monkeypatch.setattr(onttrek, "bou_opleidingsdata", lambda: _sintetiese_logdata(persone=5))
    assert tam.main(["--van-logs"]) == 0
    assert model_pad.read_bytes() == voor


def test_ongeldige_model_vervang_nie_die_bestaande_nie(model_pad):
    voor = model_pad.read_bytes()
    with pytest.raises(ValueError):
        tam.stoor_veilig({"type": "MEDIAAN", "global_median": float("nan")}, str(model_pad))
    assert model_pad.read_bytes() == voor
    assert not (model_pad.parent / "aankoms_model.joblib.nuut").exists()


def test_groep_bewuste_voue_hou_persone_apart():
    df = tam.berei_voor(_sintetiese_logdata())
    groepe = df["groep"].to_numpy()
    for _, oplei, toets in tam._voue(df, groepe):
        assert not set(groepe[oplei]) & set(groepe[toets])

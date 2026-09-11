"""TDD Eenheidstoetse vir Saamry Versoenbaarheidsalgoritme (compatibiliteit_service.py)."""

import pytest
from services.compatibiliteit_service import (
    DagSkedule,
    StudentSaamryData,
    bereken_saamry_versoenbaarheid,
    bereken_tyd_telling,
    bereken_voorstad_ooreenstemming,
    DAE_VAN_DIE_WEEK,
)


def _maak_standaard_skedule(
    aankoms_min: int = 465,  # 07:45
    vertrek_min: int = 990,  # 16:30
    aktiewe_dae: list = None,
    monsters: int = 10,
    afwyking: float = 5.0,
) -> dict[str, DagSkedule]:
    if aktiewe_dae is None:
        aktiewe_dae = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrydag"]

    skedule = {}
    for dag in DAE_VAN_DIE_WEEK:
        is_aktief = dag in aktiewe_dae
        skedule[dag] = DagSkedule(
            dag_naam=dag,
            het_aktiwiteit=is_aktief,
            aankoms_minuut=aankoms_min if is_aktief else None,
            vertrek_minuut=vertrek_min if is_aktief else None,
            aantal_monsters=monsters if is_aktief else 0,
            standaardafwyking_min=afwyking if is_aktief else 0.0,
        )
    return skedule


def test_perfekte_pasmaat():
    """Toets perfekte passing: dieselfde voorstad, tye en versoenbare rolle."""
    student_a = StudentSaamryData(
        gebruiker_id=1,
        naam="Jaco",
        van="Oosthuizen",
        saamry_rol="BESTUURDER",
        geslag="MANLIK",
        geslag_voorkeur="ENIGE",
        voorstad="Centurion",
        kampus_id=1,
        skedule_per_dag=_maak_standaard_skedule(465, 990),
    )
    kandidaat = StudentSaamryData(
        gebruiker_id=2,
        naam="Dirk",
        van="Botha",
        saamry_rol="PASSASIER",
        geslag="MANLIK",
        geslag_voorkeur="ENIGE",
        voorstad="Centurion",
        kampus_id=1,
        skedule_per_dag=_maak_standaard_skedule(465, 990),
    )

    resultaat = bereken_saamry_versoenbaarheid(student_a, kandidaat)

    assert resultaat.is_geskik is True
    assert resultaat.totale_telling >= 95.0
    assert resultaat.gehalte == "UITSTEKEND"
    assert len(resultaat.gemeenskaplike_dae) == 5
    assert resultaat.faktore["rol_telling"] == 100.0
    assert resultaat.faktore["ligging_telling"] == 100.0
    assert resultaat.faktore["tyd_telling"] == 100.0


def test_per_dag_gedeeltelike_oorvleueling_geen_straf():
    """Toets dat dae waarop slegs een student reis, nie die gemeenskaplike dae penaliseer nie."""
    # Student A is slegs Maandag en Woensdag op kampus
    skedule_a = _maak_standaard_skedule(470, 990, aktiewe_dae=["Maandag", "Woensdag"])
    # Student B is Maandag, Woensdag en Vrydag op kampus
    skedule_b = _maak_standaard_skedule(475, 1000, aktiewe_dae=["Maandag", "Woensdag", "Vrydag"])

    student_a = StudentSaamryData(
        gebruiker_id=1,
        naam="Jaco",
        van="Oosthuizen",
        saamry_rol="BESTUURDER",
        geslag="MANLIK",
        geslag_voorkeur="ENIGE",
        voorstad="Centurion",
        kampus_id=1,
        skedule_per_dag=skedule_a,
    )
    student_b = StudentSaamryData(
        gebruiker_id=2,
        naam="Pieter",
        van="Smit",
        saamry_rol="PASSASIER",
        geslag="MANLIK",
        geslag_voorkeur="ENIGE",
        voorstad="Centurion",
        kampus_id=1,
        skedule_per_dag=skedule_b,
    )

    resultaat = bereken_saamry_versoenbaarheid(student_a, student_b)

    assert resultaat.is_geskik is True
    assert "Maandag" in resultaat.gemeenskaplike_dae
    assert "Woensdag" in resultaat.gemeenskaplike_dae
    assert "Vrydag" not in resultaat.gemeenskaplike_dae
    assert len(resultaat.gemeenskaplike_dae) == 2
    # Telling moet steeds baie hoog wees omdat die dae wat hulle deel byna presies ooreenstem
    assert resultaat.totale_telling >= 85.0
    assert "Maandag" in resultaat.per_dag_afbreking
    assert "Woensdag" in resultaat.per_dag_afbreking


def test_rol_botsing_passasier_passasier():
    """Twee passasiers kan mekaar nie ry nie — harde uitsluiting."""
    student_a = StudentSaamryData(
        gebruiker_id=1,
        naam="Student",
        van="Een",
        saamry_rol="PASSASIER",
        geslag="MANLIK",
        geslag_voorkeur="ENIGE",
        voorstad="Centurion",
        kampus_id=1,
        skedule_per_dag=_maak_standaard_skedule(),
    )
    student_b = StudentSaamryData(
        gebruiker_id=2,
        naam="Student",
        van="Twee",
        saamry_rol="PASSASIER",
        geslag="MANLIK",
        geslag_voorkeur="ENIGE",
        voorstad="Centurion",
        kampus_id=1,
        skedule_per_dag=_maak_standaard_skedule(),
    )

    resultaat = bereken_saamry_versoenbaarheid(student_a, student_b)

    assert resultaat.is_geskik is False
    assert resultaat.totale_telling == 0.0
    assert resultaat.faktore["rol_telling"] == 0.0


def test_geslag_voorkeur_harde_uitsluiting():
    """As 'n student 'DIESELFDE' geslag versoek en die kandidaat verskil, moet telling 0 wees."""
    dame = StudentSaamryData(
        gebruiker_id=1,
        naam="Anri",
        van="Pretorius",
        saamry_rol="PASSASIER",
        geslag="VROULIK",
        geslag_voorkeur="DIESELFDE",
        voorstad="Pretoria Oos",
        kampus_id=1,
        skedule_per_dag=_maak_standaard_skedule(),
    )
    man = StudentSaamryData(
        gebruiker_id=2,
        naam="Kobus",
        van="Kruger",
        saamry_rol="BESTUURDER",
        geslag="MANLIK",
        geslag_voorkeur="ENIGE",
        voorstad="Pretoria Oos",
        kampus_id=1,
        skedule_per_dag=_maak_standaard_skedule(),
    )

    resultaat = bereken_saamry_versoenbaarheid(dame, man)

    assert resultaat.is_geskik is False
    assert resultaat.totale_telling == 0.0


def test_geslag_voorkeur_aanvaar_dieselfde():
    """Twee dames met DIESELFDE geslagsvoorkeur slaag die filter."""
    dame1 = StudentSaamryData(
        gebruiker_id=1,
        naam="Anri",
        van="Pretorius",
        saamry_rol="PASSASIER",
        geslag="VROULIK",
        geslag_voorkeur="DIESELFDE",
        voorstad="Pretoria Oos",
        kampus_id=1,
        skedule_per_dag=_maak_standaard_skedule(),
    )
    dame2 = StudentSaamryData(
        gebruiker_id=2,
        naam="Carla",
        van="Meyer",
        saamry_rol="BESTUURDER",
        geslag="VROULIK",
        geslag_voorkeur="DIESELFDE",
        voorstad="Pretoria Oos",
        kampus_id=1,
        skedule_per_dag=_maak_standaard_skedule(),
    )

    resultaat = bereken_saamry_versoenbaarheid(dame1, dame2)

    assert resultaat.is_geskik is True
    assert resultaat.totale_telling >= 90.0


def test_tyd_verval_sensitiwiteit():
    """Toets die lineêre stuksgewyse verval van tydverskille."""
    assert bereken_tyd_telling(0) == 100.0
    assert bereken_tyd_telling(10) == 100.0
    assert 75.0 <= bereken_tyd_telling(20) <= 85.0
    assert bereken_tyd_telling(30) == 60.0
    assert 20.0 <= bereken_tyd_telling(50) <= 30.0
    assert bereken_tyd_telling(60) == 10.0
    assert bereken_tyd_telling(61) == 0.0
    assert bereken_tyd_telling(120) == 0.0


def test_verskillende_kampusse():
    """As studente na verskillende kampusse reis, is passing 0."""
    student_a = StudentSaamryData(
        gebruiker_id=1,
        naam="Jaco",
        van="Oosthuizen",
        saamry_rol="BESTUURDER",
        geslag="MANLIK",
        geslag_voorkeur="ENIGE",
        voorstad="Centurion",
        kampus_id=1,
        skedule_per_dag=_maak_standaard_skedule(),
    )
    student_b = StudentSaamryData(
        gebruiker_id=2,
        naam="Dirk",
        van="Botha",
        saamry_rol="PASSASIER",
        geslag="MANLIK",
        geslag_voorkeur="ENIGE",
        voorstad="Centurion",
        kampus_id=2,  # Ander kampus!
        skedule_per_dag=_maak_standaard_skedule(),
    )

    resultaat = bereken_saamry_versoenbaarheid(student_a, student_b)

    assert resultaat.is_geskik is False
    assert resultaat.totale_telling == 0.0
    assert resultaat.faktore["ligging_telling"] == 0.0


def test_ligging_ooreenstemming_sones():
    """Toets voorstadooreenstemming en klusterings."""
    assert bereken_voorstad_ooreenstemming("Centurion", "Centurion") == 100.0
    assert bereken_voorstad_ooreenstemming("centurion", "CENTURION ") == 100.0
    assert bereken_voorstad_ooreenstemming("Centurion", "Pretoria Oos") in (50.0, 75.0, 80.0)
    assert bereken_voorstad_ooreenstemming("Centurion", "Pretoria Noord") <= 30.0


def test_onvoldoende_monsters_vertrouestraf():
    """Toets dat te min monsters lei tot 'n laer betroubaarheidtelling."""
    skedule_min_monsters = _maak_standaard_skedule(monsters=1)
    student_a = StudentSaamryData(
        gebruiker_id=1,
        naam="Nuut",
        van="Student",
        saamry_rol="BESTUURDER",
        geslag="MANLIK",
        geslag_voorkeur="ENIGE",
        voorstad="Centurion",
        kampus_id=1,
        skedule_per_dag=skedule_min_monsters,
    )
    student_b = StudentSaamryData(
        gebruiker_id=2,
        naam="Dirk",
        van="Botha",
        saamry_rol="PASSASIER",
        geslag="MANLIK",
        geslag_voorkeur="ENIGE",
        voorstad="Centurion",
        kampus_id=1,
        skedule_per_dag=_maak_standaard_skedule(monsters=15),
    )

    resultaat = bereken_saamry_versoenbaarheid(student_a, student_b)

    assert resultaat.faktore["betroubaarheid_telling"] < 90.0


def test_geen_gemeenskaplike_dae():
    """As daar geen oorvleueling in klastye of dae is nie."""
    skedule_a = _maak_standaard_skedule(aktiewe_dae=["Maandag", "Woensdag"])
    skedule_b = _maak_standaard_skedule(aktiewe_dae=["Dinsdag", "Donderdag"])

    student_a = StudentSaamryData(
        gebruiker_id=1,
        naam="Jaco",
        van="Oosthuizen",
        saamry_rol="BESTUURDER",
        geslag="MANLIK",
        geslag_voorkeur="ENIGE",
        voorstad="Centurion",
        kampus_id=1,
        skedule_per_dag=skedule_a,
    )
    student_b = StudentSaamryData(
        gebruiker_id=2,
        naam="Dirk",
        van="Botha",
        saamry_rol="PASSASIER",
        geslag="MANLIK",
        geslag_voorkeur="ENIGE",
        voorstad="Centurion",
        kampus_id=1,
        skedule_per_dag=skedule_b,
    )

    resultaat = bereken_saamry_versoenbaarheid(student_a, student_b)

    assert resultaat.is_geskik is False
    assert resultaat.totale_telling == 0.0
    assert resultaat.gemeenskaplike_dae == []


def test_konsekwente_tyd_vs_wisselvallige_tyd():
    """Twee studente met 'n 5 min verskil en lae variansie is beter as 'n 5 min verskil met hoë variansie."""
    # Scenario 1: Baie konsekwent
    skedule_k_kons = _maak_standaard_skedule(465, 990, afwyking=1.0)
    student_a_kons = StudentSaamryData(
        gebruiker_id=1, naam="A", van="A", saamry_rol="BESTUURDER", kampus_id=1,
        skedule_per_dag=_maak_standaard_skedule(460, 990, afwyking=1.0)
    )
    student_b_kons = StudentSaamryData(
        gebruiker_id=2, naam="B", van="B", saamry_rol="PASSASIER", kampus_id=1,
        skedule_per_dag=skedule_k_kons
    )
    res_kons = bereken_saamry_versoenbaarheid(student_a_kons, student_b_kons)

    # Scenario 2: Baie wisselvallig (groot standaardafwyking)
    skedule_k_wissel = _maak_standaard_skedule(465, 990, afwyking=35.0)
    student_a_wissel = StudentSaamryData(
        gebruiker_id=1, naam="A", van="A", saamry_rol="BESTUURDER", kampus_id=1,
        skedule_per_dag=_maak_standaard_skedule(460, 990, afwyking=35.0)
    )
    student_b_wissel = StudentSaamryData(
        gebruiker_id=3, naam="C", van="C", saamry_rol="PASSASIER", kampus_id=1,
        skedule_per_dag=skedule_k_wissel
    )
    res_wissel = bereken_saamry_versoenbaarheid(student_a_wissel, student_b_wissel)

    # Konsekwente passing moet 'n hoër tyd telling hê weens 'n baie kleiner effektiewe verskil.
    assert res_kons.faktore["tyd_telling"] > res_wissel.faktore["tyd_telling"]


def test_klein_steekproef_straf():
    """As studente 'n lae aantal logs het, moet die betroubaarheid telling drasties daal."""
    skedule_1 = _maak_standaard_skedule(monsters=1)
    student_a = StudentSaamryData(
        gebruiker_id=1, naam="A", van="A", saamry_rol="BESTUURDER", kampus_id=1,
        skedule_per_dag=skedule_1
    )
    student_b = StudentSaamryData(
        gebruiker_id=2, naam="B", van="B", saamry_rol="PASSASIER", kampus_id=1,
        skedule_per_dag=skedule_1
    )
    res_min = bereken_saamry_versoenbaarheid(student_a, student_b)

    skedule_20 = _maak_standaard_skedule(monsters=20)
    student_c = StudentSaamryData(
        gebruiker_id=3, naam="C", van="C", saamry_rol="BESTUURDER", kampus_id=1,
        skedule_per_dag=skedule_20
    )
    student_d = StudentSaamryData(
        gebruiker_id=4, naam="D", van="D", saamry_rol="PASSASIER", kampus_id=1,
        skedule_per_dag=skedule_20
    )
    res_baie = bereken_saamry_versoenbaarheid(student_c, student_d)

    assert res_min.faktore["betroubaarheid_telling"] < res_baie.faktore["betroubaarheid_telling"]
    assert res_min.faktore["betroubaarheid_telling"] <= 50.0  # Steekproef is slegs 1


def test_nul_dae_oorvleueling_zero_division():
    """Toets dat zero division hanteer word wanneer studente na dieselfde kampus ry, maar 0 dae deel."""
    skedule_a = _maak_standaard_skedule(aktiewe_dae=["Maandag"])
    skedule_b = _maak_standaard_skedule(aktiewe_dae=["Vrydag"])

    student_a = StudentSaamryData(
        gebruiker_id=1, naam="A", van="A", saamry_rol="BESTUURDER", kampus_id=1,
        skedule_per_dag=skedule_a
    )
    student_b = StudentSaamryData(
        gebruiker_id=2, naam="B", van="B", saamry_rol="PASSASIER", kampus_id=1,
        skedule_per_dag=skedule_b
    )
    # Behoort nie the crash nie
    resultaat = bereken_saamry_versoenbaarheid(student_a, student_b)
    
    assert resultaat.is_geskik is False
    assert resultaat.totale_telling == 0.0



def test_herlei_geslag_uit_id():
    """Toets die geslag-herleiding vanaf 'n SA ID-nommer."""
    from services.compatibiliteit_service import herlei_geslag_uit_id

    assert herlei_geslag_uit_id("0205155012088") == "MANLIK"
    assert herlei_geslag_uit_id("0307220034081") == "VROULIK"
    assert herlei_geslag_uit_id("kort") is None
    assert herlei_geslag_uit_id(None) is None


def test_db_saamry_profiel_en_voorstelle_integrasie(db, maak_gebruiker):
    """Toets Saamry profiel CRUD en voorstelle eindpunte teen 'n in-geheue databasis."""
    import models
    import schemas
    from routers import saamry

    # Skep twee studente
    student_a = maak_gebruiker("Student")
    student_b = maak_gebruiker("Student")

    # Voeg Student sub-rekords by (vereis vir _require_saamry_user)
    db.add(models.Student(Gebruiker_ID=student_a.Gebruiker_ID, STU_Nommer="STU001"))
    db.add(models.Student(Gebruiker_ID=student_b.Gebruiker_ID, STU_Nommer="STU002"))

    # Skep 'n kampus
    kampus = models.Kampus(KAM_Naam="Akademia Centurion", KAM_Adres="Gerhard Moerdyk")
    db.add(kampus)
    db.commit()

    # 1. Toets kry_saamry_profiel (skep outomaties verstek)
    profiel_a_resp = saamry.kry_saamry_profiel(db=db, current_user=student_a)
    assert profiel_a_resp.sukses is True
    assert profiel_a_resp.data.Rol_Tipe == "BEIDE"

    # 2. Toets werk_saamry_profiel_by
    update_payload = schemas.SaamryProfielUpdate(
        rol_tipe="BESTUURDER",
        voorstad="Centurion",
        geslag="MANLIK",
        geslag_voorkeur="ENIGE",
        kampus_id=kampus.Kampus_ID,
    )
    gewysigde_a = saamry.werk_saamry_profiel_by(payload=update_payload, db=db, current_user=student_a)
    assert gewysigde_a.sukses is True
    assert gewysigde_a.data.Rol_Tipe == "BESTUURDER"
    assert gewysigde_a.data.Voorstad == "Centurion"

    # Stel student B se profiel op
    update_b = schemas.SaamryProfielUpdate(
        rol_tipe="PASSASIER",
        voorstad="Centurion",
        geslag="MANLIK",
        geslag_voorkeur="ENIGE",
        kampus_id=kampus.Kampus_ID,
    )
    saamry.werk_saamry_profiel_by(payload=update_b, db=db, current_user=student_b)

    # Voeg klasse by vir beide studente op Maandag 08:00 - 16:00
    module = models.Module(MOD_Kode="INF370", MOD_Naam="Projek")
    db.add(module)
    db.flush()

    klas = models.Klas(
        Module_ID=module.Module_ID,
        KLA_Lokaal="Lokaal 101",
        KLA_Dag="Maandag",
        KLA_Begin_Tyd="08:00",
        KLA_Eind_Tyd="16:00",
    )
    db.add(klas)
    db.flush()

    db.add(models.Student_Klas(Gebruiker_ID=student_a.Gebruiker_ID, Klas_ID=klas.Klas_ID))
    db.add(models.Student_Klas(Gebruiker_ID=student_b.Gebruiker_ID, Klas_ID=klas.Klas_ID))
    db.commit()

    # 3. Toets kry_saamry_voorstelle
    voorstelle_resp = saamry.kry_saamry_voorstelle(limiet=10, min_telling=40.0, db=db, current_user=student_a)
    assert voorstelle_resp.sukses is True
    voorstelle = voorstelle_resp.data["voorstelle"]
    assert len(voorstelle) >= 1
    beste_kandidaat = voorstelle[0]
    assert beste_kandidaat["gebruiker_id"] == student_b.Gebruiker_ID
    assert beste_kandidaat["totale_telling"] >= 70.0
    assert "Maandag" in beste_kandidaat["gemeenskaplike_dae"]

    # 4. Toets kry_kandidaat_versoenbaarheid
    detail_resp = saamry.kry_kandidaat_versoenbaarheid(
        kandidaat_id=student_b.Gebruiker_ID,
        db=db,
        current_user=student_a,
    )
    assert detail_resp.sukses is True
    assert detail_resp.data["is_geskik"] is True
    assert detail_resp.data["per_dag_afbreking"]["Maandag"]["aankoms_geskat"] == "07:45"


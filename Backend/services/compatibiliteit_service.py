import re
"""Suiwer wiskundige en logiese diens vir Saamry Versoenbaarheid.

Hierdie module bevat slegs suiwer funksies (pure functions) sonder databasis-navrae,
wat onafhanklik getoets kan word.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from services.ml_service import voorspel_aankomstyd_offset
import math


DAE_VAN_DIE_WEEK = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrydag"]


@dataclass(frozen=True)
class DagSkedule:
    dag_naam: str
    het_aktiwiteit: bool = False
    aankoms_minuut: Optional[int] = None
    vertrek_minuut: Optional[int] = None
    aantal_monsters: int = 0
    standaardafwyking_min: float = 0.0
    bron: str = "LOGS"


@dataclass(frozen=True)
class StudentSaamryData:
    gebruiker_id: int
    naam: str
    van: str
    saamry_rol: str = "BEIDE"  # "BESTUURDER", "PASSASIER", "BEIDE"
    geslag: Optional[str] = None  # "MANLIK", "VROULIK", "ANDER"
    geslag_voorkeur: str = "ENIGE"  # "ENIGE", "DIESELFDE"
    voorstad: Optional[str] = None
    kampus_id: Optional[int] = None
    foto_url: Optional[str] = None
    skedule_per_dag: Dict[str, DagSkedule] = field(default_factory=dict)


@dataclass
class VersoenbaarheidResultaat:
    kandidaat_id: int
    totale_telling: float
    is_geskik: bool
    gehalte: str  # "UITSTEKEND", "GOED", "MATIG", "SWAK", "ONVERSOENBAAR"
    gemeenskaplike_dae: List[str]
    beste_dag: Optional[str]
    faktore: Dict[str, float]
    per_dag_afbreking: Dict[str, dict]
    aanbeveling_teks: str


# ---------------------------------------------------------------------------
# Tyd Helpers
# ---------------------------------------------------------------------------

def minuut_na_tydstring(minuut: Optional[int]) -> Optional[str]:
    """Skakel minute vanaf middernag (bv. 475) om na '07:55'."""
    if minuut is None:
        return None
    ure = (minuut // 60) % 24
    mins = minuut % 60
    return f"{ure:02d}:{mins:02d}"


def bereken_tyd_telling(verskil_min: float) -> float:
    """Lineêre stuksgewyse vervalfunksie vir tydverskil tussen twee persone.

    - 0..10 min: 100%
    - 10..30 min: daal lineêr van 100% na 60%
    - 30..60 min: daal lineêr van 60% na 10%
    - > 60 min: 0%
    """
    v = abs(float(verskil_min))
    if v <= 10.0:
        return 100.0
    if v <= 30.0:
        # lineêr van 100 by 10 na 60 by 30
        return round(100.0 - ((v - 10.0) / 20.0) * 40.0, 1)
    if v <= 60.0:
        # lineêr van 60 by 30 na 10 by 60
        return round(60.0 - ((v - 30.0) / 30.0) * 50.0, 1)
    return 0.0


# ---------------------------------------------------------------------------
# Geografiese en Voorstad Helpers
# ---------------------------------------------------------------------------

# Bekende voorstede en hul klusters in Pretoria / Tshwane omgewing
OU_VOORSTAD_KLUSTERS = {
    "oos": {
        "pretoria oos", "pretoria-oos", "garsfontein", "faerie glen", "menlyn",
        "lynnwood", "moreletapark", "silver lakes", "wapadrand", "woodhill",
        "constantia park", "elarduspark", "wingate park", "erasmuskloof",
    },
    "centurion": {
        "centurion", "lyttelton", "irene", "midstream", "eldoraigne",
        "rooihuiskraal", "wierdapark", "clubview", "die hoewes", "erasmia",
        "heuweloord", "amberfield", "raslouw",
    },
    "sentraal": {
        "hatfield", "brooklyn", "muckleneuk", "sunnyside", "arcadia",
        "pretoria sentraal", "pretoria-sentraal", "bailey's muckleneuk",
    },
    "moot": {
        "die moot", "moot", "gezinia", "villieria", "rietfontein",
        "wonderboom-suid", "waverley", "queenswood",
    },
    "noord": {
        "pretoria noord", "pretoria-noord", "wonderboom", "montana", "annlin",
        "sinoville", "magalieskruin", "doornpoort", "orchards", "rosslyn",
        "karenpark", "theresapark",
    },
    "midrand": {
        "midrand", "kyalami", "halfway house", "waterfall", "carlswald",
    },
}

VOORSTAD_KLUSTERS = {}
for k, vs in OU_VOORSTAD_KLUSTERS.items():
    VOORSTAD_KLUSTERS[k] = set(vs)

# Voeg nuwe voorstede by (samesmelting)
NEW_SUBURBS = {
    "oos": [
        "alphen park", "ashlea gardens", "brummeria", "die wilgers",
        "equestria", "erasmusrand", "hazelwood", "lynnwood glen", "lynnwood manor",
        "lynnwood park", "lynnwood ridge", "maroelana", "menlyn maine",
        "menlopark", "meyerspark", "monumentpark", "mooikloof", "mooikloof ridge",
        "murrayfield", "newlands", "rietvalleirand", "sterrewag", "waterkloof",
        "waterkloof glen", "waterkloof heights", "waterkloof park", "waterkloofrif",
        "weavind park", "willow acres"
    ],
    "centurion": [
        "blue valley golf estate", "brakfontein", "bronberrik",
        "centurion sentraal", "centurion golf estate", "celtisdal", "claudius",
        "cornwall hill", "doringkloof", "eco park estate",
        "eldo lakes", "eldo meadows", "eldo view", "eldoglen",
        "hennopspark", "heritage hill", "highveld", "irene farm villages",
        "irene park", "kloofsig", "kosmosdal", "laudium",
        "louwlardia", "lyttelton landbouhoewes", "lyttelton manor",
        "mnandi", "monavoni", "olievenhoutbosch", "pierre van ryneveld",
        "rooihuiskraal noord", "samrand", "southdowns",
        "sunderland ridge", "thatchfield", "the reeds", "valhalla", "zwartkop"
    ],
    "sentraal": [
        "baileys muckleneuk", "bryntirion", "clydesdale",
        "colbyn", "groenkloof", "hillcrest", "lukasrand",
        "nieuw muckleneuk", "pretoria central", "salvokop"
    ],
    "moot": [
        "capital park", "kilner park", "rietondale", "riviera"
    ]
}

for k, vs in NEW_SUBURBS.items():
    VOORSTAD_KLUSTERS[k].update(vs)

def norm_voorstad(s: str) -> str:
    if not s:
        return ""
    s = s.replace("'", "")
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()

VOORSTAD_NA_KLUSTER = {}
# Maak seker ons gebruik die gesamentlike lys vir presiese opsoeke
for k, vs in VOORSTAD_KLUSTERS.items():
    for v in vs:
        nv = norm_voorstad(v)
        assert nv not in VOORSTAD_NA_KLUSTER or VOORSTAD_NA_KLUSTER[nv] == k, f"Botsing: {nv}"
        VOORSTAD_NA_KLUSTER[nv] = k

def _vind_kluster(voorstad: str) -> Optional[str]:
    v = voorstad.lower().strip()
    norm_v = norm_voorstad(v)
    
    # 1. Presiese opsoek teen nuwe en ou lyste gesamentlik
    if norm_v in VOORSTAD_NA_KLUSTER:
        return VOORSTAD_NA_KLUSTER[norm_v]
        
    # 2. Gedeeltelike terugval slegs teen ou logika vir backwards compatibility
    for kluster_naam, lede in OU_VOORSTAD_KLUSTERS.items():
        if v in lede:
            return kluster_naam
        for lid in lede:
            if lid in v or v in lid:
                return kluster_naam
    return None

def bereken_voorstad_ooreenstemming(
    voorstad_a: Optional[str],
    voorstad_b: Optional[str],
) -> float:
    """Bereken die liggingpassing tussen twee voorstede (0..100%)."""
    if not voorstad_a or not voorstad_b:
        return 50.0  # Neutraal indien nie gespesifiseer nie

    va = voorstad_a.strip().lower()
    vb = voorstad_b.strip().lower()

    if va == vb:
        return 100.0

    kluster_a = _vind_kluster(va)
    kluster_b = _vind_kluster(vb)

    if kluster_a and kluster_b:
        if kluster_a == kluster_b:
            return 90.0

        # Verbindinge tussen aangrensende klusters langs hoofweë (N1, R21, N4)
        pare = {kluster_a, kluster_b}
        if pare == {"centurion", "oos"}:
            return 75.0
        if pare == {"sentraal", "oos"}:
            return 85.0
        if pare == {"sentraal", "moot"}:
            return 70.0
        if pare == {"centurion", "midrand"}:
            return 80.0
        if pare == {"moot", "noord"}:
            return 65.0
        if pare == {"centurion", "noord"}:
            return 20.0
        if pare == {"oos", "noord"}:
            return 25.0

    # Val terug op teks-ooreenstemming
    if "pretoria" in va and "pretoria" in vb:
        return 50.0

    return 30.0


# ---------------------------------------------------------------------------
# Rol en Veiligheid Helpers
# ---------------------------------------------------------------------------

def bereken_rol_telling(rol_a: str, rol_b: str) -> float:
    """Evalueer rolpassing. Twee passasiers kan nie saamry nie."""
    ra = (rol_a or "BEIDE").strip().upper()
    rb = (rol_b or "BEIDE").strip().upper()

    if ra == "PASSASIER" and rb == "PASSASIER":
        return 0.0

    if (ra == "BESTUURDER" and rb == "PASSASIER") or (ra == "PASSASIER" and rb == "BESTUURDER"):
        return 100.0

    if ra == "BEIDE" and rb == "BEIDE":
        return 100.0

    if ra == "BEIDE" or rb == "BEIDE":
        return 100.0

    if ra == "BESTUURDER" and rb == "BESTUURDER":
        return 85.0

    return 50.0


def toets_geslag_versoenbaarheid(
    student_a: StudentSaamryData,
    student_b: StudentSaamryData,
) -> bool:
    """Verifieer geslagsvoorkeure vir veiligheid en gemoedsrus."""
    ga = (student_a.geslag or "").strip().upper()
    gb = (student_b.geslag or "").strip().upper()

    va = (student_a.geslag_voorkeur or "ENIGE").strip().upper()
    vb = (student_b.geslag_voorkeur or "ENIGE").strip().upper()

    if va == "DIESELFDE":
        if ga and gb and ga != gb:
            return False

    if vb == "DIESELFDE":
        if gb and ga and gb != ga:
            return False

    return True


# ---------------------------------------------------------------------------
# Hoof Berekeningsfunksie
# ---------------------------------------------------------------------------

def bereken_saamry_versoenbaarheid(
    student: StudentSaamryData,
    kandidaat: StudentSaamryData,
) -> VersoenbaarheidResultaat:
    """Suiwer funksie wat die algehele versoenbaarheid tussen twee studente bereken."""

    # 1. Harde uitsluitings
    if student.gebruiker_id == kandidaat.gebruiker_id:
        return VersoenbaarheidResultaat(
            kandidaat_id=kandidaat.gebruiker_id,
            totale_telling=0.0,
            is_geskik=False,
            gehalte="ONVERSOENBAAR",
            gemeenskaplike_dae=[],
            beste_dag=None,
            faktore={"tyd_telling": 0.0, "ligging_telling": 0.0, "rol_telling": 0.0, "betroubaarheid_telling": 0.0},
            per_dag_afbreking={},
            aanbeveling_teks="Self-passing is nie toelaatbaar nie.",
        )

    # Kampus-ooreenstemming: moet na dieselfde kampus reis
    if student.kampus_id and kandidaat.kampus_id and student.kampus_id != kandidaat.kampus_id:
        return VersoenbaarheidResultaat(
            kandidaat_id=kandidaat.gebruiker_id,
            totale_telling=0.0,
            is_geskik=False,
            gehalte="ONVERSOENBAAR",
            gemeenskaplike_dae=[],
            beste_dag=None,
            faktore={"tyd_telling": 0.0, "ligging_telling": 0.0, "rol_telling": 0.0, "betroubaarheid_telling": 0.0},
            per_dag_afbreking={},
            aanbeveling_teks="Studente reis na verskillende kampusse.",
        )

    # Geslagsvoorkeur
    if not toets_geslag_versoenbaarheid(student, kandidaat):
        return VersoenbaarheidResultaat(
            kandidaat_id=kandidaat.gebruiker_id,
            totale_telling=0.0,
            is_geskik=False,
            gehalte="ONVERSOENBAAR",
            gemeenskaplike_dae=[],
            beste_dag=None,
            faktore={"tyd_telling": 0.0, "ligging_telling": 0.0, "rol_telling": 0.0, "betroubaarheid_telling": 0.0},
            per_dag_afbreking={},
            aanbeveling_teks="Voldoen nie aan geslagsvoorkeur nie.",
        )

    # Roltelling
    rol_telling = bereken_rol_telling(student.saamry_rol, kandidaat.saamry_rol)
    if rol_telling == 0.0:
        return VersoenbaarheidResultaat(
            kandidaat_id=kandidaat.gebruiker_id,
            totale_telling=0.0,
            is_geskik=False,
            gehalte="ONVERSOENBAAR",
            gemeenskaplike_dae=[],
            beste_dag=None,
            faktore={"tyd_telling": 0.0, "ligging_telling": 0.0, "rol_telling": 0.0, "betroubaarheid_telling": 0.0},
            per_dag_afbreking={},
            aanbeveling_teks="Beide studente is passasiers sonder voertuig.",
        )

    # 2. Per-dag skedule-analise
    skedule_s = student.skedule_per_dag or {}
    skedule_k = kandidaat.skedule_per_dag or {}

    gemeenskaplike_dae = []
    per_dag_afbreking = {}
    dag_tellings = []
    beste_dag = None
    beste_dag_telling = -1.0

    totale_monsters_s = 0
    totale_monsters_k = 0

    for dag in DAE_VAN_DIE_WEEK:
        dag_s = skedule_s.get(dag)
        dag_k = skedule_k.get(dag)

        if not dag_s or not dag_k:
            continue

        if not dag_s.het_aktiwiteit or not dag_k.het_aktiwiteit:
            # Een of albei reis nie op hierdie dag nie — moenie penaliseer nie
            continue

        if dag_s.aankoms_minuut is None or dag_k.aankoms_minuut is None:
            continue

        gemeenskaplike_dae.append(dag)
        totale_monsters_s += dag_s.aantal_monsters
        totale_monsters_k += dag_k.aantal_monsters

        # Inkorporeer beide gemiddelde verskil asook historiese onsekerheid (variansie)
        # Twee studente met lae variansie is baie meer betroubaar as studente met 40min variansie!
        verskil_in = abs(dag_s.aankoms_minuut - dag_k.aankoms_minuut)
        gesamentlike_afwyking_in = (dag_s.standaardafwyking_min + dag_k.standaardafwyking_min) / 2.0
        effektiewe_verskil_in = math.sqrt(verskil_in**2 + gesamentlike_afwyking_in**2)
        score_in = bereken_tyd_telling(effektiewe_verskil_in)

        if dag_s.vertrek_minuut is not None and dag_k.vertrek_minuut is not None:
            verskil_uit = abs(dag_s.vertrek_minuut - dag_k.vertrek_minuut)
            gesamentlike_afwyking_uit = (dag_s.standaardafwyking_min + dag_k.standaardafwyking_min) / 2.0
            effektiewe_verskil_uit = math.sqrt(verskil_uit**2 + gesamentlike_afwyking_uit**2)
            score_uit = bereken_tyd_telling(effektiewe_verskil_uit)
            dag_score = round(0.55 * score_in + 0.45 * score_uit, 1)
        else:
            verskil_uit = None
            effektiewe_verskil_uit = None
            gesamentlike_afwyking_uit = None
            dag_score = score_in

        dag_tellings.append(dag_score)
        if dag_score > beste_dag_telling:
            beste_dag_telling = dag_score
            beste_dag = dag

        # Voeg deursigtige verduidelikings by vir die UI
        def ui_bron(b):
            if b == "ML_MODEL": return "ML-voorspelling"
            if b == "MEDIAAN": return "gemiddelde aankomstyd van studente"
            if b == "KLASROOSTER": return "klasrooster-terugval"
            return "hek-logs"
            
        bron_inligting = f"Aankomste geskat deur {ui_bron(dag_k.bron)}." if dag_k.bron != "LOGS" else f"Gebaseer op {dag_k.aantal_monsters} outentieke rekords."

        verduideliking = (
            f"{bron_inligting} Basiese tydverskil is {verskil_in} min. "
            f"Met onsekerheid ({round(gesamentlike_afwyking_in, 1)} min afwyking) is die effektiewe faktor {round(effektiewe_verskil_in, 1)} min."
        )

        per_dag_afbreking[dag] = {
            "aankoms_verskil_min": verskil_in,
            "vertrek_verskil_min": verskil_uit,
            "telling": dag_score,
            "aankoms_geskat": minuut_na_tydstring(dag_k.aankoms_minuut),
            "vertrek_geskat": minuut_na_tydstring(dag_k.vertrek_minuut),
            "gesamentlike_variansie": round((gesamentlike_afwyking_in + (gesamentlike_afwyking_uit or gesamentlike_afwyking_in)) / 2.0, 1),
            "verduideliking": verduideliking,
        }

    if not gemeenskaplike_dae:
        return VersoenbaarheidResultaat(
            kandidaat_id=kandidaat.gebruiker_id,
            totale_telling=0.0,
            is_geskik=False,
            gehalte="ONVERSOENBAAR",
            gemeenskaplike_dae=[],
            beste_dag=None,
            faktore={"tyd_telling": 0.0, "ligging_telling": 0.0, "rol_telling": rol_telling, "betroubaarheid_telling": 0.0},
            per_dag_afbreking={},
            aanbeveling_teks="Geen gemeenskaplike kampusdae gevind nie.",
        )

    # Basis tydtelling = gemiddeld oor slegs die gemeenskaplike dae
    basis_tyd_telling = sum(dag_tellings) / len(dag_tellings)

    # Dae-faktor (bonus vir goeie oorvleueling van BESKIKBARE dae, ipv absolute dae)
    # Penaliseer nie 'n student wat net 2 dae klas het as hulle daardie 2 dae ten volle deel nie.
    aantal_dae = len(gemeenskaplike_dae)
    aktiewe_dae_s = sum(1 for d in skedule_s.values() if d.het_aktiwiteit)
    aktiewe_dae_k = sum(1 for d in skedule_k.values() if d.het_aktiwiteit)
    max_moontlike_dae = min(aktiewe_dae_s, aktiewe_dae_k)

    if max_moontlike_dae > 0:
        oorvleueling_verhouding = aantal_dae / float(max_moontlike_dae)
        if oorvleueling_verhouding == 1.0:
            dae_faktor = 1.05  # Bonus vir perfekte dekking van behoefte
        elif oorvleueling_verhouding >= 0.5:
            dae_faktor = 1.0   # Aanvaarbaar
        else:
            dae_faktor = 0.90  # Ligte afslag
    else:
        dae_faktor = 1.0

    finale_tyd_telling = min(round(basis_tyd_telling * dae_faktor, 1), 100.0)

    # 3. Liggingtelling
    ligging_telling = bereken_voorstad_ooreenstemming(student.voorstad, kandidaat.voorstad)

    # 4. Betroubaarheid & Vertrouetelling
    # Minimum gemiddelde monsters oor die gemeenskaplike dae
    gem_monsters = min(totale_monsters_s, totale_monsters_k) / float(aantal_dae)

    # Volgens die tegniese spesifikasie moet betroubaarheid 40% wees sodra
    # ENIGE gemeenskaplike dag vir ENIGE persoon geskat is. Die vorige kode
    # het net die eerste gemeenskaplike dag se bron nagegaan.
    student_het_geskatte_dag = any(
        skedule_s.get(dag) is not None and skedule_s[dag].bron in _ESTIMATED_BRONNE
        for dag in gemeenskaplike_dae
    )
    kandidaat_het_geskatte_dag = any(
        skedule_k.get(dag) is not None and skedule_k[dag].bron in _ESTIMATED_BRONNE
        for dag in gemeenskaplike_dae
    )

    if student_het_geskatte_dag or kandidaat_het_geskatte_dag:
        monster_faktor = 0.40
    else:
        if gem_monsters >= 10:
            monster_faktor = 1.0
        elif gem_monsters >= 5:
            # Verval lineêr van 1.0 tot 0.85 vir monsters tussen 10 en 5
            monster_faktor = 0.85 + 0.15 * ((gem_monsters - 5) / 5.0)
        elif gem_monsters >= 1:
            # Verval lineêr van 0.85 tot 0.50 vir monsters tussen 5 en 1
            monster_faktor = 0.50 + 0.35 * ((gem_monsters - 1) / 4.0)
        else:
            monster_faktor = 0.40

    # Variansie is reeds by die effektiewe_tyd ingesluit, so hierdie is slegs monster-vertroue
    betroubaarheid_telling = round(100.0 * monster_faktor, 1)

    # 5. Saamgestelde Totale Telling
    # Gewigte: Tyd 40%, Ligging 30%, Rol 15%, Betroubaarheid 15%
    totale_telling = round(
        0.40 * finale_tyd_telling +
        0.30 * ligging_telling +
        0.15 * rol_telling +
        0.15 * betroubaarheid_telling,
        1
    )

    is_geskik = totale_telling >= 50.0 and finale_tyd_telling >= 30.0

    # Gehalte kategorie
    if totale_telling >= 85.0:
        gehalte = "UITSTEKEND"
    elif totale_telling >= 70.0:
        gehalte = "GOED"
    elif totale_telling >= 50.0:
        gehalte = "MATIG"
    elif totale_telling > 0.0:
        gehalte = "SWAK"
    else:
        gehalte = "ONVERSOENBAAR"

    # Aanbeveling teks — verryk met deursigtige inligting
    if is_geskik:
        dae_str = ", ".join(gemeenskaplike_dae)
        if ligging_telling >= 90.0:
            lokasie_deel = f"woon albei in {kandidaat.voorstad or 'dieselfde omgewing'}"
        elif ligging_telling >= 70.0:
            lokasie_deel = f"woon naby mekaar ({student.voorstad or 'area'} en {kandidaat.voorstad or 'area'})"
        else:
            lokasie_deel = "reis na dieselfde kampus"

        vertroue_deel = (
            "met 'n hoë vertroue" if betroubaarheid_telling > 80.0 else
            "met matige vertroue (min geskiedkundige logs)" if betroubaarheid_telling > 50.0 else
            "met lae vertroue"
        )

        aanbeveling_teks = (
            f"{gehalte.capitalize()} pasmaat: julle {lokasie_deel} en deel {len(gemeenskaplike_dae)} dag/dae "
            f"({dae_str}). Berekende tydtelling is {finale_tyd_telling} {vertroue_deel}. "
            f"Beste passing op {beste_dag}."
        )
    else:
        aanbeveling_teks = "Beperkte versoenbaarheid weens aansienlike tyd- of roete-afwykings of klein steekproewe."

    return VersoenbaarheidResultaat(
        kandidaat_id=kandidaat.gebruiker_id,
        totale_telling=totale_telling,
        is_geskik=is_geskik,
        gehalte=gehalte,
        gemeenskaplike_dae=gemeenskaplike_dae,
        beste_dag=beste_dag,
        faktore={
            "tyd_telling": finale_tyd_telling,
            "ligging_telling": ligging_telling,
            "rol_telling": rol_telling,
            "betroubaarheid_telling": betroubaarheid_telling,
        },
        per_dag_afbreking=per_dag_afbreking,
        aanbeveling_teks=aanbeveling_teks,
    )


# ---------------------------------------------------------------------------
# Databasis Skedule-Aggregator (Stap 4)
# ---------------------------------------------------------------------------

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import func
from sqlalchemy.orm import Session
import models

SA_TZ = ZoneInfo("Africa/Johannesburg")
_ESTIMATED_BRONNE = {"ML_MODEL", "MEDIAAN", "KLASROOSTER"}


def _na_sa_tyd(ts: datetime) -> datetime:
    """Interpreteer databasis-tydstempels as UTC en skakel dit na SA plaaslike tyd om."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    else:
        ts = ts.astimezone(timezone.utc)
    return ts.astimezone(SA_TZ)


def herlei_geslag_uit_id(id_nommer: Optional[str]) -> Optional[str]:
    """Herlei geslag uit 'n 13-syfer Suid-Afrikaanse ID-nommer (syfers 7-10)."""
    if not id_nommer or len(id_nommer.strip()) != 13:
        return None
    try:
        reeks = int(id_nommer.strip()[6:10])
        return "MANLIK" if reeks >= 5000 else "VROULIK"
    except Exception:
        return None


def _parse_tyd_na_minute(tyd_str: Optional[str]) -> Optional[int]:
    """Skakel '08:00' of '8:00' om na 480 minute."""
    if not tyd_str:
        return None
    try:
        dele = tyd_str.strip().split(":")
        ure = int(dele[0])
        mins = int(dele[1]) if len(dele) > 1 else 0
        return ure * 60 + mins
    except Exception:
        return None


DAG_INDEKS_NAAM = {
    0: "Maandag",
    1: "Dinsdag",
    2: "Woensdag",
    3: "Donderdag",
    4: "Vrydag",
}


def bou_student_saamry_data_van_db(db: Session, gebruiker: models.Gebruikers) -> StudentSaamryData:
    """Aggregeer 'n student se profiel, historiese heklogs en klasrooster na 'n suiwer StudentSaamryData objek."""
    profiel = getattr(gebruiker, "saamry_profiel", None)
    if profiel is None:
        profiel = db.query(models.SaamryProfiel).filter(
            models.SaamryProfiel.Gebruiker_ID == gebruiker.Gebruiker_ID
        ).first()

    saamry_rol = profiel.Rol_Tipe if profiel else "BEIDE"
    voorstad = profiel.Voorstad if profiel else None
    kampus_id = profiel.Kampus_ID if profiel else None
    geslag = profiel.Geslag if (profiel and profiel.Geslag) else herlei_geslag_uit_id(gebruiker.GEB_ID_Nommer)
    geslag_voorkeur = profiel.Geslag_Voorkeur if profiel else "ENIGE"

    # Haal slegs KAMPUSHEK-logs van die afgelope 60 dae op. Koshuis-, klas-
    # en ander lokasie-scans mag nie die pendel-aankomstyd beïnvloed nie.
    vanaf_datum = datetime.utcnow() - timedelta(days=60)
    logs_query = (
        db.query(models.ToegangsLogs)
        .join(models.Lokasie, models.Lokasie.Lokasie_ID == models.ToegangsLogs.Lokasie_ID)
        .filter(
            models.ToegangsLogs.Gebruiker_ID == gebruiker.Gebruiker_ID,
            models.ToegangsLogs.TOE_Tydstempel >= vanaf_datum,
            models.ToegangsLogs.TOE_Rigting.in_(["IN", "UIT"]),
            func.lower(func.trim(models.Lokasie.LOK_Tipe)) == "kampus",
        )
    )
    if kampus_id is not None:
        logs_query = logs_query.filter(models.Lokasie.Kampus_ID == kampus_id)
    logs = logs_query.all()

    # Groepeer logs per weeksdag (0=Maandag .. 4=Vrydag)
    dag_in_logs: Dict[str, List[int]] = {dag: [] for dag in DAE_VAN_DIE_WEEK}
    dag_uit_logs: Dict[str, List[int]] = {dag: [] for dag in DAE_VAN_DIE_WEEK}

    for log in logs:
        plaaslike_tyd = _na_sa_tyd(log.TOE_Tydstempel)
        wd = plaaslike_tyd.weekday()
        if wd in DAG_INDEKS_NAAM:
            dag_naam = DAG_INDEKS_NAAM[wd]
            minuut = plaaslike_tyd.hour * 60 + plaaslike_tyd.minute
            if log.TOE_Rigting == "IN":
                dag_in_logs[dag_naam].append(minuut)
            elif log.TOE_Rigting == "UIT":
                dag_uit_logs[dag_naam].append(minuut)

    # Haal beide Student- EN Personeel-roosters op. Saamry is vir albei rolle
    # beskikbaar; die vorige implementasie het personeelklasse geïgnoreer.
    klasse_by_id = {}
    student_klasse = (
        db.query(models.Klas)
        .join(models.Student_Klas, models.Student_Klas.Klas_ID == models.Klas.Klas_ID)
        .filter(models.Student_Klas.Gebruiker_ID == gebruiker.Gebruiker_ID)
        .all()
    )
    personeel_klasse = (
        db.query(models.Klas)
        .join(models.Personeel_Klas, models.Personeel_Klas.Klas_ID == models.Klas.Klas_ID)
        .filter(models.Personeel_Klas.Gebruiker_ID == gebruiker.Gebruiker_ID)
        .all()
    )
    for klas in student_klasse + personeel_klasse:
        # Indien die gebruiker 'n spesifieke Saamry-kampus gekies het en die
        # klas het 'n bekende lokasie op 'n ander kampus, ignoreer daardie klas.
        if kampus_id is not None and klas.lokasie is not None and klas.lokasie.Kampus_ID != kampus_id:
            continue
        klasse_by_id[klas.Klas_ID] = klas
    klasse = list(klasse_by_id.values())

    # Groepeer klastye per dag
    dag_klasse: Dict[str, List[models.Klas]] = {dag: [] for dag in DAE_VAN_DIE_WEEK}
    for k in klasse:
        k_dag = (k.KLA_Dag or "").strip().capitalize()
        if k_dag in dag_klasse:
            dag_klasse[k_dag].append(k)

    skedule_per_dag = {}
    for dag in DAE_VAN_DIE_WEEK:
        in_lys = dag_in_logs[dag]
        uit_lys = dag_uit_logs[dag]
        klas_lys = dag_klasse[dag]

        aantal_in = len(in_lys)
        aantal_uit = len(uit_lys)
        aantal_monsters = aantal_in + aantal_uit

        if aantal_in >= 3:
            # Empiriese logs is voldoende
            gem_in = int(sum(in_lys) / aantal_in)
            gem_uit = int(sum(uit_lys) / aantal_uit) if aantal_uit > 0 else (gem_in + 480)
            afwyking = math.sqrt(sum((x - gem_in) ** 2 for x in in_lys) / aantal_in) if aantal_in > 1 else 10.0

            skedule_per_dag[dag] = DagSkedule(
                dag_naam=dag,
                het_aktiwiteit=True,
                aankoms_minuut=gem_in,
                vertrek_minuut=gem_uit,
                aantal_monsters=aantal_monsters,
                standaardafwyking_min=afwyking,
                bron="LOGS",
            )
        elif klas_lys:
            # Val terug op ML Model
            begin_tye = [_parse_tyd_na_minute(k.KLA_Begin_Tyd) for k in klas_lys]
            eind_tye = [_parse_tyd_na_minute(k.KLA_Eind_Tyd) for k in klas_lys]
            geldige_begin = [t for t in begin_tye if t is not None]
            geldige_eind = [t for t in eind_tye if t is not None]

            vroegste_in = min(geldige_begin) if geldige_begin else 480
            laaste_uit = max(geldige_eind) if geldige_eind else (vroegste_in + 360)
            
            kluster = _vind_kluster(voorstad) if voorstad else None
            is_koshuis = 1 if (gebruiker.student is not None and gebruiker.student.STU_Is_Koshuis) else 0
            offset, sigma, bron = voorspel_aankomstyd_offset(vroegste_in, kluster, saamry_rol, is_koshuis)

            geskat_in = max(0, vroegste_in - offset)
            geskat_uit = min(1439, laaste_uit + 15)

            skedule_per_dag[dag] = DagSkedule(
                dag_naam=dag,
                het_aktiwiteit=True,
                aankoms_minuut=geskat_in,
                vertrek_minuut=geskat_uit,
                aantal_monsters=aantal_monsters,
                standaardafwyking_min=sigma,
                bron=bron,
            )
        elif aantal_in > 0:
            gem_in = int(sum(in_lys) / aantal_in)
            gem_uit = int(sum(uit_lys) / aantal_uit) if aantal_uit > 0 else (gem_in + 480)
            skedule_per_dag[dag] = DagSkedule(
                dag_naam=dag,
                het_aktiwiteit=True,
                aankoms_minuut=gem_in,
                vertrek_minuut=gem_uit,
                aantal_monsters=aantal_monsters,
                standaardafwyking_min=20.0,
                bron="LOGS",
            )
        else:
            skedule_per_dag[dag] = DagSkedule(
                dag_naam=dag,
                het_aktiwiteit=False,
                aankoms_minuut=None,
                vertrek_minuut=None,
                aantal_monsters=0,
                standaardafwyking_min=0.0,
            )

    return StudentSaamryData(
        gebruiker_id=gebruiker.Gebruiker_ID,
        naam=gebruiker.GEB_Naam,
        van=gebruiker.GEB_Van,
        saamry_rol=saamry_rol,
        geslag=geslag,
        geslag_voorkeur=geslag_voorkeur,
        voorstad=voorstad,
        kampus_id=kampus_id,
        foto_url=gebruiker.GEB_Profiel_Foto,
        skedule_per_dag=skedule_per_dag,
    )


def vind_saamry_voorstelle(
    db: Session,
    current_user: models.Gebruikers,
    limiet: int = 10,
    min_telling: float = 50.0,
) -> List[dict]:
    """Soek en rangskik versoenbare saamry-kandidate vir die huidige gebruiker."""
    current_profiel = db.query(models.SaamryProfiel).filter(
        models.SaamryProfiel.Gebruiker_ID == current_user.Gebruiker_ID
    ).first()
    if current_profiel is not None and current_profiel.Is_Aktief_Saamryer is False:
        return []

    student_data = bou_student_saamry_data_van_db(db, current_user)

    kandidate = (
        db.query(models.Gebruikers)
        .outerjoin(models.SaamryProfiel, models.SaamryProfiel.Gebruiker_ID == models.Gebruikers.Gebruiker_ID)
        .filter(
            models.Gebruikers.Gebruiker_ID != current_user.Gebruiker_ID,
            models.Gebruikers.Is_Aktief == True,
            (models.SaamryProfiel.Is_Aktief_Saamryer != False) | (models.SaamryProfiel.Profiel_ID == None),
        )
        .all()
    )

    voorstelle = []

    vriendskappe = (
        db.query(models.SaamryVriendskap)
        .filter(
            (models.SaamryVriendskap.Versoeker_ID == current_user.Gebruiker_ID) |
            (models.SaamryVriendskap.Ontvanger_ID == current_user.Gebruiker_ID)
        )
        .all()
    )
    vriende_ids = set()
    for v in vriendskappe:
        if v.SAA_Status == "AANVAAR":
            vriend_id = v.Ontvanger_ID if v.Versoeker_ID == current_user.Gebruiker_ID else v.Versoeker_ID
            vriende_ids.add(vriend_id)

    for kandidaat in kandidate:
        if kandidaat.student is None and kandidaat.personeel is None:
            continue
        kandidaat_data = bou_student_saamry_data_van_db(db, kandidaat)
        res = bereken_saamry_versoenbaarheid(student_data, kandidaat_data)

        if res.is_geskik and res.totale_telling >= min_telling:
            voorstelle.append({
                "gebruiker_id": kandidaat.Gebruiker_ID,
                "naam": kandidaat.GEB_Naam,
                "van": kandidaat.GEB_Van,
                "foto_url": kandidaat.GEB_Profiel_Foto,
                "saamry_rol": kandidaat_data.saamry_rol,
                "voorstad": kandidaat_data.voorstad or "Onbekend",
                "totale_telling": res.totale_telling,
                "gehalte": res.gehalte,
                "gemeenskaplike_dae": res.gemeenskaplike_dae,
                "beste_dag": res.beste_dag,
                "is_reeds_vriend": kandidaat.Gebruiker_ID in vriende_ids,
                "faktore": res.faktore,
                "per_dag_afbreking": res.per_dag_afbreking,
                "aanbeveling_teks": res.aanbeveling_teks,
            })

    voorstelle.sort(key=lambda x: x["totale_telling"], reverse=True)

    return voorstelle[:limiet]


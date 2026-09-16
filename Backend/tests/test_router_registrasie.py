"""Regressietoets: elke router in routers/ moet in main.py geregistreer wees.

Hierdie registrasies is al meer as een keer per ongeluk uitgewis wanneer
main.py vanaf 'n verouderde werkskopie gecommit is (25009cb het instellings
en klasse verwyder; 10ac6bd het klasse wéér verwyder nadat bb1cedd dit
teruggesit het).  Die toets lees main.py se bronkode direk sodat dit nie 'n
databasis-verbinding nodig het nie (main.py loop migrasies tydens import).
"""

import re
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROUTERS_DIR = BACKEND_DIR / "routers"
MAIN_PY = BACKEND_DIR / "main.py"


def _router_modules() -> list[str]:
    """Alle modules in routers/ wat 'n APIRouter definieer."""
    modules = []
    for pad in sorted(ROUTERS_DIR.glob("*.py")):
        if pad.name == "__init__.py":
            continue
        if "APIRouter(" in pad.read_text(encoding="utf-8"):
            modules.append(pad.stem)
    return modules


def test_alle_routers_is_in_main_geregistreer():
    bron = MAIN_PY.read_text(encoding="utf-8")
    geregistreer = set(re.findall(r"app\.include_router\((\w+)\.router\)", bron))
    ontbreek = [m for m in _router_modules() if m not in geregistreer]
    assert not ontbreek, (
        "Hierdie router-modules word nie in main.py geregistreer nie: "
        f"{ontbreek}. As dit doelbewus is, verwyder die module of sluit dit "
        "hier uit; andersins is 'n app.include_router(...) per ongeluk "
        "uitgewis (dit het al by 25009cb en 10ac6bd gebeur)."
    )

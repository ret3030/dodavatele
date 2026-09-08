"""
Cteni ciselniku kategorii z taxonomie_data.json - jediny zdroj pravdy
o kategoriich (74 kategorii / 11 skupin) a jejich ICT relevanci.
Oduvodneni cleneni: TAXONOMIE.md
"""

import json
import os

_CESTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "taxonomie_data.json")

with open(_CESTA, encoding="utf-8") as _f:
    _D = json.load(_f)

KATEGORIE = _D["KATEGORIE"]                    # kod -> [skupina, nazev]
VYCHOZI_KOD = _D.get("VYCHOZI_KOD", "XXX-00")
SKUPINY = _D.get("SKUPINY", [])

_ICT = {}
for _uroven in ("ano", "hranicni", "ne"):
    for _kod in _D.get("ICT_RELEVANCE", {}).get(_uroven, []):
        _ICT[_kod] = "hraniční" if _uroven == "hranicni" else _uroven


def ict_relevance(kod):
    """'ano' / 'hraniční' / 'ne' / '' - vstup pro posouzení dle ISO 27001."""
    return _ICT.get(kod, "")


def nazev(kod):
    z = KATEGORIE.get(kod)
    return z[1] if z else ""


def skupina(kod):
    z = KATEGORIE.get(kod)
    return z[0] if z else ""

"""
Nacteni ciselniku kategorii z ../taxonomie_data.json - jeden zdroj pravdy
sdileny s dodavatele.py. Obsahuje revidovanou taxonomii v2 (74 kategorii /
11 skupin) vcetne ICT relevance a prevodni mapy ze stareho cisleniku.
Oduvodneni revize: TAXONOMIE_V2.md.
"""

import json
import os
import re

_ZAKLAD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CESTA = os.path.join(_ZAKLAD, "taxonomie_data.json")

with open(_CESTA, encoding="utf-8") as _f:
    _D = json.load(_f)

KATEGORIE = _D["KATEGORIE"]                    # kod -> [skupina, nazev]
VYCHOZI_KOD = _D.get("VYCHOZI_KOD", "XXX-00")
SKUPINY = _D.get("SKUPINY", [])
NACE_NAZVY = _D.get("NACE_NAZVY", {})

_ICT_KOD = {}
for _uroven in ("ano", "hranicni", "ne"):
    for _kod in _D.get("ICT_RELEVANCE", {}).get(_uroven, []):
        _ICT_KOD[_kod] = _uroven

MAPA_ZE_STARE = {k: v for k, v in _D.get("MAPA_ZE_STARE", {}).items()
                 if not k.startswith("_")}


def skupina(kod):
    z = KATEGORIE.get(kod)
    return z[0] if z else ""


def nazev(kod):
    z = KATEGORIE.get(kod)
    return z[1] if z else ""


def ict_relevance(kod):
    """'ano' / 'hranicni' / 'ne' / '' - vstup pro navazujici krok ISO 27001."""
    return _ICT_KOD.get(kod, "")


def prevod_ze_stare(kod):
    """Puvodni kod puvodniho cisleniku -> novy kod (migrace starych vystupu)."""
    return MAPA_ZE_STARE.get(kod, kod)


def nazev_nace(kod):
    """Nazev NACE polozky. ARES/RPO casto vraci 5mistne kody (46900), ktere
    ciselnik nema - zkusi se proto i kratsi prefixy (4630 -> 463 -> 46)."""
    if not kod:
        return ""
    cislo = re.sub(r"\D", "", str(kod))
    for k in (kod, cislo, cislo[:4], cislo[:3], cislo[:2]):
        if k and NACE_NAZVY.get(k):
            return NACE_NAZVY[k]
    return ""

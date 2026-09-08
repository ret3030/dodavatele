"""
CLI: seznam firem -> kategorie z ciselniku (deterministicky, z verejnych zdroju).

    python3 -m kategorizace.kategorizuj vstup.csv -o vystup_kat.csv
    python3 -m kategorizace.kategorizuj vstup.xlsx -o vystup_kat.xlsx --rozbor rozbor.jsonl
    python3 -m kategorizace.kategorizuj vstup.csv -o out.csv --offline   # jen z kese

Zadny API klic, zadna behova sluzba, cisty Python (bezi i na Windows bez WSL).
Signaly se sbiraji z ARES, Wikidat, Wikipedie a z webu firmy; zarazeni urcuje
list namapovanych klicovych slov (pravidla.py). Prvni beh stahuje, kazdy dalsi
beh nad stejnym seznamem jede z kese a je bajt po bajtu shodny.

Presnost hodne zvedne, kdyz vstup obsahuje sloupec s webem firmy (Web / URL) -
odpada tim nejiste dohledavani domeny.
"""

import argparse
import json
import os
import re
import sys

from .klasifikator import klasifikuj
from .zdroje import Zdroje
from .web import Web
from .taxonomie import ict_relevance, nazev_nace
from .vstup import nacti as nacti_vstup

_ZDE = os.path.dirname(os.path.abspath(__file__))
VYCHOZI_KES = os.path.join(_ZDE, ".cache")


def nace_hint(kody):
    """Seznam NACE/CZ-NACE kodu -> jejich nazvy (jako slaby textovy signal)."""
    nazvy = []
    for k in kody or []:
        for kus in re.findall(r"\d{2,6}", str(k)):
            n = nazev_nace(kus)
            if n and n not in nazvy:
                nazvy.append(n)
    return nazvy


def _zapis_csv(cesta, radky, hlavicka):
    import csv
    with open(cesta, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(hlavicka)
        w.writerows(radky)


def _zapis_xlsx(cesta, radky, hlavicka):
    try:
        from openpyxl import Workbook
    except ImportError:
        raise SystemExit("Zapis XLSX vyzaduje openpyxl - pouzijte .venv/bin/python nebo -o *.csv")
    wb = Workbook()
    ws = wb.active
    ws.title = "Kategorizace"
    ws.append(hlavicka)
    for r in radky:
        ws.append(r)
    wb.save(cesta)


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="kategorizace.kategorizuj",
        description="Deterministicke zarazeni dodavatele do kategorie z verejnych rejstriku + list klicovych slov.",
    )
    p.add_argument("vstup", help="CSV / XLSX / TXT se seznamem firem (sloupec s nazvem povinny; Web/URL, ICO, Mesto, Zeme zpresni)")
    p.add_argument("-o", "--vystup", default="vystup_kategorizace.csv",
                   help="vystupni soubor (.csv nebo .xlsx), vychozi vystup_kategorizace.csv")
    p.add_argument("--rozbor", metavar="SOUBOR.jsonl",
                   help="podrobny rozbor pro ladeni (skore vsech kategorii, duraz, signaly)")
    p.add_argument("--limit", type=int, default=0, help="zpracovat jen prvnich N firem")
    p.add_argument("--offline", action="store_true",
                   help="nestahovat nic novego, pouzit jen to, co uz je v kesi")
    p.add_argument("--bez-webu", dest="bez_webu", action="store_true",
                   help="nestahovat domovske stranky firem (jen rejstriky a Wikipedie)")
    p.add_argument("--bez-heuristiky", dest="bez_heuristiky", action="store_true",
                   help="nezkouset uhodnout domenu z nazvu (jen vstupni sloupec Web a Wikidata P856)")
    p.add_argument("--kes", default=VYCHOZI_KES, help="adresar kese (vychozi kategorizace/.cache)")
    p.add_argument("--prodleva", type=float, default=0.3,
                   help="pauza mezi dotazy na rejstriky (s)")
    a = p.parse_args(argv)

    firmy = nacti_vstup(a.vstup)
    if a.limit:
        firmy = firmy[:a.limit]
    if not firmy:
        raise SystemExit("Vstup neobsahuje zadnou firmu.")

    zdroje = Zdroje(cache_dir=a.kes, prodleva=a.prodleva, offline=a.offline,
                    povolit_heuristiku=not a.bez_heuristiky)
    web = Web(cache_dir=os.path.join(a.kes, "web"),
              povolit=not a.offline and not a.bez_webu)

    hlavicka = ["Název", "IČO", "Doména", "Zdroj domény",
                "Kód kategorie", "Kategorie", "Skupina", "ICT relevance",
                "Rozhodnutí", "Skóre", "Odstup", "Zdrojů", "Alternativy",
                "Skupina (skóre)", "Důkaz"]
    radky = []
    pocty = {"AUTO": 0, "OVERIT": 0, "LLM": 0}
    rozbor_f = open(a.rozbor, "w", encoding="utf-8") if a.rozbor else None

    for i, firma in enumerate(firmy, 1):
        info = zdroje.o_firme(
            firma["nazev"], mesto=firma.get("mesto", ""), zeme=firma.get("zeme", ""),
            ico=firma.get("ico", ""), web_hint=firma.get("web", ""),
        )
        odpovedi = info["odpovedi"]

        pridane = []
        dom = info["domena"]
        if dom:
            meta_text, telo_text = web.popis(dom)
            if meta_text:
                pridane.append(("web-meta:%s" % dom, meta_text, 3.0))
            if telo_text:
                pridane.append(("web-text:%s" % dom, telo_text, 1.6))

        kody_nace = info["nace"] or re.findall(r"\d{2,6}", firma.get("nace", "") or "")
        nace_nazvy = nace_hint(kody_nace) + info.get("nace_text", [])
        vysl = klasifikuj(odpovedi, firma["nazev"], nace_nazvy, pridane)
        pocty[vysl["rozhodnuti"]] += 1

        alt = " | ".join("%s=%.1f" % (k, s) for k, s in vysl["alternativy"])
        skup = " | ".join("%s=%.1f" % (g, s) for g, s in vysl["skupina_skore"])
        duraz = "; ".join(
            "%s (%s, +%.1f)" % (f, zdroj, pr) for f, zdroj, pr in vysl["duraz_top1"][:8]
        )
        radky.append([
            firma["nazev"], info["ico"], dom, info["domena_zdroj"],
            vysl["kod"], vysl["kategorie"], vysl["skupina"],
            ict_relevance(vysl["kod"]), vysl["rozhodnuti"], "%.1f" % vysl["skore"],
            "%.2f" % vysl["odstup"], vysl["zdroju"], alt, skup, duraz,
        ])

        if rozbor_f:
            rozbor_f.write(json.dumps({
                "nazev": firma["nazev"], "mesto": info.get("mesto", ""),
                "zeme": firma.get("zeme", ""), "ico": info["ico"],
                "domena": dom, "domena_zdroj": info["domena_zdroj"],
                "nace": info["nace"],
                "vysledek": {k: v for k, v in vysl.items() if k != "duraz_top1"},
                "duraz_top1": vysl["duraz_top1"],
            }, ensure_ascii=False) + "\n")

        if i % 10 == 0 or i == len(firmy):
            print("  %d/%d  (AUTO %d / OVERIT %d / LLM %d)"
                  % (i, len(firmy), pocty["AUTO"], pocty["OVERIT"], pocty["LLM"]),
                  file=sys.stderr)

    if rozbor_f:
        rozbor_f.close()

    if os.path.splitext(a.vystup)[1].lower() in (".xlsx", ".xlsm"):
        _zapis_xlsx(a.vystup, radky, hlavicka)
    else:
        _zapis_csv(a.vystup, radky, hlavicka)

    n = len(firmy)
    print("\nHotovo: %d firem -> %s" % (n, a.vystup), file=sys.stderr)
    print("  AUTO   %4d  (%.0f %%)  - kategorie prevzata rovnou" % (pocty["AUTO"], 100 * pocty["AUTO"] / n), file=sys.stderr)
    print("  OVERIT %4d  (%.0f %%)  - navrh s nizsi jistotou, doporucena kontrola" % (pocty["OVERIT"], 100 * pocty["OVERIT"] / n), file=sys.stderr)
    print("  LLM    %4d  (%.0f %%)  - nezarazeno, na puvodni LLM krok" % (pocty["LLM"], 100 * pocty["LLM"] / n), file=sys.stderr)
    print("  REJSTRIKY: %d z kese, %d stazeno, %d bez odpovedi" % (zdroje.z_kese, zdroje.stazeno, zdroje.chyby), file=sys.stderr)
    print("  WEB:       %d z kese, %d stazeno, %d bez odpovedi" % (web.z_kese, web.stazeno, web.chyby), file=sys.stderr)


if __name__ == "__main__":
    main()

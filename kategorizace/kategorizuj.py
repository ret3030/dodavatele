"""
CLI: seznam firem -> kategorie z ciselniku (deterministicky, pres SERPER).

    python3 -m kategorizace.kategorizuj vstup.csv -o vystup_kat.csv
    python3 -m kategorizace.kategorizuj vstup.xlsx -o vystup_kat.xlsx --rozbor rozbor.jsonl
    python3 -m kategorizace.kategorizuj vstup.csv -o out.csv --offline   # jen z kese

Klic SERPER: env SERPER_API_KEY, nebo soubor kategorizace/serper_key.txt.
"""

import argparse
import json
import os
import re
import sys

from .klasifikator import klasifikuj, vlastni_domena
from .serper import Serper, nacti_klic
from .web import Web
from .taxonomie import ict_relevance, nazev_nace
from .vstup import nacti as nacti_vstup

_ZDE = os.path.dirname(os.path.abspath(__file__))
VYCHOZI_KES = os.path.join(_ZDE, ".cache")

LOKALIZACE = {
    "CZ": ("cz", "cs"), "SK": ("sk", "sk"), "DE": ("de", "de"), "AT": ("at", "de"),
    "PL": ("pl", "pl"), "FR": ("fr", "fr"), "IT": ("it", "it"), "ES": ("es", "es"),
    "NL": ("nl", "nl"), "GB": ("gb", "en"), "UK": ("gb", "en"), "US": ("us", "en"),
}
VYCHOZI_LOK = ("cz", "cs")

_PRAVNI_RE = re.compile(
    r"\b(s\.?\s?r\.?\s?o\.?|spol\.?\s?s\.?\s?r\.?\s?o\.?|a\.?\s?s\.?|k\.?\s?s\.?|"
    r"se|v\.?\s?o\.?\s?s\.?|gmbh|ag|kg|co\.?|inc\.?|corp\.?|corporation|ltd\.?|"
    r"limited|llc|plc|s\.?a\.?|sas|sarl|n\.?v\.?|b\.?v\.?|oy|ab|kft\.?|sp\.?\s?z\.?\s?o\.?\s?o\.?|"
    r"s\.?r\.?l\.?|spa|aktiengesellschaft)\b",
    re.IGNORECASE,
)


def ocisti_nazev(nazev):
    n = _PRAVNI_RE.sub(" ", nazev or "")
    n = re.sub(r"[,\.]+", " ", n)
    return re.sub(r"\s+", " ", n).strip() or (nazev or "").strip()


def dotazy(firma):
    nazev = firma["nazev"].strip()
    mesto = firma.get("mesto", "").strip()
    zeme = (firma.get("zeme", "") or "").strip().upper()
    gl, hl = LOKALIZACE.get(zeme, VYCHOZI_LOK)
    jadro = ocisti_nazev(nazev)

    q1 = '"%s"' % nazev
    if mesto:
        q1 += " " + mesto
    if hl in ("cs", "sk"):
        q2 = '%s (výrobce OR dodavatel OR distributor OR služby OR výroba OR "o nás")' % jadro
    else:
        q2 = '%s (manufacturer OR supplier OR distributor OR services OR "about us")' % jadro
    return [(q1, gl, hl), (q2, gl, hl)]


def nace_hint(firma):
    kody = re.findall(r"\d{2,6}", firma.get("nace", "") or "")
    nazvy = []
    for k in kody:
        n = nazev_nace(k)
        if n:
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
        description="Deterministicke zarazeni dodavatele do kategorie pres SERPER + list klicovych slov.",
    )
    p.add_argument("vstup", help="CSV / XLSX / TXT se seznamem firem (sloupec s nazvem povinny)")
    p.add_argument("-o", "--vystup", default="vystup_kategorizace.csv",
                   help="vystupni soubor (.csv nebo .xlsx), vychozi vystup_kategorizace.csv")
    p.add_argument("--rozbor", metavar="SOUBOR.jsonl",
                   help="podrobny rozbor pro ladeni (skore vsech kategorii, duraz, signaly)")
    p.add_argument("--limit", type=int, default=0, help="zpracovat jen prvnich N firem")
    p.add_argument("--offline", action="store_true",
                   help="nestahovat nic novego, pouzit jen to, co uz je v kesi")
    p.add_argument("--bez-webu", dest="bez_webu", action="store_true",
                   help="nestahovat domovske stranky firem (jen SERP snippety)")
    p.add_argument("--kes", default=VYCHOZI_KES, help="adresar kese (vychozi kategorizace/.cache)")
    p.add_argument("--prodleva", type=float, default=0.5, help="pauza mezi dotazy do SERPER (s)")
    p.add_argument("--num", type=int, default=10, help="pocet organic vysledku na dotaz")
    a = p.parse_args(argv)

    firmy = nacti_vstup(a.vstup)
    if a.limit:
        firmy = firmy[:a.limit]
    if not firmy:
        raise SystemExit("Vstup neobsahuje zadnou firmu.")

    klic = "" if a.offline else nacti_klic()
    if not a.offline and not klic:
        raise SystemExit("Chybi SERPER klic (env SERPER_API_KEY nebo kategorizace/serper_key.txt). "
                         "Pro beh jen z kese pouzijte --offline.")
    serper = Serper(api_key=klic or None, cache_dir=a.kes, prodleva=a.prodleva)
    web = Web(cache_dir=os.path.join(a.kes, "web"),
              povolit=not a.offline and not a.bez_webu)

    hlavicka = ["Název", "Kód kategorie", "Kategorie", "Skupina", "ICT relevance",
                "Rozhodnutí", "Skóre", "Odstup", "Zdrojů", "Alternativy",
                "Skupina (skóre)", "Důkaz"]
    radky = []
    pocty = {"AUTO": 0, "OVERIT": 0, "LLM": 0}
    rozbor_f = open(a.rozbor, "w", encoding="utf-8") if a.rozbor else None

    for i, firma in enumerate(firmy, 1):
        odpovedi = []
        for q, gl, hl in dotazy(firma):
            odpovedi.append(serper.hledej(q, gl=gl, hl=hl, num=a.num))
        pridane = []
        dom = vlastni_domena(odpovedi, firma["nazev"])
        if dom:
            meta_text, telo_text = web.popis(dom)
            if meta_text:
                pridane.append(("web-meta:%s" % dom, meta_text, 3.0))
            if telo_text:
                pridane.append(("web-text:%s" % dom, telo_text, 1.6))
        vysl = klasifikuj(odpovedi, firma["nazev"], nace_hint(firma), pridane)
        pocty[vysl["rozhodnuti"]] += 1

        alt = " | ".join("%s=%.1f" % (k, s) for k, s in vysl["alternativy"])
        skup = " | ".join("%s=%.1f" % (g, s) for g, s in vysl["skupina_skore"])
        duraz = "; ".join(
            "%s (%s, +%.1f)" % (f, zdroj, pr) for f, zdroj, pr in vysl["duraz_top1"][:8]
        )
        radky.append([
            firma["nazev"], vysl["kod"], vysl["kategorie"], vysl["skupina"],
            ict_relevance(vysl["kod"]), vysl["rozhodnuti"], "%.1f" % vysl["skore"],
            "%.2f" % vysl["odstup"], vysl["zdroju"], alt, skup, duraz,
        ])

        if rozbor_f:
            rozbor_f.write(json.dumps({
                "nazev": firma["nazev"], "mesto": firma.get("mesto", ""),
                "zeme": firma.get("zeme", ""), "vysledek": {
                    k: v for k, v in vysl.items() if k != "duraz_top1"
                },
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
    print("  SERPER: %d z kese, %d stazeno, %d chyb" % (serper.z_kese, serper.stazeno, serper.chyby), file=sys.stderr)
    print("  WEB:    %d z kese, %d stazeno, %d bez odpovedi" % (web.z_kese, web.stazeno, web.chyby), file=sys.stderr)


if __name__ == "__main__":
    main()

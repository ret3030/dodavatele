"""
CLI: seznam firem -> kategorie z ciselniku (deterministicky, z verejnych zdroju).

    python3 -m kategorizace.kategorizuj vstup.csv -o vystup_kat.csv
    python3 -m kategorizace.kategorizuj vstup.xlsx -o vystup_kat.xlsx --rozbor rozbor.jsonl
    python3 -m kategorizace.kategorizuj vstup.csv -o out.csv --offline   # jen z kese

    # jeden beh -> deterministicky vystup + hotovy prompt pro LLM na zbytek:
    python3 -m kategorizace.kategorizuj vstup.csv -o out.csv --export-llm pro_llm.txt
    # odpoved z chatu ulozit jako CSV a domergovat do vystupu:
    python3 -m kategorizace.kategorizuj vstup.csv -o out.csv --llm-mapa odpoved.csv

Zadny API klic, zadna behova sluzba, cisty Python (bezi i na Windows bez WSL).
Signaly se sbiraji z ARES, Wikidat, Wikipedie a z webu firmy; zarazeni urcuje
list namapovanych klicovych slov (pravidla.py). Prvni beh stahuje, kazdy dalsi
beh nad stejnym seznamem jede z kese a je bajt po bajtu shodny.

Presnost hodne zvedne, kdyz vstup obsahuje sloupec s webem firmy (Web / URL) -
odpada tim nejiste dohledavani domeny.
"""

import argparse
import csv
import json
import os
import re
import sys

from .klasifikator import klasifikuj
from .zdroje import Zdroje
from .web import Web
from .taxonomie import KATEGORIE, VYCHOZI_KOD, ict_relevance, nazev_nace
from .normalizace import klic_nazvu
from .vstup import nacti as nacti_vstup

_ZDE = os.path.dirname(os.path.abspath(__file__))
VYCHOZI_KES = os.path.join(_ZDE, ".cache")
_KOD_RE = re.compile(r"\b[A-Z]{2,4}-\d{2}\b")


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
    with open(cesta, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(hlavicka)
        w.writerows(radky)


def _ciselnik_promptu():
    """Ciselnik kategorii do promptu - serazeny po skupinach, radek na kategorii."""
    radky, skup_predch = [], None
    for kod, skup, nazev in sorted(
            (k, v[0], v[1]) for k, v in KATEGORIE.items() if k != VYCHOZI_KOD):
        if skup != skup_predch:
            radky.append("  [%s]" % skup)
            skup_predch = skup
        radky.append("    %s = %s" % (kod, nazev))
    return radky


def _zapis_export_llm(polozky, cesta, davka=0):
    """
    Textovy soubor pripraveny na vlozeni do LLM chatu (Copilot/ChatGPT) - urcuje
    kategorii firmam, ktere deterministicky krok nechal nezarazene. Ke kazde firme
    prida kontext, ktery uz mame (obory z rejstriku, domena, deterministicky tip
    = top-3 kandidati). Mezikrok dela clovek v chatu; odpoved se nacte --llm-mapa.
    """
    if not polozky:
        return []

    def obsah(cast):
        r = [
            "Kazde firme nize prirad JEDEN kod kategorie z ciselniku. U firmy je "
            "v hranatych zavorkach kontext: obory zapsane v rejstriku, web a "
            "'tip' = kategorie, ke kterym se blizil deterministicky krok (casto, "
            "ne vzdy, je spravna jedna z nich - potvrd, nebo vyber lepsi z celeho "
            "ciselniku). Rozhoduj podle toho, CO FIRMA REALNE DODAVA, ne podle "
            "formalniho zapisu v rejstriku. Kdyz si nejsi jisty/a nebo o firme nic "
            "nevis, napis misto kodu 'neznamo' - chybejici udaj je lepsi nez odhad.",
            "",
            "CISELNIK KATEGORII:",
        ]
        r += _ciselnik_promptu()
        r += ["", "FIRMY K URCENI (%d):" % len(cast)]
        for p in cast:
            ud = ", ".join(x for x in (p.get("mesto"), p.get("zeme")) if x)
            zav = []
            if p.get("ico"):
                zav.append("ICO %s" % p["ico"])
            if p.get("domena"):
                zav.append("web %s" % p["domena"])
            if p.get("obory"):
                zav.append("zapsane obory: %s" % "; ".join(p["obory"][:6]))
            else:
                zav.append("bez zapsaneho oboru")
            if p.get("tip"):
                zav.append("tip: %s" % ", ".join(p["tip"]))
            r.append("- %s%s [%s]" % (
                p["nazev"], " (%s)" % ud if ud else "", " | ".join(zav)))
        r += [
            "",
            "Odpovez presne v tomto formatu, jeden radek na firmu, oddelovac ';', "
            "beze zmeny poradi a bez dalsiho textu okolo:",
            "Puvodni nazev;Kod kategorie;Cim se firma zabyva",
            "",
            "Posledni sloupec par slovy vlastnimi slovy - pro kontrolu, ze kod sedi.",
        ]
        return "\n".join(r)

    davky = ([polozky] if not davka or len(polozky) <= davka
             else [polozky[i:i + davka] for i in range(0, len(polozky), davka)])
    if len(davky) == 1:
        with open(cesta, "w", encoding="utf-8") as f:
            f.write(obsah(davky[0]))
        return [cesta]
    zaklad, pripona = os.path.splitext(cesta)
    cesty = []
    for i, d in enumerate(davky, 1):
        c = "%s_%02d%s" % (zaklad, i, pripona or ".txt")
        with open(c, "w", encoding="utf-8") as f:
            f.write(obsah(d))
        cesty.append(c)
    return cesty


def _nacti_llm_mapu(cesty):
    """CSV odpovedi z chatu (Puvodni nazev;Kod kategorie;Popis) -> {klic_nazvu: (kod, popis)}."""
    mapa = {}
    for cesta in cesty:
        with open(cesta, encoding="utf-8-sig", newline="") as f:
            vzorek = f.read(4096)
            f.seek(0)
            odd = ";" if vzorek.count(";") >= vzorek.count(",") else ","
            for radek in csv.reader(f, delimiter=odd):
                if not radek or not radek[0].strip():
                    continue
                m = _KOD_RE.search((radek[1] if len(radek) > 1 else "").upper())
                if not m:
                    continue
                klic = klic_nazvu(radek[0])
                popis = radek[2].strip() if len(radek) > 2 else ""
                if klic:
                    mapa[klic] = (m.group(0), popis)
    return mapa


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
    p.add_argument("--export-llm", dest="export_llm", metavar="SOUBOR.txt",
                   help="hned v tomhle behu napsat prompt pro LLM chat na firmy, "
                        "ktere zustaly nezarazene (rozhodnuti LLM)")
    p.add_argument("--export-davka", dest="export_davka", type=int, default=0,
                   metavar="N", help="rozdelit --export-llm po N firmach do cislovanych souboru")
    p.add_argument("--llm-i-overit", dest="llm_i_overit", action="store_true",
                   help="do --export-llm zahrnout i firmy s rozhodnutim OVERIT")
    p.add_argument("--llm-mapa", dest="llm_mapa", nargs="+", metavar="ODPOVED.csv",
                   help="CSV odpoved z chatu (Nazev;Kod kategorie;Popis) - domergovat do vystupu")
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
                "Skupina (skóre)", "Důkaz", "Popis (LLM)"]
    radky = []
    meta = []           # paralelne k radky: {"klic","rozh"} pro --llm-mapa/--export-llm
    kontext = []        # paralelne k radky: podklad pro prompt do LLM
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
            "%.2f" % vysl["odstup"], vysl["zdroju"], alt, skup, duraz, "",
        ])
        meta.append({"klic": klic_nazvu(firma["nazev"]), "rozh": vysl["rozhodnuti"]})
        obory = [("%s %s" % (k, nazev_nace(k))).strip() for k in kody_nace]
        kontext.append({
            "nazev": firma["nazev"],
            "mesto": info.get("mesto") or firma.get("mesto", ""),
            "zeme": firma.get("zeme", ""),
            "ico": info["ico"], "domena": dom,
            "obory": [o for o in obory if o] + list(info.get("nace_text", [])),
            "tip": [k for k, _ in vysl["alternativy"]],
        })

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

    # firmy, ktere jdou na LLM (a volitelne i OVERIT)
    na_llm = {"LLM", "OVERIT"} if a.llm_i_overit else {"LLM"}

    # -- domergovat odpoved z chatu (--llm-mapa) --------------------------
    doplneno = 0
    if a.llm_mapa:
        mapa = _nacti_llm_mapu(a.llm_mapa)
        for radek, m in zip(radky, meta):
            if m["rozh"] not in na_llm and radek[4] != VYCHOZI_KOD:
                continue
            hit = mapa.get(m["klic"])
            if not hit:
                continue
            kod, popis = hit
            skup_nazev = KATEGORIE.get(kod, ["", ""])
            radek[4] = kod
            radek[5] = skup_nazev[1]
            radek[6] = skup_nazev[0]
            radek[7] = ict_relevance(kod)
            radek[8] = "LLM-doplneno"
            radek[15] = popis
            m["rozh"] = "LLM-doplneno"
            doplneno += 1

    if os.path.splitext(a.vystup)[1].lower() in (".xlsx", ".xlsm"):
        _zapis_xlsx(a.vystup, radky, hlavicka)
    else:
        _zapis_csv(a.vystup, radky, hlavicka)

    # -- prompt pro LLM na zbytek (--export-llm) ------------------------
    export_cesty = []
    if a.export_llm:
        zbyva = [k for k, m in zip(kontext, meta) if m["rozh"] in na_llm]
        export_cesty = _zapis_export_llm(zbyva, a.export_llm, a.export_davka)

    n = len(firmy)
    print("\nHotovo: %d firem -> %s" % (n, a.vystup), file=sys.stderr)
    print("  AUTO   %4d  (%.0f %%)  - kategorie prevzata rovnou" % (pocty["AUTO"], 100 * pocty["AUTO"] / n), file=sys.stderr)
    print("  OVERIT %4d  (%.0f %%)  - navrh s nizsi jistotou, doporucena kontrola" % (pocty["OVERIT"], 100 * pocty["OVERIT"] / n), file=sys.stderr)
    print("  LLM    %4d  (%.0f %%)  - nezarazeno, na LLM krok" % (pocty["LLM"], 100 * pocty["LLM"] / n), file=sys.stderr)
    if a.llm_mapa:
        print("  z toho domergovano z --llm-mapa: %d" % doplneno, file=sys.stderr)
    if export_cesty:
        print("  prompt pro LLM (%d firem) -> %s" % (
            len(zbyva), ", ".join(export_cesty)), file=sys.stderr)
    print("  REJSTRIKY: %d z kese, %d stazeno, %d bez odpovedi" % (zdroje.z_kese, zdroje.stazeno, zdroje.chyby), file=sys.stderr)
    print("  WEB:       %d z kese, %d stazeno, %d bez odpovedi" % (web.z_kese, web.stazeno, web.chyby), file=sys.stderr)


if __name__ == "__main__":
    main()

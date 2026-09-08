#!/usr/bin/env python3
"""
Dodavatelé – podklad pro audit dodavatelských vztahů dle ISO/IEC 27001.

Vezme seznam kreditorů z účetnictví, ke každé firmě dohledá ve veřejných
rejstřících, kdo to je a čím se zabývá, a připraví dávky pro LLM chat, který
firmy zařadí do kategorií. Výsledek je Excel se vzorci – ten je zdroj pravdy,
dál se s ním pracuje ručně.

    python3 dodavatele.py kreditori.xlsx     1. běh – dohledá a napíše dávky
    python3 dodavatele.py odpovedi/          2. běh – doplní odpovědi z chatu

Žádné přepínače. Vzniká:
    dodavatele.xlsx        výsledek (listy Dodavatelé / Číselník / Souhrn / Podklady)
    davky/davka_01.txt     texty k vložení do ChatGPT / Copilotu
    .dodavatele-stav.json  co se dohledalo, aby druhý běh nemusel znovu na síť
"""

import csv
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, fields

import vystup
import zdroje
from zdroje import Firma, Klient, dohledej

VYSTUP = "dodavatele.xlsx"
ADRESAR_DAVEK = "davky"
STAV = ".dodavatele-stav.json"
VLAKEN = 8

# Rozpoznani sloupcu ve vstupu. Klic = nase pole, hodnoty = varianty hlavicky.
_SLOUPCE = {
    "nazev": ("nazev", "název", "name", "jmeno", "jméno", "firma", "dodavatel",
              "kreditor", "spolecnost", "společnost", "supplier", "creditor",
              "obchodni jmeno", "obchodní jméno", "lieferant", "kreditor name"),
    "adresa": ("adresa", "address", "sidlo", "sídlo", "ulice", "street",
               "adresa sidla", "adresa sídla", "anschrift"),
    "ico": ("ico", "ičo", "ic", "identifikacni cislo", "identifikační číslo",
            "reg c", "reg. č.", "company id"),
    "dic": ("dic", "dič", "vat", "vat id", "dph", "ustid", "ust id", "ust-idnr",
            "vat number", "tax id", "dic dph"),
    "zeme": ("zeme", "země", "country", "stat", "stát", "kod zeme", "kód země", "land"),
    "objem": ("objem", "obrat", "castka", "částka", "suma", "celkem", "amount",
              "hodnota", "umsatz", "abc"),
}


def _kanon(h):
    h = zdroje.bez_diakritiky(str(h or "")).strip().lower()
    return " ".join(h.replace("_", " ").split())


def _mapa_sloupcu(hlavicka):
    varianty = {c: {_kanon(v) for v in vs} for c, vs in _SLOUPCE.items()}
    mapa = {}
    for i, h in enumerate(hlavicka):
        k = _kanon(h)
        if not k:
            continue
        for cil, vs in varianty.items():
            if cil not in mapa and (k in vs or any(k.startswith(v + " ") for v in vs)):
                mapa[cil] = i
                break
    return mapa


def nacti_vstup(cesta):
    """CSV / XLSX / TXT -> seznam dictu. Bez rozpoznane hlavicky bere 1. sloupec."""
    pripona = os.path.splitext(cesta)[1].lower()
    if pripona in (".xlsx", ".xlsm"):
        try:
            from openpyxl import load_workbook
        except ImportError:
            raise SystemExit("Čtení XLSX vyžaduje openpyxl:  pip install openpyxl")
        wb = load_workbook(cesta, read_only=True, data_only=True)
        radky = [["" if b is None else str(b).strip() for b in r]
                 for r in wb.active.iter_rows(values_only=True)]
        wb.close()
    elif pripona == ".txt":
        with open(cesta, encoding="utf-8-sig") as f:
            radky = [[r.strip()] for r in f if r.strip()]
    else:
        with open(cesta, encoding="utf-8-sig", newline="") as f:
            vzorek = f.read(8192)
            f.seek(0)
            try:
                dialekt = csv.Sniffer().sniff(vzorek, delimiters=";,\t|")
            except csv.Error:
                dialekt = csv.excel
                dialekt.delimiter = ";" if vzorek.count(";") > vzorek.count(",") else ","
            radky = [list(r) for r in csv.reader(f, dialect=dialekt)]

    radky = [r for r in radky if any(str(b).strip() for b in r)]
    if not radky:
        return []
    mapa = _mapa_sloupcu(radky[0])
    datove = radky[1:] if "nazev" in mapa else radky
    if "nazev" not in mapa:
        mapa = {"nazev": 0}

    out, videno = [], set()
    for r in datove:
        def bunka(klic):
            i = mapa.get(klic)
            return str(r[i]).strip() if i is not None and i < len(r) and r[i] else ""
        nazev = bunka("nazev")
        if not nazev:
            continue
        # tyz dodavatel byva ve vypisu vickrat (vic uctu, vic obdobi)
        klic = (zdroje.normalizuj_nazev(nazev), zdroje._ico(bunka("ico")))
        if klic in videno:
            continue
        videno.add(klic)
        out.append({"nazev": nazev, "adresa": bunka("adresa"), "ico": bunka("ico"),
                    "dic": bunka("dic"), "zeme": bunka("zeme"), "objem": bunka("objem")})
    return out


# ---------------------------------------------------------------------------
# Mezistav - aby druhy beh nemusel znovu na sit
# ---------------------------------------------------------------------------

def uloz_stav(firmy, cesta=STAV):
    with open(cesta, "w", encoding="utf-8") as f:
        json.dump([asdict(x) for x in firmy], f, ensure_ascii=False)


def nacti_stav(cesta=STAV):
    if not os.path.exists(cesta):
        return []
    try:
        with open(cesta, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    povolena = {p.name for p in fields(Firma)}
    return [Firma(**{k: v for k, v in d.items() if k in povolena}) for d in data]


def _cesta_kese():
    zaklad = (os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CACHE_HOME")
              or os.path.join(os.path.expanduser("~"), ".cache"))
    adresar = os.path.join(zaklad, "dodavatele")
    os.makedirs(adresar, exist_ok=True)
    return os.path.join(adresar, "kes.json.gz")


# ---------------------------------------------------------------------------
# Behy
# ---------------------------------------------------------------------------

def beh_dohledani(vstup):
    radky = nacti_vstup(vstup)
    if not radky:
        raise SystemExit("Ve vstupu %s nejsou žádné použitelné řádky." % vstup)
    print("Načteno %d dodavatelů z %s" % (len(radky), vstup), file=sys.stderr)

    kes = _cesta_kese()
    print("Keš: %s" % kes, file=sys.stderr)
    klient = Klient(cache_soubor=kes)

    hotovo = [0]

    def uloha(radek):
        f = dohledej(klient, radek)
        hotovo[0] += 1
        if hotovo[0] % 25 == 0 or hotovo[0] == len(radky):
            print("  %d/%d dohledáno" % (hotovo[0], len(radky)), file=sys.stderr)
        return f

    try:
        with ThreadPoolExecutor(max_workers=VLAKEN) as ex:
            firmy = list(ex.map(uloha, radky))
    finally:
        klient.uloz_cache()

    uloz_stav(firmy)
    cesty = vystup.zapis_davky(firmy, ADRESAR_DAVEK)
    vystup.zapis_excel(firmy, {}, VYSTUP)

    poc = {}
    for f in firmy:
        poc[f.identita] = poc.get(f.identita, 0) + 1
    s_podklady = sum(1 for f in firmy if f.podklady())

    print("\nHotovo.", file=sys.stderr)
    print("  identita:  " + ", ".join("%s %d" % (k, v) for k, v in sorted(
        poc.items(), key=lambda kv: -kv[1])), file=sys.stderr)
    print("  podklady k činnosti: %d z %d firem" % (s_podklady, len(firmy)),
          file=sys.stderr)
    print("  dotazy: %d z keše, %d staženo" % (klient.z_kese, klient.stazeno),
          file=sys.stderr)
    print("\n  %s  (zatím bez kategorií)" % VYSTUP, file=sys.stderr)
    print("  %d dávek v %s/" % (len(cesty), ADRESAR_DAVEK), file=sys.stderr)
    print("\nDál: obsah každé dávky vložte do ChatGPT/Copilotu, odpověď uložte", file=sys.stderr)
    print("jako CSV do složky odpovedi/ a spusťte:  python3 %s odpovedi/"
          % os.path.basename(__file__), file=sys.stderr)


def beh_doplneni(adresar):
    firmy = nacti_stav()
    if not firmy:
        raise SystemExit(
            "Chybí %s – nejdřív spusťte dohledání:  python3 %s seznam.xlsx"
            % (STAV, os.path.basename(__file__)))
    odpovedi = vystup.nacti_odpovedi(adresar)
    if not odpovedi:
        raise SystemExit(
            "V %s nejsou žádné použitelné odpovědi. Čekám CSV s řádky "
            "'ID;Kód kategorie;Co dodává;Jistota'." % adresar)

    vystup.zapis_excel(firmy, odpovedi, VYSTUP)

    chybi = [i for i in range(1, len(firmy) + 1) if i not in odpovedi]
    nizka = sum(1 for o in odpovedi.values() if o.get("jistota", "").startswith("níz"))
    print("Doplněno %d z %d dodavatelů -> %s" % (len(odpovedi), len(firmy), VYSTUP),
          file=sys.stderr)
    if nizka:
        print("  z toho %d s nízkou jistotou – projděte ručně" % nizka, file=sys.stderr)
    if chybi:
        ukazka = ", ".join(str(i) for i in chybi[:15])
        print("  chybí odpověď u %d firem (ID: %s%s)"
              % (len(chybi), ukazka, " …" if len(chybi) > 15 else ""), file=sys.stderr)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1 or argv[0] in ("-h", "--help"):
        print(__doc__.strip(), file=sys.stderr)
        return 1
    cil = argv[0]
    if os.path.isdir(cil):
        beh_doplneni(cil)
    elif os.path.isfile(cil):
        beh_dohledani(cil)
    else:
        raise SystemExit("Soubor ani složka neexistuje: %s" % cil)
    return 0


if __name__ == "__main__":
    sys.exit(main())

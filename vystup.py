"""
Vystupy nastroje: davky pro LLM chat, nacteni jeho odpovedi a Excel se vzorci.

Excel je zamerne "zivy" - kategorie, skupina a ICT relevance nejsou zapsane
hodnoty, ale VLOOKUP do listu Ciselnik. Kdyz nekdo opravi kod kategorie,
prepocita se nazev, skupina, ICT priznak, kriticnost i rezim dle ISO 27001.
"""

import csv
import json
import os
import re

from taxonomie import KATEGORIE, VYCHOZI_KOD, ict_relevance

DAVKA = 250            # firem na jeden soubor pro chat
_KOD_RE = re.compile(r"\b[A-Z]{2,4}-\d{2}\b")

# Hodnoty rucne vyplnovanych sloupcu. Musi presne sedet na vzorce nize.
PRISTUP = ["žádný", "fyzický", "omezený", "privilegovaný"]
NAHRADITELNOST = ["snadná", "obtížná", "prakticky žádná"]
OBJEM = ["A", "B", "C"]
VZTAH = ["rámcová smlouva", "objednávky", "DPA", "NDA", "bez smlouvy"]

SLOUPCE = [
    ("Název ze vstupu", 34), ("Ověřený název", 34), ("Jistota identity", 15),
    ("IČO", 11), ("DIČ", 14), ("Země", 6), ("Město", 18), ("Web", 26),
    ("NACE", 14),
    ("Kód kategorie", 13), ("Kategorie", 34), ("Skupina", 30), ("ICT relevance", 13),
    ("Co dodává (LLM)", 44), ("Jistota zařazení", 14),
    ("Přístup k datům/systémům", 22), ("Nahraditelnost", 16),
    ("Objem (ABC)", 11), ("Typ vztahu", 18),
    ("Kritičnost", 16), ("Režim dle ISO 27001", 52),
    ("Poznámky nástroje", 40),
]
# indexy (1-based) klicovych sloupcu - at se vzorce nerozbiji pri zmene poradi
S_KOD, S_KATEG, S_SKUP, S_ICT = 10, 11, 12, 13
S_PRISTUP, S_NAHRAD, S_OBJEM, S_VZTAH = 16, 17, 18, 19
S_KRIT, S_ISO = 20, 21


def _pismeno(i):
    """1 -> A, 27 -> AA"""
    s = ""
    while i:
        i, z = divmod(i - 1, 26)
        s = chr(65 + z) + s
    return s


# ---------------------------------------------------------------------------
# Davky pro LLM chat
# ---------------------------------------------------------------------------

def _ciselnik_radky():
    radky, predchozi = [], None
    for kod, skupina, nazev in sorted(
            (k, v[0], v[1]) for k, v in KATEGORIE.items() if k != VYCHOZI_KOD):
        if skupina != predchozi:
            radky.append("  [%s]" % skupina)
            predchozi = skupina
        radky.append("    %s = %s" % (kod, nazev))
    return radky


ZADANI = """\
Jsi asistent pro audit dodavatelů podle ISO/IEC 27001 (příloha A, řízení
dodavatelských vztahů). Ke každé firmě níže urči:

  1. KÓD KATEGORIE z číselníku - podle toho, ČÍM SE FIRMA REÁLNĚ ZABÝVÁ,
     ne podle formálního zápisu v rejstříku. Zapsané obory jsou často
     zastaralé nebo obecné ("výroba, obchod a služby") - ber je jen jako
     vodítko. Když firmu znáš, použij i vlastní znalosti.
  2. CO DODÁVÁ - stručně vlastními slovy (pár slov až věta), ať jde
     zkontrolovat, že kód sedí.
  3. JISTOTU - vysoká / střední / nízká. Napiš "nízká" všude, kde odhaduješ
     z názvu nebo si nejsi jistý/á. Raději přiznaná nejistota než tichý omyl -
     na tenhle výstup navazuje audit.

Když o firmě nic nevíš, napiš kód XXX-00 a jistotu "nízká".

U každé firmy je v odrážkách kontext, který se podařilo dohledat ve veřejných
rejstřících a na webu. Pozor na řádek "identita" - hodnota "neověřeno" znamená,
že firmu nemáme potvrzenou z rejstříku a i název může být nepřesný.
"""

FORMAT = """\
Odpověz POUZE v CSV, jeden řádek na firmu, oddělovač ';', v tomto pořadí.
Bez hlavičky, bez uvozovek, bez textu okolo:

ID;Název firmy;Kód kategorie;Co dodává;Jistota

ID i název opiš přesně tak, jak jsou v seznamu - podle nich se odpověď páruje
zpět a nesoulad se pozná. Zpracuj všech %d firem. Když nestihneš všechny,
radši méně řádků, ale úplných - nikdy nevynechávej ID uprostřed.
"""


def _blok_firmy(cislo, f):
    hlava = "%d | %s" % (cislo, f.nazev or f.vstup_nazev)
    misto = ", ".join(x for x in (f.mesto, f.zeme) if x)
    if misto:
        hlava += " (%s)" % misto
    radky = [hlava, "   identita: %s" % f.identita]
    for stitek, text in f.podklady(strucne=True):
        radky.append("   %s: %s" % (stitek, text))
    return "\n".join(radky)


def zapis_davky(firmy, adresar):
    """Rozdeli firmy do souboru po DAVKA kusech. Vraci seznam cest."""
    os.makedirs(adresar, exist_ok=True)
    for star in os.listdir(adresar):
        if re.match(r"^davka_\d+\.txt$", star):
            os.remove(os.path.join(adresar, star))

    ciselnik = "\n".join(_ciselnik_radky())
    davky = [firmy[i:i + DAVKA] for i in range(0, len(firmy), DAVKA)] or [[]]
    cesty = []
    for i, davka in enumerate(davky, 1):
        cislo_od = (i - 1) * DAVKA + 1
        obsah = "\n".join([
            ZADANI,
            "ČÍSELNÍK KATEGORIÍ:",
            ciselnik,
            "",
            "FIRMY (%d, dávka %d z %d):" % (len(davka), i, len(davky)),
            "",
            "\n\n".join(_blok_firmy(cislo_od + j, f) for j, f in enumerate(davka)),
            "",
            FORMAT % len(davka),
        ])
        cesta = os.path.join(adresar, "davka_%02d.txt" % i)
        with open(cesta, "w", encoding="utf-8") as fh:
            fh.write(obsah)
        cesty.append(cesta)
    return cesty


# ---------------------------------------------------------------------------
# Nacteni odpovedi z chatu
# ---------------------------------------------------------------------------

def nacti_odpovedi(adresar, firmy=None):
    """
    Precte vsechny CSV/TXT v adresari a vrati (odpovedi, nesoulady), kde
    odpovedi = {id: {"kod","popis","jistota"}}.

    Radky bez rozpoznatelneho ID nebo kodu se preskoci - chat casto pripise
    uvodni vetu nebo hlavicku. Kdyz je zadany `firmy`, kontroluje se navic
    nazev: kdyby chat posunul cislovani, dostala by firma cizi kategorii
    a v auditu by se to poznalo hodne pozde. Takove radky se zahodi a vrati
    v `nesoulady`.
    """
    out, nesoulady = {}, []
    if not os.path.isdir(adresar):
        return out, nesoulady
    for jmeno in sorted(os.listdir(adresar)):
        if not jmeno.lower().endswith((".csv", ".txt")):
            continue
        with open(os.path.join(adresar, jmeno), encoding="utf-8-sig", newline="") as fh:
            vzorek = fh.read(4096)
            fh.seek(0)
            odd = ";" if vzorek.count(";") >= vzorek.count(",") else ","
            for radek in csv.reader(fh, delimiter=odd):
                if len(radek) < 2:
                    continue
                ident = re.match(r"^\s*(\d+)\s*$", (radek[0] or "").strip())
                if not ident:
                    continue
                # kod kategorie muze byt ve 2. nebo 3. sloupci podle toho,
                # jestli chat vratil i nazev firmy
                kod, i_kod = None, None
                for i in (1, 2):
                    if i < len(radek):
                        m = _KOD_RE.search((radek[i] or "").upper())
                        if m:
                            kod, i_kod = m.group(0), i
                            break
                if not kod:
                    continue

                cislo = int(ident.group(1))
                nazev_z_odpovedi = radek[1].strip() if i_kod == 2 else ""
                if firmy and nazev_z_odpovedi and not _nazev_sedi(
                        firmy, cislo, nazev_z_odpovedi):
                    ocekavany = (firmy[cislo - 1].nazev or firmy[cislo - 1].vstup_nazev
                                 if 1 <= cislo <= len(firmy) else "?")
                    nesoulady.append((cislo, nazev_z_odpovedi, ocekavany))
                    continue

                out[cislo] = {
                    "kod": kod,
                    "popis": (radek[i_kod + 1].strip() if len(radek) > i_kod + 1 else ""),
                    "jistota": (radek[i_kod + 2].strip().lower()
                                if len(radek) > i_kod + 2 else ""),
                }
    return out, nesoulady


def _nazev_sedi(firmy, cislo, nazev):
    """Odpovida nazev z odpovedi firme na tomhle poradovem cisle?"""
    if not 1 <= cislo <= len(firmy):
        return False
    f = firmy[cislo - 1]
    from zdroje import skore_shody
    return max(skore_shody(nazev, f.vstup_nazev),
               skore_shody(nazev, f.nazev or f.vstup_nazev)) >= 0.75


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------

def _vzorec_kriticnost(r):
    """
    Kriticnost dodavatele. Rozhoduje pristup k datum/systemum (ISO 27001
    A.5.19-A.5.22), ICT povaha dodavky a nahraditelnost. Objem je az doplnkove
    kriterium - levny dodavatel s privilegovanym pristupem je rizikovejsi nez
    drahy dodavatel kancelarskych potreb.
    """
    kod, ict = "$%s%d" % (_pismeno(S_KOD), r), "$%s%d" % (_pismeno(S_ICT), r)
    pri, nah = "$%s%d" % (_pismeno(S_PRISTUP), r), "$%s%d" % (_pismeno(S_NAHRAD), r)
    obj = "$%s%d" % (_pismeno(S_OBJEM), r)
    return (
        '=IF({kod}="","nezařazeno",'
        'IF({pri}="","⟵ doplňte přístup",'
        'IF(OR({pri}="privilegovaný",'
        'AND({ict}="ano",{pri}="omezený"),'
        '{nah}="prakticky žádná"),"KRITICKÝ",'
        'IF(OR({ict}="ano",{pri}="omezený",{nah}="obtížná",{obj}="A"),'
        '"VÝZNAMNÝ","BĚŽNÝ"))))'
    ).format(kod=kod, ict=ict, pri=pri, nah=nah, obj=obj)


def _vzorec_iso(r):
    krit, ict = "$%s%d" % (_pismeno(S_KRIT), r), "$%s%d" % (_pismeno(S_ICT), r)
    return (
        '=IF({krit}="KRITICKÝ",IF({ict}="ano",'
        '"Prověření dodavatele, bezpečnostní požadavky ve smlouvě vč. DPA, '
        'právo auditu, průběžný monitoring",'
        '"Prověření dodavatele, smluvní záruky, průběžný monitoring"),'
        'IF({krit}="VÝZNAMNÝ","Zjednodušené prověření, bezpečnostní doložka ve smlouvě",'
        'IF({krit}="BĚŽNÝ","Vedení v evidenci, bez dalších požadavků","")))'
    ).format(krit=krit, ict=ict)


def _vlookup(r, sloupec):
    # nazev listu v apostrofech - s diakritikou to nekterym tabulkovym
    # procesorum bez uvozeni vadi
    return "=IFERROR(VLOOKUP($%s%d,'Číselník'!$A:$D,%d,FALSE),\"\")" % (
        _pismeno(S_KOD), r, sloupec)


def zapis_excel(firmy, odpovedi, cesta):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
        from openpyxl.worksheet.datavalidation import DataValidation
    except ImportError:
        raise SystemExit(
            "Zápis XLSX vyžaduje openpyxl:  pip install openpyxl")

    wb = Workbook()

    # -- list Číselník (zdroj pro VLOOKUP i rozbalovací seznamy) -----------
    ws_c = wb.active
    ws_c.title = "Číselník"
    ws_c.append(["Kód", "Kategorie", "Skupina", "ICT relevance"])
    for kod, (skupina, nazev) in sorted(KATEGORIE.items()):
        ws_c.append([kod, nazev, skupina, ict_relevance(kod)])
    for i, sirka in enumerate((14, 44, 34, 14), 1):
        ws_c.column_dimensions[get_column_letter(i)].width = sirka

    # -- list Dodavatelé --------------------------------------------------
    ws = wb.create_sheet("Dodavatelé", 0)
    ws.append([n for n, _ in SLOUPCE])
    for i, (_, sirka) in enumerate(SLOUPCE, 1):
        ws.column_dimensions[get_column_letter(i)].width = sirka

    for cislo, f in enumerate(firmy, 1):
        odp = odpovedi.get(cislo) or {}
        r = cislo + 1
        ws.append([
            f.vstup_nazev,
            f.nazev if f.nazev != f.vstup_nazev else "",
            f.identita,
            f.ico, f.dic, f.zeme, f.mesto, f.web,
            ", ".join(f.nace[:6]),
            odp.get("kod", ""),
            _vlookup(r, 2), _vlookup(r, 3), _vlookup(r, 4),
            odp.get("popis", ""), odp.get("jistota", ""),
            "", "", f.vstup_objem, "",
            _vzorec_kriticnost(r), _vzorec_iso(r),
            "; ".join(f.poznamky),
        ])

    posledni = len(firmy) + 1

    # hlavicka
    vypln = PatternFill("solid", fgColor="1F3864")
    for b in ws[1]:
        b.font = Font(bold=True, color="FFFFFF")
        b.fill = vypln
        b.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 30
    ws.freeze_panes = "C2"
    if posledni > 1:
        ws.auto_filter.ref = "A1:%s%d" % (_pismeno(len(SLOUPCE)), posledni)

    # rucne vyplnovane sloupce - jine pozadi, at je videt, co ceka na cloveka
    rucni = PatternFill("solid", fgColor="FFF2CC")
    for sl in (S_PRISTUP, S_NAHRAD, S_OBJEM, S_VZTAH):
        ws.cell(1, sl).fill = PatternFill("solid", fgColor="BF8F00")
        for r in range(2, posledni + 1):
            ws.cell(r, sl).fill = rucni

    # rozbalovaci seznamy
    for sl, hodnoty in ((S_PRISTUP, PRISTUP), (S_NAHRAD, NAHRADITELNOST),
                        (S_OBJEM, OBJEM), (S_VZTAH, VZTAH)):
        dv = DataValidation(type="list", formula1='"%s"' % ",".join(hodnoty),
                            allow_blank=True, showDropDown=False)
        ws.add_data_validation(dv)
        dv.add("%s2:%s%d" % (_pismeno(sl), _pismeno(sl), max(posledni, 2)))

    for r in range(2, posledni + 1):
        ws.cell(r, S_KRIT).font = Font(bold=True)
        for sl in (S_KATEG, 14, S_ISO):
            ws.cell(r, sl).alignment = Alignment(wrap_text=True, vertical="top")

    # -- list Souhrn ------------------------------------------------------
    ws_s = wb.create_sheet("Souhrn")
    def _rozsah(sloupec):
        pis = _pismeno(sloupec)
        return "'Dodavatelé'!$%s$2:$%s$%d" % (pis, pis, posledni)

    kr, ic, kod = _rozsah(S_KRIT), _rozsah(S_ICT), _rozsah(S_KOD)
    ident = "'Dodavatelé'!$C$2:$C$%d" % posledni

    ws_s.append(["Přehled", ""])
    ws_s.append(["Dodavatelů celkem", len(firmy)])
    ws_s.append(["Zařazeno LLM", '=COUNTIF(%s,"<>")' % kod])
    ws_s.append(["Nezařazeno (XXX-00)", '=COUNTIF(%s,"XXX-00")' % kod])
    ws_s.append([])
    ws_s.append(["Identita", ""])
    for h in ("rejstřík", "VIES (DIČ)", "podle názvu", "neověřeno"):
        ws_s.append([h, '=COUNTIF(%s,"%s")' % (ident, h)])
    ws_s.append([])
    ws_s.append(["ICT relevance", ""])
    for h in ("ano", "hraniční", "ne"):
        ws_s.append([h, '=COUNTIF(%s,"%s")' % (ic, h)])
    ws_s.append([])
    ws_s.append(["Kritičnost", ""])
    for h in ("KRITICKÝ", "VÝZNAMNÝ", "BĚŽNÝ"):
        ws_s.append([h, '=COUNTIF(%s,"%s")' % (kr, h)])
    ws_s.append(["nevyplněno", '=COUNTIF(%s,"⟵*")' % kr])
    ws_s.append([])
    ws_s.append(["Kritických s ICT vazbou",
                 '=COUNTIFS(%s,"KRITICKÝ",%s,"ano")' % (kr, ic)])
    for radek in ws_s.iter_rows():
        if radek[0].value and not str(radek[0].value).startswith("="):
            if radek[1].value in (None, ""):
                radek[0].font = Font(bold=True, size=12)
    ws_s.column_dimensions["A"].width = 30
    ws_s.column_dimensions["B"].width = 14

    # -- list Podklady (proc to LLM zaradilo takhle) ----------------------
    ws_p = wb.create_sheet("Podklady")
    ws_p.append(["#", "Název", "Zdroj", "Text"])
    for cislo, f in enumerate(firmy, 1):
        for stitek, text in f.podklady():
            ws_p.append([cislo, f.nazev or f.vstup_nazev, stitek, text])
    for b in ws_p[1]:
        b.font = Font(bold=True)
    for i, sirka in enumerate((6, 34, 14, 120), 1):
        ws_p.column_dimensions[get_column_letter(i)].width = sirka

    wb.save(cesta)

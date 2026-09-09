"""
Kontrola vzorcu v Excelu. Vzorce nejde spustit bez Excelu, tak se tu jejich
logika prepocita v Pythonu podle stejne tabulky pravidel a porovna s tim, co
ma vyjit. Chrani pred tichou zmenou pravidel kritickosti.

    python3 test_vzorce.py
"""

import re
import sys

import vystup
from taxonomie import KATEGORIE, ict_relevance


def kriticnost(ict, pristup, nahraditelnost, objem, kod="ICT-01"):
    """Tataz pravidla jako _vzorec_kriticnost - drzet synchronne."""
    if not kod:
        return "nezařazeno"
    if not pristup:
        return "⟵ doplňte přístup"
    if (pristup == "privilegovaný"
            or (ict == "ano" and pristup == "omezený")
            or nahraditelnost == "prakticky žádná"):
        return "KRITICKÝ"
    if ict == "ano" or pristup == "omezený" or nahraditelnost == "obtížná" or objem == "A":
        return "VÝZNAMNÝ"
    return "BĚŽNÝ"


PRIPADY = [
    # (ICT, přístup, nahraditelnost, objem) -> očekáváno
    (("ano", "privilegovaný", "snadná", "C"), "KRITICKÝ"),
    (("ne", "privilegovaný", "snadná", "C"), "KRITICKÝ"),   # přístup rozhoduje i bez ICT
    (("ano", "omezený", "snadná", "C"), "KRITICKÝ"),        # ICT + přístup k datům
    (("ne", "omezený", "snadná", "C"), "VÝZNAMNÝ"),
    (("ne", "žádný", "prakticky žádná", "C"), "KRITICKÝ"),  # single point of failure
    (("ano", "žádný", "snadná", "C"), "VÝZNAMNÝ"),
    (("ne", "žádný", "obtížná", "C"), "VÝZNAMNÝ"),
    (("ne", "fyzický", "snadná", "A"), "VÝZNAMNÝ"),         # velký objem
    (("ne", "fyzický", "snadná", "C"), "BĚŽNÝ"),
    (("ne", "žádný", "snadná", "B"), "BĚŽNÝ"),
    (("ano", "", "snadná", "A"), "⟵ doplňte přístup"),      # bez ručního vstupu nepočítá
]


def _zkontroluj_syntaxi(vzorec, jmeno):
    """Zavorky a uvozovky musi sedet - preklep by Excel ohlasil az u uzivatele."""
    chyby = []
    if vzorec.count("(") != vzorec.count(")"):
        chyby.append("%s: nesedí závorky" % jmeno)
    if vzorec.count('"') % 2:
        chyby.append("%s: lichý počet uvozovek" % jmeno)
    if not vzorec.startswith("="):
        chyby.append("%s: nezačíná '='" % jmeno)
    return chyby


def _test_nacitani_odpovedi():
    """Čtení odpovědí z chatu: formát, tolerance k šumu, kontrola párování."""
    import os
    import tempfile

    class _F:
        def __init__(self, n):
            self.vstup_nazev = self.nazev = n

    firmy = [_F("Alza.cz a.s."), _F("GABEN, spol. s r. o."), _F("ESET, spol. s r.o.")]
    chyby = []

    def _precti(obsah, s_kontrolou=True):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "o.csv"), "w", encoding="utf-8") as f:
                f.write(obsah)
            return vystup.nacti_odpovedi(d, firmy if s_kontrolou else None)

    # správně spárovaná odpověď
    odp, nes = _precti("1;Alza.cz a.s.;OBH-01;e-shop;vysoká\n"
                       "2;GABEN, spol. s r. o.;ICT-08;RFID;vysoká\n")
    if len(odp) != 2 or nes:
        chyby.append("správná odpověď: %d řádků, %d nesouladů" % (len(odp), len(nes)))
    if odp.get(1, {}).get("kod") != "OBH-01" or odp.get(1, {}).get("popis") != "e-shop":
        chyby.append("špatně rozparsovaný řádek: %r" % odp.get(1))

    # posunuté číslování se musí zachytit, ne tiše přiřadit
    odp, nes = _precti("1;GABEN, spol. s r. o.;ICT-08;RFID;vysoká\n")
    if odp or len(nes) != 1:
        chyby.append("posunuté ID se nezachytilo (%d řádků, %d nesouladů)"
                     % (len(odp), len(nes)))

    # starší formát bez názvu musí pořád fungovat
    odp, nes = _precti("1;OBH-01;e-shop;vysoká\n")
    if odp.get(1, {}).get("kod") != "OBH-01":
        chyby.append("formát bez názvu firmy se nepřečetl: %r" % odp)

    # hlavička a povídání okolo se přeskočí
    odp, nes = _precti("Tady je výsledek:\nID;Název;Kód;Co dodává;Jistota\n"
                       "3;ESET, spol. s r.o.;ICT-05;antivirus;vysoká\n")
    if odp.get(3, {}).get("kod") != "ICT-05":
        chyby.append("šum okolo odpovědi se nepřeskočil: %r" % odp)

    # drobná odchylka v názvu se tolerovat má (chat občas zkrátí)
    odp, nes = _precti("1;Alza.cz;OBH-01;e-shop;vysoká\n")
    if not odp:
        chyby.append("zkrácený název se neuznal jako shoda")
    return chyby


def main():
    chyby = _test_nacitani_odpovedi()

    # 1) logika kritičnosti
    for vstup, cekano in PRIPADY:
        skutecnost = kriticnost(*vstup)
        if skutecnost != cekano:
            chyby.append("kritičnost%s = %r, čekáno %r" % (vstup, skutecnost, cekano))

    # 2) syntaxe vzorců
    for jmeno, vzorec in (("kritičnost", vystup._vzorec_kriticnost(2)),
                          ("ISO režim", vystup._vzorec_iso(2)),
                          ("VLOOKUP", vystup._vlookup(2, 2))):
        chyby += _zkontroluj_syntaxi(vzorec, jmeno)

    # 3) vzorce musí odkazovat na sloupce, které opravdu existují
    pocet = len(vystup.SLOUPCE)
    for jmeno, sl in (("KÓD", vystup.S_KOD), ("KATEGORIE", vystup.S_KATEG),
                      ("SKUPINA", vystup.S_SKUP), ("ICT", vystup.S_ICT),
                      ("PŘÍSTUP", vystup.S_PRISTUP), ("NAHRADITELNOST", vystup.S_NAHRAD),
                      ("OBJEM", vystup.S_OBJEM), ("VZTAH", vystup.S_VZTAH),
                      ("KRITIČNOST", vystup.S_KRIT), ("ISO", vystup.S_ISO)):
        if not 1 <= sl <= pocet:
            chyby.append("index sloupce %s (%d) je mimo rozsah 1..%d" % (jmeno, sl, pocet))

    ocekavane = {vystup.S_KOD: "Kód kategorie", vystup.S_ICT: "ICT relevance",
                 vystup.S_PRISTUP: "Přístup k datům/systémům",
                 vystup.S_NAHRAD: "Nahraditelnost", vystup.S_OBJEM: "Objem (ABC)",
                 vystup.S_VZTAH: "Typ vztahu", vystup.S_KRIT: "Kritičnost",
                 vystup.S_ISO: "Režim dle ISO 27001"}
    for sl, nazev in ocekavane.items():
        skutecny = vystup.SLOUPCE[sl - 1][0]
        if skutecny != nazev:
            chyby.append("sloupec %d je %r, čekán %r" % (sl, skutecny, nazev))

    # 4) hodnoty v rozbalovacích seznamech musí odpovídat vzorcům
    vzorec = vystup._vzorec_kriticnost(2)
    for hodnota in ("privilegovaný", "omezený"):
        if hodnota not in vystup.PRISTUP:
            chyby.append("vzorec zná přístup %r, ale není v nabídce" % hodnota)
    for hodnota in ("prakticky žádná", "obtížná"):
        if hodnota not in vystup.NAHRADITELNOST:
            chyby.append("vzorec zná nahraditelnost %r, ale není v nabídce" % hodnota)
    # jen hodnoty, se kterymi se doopravdy POROVNAVA (za '='), ne navratove texty
    for hodnota in re.findall(r'=\s*"([^"]*)"', vzorec):
        if hodnota in ("", "ano"):
            continue
        if hodnota not in vystup.PRISTUP + vystup.NAHRADITELNOST + vystup.OBJEM:
            chyby.append("vzorec porovnává s %r, což není v žádné nabídce" % hodnota)

    # 5) řídicí znaky z webů a rejstříků nesmí projít do buňky - XLSX je
    #    nedovoluje a openpyxl na nich padal až při ukládání, po celém běhu
    spinave = "ACME\x01 s.r.o.\x07\x1f test\x0b\x9d"
    ciste = vystup._bunka(spinave)
    if vystup._RIDICI.search(ciste):
        chyby.append("_bunka nechala řídicí znak v %r" % ciste)
    if "ACME" not in ciste or "test" not in ciste:
        chyby.append("_bunka zahodila i čitelný text: %r" % ciste)
    dlouhy = vystup._bunka("x" * 40000)
    if len(dlouhy) > 32767:
        chyby.append("_bunka nezkrátila text na limit Excelu (%d znaků)" % len(dlouhy))
    if vystup._bunka(7) != 7 or vystup._bunka(None) is not None:
        chyby.append("_bunka mrší nestringové hodnoty")

    # 6) ICT relevance musí mít každá kategorie z číselníku
    bez_ict = [k for k in KATEGORIE if k != "XXX-00" and not ict_relevance(k)]
    if bez_ict:
        chyby.append("kategorie bez ICT příznaku: %s" % ", ".join(sorted(bez_ict)))

    if chyby:
        print("CHYBY (%d):" % len(chyby))
        for c in chyby:
            print("  ✗ %s" % c)
        return 1
    print("OK: %d případů kritičnosti, syntaxe vzorců, indexy sloupců, "
          "číselník (%d kategorií), čtení odpovědí z chatu, čištění buněk"
          % (len(PRIPADY), len(KATEGORIE)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

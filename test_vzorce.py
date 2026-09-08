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


def main():
    chyby = []

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

    # 5) ICT relevance musí mít každá kategorie z číselníku
    bez_ict = [k for k in KATEGORIE if k != "XXX-00" and not ict_relevance(k)]
    if bez_ict:
        chyby.append("kategorie bez ICT příznaku: %s" % ", ".join(sorted(bez_ict)))

    if chyby:
        print("CHYBY (%d):" % len(chyby))
        for c in chyby:
            print("  ✗ %s" % c)
        return 1
    print("OK: %d případů kritičnosti, syntaxe vzorců, indexy sloupců, "
          "číselník (%d kategorií)" % (len(PRIPADY), len(KATEGORIE)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

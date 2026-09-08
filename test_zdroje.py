"""
Kontrola dohledavani - normalizace nazvu, odhad domeny a rozhodovani, jestli
nalezena stranka firme opravdu patri. Bezi bez site.

    python3 test_zdroje.py
"""

import sys

import zdroje
from zdroje import Firma, _dohad_domeny, _stranka_sedi, _tokeny_nazvu, skore_shody


def _firma(nazev, zeme="CZ", ico=""):
    f = Firma(vstup_nazev=nazev, vstup_zeme=zeme, ico=ico)
    f.zeme = zeme
    return f


# (název, země) -> očekávaná doména. None = nehádat vůbec.
DOMENY = [
    ("TESLA Blatná, a.s.", "CZ", "teslablatna.cz"),
    ("PRIMA BILAVČÍK, s.r.o.", "CZ", "primabilavcik.cz"),
    # z názvu nesmí vypadnout "Contact" - phoenix.de je německá televize
    ("Phoenix Contact GmbH & Co. KG", "DE", "phoenixcontact.de"),
    # "spol" je právní forma, ne část jména
    ("WAGO-Elektro spol. s r.o.", "CZ", "wagoelektro.cz"),
    ("Siemens, s.r.o.", "CZ", "siemens.cz"),
    ("Cloudflare, Inc.", "US", "cloudflare.com"),
]

# (název, text stránky, HTML, síla domény) -> má se přijmout?
STRANKY = [
    # doména z celého názvu + stránka firmu zmiňuje = v pořádku
    ("TESLA Blatná, a.s.", "TESLA Blatná - výroba relé a konektorů", "", 2, True),
    # doména z jednoho slova: samotné "phoenix" nestačí (televize má taky)
    ("Phoenix Contact GmbH", "phoenix - Das Ereignis- und Dokumentationsprogramm",
     "", 1, False),
    # to samé, ale stránka zmiňuje i druhé slovo názvu = v pořádku
    ("Phoenix Contact GmbH", "Phoenix Contact | Automatisierung und Verbindungstechnik",
     "", 1, True),
    # stránka o něčem úplně jiném se nepřijme
    ("PRIMA BILAVČÍK, s.r.o.", "Vítejte na stránkách obce Dolní Lhota", "", 2, False),
    # jednoslovný název: stačí jeden zásah
    ("Cloudflare, Inc.", "Cloudflare - connect, protect and build", "", 1, True),
    # viditelný text píše název s mezerou, ale v HTML je jedním slovem
    ("AutoESA a.s.", "Auto ESA - prodej ojetých vozů",
     '<link href="https://www.autoesa.cz/">', 1, True),
    # parkovaná doména název firmy neobsahuje nikde
    ("TESLA Blatná, a.s.", "", '<iframe src="https://parking.vedos.cz/">', 2, False),
]

SHODY = [
    ("Alza.cz a.s.", "Alza.cz a.s.", 1.0, 1.0),
    ("Kooperativa pojišťovna, a.s.", "Kooperativa pojišťovna, a.s., Vienna Insurance Group",
     0.80, 1.0),
    ("Siemens, s.r.o.", "Siemens Mobility, s.r.o.", 0.0, 0.90),   # jiná firma
    ("ESET, spol. s r.o.", "RESET, spol. s r.o.", 0.0, 0.90),     # nesmí splynout
]


def main():
    chyby = []

    for nazev, zeme, cekano in DOMENY:
        domena, sila = _dohad_domeny(_firma(nazev, zeme))
        if domena != cekano:
            chyby.append("doména %r -> %r, čekáno %r" % (nazev, domena, cekano))
        if domena and sila < 1:
            chyby.append("doména %r má sílu 0" % nazev)

    for nazev, text, htmls, sila, cekano in STRANKY:
        skutecnost = _stranka_sedi(_firma(nazev), text, htmls, sila)
        if skutecnost != cekano:
            chyby.append("stránka %r pro %r: %s, čekáno %s"
                         % ((text or htmls)[:34], nazev, skutecnost, cekano))

    # IČO na stránce přebije všechno ostatní
    f = _firma("Jakákoli Firma s.r.o.")
    f.ico = "12345678"
    if not _stranka_sedi(f, "úplně jiný text", "kontakt IČO 12345678", 1):
        chyby.append("IČO na stránce se neuznalo jako důkaz")

    for a, b, dolni, horni in SHODY:
        s = skore_shody(a, b)
        if not dolni <= s <= horni:
            chyby.append("skóre %r vs %r = %.3f, čekáno %.2f–%.2f" % (a, b, s, dolni, horni))

    # výplňová slova nesmí zůstat v tokenech názvu
    for nazev, nesmi in (("Phoenix Contact GmbH & Co. KG", "and"),
                         ("WAGO-Elektro spol. s r.o.", "spol"),
                         ("Bosch Group Czech s.r.o.", "group")):
        if nesmi in _tokeny_nazvu(nazev):
            chyby.append("token %r zůstal v názvu %r" % (nesmi, nazev))

    # zkracování podkladů nesmí useknout uprostřed slova
    dlouhy = "První věta o firmě. Druhá věta pokračuje dál a je delší než limit."
    kratky = zdroje._zkrat(dlouhy, 30)
    if len(kratky) > 31 or kratky.endswith(" "):
        chyby.append("zkrácení dalo %r" % kratky)

    if chyby:
        print("CHYBY (%d):" % len(chyby))
        for c in chyby:
            print("  ✗ %s" % c)
        return 1
    print("OK: %d domén, %d stránek, %d skóre shody, výplňová slova, zkracování"
          % (len(DOMENY), len(STRANKY), len(SHODY)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

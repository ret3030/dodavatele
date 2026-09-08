"""
Normalizace textu pro porovnavani frazi a nazvu firem.

Zamerne jednoducha a deterministicka: bez diakritiky, mala pismena, vse
mimo [0-9a-z] je mezera, vicenasobne mezery se slucuji. Stejny postup
plati pro text ze SERP i pro fraze v pravidlech - jinak by se neshodly.
"""

import re
import unicodedata

_NEALNUM = re.compile(r"[^0-9a-z]+")
_MEZERY = re.compile(r"\s+")

# Pravni formy a uplne obecna slova - pri tvorbe klice nazvu se zahazuji,
# aby "ABB s.r.o." a "ABB" (nebo "ABB, spol. s r.o.") daly stejny klic.
_PRAVNI_FORMY = {
    "s", "r", "o", "sro", "spol", "a", "as", "k", "v", "z", "os",
    "se", "ses", "druzstvo", "podnik", "statni",
    "gmbh", "ag", "kg", "co", "inc", "corp", "corporation", "ltd", "limited",
    "llc", "plc", "sa", "sas", "sarl", "nv", "bv", "oy", "ab", "as2",
    "kft", "sp", "zoo", "srl", "spa", "aktiengesellschaft", "kgaa",
}


def bez_diakritiky(text):
    return "".join(
        c for c in unicodedata.normalize("NFKD", text or "")
        if not unicodedata.combining(c)
    )


# Lehky cesky/slovensky stemmer - orizne bezne padove/cislo koncovky, aby
# "vyrobce kondenzatoru" sedlo na frazi "vyroba kondenzatory". Neni jazykove
# presny, jde jen o to, aby text i fraze skoncily stejne. Kratke tokeny (<5)
# a kratke pahyly (<4) se nechavaji byt.
_KONCOVKY = (
    "oveho", "ovemu", "ovych", "ackych", "nich", "ymi", "ych", "ich",
    "ami", "emi", "imi", "ove", "ova", "ovi", "osti", "ost", "ech", "ce", "um",
)


def _stem(token):
    if len(token) < 5:
        return token
    for suf in _KONCOVKY:
        if token.endswith(suf) and len(token) - len(suf) >= 4:
            return token[:-len(suf)]
    if token[-1] in "aeiouy" and len(token) >= 5:
        return token[:-1]
    return token


def _zaklad(text):
    text = _NEALNUM.sub(" ", bez_diakritiky(text).lower())
    text = _MEZERY.sub(" ", text).strip()
    return " ".join(_stem(t) for t in text.split()) if text else text


def normalizuj_text(text):
    """Text pripraveny na hledani frazi - obaleny mezerami kvuli hranicim slov."""
    return " " + _zaklad(text) + " "


def normalizuj_frazi(fraze):
    """Fraze z pravidel - stejny zaklad jako text, ale bez obalovych mezer."""
    return _zaklad(fraze)


def klic_nazvu(nazev):
    """
    Klic pro parovani stejne firmy mezi soubory (vstup vs. gold, predikce vs.
    gold). Zahodi pravni formy a interpunkci, necha poradi slov.
    """
    slova = [s for s in _zaklad(nazev).split() if s and s not in _PRAVNI_FORMY]
    return " ".join(slova)


def nazev_tokeny(nazev):
    """Vyznamove tokeny nazvu (>= 3 znaky, bez pravnich forem) - pro odhad, ktery
    web v SERP vysledcich patri primo firme."""
    return [
        s for s in _zaklad(nazev).split()
        if len(s) >= 3 and s not in _PRAVNI_FORMY
    ]

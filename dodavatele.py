#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dodavatele.py - obohaceni seznamu dodavatelu z verejnych rejstriku.

Vstup : CSV / XLSX / TXT se seznamem nazvu firem (volitelne ICO, DIC, zeme).
Vystup: XLSX / CSV se sloupci
        Jmeno | Ulice | PSC | Mesto | Zeme | ICO | DIC | NACE
        | Kategorie dodavatele | ...

Zdroje (vse bez API klice):
  ARES     ares.gov.cz            CR - plny rejstrik vc. NACE a DIC
  RPO SR   api.statistics.sk      SR - registr pravnickych osob
  GLEIF    api.gleif.org          svet - entity s LEI, narodni registracni cislo
  SEC      sec.gov                US - spolecnosti registrovane u SEC (+ SIC)
  Wikidata wikidata.org           zalozni zdroj oboru, DIC a sidla pro velke firmy
  VIES     ec.europa.eu           overeni DIC v ramci EU

Zavislosti: pouze standardni knihovna (openpyxl jen pro praci s XLSX).
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import re
import ssl
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taxonomie

UA = "supplier-lookup/1.0 (kontakt: nakup@example.com)"

ARES_HLEDAT = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/vyhledat"
ARES_DETAIL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ico}"
ARES_RES = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty-res/{ico}"
ARES_VR = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty-vr/{ico}"
RPO_SK = "https://api.statistics.sk/rpo/v1/search"
GLEIF_API = "https://api.gleif.org/api/v1/lei-records"
GLEIF_AUTO = "https://api.gleif.org/api/v1/autocompletions"
VIES_API = "https://ec.europa.eu/taxation_customs/vies/rest-api/ms/{cc}/vat/{num}"
EDGAR_API = "https://www.sec.gov/cgi-bin/browse-edgar"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
INSEE_FR = "https://recherche-entreprises.api.gouv.fr/search"
SG_ACRA = "https://data.gov.sg/api/action/datastore_search"
SG_ACRA_ZDROJ = "d_3f960c10fed6145404ca7b821f263b87"
TW_GCIS = "https://data.gcis.nat.gov.tw/od/data/api/6BBA2268-1367-4B42-9CCA-BC17499EBE8C"

_TW_SSL_KONTEXT = None


def tw_ssl_kontext():
    """
    Certifikat data.gcis.nat.gov.tw postrada rozsireni Subject Key Identifier,
    ktere novejsi OpenSSL/Python defaultne vyzaduje (VERIFY_X509_STRICT).
    Overeni retezce duvery a jmena hostitele zustava aktivni - vypina se jen
    tato jedna nadstandardni RFC 5280 kontrola, ktera zpusobuje, ze pripojeni
    ze standardniho urllib kontextu vzdy selze, i kdyz je server v poradku
    (napr. curl tuto kontrolu vubec neprovadi, proto tam problem videt neni).
    """
    global _TW_SSL_KONTEXT
    if _TW_SSL_KONTEXT is None:
        ctx = ssl.create_default_context()
        ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
        _TW_SSL_KONTEXT = ctx
    return _TW_SSL_KONTEXT

EU_STATY = {"AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "GR", "ES", "FI", "FR",
            "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE",
            "SI", "SK", "XI"}

PRAVNI_FORMY = {
    "as", "a s", "akciova spolecnost", "sro", "s r o", "spol s r o",
    "spolecnost s rucenim omezenym", "ks", "vos", "zs", "ops", "sp", "se", "statni podnik",
    "zapsany spolek", "zu", "odstepny zavod",
    "gmbh", "mbh", "ag", "kg", "kgaa", "ohg", "ug", "eg", "ev", "gbr", "co kg", "se co kg",
    "aktiengesellschaft", "gesellschaft mit beschrankter haftung", "kommanditgesellschaft",
    "aktiebolag", "aktieselskab", "naamloze vennootschap", "besloten vennootschap",
    "societe anonyme", "societa per azioni", "sociedad anonima",
    "akciova spolocnost", "spolocnost s rucenim obmedzenym",
    "bv", "nv", "cv", "vof", "sa", "sas", "sasu", "sarl", "eurl", "sci",
    "srl", "spa", "snc", "sl", "slu", "sau",
    "ltd", "limited", "plc", "llp", "lp", "llc", "inc", "incorporated", "corp",
    "corporation", "company", "co", "holding", "holdings", "group", "groupe", "gruppe",
    "oy", "oyj", "ab", "aps", "asa", "kft", "zrt", "nyrt", "bt", "kkt",
    "sp z oo", "spzoo", "z oo", "doo", "dooel", "dd", "ood", "eood", "ad", "ead",
    "lda", "unipessoal", "kk", "yk", "pte", "pty", "bhd", "sdn", "akciova spolocnost",
    # viceslovne narodni formy - bez nich se "ORLEN S.A." neshodne
    # s "ORLEN SPOLKA AKCYJNA" ani "Vodafone Group Plc" s "VODAFONE GROUP
    # PUBLIC LIMITED COMPANY"
    "public limited company", "public company limited", "company limited", "co ltd",
    "joint stock company", "designated activity company", "dac",
    "spolka akcyjna", "spolka z ograniczona odpowiedzialnoscia", "sp z o o",
    "societa per azioni", "societa a responsabilita limitata",
    "sociedad anonima unipersonal", "sociedade anonima",
    "societe par actions simplifiee", "societe a responsabilite limitee",
    "anonim sirketi", "anonim ortakligi", "limited sirketi", "sirketi",
    "reszvenytarsasag", "nyilvanosan mukodo reszvenytarsasag",
    "societate pe actiuni", "societate cu raspundere limitata",
    "kabushiki kaisha", "berhad", "sendirian berhad",
    "naamloze vennootschap", "besloten vennootschap",
    "publikt aktiebolag", "aktiengesellschaft", "eingetragener verein",
}

STAV_OK = "OK"
STAV_VYBRANO = "VYBRANO"        # vice srovnatelnych shod, nastroj vybral nejlepsi
STAV_OVERIT = "OVERIT"
STAV_NENALEZENO = "NENALEZENO"
STAV_CHYBA = "CHYBA"


# ---------------------------------------------------------------------------
# HTTP vrstva: rate limit na host, opakovani pri chybe, cache na disku
# ---------------------------------------------------------------------------

class Klient:
    def __init__(self, cache_soubor=None, prodleva=0.25, pokusy=3, timeout=25, ua=UA):
        self.prodleva = prodleva
        self.pokusy = pokusy
        self.timeout = timeout
        self.ua = ua
        self._zamek = threading.Lock()
        self._posledni = {}
        self._cache_soubor = cache_soubor
        self._cache = {}
        self._zmenena = False
        if cache_soubor and os.path.exists(cache_soubor):
            try:
                with self._otevri(cache_soubor, "rt") as f:
                    self._cache = json.load(f)
            except Exception:
                self._cache = {}

    def _otevri(self, cesta, rezim):
        """Kes s priponou .gz se komprimuje (odpovedi rejstriku jsou objemne)."""
        if self._cache_soubor and self._cache_soubor.endswith(".gz"):
            return gzip.open(cesta, rezim, encoding="utf-8")
        return open(cesta, rezim, encoding="utf-8")

    def _cekej(self, url):
        host = urllib.parse.urlparse(url).netloc
        with self._zamek:
            posledni = self._posledni.get(host, 0.0)
            ted = time.monotonic()
            spat = self.prodleva - (ted - posledni)
            self._posledni[host] = max(ted, posledni + self.prodleva)
        if spat > 0:
            time.sleep(spat)

    def ziskej(self, url, hlavicky=None, json_body=None, ocisti=None, kontext=None):
        """
        Vrati telo odpovedi. `ocisti` je funkce nad rozparsovanym JSON, ktera
        z odpovedi vyhodi nepouzivane casti - kes pak neroste do stovek MB.
        `kontext` je volitelny ssl.SSLContext pro servery s neobvyklym
        certifikatem (viz TW_SSL_KONTEXT).
        """
        klic = url
        if json_body is not None:
            klic += "|" + json.dumps(json_body, sort_keys=True, ensure_ascii=False)
        with self._zamek:
            if klic in self._cache:
                return self._cache[klic]

        h = {"User-Agent": self.ua, "Accept": "application/json"}
        if hlavicky:
            h.update(hlavicky)
        telo = None
        if json_body is not None:
            telo = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            h["Content-Type"] = "application/json"

        posledni_chyba = None
        for pokus in range(1, self.pokusy + 1):
            self._cekej(url)
            try:
                req = urllib.request.Request(url, data=telo, headers=h)
                with urllib.request.urlopen(req, timeout=self.timeout, context=kontext) as odp:
                    text = odp.read().decode("utf-8", errors="replace")
                if ocisti is not None:
                    try:
                        text = json.dumps(ocisti(json.loads(text)), ensure_ascii=False)
                    except (ValueError, KeyError, TypeError):
                        pass
                with self._zamek:
                    self._cache[klic] = text
                    self._zmenena = True
                return text
            except urllib.error.HTTPError as e:
                posledni_chyba = RuntimeError("HTTP %s" % e.code)
                if e.code == 404:
                    break
                if e.code in (429, 500, 502, 503, 504) and pokus < self.pokusy:
                    time.sleep(min(2 ** pokus, 8))
                    continue
                break
            except Exception as e:
                posledni_chyba = e
                if pokus < self.pokusy:
                    time.sleep(min(2 ** pokus, 8))
                    continue
        raise posledni_chyba or RuntimeError("neznama chyba")

    def zapomen(self, url, json_body=None):
        """
        Odstrani odpoved z kese. Pouziva se, kdyz server vratil HTTP 200
        s obsahem, ktery neni skutecna odpoved (napr. VIES pri privalu
        soubeznych dotazu vraci 200 s "MS_MAX_CONCURRENT_REQ" misto
        vysledku overeni) - bez tohoto by se docasna chyba ulozila do kese
        natrvalo, jako by to byla platna odpoved.
        """
        klic = url
        if json_body is not None:
            klic += "|" + json.dumps(json_body, sort_keys=True, ensure_ascii=False)
        with self._zamek:
            self._cache.pop(klic, None)

    def uloz_cache(self):
        if self._cache_soubor and self._zmenena:
            tmp = self._cache_soubor + ".tmp"
            with self._otevri(tmp, "wt") as f:
                json.dump(self._cache, f, ensure_ascii=False)
            os.replace(tmp, self._cache_soubor)


# ---------------------------------------------------------------------------
# Porovnavani nazvu firem
# ---------------------------------------------------------------------------

# NFKD tahle pismena nerozklada na zaklad + diakritiku - jsou to samostatna
# pismena, ne prekombinovane znaky ("ł" v "Spółka" tak bez tohoto prekladu
# zustane a rozbije tokenizaci nazvu).
BEZ_DIAKRITIKY_TABULKA = str.maketrans({
    "ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ø": "o", "Ø": "O",
    "þ": "th", "Þ": "Th", "æ": "ae", "Æ": "AE", "ß": "ss",
    "ı": "i", "İ": "I", "ĸ": "k", "ħ": "h", "Ħ": "H",
})


def bez_diakritiky(s):
    s = str(s).translate(BEZ_DIAKRITIKY_TABULKA)
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def normalizuj_nazev(s):
    """Male pismeno, bez diakritiky, bez pravni formy a interpunkce."""
    if not s:
        return ""
    s = bez_diakritiky(s).lower().replace("&", " and ")
    # zkratky typu "S.p.A." nebo "a.s." se jinak rozpadnou na osamocena
    # jednopismenna slova ("s", "p", "a") a neshodnou se s "spa"/"as" v PRAVNI_FORMY
    s = re.sub(r"([a-z0-9])\.(?=[a-z0-9])", r"\1", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    tokeny = [t for t in s.split() if t]
    for delka in (3, 2):
        while len(tokeny) > delka and " ".join(tokeny[-delka:]) in PRAVNI_FORMY:
            tokeny = tokeny[:-delka]
    while len(tokeny) > 1 and tokeny[-1] in PRAVNI_FORMY:
        tokeny = tokeny[:-1]
    zbytek = [t for t in tokeny if t not in PRAVNI_FORMY]
    return " ".join(zbytek or tokeny)


# Koncovky pravnich forem. Narozdil od PRAVNI_FORMY sem nepatri slova jako
# "group", "holding" nebo "company" - ta nesou cast identity firmy a bez nich
# by dotaz na rejstrik vratil desitky dcerinych spolecnosti.
PRAVNI_SUFIXY = {
    "as", "a s", "sro", "s r o", "spol s r o", "ks", "vos", "se", "ops", "zs",
    "akciova spolecnost", "akciova spolocnost", "spolecnost s rucenim omezenym",
    "spolocnost s rucenim obmedzenym",
    "gmbh", "mbh", "ag", "kg", "kgaa", "ohg", "ug", "eg", "gbr", "co kg", "se co kg",
    "aktiengesellschaft", "gesellschaft mit beschrankter haftung",
    "bv", "nv", "cv", "vof", "sa", "sas", "sasu", "sarl", "eurl",
    "srl", "spa", "snc", "sl", "slu", "sau", "s p a", "s a", "n v", "b v",
    "ltd", "limited", "plc", "llp", "llc", "inc", "incorporated", "corp", "corporation",
    "oy", "oyj", "ab", "aps", "asa", "kft", "zrt", "nyrt", "bt", "kkt",
    "sp z oo", "spzoo", "z oo", "doo", "dd", "ood", "eood", "ad", "ead",
    "lda", "kk", "yk", "pte", "pty", "bhd", "sdn", "dac", "cvba", "bvba",
    "sa nv", "nv sa", "a s ", "gmbh co kg", "se co kgaa",
}


def jadro_pro_hledani(s):
    """
    Nazev bez koncove pravni formy, jinak beze zmeny - "ORLEN S.A." -> "ORLEN",
    "Vodafone Group Plc" -> "Vodafone Group".

    Na dotazovani rejstriku se `normalizuj_nazev` pouzit neda: ta slouzi
    k porovnavani, vse zmensi a z "ORLEN S.A." udela "orlen s a", coz uz
    GLEIF nenajde.
    """
    tokeny = str(s or "").split()
    for _ in range(2):
        if len(tokeny) < 2:
            break
        posledni = re.sub(r"[^a-z]+", " ", bez_diakritiky(tokeny[-1]).lower()).strip()
        if posledni and posledni in PRAVNI_SUFIXY:
            tokeny = tokeny[:-1]
        else:
            break
    return re.sub(r"[\s,]+$", "", " ".join(tokeny)).strip() or str(s or "").strip()


def skore_syrove(a, b):
    """
    Podobnost nazvu bez odstraneni pravnich forem, jen bez diakritiky a
    interpunkce. Rozhoduje tam, kde `skore_shody` da remizu: "Vodafone Group
    Plc" sedi na "Vodafone Limited" i "Vodafone Group Public Limited Company"
    stejne, protoze "group" i "plc" se zahazuji - syrove skore uz rozdil vidi.
    """
    def uprav(s):
        return re.sub(r"[^a-z0-9]+", " ", bez_diakritiky(str(s or "")).lower()).strip()
    ua, ub = uprav(a), uprav(b)
    if not ua or not ub:
        return 0.0
    return round(SequenceMatcher(None, ua, ub).ratio(), 4)


def skore_shody(a, b):
    """0.0-1.0. Kombinace sekvencni podobnosti a prekryvu slov."""
    na, nb = normalizuj_nazev(a), normalizuj_nazev(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    sekvence = SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    prunik = ta & tb
    dice = (2 * len(prunik)) / (len(ta) + len(tb))
    mensi, vetsi = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    # Jeden nazev je slovnim podmnozinou druheho ("Kooperativa pojistovna" vs
    # "Kooperativa pojistovna, Vienna Insurance Group"). Bonus se udeluje jen
    # tehdy, kdyz je kratsi nazev dost specificky (aspon 2 slova), jinak by
    # "Apple" sedelo na "Apple Autos Properties".
    if mensi and mensi <= vetsi and len(mensi) >= 2:
        dice = max(dice, max(0.80, 0.97 - 0.015 * (len(vetsi) - len(mensi))))
    return round(max(sekvence, dice), 4)


# ---------------------------------------------------------------------------
# Vysledny zaznam
# ---------------------------------------------------------------------------

@dataclass
class Zaznam:
    hledany_nazev: str = ""
    jmeno: str = ""
    ulice: str = ""
    psc: str = ""
    mesto: str = ""
    zeme: str = ""
    ico: str = ""
    dic: str = ""
    nace: str = ""
    nace_popis: str = ""
    nace_vse: str = ""
    nace_zdroj: str = ""
    klasifikace: str = ""
    kod_kategorie: str = ""
    kategorie: str = ""
    skupina: str = ""
    zdroj_kategorie: str = ""
    zdroj: str = ""
    shoda: str = ""
    stav: str = STAV_NENALEZENO
    region: str = ""
    lei: str = ""
    reg_cislo: str = ""
    reg_rejstrik: str = ""
    identifikator: str = ""
    pravni_forma: str = ""
    datum_vzniku: str = ""
    dic_overeno: str = ""
    odkaz: str = ""
    poznamka: str = ""
    obory: list = field(default_factory=list)      # QID oboru z Wikidat
    jmena: list = field(default_factory=list)      # dalsi nazvy (jine jazyky/prepisy)
    aktivni: bool = True
    kandidati: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# ARES (Ceska republika)
# ---------------------------------------------------------------------------

# Cinnosti, ktere ma zapsanou temer kazda firma a hlavni obor neurcuji.
PODPURNE_NACE = {"00", "0000", "68", "682", "6820", "68200", "70", "702", "7010", "7022",
                 "74", "749", "7490", "77", "82", "829", "8299", "46", "461", "4619",
                 "469", "4690", "47", "471", "4778", "479", "4799", "52", "5210"}


def vyber_hlavni_nace(kody):
    """
    ARES vraci vsechny registrovane cinnosti bez oznaceni hlavni. Bereme prvni
    v poradi, ktera neni jen podpurna (pronajem, spravni cinnosti, obecny obchod).
    """
    if not kody:
        return ""
    hlavni = [k for k in kody if k not in PODPURNE_NACE]
    return (hlavni or kody)[0]


def _ares_ulice(sidlo):
    ulice = sidlo.get("nazevUlice") or sidlo.get("nazevCastiObce") or sidlo.get("nazevObce") or ""
    cp, co = sidlo.get("cisloDomovni"), sidlo.get("cisloOrientacni")
    cop = sidlo.get("cisloOrientacniPismeno") or ""
    if cp and co:
        cislo = "%s/%s%s" % (cp, co, cop)
    elif cp:
        cislo = str(cp)
    elif co:
        cislo = "%s%s" % (co, cop)
    else:
        cislo = ""
    return (ulice + " " + cislo).strip() or (sidlo.get("textovaAdresa") or "")


def _psc(hodnota):
    if hodnota is None:
        return ""
    p = re.sub(r"\s+", "", str(hodnota))
    return "%s %s" % (p[:3], p[3:]) if len(p) == 5 and p.isdigit() else p


def _ares_na_zaznam(s):
    sidlo = s.get("sidlo") or {}
    registrace = s.get("seznamRegistraci") or {}
    kody = s.get("czNace2008") or s.get("czNace") or []
    nace = vyber_hlavni_nace(kody)
    ico = s.get("ico") or ""
    return Zaznam(
        jmeno=s.get("obchodniJmeno") or "",
        ulice=_ares_ulice(sidlo),
        psc=_psc(sidlo.get("psc")),
        mesto=sidlo.get("nazevObce") or "",
        zeme=sidlo.get("kodStatu") or "CZ",
        ico=ico,
        dic=s.get("dic") or "",
        nace=nace,
        nace_popis=taxonomie.nazev_nace(nace),
        nace_vse=",".join(kody),
        region=sidlo.get("nazevKraje") or "",
        pravni_forma=s.get("pravniForma") or "",
        datum_vzniku=s.get("datumVzniku") or "",
        aktivni=not s.get("datumZaniku"),
        zdroj="ARES",
        odkaz="https://ares.gov.cz/ekonomicke-subjekty?ico=%s" % ico if ico else "",
        poznamka="; ".join(p for p in (
            "zanikl %s" % s.get("datumZaniku") if s.get("datumZaniku") else "",
            "registrovan k DPH, ARES neuvadi DIC"
            if registrace.get("stavZdrojeDph") == "AKTIVNI" and not s.get("dic") else "",
        ) if p),
    )


def ares_podle_ica(klient, ico):
    ico = re.sub(r"\D", "", str(ico)).zfill(8)
    return _ares_na_zaznam(json.loads(klient.ziskej(
        ARES_DETAIL.format(ico=ico), ocisti=_ares_ocisti)))


ARES_POLE = ("ico", "obchodniJmeno", "sidlo", "dic", "czNace2008", "czNace",
             "pravniForma", "datumVzniku", "datumZaniku", "seznamRegistraci")


def _ares_ocisti(data):
    """Z odpovedi ARES nechá jen pouzivana pole (dalsiUdaje byva radove vetsi)."""
    def zmensi(s):
        return {k: v for k, v in s.items() if k in ARES_POLE}
    if "ekonomickeSubjekty" in data:
        return {"ekonomickeSubjekty": [zmensi(s) for s in data["ekonomickeSubjekty"]]}
    if "zaznamy" in data:
        return {"zaznamy": [{k: v for k, v in z.items()
                             if k.startswith("czNacePrevazujici")} for z in data["zaznamy"]]}
    return zmensi(data)


def ares_prevazujici_nace(klient, ico):
    """
    Seznam czNace2008 je v ARES serazeny vzestupne, ne podle vyznamu. Zdroj RES
    ale vede prevazujici (hlavni) cinnost subjektu - tu pouzijeme prednostne.
    """
    ico = re.sub(r"\D", "", str(ico)).zfill(8)
    data = json.loads(klient.ziskej(ARES_RES.format(ico=ico), ocisti=_ares_ocisti))
    for zaznam in data.get("zaznamy", []):
        nace = zaznam.get("czNacePrevazujici2008") or zaznam.get("czNacePrevazujici")
        if nace:
            return str(nace)
    return ""


def doplr_prevazujici_nace(klient, z):
    """Prepise hlavni NACE zaznamu prevazujici cinnosti z RES, je-li dostupna."""
    if z.zdroj != "ARES" or not z.ico:
        return
    try:
        nace = ares_prevazujici_nace(klient, z.ico)
    except Exception:
        return
    if nace:
        z.nace = nace
        z.nace_popis = taxonomie.nazev_nace(nace)


def _ares_vr_ocisti(data):
    """Z odpovedi Verejneho rejstriku (VR) nechá jen pole k dohledani vymazu."""
    def zmensi(z):
        return {k: v for k, v in z.items()
                if k in ("stavSubjektu", "datumVymazu", "pravniDuvodVymazu")}
    return {"zaznamy": [zmensi(z) for z in data.get("zaznamy", [])]}


def ares_vr_vymaz(klient, ico):
    """
    Doplnkovy dotaz do Verejneho rejstriku (zdroj VR). Narozdil od hlavniho
    ARES indexu (ekonomicke-subjekty), ktery jiz vymazane subjekty neobsahuje,
    VR drzi historii i po vymazu - vc. data a pravniho duvodu vymazu (napr.
    "z duvodu likvidace", "fuze se spolecnosti..."). Vraci None, pokud subjekt
    ve VR neni vubec veden, nebo pokud (zatim) vymazan neni.
    """
    ico = re.sub(r"\D", "", str(ico)).zfill(8)
    data = json.loads(klient.ziskej(ARES_VR.format(ico=ico), ocisti=_ares_vr_ocisti))
    for zaznam in data.get("zaznamy", []):
        datum = zaznam.get("datumVymazu")
        if not datum:
            continue
        duvody = [d.get("hodnota") for d in (zaznam.get("pravniDuvodVymazu") or [])
                  if d.get("hodnota")]
        return {"datum": datum, "duvod": "; ".join(duvody)}
    return None


def ares_podle_nazvu(klient, nazev, pocet=30):
    data = json.loads(klient.ziskej(ARES_HLEDAT, ocisti=_ares_ocisti, json_body={
        "obchodniJmeno": nazev, "pocet": min(pocet, 200), "start": 0}))
    return [_ares_na_zaznam(s) for s in data.get("ekonomickeSubjekty", [])]


# ---------------------------------------------------------------------------
# RPO - Registr pravnickych osob SR
# ---------------------------------------------------------------------------

def _sk_platny(polozky):
    """Z historie hodnot vrati aktualne platnou (bez validTo), jinak posledni."""
    if not polozky:
        return None
    aktualni = [p for p in polozky if not p.get("validTo")]
    return (aktualni or polozky)[-1]


def rpo_sk_podle_nazvu(klient, nazev, pocet=10):
    url = RPO_SK + "?" + urllib.parse.urlencode({"fullName": nazev, "limit": pocet})
    data = json.loads(klient.ziskej(url, ocisti=lambda d: {"results": [
        {k: v for k, v in r.items()
         if k in ("fullNames", "addresses", "identifiers", "establishment", "termination")}
        for r in d.get("results", [])]}))
    vysledky = []
    for r in data.get("results", []):
        jmeno = _sk_platny(r.get("fullNames")) or {}
        adresa = _sk_platny(r.get("addresses")) or {}
        ident = _sk_platny(r.get("identifiers")) or {}
        ico = str(ident.get("value") or "")
        psc = (adresa.get("postalCodes") or [""])[0]
        ulice = " ".join(x for x in (adresa.get("street"), adresa.get("buildingNumber")) if x)
        vysledky.append(Zaznam(
            jmeno=jmeno.get("value") or "",
            ulice=ulice,
            psc=_psc(psc),
            mesto=(adresa.get("municipality") or {}).get("value") or "",
            zeme="SK",
            ico=ico,
            dic="SK%s" % ico if ico else "",
            reg_cislo=ico,
            reg_rejstrik="RPO SR",
            datum_vzniku=r.get("establishment") or "",
            aktivni=not r.get("termination"),
            zdroj="RPO SR",
            odkaz="https://www.registeruz.sk/cruz-public/domain/accountingentity/simplesearch?ico=%s" % ico,
            poznamka="zanikl %s" % r.get("termination") if r.get("termination") else "",
        ))
    return vysledky


# ---------------------------------------------------------------------------
# GLEIF (LEI) - cely svet
# ---------------------------------------------------------------------------

GLEIF_RA = "https://api.gleif.org/api/v1/registration-authorities/{kod}"
GLEIF_ELF = "https://api.gleif.org/api/v1/entity-legal-forms/{kod}"
GLEIF_HLAVICKY = {"Accept": "application/vnd.api+json"}


def je_latinka(s):
    """True, pokud retezec nese aspon jedno pismeno a vsechna jsou latinkou."""
    pismena = [c for c in str(s or "") if c.isalpha()]
    if not pismena:
        return False
    return all("LATIN" in unicodedata.name(c, "") for c in pismena)


def _gleif_jmena(ent):
    """
    Vsechny nazvy entity. GLEIF vede pravni nazev v narodnim jazyce, takze
    korejska nebo japonska firma ma v `legalName` znaky, ktere se se vstupem
    nikdy neshodnou - anglicka varianta je az v `otherNames`. Bez ni by
    dodavatele z KR, JP, CN, TW nebo BG nesli dohledat vubec.
    """
    jmena = []
    hlavni = (ent.get("legalName") or {}).get("name") or ""
    if hlavni:
        jmena.append(hlavni)
    for klic in ("otherNames", "transliteratedOtherNames"):
        for o in ent.get(klic) or []:
            n = (o or {}).get("name")
            if n and n not in jmena:
                jmena.append(n)
    return jmena


def _gleif_adresa(ent):
    """
    Vrati adresu prednostne latinkou. Poradi: pravni sidlo -> alternativni
    jazykova varianta sidla -> centrala. Adresy typu "c/o ..." patri
    registracnimu agentovi, ne firme, takze se preskakuji.
    """
    def radky(adr):
        return [r for r in (adr.get("addressLines") or []) if r]

    moznosti = []
    for adr in (ent.get("legalAddress"), ent.get("headquartersAddress")):
        if adr:
            moznosti.append(adr)
    for adr in ent.get("otherAddresses") or []:
        if (adr.get("type") or "").startswith("ALTERNATIVE_LANGUAGE"):
            moznosti.append(adr)

    pouzitelne = [a for a in moznosti
                  if radky(a) and not re.match(r"(?i)\s*c/?o[\s.]", radky(a)[0])]
    if not pouzitelne:
        return ent.get("legalAddress") or {}, ""
    latinkou = [a for a in pouzitelne if je_latinka(radky(a)[0])]
    return (latinkou or pouzitelne)[0], ""


def _gleif_na_zaznam(rec):
    a = rec.get("attributes", {})
    ent = a.get("entity", {}) or {}
    jmena = _gleif_jmena(ent)
    # do vystupu jde nazev latinkou, aby byl seznam citelny; originalni zapis
    # zustava v poznamce
    zobrazit = next((j for j in jmena if je_latinka(j)), jmena[0] if jmena else "")
    puvodni = jmena[0] if jmena else ""

    adr, _ = _gleif_adresa(ent)
    radky = [r for r in (adr.get("addressLines") or []) if r]
    zeme = adr.get("country") or ent.get("jurisdiction") or ""
    stav = ent.get("status")
    reg = ent.get("registeredAs") or ""
    poznamky = []
    if stav and stav != "ACTIVE":
        poznamky.append("stav v LEI: %s" % stav)
    if puvodni and puvodni != zobrazit:
        poznamky.append("puvodni zapis nazvu: %s" % puvodni)
    return Zaznam(
        jmeno=zobrazit,
        ulice=radky[0] if radky else "",
        psc=adr.get("postalCode") or "",
        mesto=adr.get("city") or "",
        zeme=zeme[:2],
        reg_cislo=reg,
        reg_rejstrik=(ent.get("registeredAt") or {}).get("id") or "",
        region=adr.get("region") or "",
        lei=a.get("lei") or "",
        pravni_forma=(ent.get("legalForm") or {}).get("id") or "",
        datum_vzniku=(ent.get("creationDate") or "")[:10],
        jmena=jmena,
        aktivni=stav in (None, "", "ACTIVE"),
        zdroj="GLEIF",
        odkaz="https://search.gleif.org/#/record/%s" % a.get("lei", ""),
        poznamka="; ".join(poznamky),
    )


GLEIF_POLE = ("lei", "entity")


def _gleif_ocisti(data):
    """Z odpovedi GLEIF nechá jen atributy, ktere ctame."""
    def zmensi(r):
        return {"attributes": {k: v for k, v in (r.get("attributes") or {}).items()
                               if k in GLEIF_POLE}}
    if isinstance(data.get("data"), list):
        return {"data": [zmensi(r) for r in data["data"]]}
    if isinstance(data.get("data"), dict):
        return {"data": zmensi(data["data"])}
    return data


def gleif_podle_nazvu(klient, nazev, zeme=None, pocet=15):
    """
    Hleda v GLEIF nekolika zpusoby a vysledky slucuje.

    Jeden dotaz nestaci: filtr `entity.names` neprojde, kdyz nazev obsahuje
    pravni formu ("Vodafone Group Plc" nenajde nic, "Vodafone Group" ano),
    a naopak zkraceny nazev sam o sobe vraci desitky dcerinych spolecnosti.
    Posilame proto obe varianty a vyber nejlepsiho nechavame na skorovani.
    """
    nalezene, videne = [], set()

    def pridej(zaznamy):
        for z in zaznamy:
            if z.lei and z.lei not in videne:
                videne.add(z.lei)
                nalezene.append(z)

    def dotaz(parametry):
        url = GLEIF_API + "?" + urllib.parse.urlencode(parametry)
        data = json.loads(klient.ziskej(url, hlavicky=GLEIF_HLAVICKY, ocisti=_gleif_ocisti))
        return [_gleif_na_zaznam(r) for r in data.get("data", [])]

    jadro = jadro_pro_hledani(nazev)
    varianty = [nazev] + ([jadro] if jadro.lower() != nazev.lower() else [])

    for hledat in varianty:
        for s_zemi in ([True, False] if zeme else [False]):
            parametry = {"filter[entity.names]": hledat, "page[size]": min(pocet, 50)}
            if s_zemi:
                parametry["filter[entity.legalAddress.country]"] = zeme
            try:
                pridej(dotaz(parametry))
            except Exception:
                pass
        # dalsi varianty ma smysl vynechat, az kdyz uz mame presnou shodu
        # nazvu ze spravne zeme
        if any(z.zeme == zeme and max(skore_shody(nazev, j) for j in (z.jmena or [z.jmeno]))
               >= 0.97 for z in nalezene if z.jmena or z.jmeno):
            break

    # naseptavac vraci LEI presnych/blizkych nazvu, ktere fulltext casto minie
    if len(nalezene) < 3:
        try:
            url = GLEIF_AUTO + "?" + urllib.parse.urlencode({"field": "fulltext", "q": nazev})
            data = json.loads(klient.ziskej(url, hlavicky=GLEIF_HLAVICKY))
            leie = [d["relationships"]["lei-records"]["data"]["id"]
                    for d in data.get("data", [])[:5]
                    if d.get("relationships", {}).get("lei-records", {}).get("data")]
            for lei in leie:
                if lei in videne:
                    continue
                rec = json.loads(klient.ziskej(GLEIF_API + "/" + lei,
                                               hlavicky=GLEIF_HLAVICKY, ocisti=_gleif_ocisti))
                pridej([_gleif_na_zaznam(rec["data"])])
        except Exception:
            pass

    if not nalezene:
        zakladni = {"filter[fulltext]": nazev, "page[size]": min(pocet, 50)}
        if zeme:
            zakladni["filter[entity.legalAddress.country]"] = zeme
        try:
            pridej(dotaz(zakladni))
        except Exception:
            pass
    return nalezene


def gleif_popis_rejstriku(klient, kod):
    """Prelozi kod registracni autority (RA000657) na nazev rejstriku."""
    if not kod or not kod.startswith("RA"):
        return kod or ""
    try:
        data = json.loads(klient.ziskej(GLEIF_RA.format(kod=kod), hlavicky=GLEIF_HLAVICKY,
                                        ocisti=lambda d: {"data": {"attributes": {
                                            k: v for k, v in d["data"]["attributes"].items()
                                            if k in ("internationalName",
                                                     "internationalOrganizationName")}}}))
        a = data["data"]["attributes"]
        return ", ".join(x for x in (a.get("internationalOrganizationName"),
                                     a.get("internationalName")) if x) or kod
    except Exception:
        return kod


def gleif_popis_formy(klient, kod):
    """Prelozi ELF kod pravni formy (5RCH) na citelny nazev."""
    if not kod or len(kod) != 4:
        return kod or ""
    try:
        data = json.loads(klient.ziskej(GLEIF_ELF.format(kod=kod), hlavicky=GLEIF_HLAVICKY,
                                        ocisti=lambda d: {"data": {"attributes": {
                                            "names": d["data"]["attributes"].get("names")}}}))
        for n in data["data"]["attributes"].get("names") or []:
            nazev = n.get("transliteratedName") or n.get("localName")
            if nazev:
                return nazev
    except Exception:
        pass
    return kod


def gleif_podle_lei(klient, lei):
    """Primy dotaz na jeden LEI zaznam - presnejsi a rychlejsi nez hledani jmenem."""
    try:
        data = json.loads(klient.ziskej(GLEIF_API + "/" + lei, hlavicky=GLEIF_HLAVICKY,
                                        ocisti=_gleif_ocisti))
    except Exception:
        return None
    return _gleif_na_zaznam(data["data"]) if data.get("data") else None


def gleif_podle_registrovane(klient, cislo, zeme=None, pocet=10):
    """
    Presne vyhledani podle narodniho registracniho cisla (pole `registeredAs`
    v GLEIF - napr. nemecke HRB, slovenske ICO). Spolehlivejsi nez hledani
    jmenem, protoze cislo je (na rozdil od nazvu) jednoznacne.
    """
    parametry = {"filter[entity.registeredAs]": cislo, "page[size]": min(pocet, 25)}
    if zeme:
        parametry["filter[entity.legalAddress.country]"] = zeme
    url = GLEIF_API + "?" + urllib.parse.urlencode(parametry)
    try:
        data = json.loads(klient.ziskej(url, hlavicky=GLEIF_HLAVICKY, ocisti=_gleif_ocisti))
    except Exception:
        return []
    vysledky = [_gleif_na_zaznam(r) for r in data.get("data", [])]
    # filtr je u GLEIF niekdy jen fulltextovy - overit presnou shodu cisla
    cislo_n = re.sub(r"[\s.\-]", "", cislo).upper()
    presne = [z for z in vysledky if re.sub(r"[\s.\-]", "", z.reg_cislo).upper() == cislo_n]
    return presne or vysledky


# ---------------------------------------------------------------------------
# SEC EDGAR - USA
# ---------------------------------------------------------------------------

def _bez_ns(prvek, tag):
    """
    Najde primeho potomka podle mistniho jmena znacky bez ohledu na jmenny
    prostor. Atom feed EDGARu vse zabaluje do namespace
    "http://www.w3.org/2005/Atom", takze holé `Element.find("cik")` na nem
    nikdy nic nenajde - tise vraci None i tam, kde element skutecne je.
    """
    return next((e for e in prvek if e.tag.rsplit("}", 1)[-1] == tag), None)


def _vsichni_bez_ns(prvek, tag):
    return [e for e in prvek.iter() if e.tag.rsplit("}", 1)[-1] == tag]


def _edgar_adresa(prvek):
    for typ in ("business", "mailing"):
        for adr in _vsichni_bez_ns(prvek, "address"):
            if adr.get("type") != typ:
                continue

            def h(tag):
                e = _bez_ns(adr, tag)
                return (e.text or "").strip() if e is not None and e.text else ""
            ulice = " ".join(x for x in (h("street1"), h("street2")) if x)
            if ulice or h("city"):
                return ulice, h("city"), h("state"), h("zip")
    return "", "", "", ""


def _edgar_na_zaznam(ci, cik_zaloha="", nazev_zaloha=""):
    def h(tag):
        e = _bez_ns(ci, tag)
        return (e.text or "").strip() if e is not None and e.text else ""
    cik = h("cik") or cik_zaloha
    sic = h("assigned-sic")
    # v USA se NACE nepouziva - domaci obdoba je NAICS (SIC u SEC je jeho
    # starsi predchudce). NACE se dopocitava jen jako priblizny ekvivalent
    # pro zarazeni do vlastni taxonomie.
    nace = taxonomie.sic_na_nace(sic) or ""
    naics = taxonomie.sic_na_naics(sic) or ""
    ulice, mesto, stat, psc = _edgar_adresa(ci)
    cik_cislo = cik.lstrip("0") if cik else ""
    return Zaznam(
        jmeno=h("conformed-name") or nazev_zaloha,
        ulice=ulice, psc=psc, mesto=mesto, region=stat, zeme="US",
        reg_cislo=cik_cislo, reg_rejstrik="SEC CIK",
        nace=nace, nace_popis=taxonomie.nazev_nace(nace),
        klasifikace="NAICS %s - %s" % (naics, taxonomie.nazev_naics(naics)) if naics else "",
        zdroj="SEC EDGAR",
        odkaz="https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=%s" % cik if cik else "",
        poznamka=("SIC %s %s" % (sic, h("assigned-sic-desc"))).strip() if sic else "",
    )


def edgar_podle_nazvu(klient, nazev, pocet=10):
    url = EDGAR_API + "?" + urllib.parse.urlencode({
        "company": nazev, "type": "", "dateb": "", "owner": "include",
        "count": pocet, "action": "getcompany", "output": "atom"})
    try:
        koren = ET.fromstring(klient.ziskej(
            url, hlavicky={"Accept": "application/atom+xml"}).encode("utf-8"))
    except (ET.ParseError, Exception):
        return []

    ci = _bez_ns(koren, "company-info")
    if ci is not None:
        return [_edgar_na_zaznam(ci)]

    vysledky = []
    for entry in koren.iter():
        if not entry.tag.endswith("entry"):
            continue
        # u vice shodujicich se firem je <company-info> vnorene v <content>,
        # ne primo pod <entry> - proto hledani do hloubky
        ci = next(iter(_vsichni_bez_ns(entry, "company-info")), None)
        if ci is not None:
            vysledky.append(_edgar_na_zaznam(ci))
            continue
        titul = next((e for e in entry if e.tag.endswith("title")), None)
        if titul is not None and titul.text:
            m = re.match(r"(.*?)\s*\(CIK (\d+)\)", titul.text.strip())
            if m:
                vysledky.append(_edgar_na_zaznam(entry, m.group(2), m.group(1)))
    return vysledky


def edgar_podle_cik(klient, cik):
    """Primy dotaz na jedno CIK - presnejsi a rychlejsi nez hledani jmenem."""
    cik_cislo = re.sub(r"\D", "", str(cik))
    if not cik_cislo:
        return None
    url = EDGAR_API + "?" + urllib.parse.urlencode({
        "CIK": cik_cislo, "type": "", "dateb": "", "owner": "include",
        "count": 1, "action": "getcompany", "output": "atom"})
    try:
        koren = ET.fromstring(klient.ziskej(
            url, hlavicky={"Accept": "application/atom+xml"}).encode("utf-8"))
    except (ET.ParseError, Exception):
        return None
    ci = _bez_ns(koren, "company-info")
    return _edgar_na_zaznam(ci) if ci is not None else None


# ---------------------------------------------------------------------------
# Francie - Recherche d'entreprises (INSEE/INPI, data.gouv.fr)
# ---------------------------------------------------------------------------

def fr_dic_ze_siren(siren):
    """
    Francouzske DIC se pocita ze SIREN kontrolnim vzorcem (bez sazby
    z rejstriku): klic = (12 + 3 * (SIREN mod 97)) mod 97.
    """
    cislice = re.sub(r"\D", "", str(siren or ""))
    if len(cislice) != 9:
        return ""
    klic = (12 + 3 * (int(cislice) % 97)) % 97
    return "FR%02d%s" % (klic, cislice)


def _fr_adresa(sidlo):
    cast = " ".join(x for x in (
        sidlo.get("numero_voie"), sidlo.get("type_voie"), sidlo.get("libelle_voie")) if x)
    return cast or (sidlo.get("adresse") or "")


FR_POLE = ("siren", "nom_complet", "nom_raison_sociale", "sigle", "siege",
           "activite_principale", "nature_juridique", "date_creation", "etat_administratif")


def _fr_ocisti(data):
    def zmensi(r):
        r = {k: v for k, v in r.items() if k in FR_POLE}
        s = r.get("siege") or {}
        r["siege"] = {k: v for k, v in s.items() if k in (
            "numero_voie", "type_voie", "libelle_voie", "code_postal",
            "libelle_commune", "adresse", "etat_administratif")}
        return r
    return {"results": [zmensi(r) for r in data.get("results", [])]}


def fr_podle_nazvu(klient, nazev, pocet=15):
    url = INSEE_FR + "?" + urllib.parse.urlencode({"q": nazev, "per_page": min(pocet, 25)})
    data = json.loads(klient.ziskej(url, ocisti=_fr_ocisti))
    vysledky = []
    for r in data.get("results", []):
        sidlo = r.get("siege") or {}
        naf = r.get("activite_principale") or ""
        nace = taxonomie.naf_na_nace(naf)
        siren = r.get("siren") or ""
        aktivni = (sidlo.get("etat_administratif") or r.get("etat_administratif")) != "F"
        vysledky.append(Zaznam(
            jmeno=r.get("nom_complet") or r.get("nom_raison_sociale") or "",
            ulice=_fr_adresa(sidlo),
            psc=_psc(sidlo.get("code_postal")),
            mesto=sidlo.get("libelle_commune") or "",
            zeme="FR",
            dic=fr_dic_ze_siren(siren),
            reg_cislo=siren,
            reg_rejstrik="SIREN",
            nace=nace,
            nace_popis=taxonomie.nazev_nace(nace),
            nace_vse=naf,
            pravni_forma=r.get("nature_juridique") or "",
            datum_vzniku=r.get("date_creation") or "",
            aktivni=aktivni,
            zdroj="INSEE/INPI",
            odkaz="https://annuaire-entreprises.data.gouv.fr/entreprise/%s" % siren if siren else "",
            poznamka="zanikla firma (INSEE)" if not aktivni else "",
        ))
    return vysledky


# ---------------------------------------------------------------------------
# Singapur - ACRA (data.gov.sg, otevrena data)
# ---------------------------------------------------------------------------

SG_ACRA_POLE = ("uen", "entity_name", "entity_type_desc", "uen_status_desc",
               "reg_street_name", "reg_postal_code")


def _sg_ocisti(d):
    return {"result": {"records": [{k: v for k, v in r.items() if k in SG_ACRA_POLE}
                                   for r in d.get("result", {}).get("records", [])]}}


def _sg_na_zaznam(r):
    uen = r.get("uen") or ""
    aktivni = (r.get("uen_status_desc") or "").strip().lower() == "registered"
    return Zaznam(
        jmeno=r.get("entity_name") or "",
        ulice=r.get("reg_street_name") or "",
        psc=r.get("reg_postal_code") or "",
        mesto="Singapore" if r.get("reg_street_name") else "",
        zeme="SG",
        reg_cislo=uen,
        reg_rejstrik="UEN (ACRA)",
        pravni_forma=r.get("entity_type_desc") or "",
        aktivni=aktivni,
        zdroj="ACRA (data.gov.sg)",
        odkaz="https://www.uen.gov.sg/ueninternet/faces/pages/uenResults.jspx?uen=%s" % uen
              if uen else "",
        poznamka="stav v ACRA: %s" % r["uen_status_desc"]
                 if r.get("uen_status_desc") and not aktivni else "",
    )


def sg_podle_nazvu(klient, nazev, pocet=15):
    url = SG_ACRA + "?" + urllib.parse.urlencode({
        "resource_id": SG_ACRA_ZDROJ, "q": nazev, "limit": min(pocet, 30)})
    data = json.loads(klient.ziskej(url, ocisti=_sg_ocisti))
    return [_sg_na_zaznam(r) for r in data.get("result", {}).get("records", [])]


def sg_podle_uen(klient, uen):
    """Presny dotaz na jeden UEN - spolehlivejsi nez fulltextove hledani jmenem."""
    url = SG_ACRA + "?" + urllib.parse.urlencode({
        "resource_id": SG_ACRA_ZDROJ, "filters": json.dumps({"uen": uen}), "limit": 1})
    data = json.loads(klient.ziskej(url, ocisti=_sg_ocisti))
    zaznamy = data.get("result", {}).get("records", [])
    return _sg_na_zaznam(zaznamy[0]) if zaznamy else None


# ---------------------------------------------------------------------------
# Tchaj-wan - GCIS (data.gcis.nat.gov.tw, otevrena data)
# ---------------------------------------------------------------------------

def tw_podle_nazvu(klient, nazev, pocet=15):
    """
    GCIS bez filtru na stav vraci prazdno i pro bezne existujici firmy - proto
    je "Company_Status eq 01" (aktivni/schvalene zalozeni) soucasti dotazu,
    ne dodatecny filtr az na strane klienta.
    """
    url = TW_GCIS + "?" + urllib.parse.urlencode({
        "$format": "json",
        "$filter": "Company_Name like %s and Company_Status eq 01" % nazev,
        "$skip": 0, "$top": min(pocet, 30),
    })
    data = klient.ziskej(url, kontext=tw_ssl_kontext(), ocisti=lambda d: [
        {k: v for k, v in r.items() if k in (
            "Business_Accounting_NO", "Company_Name", "Company_Status_Desc",
            "Company_Location", "Company_Setup_Date")}
        for r in d] if isinstance(d, list) else d)
    zaznamy = json.loads(data)
    if not isinstance(zaznamy, list):
        return []
    vysledky = []
    for r in zaznamy:
        cislo = r.get("Business_Accounting_NO") or ""
        datum = r.get("Company_Setup_Date") or ""
        # tchajwanske datum je v minguo kalendari (rok - 1911), napr. "0760221"
        # = 1976-02-21 - pro cteni ve vystupu neni potreba prevadet, jen orezat
        vysledky.append(Zaznam(
            jmeno=r.get("Company_Name") or "",
            ulice=r.get("Company_Location") or "",
            zeme="TW",
            reg_cislo=cislo,
            reg_rejstrik="統一編號 (GCIS)",
            datum_vzniku=datum,
            zdroj="GCIS",
            odkaz="https://data.gcis.nat.gov.tw/od/detail?oid=6BBA2268-1367-4B42-9CCA-BC17499EBE8C",
            poznamka="",
        ))
    return vysledky


# ---------------------------------------------------------------------------
# Wikidata - zalozni zdroj pro velke zahranicni firmy
# ---------------------------------------------------------------------------

WIKIDATA_POLE = ("P452", "P17", "P159", "P3608", "P1278", "P297")


def _wikidata_ocisti(data):
    """
    Odpovedi wbgetentities jsou obrovske (entita zeme ma tisice tvrzeni).
    Do kese ukladame jen popisky a tvrzeni, ktera cteme.
    """
    entity = {}
    for qid, e in (data.get("entities") or {}).items():
        entity[qid] = {
            "labels": {j: v for j, v in (e.get("labels") or {}).items() if j in ("en", "cs", "de")},
            "claims": {p: v for p, v in (e.get("claims") or {}).items() if p in WIKIDATA_POLE},
        }
    return {"entities": entity}


def wikidata_podle_nazvu(klient, nazev, pocet=5, i_kratky_nazev=False):
    """
    `i_kratky_nazev=True` navic zkusi hledani pod zkracenym nazvem (bez
    pravni formy) a vysledky sloucí, i kdyz plny nazev neco naslo. Rejstriky
    a VIES vraceji plny pravni nazev ("ABB Schweiz AG", "ENI SPA"), Wikidata
    ale firmy vetsinou vede pod kratkym nazvem clanku ("ABB", "Eni") -
    hledani s plnym nazvem tak casto neni prazdne, jen vrati nekoho jineho
    (dceřinou spolecnost, pobocku).

    Vyplati se to jen pri doplnovani oboru k uz jednoznacne identifikovane
    firme (vic kandidatu vadit nemuze - obor se bere z prvniho s dost
    podobnym jmenem). U hledani samotne identity firmy by to naopak skodilo:
    kratky nazev typicky vrati vic stejne se jmenujicich firem/dceřinych
    spolecnosti se stejnym skore, coz zvysuje falesnou "VICE_SHOD"
    nejednoznacnost a muze prebit spravneho kandidata horsim.
    """
    def hledej(text):
        url = WIKIDATA_API + "?" + urllib.parse.urlencode({
            "action": "wbsearchentities", "search": text, "language": "en",
            "uselang": "en", "type": "item", "limit": pocet, "format": "json"})
        return json.loads(klient.ziskej(url, ocisti=lambda d: {"search": [
            {"id": h.get("id")} for h in d.get("search", [])]})).get("search", [])

    hledani = hledej(nazev)
    jadro = jadro_pro_hledani(re.sub(r"[,.]+$", "", nazev.replace(",", " ")))
    jadro = re.sub(r"[\s,.\-]+$", "", jadro)
    ma_smysl_zkusit_jadro = jadro.lower() != nazev.lower() and jadro
    if ma_smysl_zkusit_jadro and (not hledani or i_kratky_nazev):
        videne = {h["id"] for h in hledani}
        hledani += [h for h in hledej(jadro) if h["id"] not in videne]
    if not hledani:
        return []

    qidy = [h["id"] for h in hledani[:8]]
    url = WIKIDATA_API + "?" + urllib.parse.urlencode({
        "action": "wbgetentities", "ids": "|".join(qidy),
        "props": "claims|labels", "languages": "en|cs|de", "format": "json"})
    entity = json.loads(klient.ziskej(url, ocisti=_wikidata_ocisti)).get("entities", {})

    def tvrzeni(claims, prop):
        vysledek = []
        for s in claims.get(prop, []):
            dv = s.get("mainsnak", {}).get("datavalue", {}).get("value")
            if isinstance(dv, dict) and "id" in dv:
                vysledek.append(dv["id"])
            elif isinstance(dv, str):
                vysledek.append(dv)
        return vysledek

    # QID odvetvi / zeme / sidla je treba prelozit na text
    odkazovane = set()
    for qid in qidy:
        c = entity.get(qid, {}).get("claims", {})
        odkazovane.update(tvrzeni(c, "P452")[:5] + tvrzeni(c, "P17")[:1] + tvrzeni(c, "P159")[:1])
    popisky, iso = {}, {}
    if odkazovane:
        url = WIKIDATA_API + "?" + urllib.parse.urlencode({
            "action": "wbgetentities", "ids": "|".join(sorted(odkazovane)[:50]),
            "props": "labels|claims", "languages": "en|cs", "format": "json"})
        for qid, e in json.loads(
                klient.ziskej(url, ocisti=_wikidata_ocisti)).get("entities", {}).items():
            lab = e.get("labels", {})
            popisky[qid] = (lab.get("en") or lab.get("cs") or {}).get("value", "")
            kody = [s.get("mainsnak", {}).get("datavalue", {}).get("value")
                    for s in e.get("claims", {}).get("P297", [])]
            if kody and isinstance(kody[0], str):
                iso[qid] = kody[0]

    vysledky = []
    for qid in qidy:
        e = entity.get(qid, {})
        c = e.get("claims", {})
        obory_qid = tvrzeni(c, "P452")[:5]
        obory = [popisky.get(q, "") for q in obory_qid]
        zeme_q = tvrzeni(c, "P17")[:1]
        sidlo_q = tvrzeni(c, "P159")[:1]
        dic = next((v for v in tvrzeni(c, "P3608") if isinstance(v, str)), "")
        lei = next((v for v in tvrzeni(c, "P1278") if isinstance(v, str)), "")
        lab = e.get("labels", {})
        vysledky.append(Zaznam(
            jmeno=(lab.get("en") or lab.get("cs") or lab.get("de") or {}).get("value", ""),
            mesto=popisky.get(sidlo_q[0], "") if sidlo_q else "",
            zeme=iso.get(zeme_q[0], "") if zeme_q else "",
            dic=dic, lei=lei,
            obory=obory_qid,
            zdroj="Wikidata",
            odkaz="https://www.wikidata.org/wiki/%s" % qid,
            poznamka="obor dle Wikidata: %s" % ", ".join(o for o in obory if o) if any(obory) else "",
        ))
    return vysledky


# ---------------------------------------------------------------------------
# VIES - overeni DIC v EU
# ---------------------------------------------------------------------------

def rozloz_dic(dic):
    if not dic:
        return None, None
    d = re.sub(r"[^A-Za-z0-9]", "", str(dic)).upper()
    m = re.match(r"^([A-Z]{2})(\w+)$", d)
    return (m.group(1), m.group(2)) if m else (None, None)


# VIES vraci docasne vypadky sluzby jako HTTP 200 s isValid:false a timto
# priznakem v "userError" - ne jako chybu. Bez rozliseni by to vypadalo
# jako platne overeni "DIC neexistuje", pritom sluzba jen byla docasne
# preteizena (typicky pri vic soubeznych dotazech na stejny stat).
VIES_DOCASNE_CHYBY = {"MS_MAX_CONCURRENT_REQ", "MS_UNAVAILABLE", "GLOBAL_MAX_CONCURRENT_REQ",
                      "SERVICE_UNAVAILABLE", "TIMEOUT", "SERVER_BUSY"}


def vies_over(klient, dic, pokusy=5):
    cc, num = rozloz_dic(dic)
    if not cc or cc not in EU_STATY:
        return None
    url = VIES_API.format(cc=cc, num=num)
    for pokus in range(1, pokusy + 1):
        data = json.loads(klient.ziskej(url))
        chyba = data.get("userError")
        if chyba in VIES_DOCASNE_CHYBY:
            klient.zapomen(url)   # nezustane v kesi jako by to byla platna odpoved
            if pokus < pokusy:
                time.sleep(min(2 ** pokus, 6))
                continue
            raise RuntimeError("docasne nedostupne (%s)" % chyba)
        return {"platne": bool(data.get("isValid")),
                "jmeno": (data.get("name") or "").strip(" -"),
                "adresa": (data.get("address") or "").strip(" -")}


# ---------------------------------------------------------------------------
# Odkaz na rucni dohledani - zeme bez napojeneho rejstriku ani u GLEIF/Wikidat
# ---------------------------------------------------------------------------

# Domena narodniho rejstriku pro zeme, kde nemame API (viz README - overeno,
# ze bezklicove hromadne API neexistuje). Pouziva se jen k sestaveni odkazu
# na vyhledavani "site:domena nazev" - clovek pak dotaz jen otevre, nic se
# tim neautomatizuje ani neobchazi.
ZEME_MANUALNI_REJSTRIK = {
    "DE": "handelsregister.de",
    "NL": "kvk.nl",
    "AT": "justiz.gv.at",
    "BE": "kbopub.economie.fgov.be",
    "CH": "zefix.ch",
    "IT": "registroimprese.it",
    "ES": "sede.registradores.org",
    "HU": "e-cegjegyzek.hu",
    "PL": "krs-online.com.pl",
    "RO": "onrc.ro",
    "BG": "portal.registryagency.bg",
    "TR": "ticaretsicil.gov.tr",
    "MY": "ssm-einfo.my",
    "HK": "cr.gov.hk",
    "CA": "corporationscanada.ic.gc.ca",
    "GB": "find-and-update.company-information.service.gov.uk",
}

# Zeme pripojene k BRIS (European Business Registers Interconnection System) -
# u tech je alternativou i centralni EU vyhledavani (rucne, viz README)
BRIS_ZEME = {"AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI",
             "FR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL",
             "PT", "RO", "SE", "SI", "SK", "IS", "LI", "NO"}


def manualni_odkaz(zeme, nazev):
    """
    Kdyz se firma nenajde a zeme nema napojeny zadny rejstrik, vrati odkaz
    na predpripraveny vyhledavaci dotaz (Google omezeny na spravnou domenu,
    pripadne centralni BRIS) - usetri rucni psani nazvu do vyhledavace.
    """
    if not nazev:
        return ""
    domena = ZEME_MANUALNI_REJSTRIK.get(zeme)
    if domena:
        dotaz = 'site:%s "%s"' % (domena, nazev)
        return "https://www.google.com/search?q=" + urllib.parse.quote(dotaz)
    if zeme in BRIS_ZEME:
        return "https://e-justice.europa.eu/content_find_a_company-489-en.do"
    return ""


# ---------------------------------------------------------------------------
# Zpracovani jednoho radku
# ---------------------------------------------------------------------------

def _normalizuj_mesto(s):
    return re.sub(r"[^a-z0-9]+", " ", bez_diakritiky(str(s or "")).lower()).strip()


def _normalizuj_psc(s):
    return re.sub(r"\D", "", str(s or ""))


def _shoduje_se_adresa(hledana, k):
    """
    Porovna zadanou adresu s adresou kandidata. Vraci (bonus, duvod|None).
    Shoda mesta nebo PSC je silny signal, ze jde o spravny subjekt (obzvlast
    u firem se skupinou stejne se jmenujicich dcerinych spolecnosti v ruznych
    mestech) - naopak jasny nesoulad (zadano konkretni mesto, kandidat sidli
    jinde) je duvod k ostrazitosti podobne jako spatna zeme.
    """
    if not hledana or not any(hledana.values()):
        return 0.0, None
    mesto_h, psc_h = _normalizuj_mesto(hledana.get("mesto")), _normalizuj_psc(hledana.get("psc"))
    mesto_k, psc_k = _normalizuj_mesto(k.mesto), _normalizuj_psc(k.psc)

    if psc_h and psc_k:
        if psc_h == psc_k:
            return 0.06, None
        if psc_h[:2] != psc_k[:2]:
            return -0.05, "PSC %s misto %s" % (k.psc, hledana.get("psc"))
    if mesto_h and mesto_k:
        if mesto_h == mesto_k or mesto_h in mesto_k or mesto_k in mesto_h:
            return 0.06, None
        return -0.05, "sidlo v %s misto %s" % (k.mesto, hledana.get("mesto"))
    return 0.0, None


def skore_kandidata(nazev, zeme, k, adresa=None):
    """
    Slozene skore jednoho kandidata: podobnost nazvu plus prirazky za to,
    jak dobre zaznam sedi na zbytek zadani.

    Diky prirazkam se da rozhodnout i tam, kde je nazev stejne podobny u vic
    firem - typicky "Danone S.A." sedi na DANONE (FR) i DANONE PORTUGAL (PT)
    a rozhodne az zadana zeme (nebo adresa, je-li k dispozici).

    Vrati (celkove skore, skore nazvu, duvody prirazek).
    """
    jmena = [j for j in (k.jmena or [k.jmeno]) if j]
    if not jmena:
        return 0.0, 0.0, []
    skore = max(skore_shody(nazev, j) for j in jmena)
    syrove = max(skore_syrove(nazev, j) for j in jmena)

    bonus, duvody = 0.0, []
    if zeme and k.zeme:
        if k.zeme == zeme:
            bonus += 0.08
        else:
            bonus -= 0.12
            duvody.append("sidlo v %s misto %s" % (k.zeme, zeme))
    adr_bonus, adr_duvod = _shoduje_se_adresa(adresa, k)
    bonus += adr_bonus
    if adr_duvod:
        duvody.append(adr_duvod)
    if not k.aktivni:
        bonus -= 0.15
        duvody.append("neaktivni subjekt")
    if k.nace:
        bonus += 0.03
    if k.reg_cislo or k.ico:
        bonus += 0.02
    if k.dic:
        bonus += 0.01
    if k.obory:
        bonus += 0.02
    # syrova podobnost rozhodne remizy, kde normalizace zahodila prave to
    # slovo, kterym se kandidati lisi ("Group", "Holding")
    return round(skore + bonus + 0.05 * syrove, 4), skore, duvody


def vyber_nejlepsi(kandidati, nazev, prah_ok, prah_overit, zeme=None, adresa=None):
    """
    Vrati (nejlepsi, stav, prehled kandidatu).

    Pri vice srovnatelnych shodach se vzdy vybere jeden zaznam - ten
    s nejvyssim slozenym skore - a stav je VYBRANO. Rucni dohledavani
    v seznamu o stovkach dodavatelu se tim nahradi kontrolou par radku;
    ostatni kandidati zustavaji vypsani v poznamce.
    """
    if not kandidati:
        return None, STAV_NENALEZENO, []
    ohodnocene = sorted(((skore_kandidata(nazev, zeme, k, adresa), k) for k in kandidati),
                        key=lambda x: -x[0][0])
    (celkem, skore, duvody), nejlepsi = ohodnocene[0]
    nejlepsi.shoda = "%.0f%%" % (skore * 100)

    prehled = ["%s [%s%s] %.0f%%" % (k.jmeno, k.zeme + " " if k.zeme else "",
                                     k.reg_cislo or k.ico or k.lei or k.mesto or "?", s * 100)
               for (c, s, _), k in ohodnocene[:5] if s > 0.3]

    if skore >= prah_ok:
        # kolik dalsich kandidatu je jmenem stejne dobrych
        srovnatelni = sum(1 for (c, s, _), _ in ohodnocene[1:] if s >= prah_ok)
        if srovnatelni:
            druhy_celkem = ohodnocene[1][0][0]
            nejlepsi.poznamka = "; ".join(p for p in (
                nejlepsi.poznamka,
                "vybrano z %d srovnatelnych shod, druhy v poradi o %.2f bodu niz"
                % (srovnatelni + 1, celkem - druhy_celkem),
                ", ".join(duvody),
            ) if p)
            return nejlepsi, STAV_VYBRANO, prehled
        if duvody:
            nejlepsi.poznamka = "; ".join(p for p in (nejlepsi.poznamka,
                                                      "pozor: " + ", ".join(duvody)) if p)
            return nejlepsi, STAV_OVERIT, prehled
        return nejlepsi, STAV_OK, prehled
    if skore >= prah_overit:
        return nejlepsi, STAV_OVERIT, prehled
    return nejlepsi, STAV_NENALEZENO, prehled


def zpracuj_radek(vstup, klient, n):
    nazev = (vstup.get("nazev") or "").strip()
    ico = (vstup.get("ico") or "").strip()
    dic = (vstup.get("dic") or "").strip()
    zeme = (vstup.get("zeme") or "").strip().upper()[:2]
    hledana_adresa = {
        "ulice": (vstup.get("ulice") or "").strip(),
        "psc": (vstup.get("psc") or "").strip(),
        "mesto": (vstup.get("mesto") or "").strip(),
    }

    z = Zaznam(hledany_nazev=nazev or ico or dic)
    poznamky = []

    try:
        if not ico and dic:
            cc, num = rozloz_dic(dic)
            if cc == "CZ" and num and num.isdigit():
                ico = num
        if not ico and nazev and re.fullmatch(r"\d{6,8}", re.sub(r"\s", "", nazev)):
            ico = re.sub(r"\s", "", nazev)

        # 1) presna identifikace podle ICO
        if ico and zeme in ("", "CZ") and not n["bez_ares"]:
            try:
                z = ares_podle_ica(klient, ico)
                z.hledany_nazev = nazev or ico
                z.shoda = "100%" if not nazev else "%.0f%%" % (skore_shody(nazev, z.jmeno) * 100)
                z.stav = STAV_OK
            except Exception as e:
                poznamky.append("ARES podle ICO: %s" % e)
                # subjekt jiz neni v hlavnim indexu ARES - zkusit Verejny
                # rejstrik, ktery drzi historii i po vymazu (datum a duvod)
                try:
                    vymaz = ares_vr_vymaz(klient, ico)
                    if vymaz:
                        poznamky.append("vymazan z rejstriku %s%s" % (
                            vymaz["datum"],
                            (", duvod: %s" % vymaz["duvod"]) if vymaz["duvod"] else ""))
                except Exception:
                    pass

        # 1b) presna identifikace zahranicniho subjektu podle zadaneho cisla
        # (LEI, narodni registracni cislo typu HRB/SIREN/CIK zapsane
        # do sloupce ICO) - spolehlivejsi nez hledani jmenem, protoze cislo
        # je na rozdil od nazvu jednoznacne
        if z.stav != STAV_OK and ico and zeme and zeme != "CZ":
            try:
                kandidati = []
                if zeme == "FR" and not n["bez_fr"]:
                    cislice = re.sub(r"\D", "", ico)
                    kandidati = [k for k in fr_podle_nazvu(klient, ico, 10)
                                if k.reg_cislo == cislice]
                elif zeme == "US" and not n["bez_edgar"]:
                    nalezeny = edgar_podle_cik(klient, ico)
                    kandidati = [nalezeny] if nalezeny else []
                elif zeme == "SG" and not n["bez_sg"]:
                    nalezeny = sg_podle_uen(klient, ico.upper())
                    kandidati = [nalezeny] if nalezeny else []
                if not kandidati and not n["bez_gleif"]:
                    if re.fullmatch(r"[A-Za-z0-9]{20}", ico):
                        nalezeny = gleif_podle_lei(klient, ico.upper())
                        kandidati = [nalezeny] if nalezeny else []
                    else:
                        kandidati = gleif_podle_registrovane(klient, ico, zeme)

                if len(kandidati) == 1:
                    z = kandidati[0]
                    z.hledany_nazev = nazev or ico
                    z.stav = STAV_OK
                    z.shoda = "100%"
                    z.poznamka = "; ".join(p for p in (
                        z.poznamka, "nalezeno podle zadaneho identifikacniho cisla") if p)
                elif len(kandidati) > 1:
                    # vzacny pripad - stejne cislo u vice zaznamu (napr.
                    # znovupouzite HRB po zaniku puvodni firmy). Bez nazvu
                    # k rozhodnuti aspon vypsat kandidaty k rucni kontrole
                    if nazev:
                        nej, stav_id, prehled_id = vyber_nejlepsi(
                            kandidati, nazev, n["prah_ok"], n["prah_overit"], zeme,
                            hledana_adresa)
                        if nej is not None and stav_id != STAV_NENALEZENO:
                            nej.hledany_nazev = nazev
                            nej.kandidati = prehled_id
                            z = nej
                    else:
                        z.kandidati = ["%s [%s %s]" % (k.jmeno, k.zeme, k.reg_cislo)
                                      for k in kandidati[:5]]
                        poznamky.append(
                            "zadane cislo odpovida %d ruznym zaznamum - chybi nazev "
                            "k rozliseni" % len(kandidati))
            except Exception as e:
                poznamky.append("presna identifikace podle cisla: %s" % e)

        # 1c) presna identifikace podle DIC pres VIES - kdyz ICO cestu
        # nevyresilo. Data jsou chudsi (jen jmeno a adresa, zadne NACE ani
        # registracni cislo), ale DIC je - na rozdil od nazvu - jednoznacne,
        # takze se zaradi jeste pred hledanim jmenem. Funguje jen pro EU DIC
        # (vies_over pro ostatni vrati None).
        if z.stav != STAV_OK and dic:
            try:
                v = vies_over(klient, dic)
                if v and v["platne"] and v["jmeno"]:
                    cc, _ = rozloz_dic(dic)
                    z.jmeno = v["jmeno"]
                    z.ulice = v["adresa"]
                    z.zeme = z.zeme or cc or ""
                    z.dic = dic
                    z.dic_overeno = "ANO"
                    z.stav = STAV_OK
                    z.shoda = "100%"
                    z.zdroj = "VIES"
                    z.hledany_nazev = nazev or dic
                    poznamky.append("nalezeno podle DIC pres VIES")
            except Exception as e:
                poznamky.append("VIES (hledani podle DIC): %s" % e)

        # 2) hledani podle nazvu
        if z.stav != STAV_OK and nazev:
            nejlepsi, stav, prehled, nej_skore = None, STAV_NENALEZENO, [], -1.0
            # poradi stavu pri rozhodovani, ktery zdroj vyhraje
            vaha = {STAV_OK: 3, STAV_VYBRANO: 2, STAV_OVERIT: 1, STAV_NENALEZENO: 0}

            def zkus(funkce, *args):
                nonlocal nejlepsi, stav, prehled, nej_skore
                if stav == STAV_OK:            # jednoznacna shoda, dal nehledame
                    return
                try:
                    k_nejlepsi, k_stav, k_prehled = vyber_nejlepsi(
                        funkce(klient, *args), nazev, n["prah_ok"], n["prah_overit"], zeme,
                        hledana_adresa)
                except Exception as e:
                    poznamky.append("%s: %s" % (funkce.__name__, e))
                    return
                if k_nejlepsi is None:
                    return
                k_skore = float(k_nejlepsi.shoda.rstrip("%") or 0) / 100.0
                if (vaha[k_stav], k_skore) > (vaha[stav], nej_skore):
                    nejlepsi, stav, nej_skore = k_nejlepsi, k_stav, k_skore
                    prehled = k_prehled or prehled

            # poradi: nejdriv narodni rejstriky, ktere nesou i obor cinnosti,
            # az pak celosvetove zdroje bez oboru (GLEIF) a bez presneho NACE
            # (Wikidata)
            if zeme in ("", "CZ") and not n["bez_ares"]:
                zkus(ares_podle_nazvu, nazev, n["pocet"])
            if zeme in ("", "SK") and not n["bez_sk"]:
                zkus(rpo_sk_podle_nazvu, nazev, min(n["pocet"], 20))
            if zeme == "FR" and not n["bez_fr"]:
                zkus(fr_podle_nazvu, nazev, n["pocet"])
            if zeme == "SG" and not n["bez_sg"]:
                zkus(sg_podle_nazvu, nazev, n["pocet"])
            if zeme == "TW" and not n["bez_tw"]:
                zkus(tw_podle_nazvu, nazev, n["pocet"])
            if zeme in ("", "US") and not n["bez_edgar"]:
                zkus(edgar_podle_nazvu, nazev, n["pocet"])
            if zeme != "CZ" and not n["bez_gleif"]:
                zkus(gleif_podle_nazvu, nazev, zeme or None, n["pocet"])
            if zeme != "CZ" and not n["bez_wikidata"]:
                zkus(wikidata_podle_nazvu, nazev, 5)

            if nejlepsi is not None and stav != STAV_NENALEZENO:
                if nejlepsi.poznamka:
                    poznamky.insert(0, nejlepsi.poznamka)
                nejlepsi.hledany_nazev = nazev
                nejlepsi.stav = stav
                nejlepsi.kandidati = prehled
                z = nejlepsi
            else:
                # nic dost podobneho - data kandidatu se do vystupu neprenaseji,
                # jen se nabidnou v poznamce k rucni kontrole
                z.hledany_nazev = nazev
                z.stav = STAV_NENALEZENO
                z.kandidati = prehled

        if not nazev and not ico and not dic:
            z.stav = STAV_CHYBA
            poznamky.append("prazdny radek vstupu")

        z.ico = z.ico or ico
        z.dic = z.dic or dic
        z.zeme = z.zeme or zeme

        # 3) upresneni oboru cinnosti
        if z.stav != STAV_NENALEZENO and not n["bez_ares"]:
            doplr_prevazujici_nace(klient, z)
        if (z.stav not in (STAV_NENALEZENO, STAV_CHYBA) and not z.nace and not z.obory
                and z.zdroj != "Wikidata" and not n["bez_wikidata"]):
            try:
                shodne = [w for w in wikidata_podle_nazvu(klient, z.jmeno or nazev, 5,
                                                          i_kratky_nazev=True)
                         if skore_shody(z.jmeno or nazev, w.jmeno) >= n["prah_ok"]]
                # stejny nazev v ruznych jazykovych mutacich casto vede na vic
                # QID - obor cinnosti byva zapsany jen u jednoho z nich
                w = next((c for c in shodne if c.obory), shodne[0] if shodne else None)
                if w is not None:
                    if w.poznamka:
                        poznamky.append(w.poznamka)
                    z.obory = w.obory
                    if not z.dic and w.dic:
                        z.dic = w.dic
                    if not z.lei and w.lei:
                        z.lei = w.lei
            except Exception as e:
                poznamky.append("Wikidata: %s" % e)

        # 4) overeni DIC pres VIES
        if n["vies"] and not z.dic and z.zeme == "CZ" and z.ico and "DPH" in z.poznamka:
            try:
                v = vies_over(klient, "CZ" + z.ico)
                if v and v["platne"]:
                    z.dic = "CZ" + z.ico
                    z.dic_overeno = "ANO"
                    poznamky.append("DIC doplneno a overeno pres VIES")
            except Exception as e:
                poznamky.append("VIES (odvozeni DIC): %s" % e)

        if n["vies"] and z.dic and not z.dic_overeno:
            try:
                v = vies_over(klient, z.dic)
                if v is not None:
                    z.dic_overeno = "ANO" if v["platne"] else "NE"
                    if v["platne"]:
                        if not z.jmeno and v["jmeno"]:
                            z.jmeno = v["jmeno"]
                        if not z.ulice and v["adresa"]:
                            z.ulice = v["adresa"]
            except Exception as e:
                poznamky.append("VIES: %s" % e)

        # 5) narodni registracni cislo -> citelny nazev rejstriku / pravni forma
        if z.zdroj == "GLEIF" and not n["bez_gleif_popisy"]:
            try:
                if z.reg_rejstrik:
                    z.reg_rejstrik = gleif_popis_rejstriku(klient, z.reg_rejstrik)
                if z.pravni_forma and len(z.pravni_forma) == 4:
                    z.pravni_forma = gleif_popis_formy(klient, z.pravni_forma)
            except Exception:
                pass

        # 7) vlastni taxonomie - jen z fakticke podkladu: NACE z rejstriku ma
        # prednost, pak obor z Wikidat (strukturovany QID, ne odhad z textu).
        # Bez ani jednoho jde zaznam do XXX-00 - kategorie se z nazvu firmy
        # nehada (hrozi false positive, viz README)
        k = taxonomie.zarad(nace=z.nace, mapa=n["mapa"], kategorie=n["kategorie_ciselnik"],
                            obory=z.obory, mapa_oboru=n["mapa_oboru"])
        z.kod_kategorie = k["kod"]
        z.kategorie = k["kategorie"]
        z.skupina = k["skupina"]
        z.zdroj_kategorie = k["zdroj"]
        if not z.nace and k["nace"]:
            # NACE se u zahranicnich firem bez rejstriku pocita jen jako
            # odhad z oboru cinnosti - proto se oznaci zvlast, ne jako
            # oficialni udaj z rejstriku
            z.nace = k["nace"]
            z.nace_zdroj = "odhad z oboru (Wikidata)"
        if not z.nace_popis:
            z.nace_popis = taxonomie.nazev_nace(z.nace)
        if z.nace and not z.nace_zdroj:
            z.nace_zdroj = z.zdroj

        # 8) je zaznam za aktivni subjekt?
        if not z.aktivni and z.stav not in (STAV_NENALEZENO, STAV_CHYBA):
            poznamky.append("subjekt neni v rejstriku veden jako aktivni")

    except Exception as e:
        z.stav = STAV_CHYBA
        poznamky.append("chyba: %r" % e)

    if z.kandidati and z.stav != STAV_OK:
        poznamky.append("kandidati: " + " | ".join(z.kandidati))
    z.poznamka = "; ".join(p for p in poznamky if p)

    # zaznam bez shody se do datovych sloupcu nepropisuje (viz README), ale
    # hledany nazev musi zustat viditelny i v zakladnim sloupci Jmeno -
    # jinak firma z nenalezene shody v exportu "zmizi"
    if not z.jmeno:
        z.jmeno = z.hledany_nazev or nazev or ico or dic

    # u nenalezene firmy ze zeme bez napojeneho rejstriku aspon predpripravit
    # odkaz na rucni vyhledani - usetri psani nazvu do vyhledavace
    if z.stav == STAV_NENALEZENO and not z.odkaz:
        z.odkaz = manualni_odkaz(z.zeme, z.jmeno)

    # nejlepsi cislo k rucnimu vlozeni do sloupce ICO pri druhem behu
    # (viz rezim --jen-id) - ICO/registracni cislo je citelnejsi nez LEI,
    # proto ma prednost
    z.identifikator = z.ico or z.reg_cislo or z.lei

    return z


# ---------------------------------------------------------------------------
# Vstup / vystup
# ---------------------------------------------------------------------------

MAPOVANI_SLOUPCU = {
    "nazev": ("nazev", "název", "jmeno", "jméno", "name", "firma", "company", "company name",
              "nazev spolecnosti", "název společnosti", "dodavatel", "supplier",
              "supplier name", "vendor", "vendor name", "obchodni jmeno", "obchodní jméno",
              "lieferant", "firmenname"),
    "ico": ("ico", "ičo", "ic", "reg no", "registration number", "company id", "identifikacni cislo"),
    "dic": ("dic", "dič", "vat", "vat id", "vat number", "ust-idnr", "ustidnr", "tax id",
            "st.-nr.", "st-nr"),
    "zeme": ("zeme", "země", "country", "stat", "stát", "land", "iso", "kod zeme"),
    "ulice": ("ulice", "street", "address", "adresa", "strasse", "straße", "adresse"),
    "psc": ("psc", "psč", "zip", "zip code", "postal code", "postcode", "plz"),
    "mesto": ("mesto", "město", "city", "town", "obec", "ort", "stadt"),
}


def klic_sloupce(hlavicka):
    h = bez_diakritiky(hlavicka or "").strip().lower()
    for klic, varianty in MAPOVANI_SLOUPCU.items():
        if h in {bez_diakritiky(v).lower() for v in varianty}:
            return klic
    return None


def nacti_vstup(cesta, sloupec_nazvu=None):
    pripona = os.path.splitext(cesta)[1].lower()
    radky = []

    if pripona in (".xlsx", ".xlsm"):
        try:
            from openpyxl import load_workbook
        except ImportError:
            sys.exit("Pro cteni XLSX nainstalujte openpyxl:  pip install openpyxl")
        ws = load_workbook(cesta, read_only=True, data_only=True).active
        it = ws.iter_rows(values_only=True)
        hlavicka = [str(c) if c is not None else "" for c in next(it, [])]
        mapa = {}
        for i, h in enumerate(hlavicka):
            mapa[i] = "nazev" if (sloupec_nazvu and h == sloupec_nazvu) else klic_sloupce(h)
        if "nazev" not in mapa.values():
            mapa[0] = "nazev"
        for r in it:
            zaznam = {}
            for i, hodnota in enumerate(r):
                k = mapa.get(i)
                if k and hodnota is not None:
                    zaznam[k] = str(hodnota).strip()
            if zaznam.get("nazev") or zaznam.get("ico") or zaznam.get("dic"):
                radky.append(zaznam)
        return radky

    with open(cesta, encoding="utf-8-sig", newline="") as f:
        vzorek = f.read(4096)
        f.seek(0)
        if pripona == ".txt" or not any(d in vzorek for d in ";,\t"):
            return [{"nazev": r.strip()} for r in f if r.strip()]
        try:
            dialekt = csv.Sniffer().sniff(vzorek, delimiters=";,\t|")
        except csv.Error:
            dialekt = csv.excel
            dialekt.delimiter = ";"
        for r in csv.DictReader(f, dialect=dialekt):
            zaznam = {}
            for h, hodnota in r.items():
                k = "nazev" if (sloupec_nazvu and h == sloupec_nazvu) else klic_sloupce(h)
                if k and hodnota:
                    zaznam[k] = str(hodnota).strip()
            if not zaznam and r:
                prvni = next(iter(r.values()), None)
                if prvni:
                    zaznam = {"nazev": str(prvni).strip()}
            if zaznam.get("nazev") or zaznam.get("ico") or zaznam.get("dic"):
                radky.append(zaznam)
    return radky


SLOUPCE_ZAKLAD = [
    ("jmeno", "Jméno"), ("ulice", "Ulice"), ("psc", "PSČ"), ("mesto", "Město"),
    ("zeme", "Země"), ("ico", "IČO"), ("dic", "DIČ"),
    ("nace", "NACE"), ("nace_popis", "NACE popis"),
    ("kod_kategorie", "Kód kategorie"), ("skupina", "Skupina"),
    ("kategorie", "Kategorie dodavatele"),
]
SLOUPCE_DOPLNKY = [
    ("zdroj_kategorie", "Zařazeno podle"), ("zdroj", "Zdroj dat"), ("shoda", "Shoda názvu"),
    ("stav", "Stav"), ("hledany_nazev", "Hledaný název"), ("region", "Region"),
    ("lei", "LEI"), ("reg_cislo", "Registrační číslo"), ("reg_rejstrik", "Rejstřík"),
    ("pravni_forma", "Právní forma"), ("datum_vzniku", "Datum vzniku"),
    ("dic_overeno", "DIČ ověřeno (VIES)"), ("nace_vse", "NACE (všechny)"),
    ("nace_zdroj", "NACE - zdroj"), ("klasifikace", "Klasifikace (US NAICS)"),
    ("odkaz", "Odkaz na rejstřík"), ("poznamka", "Poznámka"),
]

# Rezim --jen-id: prvni sloupce jsou zamerne stejne jako vzorovy vstup
# (Nazev/ICO/DIC/Zeme), aby sel vystup rovnou pouzit jako vstup druheho,
# plneho behu - staci zkontrolovat/opravit doplnene ICO.
SLOUPCE_ID = [
    ("hledany_nazev", "Název"), ("identifikator", "IČO"), ("dic", "DIČ"), ("zeme", "Země"),
    ("jmeno", "Nalezené jméno"), ("reg_rejstrik", "Typ čísla / rejstřík"),
    ("shoda", "Shoda názvu"), ("stav", "Stav"), ("zdroj", "Zdroj dat"),
    ("poznamka", "Poznámka"),
]

SIRKY = {"Jméno": 40, "Ulice": 30, "PSČ": 9, "Město": 20, "Země": 7, "IČO": 12, "DIČ": 15,
         "NACE": 9, "NACE popis": 34, "Kód kategorie": 13, "Skupina": 24,
         "Kategorie dodavatele": 42, "Zařazeno podle": 14, "Zdroj dat": 12, "Shoda názvu": 11,
         "Stav": 12, "Hledaný název": 34, "Region": 18, "LEI": 22,
         "Registrační číslo": 18, "Rejstřík": 20, "Právní forma": 14,
         "NACE - zdroj": 22, "Klasifikace (US NAICS)": 34,
         "Datum vzniku": 13, "DIČ ověřeno (VIES)": 16, "NACE (všechny)": 30,
         "Odkaz na rejstřík": 46, "Poznámka": 70,
         "Název": 34, "Nalezené jméno": 34, "Typ čísla / rejstřík": 20}


def zapis_vystup(zaznamy, cesta, oddelovac=";", kompakt=False, jen_id=False):
    if jen_id:
        sloupce = SLOUPCE_ID
    else:
        sloupce = SLOUPCE_ZAKLAD + ([] if kompakt else SLOUPCE_DOPLNKY)
    hlavicka = [n for _, n in sloupce]
    radky = [[getattr(z, k, "") or "" for k, _ in sloupce] for z in zaznamy]

    if os.path.splitext(cesta)[1].lower() != ".xlsx":
        with open(cesta, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, delimiter=oddelovac)
            w.writerow(hlavicka)
            w.writerows(radky)
        return

    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter
    except ImportError:
        sys.exit("Pro zapis XLSX nainstalujte openpyxl:  pip install openpyxl\n"
                 "(nebo zvolte vystup s priponou .csv)")

    wb = Workbook()
    ws = wb.active
    ws.title = "Dodavatelé"
    ws.append(hlavicka)
    for r in radky:
        ws.append(r)
    hlavicka_font = Font(bold=True, color="FFFFFF")
    vypln = PatternFill("solid", fgColor="2E4A62")
    for b in ws[1]:
        b.font = hlavicka_font
        b.fill = vypln
        b.alignment = Alignment(vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for i, n in enumerate(hlavicka, 1):
        ws.column_dimensions[get_column_letter(i)].width = SIRKY.get(n, 16)

    # druhy list: ciselnik pouzite taxonomie (nema smysl v rezimu --jen-id,
    # kde jde jen o dohledani identifikacniho cisla, ne o zarazeni)
    if not jen_id:
        ws2 = wb.create_sheet("Číselník kategorií")
        ws2.append(["Kód", "Skupina", "Kategorie dodavatele", "Počet dodavatelů"])
        pocty = {}
        for z in zaznamy:
            pocty[z.kod_kategorie] = pocty.get(z.kod_kategorie, 0) + 1
        for kod, skupina, nazev in taxonomie.prehled_kategorii():
            ws2.append([kod, skupina, nazev, pocty.get(kod, 0)])
        for b in ws2[1]:
            b.font = hlavicka_font
            b.fill = vypln
        ws2.freeze_panes = "A2"
        for i, s in enumerate((14, 28, 48, 16), 1):
            ws2.column_dimensions[get_column_letter(i)].width = s

    wb.save(cesta)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    p = argparse.ArgumentParser(
        description="Obohaceni seznamu dodavatelu z verejnych rejstriku "
                    "(ARES, RPO SR, GLEIF, SEC EDGAR, Wikidata, VIES).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""priklady:
  python3 dodavatele.py dodavatele.csv -o vystup.xlsx
  python3 dodavatele.py seznam.txt -o vystup.csv --vies --workers 6
  python3 dodavatele.py --dump-taxonomy taxonomie.json     # export k uprave
  python3 dodavatele.py vstup.csv --taxonomy taxonomie.json
""")
    p.add_argument("vstup", nargs="?", help="CSV / XLSX / TXT se seznamem firem")
    p.add_argument("-o", "--vystup", default="dodavatele_vystup.xlsx",
                   help="vystupni soubor .xlsx nebo .csv (vychozi: %(default)s)")
    p.add_argument("--sloupec", help="nazev sloupce se jmenem firmy, pokud se neurci automaticky")
    p.add_argument("--oddelovac", default=";", help="oddelovac pro CSV vystup (vychozi: ;)")
    p.add_argument("--kompakt", action="store_true", help="jen zakladni sloupce")
    p.add_argument("--jen-id", action="store_true",
                   help="jen dohledat ICO/registracni cislo (bez plneho obohaceni) - "
                        "vystup jde rovnou pouzit jako vstup druheho, plneho behu")
    p.add_argument("--workers", type=int, default=4, help="pocet soubeznych dotazu (vychozi: 4)")
    p.add_argument("--prodleva", type=float, default=0.25,
                   help="min. prodleva mezi dotazy na jeden server v s (vychozi: 0.25)")
    p.add_argument("--pocet", type=int, default=30, help="kolik kandidatu nacist (vychozi: 30)")
    p.add_argument("--prah-ok", type=float, default=0.90,
                   help="skore shody nazvu pro automaticke prijeti (vychozi: 0.90)")
    p.add_argument("--prah-overit", type=float, default=0.72,
                   help="skore, pod kterym je zaznam nenalezeny (vychozi: 0.72)")
    p.add_argument("--vies", action="store_true", help="overit DIC v EU pres VIES (pomalejsi)")
    p.add_argument("--bez-ares", action="store_true")
    p.add_argument("--bez-sk", action="store_true")
    p.add_argument("--bez-fr", action="store_true")
    p.add_argument("--bez-sg", action="store_true")
    p.add_argument("--bez-tw", action="store_true")
    p.add_argument("--bez-gleif", action="store_true")
    p.add_argument("--bez-gleif-popisy", action="store_true",
                   help="nepřekládat kódy GLEIF (rejstřík, právní forma) na text - rychlejší")
    p.add_argument("--bez-edgar", action="store_true")
    p.add_argument("--bez-wikidata", action="store_true")
    p.add_argument("--cache", default=".dodavatele_cache.json.gz",
                   help="soubor s kesi odpovedi (prazdny retezec = bez kese)")
    p.add_argument("--taxonomy", help="JSON soubor s vlastni taxonomii")
    p.add_argument("--dump-taxonomy", metavar="SOUBOR",
                   help="zapsat vestavenou taxonomii do JSON a skoncit")
    p.add_argument("--ua", default=UA, help="hlavicka User-Agent (SEC vyzaduje kontakt)")
    a = p.parse_args(argv)

    if a.dump_taxonomy:
        with open(a.dump_taxonomy, "w", encoding="utf-8") as f:
            json.dump(taxonomie.jako_json(), f, ensure_ascii=False, indent=2)
        print("Taxonomie zapsana do %s" % a.dump_taxonomy)
        return 0

    if not a.vstup:
        p.error("chybi vstupni soubor (nebo pouzijte --dump-taxonomy)")

    mapa, ciselnik, mapa_oboru = None, None, None
    if a.taxonomy:
        with open(a.taxonomy, encoding="utf-8") as f:
            mapa, ciselnik, mapa_oboru = taxonomie.z_json(json.load(f))

    radky = nacti_vstup(a.vstup, a.sloupec)
    if not radky:
        sys.exit("Ve vstupu %s nejsou zadne pouzitelne radky." % a.vstup)
    print("Nacteno %d radku z %s" % (len(radky), a.vstup), file=sys.stderr)

    klient = Klient(cache_soubor=a.cache or None, prodleva=a.prodleva, ua=a.ua)
    n = {"pocet": a.pocet, "prah_ok": a.prah_ok, "prah_overit": a.prah_overit,
         "vies": a.vies, "bez_ares": a.bez_ares, "bez_sk": a.bez_sk,
         "bez_fr": a.bez_fr, "bez_sg": a.bez_sg, "bez_tw": a.bez_tw,
         "bez_gleif": a.bez_gleif, "bez_gleif_popisy": a.bez_gleif_popisy,
         "bez_edgar": a.bez_edgar, "bez_wikidata": a.bez_wikidata,
         "mapa": mapa, "kategorie_ciselnik": ciselnik, "mapa_oboru": mapa_oboru}

    hotovo = [0]
    zamek = threading.Lock()

    def uloha(vstup):
        z = zpracuj_radek(vstup, klient, n)
        with zamek:
            hotovo[0] += 1
            print("  [%d/%d] %-42.42s -> %-11s %s" % (
                hotovo[0], len(radky), z.hledany_nazev, z.stav,
                "%s %s" % (z.kod_kategorie, z.kategorie)), file=sys.stderr)
        return z

    with ThreadPoolExecutor(max_workers=max(1, a.workers)) as ex:
        zaznamy = list(ex.map(uloha, radky))

    klient.uloz_cache()
    zapis_vystup(zaznamy, a.vystup, a.oddelovac, a.kompakt, jen_id=a.jen_id)

    souhrn = {}
    for z in zaznamy:
        souhrn[z.stav] = souhrn.get(z.stav, 0) + 1
    print("\nHotovo -> %s" % a.vystup, file=sys.stderr)
    print("Souhrn: " + ", ".join("%s=%d" % kv for kv in sorted(souhrn.items())), file=sys.stderr)
    nezarazeno = [z for z in zaznamy if z.kod_kategorie == taxonomie.VYCHOZI_KOD]
    if nezarazeno:
        print("Bez kategorie (%d): %s" % (
            len(nezarazeno), ", ".join(z.hledany_nazev for z in nezarazeno[:10])), file=sys.stderr)
    k_kontrole = [z for z in zaznamy if z.stav != STAV_OK]
    if k_kontrole:
        print("K rucni kontrole (%d): %s" % (
            len(k_kontrole), ", ".join(z.hledany_nazev for z in k_kontrole[:10])), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dodavatele.py - obohaceni seznamu dodavatelu z verejnych rejstriku.

Vstup : CSV / XLSX / TXT se seznamem nazvu firem (volitelne ICO, DIC, zeme).
Vystup: XLSX / CSV se sloupci
        Jmeno | Ulice | PSC | Mesto | Zeme | ICO | DIC | NACE
        | Kategorie dodavatele | ...

Zdroje (vse bez API klice):
  ARES     ares.gov.cz                        CR - plny rejstrik vc. NACE a DIC
  RPO SR   api.statistics.sk                  SR - registr pravnickych osob
  INSEE    recherche-entreprises.api.gouv.fr  FR - registr firem vc. NAF (= NACE)
  SEC      sec.gov                            US - spolecnosti registrovane u SEC (+ SIC)
  GLEIF    api.gleif.org                      svet - entity s LEI, narodni registracni cislo
  Wikidata wikidata.org                       zalozni zdroj oboru, DIC a sidla pro velke firmy

Kategorii dodavatele a popis cinnosti neurcuje skript sam (viz komentar
u KATEGORIE nize) - dohleda je az LLM krok (--export-llm/--llm-mapa).

Zavislosti: pouze standardni knihovna (openpyxl jen pro praci s XLSX).
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import re
import shutil
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

UA = "supplier-lookup/1.0 (kontakt: nakup@example.com)"

# ---------------------------------------------------------------------------
# Katalog kategorii dodavatelu + nazvy NACE kodu
#
# Driv dva samostatne soubory (taxonomie.py, nace_nomenklatura.py), skoro
# cele o automatickem odvozovani kategorie z NACE kodu (mapa NACE->kategorie,
# pravidlo "kazdy zapsany obor musi souhlasit"...). To se ukazalo jako
# zbytecna slozitost navic - kategorii i strucny popis cinnosti dnes urcuje
# LLM krok (--export-llm/--llm-mapa), ktery ma k dispozici jmeno firmy,
# adresu a VSECHNY NACE kody, co se u ni nasly - a je v tom o dost lepsi nez
# pevna mapovaci tabulka. Zbyl proto jen:
#   - KATEGORIE: pevny ciselnik kategorii (kod -> skupina, nazev), ze ktereho
#     LLM vybira - je to "zdroj pravdy" pro to, jake kategorie vubec existuji
#   - nazev_nace(): anglicky nazev NACE kodu, pro cteni ve vystupu i v
#     promptu pro LLM
# Cela tabulka je v JSON vedle skriptu (TAXONOMIE_JSON) - je to cisty
# ciselnik, ne kod, tak nema smysl mit ho jako .py.
#
# Cesta se resi pres sys._MEIPASS, kdyz beh jede jako zabalena appka
# (gui.py pres PyInstaller, viz .github/workflows/build-gui.yml) - PyInstaller
# do baliku zahrne jen to, co pozna staticky (importy), takhle otevirany JSON
# soubor ne. Musi se proto explicitne pridat pres --add-data a najit za behu
# v docasnem adresari, kam PyInstaller balik rozbali, jinak by zabalena appka
# hned pri startu spadla na FileNotFoundError.
_ZAKLADNI_ADRESAR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
TAXONOMIE_JSON = os.path.join(_ZAKLADNI_ADRESAR, "taxonomie_data.json")

with open(TAXONOMIE_JSON, encoding="utf-8") as _f:
    _tax = json.load(_f)
KATEGORIE = {k: tuple(v) for k, v in _tax["KATEGORIE"].items()}   # kod -> (skupina, nazev)
VYCHOZI_KOD = _tax["VYCHOZI_KOD"]                                 # "XXX-00" = zatim nezarazeno
SIC_NA_NACE = _tax["SIC_NA_NACE"]                                 # US SIC -> priblizny NACE
NACE_NAZVY = _tax["NACE_NAZVY"]                                   # NACE kod -> anglicky nazev
del _tax, _f


def nazev_nace(kod):
    """
    Anglicky nazev cinnosti pro NACE kod (nejdelsi prefix, ktery nomenklatura
    zna) - pokryva i narodni kody s cislici navic: britska UK SIC 2007
    "62012" i nemecka WZ "62.01.0" vedou na tridu NACE "6201".
    """
    cislice = "".join(c for c in str(kod or "") if c.isdigit())
    for delka in range(min(len(cislice), 4), 1, -1):
        nazev = NACE_NAZVY.get(cislice[:delka])
        if nazev:
            return nazev
    return ""


def sic_na_nace(sic):
    """Prevede US SIC kod (SEC EDGAR) na priblizny NACE (prefixove hledani)."""
    if not sic:
        return None
    sic = "".join(ch for ch in str(sic) if ch.isdigit())
    for delka in range(len(sic), 0, -1):
        hodnota = SIC_NA_NACE.get(sic[:delka])
        if hodnota is not None:
            return hodnota
    return None


def naf_na_nace(naf):
    """
    Francouzsky NAF (APE) je NACE rev. 2 s pismenem na konci - "62.02A" je
    NACE 6202. Staci tedy zahodit oddelovace a koncove pismeno.
    """
    if not naf:
        return ""
    return "".join(ch for ch in str(naf) if ch.isdigit())


def prehled_kategorii():
    """Serazeny seznam (kod, skupina, nazev) - pro ciselnik ve vystupu i v promptu pro LLM."""
    return sorted(((k, v[0], v[1]) for k, v in KATEGORIE.items()))

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

# ARES kody pravni formy pro fyzickou osobu podnikajici (OSVC) - viz RES
# ciselnik pravnich forem. Jmeno osoby (na rozdil od nazvu firmy) neni
# jednoznacny identifikator - u bezneho jmena (Jan Novak) ARES bezne eviduje
# stovky ruznych lidi (napr. "Jan Novak" ma v ARES 428 zaznamu) - proto se
# shoda podle pouheho jmena OSVC bez adresy/ICO k rozliseni nebere jako OK,
# viz vyber_nejlepsi().
OSVC_PRAVNI_FORMY = {"100", "101", "102", "103", "104", "105", "106", "107", "108"}


# ---------------------------------------------------------------------------
# HTTP vrstva: rate limit na host, opakovani pri chybe, cache na disku
# ---------------------------------------------------------------------------

CACHE_JMENO = ".dodavatele_cache.json.gz"

# Kdy kes ulozit uz behem behu. Driv se ukladala az po dobehnuti celeho
# seznamu, takze preruseny beh (Ctrl+C, zavrene okno appky, pad) zahodil
# vsechno stazene a dalsi beh zacinal od nuly - navenek to vypadalo, ze kes
# nefunguje. Zapisuje se cela kes najednou, u tisicu firem uz to nejsou
# jednotky milisekund, proto krome poctu novych odpovedi i minimalni odstup:
# rezie zapisu tak zustane nizka i u velke kese.
PRUBEZNY_ZAPIS_PO = 200        # novych odpovedi
PRUBEZNY_ZAPIS_ODSTUP = 30.0   # s od posledniho ulozeni


def _adresar_kese():
    """Adresar pro kes v profilu uzivatele (bez vytvareni)."""
    domov = os.path.expanduser("~")
    if sys.platform == "win32":
        zaklad = os.environ.get("LOCALAPPDATA") or domov
    elif sys.platform == "darwin":
        zaklad = os.path.join(domov, "Library", "Caches")
    else:
        zaklad = os.environ.get("XDG_CACHE_HOME") or os.path.join(domov, ".cache")
    return os.path.join(zaklad, "dodavatele")


def vychozi_cache():
    """
    Kde drzet kes: pevne v profilu uzivatele (%LOCALAPPDATA%, ~/Library/Caches,
    ~/.cache). Driv to byla relativni cesta ".dodavatele_cache.json.gz" resena
    proti pracovnimu adresari - u zabalene appky spustene dvojklikem je ten
    nepredvidatelny (na macOS dokonce korenovy adresar, kam se zapsat neda),
    takze se kes tise neulozila.

    Nasledna oprava davala prednost kesi lezici v pracovnim adresari, cimz ale
    umisteni zase zaviselo na tom, odkud se program spusti: z projektoveho
    adresare se pouzila jedna kes, po dvojkliku na appku druha, a beh, ktery
    "uz jednou probehl", stahoval vsechno znovu. Ted je misto jedno jedine
    a stara kes z pracovniho adresare se do nej jednorazove prekopiruje
    (jen kdyz v profilu jeste zadna neni - at se necim starym neprepise ta,
    do ktere se aktualne pise).
    """
    try:
        adresar = _adresar_kese()
        os.makedirs(adresar, exist_ok=True)
    except OSError:
        # Nezapisovatelny profil - at to radeji bezi bez kese nez spadne.
        return CACHE_JMENO
    cil = os.path.join(adresar, CACHE_JMENO)
    if not os.path.exists(cil) and os.path.exists(CACHE_JMENO):
        try:
            shutil.copyfile(CACHE_JMENO, cil)
        except OSError:
            return CACHE_JMENO
    return cil


class Klient:
    def __init__(self, cache_soubor=None, prodleva=0.25, pokusy=3, timeout=25, ua=UA):
        self.prodleva = prodleva
        self.pokusy = pokusy
        self.timeout = timeout
        self.ua = ua
        self._zamek = threading.Lock()
        self._zamek_zapisu = threading.Lock()   # serializuje zapisy kese na disk
        self._posledni = {}
        self._cache_soubor = cache_soubor
        self._cache = {}
        self._zmenena = False
        self._od_zapisu = 0     # novych odpovedi od posledniho ulozeni kese
        self._cas_zapisu = time.monotonic()
        self.z_kese = 0         # statistika behu: odpovedi vzatych z kese
        self.stazeno = 0        # statistika behu: odpovedi stazenych ze site
        self._obnova = threading.local()   # viz zapni_obnovu/vypni_obnovu
        if cache_soubor and os.path.exists(cache_soubor):
            try:
                with self._otevri(cache_soubor, "rt") as f:
                    self._cache = json.load(f)
            except Exception as e:
                # Poskozenou kes zahodime, ale potichu ne - jinak se jen
                # zahadne kazdy beh vleze stejne dlouho jako ten prvni.
                print("Kes %s se nepodarilo nacist (%s), zaklada se nova."
                      % (cache_soubor, e), file=sys.stderr)
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

    def zapni_obnovu(self):
        """
        Pro aktualni vlakno vynuti pri ziskej() ignorovani cteni z kese (zapis
        do kese probiha porad, vysledek se tedy osvezi) - viz --obnovit ve
        spustit(), kde se takhle znovu dotazuji jen firmy se spatnym stavem
        z tohoto behu, aniz by se musela mazat cela kes.
        """
        self._obnova.aktivni = True

    def vypni_obnovu(self):
        self._obnova.aktivni = False

    def ziskej(self, url, hlavicky=None, json_body=None, ocisti=None):
        """
        Vrati telo odpovedi. `ocisti` je funkce nad rozparsovanym JSON, ktera
        z odpovedi vyhodi nepouzivane casti - kes pak neroste do stovek MB.
        """
        klic = url
        if json_body is not None:
            klic += "|" + json.dumps(json_body, sort_keys=True, ensure_ascii=False)
        if not getattr(self._obnova, "aktivni", False):
            with self._zamek:
                if klic in self._cache:
                    self.z_kese += 1
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
                with urllib.request.urlopen(req, timeout=self.timeout) as odp:
                    text = odp.read().decode("utf-8", errors="replace")
                if ocisti is not None:
                    try:
                        text = json.dumps(ocisti(json.loads(text)), ensure_ascii=False)
                    except (ValueError, KeyError, TypeError):
                        pass
                with self._zamek:
                    self._cache[klic] = text
                    self._zmenena = True
                    self.stazeno += 1
                    self._od_zapisu += 1
                    ulozit = (self._od_zapisu >= PRUBEZNY_ZAPIS_PO
                              and time.monotonic() - self._cas_zapisu
                              >= PRUBEZNY_ZAPIS_ODSTUP)
                if ulozit:
                    self.uloz_cache()
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
        """
        Zapise kes na disk. Vola se nejen na konci behu, ale i prubezne
        (viz PRUBEZNY_ZAPIS_PO), takze musi snest soubezne dotazy ostatnich
        vlaken - obsah se proto pod zamkem zkopiruje (jen reference na
        retezce, levne) a serializuje se az kopie, jinak by json.dump padal
        na "dictionary changed size during iteration".
        """
        if not self._cache_soubor:
            return
        with self._zamek:
            if not self._zmenena:
                return
            data = dict(self._cache)
            self._zmenena = False
            self._od_zapisu = 0
            self._cas_zapisu = time.monotonic()
        tmp = self._cache_soubor + ".tmp"
        with self._zamek_zapisu:
            try:
                with self._otevri(tmp, "wt") as f:
                    json.dump(data, f, ensure_ascii=False)
                os.replace(tmp, self._cache_soubor)
            except OSError as e:
                # Kes je jen zrychleni - neulozena at beh nezabije. Ale at
                # o tom uzivatel vi, jinak jen zahadne kazdy beh trva stejne.
                print("Kes se nepodarilo ulozit do %s: %s"
                      % (self._cache_soubor, e), file=sys.stderr)
                with self._zamek:
                    self._zmenena = True   # zkusit to znovu pri dalsim zapisu
                try:
                    os.remove(tmp)
                except OSError:
                    pass


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
    # Kategorie dodavatele a popis cinnosti se NEURCUJI automaticky (viz
    # komentar u KATEGORIE vyse) - zustavaji prazdne, dokud je nedoplni LLM
    # krok (--export-llm/--llm-mapa, viz pouzij_llm_mapu).
    kod_kategorie: str = ""
    kategorie: str = ""
    skupina: str = ""
    popis: str = ""     # co firma skutecne dodava - popis od LLM
    zdroj: str = ""
    shoda: str = ""
    stav: str = STAV_NENALEZENO
    region: str = ""
    lei: str = ""
    reg_cislo: str = ""
    reg_rejstrik: str = ""
    rpo_id: str = ""    # interni ID v RPO SR pro dohledani SK NACE (viz doplnit_sk_nace)
    pravni_forma: str = ""
    datum_vzniku: str = ""
    odkaz: str = ""
    poznamka: str = ""
    obory: list = field(default_factory=list)      # QID oboru z Wikidat
    jmena: list = field(default_factory=list)      # dalsi nazvy (jine jazyky/prepisy)
    aktivni: bool = True
    kandidati: list = field(default_factory=list)
    nace_nejisty: bool = False   # rejstrikem deklarovana hlavni cinnost kategorii neurcuje


# ---------------------------------------------------------------------------
# ARES (Ceska republika)
# ---------------------------------------------------------------------------

# Firma nema jeden "hlavni" zapsany obor - ma jich zapsanych vic (Asseco
# Central Europe jich ma v ARES 23) a rejstrik mezi nimi nerozlisuje. Pole
# `nace` (jeden kod) se proto plni jen tam, kde hlavni cinnost deklaruje SAM
# rejstrik (ceske RES - prevazujici cinnost, francouzsky NAF), `nace_vse`
# nese vzdy VSECHNY zapsane kody - kategorii i popis cinnosti z nich urcuje
# az LLM krok (--export-llm/--llm-mapa), ne my sami (viz komentar u KATEGORIE).


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
    # "czNace" = CZ-NACE 2025 (nova revize), "czNace2008" = starsi CZ-NACE
    # 2008 - stejna prednost nove revize jako u ares_prevazujici_nace vyse,
    # aby sloupec NACE (vsechny) nesl kody v jedne soustave, ne namixovane
    # ze dvou ruznych revizi.
    kody = s.get("czNace") or s.get("czNace2008") or []
    # ARES hlavni obor neoznacuje - `nace` proto zustava prazdne a doplni ho az
    # doplr_prevazujici_nace() z RES, kde ho rejstrik skutecne deklaruje.
    ico = s.get("ico") or ""
    return Zaznam(
        jmeno=s.get("obchodniJmeno") or "",
        ulice=_ares_ulice(sidlo),
        psc=_psc(sidlo.get("psc")),
        mesto=sidlo.get("nazevObce") or "",
        zeme=sidlo.get("kodStatu") or "CZ",
        ico=ico,
        dic=s.get("dic") or "",
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

    RES vraci prevazujici cinnost hned ve dvou klasifikacnich soustavach:
    "czNacePrevazujici" (CZ-NACE 2025 = NACE Rev. 2.1, zavazna revize EU
    statistiky od 1.1.2025, v RES vychozi od 1.1.2026) a "czNacePrevazujici2008"
    (starsi CZ-NACE 2008 = NACE Rev. 2, ktere RES drzi soubezne jen po
    prechodne obdobi, cca 4 roky od zavedeni). Preferuje se novejsi 2025
    soustava. Nejde o "cerstvejsi hodnotu tehoz cisla" - jde o dve ruzne klasifikacni
    soustavy, kde stejne cislo muze v kazde znamenat neco jineho (napr.
    trida 58.12 byla v 2008 "vydavani adresaru", v 2025 uz "vydavani novin") -
    proto se nemixuji, jen se bere jedna nebo druha cela hodnota naraz.
    2008 pole zustava jen jako zaloha pro pripad, ze by 2025 pole u
    konkretniho zaznamu chybelo.

    "00"/"0000" znamena u RES "neurceno" (subjekt nema prevazujici cinnost
    formalne nastavenou - typicky OSVC s vice zivnostmi bez oznacene hlavni)
    a neni to skutecny NACE kod - takovy zaznam se ignoruje, jinak by prepsal
    i skutecne deklarovanou cinnost nepouzitelnou hodnotou.
    """
    ico = re.sub(r"\D", "", str(ico)).zfill(8)
    data = json.loads(klient.ziskej(ARES_RES.format(ico=ico), ocisti=_ares_ocisti))
    for zaznam in data.get("zaznamy", []):
        nace = zaznam.get("czNacePrevazujici") or zaznam.get("czNacePrevazujici2008")
        cislice = re.sub(r"\D", "", str(nace or ""))
        if cislice and cislice.strip("0"):
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
        z.nace_popis = nazev_nace(nace)


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
    """
    Vyhledavaci pole RPO SR (fullName) je na interpunkci prekvapive citlive -
    s carkou pred pravni formou ("Firma, a.s.") nebo s teckovanou zkratkou
    ("Firma a.s." i "Firma a. s.") vraci 0 vysledku, zatimco bez pravni formy
    ("Firma") normalne najde. Dotaz se proto posila v ocistene podobe
    (normalizuj_nazev) - presnost vyberu spravneho zaznamu resi az nasledne
    porovnani skore_shody s puvodnim (neocistenym) nazvem.
    """
    dotaz = normalizuj_nazev(nazev) or nazev
    url = RPO_SK + "?" + urllib.parse.urlencode({"fullName": dotaz, "limit": pocet})
    data = json.loads(klient.ziskej(url, ocisti=lambda d: {"results": [
        {k: v for k, v in r.items()
         if k in ("id", "fullNames", "addresses", "identifiers", "establishment", "termination")}
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
            rpo_id=str(r.get("id") or ""),
            datum_vzniku=r.get("establishment") or "",
            aktivni=not r.get("termination"),
            zdroj="RPO SR",
            odkaz="https://www.registeruz.sk/cruz-public/domain/accountingentity/simplesearch?ico=%s" % ico,
            poznamka="zanikl %s" % r.get("termination") if r.get("termination") else "",
        ))
    return vysledky


RPO_SK_DETAIL = "https://api.statistics.sk/rpo/v1/entity/{id}"


def _rpo_sk_detail_ocisti(data):
    return {k: v for k, v in data.items() if k in ("statisticalCodes", "legalForms")}


def rpo_sk_detail(klient, entity_id):
    """
    Vyhledavaci endpoint RPO SR (rpo_sk_podle_nazvu) vraci jen jmeno/adresu/ICO -
    hlavni ekonomicka cinnost (SK NACE, stejne cislovani jako CZ-NACE - obojí
    je narodni provedeni NACE Rev. 2) a pravni forma jsou az na urovni
    jednotliveho zaznamu (RPO SR ji vede jako soucast statistickych kodu,
    aktualizovanych Statistickym uradem SR).
    """
    data = json.loads(klient.ziskej(
        RPO_SK_DETAIL.format(id=entity_id), ocisti=_rpo_sk_detail_ocisti))
    hlavni = (data.get("statisticalCodes") or {}).get("mainActivity") or {}
    forma = _sk_platny(data.get("legalForms")) or {}
    return {
        "nace": str(hlavni.get("code") or ""),
        "pravni_forma": (forma.get("value") or {}).get("value") or "",
    }


def doplnit_sk_nace(klient, z):
    """Doplni SK NACE hlavni cinnosti a pravni formu z detailu RPO SR."""
    if z.zdroj != "RPO SR" or not z.rpo_id or z.nace:
        return
    try:
        detail = rpo_sk_detail(klient, z.rpo_id)
    except Exception:
        return
    if detail["nace"]:
        z.nace = detail["nace"]
        z.nace_popis = nazev_nace(detail["nace"])
    if detail["pravni_forma"] and not z.pravni_forma:
        z.pravni_forma = detail["pravni_forma"]


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
    # v USA se NACE nepouziva - SEC vede jeho starsiho predchudce SIC. NACE
    # se dopocitava jen jako priblizny ekvivalent, aby sloupec NACE mel
    # smysluplnou hodnotu i u americkych firem.
    nace = sic_na_nace(sic) or ""
    ulice, mesto, stat, psc = _edgar_adresa(ci)
    cik_cislo = cik.lstrip("0") if cik else ""
    return Zaznam(
        jmeno=h("conformed-name") or nazev_zaloha,
        ulice=ulice, psc=psc, mesto=mesto, region=stat, zeme="US",
        reg_cislo=cik_cislo, reg_rejstrik="SEC CIK",
        nace=nace, nace_popis=nazev_nace(nace),
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
    for z in vysledky:
        if not z.jmeno:
            # U hromadneho vyhledavani podle jmena SEC u firem s vic
            # registrovanymi subjekty (napr. vic dcerinych spolecnosti
            # jedne skupiny) vraci zaznam bez <conformed-name> vubec -
            # bez jmena by kandidat dostal 0% shodu a jinak spravny
            # CIK/SIC (napr. skutecny obor cinnosti) by se tise zahodil.
            z.jmeno = nazev
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


_DE_LOCAL = threading.local()


# "Ulice cislo, PSC Mesto." - format adres v datech OpenCorporates. Cast
# firem ma adresu neuplnou (jen ulice, bez PSC/mesta) - v tom pripade zustane
# cely retezec v ulici a psc/mesto prazdne.
_DE_ADRESA_RE = re.compile(r"^(?P<ulice>.*?),\s*(?P<psc>\d{5})\s+(?P<mesto>.*?)\.?\s*$")


_DE_SLOUPCE = ("company_number", "name", "registered_address", "current_status",
               "register_art", "register_nummer")


_DE_REG_CISLO_RE = re.compile(r"\b(HRA|HRB|GnR|PR|VR)\s*0*(\d+)\b", re.IGNORECASE)


# (nazev sloupce v CSV, nazev sloupce v nasi SQLite tabulce)
_GB_SLOUPCE_CSV = (
    ("CompanyNumber", "company_number"), ("CompanyName", "name"),
    ("CompanyStatus", "status"), ("CompanyCategory", "category"),
    ("IncorporationDate", "incorporation_date"),
    ("RegAddress.AddressLine1", "address1"), ("RegAddress.AddressLine2", "address2"),
    ("RegAddress.PostTown", "post_town"), ("RegAddress.PostCode", "post_code"),
    ("SICCode.SicText_1", "sic1"), ("SICCode.SicText_2", "sic2"),
    ("SICCode.SicText_3", "sic3"), ("SICCode.SicText_4", "sic4"),
)
_GB_SLOUPCE = tuple(nazev_db for _, nazev_db in _GB_SLOUPCE_CSV)

_GB_LOCAL = threading.local()


_GB_SIC_RE = re.compile(r"^\s*(\d{4,5})")


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
        nace = naf_na_nace(naf)
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
            nace_popis=nazev_nace(nace),
            nace_vse=naf,
            pravni_forma=r.get("nature_juridique") or "",
            datum_vzniku=r.get("date_creation") or "",
            aktivni=aktivni,
            zdroj="INSEE/INPI",
            odkaz="https://annuaire-entreprises.data.gouv.fr/entreprise/%s" % siren if siren else "",
            poznamka="zanikla firma (INSEE)" if not aktivni else "",
        ))
    return vysledky


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
        # OSVC: kdyz mame vic stejnojmennych osob (aspon jedna dalsi se stejnym
        # jmenem mezi VSEMI kandidaty, ne jen mezi temi s vysokym skore) a
        # zadana adresa nesedi ani na tu nejlepe skorujici, nejde jen o "trochu
        # nejiste" - presna kombinace jmeno+adresa mezi kandidaty vubec neni.
        # Radeji NENALEZENO, nez tipovat (byt s upozornenim v poznamce), ktery
        # z nekolika stejnojmennych je ten spravny - propsani cizi adresy/ICO
        # by bylo horsi nez prazdno. Musi se resit pred VYBRANO/OVERIT - jinak
        # "srovnatelni" (pocitane jen z podobnosti jmena) skoro vzdy odchyti
        # tenhle pripad driv a schova ho za VYBRANO.
        if nejlepsi.pravni_forma in OSVC_PRAVNI_FORMY and adresa and any(adresa.values()):
            adresa_nesedi = any(d.startswith(("sidlo v", "PSC ")) for d in duvody)
            stejne_jmeno = sum(
                1 for k in kandidati
                if k.pravni_forma in OSVC_PRAVNI_FORMY
                and normalizuj_nazev(k.jmeno) == normalizuj_nazev(nejlepsi.jmeno))
            if adresa_nesedi and stejne_jmeno > 1:
                return None, STAV_NENALEZENO, prehled

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
        # OSVC nalezena jen podle jmena osoby, bez adresy k rozliseni - jmeno
        # samo o sobe neni jednoznacne (na rozdil od nazvu firmy), takze i
        # jediny takto ziskany kandidat neni jisty (viz OSVC_PRAVNI_FORMY) -
        # jina stejnojmenna osoba mohla byt jen mimo nactenych "pocet" kandidatu.
        if nejlepsi.pravni_forma in OSVC_PRAVNI_FORMY and not (adresa and any(adresa.values())):
            nejlepsi.poznamka = "; ".join(p for p in (
                nejlepsi.poznamka,
                "pozor: nalezeno jen podle jmena osoby (OSVC) bez adresy k rozliseni - "
                "u beznych jmen muze v ARES existovat vic stejnojmennych osob, "
                "doplnte adresu nebo ICO pro jistotu",
            ) if p)
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
        if ico and zeme in ("", "CZ"):
            try:
                z = ares_podle_ica(klient, ico)
                z.hledany_nazev = nazev or ico
                z.shoda = "100%" if not nazev else "%.0f%%" % (skore_shody(nazev, z.jmeno) * 100)
                z.stav = STAV_OK
                # Presne cislo (ICO, nebo ICO odvozene z DIC) muze byt na
                # vstupu spatne - preklep, spatne zkopirovany radek apod.
                # U OSVC muze byt jinak stejne jmeno zadano se spravnou
                # adresou, ale s cislem patricim jinemu stejnojmennemu
                # clovku - bez kontroly adresy by se to tise vzalo jako
                # jiste OK. Kontroluje se JEN u OSVC (fyzickych osob) -
                # u firem je bezne, ze provozni/korespondencni adresa na
                # vstupu neodpovida formalnimu sidlu v ARES, a takovy
                # nesoulad nic neznamena (na rozdil od skutecne jine
                # osoby/firmy u shodneho jmena).
                if z.pravni_forma in OSVC_PRAVNI_FORMY:
                    adr_bonus, adr_duvod = _shoduje_se_adresa(hledana_adresa, z)
                    if adr_duvod and adr_bonus < 0:
                        z.stav = STAV_OVERIT
                        poznamky.append(
                            "pozor: zadane ICO/DIC bylo v ARES nalezeno, ale zadana "
                            "adresa neodpovida (%s) - zkontrolujte, jestli cislo "
                            "patri ke spravne osobe" % adr_duvod)
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
                if zeme == "FR":
                    cislice = re.sub(r"\D", "", ico)
                    kandidati = [k for k in fr_podle_nazvu(klient, ico, 10)
                                if k.reg_cislo == cislice]
                elif zeme == "US":
                    nalezeny = edgar_podle_cik(klient, ico)
                    kandidati = [nalezeny] if nalezeny else []
                if not kandidati:
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
            if zeme in ("", "CZ"):
                zkus(ares_podle_nazvu, nazev, n["pocet"])
            if zeme in ("", "SK"):
                zkus(rpo_sk_podle_nazvu, nazev, min(n["pocet"], 20))
            if zeme == "FR":
                zkus(fr_podle_nazvu, nazev, n["pocet"])
            if zeme in ("", "US"):
                zkus(edgar_podle_nazvu, nazev, n["pocet"])
            if zeme != "CZ":
                zkus(gleif_podle_nazvu, nazev, zeme or None, n["pocet"])
            if zeme != "CZ":
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

        # Udaje ze vstupu se doplni tam, kde je rejstrik nedal - typicky
        # u nenalezene firmy, kde by jinak radek ve vystupu zustal skoro
        # prazdny a nesel by porovnat s puvodnim seznamem. Prepsat rejstrikovy
        # udaj vstupnim se ale nesmi: kdyz firmu najdeme, plati adresa
        # z rejstriku, i kdyz se od zadane lisi (prave to je casto duvod,
        # proc se hledani nepovedlo napoprve).
        z.ico = z.ico or ico
        z.dic = z.dic or dic
        z.zeme = z.zeme or zeme
        z.ulice = z.ulice or hledana_adresa["ulice"]
        z.psc = z.psc or hledana_adresa["psc"]
        z.mesto = z.mesto or hledana_adresa["mesto"]

        # 3) upresneni oboru cinnosti
        if z.stav != STAV_NENALEZENO:
            doplr_prevazujici_nace(klient, z)
            # "00"/"0000" v prevazujici cinnosti znamena doslova "neurceno" -
            # subjekt nema hlavni cinnost formalne nastavenou (typicky OSVC
            # s vice zivnostmi bez oznacene hlavni). Skutecnou cinnost pak
            # dohleda az LLM krok (--export-llm), zaznam se jen oznaci.
            zakladni_kod = re.sub(r"\D", "", str(z.nace or ""))
            if zakladni_kod and zakladni_kod.strip("0") == "":
                z.nace_nejisty = True
                poznamky.append(
                    "firma nema v ARES zapsanou zadnou hlavni cinnost (kod %s "
                    "= neurceno) - overte skutecnou cinnost (--export-llm)" % z.nace)
                if z.stav == STAV_OK:
                    z.stav = STAV_OVERIT
        if z.stav != STAV_NENALEZENO:
            doplnit_sk_nace(klient, z)
        if (z.stav not in (STAV_NENALEZENO, STAV_CHYBA) and not z.nace and not z.obory
                and z.zdroj != "Wikidata"):
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


        # 5) narodni registracni cislo -> citelny nazev rejstriku / pravni forma
        if z.zdroj == "GLEIF":
            try:
                if z.reg_rejstrik:
                    z.reg_rejstrik = gleif_popis_rejstriku(klient, z.reg_rejstrik)
                if z.pravni_forma and len(z.pravni_forma) == 4:
                    z.pravni_forma = gleif_popis_formy(klient, z.pravni_forma)
            except Exception:
                pass

        # 7) anglicky nazev k jiz zjistenemu NACE kodu. Kategorii dodavatele
        # a popis skutecne cinnosti dnes NEURCUJEME sami (viz komentar
        # u KATEGORIE na zacatku souboru) - o to se stara az LLM krok
        # (--export-llm/--llm-mapa), ktery ma k dispozici VSECHNY zapsane
        # NACE kody, ne jen tenhle jeden.
        if not z.nace_popis:
            z.nace_popis = nazev_nace(z.nace)
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


# Jeden pevny seznam sloupcu - zadny --kompakt/--jen-id prepinac, pro ktery
# by si clovek musel pamatovat, jaky vystup zrovna dostane. Doplnkove sloupce
# (SLOUPCE_DOPLNKY), ktere jsou prazdne u VSECH firem v danem behu, se
# nepridavaji - jen by roztahovaly tabulku o prazdno (typicky LEI nebo
# Odkaz na rejstřík u ciste ceskeho seznamu, kde vsechno vyresil ARES).
SLOUPCE_ZAKLAD = [
    ("jmeno", "Jméno"), ("ulice", "Ulice"), ("psc", "PSČ"), ("mesto", "Město"),
    ("zeme", "Země"), ("ico", "IČO"), ("dic", "DIČ"),
    ("nace_vse", "NACE"), ("stav", "Stav"), ("zdroj", "Zdroj dat"),
    ("kod_kategorie", "Kód kategorie"), ("skupina", "Skupina"),
    ("kategorie", "Kategorie dodavatele"), ("popis", "Popis činnosti"),
]
SLOUPCE_DOPLNKY = [
    ("nace_zdroj", "NACE - zdroj"),
    ("lei", "LEI"), ("reg_cislo", "Registrační číslo"), ("reg_rejstrik", "Rejstřík"),
    ("pravni_forma", "Právní forma"), ("datum_vzniku", "Datum vzniku"),
    ("odkaz", "Odkaz na rejstřík"), ("poznamka", "Poznámka"),
]


def zaznamy_z_vystupu(cesta):
    """
    Nacte uz vygenerovany vystup (XLSX/CSV z drivejsiho behu, viz
    zapis_vystup) zpet do Zaznamu - pro --z-vystupu, ktere umozni
    --export-llm/--llm-mapa bez opakovani cele enrichment casti (dotazy do
    rejstriku). Sloupce se poznaji podle stejneho seznamu jako pri zapisu
    (SLOUPCE_ZAKLAD/SLOUPCE_DOPLNKY), takze funguje i vystup bez doplnkovych
    sloupcu (ty v danem behu chybely, protoze byly prazdne u vsech firem).
    """
    if os.path.splitext(cesta)[1].lower() in (".xlsx", ".xlsm"):
        from openpyxl import load_workbook
        ws = load_workbook(cesta, read_only=True, data_only=True).active
        it = ws.iter_rows(values_only=True)
        hlavicka = [str(h or "").strip() for h in next(it)]
        radky = [["" if v is None else str(v) for v in r] for r in it]
    else:
        with open(cesta, encoding="utf-8-sig", newline="") as f:
            vzorek = f.read(4096)
            f.seek(0)
            try:
                dialekt = csv.Sniffer().sniff(vzorek, delimiters=";,\t|")
            except csv.Error:
                dialekt = csv.excel
                dialekt.delimiter = ";"
            r = csv.reader(f, dialect=dialekt)
            hlavicka = [h.strip() for h in next(r)]
            radky = list(r)

    indexy = {pole: hlavicka.index(nazev) for pole, nazev in SLOUPCE_ZAKLAD + SLOUPCE_DOPLNKY
              if nazev in hlavicka}
    if "jmeno" not in indexy:
        sys.exit("V souboru %s nenajdu sloupec 'Jméno' - je to opravdu vystup "
                 "tohohle nastroje?" % cesta)
    zaznamy = []
    for r in radky:
        z = Zaznam()
        for pole, i in indexy.items():
            if i < len(r) and r[i]:
                setattr(z, pole, str(r[i]).strip())
        z.hledany_nazev = z.jmeno
        if z.jmeno:
            zaznamy.append(z)
    return zaznamy

SIRKY = {"Jméno": 40, "Ulice": 30, "PSČ": 9, "Město": 20, "Země": 7, "IČO": 12, "DIČ": 15,
         "Kód kategorie": 13, "Skupina": 24, "Kategorie dodavatele": 42, "Popis činnosti": 46,
         "Zdroj dat": 12, "Stav": 12, "LEI": 22, "NACE - zdroj": 22,
         "Registrační číslo": 18, "Rejstřík": 20, "Právní forma": 14,
         "Datum vzniku": 13, "NACE": 30, "Odkaz na rejstřík": 46, "Poznámka": 70}


# ---------------------------------------------------------------------------
# Zarazeni pres LLM chat (MS Copilot, ChatGPT...) - bez API klice
#
# Kategorii dodavatele a strucny popis cinnosti neurcujeme sami (viz komentar
# u KATEGORIE na zacatku souboru) - bez programoveho pristupu k LLM (jen
# chatove okno) to nejde zapojit primo do behu skriptu, takze nastroj pripravi
# soubor k rucnimu vlozeni do chatu a pak nacte odpoved zpet. LLM dostane
# jmeno, adresu a VSECHNY NACE kody, co jsme u firmy nasli - a z toho urci
# kategorii z naseho ciselniku a napise, co firma skutecne dodava.
# ---------------------------------------------------------------------------

def zapis_export_llm(zaznamy, cesta, davka=None):
    """
    Vypise dodavatele do textoveho souboru pripraveneho na vlozeni do LLM chatu
    (Copilot, ChatGPT...) - bez API klice, mezikrok dela clovek v chatu mimo
    skript (viz pouzij_llm_mapu() pro nacteni odpovedi zpet).

    Export je vzdy za VSECHNY dodavatele, i ty, kteri uz kategorii/popis maji -
    novy beh v chatu proste prepise stary. Vraci (pocet vypsanych firem,
    seznam zapsanych cest).
    """
    kandidati = [z for z in zaznamy if z.hledany_nazev or z.jmeno]
    if not kandidati:
        return 0, []

    def obsah(davka_zaznamu):
        radky = [
            "Pro kazdou z firem nize urci (1) NACE kod skutecne hlavni cinnosti, "
            "(2) kod kategorie z ciselniku nize a (3) strucny popis, co firma "
            "skutecne dodava. U kazde firmy je v hranate zavorce seznam JEJICH "
            "NACE kodu zapsanych v obchodnim rejstriku, pokud je rejstrik uvadi - "
            "ber je jako hlavni napovedu pro NACE odpoved (bud jeden z nich "
            "potvrd, nebo navrhni presnejsi, pokud zjevne neodpovida skutecne "
            "cinnosti; rejstrik casto vede jen zastaraly nebo formalni udaj, "
            "napr. 'maloobchod pres internet' u firmy delajici 3D tisk). "
            "U firem OZNACENYCH '[bez zapsaneho oboru]' NACE navrhni cele sam "
            "podle vlastnich znalosti o firme (nazev casto napovi, o jakou "
            "firmu jde). Pokud si u NACE ani kategorie nejsi jisty/a nebo "
            "o firme nic nenajdes, napis misto kodu 'neznamo' - chybejici udaj "
            "je lepsi nez neopodstatneny odhad.",
            "",
            "ČÍSELNÍK KATEGORIÍ:",
        ]
        radky += _ciselnik_do_promptu()
        radky += [
            "",
            "FIRMY K URČENÍ (%d):" % len(davka_zaznamu),
        ]
        for z in davka_zaznamu:
            udaje = [x for x in (z.zeme, z.ulice, z.psc, z.mesto) if x]
            # Kody se vypisuji i s urednim nazvem - LLM (a clovek pri kontrole)
            # cte "4791 Intermediation service activities" mnohem lip nez "4791".
            popsane = []
            for c in dict.fromkeys(x for x in z.nace_vse.split(",") if x):
                nazev = nazev_nace(c)
                popsane.append("%s %s" % (c, nazev) if nazev else c)
            kontext = (" [zapsane obory: %s]" % "; ".join(popsane) if popsane
                       else " [bez zapsaneho oboru]")
            radky.append("- %s%s%s" % (z.hledany_nazev or z.jmeno,
                                       " (%s)" % ", ".join(udaje) if udaje else "", kontext))
        radky += [
            "",
            "Odpověz přesně v tomto formátu, jeden řádek na firmu, oddělovač ';', "
            "beze změny pořadí a bez dalšího textu okolo:",
            "Původní název;NACE kód;Kód kategorie;Čím se firma zabývá",
            "",
            "Poslední sloupec napiš vlastními slovy (pár slov až věta) - slouží "
            "ke kontrole, aby šlo posoudit, jestli NACE a kategorie sedí, aniž "
            "by to musel někdo dohledávat znovu.",
        ]
        return "\n".join(radky)

    davky = _rozdel_davky(kandidati, davka)
    cesty = _zapis_davky(cesta, davky, obsah)
    return len(kandidati), cesty


def _ciselnik_do_promptu():
    """Ciselnik kategorii pro vlozeni do promptu - serazeny po skupinach, jeden radek na kategorii."""
    radky, skupina_predchozi = [], None
    for kod, skupina, nazev in sorted(
            (k, v[0], v[1]) for k, v in KATEGORIE.items() if k != VYCHOZI_KOD):
        if skupina != skupina_predchozi:
            radky.append("  [%s]" % skupina)
            skupina_predchozi = skupina
        radky.append("    %s = %s" % (kod, nazev))
    return radky


def _rozdel_davky(polozky, velikost):
    """Rozdeli seznam do davek po `velikost` polozkach (bez deleni = [polozky])."""
    if not velikost or velikost <= 0 or len(polozky) <= velikost:
        return [polozky]
    return [polozky[i:i + velikost] for i in range(0, len(polozky), velikost)]


def _zapis_davky(cesta, davky, obsah_davky):
    """
    Zapise jednu nebo vice davek do souboru - pri jedine davce primo do
    `cesta`, pri vice davkach do cislovanych souboru `<zaklad>_01<pripona>`
    atd., aby se kazda davka dala vlozit do LLM chatu zvlast (Copilot/ChatGPT
    maji praktický strop, kolik firem najednou spolehlive zpracuji).
    Vraci seznam skutecne zapsanych cest.
    """
    if len(davky) == 1:
        with open(cesta, "w", encoding="utf-8") as f:
            f.write(obsah_davky(davky[0]))
        return [cesta]
    zaklad, pripona = os.path.splitext(cesta)
    cesty = []
    for i, davka in enumerate(davky, 1):
        cesta_davky = "%s_%02d%s" % (zaklad, i, pripona)
        with open(cesta_davky, "w", encoding="utf-8") as f:
            f.write(obsah_davky(davka))
        cesty.append(cesta_davky)
    return cesty


_NACE_KOD_RE = re.compile(r"\b\d{2,6}(?:\.\d+)?\b")
_KATEGORIE_KOD_RE = re.compile(r"\b[A-Z]{2,4}-\d{2}\b")


def nacti_llm_odpovedi(cesta):
    """
    Nacte odpoved z LLM chatu (Nazev;NACE kod;Kod kategorie;Popis - viz
    zapis_export_llm) zpet. Vraci {klic nazvu: {"nace": kod, "kategorie": kod,
    "popis": text}}.
    """
    mapa = {}
    with open(cesta, encoding="utf-8-sig", newline="") as f:
        vzorek = f.read(4096)
        f.seek(0)
        # Format vzdy pozadujeme se strednikem, ale sloupec s popisem casto
        # obsahuje carku v beznem textu - u kratkych/jednoradkovych souboru
        # (posledni davka pri --export-davka) to csv.Sniffer bez dalsich
        # signalu spolehlive plete s carkou jako oddelovacem a tise vrati
        # prazdnou mapu. Kdyz je ve vzorku vubec nejaky strednik, bere se
        # jako jisty oddelovac rovnou - sniffing je jen zalozni pro jiny format.
        dialekt = csv.excel
        if ";" in vzorek:
            dialekt.delimiter = ";"
        else:
            try:
                dialekt = csv.Sniffer().sniff(vzorek, delimiters=";,\t|")
            except csv.Error:
                dialekt = csv.excel
                dialekt.delimiter = ";"
        for radek in csv.reader(f, dialect=dialekt):
            if len(radek) < 2:
                continue
            nazev = radek[0].strip()
            kod_nace = _nace_z_pole(radek[1] if len(radek) > 1 else "")
            kod_kat = _kategorie_z_pole(radek[2] if len(radek) > 2 else "")
            popis = radek[3].strip() if len(radek) > 3 else ""
            if not kod_kat:
                # Kod kategorie se nenasel na ocekavane pozici (LLM format
                # nedodrzelo) - zkusi se najit kdekoli ve zbytku radku. Kod
                # kategorie se vyjme jako prvni, jinak by jeho koncove cislice
                # (napr. "PRO-03") zamotaly hledani NACE.
                zbytek = " ".join(radek[1:])
                kod_kat = _kategorie_z_pole(zbytek)
                if not kod_nace:
                    kod_nace = _nace_z_pole(_KATEGORIE_KOD_RE.sub(" ", zbytek))
            if not nazev or not (kod_nace or kod_kat or popis):
                continue
            klic = normalizuj_nazev(nazev)
            if klic:
                mapa[klic] = {"nace": kod_nace, "kategorie": kod_kat, "popis": popis}
    return mapa


def _nace_z_pole(text):
    """Prvni rozpoznatelny NACE kod v poli, jen cislice ('62.01' -> '6201')."""
    shoda = _NACE_KOD_RE.search(text or "")
    return re.sub(r"\D", "", shoda.group()) if shoda else ""


def _kategorie_z_pole(text):
    """Kod kategorie v poli; kod mimo nas ciselnik (preklep/halucinace) se zahodi."""
    shoda = _KATEGORIE_KOD_RE.search(text or "")
    kod = shoda.group() if shoda else ""
    return kod if kod in KATEGORIE else ""


def pouzij_llm_mapu(zaznamy, mapa):
    """
    Aplikuje odpoved z LLM chatu (viz zapis_export_llm) na zaznamy.

    Kod kategorie a popis cinnosti se prevezmou vzdy, kdyz je mapa obsahuje -
    i pro firmu, ktera uz je mela z predchoziho behu v chatu. NACE od LLM se
    naopak pouzije JEN tam, kde firma dosud zadny NACE nema (nenasel se
    v zadnem rejstriku) - skutecny udaj z rejstriku se nikdy neprepisuje
    odhadem. Takovy NACE se oznaci ve sloupci "NACE - zdroj" jako odhad LLM,
    ne rejstrikovy fakt.

    Vraci pocet zmenenych zaznamu.
    """
    zmeny = 0
    for z in zaznamy:
        if not (z.hledany_nazev or z.jmeno):
            continue
        klic = normalizuj_nazev(z.hledany_nazev or z.jmeno)
        odpoved = mapa.get(klic)
        if not odpoved:
            continue
        kod_nace = odpoved.get("nace", "")
        kod_kat, popis = odpoved.get("kategorie", ""), odpoved.get("popis", "")
        zmena = False
        if kod_nace and not z.nace and not z.nace_vse:
            # Sloupec "NACE" ve vystupu ctuze pole nace_vse (vsechny zname
            # kody), ne nace (jen jeden "hlavni") - obe se proto musi
            # nastavit spolu, jinak by odhad z LLM ve vystupu nebyl videt.
            z.nace = kod_nace
            z.nace_vse = kod_nace
            z.nace_zdroj = "odhad LLM"
            if not z.nace_popis:
                z.nace_popis = nazev_nace(kod_nace)
            zmena = True
        if kod_kat:
            skupina, nazev_kat = KATEGORIE[kod_kat]
            z.kod_kategorie, z.kategorie, z.skupina = kod_kat, nazev_kat, skupina
            zmena = True
        if popis:
            z.popis = popis
            zmena = True
        if zmena:
            zmeny += 1
    return zmeny


def _stylizuj_hlavicku_xlsx(ws, hlavicka, sirky=None):
    """Spolecny vzhled hlavicky pro vsechny XLSX vystupy - tucne bile pismo na
    tmavem podkladu, zamrazeny prvni radek, autofilter, sirky sloupcu podle SIRKY."""
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    sirky = sirky if sirky is not None else SIRKY
    hlavicka_font = Font(bold=True, color="FFFFFF")
    vypln = PatternFill("solid", fgColor="2E4A62")
    for b in ws[1]:
        b.font = hlavicka_font
        b.fill = vypln
        b.alignment = Alignment(vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for i, n in enumerate(hlavicka, 1):
        ws.column_dimensions[get_column_letter(i)].width = sirky.get(n, 16)
    return hlavicka_font, vypln


def zapis_vystup(zaznamy, cesta, oddelovac=";"):
    # Doplnkove sloupce, ktere jsou prazdne u VSECH firem, se do vystupu
    # nedavaji - jen by ho rozsirovaly o prazdno. Typicky LEI nebo Odkaz na
    # rejstřík u ciste ceskeho seznamu, kde vsechno vyresil ARES.
    doplnky = [(k, n) for k, n in SLOUPCE_DOPLNKY
               if any(str(getattr(z, k, "") or "").strip() for z in zaznamy)]
    sloupce = SLOUPCE_ZAKLAD + doplnky
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
    hlavicka_font, vypln = _stylizuj_hlavicku_xlsx(ws, hlavicka)

    # druhy list: nas ciselnik kategorii, at je videt, co vsechno existuje
    # a kolik dodavatelu do ktere kategorie zatim spadlo.
    ws2 = wb.create_sheet("Číselník kategorií")
    ws2.append(["Kód", "Skupina", "Kategorie dodavatele", "Počet dodavatelů"])
    pocty = {}
    for z in zaznamy:
        kod = z.kod_kategorie or VYCHOZI_KOD   # prazdne = jeste nezarazeno LLM krokem
        pocty[kod] = pocty.get(kod, 0) + 1
    for kod, skupina, nazev in prehled_kategorii():
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
                    "(ARES, RPO SR, INSEE, SEC EDGAR, GLEIF, Wikidata).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""priklady:
  python3 dodavatele.py dodavatele.csv -o vystup.xlsx
  python3 dodavatele.py dodavatele.csv --export-llm pro_llm.txt
  python3 dodavatele.py dodavatele.csv --llm-mapa odpoved_z_chatu.csv -o vystup.xlsx
  python3 dodavatele.py dodavatele.csv --obnovit -o vystup.xlsx
""")
    p.add_argument("vstup", nargs="?", help="CSV / XLSX / TXT se seznamem firem")
    p.add_argument("-o", "--vystup", default="dodavatele_vystup.xlsx",
                   help="vystupni soubor .xlsx nebo .csv (vychozi: %(default)s)")
    p.add_argument("--z-vystupu", metavar="SOUBOR",
                   help="misto --vstup vzit uz hotovy vystup z drivejsiho behu "
                        "(XLSX/CSV) a pokracovat rovnou na --export-llm/--llm-mapa, "
                        "bez opakovani dotazu do rejstriku")
    p.add_argument("--export-llm", metavar="SOUBOR",
                   help="vypsat dodavatele do textu pripraveneho na vlozeni do LLM "
                        "chatu (Copilot, ChatGPT...) - LLM podle jmena, adresy "
                        "a nalezenych NACE kodu urci kategorii z naseho ciselniku "
                        "a strucny popis cinnosti")
    p.add_argument("--export-davka", type=int, metavar="N",
                   help="rozdelit --export-llm do vice souboru po N firmach - pro "
                        "vkladani do LLM chatu po castech u velkych seznamu")
    p.add_argument("--llm-mapa", metavar="SOUBOR", nargs="+",
                   help="jeden nebo vice CSV souboru s odpovedi na --export-llm "
                        "(pri vice davkach jeden soubor na davku) ve tvaru "
                        "Nazev;Kod kategorie;Popis - pred zapisem vystupu se "
                        "aplikuje na vsechny zaznamy, pro ktere mapa obsahuje odpoved")
    p.add_argument("--obnovit", action="store_true",
                   help="firmy, ktere v tomto behu skonci jako NENALEZENO/OVERIT/"
                        "CHYBA, se jeste jednou zkusi dohledat s obejitim kese - "
                        "pro pripad, ze se od minule kese firma mezitim "
                        "objevila v rejstriku nebo minule selhalo docasne (vypadek)")
    p.add_argument("--workers", type=int, default=4, help="pocet soubeznych dotazu (vychozi: 4)")
    p.add_argument("--cache", default=None, metavar="SOUBOR",
                   help="vlastni soubor s kesi odpovedi (vychozi: v profilu uzivatele)")
    p.add_argument("--no-cache", dest="bez_kese", action="store_true",
                   help="nepouzivat kes - kazdy dotaz jde znovu do rejstriku "
                        "(a nic se neuklada)")
    p.add_argument("--ua", default=UA, help="hlavicka User-Agent (SEC vyzaduje kontakt)")
    a = p.parse_args(argv)
    if not a.vstup and not a.z_vystupu:
        p.error("chybi vstupni soubor (nebo pouzijte --z-vystupu)")

    try:
        spustit(a)
    except RuntimeError as e:
        sys.exit(str(e))
    except KeyboardInterrupt:
        # Kes uz je ulozena (viz spustit) - at je videt, ze prerusenim
        # se stazene odpovedi neztratily a dalsi beh na ne navaze.
        print("\nPreruseno. Stazene odpovedi zustaly v kesi, dalsi beh na ne navaze.",
              file=sys.stderr)
        return 130
    return 0


def spustit(a, na_radek=None):
    """
    Provede plne obohaceni podle `a` (argparse.Namespace, nebo jakykoli
    objekt se stejnymi atributy jako CLI parametry main() - viz gui.py,
    ktery si vlastni Namespace staví rucne) a vrati seznam zpracovanych
    Zaznamu. Sdilene jadro pro CLI (main()) i pro desktopove GUI (gui.py),
    aby se logika behu nemusela udrzovat na dvou mistech.

    `na_radek(hotovo, celkem, zaznam)` se zavola po zpracovani kazdeho
    radku (navic k prubeznemu vypisu na stderr) - GUI si tim aktualizuje
    progress bar bez nutnosti parsovat konzolovy vystup.
    """
    z_kese, stazeno = 0, 0

    if getattr(a, "z_vystupu", None):
        # --z-vystupu: zadne dotazy do rejstriku, jen export/import pro LLM
        # nad uz hotovym vystupem - proto se tu vubec nezaklada Klient/kes
        # ani se nespousti enrichment smycka nize.
        zaznamy = zaznamy_z_vystupu(a.z_vystupu)
        print("Nacteno %d firem z %s" % (len(zaznamy), a.z_vystupu), file=sys.stderr)
    else:
        radky = nacti_vstup(a.vstup, getattr(a, "sloupec", None))
        if not radky:
            raise RuntimeError("Ve vstupu %s nejsou zadne pouzitelne radky." % a.vstup)
        print("Nacteno %d radku z %s" % (len(radky), a.vstup), file=sys.stderr)

        if getattr(a, "bez_kese", False):
            cesta_kese = None
        else:
            # --cache "" znamena tez "bez kese" (drivejsi zpusob, nez pribylo
            # --no-cache); None = neurceno, tedy vychozi misto v profilu.
            cesta_kese = (a.cache if a.cache is not None else vychozi_cache()) or None
        print("Kes: %s" % (cesta_kese or "vypnuta"), file=sys.stderr)
        klient = Klient(cache_soubor=cesta_kese, prodleva=0.25, ua=a.ua)
        n = {"pocet": 30, "prah_ok": 0.90, "prah_overit": 0.72}

        hotovo = [0]
        zamek = threading.Lock()
        obnovit = getattr(a, "obnovit", False)
        SPATNE_STAVY = (STAV_NENALEZENO, STAV_OVERIT, STAV_CHYBA)

        def uloha(vstup):
            z = zpracuj_radek(vstup, klient, n)
            # --obnovit: kdyz beh skoncil se spatnym stavem, zkusit JEStE JEDNOU
            # s obejitim kese - stejny princip jako drivejsi --obnovit-nenalezene,
            # jen bez nutnosti tahat kvuli tomu drivejsi vystup - spatny stav se
            # pozna rovnou v tomhle behu.
            if obnovit and z.stav in SPATNE_STAVY:
                klient.zapni_obnovu()
                try:
                    znovu = zpracuj_radek(vstup, klient, n)
                finally:
                    klient.vypni_obnovu()
                if znovu.stav not in SPATNE_STAVY or znovu.stav != z.stav:
                    z = znovu
            with zamek:
                hotovo[0] += 1
                print("  [%d/%d] %-42.42s -> %s" % (
                    hotovo[0], len(radky), z.hledany_nazev, z.stav), file=sys.stderr)
                if na_radek is not None:
                    na_radek(hotovo[0], len(radky), z)
            return z

        # Kes se uklada i kdyz beh spadne nebo ho uzivatel prerusi - jinak by
        # hodiny stahovani prisly vnivec a dalsi pokus by zacinal od nuly.
        try:
            with ThreadPoolExecutor(max_workers=max(1, a.workers)) as ex:
                zaznamy = list(ex.map(uloha, radky))
        finally:
            klient.uloz_cache()
        z_kese, stazeno = klient.z_kese, klient.stazeno

    if getattr(a, "llm_mapa", None):
        mapa_llm = {}
        for cesta_mapy in a.llm_mapa:
            mapa_llm.update(nacti_llm_odpovedi(cesta_mapy))
        zmeny = pouzij_llm_mapu(zaznamy, mapa_llm)
        print("Zarazeni z odpovedi LLM (%s): pouzito %d/%d" % (
            ", ".join(a.llm_mapa), zmeny, len(mapa_llm)), file=sys.stderr)

    if getattr(a, "export_llm", None):
        pocet, cesty = zapis_export_llm(zaznamy, a.export_llm, davka=getattr(a, "export_davka", None))
        print("Export pro LLM chat -> %s (%d firem)" % (", ".join(cesty), pocet), file=sys.stderr)

    zapis_vystup(zaznamy, a.vystup, getattr(a, "oddelovac", ";"))

    souhrn = {}
    for z in zaznamy:
        souhrn[z.stav] = souhrn.get(z.stav, 0) + 1
    print("\nHotovo -> %s" % a.vystup, file=sys.stderr)
    print("Souhrn: " + ", ".join("%s=%d" % kv for kv in sorted(souhrn.items())), file=sys.stderr)
    if not getattr(a, "z_vystupu", None):
        print("Dotazy: %d z kese, %d stazeno" % (z_kese, stazeno), file=sys.stderr)
    nezarazeno = [z for z in zaznamy if not z.kod_kategorie]
    if nezarazeno:
        print("Bez kategorie (%d): %s" % (
            len(nezarazeno), ", ".join(z.hledany_nazev for z in nezarazeno[:10])), file=sys.stderr)
    k_kontrole = [z for z in zaznamy if z.stav != STAV_OK]
    if k_kontrole:
        print("K rucni kontrole (%d): %s" % (
            len(k_kontrole), ", ".join(z.hledany_nazev for z in k_kontrole[:10])), file=sys.stderr)
    return zaznamy


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dodavatele.py - obohaceni seznamu dodavatelu z verejnych rejstriku.

Vstup : CSV / XLSX / TXT se seznamem nazvu firem (volitelne ICO, DIC, zeme).
Vystup: XLSX / CSV se sloupci
        Jmeno | Ulice | PSC | Mesto | Zeme | ICO | DIC | St.-Nr. 2 | NACE
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
RPO_SK = "https://api.statistics.sk/rpo/v1/search"
GLEIF_API = "https://api.gleif.org/api/v1/lei-records"
GLEIF_AUTO = "https://api.gleif.org/api/v1/autocompletions"
VIES_API = "https://ec.europa.eu/taxation_customs/vies/rest-api/ms/{cc}/vat/{num}"
EDGAR_API = "https://www.sec.gov/cgi-bin/browse-edgar"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"

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
}

STAV_OK = "OK"
STAV_OVERIT = "OVERIT"
STAV_VICE = "VICE_SHOD"
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

    def ziskej(self, url, hlavicky=None, json_body=None, ocisti=None):
        """
        Vrati telo odpovedi. `ocisti` je funkce nad rozparsovanym JSON, ktera
        z odpovedi vyhodi nepouzivane casti - kes pak neroste do stovek MB.
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

    def uloz_cache(self):
        if self._cache_soubor and self._zmenena:
            tmp = self._cache_soubor + ".tmp"
            with self._otevri(tmp, "wt") as f:
                json.dump(self._cache, f, ensure_ascii=False)
            os.replace(tmp, self._cache_soubor)


# ---------------------------------------------------------------------------
# Porovnavani nazvu firem
# ---------------------------------------------------------------------------

def bez_diakritiky(s):
    return "".join(c for c in unicodedata.normalize("NFKD", str(s)) if not unicodedata.combining(c))


def normalizuj_nazev(s):
    """Male pismeno, bez diakritiky, bez pravni formy a interpunkce."""
    if not s:
        return ""
    s = bez_diakritiky(s).lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    tokeny = [t for t in s.split() if t]
    for delka in (3, 2):
        while len(tokeny) > delka and " ".join(tokeny[-delka:]) in PRAVNI_FORMY:
            tokeny = tokeny[:-delka]
    while len(tokeny) > 1 and tokeny[-1] in PRAVNI_FORMY:
        tokeny = tokeny[:-1]
    zbytek = [t for t in tokeny if t not in PRAVNI_FORMY]
    return " ".join(zbytek or tokeny)


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
    stnr2: str = ""
    nace: str = ""
    nace_popis: str = ""
    nace_vse: str = ""
    kod_kategorie: str = ""
    kategorie: str = ""
    skupina: str = ""
    zdroj_kategorie: str = ""
    zdroj: str = ""
    shoda: str = ""
    stav: str = STAV_NENALEZENO
    region: str = ""
    lei: str = ""
    pravni_forma: str = ""
    datum_vzniku: str = ""
    dic_overeno: str = ""
    odkaz: str = ""
    poznamka: str = ""
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
            stnr2=ico,
            datum_vzniku=r.get("establishment") or "",
            zdroj="RPO SR",
            odkaz="https://www.registeruz.sk/cruz-public/domain/accountingentity/simplesearch?ico=%s" % ico,
            poznamka="zanikl %s" % r.get("termination") if r.get("termination") else "",
        ))
    return vysledky


# ---------------------------------------------------------------------------
# GLEIF (LEI) - cely svet
# ---------------------------------------------------------------------------

def _gleif_na_zaznam(rec):
    a = rec.get("attributes", {})
    ent = a.get("entity", {}) or {}
    adr = ent.get("legalAddress") or {}
    hq = ent.get("headquartersAddress") or {}
    radky = [r for r in (adr.get("addressLines") or []) if r]
    je_agent = radky and re.match(r"(?i)\s*c/?o[\s.]", radky[0])
    if (je_agent or not radky) and hq.get("addressLines"):
        adr = hq
        radky = [r for r in hq.get("addressLines") or [] if r]
    zeme = adr.get("country") or ent.get("jurisdiction") or ""
    stav = ent.get("status")
    return Zaznam(
        jmeno=(ent.get("legalName") or {}).get("name") or "",
        ulice=radky[0] if radky else "",
        psc=adr.get("postalCode") or "",
        mesto=adr.get("city") or "",
        zeme=zeme[:2],
        stnr2=ent.get("registeredAs") or "",
        region=adr.get("region") or "",
        lei=a.get("lei") or "",
        pravni_forma=(ent.get("legalForm") or {}).get("id") or "",
        zdroj="GLEIF",
        odkaz="https://search.gleif.org/#/record/%s" % a.get("lei", ""),
        poznamka="stav v LEI: %s" % stav if stav and stav != "ACTIVE" else "",
    )


def gleif_podle_nazvu(klient, nazev, zeme=None, pocet=10):
    """Kombinuje presnejsi filtr na nazev, naseptavac a fulltext."""
    nalezene, videne = [], set()

    def pridej(zaznamy):
        for z in zaznamy:
            if z.lei and z.lei not in videne:
                videne.add(z.lei)
                nalezene.append(z)

    def dotaz(parametry):
        url = GLEIF_API + "?" + urllib.parse.urlencode(parametry)
        data = json.loads(klient.ziskej(url, hlavicky={"Accept": "application/vnd.api+json"}))
        return [_gleif_na_zaznam(r) for r in data.get("data", [])]

    zakladni = {"page[size]": min(pocet, 50)}
    if zeme:
        zakladni["filter[entity.legalAddress.country]"] = zeme
    try:
        pridej(dotaz(dict(zakladni, **{"filter[entity.legalName]": nazev})))
    except Exception:
        pass

    # naseptavac vraci LEI presnych/blizkych nazvu, ktere fulltext casto minie
    try:
        url = GLEIF_AUTO + "?" + urllib.parse.urlencode({"field": "fulltext", "q": nazev})
        data = json.loads(klient.ziskej(url, hlavicky={"Accept": "application/vnd.api+json"}))
        leie = [d["relationships"]["lei-records"]["data"]["id"]
                for d in data.get("data", [])[:5]
                if d.get("relationships", {}).get("lei-records", {}).get("data")]
        for lei in leie:
            if lei in videne:
                continue
            rec = json.loads(klient.ziskej(GLEIF_API + "/" + lei,
                                           hlavicky={"Accept": "application/vnd.api+json"}))
            pridej([_gleif_na_zaznam(rec["data"])])
    except Exception:
        pass

    if not nalezene:
        try:
            pridej(dotaz(dict(zakladni, **{"filter[fulltext]": nazev})))
        except Exception:
            pass
    return nalezene


# ---------------------------------------------------------------------------
# SEC EDGAR - USA
# ---------------------------------------------------------------------------

def _edgar_adresa(prvek):
    for typ in ("business", "mailing"):
        for adr in prvek.iter("address"):
            if adr.get("type") != typ:
                continue

            def h(tag):
                e = adr.find(tag)
                return (e.text or "").strip() if e is not None and e.text else ""
            ulice = " ".join(x for x in (h("street1"), h("street2")) if x)
            if ulice or h("city"):
                return ulice, h("city"), h("state"), h("zip")
    return "", "", "", ""


def edgar_podle_nazvu(klient, nazev, pocet=10):
    url = EDGAR_API + "?" + urllib.parse.urlencode({
        "company": nazev, "type": "", "dateb": "", "owner": "include",
        "count": pocet, "action": "getcompany", "output": "atom"})
    try:
        koren = ET.fromstring(klient.ziskej(
            url, hlavicky={"Accept": "application/atom+xml"}).encode("utf-8"))
    except (ET.ParseError, Exception):
        return []

    def z_prvku(ci, cik_zaloha="", nazev_zaloha=""):
        def h(tag):
            e = ci.find(tag)
            return (e.text or "").strip() if e is not None and e.text else ""
        cik = h("cik") or cik_zaloha
        sic = h("assigned-sic")
        nace = taxonomie.sic_na_nace(sic) or ""
        ulice, mesto, stat, psc = _edgar_adresa(ci)
        return Zaznam(
            jmeno=h("conformed-name") or nazev_zaloha,
            ulice=ulice, psc=psc, mesto=mesto, region=stat, zeme="US",
            stnr2="CIK %s" % cik.lstrip("0") if cik else "",
            nace=nace, nace_popis=taxonomie.nazev_nace(nace),
            zdroj="SEC EDGAR",
            odkaz="https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=%s" % cik if cik else "",
            poznamka=("SIC %s %s" % (sic, h("assigned-sic-desc"))).strip() if sic else "",
        )

    ci = koren.find("company-info")
    if ci is not None:
        return [z_prvku(ci)]

    vysledky = []
    for entry in koren.iter():
        if not entry.tag.endswith("entry"):
            continue
        ci = entry.find("company-info")
        if ci is not None:
            vysledky.append(z_prvku(ci))
            continue
        titul = next((e for e in entry if e.tag.endswith("title")), None)
        if titul is not None and titul.text:
            m = re.match(r"(.*?)\s*\(CIK (\d+)\)", titul.text.strip())
            if m:
                vysledky.append(z_prvku(entry, m.group(2), m.group(1)))
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


def wikidata_podle_nazvu(klient, nazev, pocet=5):
    url = WIKIDATA_API + "?" + urllib.parse.urlencode({
        "action": "wbsearchentities", "search": nazev, "language": "en",
        "uselang": "en", "type": "item", "limit": pocet, "format": "json"})
    hledani = json.loads(klient.ziskej(url, ocisti=lambda d: {"search": [
        {"id": h.get("id")} for h in d.get("search", [])]})).get("search", [])
    if not hledani:
        return []

    qidy = [h["id"] for h in hledani[:3]]
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
        odkazovane.update(tvrzeni(c, "P452")[:3] + tvrzeni(c, "P17")[:1] + tvrzeni(c, "P159")[:1])
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
        obory = [popisky.get(q, "") for q in tvrzeni(c, "P452")[:3]]
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


def vies_over(klient, dic):
    cc, num = rozloz_dic(dic)
    if not cc or cc not in EU_STATY:
        return None
    data = json.loads(klient.ziskej(VIES_API.format(cc=cc, num=num)))
    return {"platne": bool(data.get("isValid")),
            "jmeno": (data.get("name") or "").strip(" -"),
            "adresa": (data.get("address") or "").strip(" -")}


# ---------------------------------------------------------------------------
# Zpracovani jednoho radku
# ---------------------------------------------------------------------------

def vyber_nejlepsi(kandidati, nazev, prah_ok, prah_overit):
    """Vrati (nejlepsi, stav, prehled kandidatu)."""
    if not kandidati:
        return None, STAV_NENALEZENO, []
    ohodnocene = sorted(((skore_shody(nazev, k.jmeno), k) for k in kandidati), key=lambda x: -x[0])
    skore, nejlepsi = ohodnocene[0]
    nejlepsi.shoda = "%.0f%%" % (skore * 100)
    prehled = ["%s [%s] %.0f%%" % (k.jmeno, k.ico or k.lei or k.mesto or "?", s * 100)
               for s, k in ohodnocene[:5] if s > 0.3]
    if skore >= prah_ok:
        druhy = ohodnocene[1][0] if len(ohodnocene) > 1 else 0.0
        if druhy >= prah_ok and (skore - druhy) < 0.03:
            return nejlepsi, STAV_VICE, prehled
        return nejlepsi, STAV_OK, prehled
    if skore >= prah_overit:
        return nejlepsi, STAV_OVERIT, prehled
    return nejlepsi, STAV_NENALEZENO, prehled


def zpracuj_radek(vstup, klient, n):
    nazev = (vstup.get("nazev") or "").strip()
    ico = (vstup.get("ico") or "").strip()
    dic = (vstup.get("dic") or "").strip()
    zeme = (vstup.get("zeme") or "").strip().upper()[:2]

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

        # 2) hledani podle nazvu
        if z.stav != STAV_OK and nazev:
            nejlepsi, stav, prehled, nej_skore = None, STAV_NENALEZENO, [], -1.0
            # poradi stavu pri rozhodovani, ktery zdroj vyhraje
            vaha = {STAV_OK: 3, STAV_VICE: 2, STAV_OVERIT: 1, STAV_NENALEZENO: 0}

            def zkus(funkce, *args):
                nonlocal nejlepsi, stav, prehled, nej_skore
                if stav == STAV_OK:            # jednoznacna shoda, dal nehledame
                    return
                try:
                    k_nejlepsi, k_stav, k_prehled = vyber_nejlepsi(
                        funkce(klient, *args), nazev, n["prah_ok"], n["prah_overit"])
                except Exception as e:
                    poznamky.append("%s: %s" % (funkce.__name__, e))
                    return
                if k_nejlepsi is None:
                    return
                k_skore = float(k_nejlepsi.shoda.rstrip("%") or 0) / 100.0
                if (vaha[k_stav], k_skore) > (vaha[stav], nej_skore):
                    nejlepsi, stav, nej_skore = k_nejlepsi, k_stav, k_skore
                    prehled = k_prehled or prehled

            # poradi: nejdriv rejstriky, ktere nesou i obor cinnosti
            if zeme in ("", "CZ") and not n["bez_ares"]:
                zkus(ares_podle_nazvu, nazev, n["pocet"])
            if zeme in ("", "SK") and not n["bez_sk"]:
                zkus(rpo_sk_podle_nazvu, nazev, min(n["pocet"], 20))
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

        if not nazev and not ico:
            z.stav = STAV_CHYBA
            poznamky.append("prazdny radek vstupu")

        z.ico = z.ico or ico
        z.dic = z.dic or dic
        z.zeme = z.zeme or zeme

        # 3) upresneni oboru
        if z.stav != STAV_NENALEZENO and not n["bez_ares"]:
            doplr_prevazujici_nace(klient, z)
        obor_z_wikidat = ""
        if (z.stav != STAV_NENALEZENO and not z.nace and z.zdroj != "Wikidata"
                and not n["bez_wikidata"]):
            try:
                for w in wikidata_podle_nazvu(klient, z.jmeno or nazev, 3):
                    if skore_shody(z.jmeno or nazev, w.jmeno) >= n["prah_ok"]:
                        obor_z_wikidat = w.poznamka
                        if obor_z_wikidat:
                            poznamky.append(obor_z_wikidat)
                        if not z.dic and w.dic:
                            z.dic = w.dic
                        if not z.lei and w.lei:
                            z.lei = w.lei
                        break
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

        # 5) St.-Nr. 2
        z.stnr2 = urci_stnr2(z, n["stnr2"])

        # 6) vlastni taxonomie
        podklad_nazev = " ".join(x for x in (z.jmeno or nazev, obor_z_wikidat, z.poznamka) if x)
        k = taxonomie.zarad(nace=z.nace, nazev=podklad_nazev, mapa=n["mapa"],
                            klicova_slova=n["klicova_slova"], kategorie=n["kategorie_ciselnik"])
        z.kod_kategorie = k["kod"]
        z.kategorie = k["kategorie"]
        z.skupina = k["skupina"]
        z.zdroj_kategorie = k["zdroj"]
        if not z.nace_popis:
            z.nace_popis = taxonomie.nazev_nace(z.nace)

    except Exception as e:
        z.stav = STAV_CHYBA
        poznamky.append("chyba: %r" % e)

    if z.kandidati and z.stav != STAV_OK:
        poznamky.append("kandidati: " + " | ".join(z.kandidati))
    z.poznamka = "; ".join(p for p in poznamky if p)
    return z


def urci_stnr2(z, rezim):
    """
    'St.-Nr. 2' je v nemeckych systemech (SAP pole STCD2) druhe danove/registracni
    cislo vedle DIC. Rezimy:
      auto       - u ceskych firem prazdne (staci ICO + DIC), u ostatnich narodni
                   registracni cislo (napr. HRB u DE, CIK u US)
      registrace - vzdy narodni registracni cislo
      ico        - vzdy ICO
      dic        - VAT / DIC
      zadne      - nevyplnovat
    """
    if rezim == "zadne":
        return ""
    if rezim == "dic":
        return z.dic
    if rezim == "ico":
        return z.ico or z.stnr2
    if rezim == "registrace":
        return z.stnr2 or z.ico
    return "" if z.zeme == "CZ" else (z.stnr2 or z.ico)


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
            if zaznam.get("nazev") or zaznam.get("ico"):
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
            if zaznam.get("nazev") or zaznam.get("ico"):
                radky.append(zaznam)
    return radky


SLOUPCE_ZAKLAD = [
    ("jmeno", "Jméno"), ("ulice", "Ulice"), ("psc", "PSČ"), ("mesto", "Město"),
    ("zeme", "Země"), ("ico", "IČO"), ("dic", "DIČ"), ("stnr2", "St.-Nr. 2"),
    ("nace", "NACE"), ("nace_popis", "NACE popis"),
    ("kod_kategorie", "Kód kategorie"), ("skupina", "Skupina"),
    ("kategorie", "Kategorie dodavatele"),
]
SLOUPCE_DOPLNKY = [
    ("zdroj_kategorie", "Zařazeno podle"), ("zdroj", "Zdroj dat"), ("shoda", "Shoda názvu"),
    ("stav", "Stav"), ("hledany_nazev", "Hledaný název"), ("region", "Region"),
    ("lei", "LEI"), ("pravni_forma", "Právní forma"), ("datum_vzniku", "Datum vzniku"),
    ("dic_overeno", "DIČ ověřeno (VIES)"), ("nace_vse", "NACE (všechny)"),
    ("odkaz", "Odkaz na rejstřík"), ("poznamka", "Poznámka"),
]

SIRKY = {"Jméno": 40, "Ulice": 30, "PSČ": 9, "Město": 20, "Země": 7, "IČO": 12, "DIČ": 15,
         "St.-Nr. 2": 16, "NACE": 9, "NACE popis": 34, "Kód kategorie": 13, "Skupina": 24,
         "Kategorie dodavatele": 42, "Zařazeno podle": 14, "Zdroj dat": 12, "Shoda názvu": 11,
         "Stav": 12, "Hledaný název": 34, "Region": 18, "LEI": 22, "Právní forma": 12,
         "Datum vzniku": 13, "DIČ ověřeno (VIES)": 16, "NACE (všechny)": 30,
         "Odkaz na rejstřík": 46, "Poznámka": 70}


def zapis_vystup(zaznamy, cesta, oddelovac=";", kompakt=False):
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

    # druhy list: ciselnik pouzite taxonomie
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
    p.add_argument("--workers", type=int, default=4, help="pocet soubeznych dotazu (vychozi: 4)")
    p.add_argument("--prodleva", type=float, default=0.25,
                   help="min. prodleva mezi dotazy na jeden server v s (vychozi: 0.25)")
    p.add_argument("--pocet", type=int, default=30, help="kolik kandidatu nacist (vychozi: 30)")
    p.add_argument("--prah-ok", type=float, default=0.90,
                   help="skore shody nazvu pro automaticke prijeti (vychozi: 0.90)")
    p.add_argument("--prah-overit", type=float, default=0.72,
                   help="skore, pod kterym je zaznam nenalezeny (vychozi: 0.72)")
    p.add_argument("--stnr2", choices=["auto", "registrace", "ico", "dic", "zadne"],
                   default="auto", help="cim naplnit sloupec St.-Nr. 2 (vychozi: auto)")
    p.add_argument("--vies", action="store_true", help="overit DIC v EU pres VIES (pomalejsi)")
    p.add_argument("--bez-ares", action="store_true")
    p.add_argument("--bez-sk", action="store_true")
    p.add_argument("--bez-gleif", action="store_true")
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

    mapa, klicova, ciselnik = None, None, None
    if a.taxonomy:
        with open(a.taxonomy, encoding="utf-8") as f:
            mapa, klicova, ciselnik = taxonomie.z_json(json.load(f))

    radky = nacti_vstup(a.vstup, a.sloupec)
    if not radky:
        sys.exit("Ve vstupu %s nejsou zadne pouzitelne radky." % a.vstup)
    print("Nacteno %d radku z %s" % (len(radky), a.vstup), file=sys.stderr)

    klient = Klient(cache_soubor=a.cache or None, prodleva=a.prodleva, ua=a.ua)
    n = {"pocet": a.pocet, "prah_ok": a.prah_ok, "prah_overit": a.prah_overit,
         "stnr2": a.stnr2, "vies": a.vies, "bez_ares": a.bez_ares, "bez_sk": a.bez_sk,
         "bez_gleif": a.bez_gleif, "bez_edgar": a.bez_edgar, "bez_wikidata": a.bez_wikidata,
         "mapa": mapa, "klicova_slova": klicova, "kategorie_ciselnik": ciselnik}

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
    zapis_vystup(zaznamy, a.vystup, a.oddelovac, a.kompakt)

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

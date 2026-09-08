"""
Dohledani dodavatele ve verejnych zdrojich - bez API klice, bez behove sluzby.

Ukol tohohle modulu je JEN posbirat, co se o firme da zjistit spolehlive:
identitu (kdo to je) a podklady (cim se zabyva). NIC neklasifikuje - zarazeni
do kategorie dela az LLM z podkladu, ktere tu vzniknou.

Identita, od nejspolehlivejsi:
    ICO  + CZ  -> ARES        uredni nazev, adresa, CZ-NACE, predmet podnikani
    ICO  + SK  -> RPO SR      uredni nazev, adresa, SK-NACE
    DIC (EU)   -> VIES        uredni nazev a adresa, vsech ~20 EU statu
    jen nazev  -> ARES/RPO podle zeme, jinak nic  (identita zustane neoverena)

Podklady k cinnosti:
    ARES-VR    predmet podnikani (cesky text, u firem bez webu casto jediny signal)
    Wikidata   oficialni web (P856), obor, popis
    Wikipedie  uvodni odstavec
    web firmy  <title>, meta popis, <h1>, kus viditelneho textu

Nezarazene zeme (US, CH, JP, HK, SG, ...) nemaji verejny rejstrik zdarma -
u nich se identita neoveruje a rozhoduje web + znalosti LLM. Pozna se to
podle pole `identita`.
"""

import gzip
import html
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
from dataclasses import dataclass, field
from difflib import SequenceMatcher

UA = "dodavatele-audit/2.0 (+https://github.com/ret3030/dodavatele)"

ARES_HLEDAT = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/vyhledat"
ARES_DETAIL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ico}"
ARES_VR = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty-vr/{ico}"
RPO_HLEDAT = "https://api.statistics.sk/rpo/v1/search"
RPO_DETAIL = "https://api.statistics.sk/rpo/v1/entity/{id}"
VIES_API = "https://ec.europa.eu/taxation_customs/vies/rest-api/ms/{cc}/vat/{num}"
WD_API = "https://www.wikidata.org/w/api.php"
WP_API = "https://{lang}.wikipedia.org/w/api.php"

EU_STATY = {"AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "GR", "ES", "FI", "FR",
            "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE",
            "SI", "SK", "XI"}

# Jak byla identita overena - od nejsilnejsi. Jde do Excelu, aby bylo videt,
# ktery radek stoji na urednim zaznamu a ktery jen na dohadu.
IDENT_REJSTRIK = "rejstřík"       # ARES / RPO SR podle ICO nebo presneho nazvu
IDENT_VIES = "VIES (DIČ)"         # uredni nazev z overeni DIC
IDENT_NAZEV = "podle názvu"       # shoda jmenem v rejstriku, ne podle identifikatoru
IDENT_NEOVERENO = "neověřeno"     # zeme bez rejstriku / nenalezeno

BEZ_DIAKRITIKY_TABULKA = str.maketrans({
    "ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ø": "o", "Ø": "O",
    "þ": "th", "Þ": "Th", "æ": "ae", "Æ": "AE", "ß": "ss",
    "ı": "i", "İ": "I", "ĸ": "k", "ħ": "h", "Ħ": "H",
})

PRAVNI_FORMY = {
    # Zbytky po sluceni tecek: "spol. s r.o." -> "spol s ro" (ne "spol s r o",
    # protoze "r.o." se slepi na "ro"). Kdyz tu tyhle varianty chybi, zvedaji
    # podobnost mezi jinak odlisnymi firmami - "ESET s ro" vs "RESET s ro"
    # dava 0.95 a ARES by je zamenil.
    "spol", "a spol", "s ro", "spol s ro", "s r o s", "ro",
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
    "lda", "unipessoal", "kk", "yk", "pte", "pty", "bhd", "sdn",
    "public limited company", "public company limited", "company limited", "co ltd",
    "joint stock company", "designated activity company", "dac",
    "spolka akcyjna", "spolka z ograniczona odpowiedzialnoscia", "sp z o o",
    "societa a responsabilita limitata",
    "sociedad anonima unipersonal", "sociedade anonima",
    "societe par actions simplifiee", "societe a responsabilite limitee",
    "anonim sirketi", "anonim ortakligi", "limited sirketi", "sirketi",
    "reszvenytarsasag", "nyilvanosan mukodo reszvenytarsasag",
    "societate pe actiuni", "societate cu raspundere limitata",
    "kabushiki kaisha", "berhad", "sendirian berhad",
    "publikt aktiebolag", "eingetragener verein",
}

_ICO_RE = re.compile(r"\b\d{6,8}\b")
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Normalizace a porovnavani nazvu
# ---------------------------------------------------------------------------

def bez_diakritiky(s):
    s = str(s or "").translate(BEZ_DIAKRITIKY_TABULKA)
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def normalizuj_nazev(s):
    """Male pismeno, bez diakritiky, bez pravni formy a interpunkce."""
    if not s:
        return ""
    s = bez_diakritiky(s).lower().replace("&", " and ")
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
    if mensi and mensi <= vetsi and len(mensi) >= 2:
        dice = max(dice, max(0.80, 0.97 - 0.015 * (len(vetsi) - len(mensi))))
    return round(max(sekvence, dice), 4)


def _text(s, limit=None):
    t = _WS.sub(" ", html.unescape(_TAG.sub(" ", str(s or "")))).strip()
    return t[:limit] if limit else t


def _zkrat(text, limit):
    """Zkrati na hranici vety nebo slova, at text nekonci uprostred slova."""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    orez = text[:limit]
    for hranice in (". ", "! ", "? ", " · "):
        i = orez.rfind(hranice)
        if i > limit * 0.5:
            return orez[:i + 1].strip()
    i = orez.rfind(" ")
    return (orez[:i] if i > limit * 0.5 else orez).rstrip(" ,;·") + "…"


def _ico(hodnota):
    m = _ICO_RE.search(re.sub(r"\s", "", str(hodnota or "")))
    return m.group(0).zfill(8) if m else ""


def rozloz_dic(dic):
    d = re.sub(r"[^A-Za-z0-9]", "", str(dic or "")).upper()
    m = re.match(r"^([A-Z]{2})(\w+)$", d)
    return (m.group(1), m.group(2)) if m else (None, None)


# ---------------------------------------------------------------------------
# HTTP klient s diskovou kesi (klic = URL) a skrcenim po hostitelich
# ---------------------------------------------------------------------------

PRUBEZNY_ZAPIS_PO = 200
PRUBEZNY_ZAPIS_ODSTUP = 30.0


class Klient:
    def __init__(self, cache_soubor=None, prodleva=0.25, pokusy=3, timeout=20):
        self.prodleva = prodleva
        self.pokusy = pokusy
        self.timeout = timeout
        self._zamek = threading.Lock()
        self._zamek_zapisu = threading.Lock()
        self._posledni = {}
        self._cache_soubor = cache_soubor
        self._cache = {}
        self._zmenena = False
        self._od_zapisu = 0
        self._cas_zapisu = time.monotonic()
        self.z_kese = 0
        self.stazeno = 0
        if cache_soubor and os.path.exists(cache_soubor):
            try:
                with self._otevri(cache_soubor, "rt") as f:
                    self._cache = json.load(f)
            except Exception as e:
                print("Keš %s se nepodařilo načíst (%s), zakládá se nová."
                      % (cache_soubor, e), file=sys.stderr)

    def _otevri(self, cesta, rezim):
        if self._cache_soubor and self._cache_soubor.endswith(".gz"):
            return gzip.open(cesta, rezim, encoding="utf-8")
        return open(cesta, rezim, encoding="utf-8")

    def _cekej(self, url):
        """Rozestup se drzi zvlast pro kazdeho hostitele - ARES a Wikidata se
        tak neblokuji navzajem a bezi soubezne."""
        host = urllib.parse.urlparse(url).netloc
        with self._zamek:
            posledni = self._posledni.get(host, 0.0)
            ted = time.monotonic()
            spat = self.prodleva - (ted - posledni)
            self._posledni[host] = max(ted, posledni + self.prodleva)
        if spat > 0:
            time.sleep(spat)

    def ziskej(self, url, json_body=None, ocisti=None, hlavicky=None):
        klic = url if json_body is None else url + "|" + json.dumps(
            json_body, sort_keys=True, ensure_ascii=False)
        with self._zamek:
            if klic in self._cache:
                self.z_kese += 1
                return self._cache[klic]

        h = {"User-Agent": UA, "Accept": "application/json"}
        if hlavicky:
            h.update(hlavicky)
        telo = None
        if json_body is not None:
            telo = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            h["Content-Type"] = "application/json"

        chyba = None
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
                self._uloz(klic, text)
                return text
            except urllib.error.HTTPError as e:
                chyba = RuntimeError("HTTP %s" % e.code)
                if e.code == 404:
                    break
                if e.code in (429, 500, 502, 503, 504) and pokus < self.pokusy:
                    time.sleep(min(2 ** pokus, 10))
                    continue
                break
            except Exception as e:
                chyba = e
                if pokus < self.pokusy:
                    time.sleep(min(2 ** pokus, 10))
        raise chyba or RuntimeError("neznámá chyba")

    def _uloz(self, klic, text):
        with self._zamek:
            self._cache[klic] = text
            self._zmenena = True
            self.stazeno += 1
            self._od_zapisu += 1
            ulozit = (self._od_zapisu >= PRUBEZNY_ZAPIS_PO
                      and time.monotonic() - self._cas_zapisu >= PRUBEZNY_ZAPIS_ODSTUP)
        if ulozit:
            self.uloz_cache()

    def zapomen(self, url):
        with self._zamek:
            self._cache.pop(url, None)

    def json(self, url, json_body=None, ocisti=None):
        """Dotaz vracejici rozparsovany JSON; pri chybe {} (a nespadne to)."""
        try:
            return json.loads(self.ziskej(url, json_body=json_body, ocisti=ocisti))
        except Exception:
            return {}

    # Kes i pro veci, ktere se nestahuji pres ziskej() - napr. UZ VYTAZENY text
    # z webu firmy. Ukladat cele HTML by kes nafouklo do stovek MB, kdezto
    # vysledek je par set znaku a druhy beh uz nemusi na sit vubec.
    def cti(self, klic):
        with self._zamek:
            syrove = self._cache.get(klic)
        if syrove is None:
            return None
        with self._zamek:
            self.z_kese += 1
        try:
            return json.loads(syrove)
        except ValueError:
            return None

    def zapis(self, klic, hodnota):
        self._uloz(klic, json.dumps(hodnota, ensure_ascii=False))

    def uloz_cache(self):
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
                print("Keš se nepodařilo uložit (%s)" % e, file=sys.stderr)
                with self._zamek:
                    self._zmenena = True


# ---------------------------------------------------------------------------
# Vysledek dohledani
# ---------------------------------------------------------------------------

@dataclass
class Firma:
    # ze vstupu
    vstup_nazev: str = ""
    vstup_adresa: str = ""
    vstup_ico: str = ""
    vstup_dic: str = ""
    vstup_zeme: str = ""
    vstup_objem: str = ""
    # zjisteno
    nazev: str = ""
    ico: str = ""
    dic: str = ""
    ulice: str = ""
    psc: str = ""
    mesto: str = ""
    zeme: str = ""
    pravni_forma: str = ""
    datum_vzniku: str = ""
    aktivni: bool = True
    nace: list = field(default_factory=list)        # kody
    obory: list = field(default_factory=list)       # textovy predmet podnikani / cinnosti
    web: str = ""
    popis_wikidata: str = ""
    popis_wikipedie: str = ""
    web_text: str = ""
    # metadata
    identita: str = IDENT_NEOVERENO
    shoda: float = 0.0
    poznamky: list = field(default_factory=list)

    @property
    def adresa(self):
        casti = [self.ulice, " ".join(x for x in (self.psc, self.mesto) if x), self.zeme]
        return ", ".join(c for c in casti if c) or self.vstup_adresa

    def podklady(self, strucne=False):
        """
        Co o firme vime, jako seznam (stitek, text).

        `strucne=True` je pro prompt do chatu: podklady se zkrati, at se do
        jedne davky vejde 250 firem a da se to vlozit do okna chatu. Na urceni
        oboru staci prvni veta - zbytek je pro cloveka, ktery to overuje.
        """
        limit_polozky = 240 if strucne else 700
        pocet_oboru = 3 if strucne else 8
        out = []
        if self.obory:
            out.append(("zapsané obory",
                        _zkrat("; ".join(self.obory[:pocet_oboru]), limit_polozky)))
        if self.nace:
            out.append(("NACE", ", ".join(self.nace[:6])))
        if self.popis_wikidata:
            out.append(("Wikidata", _zkrat(self.popis_wikidata, limit_polozky)))
        if self.popis_wikipedie:
            out.append(("Wikipedie", _zkrat(self.popis_wikipedie, limit_polozky)))
        if self.web_text:
            out.append(("web", _zkrat(self.web_text, limit_polozky)))
        return out


# ---------------------------------------------------------------------------
# ARES (Ceska republika)
# ---------------------------------------------------------------------------

_ARES_POLE = ("ico", "obchodniJmeno", "sidlo", "dic", "czNace", "pravniForma",
              "datumVzniku", "datumZaniku")


def _ares_ocisti(d):
    if "ekonomickeSubjekty" in d:
        return {"ekonomickeSubjekty": [{k: v for k, v in s.items() if k in _ARES_POLE}
                                       for s in d.get("ekonomickeSubjekty") or []]}
    return {k: v for k, v in d.items() if k in _ARES_POLE}


def _ares_do_firmy(f, d):
    sidlo = d.get("sidlo") or {}
    f.nazev = _text(d.get("obchodniJmeno"))
    f.ico = _ico(d.get("ico"))
    f.dic = _text(d.get("dic")) or f.dic
    ulice = " ".join(str(x) for x in (sidlo.get("nazevUlice"),
                                      sidlo.get("cisloDomovni")) if x)
    f.ulice = ulice or _text(sidlo.get("textovaAdresa")).split(",")[0]
    f.psc = re.sub(r"\D", "", str(sidlo.get("psc") or ""))
    f.mesto = _text(sidlo.get("nazevObce"))
    f.zeme = "CZ"
    f.datum_vzniku = _text(d.get("datumVzniku"))
    f.aktivni = not d.get("datumZaniku")
    if d.get("datumZaniku"):
        f.poznamky.append("zanikla %s" % d["datumZaniku"])
    f.nace = [str(k) for k in (d.get("czNace") or []) if str(k).isdigit()]
    return f


def ares_detail(klient, f, ico):
    """Zaznam podle ICO - nejspolehlivejsi cesta, zadne hadani."""
    d = klient.json(ARES_DETAIL.format(ico=ico), ocisti=_ares_ocisti)
    if not d.get("ico"):
        return False
    _ares_do_firmy(f, d)
    f.identita = IDENT_REJSTRIK
    f.shoda = 1.0
    return True


def ares_podle_nazvu(klient, f, nazev, mesto=""):
    """Hledani jmenem. Prijme jen dost jednoznacnou shodu - radsi nic nez
    spatna firma (spatna identita = spatna kategorie = vadny audit)."""
    d = klient.json(ARES_HLEDAT, json_body={"obchodniJmeno": nazev, "pocet": 20},
                    ocisti=_ares_ocisti)
    kandidati = d.get("ekonomickeSubjekty") or []
    if not kandidati:
        return False

    nejlepsi, nej_skore = None, 0.0
    for s in kandidati:
        sk = skore_shody(nazev, s.get("obchodniJmeno", ""))
        if mesto and _text((s.get("sidlo") or {}).get("nazevObce")):
            if normalizuj_nazev(mesto) == normalizuj_nazev(
                    (s.get("sidlo") or {}).get("nazevObce")):
                sk = min(1.0, sk + 0.05)
        if sk > nej_skore:
            nejlepsi, nej_skore = s, sk
    if nejlepsi is None or nej_skore < 0.90:
        return False
    # dva stejne dobri kandidati -> nevime ktery; nechame na LLM
    stejne = [s for s in kandidati
              if abs(skore_shody(nazev, s.get("obchodniJmeno", "")) - nej_skore) < 0.02]
    if len(stejne) > 1 and nej_skore < 1.0:
        f.poznamky.append("v ARES víc firem podobného jména (%d)" % len(stejne))
        return False

    _ares_do_firmy(f, nejlepsi)
    if not f.nace:                      # seznam z vyhledavani byva chudsi nez detail
        ares_detail(klient, f, f.ico)
    f.identita = IDENT_REJSTRIK if nej_skore >= 0.995 else IDENT_NAZEV
    f.shoda = nej_skore
    return True


def _ares_vr_ocisti(d):
    zazn = (d.get("zaznamy") or [{}])[0]
    return {"cinnosti": zazn.get("cinnosti") or {}, "pravniForma": zazn.get("pravniForma")}


def ares_predmet_podnikani(klient, f):
    """
    Predmet podnikani z Verejneho rejstriku - cesky textovy popis zapsanych
    cinnosti. U firem bez webu je to casto jediny konkretni podklad, ktery
    LLM dostane. Berou se jen aktualne platne polozky (bez datumVymazu).
    """
    if not f.ico:
        return
    d = klient.json(ARES_VR.format(ico=f.ico), ocisti=_ares_vr_ocisti)
    polozky = (d.get("cinnosti") or {}).get("predmetPodnikani") or []
    texty = []
    for p in polozky:
        if not isinstance(p, dict) or p.get("datumVymazu"):
            continue
        t = _text(p.get("hodnota"))
        # obecne zivnosti nesou nulovou informaci, jen by zaplnily prompt
        if t and not t.lower().startswith("výroba, obchod a služby neuvedené"):
            texty.append(t)
    if texty:
        f.obory = list(dict.fromkeys(texty))[:8]
    if d.get("pravniForma") and not f.pravni_forma:
        f.pravni_forma = _text(d["pravniForma"])


# ---------------------------------------------------------------------------
# RPO SR (Slovensko)
# ---------------------------------------------------------------------------

def _sk_platny(polozky):
    """RPO vede jmeno/adresu/ICO jako historii - vrati aktualne platnou."""
    if not polozky:
        return {}
    aktualni = [p for p in polozky if isinstance(p, dict) and not p.get("validTo")]
    return (aktualni or [p for p in polozky if isinstance(p, dict)] or [{}])[-1]


def rpo(klient, f, nazev, ico=""):
    """
    Vyhledavaci pole fullName je hodne fuzzy ("ESET" vrati i "RESET") a citlive
    na interpunkci (s carkou vrati 0). Posila se holy nazev, zaznam se vybira
    striktne: shoda ICO, nebo prave jeden kandidat s presne shodnym jmenem.
    """
    if ico:
        # RPO umi hledat primo podle identifikatoru - presne a bez fuzzy sumu
        d = klient.json(RPO_HLEDAT + "?" + urllib.parse.urlencode(
            {"identifier": ico, "limit": 5}))
    else:
        dotaz = " ".join(t for t in normalizuj_nazev(nazev).split()) or nazev
        d = klient.json(RPO_HLEDAT + "?" + urllib.parse.urlencode(
            {"fullName": dotaz, "limit": 40}))
    vysledky = d.get("results") or []
    if not vysledky:
        return False

    vybrany = None
    if ico:
        for r in vysledky:
            if _ico(_sk_platny(r.get("identifiers")).get("value")) == ico:
                vybrany = r
                break
    if vybrany is None:
        cil = normalizuj_nazev(nazev)
        shody = [r for r in vysledky
                 if normalizuj_nazev(_sk_platny(r.get("fullNames")).get("value")) == cil]
        if len(shody) == 1:
            vybrany = shody[0]
        elif len(shody) > 1:
            f.poznamky.append("v RPO SR víc firem stejného jména (%d)" % len(shody))
    if vybrany is None:
        return False

    jmeno = _sk_platny(vybrany.get("fullNames"))
    adresa = _sk_platny(vybrany.get("addresses"))
    nalezene_ico = _ico(_sk_platny(vybrany.get("identifiers")).get("value"))
    f.nazev = _text(jmeno.get("value"))
    f.ico = nalezene_ico or ico
    f.dic = f.dic or ("SK%s" % f.ico if f.ico else "")
    f.ulice = " ".join(str(x) for x in (adresa.get("street"),
                                        adresa.get("buildingNumber")) if x)
    f.psc = re.sub(r"\D", "", (adresa.get("postalCodes") or [""])[0])
    f.mesto = (adresa.get("municipality") or {}).get("value") or ""
    f.zeme = "SK"
    f.datum_vzniku = _text(vybrany.get("establishment"))
    f.aktivni = not vybrany.get("termination")
    f.identita = IDENT_REJSTRIK if (ico or f.nazev) else IDENT_NAZEV
    f.shoda = 1.0 if ico else skore_shody(nazev, f.nazev)

    eid = str(vybrany.get("id") or "")
    if eid:
        det = klient.json(RPO_DETAIL.format(id=eid))
        hlavni = (det.get("statisticalCodes") or {}).get("mainActivity") or {}
        if str(hlavni.get("code") or "").isdigit():
            f.nace = [str(hlavni["code"])]
        if hlavni.get("value"):
            f.obory = [_text(hlavni["value"])]
        forma = _sk_platny(det.get("legalForms")).get("value") or {}
        f.pravni_forma = _text(forma.get("value") if isinstance(forma, dict) else forma)
    return True


# ---------------------------------------------------------------------------
# VIES - overeni DIC (vsechny staty EU jednim rozhranim)
# ---------------------------------------------------------------------------

VIES_DOCASNE = {"MS_MAX_CONCURRENT_REQ", "MS_UNAVAILABLE", "GLOBAL_MAX_CONCURRENT_REQ",
                "SERVICE_UNAVAILABLE", "TIMEOUT", "SERVER_BUSY"}


def vies(klient, f, dic, pokusy=4):
    """
    Uredni nazev a adresa z overeni DIC. Pro nemecke, nizozemske, rakouske
    a dalsi EU dodavatele je to jedina bezplatna cesta k overene identite.
    """
    cc, num = rozloz_dic(dic)
    if not cc or cc not in EU_STATY:
        return False
    url = VIES_API.format(cc=cc, num=num)
    for pokus in range(1, pokusy + 1):
        d = klient.json(url)
        if not d:
            return False
        chyba = d.get("userError")
        if chyba in VIES_DOCASNE:
            klient.zapomen(url)     # docasny vypadek at nezustane v kesi
            if pokus < pokusy:
                time.sleep(min(2 ** pokus, 6))
                continue
            f.poznamky.append("VIES dočasně nedostupné")
            return False
        if not d.get("isValid"):
            f.poznamky.append("DIČ %s neplatné podle VIES" % dic)
            return False
        jmeno = (d.get("name") or "").strip(" -")
        adresa = (d.get("address") or "").strip(" -")
        if jmeno and jmeno != "---":
            f.nazev = f.nazev or _text(jmeno)
            f.shoda = f.shoda or skore_shody(f.vstup_nazev, jmeno)
        if adresa and not f.ulice:
            f.ulice = _text(adresa.replace("\n", ", "))
        f.dic = dic
        f.zeme = f.zeme or cc
        if f.identita == IDENT_NEOVERENO:
            f.identita = IDENT_VIES
        return True
    return False


# ---------------------------------------------------------------------------
# Wikidata + Wikipedie - popis cinnosti a oficialni web
# ---------------------------------------------------------------------------

def _wd_hodnoty(claims, pid, typ="id"):
    out = []
    for c in claims.get(pid, []):
        try:
            v = c["mainsnak"]["datavalue"]["value"]
        except (KeyError, TypeError):
            continue
        out.append(v["id"] if typ == "id" and isinstance(v, dict) else v)
    return [x for x in out if isinstance(x, str)]


def wikidata(klient, f):
    """Prirazeni entity: podle ICO (presne), jinak podle presneho nazvu."""
    qid = ""
    if f.ico:
        d = klient.json(WD_API + "?" + urllib.parse.urlencode({
            "action": "query", "list": "search",
            "srsearch": "haswbstatement:P4156=%s" % f.ico, "srlimit": 1, "format": "json"}))
        hits = (d.get("query") or {}).get("search") or []
        if hits:
            qid = hits[0].get("title", "")
    if not qid:
        hledany = f.nazev or f.vstup_nazev
        d = klient.json(WD_API + "?" + urllib.parse.urlencode({
            "action": "wbsearchentities", "search": hledany, "language": "cs",
            "uselang": "cs", "type": "item", "limit": 5, "format": "json"}))
        cil = normalizuj_nazev(hledany)
        for s in d.get("search") or []:
            if normalizuj_nazev(s.get("label", "")) == cil:
                qid = s.get("id", "")
                break
    if not re.match(r"^Q\d+$", qid or ""):
        return

    d = klient.json(WD_API + "?" + urllib.parse.urlencode({
        "action": "wbgetentities", "ids": qid,
        "props": "claims|descriptions|sitelinks", "languages": "cs|en|de",
        "sitefilter": "cswiki|enwiki|dewiki", "format": "json"}))
    e = (d.get("entities") or {}).get(qid) or {}
    if not e:
        return
    claims = e.get("claims") or {}

    weby = _wd_hodnoty(claims, "P856", typ="str")
    if weby and not f.web:
        f.web = weby[0]

    popisy = e.get("descriptions") or {}
    casti = [_text((popisy.get(l) or {}).get("value")) for l in ("cs", "en", "de")]
    stitky = _stitky(klient, _wd_hodnoty(claims, "P452") + _wd_hodnoty(claims, "P1056"))
    f.popis_wikidata = _text(" · ".join(x for x in casti[:1] + stitky if x), 400)

    for wiki, lang in (("cswiki", "cs"), ("dewiki", "de"), ("enwiki", "en")):
        titul = ((e.get("sitelinks") or {}).get(wiki) or {}).get("title")
        if titul:
            f.popis_wikipedie = _wikipedie(klient, titul, lang)
            if f.popis_wikipedie:
                break


def _stitky(klient, qidy):
    qidy = [q for q in dict.fromkeys(qidy) if re.match(r"^Q\d+$", q or "")][:8]
    if not qidy:
        return []
    d = klient.json(WD_API + "?" + urllib.parse.urlencode({
        "action": "wbgetentities", "ids": "|".join(qidy), "props": "labels",
        "languages": "cs|en", "format": "json"}))
    out = []
    for ent in (d.get("entities") or {}).values():
        labs = ent.get("labels") or {}
        v = (labs.get("cs") or labs.get("en") or {}).get("value")
        if v:
            out.append(v)
    return out


def _wikipedie(klient, titul, lang):
    d = klient.json(WP_API.format(lang=lang) + "?" + urllib.parse.urlencode({
        "action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1,
        "redirects": 1, "titles": titul, "format": "json"}))
    for pg in ((d.get("query") or {}).get("pages") or {}).values():
        if pg.get("extract"):
            return _text(pg["extract"], 700)
    return ""


# ---------------------------------------------------------------------------
# Web firmy - <title>, meta popis, <h1> a kus viditelneho textu
# ---------------------------------------------------------------------------

_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
_META = re.compile(r"<meta\s+[^>]*>", re.I)
_ATTR = re.compile(r'([\w:-]+)\s*=\s*"([^"]*)"|([\w:-]+)\s*=\s*\'([^\']*)\'')
_ODSTRAN = re.compile(r"<(script|style|noscript|svg|template|nav|footer)[^>]*>.*?</\1>",
                      re.I | re.S)


def _meta_popis(htmls):
    for m in _META.finditer(htmls):
        attrs = {}
        for a in _ATTR.finditer(m.group(0)):
            k = (a.group(1) or a.group(3) or "").lower()
            attrs[k] = a.group(2) if a.group(2) is not None else a.group(4)
        klic = (attrs.get("name") or attrs.get("property") or "").lower()
        if klic in ("description", "og:description") and attrs.get("content"):
            return _text(attrs["content"])
    return ""


_SMETI = re.compile(r"\S{32,}")             # base64, minifikovane CSS/JS zbytky
_SYMBOLY = re.compile(r"[{}();:=<>\[\]|\\/_%#@~^*+]")


def _cisty_text(htmls, limit):
    """
    Viditelny text stranky bez zbytku CSS/JS. Stranky casto nechavaji inline
    styly a data: URI primo v tele - bez ocisteni by se do promptu dostalo
    par kilobajtu smeti misto popisu firmy.
    """
    text = _text(_ODSTRAN.sub(" ", htmls))
    text = _SMETI.sub(" ", text)
    vety = []
    for kus in re.split(r"(?<=[.!?·])\s+|\s{2,}", text):
        kus = kus.strip()
        if len(kus) < 3:
            continue
        # segmenty s vysokym podilem zavorek a operatoru jsou kod, ne text
        if len(_SYMBOLY.findall(kus)) * 8 > len(kus):
            continue
        vety.append(kus)
        if sum(len(v) for v in vety) > limit:
            break
    return _text(" ".join(vety), limit)


def web_text(klient, f):
    """
    Stahne titulni stranku a vytahne popisny text. Zamerne jen titulka -
    zarazeni dela LLM, kteremu staci vystizny meta popis; podstranky byly
    potreba jen drivejsimu vyhledavani klicovych slov.

    Domena z Wikidat (P856) se bere jako dana. Domena uhodnuta z nazvu se
    PRIJME AZ PO OVERENI, ze stranka firmu opravdu zminuje - "Phoenix Contact"
    by jinak dostal phoenix.de, coz je nemecka televize, a LLM by podle toho
    zaradil dodavatele svorkovnic mezi media.
    """
    dohadovana = not f.web
    sila = 0
    if dohadovana:
        dom, sila = _dohad_domeny(f)
    else:
        dom = f.web
    if not dom:
        return
    if not dom.startswith("http"):
        dom = "https://" + dom

    klic = "WEB|%s|%s" % (dom, f.ico)
    ulozene = klient.cti(klic)
    if ulozene is not None:
        if ulozene.get("web"):
            f.web, f.web_text = ulozene["web"], ulozene.get("text", "")
        elif ulozene.get("poznamka"):
            f.poznamky.append(ulozene["poznamka"])
        return

    cil, htmls = _stahni_stranku(dom)
    if not htmls:
        klient.zapis(klic, {})
        return

    casti = []
    t = _TITLE.search(htmls)
    if t:
        casti.append(_text(t.group(1)))
    popis = _meta_popis(htmls)
    if popis:
        casti.append(popis)
    h = _H1.search(htmls)
    if h:
        casti.append(_text(h.group(1)))
    telo = _cisty_text(htmls, 500)
    if telo:
        casti.append(telo)
    text = _text(" · ".join(c for c in casti if c), 900)

    if dohadovana and not _stranka_sedi(f, text, htmls, sila):
        poznamka = ("web %s neověřen (nezmiňuje firmu), nepoužit"
                    % urllib.parse.urlsplit(cil).netloc)
        f.poznamky.append(poznamka)
        klient.zapis(klic, {"poznamka": poznamka})
        return

    f.web = cil
    f.web_text = text
    klient.zapis(klic, {"web": cil, "text": text})


def _stahni_stranku(url):
    """
    Vrati (vysledna_url, html). Zkusi zadanou adresu, a kdyz neuspeje a slo
    o hlubsi odkaz (Wikidata umi ukazovat na podstranku), jeste koren domeny.
    Vraci ("", "") kdyz se nic nepovedlo.
    """
    rozklad = urllib.parse.urlsplit(url)
    # Wikidata umi ukazovat na podstranku, ktera uz neexistuje, a nekdy je
    # zapsany http u webu, ktery jede jen na https - zkousi se obojí.
    adresy = [url]
    for schema in ("https", "http"):
        adresy.append("%s://%s/" % (schema, rozklad.netloc))

    for adresa in dict.fromkeys(adresy):
        try:
            req = urllib.request.Request(adresa, headers={
                "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/125.0.0.0 Safari/537.36"),
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "cs,de;q=0.8,en;q=0.6"})
            with urllib.request.urlopen(req, timeout=8) as r:
                cil = r.geturl()
                syrove = r.read(300_000)
        except Exception:
            continue
        if not syrove:
            continue
        m = re.search(rb'charset=["\']?([\w-]+)', syrove[:4000], re.I)
        enc = (m.group(1).decode("ascii", "ignore") if m else "utf-8") or "utf-8"
        try:
            return cil, syrove.decode(enc, "replace")
        except LookupError:
            return cil, syrove.decode("utf-8", "replace")
    return "", ""


def _stranka_sedi(f, text, htmls, sila):
    """
    Patri stranka opravdu teto firme?

    `sila` = kolik tokenu nazvu slo do uhodnute domeny. Domena slozena z celeho
    nazvu (teslablatna.cz) je sama o sobe silny dukaz - staci, kdyz stranka
    firmu zmini. Domena z jednoho slova (phoenix.de) je slaba: takovou adresu
    ma i nekdo uplne jiny, takze se chce potvrzeni z dalsiho slova nazvu.
    """
    if f.ico and f.ico in htmls:
        return True
    tokeny = _tokeny_nazvu(f.vstup_nazev)
    if not tokeny:
        return False
    # Hleda se i v syrovem HTML, ne jen ve viditelnem textu: "AutoESA" ma web
    # nadepsany "Auto ESA" s mezerou, ale v adresach a meta znackach je jednim
    # slovem. Parkovana domena (teslablatna.cz -> parking.vedos.cz) nazev
    # firmy neobsahuje nikde, takze projde odmitnutim tak jako tak.
    nizky = bez_diakritiky(text + " " + htmls).lower()
    zasazene = sum(1 for t in set(tokeny) if t in nizky)
    if sila >= 2 or len(tokeny) == 1:
        return zasazene >= 1
    return zasazene >= 2


# Slova, ktera nenesou identitu firmy - do domeny ani do overovani nepatri.
_VYPLNOVA_SLOVA = {"and", "spol", "the", "und", "group", "holding", "holdings",
                   "company", "international", "czech", "cz", "slovakia", "sk",
                   "deutschland", "europe", "eu", "praha", "brno", "gmbh", "bohemia"}


def _tokeny_nazvu(nazev):
    """Vyznamova slova nazvu - bez pravnich forem a vyplnovych slov."""
    return [t for t in normalizuj_nazev(nazev).split()
            if len(t) >= 3 and t not in _VYPLNOVA_SLOVA]


def _dohad_domeny(f):
    """
    Domena z nazvu. Vraci (domena, sila), kde sila je pocet slov nazvu, ktera
    do domeny sla - podle toho se pak posuzuje, jak moc vysledku verit.
    Spatny odhad podklady neznehodnoti, `_stranka_sedi` ho zahodi.
    """
    tokeny = _tokeny_nazvu(f.vstup_nazev)
    if not tokeny:
        return "", 0
    # cely nazev je specificky (teslablatna.cz); jedno slovo je risk (phoenix.de)
    zaklad = "".join(tokeny[:3]) if len(tokeny) <= 3 else "".join(tokeny[:2])
    sila = min(len(tokeny), 3 if len(tokeny) <= 3 else 2)
    if len(zaklad) < 4:
        return "", 0
    tld = {"CZ": "cz", "SK": "sk", "DE": "de", "AT": "at", "PL": "pl", "NL": "nl",
           "FR": "fr", "IT": "it", "ES": "es", "HU": "hu", "SE": "se", "CH": "ch"}
    return zaklad + "." + tld.get((f.zeme or f.vstup_zeme).upper(), "com"), sila


# ---------------------------------------------------------------------------
# Jeden dodavatel od zacatku do konce
# ---------------------------------------------------------------------------

def dohledej(klient, radek):
    """
    radek = {"nazev","adresa","ico","dic","zeme","objem"} ze vstupu.
    Vraci Firmu se vsim, co se podarilo zjistit. Nikdy nevyhodi vyjimku -
    neuspech se pozna podle pole `identita`.
    """
    f = Firma(
        vstup_nazev=radek.get("nazev", "").strip(),
        vstup_adresa=radek.get("adresa", "").strip(),
        vstup_ico=_ico(radek.get("ico")),
        vstup_dic=(radek.get("dic") or "").strip(),
        vstup_zeme=(radek.get("zeme") or "").strip().upper()[:2],
        vstup_objem=str(radek.get("objem") or "").strip(),
    )
    f.ico, f.dic, f.zeme = f.vstup_ico, f.vstup_dic, f.vstup_zeme
    nazev = f.vstup_nazev
    zeme_dic, _ = rozloz_dic(f.vstup_dic)
    zeme = f.vstup_zeme or (zeme_dic or "")
    mesto = _mesto_z_adresy(f.vstup_adresa)

    try:
        # 1) identita podle identifikatoru
        if f.vstup_ico and zeme in ("", "CZ"):
            ares_detail(klient, f, f.vstup_ico)
        if f.identita == IDENT_NEOVERENO and f.vstup_ico and zeme == "SK":
            rpo(klient, f, nazev, f.vstup_ico)
        if f.identita == IDENT_NEOVERENO and f.vstup_dic:
            vies(klient, f, f.vstup_dic)

        # 2) identita podle nazvu tam, kde na to mame rejstrik
        if f.identita == IDENT_NEOVERENO and nazev:
            if zeme in ("", "CZ"):
                ares_podle_nazvu(klient, f, nazev, mesto)
            elif zeme == "SK":
                rpo(klient, f, nazev)

        # 3) predmet podnikani (jen CZ, jen kdyz uz mame ICO)
        if f.ico and (f.zeme or zeme) in ("", "CZ") and not f.obory:
            ares_predmet_podnikani(klient, f)

        # 4) podklady k cinnosti
        wikidata(klient, f)
        web_text(klient, f)
    except Exception as e:
        f.poznamky.append("chyba dohledání: %s" % e)

    if not f.nazev:
        f.nazev = nazev
    if not f.mesto and mesto:
        f.mesto = mesto
    if not f.ulice and f.vstup_adresa:
        f.ulice = f.vstup_adresa
    f.zeme = f.zeme or zeme
    return f


_PSC_MESTO = re.compile(r"(\d{3}\s?\d{2}|\d{5})\s+([^\d,]{2,40})")


def _mesto_z_adresy(adresa):
    if not adresa:
        return ""
    m = _PSC_MESTO.search(adresa)
    if m:
        return m.group(2).strip(" ,.")
    casti = [c.strip() for c in adresa.split(",") if c.strip()]
    return casti[-1] if len(casti) > 1 else ""

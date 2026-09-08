"""
Obohaceni firmy z verejnych rejstriku a bazi znalosti - bez API klice, bez
behove sluzby, cisty Python (urllib). Bezi i na Windows bez WSL.

Zdroje (vsechny verejne, bez registrace):
  - ARES (ares.gov.cz)           - kanonicky nazev, ICO, DIC, sidlo, CZ-NACE
  - Wikidata (wikidata.org)      - identifikace firmy podle ICO (P4156), z ni
                                   oficialni web (P856), obor (P452), produkt
                                   (P1056), typ (P31), popis
  - Wikipedia (cs, pak en)       - uvodni odstavec clanku (popis cinnosti)
  - web firmy                    - dohledava se az v kategorizuj.py (web.py);
                                   domenu sem dodava tenhle modul

Vysledek se prevede na strukturu {organic, knowledgeGraph}, kterou ceka
klasifikator, a ulozi na disk (gzip JSON). Prvni beh stahuje, kazdy dalsi beh
nad stejnym seznamem jede z kese a je bajt po bajtu shodny (deterministicky).
Rejstrikova data se meni radove pomaleji nez SERP snippety, takze i prvni beh
je dobre reprodukovatelny.

offline rezim (--offline): pouzije jen to, co uz je v kesi.
"""

import gzip
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from .normalizace import bez_diakritiky, klic_nazvu, nazev_tokeny

_KES_VERZE = "z1"

UA = ("kategorizace-dodavatelu/1.0 "
      "(https://github.com/ret3030/dodavatele; obohaceni z verejnych rejstriku)")

ARES_HLEDAT = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/vyhledat"
ARES_DETAIL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/"
RPO_HLEDAT = "https://api.statistics.sk/rpo/v1/search"        # Registr pravnickych osob SR
RPO_DETAIL = "https://api.statistics.sk/rpo/v1/entity/"
WD_API = "https://www.wikidata.org/w/api.php"
WP_API = "https://%s.wikipedia.org/w/api.php"

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_ICO_RE = re.compile(r"\b\d{8}\b")


def _text(s):
    return _WS.sub(" ", html.unescape(_TAG.sub(" ", str(s or "")))).strip()


def _domena_z_url(url):
    try:
        host = urllib.parse.urlsplit(url).netloc.lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def _sk_platny(polozky):
    """RPO SR vede jmeno/adresu/ICO jako historii - vrati aktualne platnou
    (bez validTo), jinak posledni zaznam."""
    if not polozky:
        return {}
    aktualni = [p for p in polozky if isinstance(p, dict) and not p.get("validTo")]
    return (aktualni or [p for p in polozky if isinstance(p, dict)] or [{}])[-1]


class Zdroje:
    def __init__(self, cache_dir=None, prodleva=0.3, timeout=25, pokusy=6,
                 offline=False, povolit_heuristiku=True):
        self.cache_dir = cache_dir
        self.prodleva = prodleva
        self.timeout = timeout
        self.pokusy = pokusy
        self.offline = offline
        self.povolit_heuristiku = povolit_heuristiku
        self.z_kese = 0
        self.stazeno = 0
        self.chyby = 0
        self._posledni_dotaz = 0.0
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)

    # -- kes ----------------------------------------------------------------
    def _cesta(self, klic):
        h = hashlib.sha256((_KES_VERZE + "|" + klic).encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, h + ".json.gz") if self.cache_dir else None

    def _cti(self, klic):
        cesta = self._cesta(klic)
        if not cesta or not os.path.exists(cesta):
            return None
        try:
            with gzip.open(cesta, "rt", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def _zapis(self, klic, hodnota):
        cesta = self._cesta(klic)
        if not cesta:
            return
        try:
            with gzip.open(cesta, "wt", encoding="utf-8") as f:
                json.dump(hodnota, f, ensure_ascii=False)
        except OSError as e:
            print("  ! kes nejde zapsat: %s" % e, file=sys.stderr)

    # -- HTTP -------------------------------------------------------------
    def _skrt(self):
        """Serializace dotazu - aspon `prodleva` sekund mezi kterymikoli dvema
        (ne az po uspechu). Wikidata/Wikipedia API jinak rychle vrati HTTP 429."""
        if self.prodleva:
            spano = time.time() - self._posledni_dotaz
            if spano < self.prodleva:
                time.sleep(self.prodleva - spano)
        self._posledni_dotaz = time.time()

    def _http(self, url, data=None, hlavicky=None):
        h = {"User-Agent": UA, "Accept": "application/json"}
        if hlavicky:
            h.update(hlavicky)
        telo = json.dumps(data).encode("utf-8") if isinstance(data, dict) else data
        if isinstance(data, dict):
            h["Content-Type"] = "application/json"
        posledni = None
        for pokus in range(1, self.pokusy + 1):
            self._skrt()
            try:
                with urllib.request.urlopen(
                    urllib.request.Request(url, data=telo, headers=h),
                    timeout=self.timeout,
                ) as odp:
                    return odp.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as e:
                posledni = "HTTP %s" % e.code
                if e.code == 404:
                    return None
                if e.code in (429, 500, 502, 503):
                    # Retry-After respektujeme (Wikimedia ho posila u 429 i maxlag 503)
                    ra = 0
                    try:
                        ra = int(e.headers.get("Retry-After", "0"))
                    except (TypeError, ValueError):
                        ra = 0
                    time.sleep(max(ra, min(2 ** pokus, 30)))
                    continue
                return None
            except (urllib.error.URLError, TimeoutError, ValueError) as e:
                posledni = str(e)
                time.sleep(min(2 ** pokus, 30))
        print("  ! dotaz selhal (%s): %s" % (posledni, url[:80]), file=sys.stderr)
        return None

    def _json(self, klic, url, data=None):
        """Kesovany JSON dotaz. Vraci dict/list, nebo {} kdyz nic."""
        ulozene = self._cti(klic)
        if ulozene is not None:
            self.z_kese += 1
            return ulozene
        if self.offline:
            self.chyby += 1
            return {}
        syrove = self._http(url, data=data)
        if syrove is None:
            self.chyby += 1
            self._zapis(klic, {})           # i negativni vysledek kesujeme
            return {}
        try:
            hodnota = json.loads(syrove)
        except ValueError:
            hodnota = {}
        self.stazeno += 1
        self._zapis(klic, hodnota)
        return hodnota

    # -- ARES ----------------------------------------------------------
    def ares(self, nazev, ico=""):
        """Vraci {ico, nazev, mesto, dic, nace:[...]}  nebo {}."""
        ico = (ico or "").strip()
        ico = _ICO_RE.search(ico).group(0) if _ICO_RE.search(ico) else ""
        if not ico:
            hled = self._json(
                "ares:hledat:" + klic_nazvu(nazev),
                ARES_HLEDAT, data={"obchodniJmeno": nazev, "pocet": 10},
            )
            kandidati = hled.get("ekonomickeSubjekty") or []
            cil_klic = klic_nazvu(nazev)
            vybrany = None
            for s in kandidati:
                if klic_nazvu(s.get("obchodniJmeno", "")) == cil_klic:
                    vybrany = s
                    break
            if not vybrany and len(kandidati) == 1:
                vybrany = kandidati[0]
            if not vybrany:
                return {}
            ico = str(vybrany.get("ico") or "")

        det = self._json("ares:ico:" + ico, ARES_DETAIL + ico) if ico else {}
        if not det.get("ico"):
            return {}
        adr = (det.get("sidlo") or {}).get("textovaAdresa") or ""
        mesto = ""
        m = re.search(r"\b\d{3}\s?\d{2}\s+([^,]+)$", adr)
        if m:
            mesto = m.group(1).strip()
        nace = [str(k) for k in (det.get("czNace") or []) if str(k).isdigit() and len(str(k)) >= 3]
        return {
            "ico": str(det.get("ico") or ""),
            "nazev": _text(det.get("obchodniJmeno") or ""),
            "mesto": mesto,
            "dic": _text(det.get("dic") or ""),
            "nace": nace,
            "nace_text": [],
        }

    # -- RPO SR (slovensky protejsek ARES) ---------------------------
    def rpo(self, nazev, ico=""):
        """Vraci {ico, nazev, mesto, dic, nace:[...], nace_text:[...]}  nebo {}."""
        ico = _ICO_RE.search((ico or "").strip())
        ico = ico.group(0) if ico else ""

        # Vyhledavaci pole fullName je hodne fuzzy (dotaz "ESET" vrati i "RESET"
        # a stovky dalsich) a citlive na interpunkci (s carkou vraci 0). Posila se
        # tedy holy nazev bez pravnich forem a spravny zaznam se vybira striktne:
        # bud shoda ICO, nebo PRAVE JEDEN kandidat s presne shodnym (norm.) jmenem.
        # Vic nejednoznacnych kandidatu -> radsi nic nez spatna firma se spatnym NACE.
        dotaz = " ".join(nazev_tokeny(nazev)) or nazev
        hled = self._json(
            "rpo:hledat:" + klic_nazvu(nazev),
            RPO_HLEDAT + "?" + urllib.parse.urlencode({"fullName": dotaz, "limit": 40}),
        )
        cil = klic_nazvu(nazev)
        vysledky = hled.get("results") or []

        vybrany = None
        if ico:
            for r in vysledky:
                if str(_sk_platny(r.get("identifiers")).get("value") or "") == ico:
                    vybrany = r
                    break
        if not vybrany:
            shody = [r for r in vysledky
                     if klic_nazvu(_sk_platny(r.get("fullNames")).get("value") or "") == cil]
            if len(shody) == 1:
                vybrany = shody[0]
        if not vybrany:
            return {}

        eid = str(vybrany.get("id") or "")
        adresa = _sk_platny(vybrany.get("addresses"))
        ident = _sk_platny(vybrany.get("identifiers"))
        found_ico = str(ident.get("value") or ico or "")
        mesto = (adresa.get("municipality") or {}).get("value") or ""

        det = self._json("rpo:entita:" + eid, RPO_DETAIL + eid) if eid else {}
        hlavni = (det.get("statisticalCodes") or {}).get("mainActivity") or {}
        nace = [str(hlavni.get("code"))] if str(hlavni.get("code") or "").isdigit() else []
        nace_text = [_text(hlavni.get("value"))] if hlavni.get("value") else []
        return {
            "ico": found_ico,
            "nazev": _text(_sk_platny(vybrany.get("fullNames")).get("value") or nazev),
            "mesto": mesto,
            "dic": "SK%s" % found_ico if found_ico else "",
            "nace": nace,
            "nace_text": nace_text,
        }

    # -- Wikidata ------------------------------------------------------
    def wikidata(self, nazev, ico="", zeme=""):
        """Vraci {qid, web, popis, obor:[...], produkt:[...], typ:[...], wiki:{lang:title}} nebo {}."""
        qid = ""
        ico = _ICO_RE.search(ico or "").group(0) if _ICO_RE.search(ico or "") else ""
        if ico:
            d = self._json(
                "wd:ico:" + ico,
                WD_API + "?" + urllib.parse.urlencode({
                    "action": "query", "list": "search",
                    "srsearch": "haswbstatement:P4156=%s" % ico,
                    "srlimit": 1, "format": "json",
                }),
            )
            hits = (d.get("query") or {}).get("search") or []
            if hits:
                qid = hits[0].get("title", "")

        if not qid:
            d = self._json(
                "wd:hledat:" + klic_nazvu(nazev) + ":" + (zeme or ""),
                WD_API + "?" + urllib.parse.urlencode({
                    "action": "wbsearchentities", "search": nazev,
                    "language": "cs", "uselang": "cs", "type": "item",
                    "limit": 5, "format": "json",
                }),
            )
            cil = klic_nazvu(nazev)
            for s in d.get("search") or []:
                lbl = klic_nazvu(s.get("label", ""))
                # jen pri shode normalizovaneho nazvu - spatna entita by pres
                # P856 dosadila cizi web a tim cizi kategorii
                if lbl and (lbl == cil or lbl == cil + " cz" or cil == lbl + " cz"):
                    qid = s.get("id", "")
                    break

        if not qid or not re.match(r"^Q\d+$", qid):
            return {}

        ent = self._json(
            "wd:entita:" + qid,
            WD_API + "?" + urllib.parse.urlencode({
                "action": "wbgetentities", "ids": qid,
                "props": "claims|descriptions|labels|sitelinks",
                "languages": "cs|en", "sitefilter": "cswiki|enwiki", "format": "json",
            }),
        )
        e = (ent.get("entities") or {}).get(qid) or {}
        if not e:
            return {}
        cl = e.get("claims") or {}

        def _ids(pid):
            out = []
            for c in cl.get(pid, []):
                try:
                    out.append(c["mainsnak"]["datavalue"]["value"]["id"])
                except (KeyError, TypeError):
                    pass
            return out

        def _str(pid):
            out = []
            for c in cl.get(pid, []):
                try:
                    v = c["mainsnak"]["datavalue"]["value"]
                    out.append(v if isinstance(v, str) else v.get("text", ""))
                except (KeyError, TypeError):
                    pass
            return [x for x in out if x]

        obor_ids = _ids("P452") + _ids("P1056") + _ids("P31")
        stitky = self._stitky(obor_ids)
        popis = (e.get("descriptions", {}).get("cs", {}).get("value")
                 or e.get("descriptions", {}).get("en", {}).get("value") or "")
        wiki = {}
        for klic, sl in (e.get("sitelinks") or {}).items():
            if klic == "cswiki":
                wiki["cs"] = sl.get("title", "")
            elif klic == "enwiki":
                wiki["en"] = sl.get("title", "")

        weby = _str("P856")
        return {
            "qid": qid,
            "web": weby[0] if weby else "",
            "vsechny_weby": weby,
            "popis": _text(popis),
            "obor": [stitky.get(i, "") for i in _ids("P452") if stitky.get(i)],
            "produkt": [stitky.get(i, "") for i in _ids("P1056") if stitky.get(i)],
            "typ": [stitky.get(i, "") for i in _ids("P31") if stitky.get(i)],
            "oficialni_nazev": (_str("P1448")[:1] or [""])[0],
            "wiki": wiki,
        }

    def _stitky(self, qids):
        """QID -> cesky (nebo anglicky) stitek, davkove."""
        qids = [q for q in dict.fromkeys(qids) if re.match(r"^Q\d+$", q or "")]
        out = {}
        for i in range(0, len(qids), 40):
            davka = qids[i:i + 40]
            d = self._json(
                "wd:stitky:" + "|".join(davka),
                WD_API + "?" + urllib.parse.urlencode({
                    "action": "wbgetentities", "ids": "|".join(davka),
                    "props": "labels", "languages": "cs|en", "format": "json",
                }),
            )
            for qid, ent in (d.get("entities") or {}).items():
                labs = ent.get("labels") or {}
                out[qid] = (labs.get("cs", {}).get("value")
                            or labs.get("en", {}).get("value") or "")
        return out

    # -- Wikipedia ---------------------------------------------------
    def wikipedia_extract(self, titul, lang="cs"):
        if not titul:
            return ""
        d = self._json(
            "wp:%s:%s" % (lang, titul),
            (WP_API % lang) + "?" + urllib.parse.urlencode({
                "action": "query", "prop": "extracts", "exintro": 1,
                "explaintext": 1, "redirects": 1, "titles": titul, "format": "json",
            }),
        )
        for pg in ((d.get("query") or {}).get("pages") or {}).values():
            if pg.get("extract"):
                return _text(pg["extract"])[:4000]
        return ""

    # -- domena heuristikou --------------------------------------------
    def _stahni_hlavicku(self, url):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.geturl(), r.read(120000).decode("utf-8", "replace")
        except Exception:
            return None, ""

    def domena_heuristikou(self, nazev, mesto="", ico=""):
        """
        Zkusi par pravdepodobnych domen z nazvu a PRIJME jen tu, kde stranka
        prokazatelne patri firme (ICO na strance, nebo mesto + vic tokenu nazvu).
        Konzervativni schvalne - spatna domena = spatna kategorie.
        """
        if not self.povolit_heuristiku or self.offline:
            return ""
        klic = "domena:" + klic_nazvu(nazev) + ":" + (ico or "")
        ulozene = self._cti(klic)
        if ulozene is not None:
            self.z_kese += 1
            return ulozene.get("domena", "") if isinstance(ulozene, dict) else ""

        tokeny = [t for t in nazev_tokeny(nazev) if len(t) >= 3]
        if not tokeny:
            self._zapis(klic, {"domena": ""})
            return ""
        spojene = "".join(tokeny)
        prvni = tokeny[0]
        kandidati = []
        for zaklad in dict.fromkeys([spojene, prvni,
                                     "".join(tokeny[:2]) if len(tokeny) >= 2 else prvni]):
            if len(zaklad) < 3:
                continue
            for tld in (".cz", ".sk", ".com", ".eu"):
                kandidati.append(zaklad + tld)

        mesto_n = bez_diakritiky((mesto or "").lower())
        nalezena = ""
        for dom in kandidati[:10]:
            fin, body = self._stahni_hlavicku("https://" + dom)
            if not body:
                continue
            low = bez_diakritiky(body.lower())
            ma_ico = bool(ico) and ico in body
            zasazene = sum(1 for t in set(tokeny) if t in low)
            ma_mesto = bool(mesto_n) and len(mesto_n) >= 4 and mesto_n in low
            fin_dom = _domena_z_url(fin or ("https://" + dom))
            # prijmi jen kdyz je vazba na firmu silna
            if ma_ico or (zasazene >= 2 and ma_mesto) or (zasazene >= 2 and len(tokeny) >= 2):
                nalezena = fin_dom or dom
                break
        self.stazeno += 1
        self._zapis(klic, {"domena": nalezena})
        if self.prodleva:
            time.sleep(self.prodleva)
        return nalezena

    # -- vysledek pro klasifikator ----------------------------------
    def o_firme(self, nazev, mesto="", zeme="", ico="", web_hint=""):
        """
        Sesbira vsechno verejne a vrati:
          {
            "ico","nazev_ares","mesto","nace":[...],"nace_text":[...],
            "domena","domena_zdroj",
            "odpovedi":[ {knowledgeGraph:{...}}, {organic:[...]} ],
          }
        """
        info = {"ico": ico, "nazev_ares": "", "mesto": mesto, "nace": [],
                "nace_text": [], "domena": "", "domena_zdroj": "", "odpovedi": []}

        zeme_u = (zeme or "").strip().upper()
        if zeme_u == "SK":
            rej = self.rpo(nazev, ico)
        elif zeme_u in ("", "CZ"):
            rej = self.ares(nazev, ico)
        else:
            rej = {}
        if rej:
            info["ico"] = rej["ico"] or info["ico"]
            info["nazev_ares"] = rej["nazev"]
            info["mesto"] = rej["mesto"] or mesto
            info["nace"] = rej["nace"]
            info["nace_text"] = rej.get("nace_text", [])

        wd = self.wikidata(nazev, info["ico"], zeme_u)

        # -- domena: vstup > Wikidata P856 > heuristika ------------------
        dom = _domena_z_url(web_hint) if web_hint else ""
        zdroj = "vstup" if dom else ""
        if not dom and wd.get("web"):
            dom = _domena_z_url(wd["web"])
            zdroj = "wikidata"
        if not dom:
            dom = self.domena_heuristikou(nazev, info["mesto"], info["ico"])
            zdroj = "heuristika" if dom else ""
        info["domena"] = dom
        info["domena_zdroj"] = zdroj

        # -- knowledgeGraph z Wikidata + Wikipedia ---------------------
        kg_casti = []
        if wd:
            kg_casti += [wd.get("popis", "")]
            kg_casti += wd.get("obor", []) + wd.get("produkt", []) + wd.get("typ", [])
            extrakt = self.wikipedia_extract(wd.get("wiki", {}).get("cs", ""), "cs")
            if not extrakt and wd.get("wiki", {}).get("en"):
                extrakt = self.wikipedia_extract(wd["wiki"]["en"], "en")
            if extrakt:
                kg_casti.append(extrakt)
        kg_text = _text(" . ".join(c for c in kg_casti if c))
        if kg_text:
            info["odpovedi"].append({"knowledgeGraph": {
                "title": info["nazev_ares"] or nazev,
                "type": " ".join(wd.get("typ", [])),
                "description": kg_text,
                "attributes": {},
            }})

        # -- organic: oficialni web firmy (aby dostal vahu web:<domena>) --
        if dom:
            info["odpovedi"].append({"organic": [{
                "link": "https://" + dom,
                "title": info["nazev_ares"] or nazev,
                "snippet": wd.get("popis", ""),
            }]})

        return info

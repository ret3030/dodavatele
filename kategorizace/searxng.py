"""
Klient pro vlastni instanci SearXNG (metavyhledavac).

- GET {base}/search?q=...&format=json&language=..&categories=general&pageno=N
- odpoved SearXNG se prevede na strukturu, kterou ceka klasifikator
  (organic / knowledgeGraph / answerBox), a ulozi na disk (gzip JSON).
  Klic kese = hash dotazu vc. jazyka a poctu vysledku -> opakovany beh uz
  nic nestahuje a je deterministicky.
- offline rezim (bez adresy): pouzije jen to, co uz je v kesi.

Nazvy dodavatelu tak zustavaji na vlastni infrastrukture - nic se neposila
do zadne externi vyhledavaci sluzby.

Nastaveni instance: v settings.yml povolit JSON vystup
    search:
      formats: [html, json]
Adresa: env SEARXNG_URL, jinak soubor kategorizace/searxng_url.txt
(napr. http://localhost:8888 nebo http://uzivatel:heslo@vyhledavac.interni:8080).
"""

import base64
import gzip
import hashlib
import html
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "kategorizace-dodavatelu/0.3"
VYCHOZI_URL = "http://localhost:8888"
_KES_VERZE = "sx1"          # odlisi kes SearXNG od drivejsi kese jineho zdroje

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def _text(s):
    return _WS.sub(" ", html.unescape(_TAG.sub(" ", str(s or "")))).strip()


def _normalizuj_odpoved(syrove):
    """SearXNG JSON -> {organic, knowledgeGraph, answerBox}, jak to ceka klasifikator."""
    if not isinstance(syrove, dict):
        return {}

    organic = []
    for r in syrove.get("results") or []:
        if not isinstance(r, dict):
            continue
        odkaz = r.get("url") or ""
        if not odkaz:
            continue
        organic.append({
            "link": odkaz,
            "title": _text(r.get("title", "")),
            "snippet": _text(r.get("content", "")),
        })
    out = {"organic": organic}

    infoboxes = syrove.get("infoboxes") or []
    if infoboxes and isinstance(infoboxes[0], dict):
        ib = infoboxes[0]
        atributy = {}
        for a in ib.get("attributes") or []:
            if isinstance(a, dict) and a.get("label"):
                atributy[str(a["label"])] = str(a.get("value", ""))
        out["knowledgeGraph"] = {
            "title": _text(ib.get("infobox", "")),
            "type": "",
            "description": _text(ib.get("content", "")),
            "attributes": atributy,
        }

    for ans in syrove.get("answers") or []:
        txt = _text(ans.get("answer") or ans.get("content") or "") if isinstance(ans, dict) else _text(ans)
        if txt:
            out["answerBox"] = {"answer": txt}
            break

    return out


class SearXNG:
    def __init__(self, base_url=None, cache_dir=None, prodleva=0.0, timeout=25, pokusy=3):
        self.auth = None
        raw = (base_url or "").strip().rstrip("/")
        if raw:
            rozklad = urllib.parse.urlsplit(raw)
            if rozklad.username:
                token = "%s:%s" % (
                    urllib.parse.unquote(rozklad.username),
                    urllib.parse.unquote(rozklad.password or ""),
                )
                self.auth = base64.b64encode(token.encode("utf-8")).decode("ascii")
                netloc = rozklad.hostname or ""
                if rozklad.port:
                    netloc += ":%d" % rozklad.port
                raw = urllib.parse.urlunsplit((rozklad.scheme, netloc, rozklad.path, "", ""))
        self.base_url = raw or None
        self.cache_dir = cache_dir
        self.prodleva = prodleva
        self.timeout = timeout
        self.pokusy = pokusy
        self.z_kese = 0
        self.stazeno = 0
        self.chyby = 0
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)

    # -- kes ---------------------------------------------------------------
    def _cesta_kese(self, payload):
        klic = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        return os.path.join(self.cache_dir, klic + ".json.gz") if self.cache_dir else None

    def _cti_kes(self, cesta):
        if not cesta or not os.path.exists(cesta):
            return None
        try:
            with gzip.open(cesta, "rt", encoding="utf-8") as f:
                return json.load(f).get("response")
        except (OSError, ValueError):
            return None

    def _zapis_kes(self, cesta, payload, response):
        if not cesta:
            return
        try:
            with gzip.open(cesta, "wt", encoding="utf-8") as f:
                json.dump({"dotaz": payload, "response": response}, f, ensure_ascii=False)
        except OSError as e:
            print("  ! kes nejde zapsat: %s" % e, file=sys.stderr)

    # -- dotaz -----------------------------------------------------------
    def hledej(self, q, gl="cz", hl="cs", num=10):
        payload = {"q": q, "gl": gl, "hl": hl, "num": num, "v": _KES_VERZE}
        cesta = self._cesta_kese(payload)
        z_kese = self._cti_kes(cesta)
        if z_kese is not None:
            self.z_kese += 1
            return z_kese

        if not self.base_url:
            self.chyby += 1
            return {}

        data = self._stahni(q, hl, num)
        if data is None:
            self.chyby += 1
            return {}
        self.stazeno += 1
        self._zapis_kes(cesta, payload, data)
        if self.prodleva:
            time.sleep(self.prodleva)
        return data

    def _stahni(self, q, hl, num):
        jazyk = hl if (hl and 2 <= len(hl) <= 5) else "all"
        stran = max(1, min(5, math.ceil(num / 10)))
        vysledky, infoboxes, answers = [], [], []
        for strana in range(1, stran + 1):
            syrove = self._strana(q, jazyk, strana)
            if syrove is None:
                if strana == 1:
                    return None
                break
            davka = syrove.get("results") or []
            vysledky.extend(davka)
            infoboxes = infoboxes or syrove.get("infoboxes") or []
            answers = answers or syrove.get("answers") or []
            if len(vysledky) >= num or not davka:
                break
            if self.prodleva:
                time.sleep(self.prodleva)
        return _normalizuj_odpoved(
            {"results": vysledky[:num], "infoboxes": infoboxes, "answers": answers}
        )

    def _strana(self, q, jazyk, pageno):
        qs = urllib.parse.urlencode({
            "q": q, "format": "json", "language": jazyk,
            "categories": "general", "pageno": pageno, "safesearch": 0,
        })
        url = "%s/search?%s" % (self.base_url, qs)
        posledni = None
        for pokus in range(1, self.pokusy + 1):
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept": "application/json"},
            )
            if self.auth:
                req.add_header("Authorization", "Basic " + self.auth)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as odp:
                    return json.loads(odp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                posledni = "HTTP %s" % e.code
                if e.code in (403, 404):
                    posledni += " - v SearXNG settings.yml povolte 'search: formats: [html, json]'"
                    break
                if e.code in (429, 500, 502, 503):
                    time.sleep(min(2 ** pokus, 10))
                    continue
                break
            except (urllib.error.URLError, TimeoutError, ValueError) as e:
                posledni = str(e)
                time.sleep(min(2 ** pokus, 10))
        print("  ! SearXNG dotaz selhal (%s): %s" % (posledni, q), file=sys.stderr)
        return None


def nacti_url(cesta_souboru=None):
    """Adresa SearXNG z env SEARXNG_URL, jinak z kategorizace/searxng_url.txt."""
    url = os.environ.get("SEARXNG_URL", "").strip()
    if url:
        return url.rstrip("/")
    cesta = cesta_souboru or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "searxng_url.txt")
    if os.path.exists(cesta):
        with open(cesta, encoding="utf-8") as f:
            return f.read().strip().rstrip("/")
    return ""

"""
Klient pro Google Search API od serper.dev.

- POST https://google.serper.dev/search, hlavicka X-API-KEY
- surova odpoved se uklada na disk (gzip JSON), klicem je hash dotazu vcetne
  parametru gl/hl/num - opakovany beh nad stejnym seznamem uz nic nestahuje
  a je deterministicky (Google jinak vysledky prehazuje)
- offline rezim (bez klice): pouzije jen to, co uz je v kesi
"""

import gzip
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request

URL = "https://google.serper.dev/search"
UA = "kategorizace-dodavatelu/0.1"


class Serper:
    def __init__(self, api_key=None, cache_dir=None, prodleva=0.5, timeout=25, pokusy=3):
        self.api_key = (api_key or "").strip() or None
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

    # -- dotaz ----------------------------------------------------------------
    def hledej(self, q, gl="cz", hl="cs", num=10):
        payload = {"q": q, "gl": gl, "hl": hl, "num": num}
        cesta = self._cesta_kese(payload)
        z_kese = self._cti_kes(cesta)
        if z_kese is not None:
            self.z_kese += 1
            return z_kese

        if not self.api_key:
            self.chyby += 1
            return {}

        data = self._stahni(payload)
        if data is None:
            self.chyby += 1
            return {}
        self.stazeno += 1
        self._zapis_kes(cesta, payload, data)
        if self.prodleva:
            time.sleep(self.prodleva)
        return data

    def _stahni(self, payload):
        telo = json.dumps(payload).encode("utf-8")
        posledni = None
        for pokus in range(1, self.pokusy + 1):
            req = urllib.request.Request(
                URL, data=telo, method="POST",
                headers={
                    "X-API-KEY": self.api_key,
                    "Content-Type": "application/json",
                    "User-Agent": UA,
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as odp:
                    return json.loads(odp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                posledni = "HTTP %s" % e.code
                if e.code in (429, 500, 502, 503):
                    time.sleep(min(2 ** pokus, 10))
                    continue
                break
            except (urllib.error.URLError, TimeoutError, ValueError) as e:
                posledni = str(e)
                time.sleep(min(2 ** pokus, 10))
        print("  ! SERPER dotaz selhal (%s): %s" % (posledni, payload["q"]), file=sys.stderr)
        return None


def nacti_klic(cesta_souboru=None):
    """Klic z env SERPER_API_KEY, jinak z kategorizace/serper_key.txt."""
    klic = os.environ.get("SERPER_API_KEY", "").strip()
    if klic:
        return klic
    cesta = cesta_souboru or os.path.join(os.path.dirname(os.path.abspath(__file__)), "serper_key.txt")
    if os.path.exists(cesta):
        with open(cesta, encoding="utf-8") as f:
            return f.read().strip()
    return ""

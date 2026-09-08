"""
Stazeni webu firmy a vytazeni popisneho textu.

- domovska stranka: <title>, meta description / og:description, keywords, <h1>
  (silny, cisty signal) + viditelny text stranky (sirsi, sumavejsi signal)
- az 2 vnitrni stranky typu "o nas" / "produkty" / "sluzby" - tam je popis
  cinnosti casto konkretnejsi nez na titulce
Vsechno stazene se kesuje (gzip) podle URL.
"""

import gzip
import hashlib
import html
import os
import re
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (compatible; kategorizace-dodavatelu/0.2)"

_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
_META = re.compile(r"<meta\s+[^>]*>", re.I)
_ATTR = re.compile(r'(\w[\w:-]*)\s*=\s*"([^"]*)"|(\w[\w:-]*)\s*=\s*\'([^\']*)\'')
_A = re.compile(r'<a\s+[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
_ODSTRAN_BLOK = re.compile(
    r"<(script|style|noscript|svg|template)[^>]*>.*?</\1>", re.I | re.S)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")

# Vnitrni stranky, ktere maji smysl stahnout (priorita: popis firmy > sortiment).
_STRANKY = [
    (1, ("o-nas", "o nas", "o-spolecnosti", "o spolecnosti", "o-firme", "o firme",
         "kdo-jsme", "kdo jsme", "profil", "about", "about-us", "company", "unternehmen")),
    (2, ("co-delame", "co delame", "cinnost", "predmet-cinnosti", "zamereni",
         "what-we-do", "produkty", "products", "produkte", "sluzby", "services",
         "leistungen", "sortiment", "nabidka", "reseni", "solutions", "vyroba",
         "technologie", "program")),
]
_PRESKOCIT_PRIPONY = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".zip", ".doc",
                      ".docx", ".xls", ".xlsx", ".mp4", ".svg", ".webp")


def _text(kus):
    return _WS.sub(" ", html.unescape(_TAG.sub(" ", kus or ""))).strip()


def _viditelny_text(htmls, limit=3000):
    bez = _ODSTRAN_BLOK.sub(" ", htmls)
    return _text(bez)[:limit]


def _meta_mapa(htmls):
    out = {}
    for m in _META.finditer(htmls):
        attrs = {}
        for a in _ATTR.finditer(m.group(0)):
            k = (a.group(1) or a.group(3) or "").lower()
            v = a.group(2) if a.group(2) is not None else a.group(4)
            attrs[k] = v or ""
        klic = (attrs.get("name") or attrs.get("property") or "").lower()
        if klic in ("description", "og:description", "keywords", "twitter:description"):
            out.setdefault(klic, _text(attrs.get("content", "")))
    return out


def _vnitrni_odkazy(htmls, zaklad_url, kolik=2):
    host = urllib.parse.urlsplit(zaklad_url).netloc.lower().lstrip("www.")
    kandidati = []
    videno = set()
    for i, (href, kotva) in enumerate(_A.findall(htmls)):
        href = href.strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        plna = urllib.parse.urljoin(zaklad_url, href)
        rozklad = urllib.parse.urlsplit(plna)
        if rozklad.scheme not in ("http", "https"):
            continue
        h = rozklad.netloc.lower().lstrip("www.")
        if h != host and not h.endswith("." + host) and not host.endswith("." + h):
            continue
        if rozklad.path.lower().endswith(_PRESKOCIT_PRIPONY):
            continue
        cil = plna.split("#")[0]
        if cil in videno or cil.rstrip("/") == zaklad_url.rstrip("/"):
            continue
        vzorek = (rozklad.path + " " + _text(kotva)).lower().replace("_", "-")
        for prio, klice in _STRANKY:
            if any(k in vzorek for k in klice):
                videno.add(cil)
                kandidati.append((prio, i, cil))
                break
    kandidati.sort()
    return [c for _, _, c in kandidati[:kolik]]


class Web:
    def __init__(self, cache_dir=None, timeout=10, povolit=True, podstranky=2):
        self.cache_dir = cache_dir
        self.timeout = timeout
        self.povolit = povolit
        self.podstranky = podstranky
        self.z_kese = 0
        self.stazeno = 0
        self.chyby = 0
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)

    # -- kes ----------------------------------------------------------------
    def _cesta(self, klic):
        h = hashlib.sha256(klic.encode("utf-8")).hexdigest()[:32]
        return os.path.join(self.cache_dir, "web_" + h + ".html.gz") if self.cache_dir else None

    def _cti(self, klic):
        cesta = self._cesta(klic)
        if not cesta or not os.path.exists(cesta):
            return None
        try:
            with gzip.open(cesta, "rt", encoding="utf-8", errors="replace") as f:
                return f.read()
        except OSError:
            return None

    def _zapis(self, klic, obsah):
        cesta = self._cesta(klic)
        if not cesta:
            return
        try:
            with gzip.open(cesta, "wt", encoding="utf-8", errors="replace") as f:
                f.write(obsah)
        except OSError:
            pass

    # -- stahovani --------------------------------------------------------
    def _http(self, url):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=self.timeout) as odp:
                syrove = odp.read(500_000)
            m = re.search(rb'charset=["\']?([\w-]+)', syrove[:4000], re.I)
            enc = (m.group(1).decode("ascii", "ignore") if m else "utf-8") or "utf-8"
            return syrove.decode(enc, "replace")
        except (urllib.error.URLError, TimeoutError, ValueError, OSError):
            return None

    def _ziskej(self, klic, url_varianty):
        """Vrati HTML z kese, nebo stahne prvni fungujici z url_varianty."""
        hotovo = self._cti(klic)
        if hotovo is not None:
            self.z_kese += 1
            return hotovo or None
        if not self.povolit:
            return None
        for url in url_varianty:
            htmls = self._http(url)
            if htmls:
                self.stazeno += 1
                self._zapis(klic, htmls)
                return htmls
        self.chyby += 1
        self._zapis(klic, "")  # negativni vysledek taky kesujeme
        return None

    # -- verejne ---------------------------------------------------------
    def popis(self, domena):
        """
        Vrati (meta_text, telo_text):
          meta_text = title + meta description + og + keywords + h1 (cisty signal)
          telo_text = viditelny text titulky + az `podstranky` vnitrnich stranek
        Kdyz web neodpovi, vraci ("", "").
        """
        if not domena:
            return "", ""
        titulka = self._ziskej(domena, ["https://" + domena, "http://" + domena])
        if not titulka:
            return "", ""

        meta_casti = []
        t = _TITLE.search(titulka)
        if t:
            meta_casti.append(_text(t.group(1)))
        mm = _meta_mapa(titulka)
        for k in ("description", "og:description", "twitter:description", "keywords"):
            if mm.get(k):
                meta_casti.append(mm[k])
        h = _H1.search(titulka)
        if h:
            meta_casti.append(_text(h.group(1)))

        telo_casti = [_viditelny_text(titulka)]
        if self.podstranky:
            zaklad = "https://" + domena
            for url in _vnitrni_odkazy(titulka, zaklad, self.podstranky):
                pod = self._ziskej(url, [url])
                if pod:
                    telo_casti.append(_viditelny_text(pod, 2500))

        return (" ".join(c for c in meta_casti if c)[:2000],
                " ".join(c for c in telo_casti if c)[:6000])

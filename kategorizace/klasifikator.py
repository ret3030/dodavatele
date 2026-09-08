"""
Deterministicky klasifikator: ze SERP odpovedi (organic vysledky, knowledge
graph, answer box) posbira text, obodova ho podle pravidel a vrati kategorii
s rozhodnutim AUTO / OVERIT / LLM.

Skore kategorie = suma  vaha_fraze * vaha_zdroje * min(pocet_vyskytu, 2)
pres vsechny pos fraze; neg fraze odecitaji. Rozhodnuti se ridi absolutnim
skore top kategorie, jejim odstupem od druhe a poctem ruznych zdroju, ktere
pro ni svedcily.
"""

from urllib.parse import urlsplit

from .normalizace import normalizuj_text, nazev_tokeny
from .pravidla import PRAVIDLA_NORM
from .taxonomie import KATEGORIE, VYCHOZI_KOD

# -- prahy rozhodovani (ladi se proti gold seznamu ve vyhodnoceni.py) --------
# Nastaveno na "AUTO jen kdyz jsme si dost jisti": ~38 % pokryti pri ~95 %
# presnosti listu. Volnejsi prahy pokryti zvednou, presnost uz ne - kolem
# 95 % je strop dany vicoborovymi firmami a spornym zarazenim samotnym.
PRAH_AUTO_SKORE = 12.0      # min. absolutni skore top kategorie pro AUTO
PRAH_AUTO_ODSTUP = 0.50     # (top1 - top2) / top1  >=  tohle pro AUTO
PRAH_AUTO_ZDROJE = 3        # min. pocet ruznych zdroju svedcicich pro top1
PRAH_OVERIT_SKORE = 6.0     # pod tohle -> LLM (nezarazeno)

# Katalogy firem, rejstriky a socialni site - text z nich je casto o firme,
# ale domena nepatri firme; nizka vaha a nepovazujeme za "vlastni web".
KATALOGY = {
    "firmy.cz", "zivefirmy.cz", "kurzy.cz", "rejstrik-firem.kurzy.cz",
    "justice.cz", "or.justice.cz", "ares.gov.cz", "ico.cz", "edb.cz",
    "najisto.cz", "abc.cz", "detail.cz", "merk.cz", "cribis.cz", "hlidacstatu.cz",
    "monitor.statnipokladna.cz", "rejstriky.info", "profesia.cz", "jobs.cz",
    "linkedin.com", "facebook.com", "instagram.com", "youtube.com", "twitter.com",
    "x.com", "wikipedia.org", "wikidata.org", "orsr.sk", "finstat.sk", "rbb.sk",
    "kompass.com", "europages.cz", "europages.co.uk", "yellowpages.com",
    "zoominfo.com", "dnb.com", "bloomberg.com", "crunchbase.com",
}


def _domena(url):
    try:
        host = urlsplit(url).netloc.lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def _hlavni_domena(host):
    casti = host.split(".")
    return ".".join(casti[-2:]) if len(casti) >= 2 else host


def signaly(odpovedi, nazev):
    """
    Ze seznamu SERP odpovedi (dict) vytahne signaly: (jmeno_zdroje, text, vaha).

    Vic dotazu na tutéž firmu se slucuje. Organic vysledky se deduplikuji podle
    odkazu, ale texty se SLUCUJI - Google vraci pro stejnou URL ruzny snippet
    podle dotazu (dotaz '"nazev" mesto' vrati adresu, dotaz 'nazev (výrobce OR
    …)' vrati popis cinnosti), a chceme oboji.
    """
    tokeny = set(nazev_tokeny(nazev))
    out = []
    ma_kg = False
    per_link = {}       # odkaz -> {"poz": nejnizsi pozice, "texty": [snippet, ...]}
    poradi = []

    for odp in odpovedi:
        if not isinstance(odp, dict):
            continue

        kg = odp.get("knowledgeGraph") or {}
        if kg and not ma_kg:
            ma_kg = True
            casti = [kg.get("title", ""), kg.get("type", ""), kg.get("description", "")]
            atributy = kg.get("attributes") or {}
            if isinstance(atributy, dict):
                casti += ["%s %s" % (k, v) for k, v in atributy.items()]
            out.append(("knowledgeGraph", " ".join(str(c) for c in casti), 3.0))

        ab = odp.get("answerBox") or {}
        if ab:
            casti = [ab.get("title", ""), ab.get("answer", ""), ab.get("snippet", "")]
            txt = " ".join(str(c) for c in casti if c)
            if txt.strip():
                out.append(("answerBox", txt, 2.5))

        for i, org in enumerate(odp.get("organic") or []):
            odkaz = org.get("link", "") or ("bez-odkazu:%d" % i)
            cast = "%s %s" % (org.get("title", ""), org.get("snippet", ""))
            sitelinks = org.get("sitelinks") or []
            if sitelinks:
                cast += " " + " ".join(
                    "%s %s" % (s.get("title", ""), s.get("snippet", "")) for s in sitelinks
                )
            if odkaz not in per_link:
                per_link[odkaz] = {"poz": i, "texty": []}
                poradi.append(odkaz)
            per_link[odkaz]["poz"] = min(per_link[odkaz]["poz"], i)
            if cast.strip() and cast not in per_link[odkaz]["texty"]:
                per_link[odkaz]["texty"].append(cast)

    for odkaz in poradi:
        rec = per_link[odkaz]
        host = _domena(odkaz)
        hd = _hlavni_domena(host)
        text = " ".join(rec["texty"])
        je_katalog = hd in KATALOGY or host in KATALOGY
        domena_sedi = any(t in host.replace("-", "") for t in tokeny if len(t) >= 4)

        if je_katalog:
            jmeno, vaha = "katalog:%s" % hd, 0.8
        elif domena_sedi:
            jmeno, vaha = "web:%s" % hd, 3.5
        elif rec["poz"] < 3:
            jmeno, vaha = "organic:%s" % hd, 2.0
        else:
            jmeno, vaha = "organic:%s" % hd, 1.0
        out.append((jmeno, text, vaha))

    return out


def vlastni_domena(odpovedi, nazev):
    """Nejlepsi odhad domeny, kterou vlastni sama firma (na dohledani meta popisu)."""
    tokeny = [t for t in nazev_tokeny(nazev) if len(t) >= 4]
    if not tokeny:
        return ""
    for odp in odpovedi:
        if not isinstance(odp, dict):
            continue
        for org in odp.get("organic") or []:
            host = _domena(org.get("link", ""))
            hd = _hlavni_domena(host)
            if hd in KATALOGY or host in KATALOGY:
                continue
            if any(t in host.replace("-", "") for t in tokeny):
                return hd
    return ""


def _pocet(text_pad, fraze):
    return text_pad.count(" " + fraze + " ")


def skoruj(seznam_signalu, nace_nazvy=()):
    """
    Vrati (skore, duraz):
      skore: {kod_kategorie: float}
      duraz: {kod_kategorie: [(fraze, jmeno_zdroje, prispevek), ...]}
    """
    prace = list(seznam_signalu)
    if nace_nazvy:
        prace.append(("nace", " ".join(nace_nazvy), 1.2))
    normy = [(jmeno, normalizuj_text(text), vaha) for jmeno, text, vaha in prace]

    skore, duraz = {}, {}
    for kod, pravidlo in PRAVIDLA_NORM.items():
        s = 0.0
        hits = []
        # Kazda fraze se za jeden zdroj zapocita jen jednou (bez ohledu na pocet
        # vyskytu) - jinak keyword-stuffed meta popis firmy neumerne prebije
        # ostatni signaly. Rozhoduje sirka shody (kolik ruznych frazi/zdroju),
        # ne kolikrat je jedno slovo na strance.
        for frazes, w in pravidlo["pos"]:
            for fraze in frazes:
                for jmeno, textp, vz in normy:
                    if _pocet(textp, fraze):
                        prispevek = w * vz
                        s += prispevek
                        hits.append((fraze, jmeno, round(prispevek, 2)))
        for frazes, w in pravidlo["neg"]:
            for fraze in frazes:
                for jmeno, textp, vz in normy:
                    if _pocet(textp, fraze):
                        s -= w * vz
        skore[kod] = round(max(s, 0.0), 2)
        duraz[kod] = hits
    return skore, duraz


def rozhodni(skore, duraz):
    poradi = sorted(skore.items(), key=lambda kv: kv[1], reverse=True)
    k1, s1 = poradi[0]
    k2, s2 = poradi[1] if len(poradi) > 1 else ("", 0.0)
    odstup = (s1 - s2) / s1 if s1 > 0 else 0.0
    zdroje = {jmeno for _, jmeno, _ in duraz.get(k1, [])}
    n_zdroju = len(zdroje)

    # skore po skupinach
    skup = {}
    for kod, sc in skore.items():
        skup[KATEGORIE[kod][0]] = skup.get(KATEGORIE[kod][0], 0.0) + sc
    skup_poradi = sorted(skup.items(), key=lambda kv: kv[1], reverse=True)

    if s1 >= PRAH_AUTO_SKORE and odstup >= PRAH_AUTO_ODSTUP and n_zdroju >= PRAH_AUTO_ZDROJE:
        rozh, kod = "AUTO", k1
    elif s1 >= PRAH_OVERIT_SKORE and n_zdroju >= 1:
        rozh, kod = "OVERIT", k1
    else:
        rozh, kod = "LLM", VYCHOZI_KOD

    return {
        "rozhodnuti": rozh,
        "kod": kod,
        "kategorie": KATEGORIE[kod][1],
        "skupina": KATEGORIE[kod][0],
        "skore": s1,
        "odstup": round(odstup, 2),
        "zdroju": n_zdroju,
        "kod_top1": k1,
        "skupina_top1": KATEGORIE[k1][0],
        "alternativy": [(k, sc) for k, sc in poradi[:3] if sc > 0],
        "skupina_skore": skup_poradi[:3],
        "duraz_top1": duraz.get(k1, []),
    }


def klasifikuj(odpovedi, nazev, nace_nazvy=(), pridane=None):
    sig = signaly(odpovedi, nazev)
    if pridane:
        sig = list(sig) + [s for s in pridane if s and s[1]]
    skore, duraz = skoruj(sig, nace_nazvy)
    vysledek = rozhodni(skore, duraz)
    vysledek["signalu"] = len(sig)
    return vysledek

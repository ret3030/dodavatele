"""
Vystupy nastroje: davky pro LLM chat, nacteni jeho odpovedi a Excel se vzorci.

Excel je zamerne "zivy" - kategorie, skupina a ICT relevance nejsou zapsane
hodnoty, ale VLOOKUP do listu Ciselnik. Kdyz nekdo opravi kod kategorie,
prepocita se nazev, skupina, ICT priznak, kriticnost i rezim dle ISO 27001.

Sesit je zaroven pracovni nastroj pro klienta, ne jen export: kazdy list zacina
kartou (nadpis + k cemu list je a jak se pouziva) a prvni list je kosilka.
Proto data na listech nezacinaji na radku 1 - viz _karta().
"""

import csv
import json
import os
import re

from taxonomie import KATEGORIE, VYCHOZI_KOD, ict_relevance

# Znacka pro fyzickou osobu, ke ktere se nenaslo nic o oboru. Neprideluje
# ji model, ale nastroj - podle pravni formy z rejstriku. Do ciselniku
# v promptu proto nepatri, model by ji jinak zacal hadat sam.
KOD_OSVC = "XXX-01"

DAVKA = 250            # firem na jeden soubor pro chat
_KOD_RE = re.compile(r"\b[A-Z]{2,4}-\d{2}\b")

# Hodnoty rucne vyplnovanych sloupcu. Musi presne sedet na vzorce nize.
#
# Pristup je zebricek, ne vycet: kazdy stupen v sobe obsahuje nizsi, takze se
# vybira nejvyssi, ktery plati. Diky tomu se stupne neprekryvaji a nikdo nemusi
# resit, do ktere skatulky dodavatel patri - jen kam az dohledne.
#
# Poradi je proto soucast logiky, ne kosmetika. _vzorec_kriticnost bere
# PRISTUP[2:] jako "dostane se k nasim informacim" a PRISTUP[-1] jako
# privilegovany pristup; prehazenim radku by se rozesel vypocet.
PRISTUP = [
    "Žádný přístup",                # nevidí naše informace ani do prostor
    "Fyzický vstup do prostor",     # úklid, servis, ostraha, stěhování
    "Má naše data u sebe",          # dostane exporty, nebo je zpracovává u sebe
    "Přístup do našich systémů",    # účet v našich aplikacích, API, cloud
    "Privilegovaná správa systémů",  # administrátor, vzdálená správa
]
# Nahraditelnost je taky stupnice, ale jineho druhu nez Pristup: nejsou to
# pricky, ktere se scitaji, ale tri navzajem se vylucujici stavy. Vybira se
# ten, ktery sedi - ne "nejvyssi, ktery plati", to by kazdeho tlacilo nahoru.
#
# Poradi presto nese logiku: _vzorec_kriticnost bere NAHRADITELNOST[-1] jako
# kritickou zavislost a [-2] jako obtiznou nahraditelnost, takze prehozeni
# radku by prohodilo i vysledek.
NAHRADITELNOST = [
    "Běžně nahraditelný",           # na trhu je víc alternativ, přechod v týdnech
    "Obtížně nahraditelný",         # náhrada existuje, ale znamená migraci a měsíce
    "Kritická závislost",           # prakticky nenahraditelný, výpadek zastaví provoz
]

SLOUPCE = [
    ("Kreditor", 12),
    ("Název ze vstupu", 34), ("Ověřený název", 34), ("Jistota identity", 15),
    ("IČO", 11), ("DIČ", 14), ("Země", 6), ("Město", 18), ("Web", 26),
    ("NACE", 14),
    ("Kód kategorie", 13), ("Kategorie", 34), ("Skupina", 30), ("ICT relevance", 13),
    ("Co dodává (LLM)", 44), ("Jistota zařazení", 14),
    ("Přístup k datům/systémům", 26), ("Nahraditelnost", 22),
    ("Kritičnost", 16), ("Režim dle ISO 27001", 52),
    # revizni blok - vyplnuje klient u kritickych a vyznamnych dodavatelu
    ("Vlastník vztahu", 22), ("Datum posouzení", 16),
    ("Datum příštího přezkoumání", 22), ("Poznámka", 44),
]
# indexy (1-based) klicovych sloupcu - at se vzorce nerozbiji pri zmene poradi
S_KREDITOR, S_IDENTITA, S_POPIS = 1, 4, 15
S_KOD, S_KATEG, S_SKUP, S_ICT = 11, 12, 13, 14
S_PRISTUP, S_NAHRAD = 17, 18
S_KRIT, S_ISO = 19, 20
S_VLASTNIK, S_POSOUZENI, S_PREZKOUM, S_POZNAMKA = 21, 22, 23, 24
RUCNI = (S_PRISTUP, S_NAHRAD, S_VLASTNIK, S_POSOUZENI, S_PREZKOUM, S_POZNAMKA)

# Popis kazdeho sloupce listu Dodavatele a jeho vazba na ISO/IEC 27001, pro
# list Metodika. Poradi a delka musi sedet na SLOUPCE - kdyz nekdo prida
# sloupec a zapomene na tohle, zapis_excel to shodi hned pri generovani.
METODIKA = [
    ("Kreditor", "Identifikátor dodavatele z účetnictví (číslo kreditora). "
     "Když ho vstup neobsahoval, je tu pořadové číslo řádku – to je zároveň "
     "ID, pod kterým firma vystupuje v dávkách pro chat a na listu Podklady.",
     "A.5.19 – evidence dodavatelů musí být jednoznačně adresovatelná"),
    ("Název ze vstupu", "Název dodavatele přesně tak, jak přišel ze vstupního "
     "souboru (z účetnictví).", ""),
    ("Ověřený název", "Úřední název z rejstříku (ARES / RPO SR) nebo VIES, "
     "pokud se liší od vstupu.", "A.5.19 – dodavatele je třeba jednoznačně "
     "identifikovat"),
    ("Jistota identity", "Jak spolehlivě je identita ověřená: rejstřík (podle "
     "IČO nebo přesné shody jména) > VIES (DIČ) > podle názvu > neověřeno.",
     "A.5.19"),
    ("IČO", "Identifikátor dohledaný v ARES / RPO SR.", ""),
    ("DIČ", "Identifikátor použitý k ověření přes VIES u zahraničních "
     "dodavatelů v EU.", ""),
    ("Země", "Sídlo dodavatele.", ""),
    ("Město", "Sídlo dodavatele.", ""),
    ("Web", "Ověřený web dodavatele – ne jen odhad z názvu.", ""),
    ("NACE", "Úředně zapsaný obor podnikání. Jen vodítko pro kategorizaci, "
     "ne finální zařazení – bývá zastaralý nebo obecný.", ""),
    ("Kód kategorie", "Kód z Číselníku, který LLM přiřadil podle toho, čím "
     "se dodavatel reálně zabývá. Kód XXX-01 nedal model, ale nástroj: jde "
     "o fyzickou osobu (OSVČ), která není v obchodním rejstříku, takže "
     "k oboru nebyl žádný podklad – zařaďte ji ručně podle toho, co pro vás "
     "opravdu dělá.", "A.5.19 – podklad pro posouzení druhu dodávky"),
    ("Kategorie", "Název kategorie – VLOOKUP do listu Číselník podle kódu.", ""),
    ("Skupina", "Nadřazená skupina kategorie – VLOOKUP do listu Číselník.", ""),
    ("ICT relevance", "ano / podmíněná / ne – jestli dodavatel typicky "
     "zpracovává informace firmy nebo se připojuje do jejích systémů. "
     "VLOOKUP do Číselníku. „Podmíněná“ není něco mezi: znamená, že o "
     "přístupu nerozhoduje obor, ale konkrétní smlouva – advokát na jednu "
     "žalobu a advokát s celou personální agendou mají stejnou kategorii. "
     "U těchto řádků neproklikávejte Přístup automaticky, rozhoduje jen "
     "vaše odpověď.", "A.5.21 – řízení bezpečnosti v ICT dodavatelském "
     "řetězci"),
    ("Co dodává (LLM)", "Stručný popis od LLM, aby šlo zkontrolovat, že kód "
     "kategorie sedí.", ""),
    ("Jistota zařazení", "vysoká / střední / nízká – jak jistý si LLM byl "
     "při zařazení do kategorie.", ""),
    ("Přístup k datům/systémům", "RUČNĚ. Žebříček, ne výčet – vyberte "
     "NEJVYŠŠÍ stupeň, který platí; vyšší v sobě obsahuje nižší, takže se "
     "nemusíte rozhodovat mezi překrývajícími se možnostmi. "
     "1) Žádný přístup = nevidí naše informace a nechodí do prostor. "
     "2) Fyzický vstup do prostor = úklid, servis, ostraha, stěhování. "
     "3) Má naše data u sebe = dostane od nás exporty, dokumenty nebo osobní "
     "údaje, nebo je pro nás zpracovává ve svém prostředí (účetní, advokát, "
     "mzdová kancelář, cloud či SaaS, kde data leží u něj). "
     "4) Přístup do našich systémů = má účet v našich aplikacích nebo se do "
     "nich připojuje přes API či vzdálený přístup. "
     "5) Privilegovaná správa systémů = administrátorská práva nebo vzdálená "
     "správa – spravuje nám je, ne v nich jen pracuje. "
     "Dodavatel, který chodí do prostor a zároveň nám spravuje servery, patří "
     "na stupeň 5; fyzický vstup je u něj to menší z obojího. Rozhoduje "
     "skutečný stav, ne to, co je ve smlouvě.",
     "A.5.19, A.5.20; A.5.14 (přenos informací); A.5.23 (cloudové služby); "
     "A.7.2 (fyzický vstup); A.8.2 (privilegovaná přístupová práva)"),
    ("Nahraditelnost", "RUČNĚ. Běžně nahraditelný = na trhu je víc alternativ, "
     "přechod je otázka týdnů. Obtížně nahraditelný = náhrada existuje, ale "
     "znamená migraci dat, integrace nebo měsíce práce. Kritická závislost = "
     "prakticky nenahraditelný, jeho výpadek zastaví provoz.",
     "A.5.21; A.5.29/A.5.30 (kontinuita provozu)"),
    ("Kritičnost", "KRITICKÝ / VÝZNAMNÝ / BĚŽNÝ – vzorec z ICT relevance, "
     "Přístupu a Nahraditelnosti. Rozhoduje přístup a závislost, ne cena ani "
     "objem fakturace.", "shrnutí A.5.19–A.5.22"),
    ("Režim dle ISO 27001", "Doporučená opatření podle Kritičnosti a ICT "
     "relevance – prověření, bezpečnostní požadavky ve smlouvě, DPA, právo "
     "auditu, monitoring.", "A.5.19–A.5.22"),
    ("Vlastník vztahu", "RUČNĚ: jméno člověka u nás, který za vztah "
     "s dodavatelem odpovídá. U kritického dodavatele nesmí zůstat prázdné – "
     "bez konkrétní osoby se opatření nikdy nevymáhají.",
     "A.5.19; A.5.2 (role a odpovědnosti v bezpečnosti informací)"),
    ("Datum posouzení", "RUČNĚ: kdy bylo naposledy posouzeno riziko tohohle "
     "dodavatele a ověřeno, že sloupce vlevo platí.", "A.5.19, A.5.22 – "
     "monitorování a přezkoumání dodavatelských služeb"),
    ("Datum příštího přezkoumání", "RUČNĚ: kdy se má posouzení zopakovat. "
     "Doporučení: kritický dodavatel po roce, významný po dvou letech, "
     "běžný při změně vztahu. Prošlé datum list zvýrazní červeně.",
     "A.5.22 – přezkoumání v plánovaných intervalech"),
    ("Poznámka", "RUČNĚ: cokoli k tomuhle dodavateli – co bylo prověřeno, "
     "kde je smlouva a DPA, otevřené body, dohodnutá opatření.", "A.5.20"),
]
assert len(METODIKA) == len(SLOUPCE), "METODIKA musí popisovat každý sloupec SLOUPCE"


def _pismeno(i):
    """1 -> A, 27 -> AA"""
    s = ""
    while i:
        i, z = divmod(i - 1, 26)
        s = chr(65 + z) + s
    return s


# XLSX v bunce nedovoluje ridici znaky. Lezou sem z rozbitych webu, z rejstriku
# i ze vstupniho CSV a openpyxl na nich spadne az pri wb.save(), tedy po celem
# behu - proto se sem sahne u kazde hodnoty, ne jen u tech z internetu.
_RIDICI = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f"
                     "\ud800-\udfff\ufdd0-\ufdef\ufffe\uffff]")
LIMIT_BUNKY = 32000   # tvrdy strop Excelu je 32767 znaku


def _bunka(h):
    if not isinstance(h, str):
        return h
    h = _RIDICI.sub(" ", h)
    return h[:LIMIT_BUNKY - 1] + "…" if len(h) > LIMIT_BUNKY else h


def _radek(ws, hodnoty):
    """append() s ocistenim - jediny vstup dat do sesitu. Vraci cislo radku."""
    ws.append([_bunka(h) for h in hodnoty])
    return ws.max_row


# ---------------------------------------------------------------------------
# Davky pro LLM chat
# ---------------------------------------------------------------------------

def _ciselnik_radky():
    radky, predchozi = [], None
    for kod, skupina, nazev in sorted(
            (k, v[0], v[1]) for k, v in KATEGORIE.items()
            if k not in (VYCHOZI_KOD, KOD_OSVC)):
        if skupina != predchozi:
            radky.append("  [%s]" % skupina)
            predchozi = skupina
        radky.append("    %s = %s" % (kod, nazev))
    return radky


ZADANI = """\
Jsi asistent pro audit dodavatelů podle ISO/IEC 27001 (příloha A, řízení
dodavatelských vztahů). Ke každé firmě níže urči:

  1. KÓD KATEGORIE z číselníku - podle toho, ČÍM SE FIRMA REÁLNĚ ZABÝVÁ,
     ne podle formálního zápisu v rejstříku. Zapsané obory jsou často
     zastaralé nebo obecné ("výroba, obchod a služby") - ber je jen jako
     vodítko. Když firmu znáš, použij i vlastní znalosti.
  2. CO DODÁVÁ - stručně vlastními slovy (pár slov až věta), ať jde
     zkontrolovat, že kód sedí.
  3. JISTOTU - vysoká / střední / nízká. Napiš "nízká" všude, kde odhaduješ
     z názvu nebo si nejsi jistý/á. Raději přiznaná nejistota než tichý omyl -
     na tenhle výstup navazuje audit.

Když o firmě nic nevíš, napiš kód XXX-00 a jistotu "nízká".

U každé firmy je v odrážkách kontext, který se podařilo dohledat ve veřejných
rejstřících a na webu. Pozor na řádek "identita" - hodnota "neověřeno" znamená,
že firmu nemáme potvrzenou z rejstříku a i název může být nepřesný.
"""

FORMAT = """\
Odpověz POUZE v CSV, jeden řádek na firmu, oddělovač ';', v tomto pořadí.
Bez hlavičky, bez uvozovek, bez textu okolo:

ID;Název firmy;Kód kategorie;Co dodává;Jistota

ID i název opiš přesně tak, jak jsou v seznamu - podle nich se odpověď páruje
zpět a nesoulad se pozná. Zpracuj všech %d firem. Když nestihneš všechny,
radši méně řádků, ale úplných - nikdy nevynechávej ID uprostřed.
"""


def _blok_firmy(cislo, f):
    hlava = "%d | %s" % (cislo, f.nazev or f.vstup_nazev)
    misto = ", ".join(x for x in (f.mesto, f.zeme) if x)
    if misto:
        hlava += " (%s)" % misto
    radky = [hlava, "   identita: %s" % f.identita]
    for stitek, text in f.podklady(strucne=True):
        radky.append("   %s: %s" % (stitek, text))
    return "\n".join(radky)


def zapis_davky(firmy, adresar):
    """Rozdeli firmy do souboru po DAVKA kusech. Vraci seznam cest."""
    os.makedirs(adresar, exist_ok=True)
    for star in os.listdir(adresar):
        if re.match(r"^davka_\d+\.txt$", star):
            os.remove(os.path.join(adresar, star))

    from zdroje import bez_zarazeni

    ciselnik = "\n".join(_ciselnik_radky())
    davky = [firmy[i:i + DAVKA] for i in range(0, len(firmy), DAVKA)] or [[]]
    cesty = []
    for i, davka in enumerate(davky, 1):
        cislo_od = (i - 1) * DAVKA + 1
        # Fyzicka osoba bez jedineho podkladu se modelu neposila. Dostal by
        # hole jmeno cloveka a vratil dohad, ktery by v sesitu vypadal jako
        # zjisteny obor. Cislovani se tim neposune - to jde z indexu.
        bloky = [_blok_firmy(cislo_od + j, f) for j, f in enumerate(davka)
                 if not bez_zarazeni(f)]
        if not bloky:
            continue
        obsah = "\n".join([
            ZADANI,
            "ČÍSELNÍK KATEGORIÍ:",
            ciselnik,
            "",
            "FIRMY (%d, dávka %d z %d):" % (len(bloky), i, len(davky)),
            "",
            "\n\n".join(bloky),
            "",
            FORMAT % len(bloky),
        ])
        cesta = os.path.join(adresar, "davka_%02d.txt" % i)
        with open(cesta, "w", encoding="utf-8") as fh:
            fh.write(obsah)
        cesty.append(cesta)
    return cesty


# ---------------------------------------------------------------------------
# Nacteni odpovedi z chatu
# ---------------------------------------------------------------------------

def nacti_odpovedi(adresar, firmy=None):
    """
    Precte vsechny CSV/TXT v adresari a vrati (odpovedi, nesoulady), kde
    odpovedi = {id: {"kod","popis","jistota"}}.

    Radky bez rozpoznatelneho ID nebo kodu se preskoci - chat casto pripise
    uvodni vetu nebo hlavicku. Kdyz je zadany `firmy`, kontroluje se navic
    nazev: kdyby chat posunul cislovani, dostala by firma cizi kategorii
    a v auditu by se to poznalo hodne pozde. Takove radky se zahodi a vrati
    v `nesoulady`.
    """
    out, nesoulady = {}, []
    if not os.path.isdir(adresar):
        return out, nesoulady
    for jmeno in sorted(os.listdir(adresar)):
        if not jmeno.lower().endswith((".csv", ".txt")):
            continue
        with open(os.path.join(adresar, jmeno), encoding="utf-8-sig", newline="") as fh:
            vzorek = fh.read(4096)
            fh.seek(0)
            odd = ";" if vzorek.count(";") >= vzorek.count(",") else ","
            for radek in csv.reader(fh, delimiter=odd):
                if len(radek) < 2:
                    continue
                ident = re.match(r"^\s*(\d+)\s*$", (radek[0] or "").strip())
                if not ident:
                    continue
                # kod kategorie muze byt ve 2. nebo 3. sloupci podle toho,
                # jestli chat vratil i nazev firmy
                kod, i_kod = None, None
                for i in (1, 2):
                    if i < len(radek):
                        m = _KOD_RE.search((radek[i] or "").upper())
                        if m:
                            kod, i_kod = m.group(0), i
                            break
                if not kod:
                    continue

                cislo = int(ident.group(1))
                nazev_z_odpovedi = radek[1].strip() if i_kod == 2 else ""
                if firmy and nazev_z_odpovedi and not _nazev_sedi(
                        firmy, cislo, nazev_z_odpovedi):
                    ocekavany = (firmy[cislo - 1].nazev or firmy[cislo - 1].vstup_nazev
                                 if 1 <= cislo <= len(firmy) else "?")
                    nesoulady.append((cislo, nazev_z_odpovedi, ocekavany))
                    continue

                out[cislo] = {
                    "kod": kod,
                    "popis": (radek[i_kod + 1].strip() if len(radek) > i_kod + 1 else ""),
                    "jistota": (radek[i_kod + 2].strip().lower()
                                if len(radek) > i_kod + 2 else ""),
                }
    return out, nesoulady


def _nazev_sedi(firmy, cislo, nazev):
    """Odpovida nazev z odpovedi firme na tomhle poradovem cisle?"""
    if not 1 <= cislo <= len(firmy):
        return False
    f = firmy[cislo - 1]
    from zdroje import skore_shody
    return max(skore_shody(nazev, f.vstup_nazev),
               skore_shody(nazev, f.nazev or f.vstup_nazev)) >= 0.75


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------

BARVA_TMAVA = "1F3864"      # zahlavi tabulek
BARVA_KARTA = "DDEBF7"      # karta nad tabulkou
BARVA_BANNER = "EEF3FA"     # hlavicka listu Uvod
BARVA_LINKA = "8EA9DB"      # delici linka pod nadpisy
BARVA_RUCNI = "FFF2CC"      # bunky, ktere vyplnuje clovek
BARVA_RUCNI_HLAVA = "BF8F00"
BARVA_VYSTRAHA = "FFC7CE"   # chybejici udaj u kritickeho dodavatele
BARVA_KRIT = "C00000"

VYCHOZI_SIRKA = 8.43        # sirka sloupce, kteremu ji nikdo nenastavil


def _sirka(ws, i):
    pis = _pismeno(i)
    if pis in ws.column_dimensions:
        return ws.column_dimensions[pis].width or VYCHOZI_SIRKA
    return VYCHOZI_SIRKA


def _karta(ws, nadpis, radky):
    """
    Vysvetlivka nad tabulkou: nadpis + par radku o tom, co list je a jak se
    pouziva. Vraci cislo radku, na ktery ma prijit zahlavi tabulky.

    Kvuli karte data na listech nezacinaji na radku 1 - vsechny vzorce a
    rozsahy proto pocitaji s navratovou hodnotou, nikde nejsou natvrdo.

    Text se slouci pres tolik sloupcu, aby se nejdelsi radek vesel - ve
    sloucene bunce se text nepretece do sousedni, takze by se jinak orizl.
    Sirky sloupcu proto musi byt nastavene uz pred volanim.
    """
    from openpyxl.styles import Alignment, Font, PatternFill

    vypln = PatternFill("solid", fgColor=BARVA_KARTA)
    potreba = max(len(t) for t in [nadpis] + list(radky)) + 2
    sloupcu, sirka = 0, 0.0
    while sirka < potreba and sloupcu < 40:
        sloupcu += 1
        sirka += _sirka(ws, sloupcu)
    posledni_sl = _pismeno(sloupcu)

    def _pruh(r, text, font, vyska):
        ws.cell(r, 1, text).font = font
        ws.cell(r, 1).alignment = Alignment(vertical="center")
        for c in range(1, sloupcu + 1):
            ws.cell(r, c).fill = vypln
        ws.merge_cells("A%d:%s%d" % (r, posledni_sl, r))
        ws.row_dimensions[r].height = vyska

    _pruh(1, nadpis, Font(bold=True, size=13, color=BARVA_TMAVA), 24)
    r = 1
    for text in radky:
        r += 1
        _pruh(r, text, Font(size=10, color=BARVA_TMAVA), 15)
    _pruh(r + 1, "", Font(size=10), 6)
    return r + 3          # jeden prazdny radek mezi kartou a zahlavim


def _souhrn_ict(rozsah="ICT"):
    """
    Radky Souhrnu za ICT relevanci. Urovne se berou z ciselniku, ne z ruky -
    prejmenovana hodnota by jinak zustala v COUNTIF a Souhrn by ukazoval nuly.
    """
    urovne = sorted({ict_relevance(k) for k in KATEGORIE} - {""},
                    key=lambda u: ("ano", "podmíněná", "ne").index(u)
                    if u in ("ano", "podmíněná", "ne") else 9)
    return [(u, '=COUNTIF(%s,"%s")' % (rozsah, u)) for u in urovne]


def _vzorec_kriticnost(r):
    """
    Kriticnost dodavatele. Rozhoduji dve veci: jaky ma dodavatel pristup
    (ISO 27001 A.5.19-A.5.22) a jak snadno jde nahradit. Objem fakturace ani
    typ smlouvy do vypoctu nevstupuji - levny dodavatel se vzdalenou spravou
    serveru je rizikovejsi nez drahy dodavatel kancelarskych potreb.

    Nejvyssi pricka zebricku (privilegovana sprava) je kriticka vzdycky. Nizsi
    pricky, na kterych uz se dodavatel dostane k nasim informacim - ma nase data
    u sebe, chodi do nasich systemu - zvedaji na VYZNAMNY a na KRITICKY az
    u ICT dodavky. Zadny pristup a pouhy fyzicky vstup kriticnost nezvedaji.
    """
    kod, ict = "$%s%d" % (_pismeno(S_KOD), r), "$%s%d" % (_pismeno(S_ICT), r)
    pri, nah = "$%s%d" % (_pismeno(S_PRISTUP), r), "$%s%d" % (_pismeno(S_NAHRAD), r)
    # volby, u kterych se dodavatel dostane k nasim informacim nebo systemum
    k_informacim = ",".join('%s="%s"' % (pri, v) for v in PRISTUP[2:])
    return (
        '=IF({kod}="","nezařazeno",'
        'IF({pri}="","⟵ doplňte přístup",'
        'IF(OR({pri}="{sprava}",'
        '{nah}="{zavislost}",'
        'AND({ict}="ano",OR({info}))),"KRITICKÝ",'
        'IF(OR({ict}="ano",{info},{nah}="{obtizne}"),'
        '"VÝZNAMNÝ","BĚŽNÝ"))))'
    ).format(kod=kod, ict=ict, pri=pri, nah=nah, info=k_informacim,
             sprava=PRISTUP[-1], zavislost=NAHRADITELNOST[-1],
             obtizne=NAHRADITELNOST[-2])


def _vzorec_iso(r):
    krit, ict = "$%s%d" % (_pismeno(S_KRIT), r), "$%s%d" % (_pismeno(S_ICT), r)
    return (
        '=IF({krit}="KRITICKÝ",IF({ict}="ano",'
        '"Prověření dodavatele, bezpečnostní požadavky ve smlouvě vč. DPA, '
        'právo auditu, průběžný monitoring",'
        '"Prověření dodavatele, smluvní záruky, průběžný monitoring"),'
        'IF({krit}="VÝZNAMNÝ","Zjednodušené prověření, bezpečnostní doložka ve smlouvě",'
        'IF({krit}="BĚŽNÝ","Vedení v evidenci, bez dalších požadavků","")))'
    ).format(krit=krit, ict=ict)


def _vlookup(r, sloupec):
    # nazev listu v apostrofech - s diakritikou to nekterym tabulkovym
    # procesorum bez uvozeni vadi
    return "=IFERROR(VLOOKUP($%s%d,'Číselník'!$A:$D,%d,FALSE),\"\")" % (
        _pismeno(S_KOD), r, sloupec)


def _list_uvod(wb, firmy):
    """Kosilka: co sesit je, jak se s nim pracuje a co znamenaji barvy."""
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    ws = wb.active
    ws.title = "Úvod"
    ws.sheet_view.showGridLines = False
    # sirka musi pobrat nejdelsi radek textu: ten se slucuje pres A:B a ve
    # sloucene bunce se nepretece do sousedni ani nezvedne vysku radku,
    # takze prilis uzky list by delsi vety tise orizl (test_vzorce to hlida)
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 112
    stav = [0]

    def _pis(a="", b="", tucne=False, vypln=None, vyska=None, odsazeni=0):
        stav[0] += 1
        r = stav[0]
        bunka_a = ws.cell(r, 1, a)
        bunka_a.font = Font(bold=tucne, size=11,
                            color=BARVA_TMAVA if tucne else "000000")
        bunka_a.alignment = Alignment(vertical="center", wrap_text=True,
                                      indent=odsazeni)
        if vypln:
            bunka_a.fill = PatternFill("solid", fgColor=vypln)
        if b:
            bunka_b = ws.cell(r, 2, b)
            bunka_b.alignment = Alignment(vertical="center", wrap_text=True)
        elif a:
            ws.merge_cells("A%d:B%d" % (r, r))
        if vyska:
            ws.row_dimensions[r].height = vyska
        return r

    def _banner(nadpis, podnadpis, shrnuti):
        """Hlavicka listu: nadpis v lehkem odstinu, pod nim tenka linka."""
        vypln = PatternFill("solid", fgColor=BARVA_BANNER)
        prvni = _pis(vyska=6)                   # horni vzduch uvnitr banneru
        r = _pis(nadpis, vyska=30)
        ws.cell(r, 1).font = Font(bold=True, size=18, color=BARVA_TMAVA)
        r = _pis(podnadpis, vyska=18)
        ws.cell(r, 1).font = Font(size=11, color=BARVA_TMAVA)
        r = _pis(shrnuti, vyska=18)
        ws.cell(r, 1).font = Font(size=11, color=BARVA_TMAVA)
        posledni = _pis(vyska=6)                # dolni vzduch
        for radek in range(prvni, posledni + 1):
            for sl in (1, 2):
                ws.cell(radek, sl).fill = vypln
        # linka misto silneho pruhu - banner tak drzi pohromade, ale nekrici
        r = _pis(vyska=4)
        for sl in (1, 2):
            ws.cell(r, sl).border = Border(
                top=Side(style="medium", color=BARVA_LINKA))

    def _nadpis(text):
        _pis(vyska=10)
        r = _pis(text, tucne=True, vyska=20)
        ws.cell(r, 1).font = Font(bold=True, size=12, color=BARVA_TMAVA)
        for sl in (1, 2):
            ws.cell(r, sl).border = Border(
                bottom=Side(style="thin", color=BARVA_LINKA))
        _pis(vyska=4)

    _banner("Evidence dodavatelů",
            "Audit dodavatelských vztahů dle ISO/IEC 27001 (příloha A, "
            "A.5.19–A.5.22)",
            "Dodavatelů v sešitu: %d" % len(firmy))

    _nadpis("K čemu sešit je")
    for text in (
        "Seznam kreditorů z účetnictví převedený na evidenci dodavatelů: kdo "
        "dodavatel doopravdy je, čím se zabývá,",
        "jestli má vazbu na ICT a jak je pro vaši firmu kritický. Identitu "
        "dohledal nástroj ve veřejných rejstřících,",
        "zařazení do kategorie navrhl jazykový model. Vztah k vaší firmě "
        "posoudíte vy – nástroj ho odjinud zjistit neumí.",
        "",
        "Sešit je živý dokument, ne export. Sloupce se vzorci se přepočítají, "
        "jakmile změníte vstup, ze kterého počítají.",
    ):
        _pis(text)

    _nadpis("Jak s ním pracovat")
    for text in (
        "1.  Projděte list Dodavatelé a zkontrolujte zařazení – hlavně řádky, "
        "kde je Jistota identity „neověřeno“ nebo Jistota zařazení „nízká“.",
        "2.  Kde kategorie nesedí, přepište Kód kategorie podle listu Číselník. "
        "Kategorie, Skupina i ICT relevance se dopočítají samy.",
        "3.  U každého dodavatele vyplňte dva žluté sloupce: Přístup "
        "k datům/systémům a Nahraditelnost. Z nich vyjde Kritičnost.",
        "     Přístup je žebříček od „Žádný“ po „Privilegovaná správa“ – "
        "vyberte nejvyšší stupeň, který platí, ne ten nejlépe sedící.",
        "4.  U dodavatelů, kteří vyjdou jako KRITICKÝ (a podle uvážení "
        "i VÝZNAMNÝ), doplňte revizní blok na konci řádku:",
        "     Vlastník vztahu, Datum posouzení, Datum příštího přezkoumání "
        "a Poznámku. Chybějící údaje se zvýrazní červeně.",
        "5.  Sledujte list Souhrn – ukazuje, kolik toho zbývá vyplnit a kolik "
        "dodavatelů čeká na přezkoumání.",
        "",
        "Význam jednotlivých voleb je popsaný na listu Metodika, včetně toho, "
        "ke kterému řízení ISO/IEC 27001 se sloupec váže.",
    ):
        _pis(text)

    _nadpis("Co je na kterém listu")
    for nazev, popis in LISTY:
        r = _pis(nazev, popis, odsazeni=1)
        ws.cell(r, 1).font = Font(bold=True, size=11, color=BARVA_TMAVA)

    _nadpis("Barvy a značky")
    for barva, popis, vysvetleni in (
        (BARVA_TMAVA, "tmavě modré záhlaví", "sloupec vyplní nástroj nebo vzorec – "
         "přepisovat ho nemá smysl, přepíše se zpátky"),
        (BARVA_RUCNI_HLAVA, "žluté záhlaví a buňky", "sem patří vaše rozhodnutí; "
         "buňky s rozbalovacím seznamem berou jen hodnoty z nabídky"),
        (BARVA_VYSTRAHA, "červené podbarvení", "u kritického dodavatele chybí "
         "vlastník nebo datum posouzení, nebo je přezkoumání po termínu"),
    ):
        r = _pis(popis, vysvetleni, vypln=barva, odsazeni=1)
        ws.cell(r, 1).font = Font(bold=True, size=11,
                                  color="FFFFFF" if barva == BARVA_TMAVA else "000000")
    return ws


LISTY = [
    ("Dodavatelé", "hlavní tabulka – jeden řádek na dodavatele; tady se pracuje"),
    ("Číselník", "kategorie ve skupinách + ICT příznak; zdroj pro vzorce "
     "a rozbalovací seznamy"),
    ("Souhrn", "kolik dodavatelů je ICT, kolik kritických, co ještě chybí vyplnit"),
    ("Podklady", "co se o firmě našlo ve veřejných zdrojích a jak dohledávání "
     "dopadlo – pro zpětnou kontrolu zařazení"),
    ("Metodika", "co znamená který sloupec a na které řízení ISO/IEC 27001 se váže"),
]


def zapis_excel(firmy, odpovedi, cesta):
    try:
        from openpyxl import Workbook
        from openpyxl.formatting.rule import FormulaRule
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
        from openpyxl.worksheet.datavalidation import DataValidation
    except ImportError:
        raise SystemExit(
            "Zápis XLSX vyžaduje openpyxl:  pip install openpyxl")

    wb = Workbook()
    _list_uvod(wb, firmy)

    # -- list Dodavatelé --------------------------------------------------
    ws = wb.create_sheet("Dodavatelé")
    for i, (_, sirka) in enumerate(SLOUPCE, 1):
        ws.column_dimensions[get_column_letter(i)].width = sirka
    zahlavi = _karta(ws, "Dodavatelé – hlavní tabulka", [
        "Jeden řádek na dodavatele. Bílé sloupce dohledal nástroj, žluté "
        "vyplňujete vy, Kritičnost a Režim dle ISO 27001 se počítají vzorcem.",
        "Vyplňte Přístup k datům/systémům a Nahraditelnost – bez nich se "
        "kritičnost nespočítá. Přístup je žebříček: vyberte nejvyšší stupeň, "
        "který platí. U kritických dodavatelů pak revizní blok na konci řádku.",
        "Kategorii opravíte přepsáním Kódu kategorie (nabídka je na listu "
        "Číselník); název, skupina i ICT relevance se dopočítají.",
    ])
    prvni = zahlavi + 1

    for i, (nazev, _) in enumerate(SLOUPCE, 1):
        ws.cell(zahlavi, i, nazev)

    from zdroje import bez_zarazeni

    for cislo, f in enumerate(firmy, 1):
        odp = odpovedi.get(cislo) or {}
        r = zahlavi + cislo
        kod = KOD_OSVC if bez_zarazeni(f) else odp.get("kod", "")
        _radek(ws, [
            f.vstup_kod or cislo,
            f.vstup_nazev,
            f.nazev if f.nazev != f.vstup_nazev else "",
            f.identita,
            f.ico, f.dic, f.zeme, f.mesto, f.web,
            ", ".join(f.nace[:6]),
            kod,
            _vlookup(r, 2), _vlookup(r, 3), _vlookup(r, 4),
            odp.get("popis", ""), odp.get("jistota", ""),
            "", "",
            _vzorec_kriticnost(r), _vzorec_iso(r),
            "", "", "", "",
        ])

    posledni = zahlavi + len(firmy)

    # zahlavi
    vypln = PatternFill("solid", fgColor=BARVA_TMAVA)
    for b in ws[zahlavi]:
        b.font = Font(bold=True, color="FFFFFF")
        b.fill = vypln
        b.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[zahlavi].height = 30
    ws.freeze_panes = "C%d" % prvni
    if posledni >= prvni:
        ws.auto_filter.ref = "A%d:%s%d" % (zahlavi, _pismeno(len(SLOUPCE)), posledni)

    # rucne vyplnovane sloupce - jine pozadi, at je videt, co ceka na cloveka
    rucni = PatternFill("solid", fgColor=BARVA_RUCNI)
    for sl in RUCNI:
        ws.cell(zahlavi, sl).fill = PatternFill("solid", fgColor=BARVA_RUCNI_HLAVA)
        for r in range(prvni, posledni + 1):
            ws.cell(r, sl).fill = rucni

    # rozbalovaci seznamy
    for sl, hodnoty in ((S_PRISTUP, PRISTUP), (S_NAHRAD, NAHRADITELNOST)):
        dv = DataValidation(type="list", formula1='"%s"' % ",".join(hodnoty),
                            allow_blank=True, showDropDown=False)
        ws.add_data_validation(dv)
        dv.add("%s%d:%s%d" % (_pismeno(sl), prvni, _pismeno(sl),
                              max(posledni, prvni)))

    for r in range(prvni, posledni + 1):
        ws.cell(r, S_KRIT).font = Font(bold=True)
        for sl in (S_KATEG, S_POPIS, S_ISO, S_POZNAMKA):
            ws.cell(r, sl).alignment = Alignment(wrap_text=True, vertical="top")
        for sl in (S_POSOUZENI, S_PREZKOUM):
            ws.cell(r, sl).number_format = "DD.MM.YYYY"

    # zvyrazneni - co u kritickeho dodavatele chybi a co je po termínu
    if posledni >= prvni:
        cerveny = PatternFill("solid", fgColor=BARVA_VYSTRAHA)
        krit = "$%s%d" % (_pismeno(S_KRIT), prvni)
        for sl in (S_VLASTNIK, S_POSOUZENI):
            pis = _pismeno(sl)
            ws.conditional_formatting.add(
                "%s%d:%s%d" % (pis, prvni, pis, posledni),
                FormulaRule(formula=['AND(%s="KRITICKÝ",%s%d="")'
                                     % (krit, pis, prvni)], fill=cerveny))
        pis = _pismeno(S_PREZKOUM)
        ws.conditional_formatting.add(
            "%s%d:%s%d" % (pis, prvni, pis, posledni),
            FormulaRule(formula=['AND(%s%d<>"",%s%d<TODAY())'
                                 % (pis, prvni, pis, prvni)], fill=cerveny))
        pis = _pismeno(S_KRIT)
        ws.conditional_formatting.add(
            "%s%d:%s%d" % (pis, prvni, pis, posledni),
            FormulaRule(formula=['%s%d="KRITICKÝ"' % (pis, prvni)],
                        font=Font(bold=True, color=BARVA_KRIT)))

    # -- list Číselník (zdroj pro VLOOKUP i rozbalovací seznamy) -----------
    ws_c = wb.create_sheet("Číselník")
    for i, sirka in enumerate((14, 44, 34, 14), 1):
        ws_c.column_dimensions[get_column_letter(i)].width = sirka
    zahlavi_c = _karta(ws_c, "Číselník kategorií", [
        "Zdroj pro sloupce Kategorie, Skupina a ICT relevance na listu "
        "Dodavatelé – dosazují se sem podle Kódu kategorie.",
        "Když chcete dodavatele přeřadit, najděte tu správný kód a přepište "
        "ho v listu Dodavatelé. Tady nic přepisovat nemusíte.",
        "ICT relevance říká, jestli kategorie typicky znamená přístup "
        "k informacím firmy nebo do jejích systémů (A.5.21). „Podmíněná“ = "
        "rozhoduje smlouva, ne obor.",
    ])
    ws_c.cell(zahlavi_c, 1, "Kód")
    ws_c.cell(zahlavi_c, 2, "Kategorie")
    ws_c.cell(zahlavi_c, 3, "Skupina")
    ws_c.cell(zahlavi_c, 4, "ICT relevance")
    for kod, (skupina, nazev) in sorted(KATEGORIE.items()):
        _radek(ws_c, [kod, nazev, skupina, ict_relevance(kod)])
    for b in ws_c[zahlavi_c]:
        b.font = Font(bold=True, color="FFFFFF")
        b.fill = vypln
    ws_c.freeze_panes = "A%d" % (zahlavi_c + 1)

    # -- list Souhrn ------------------------------------------------------
    ws_s = wb.create_sheet("Souhrn")
    ws_s.column_dimensions["A"].width = 38
    ws_s.column_dimensions["B"].width = 14
    zahlavi_s = _karta(ws_s, "Souhrn", [
        "Kontrolní pohled na celou evidenci. Čísla jsou vzorce – po každé "
        "změně na listu Dodavatelé se přepočítají sama.",
        "Blok „Co zbývá vyplnit“ ukazuje, jak daleko jste s posouzením; "
        "dokud nejsou nuly, evidence není hotová.",
    ])

    def _rozsah(sloupec):
        pis = _pismeno(sloupec)
        return "'Dodavatelé'!$%s$%d:$%s$%d" % (pis, prvni, pis, max(posledni, prvni))

    kr, ic, kod = _rozsah(S_KRIT), _rozsah(S_ICT), _rozsah(S_KOD)
    ident = _rozsah(S_IDENTITA)
    vlastnik, posouzeni = _rozsah(S_VLASTNIK), _rozsah(S_POSOUZENI)
    prezkoum = _rozsah(S_PREZKOUM)

    radky_souhrnu = [
        ("Přehled", ""),
        ("Dodavatelů celkem", len(firmy)),
        ("Zařazeno LLM", '=COUNTIF({k},"<>")-COUNTIF({k},"XXX-00")'
         '-COUNTIF({k},"{osvc}")'.format(k=kod, osvc=KOD_OSVC)),
        ("Nezařazeno (XXX-00)", '=COUNTIF(%s,"XXX-00")' % kod),
        ("OSVČ – obor nezjištěn (%s)" % KOD_OSVC,
         '=COUNTIF(%s,"%s")' % (kod, KOD_OSVC)),
        (None, None),
        ("Identita", ""),
        ("rejstřík", '=COUNTIF(%s,"rejstřík")' % ident),
        ("VIES (DIČ)", '=COUNTIF(%s,"VIES (DIČ)")' % ident),
        ("podle názvu", '=COUNTIF(%s,"podle názvu")' % ident),
        ("neověřeno", '=COUNTIF(%s,"neověřeno")' % ident),
        (None, None),
        ("ICT relevance", ""),
    ] + _souhrn_ict(ic) + [
        (None, None),
        ("Kritičnost", ""),
        ("KRITICKÝ", '=COUNTIF(%s,"KRITICKÝ")' % kr),
        ("VÝZNAMNÝ", '=COUNTIF(%s,"VÝZNAMNÝ")' % kr),
        ("BĚŽNÝ", '=COUNTIF(%s,"BĚŽNÝ")' % kr),
        ("Kritických s ICT vazbou", '=COUNTIFS(%s,"KRITICKÝ",%s,"ano")' % (kr, ic)),
        (None, None),
        ("Co zbývá vyplnit", ""),
        ("bez přístupu (kritičnost nespočtena)", '=COUNTIF(%s,"⟵*")' % kr),
        ("kritických bez vlastníka vztahu",
         '=COUNTIFS(%s,"KRITICKÝ",%s,"")' % (kr, vlastnik)),
        ("kritických bez data posouzení",
         '=COUNTIFS(%s,"KRITICKÝ",%s,"")' % (kr, posouzeni)),
        ("přezkoumání po termínu",
         '=COUNTIFS(%s,"<"&TODAY(),%s,"<>")' % (prezkoum, prezkoum)),
    ]
    for popisek, hodnota in radky_souhrnu:
        if popisek is None:
            _radek(ws_s, [])
            continue
        r = _radek(ws_s, [popisek, hodnota])
        if hodnota == "":
            ws_s.cell(r, 1).font = Font(bold=True, size=12, color=BARVA_TMAVA)
    ws_s.sheet_view.showGridLines = False

    # -- list Podklady (proc to LLM zaradilo takhle) ----------------------
    ws_p = wb.create_sheet("Podklady")
    for i, sirka in enumerate((12, 34, 14, 104, 34), 1):
        ws_p.column_dimensions[get_column_letter(i)].width = sirka
    zahlavi_p = _karta(ws_p, "Podklady k zařazení", [
        "Co se o firmě našlo ve veřejných zdrojích – zapsané obory, NACE, "
        "Wikidata, Wikipedie a text z webu.",
        "Slouží ke kontrole: když u dodavatele pochybujete o kategorii, "
        "najděte si ho tu podle Kreditora a přečtěte, z čeho se vycházelo.",
        "Poslední sloupec je záznam o průběhu dohledávání (např. web "
        "nenalezen) – vypovídá o procesu, ne o dodavateli.",
        "Firma bez řádků tady neměla dohledatelné podklady – zařazení stojí "
        "jen na názvu a znalostech modelu.",
    ])
    ws_p.cell(zahlavi_p, 1, "Kreditor")
    ws_p.cell(zahlavi_p, 2, "Název")
    ws_p.cell(zahlavi_p, 3, "Zdroj")
    ws_p.cell(zahlavi_p, 4, "Text")
    ws_p.cell(zahlavi_p, 5, "Poznámky nástroje")
    for cislo, f in enumerate(firmy, 1):
        kreditor, jmeno = f.vstup_kod or cislo, f.nazev or f.vstup_nazev
        # poznamky patri k firme, ne k jednotlivemu zdroji - proto jen na
        # prvni radek. Firma, o ktere se nic nenaslo, zadny radek nema, ale
        # poznamku mit muze - a prave u ni je nejdulezitejsi, at nezmizi.
        poznamky = "; ".join(f.poznamky)
        radky = list(f.podklady())
        if not radky and poznamky:
            radky = [("", "")]
        for i, (stitek, text) in enumerate(radky):
            _radek(ws_p, [kreditor, jmeno, stitek, text,
                          poznamky if i == 0 else ""])
    for b in ws_p[zahlavi_p]:
        b.font = Font(bold=True, color="FFFFFF")
        b.fill = vypln
    for radek in ws_p.iter_rows(min_row=zahlavi_p + 1, min_col=4, max_col=5):
        for bunka in radek:
            bunka.alignment = Alignment(wrap_text=True, vertical="top")
    ws_p.freeze_panes = "A%d" % (zahlavi_p + 1)

    # -- list Metodika (co který sloupec znamená a vazba na ISO 27001) ----
    ws_m = wb.create_sheet("Metodika")
    for i, sirka in enumerate((28, 78, 40), 1):
        ws_m.column_dimensions[get_column_letter(i)].width = sirka
    zahlavi_m = _karta(ws_m, "Metodika", [
        "Co znamená který sloupec listu Dodavatelé, co do něj patří a na "
        "které řízení ISO/IEC 27001 se váže.",
        "Sem se dívejte, když nevíte, kterou hodnotu z rozbalovacího seznamu "
        "vybrat – u Přístupu a Nahraditelnosti jsou popsané všechny volby.",
        "Prázdná vazba na ISO znamená, že sloupec je jen identifikační nebo "
        "provozní, ne důkaz k žádnému řízení.",
    ])
    ws_m.cell(zahlavi_m, 1, "Sloupec listu Dodavatelé")
    ws_m.cell(zahlavi_m, 2, "Popis")
    ws_m.cell(zahlavi_m, 3, "Vazba na ISO/IEC 27001")
    for nazev, popis, iso in METODIKA:
        _radek(ws_m, [nazev, popis, iso])
    _radek(ws_m, [])
    r = _radek(ws_m, ["Jak se počítá Kritičnost", "", ""])
    ws_m.cell(r, 1).font = Font(bold=True, size=12, color=BARVA_TMAVA)
    for nazev, popis in (
        ("KRITICKÝ", "dodavatel nám spravuje systémy (stupeň 5), nebo je na "
         "něm kritická závislost, nebo jde o ICT dodávku a dodavatel je "
         "přitom aspoň na stupni 3 – má naše data nebo chodí do systémů"),
        ("VÝZNAMNÝ", "ICT dodávka, nebo je dodavatel aspoň na stupni 3 "
         "(má naše data u sebe, přístup do systémů), nebo je obtížně "
         "nahraditelný"),
        ("BĚŽNÝ", "vše ostatní – žádný nebo pouze fyzický přístup u běžně "
         "nahraditelného dodavatele mimo ICT"),
        ("⟵ doplňte přístup", "není vyplněný Přístup k datům/systémům; "
         "kritičnost se záměrně nepočítá, aby prázdný řádek nevypadal jako "
         "posouzený"),
    ):
        _radek(ws_m, [nazev, popis, ""])
    for b in ws_m[zahlavi_m]:
        b.font = Font(bold=True, color="FFFFFF")
        b.fill = vypln
    ws_m.freeze_panes = "A%d" % (zahlavi_m + 1)
    for radek in ws_m.iter_rows(min_row=zahlavi_m + 1):
        for bunka in radek:
            bunka.alignment = Alignment(wrap_text=True, vertical="top")

    wb.save(cesta)

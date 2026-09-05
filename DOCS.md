# Podrobná dokumentace

Referenční dokumentace k `dodavatele.py` – jak spustit a co dělá základní
běh je v [README.md](README.md), tady jsou detaily, edge case a kompletní
seznam přepínačů/kategorií.

**Obsah:**
- [Vstup](#vstup)
- [Výstup](#výstup)
- [Dohledání identifikátoru pro zahraniční firmy (--jen-id)](#dohledání-identifikátoru-pro-zahraniční-firmy---jen-id)
- [Ruční zařazení nekategorizovaných firem přes LLM chat (--export-nezarazene)](#ruční-zařazení-nekategorizovaných-firem-přes-llm-chat---export-nezarazene)
- [Komparace NACE s externím zdrojem (--komparace)](#komparace-nace-s-externím-zdrojem---komparace)
- [Zdroje dat](#zdroje-dat)
- [Taxonomie kategorií](#taxonomie-kategorií)
- [Přepínače](#přepínače)
- [Poznámky k provozu](#poznámky-k-provozu)

## Vstup

`.csv`, `.xlsx` nebo `.txt` (jeden název na řádek). U CSV/XLSX se hlavička
rozpozná automaticky, rozumí česky i anglicky:

| sloupec | rozpoznávané názvy | povinný |
|---|---|---|
| název | Název, Jméno, Firma, Company, Supplier, Vendor, Lieferant … | ano* |
| IČO | IČO, IC, Company ID, Registration number | ne |
| DIČ | DIČ, VAT, VAT ID, USt-IdNr, Tax ID | ne |
| země | Země, Country, Stát, ISO | ne |
| ulice | Ulice, Street, Address, Adresa, Straße | ne |
| PSČ | PSČ, ZIP, Postal code, PLZ | ne |
| město | Město, City, Town, Ort | ne |

\* místo názvu stačí IČO nebo DIČ. Vyplněná **země** zúží hledání na správný
rejstřík a zrychlí běh.

Vyplněná **adresa** (ulice/PSČ/město) pomáhá rozlišit mezi více firmami se
stejným nebo podobným názvem — třeba dvě samostatné firmy `Škoda a.s.`
(jedna v Plzni, druhá v Praze) mají v rejstříku identický název a bez adresy
by šlo o čirou náhodu, která se vybere. Shoda PSČ nebo města zvýší důvěru ve
správný nález, nesoulad naopak upozorní v Poznámce. Kategorii ani NACE
adresa neurčuje — pomáhá jen najít správný subjekt, ne ho zařadit.

### Pořadí vyhledávání

Nástroj zkouší postupně tři cesty, každá jednoznačnější než ta další:

1. **IČO** – přesné vyhledání v rejstříku. U zahraničních firem může sloupec
   IČO obsahovat i jiný identifikátor než české IČO — LEI, nebo národní
   registrační číslo (např. německé `HRB 6684`, francouzské SIREN, americké
   CIK). Nástroj typ čísla podle tvaru i země pozná sám. Viz
   [Dohledání identifikátoru pro zahraniční firmy](#dohledání-identifikátoru-pro-zahraniční-firmy---jen-id)
   níže, pokud takové číslo nemáte a chcete ho nechat dohledat automaticky.
2. **DIČ** – když IČO cestu nevyřešilo (nebo nebylo zadané), zkusí se DIČ
   přes evropský systém VIES. Data jsou chudší (jen jméno a adresa, žádné
   NACE ani registrační číslo), ale DIČ je na rozdíl od názvu jednoznačné.
   Funguje jen pro DIČ v rámci EU/EHP.
3. **Jméno** – až když ani IČO, ani DIČ nevedlo k jednoznačnému výsledku,
   hledá se fuzzy podle názvu firmy napříč dostupnými zdroji.

VIES je občas dočasně přetížený (hlavně při více souběžných dotazech na
stejný stát) — nástroj to pozná a dotaz sám 5× zopakuje, než to vzdá a
přejde na hledání jménem.

## Výstup

Sloupce podle zadání: `Jméno | Ulice | PSČ | Město | Země | IČO | DIČ | NACE`,
k tomu `Kód kategorie | Skupina | Kategorie dodavatele` a doplňkové sloupce
pro kontrolu (`--kompakt` je vypne):

* **Registrační číslo / Rejstřík** – u zahraničních firem národní registrační
  číslo (obdoba IČO, např. `HRB 719915` u Německa, `1803-01-018771` u Japonska)
  a jméno rejstříku, u kterého je vedeno.
* **NACE - zdroj** – rozlišuje skutečný NACE z rejstříku (ARES, INSEE) od
  odhadu z oboru na Wikidatech, který je méně přesný.
* **Klasifikace (US NAICS)** – u amerických dodavatelů severoamerická obdoba
  NACE (NACE se u USA jen odhaduje pro účely vlastní taxonomie).

XLSX má druhý list **Číselník kategorií** s celou taxonomií a počtem
dodavatelů v každé kategorii, a třetí list **Číselník NACE** s názvy všech
NACE divizí (2místné kódy) - aby šlo kód ve sloupci NACE dohledat v plném
znění i bez opuštění sešitu (pro klienta apod.). Jde jen o hlavní divize, ne
o kompletní podrobnou nomenklaturu (tisíce 4-6místných tříd).

### Sloupec „Stav“

| stav | význam |
|---|---|
| `OK` | jednoznačná shoda názvu, data lze převzít |
| `VYBRANO` | více srovnatelně podobných firem – nástroj automaticky vybral tu nejlepší (viz níže), ostatní kandidáty najdete v Poznámce |
| `OVERIT` | shoda pod prahem, nebo shoda s výhradou (např. jiná země sídla, než jste zadali) – data převzata, ale zkontrolujte je |
| `NENALEZENO` | nic dost podobného; sloupce, které by musely přijít z rejstříku (adresa, NACE…), **zůstávají prázdné**, v Poznámce jsou nejbližší kandidáti |
| `CHYBA` | prázdný řádek nebo výpadek všech zdrojů |

Údaje nalezeného kandidáta se do výstupu propíšou jen při dostatečné shodě —
u nízké shody radši prázdno než data cizí firmy. To se ale týká jen toho, co
by muselo přijít z rejstříku. **Co jste zadali na vstupu (Jméno, IČO, DIČ,
Země), se do výstupu propíše vždy** — i u `NENALEZENO`, protože to už vaše
data jsou a nemá smysl je zahazovat jen proto, že se firma nedohledala.

#### Automatický výběr při více shodách

Dřív, když rejstřík vrátil víc stejně podobných firem (např. "Danone S.A."
sedí jak na francouzskou mateřskou společnost, tak na portugalskou dceřinou),
musel se výsledek dohledávat ručně. Nástroj teď vybere sám — kombinuje
podobnost názvu s dalšími signály:

* **shoda země** – kandidát se sídlem v zadané zemi má přednost, sídlo jinde je penalizováno,
* **aktivní subjekt** – zaniklá/vymazaná firma je penalizována,
* **úplnost záznamu** – kandidát s NACE, registračním číslem nebo DIČ vyhrává těsné remízy.

Pokud po tomto zvážení zbude jasný vítěz, dostane stav `VYBRANO` a do
Poznámky se zapíše, o kolik bodů byl druhý v pořadí horší — u výrazně horších
kandidátů rovnou `OK`. Pokud i po zvážení zůstanou dva kandidáti prakticky
nerozeznatelní, projeví se to nižším skóre a stavem `OVERIT` s vysvětlením v
Poznámce (např. „pozor: sídlo v PT místo FR“) — tam ještě stojí za to
zkontrolovat ručně.

#### Firma se nenajde v ARES (`NENALEZENO` u české firmy)

Když zadané IČO není v hlavním rejstříku ARES (firma z něj vypadla), nástroj
automaticky zkusí ještě **Veřejný rejstřík (VR)** — ten na rozdíl od
hlavního indexu drží historii i po výmazu. Pokud tam záznam o výmazu je,
doplní se do **Poznámky** datum a právní důvod výmazu (např. „vymazan z
rejstriku 2019-06-30, duvod: Výmaz z důvodu likvidace“).

Řádek přesto zůstane `NENALEZENO` s prázdnými datovými sloupci — firma
už neexistuje, takže nemá smysl vyplňovat aktuální adresu/NACE. Pokud ani VR
nic nenajde, ověřte IČO ručně např. v insolvenčním rejstříku nebo Obchodním
věstníku.

#### Firma má v ARES víc oborů podnikání a kategorie nesedí

U českých firem se kategorie určuje z pole **převažující činnost** (RES),
které ARES vede jako oficiální označení hlavního oboru napříč všemi
zapsanými NACE kódy — u firem s víc obory (typicky OSVČ s víc živnostmi)
tak nejde o náhodný výběr, ale o údaj, který přímo rejstřík označuje jako
hlavní.

Dvě situace, kdy to přesto nesedí:

* **Firma nemá převažující činnost formálně nastavenou.** RES pak vrací
  kód `00` ("neurčeno") — nástroj ho ignoruje (jinak by přepsal i dobře
  určený obor nepoužitelnou hodnotou) a spadne zpět na první nepodpůrný kód
  ze seznamu všech zapsaných NACE. Pokud i to selže, zůstává `XXX-00` —
  firma opravdu žádný použitelný kód nemá.
* **Převažující činnost je obecný/podpůrný kód** (např. `6820` pronájem
  nemovitostí — mnoho firem ho má zapsaný jen jako formální rezervu při
  založení, ne jako skutečnou náplň podnikání). Nástroj takový kód
  nepřehazuje za jiný ze seznamu (bylo by to hádání), ale doplní do
  **Poznámky** upozornění „převažující NACE je obecný kód… zkontrolujte
  NACE (všechny)“ — v tom sloupci najdete i ostatní zapsané obory
  k ručnímu porovnání se skutečnou činností firmy.

#### Firma se nenajde v zemi bez napojeného rejstříku

U zemí bez vlastního připojení (DE, NL, AT, BE, CH, IT, ES, HU, PL, RO, BG,
TR, MY, HK, CA, zatím i GB) se u `NENALEZENO` řádku předpřipraví do sloupce
**Odkaz na rejstřík** hotový vyhledávací dotaz — Google omezený na doménu
příslušného národního rejstříku (`site:handelsregister.de "Název firmy"`),
u zemí připojených k evropskému BRIS odkaz na centrální
[e-justice.europa.eu](https://e-justice.europa.eu/content_find_a_company-489-en.do).
Stačí kliknout, nemusíte nic přepisovat ručně.

## Dohledání identifikátoru pro zahraniční firmy (--jen-id)

Nejpřesnější způsob, jak najít zahraniční firmu, je podle **jejího
identifikačního čísla** (LEI, německé `HRB`, francouzské SIREN, americké
CIK…) — na rozdíl od jména je jednoznačné, takže odpadá riziko `VYBRANO`
u více podobně znějících firem. Pokud takové číslo nemáte, dá se nechat
dohledat ve dvou krocích:

```bash
# 1. krok - jen dohledat identifikační čísla, bez plného obohacení
python3 dodavatele.py vstup.csv -o kroky/id.xlsx --jen-id

# --> zkontrolovat sloupce "Nalezené jméno" a "Shoda názvu" v kroky/id.xlsx,
#     případně opravit řádky se stavem VYBRANO/OVERIT ručně

# 2. krok - plné obohacení, tentokrat uz s dohledanymi cisly
python3 dodavatele.py kroky/id.xlsx -o vystup.xlsx
```

První krok (`--jen-id`) prohledá stejné zdroje jako běžný běh, ale vypíše jen
sloupce potřebné ke kontrole — `Název | IČO | DIČ | Země` (přesně ve tvaru
vzorového vstupu, takže výstup jde bez úprav použít jako vstup druhého kroku)
a navíc `Nalezené jméno`, `Typ čísla / rejstřík`, `Shoda názvu`, `Stav`,
`Zdroj dat`, `Poznámka` pro kontrolu.

Druhý krok pak u řádků s vyplněným IČO/identifikátorem **přeskočí hledání
podle jména** a jde rovnou na přesné vyhledání podle čísla — přesnější
i rychlejší. Nástroj typ čísla pozná automaticky:

* 20znakový kód → **LEI**, přímé vyhledání v GLEIF,
* francouzská země → **SIREN**, přímé vyhledání v INSEE,
* americká země → **CIK**, přímé vyhledání v SEC EDGAR,
* jinak → **národní registrační číslo**, přesný filtr v GLEIF podle země.

Když číslo odpovídá více firmám najednou (vzácné, např. znovupoužité
registrační číslo po zániku původní firmy), a řádek nemá vyplněné i jméno,
zůstane `NENALEZENO` s kandidáty v Poznámce — bez jména totiž není podle čeho
rozhodnout, která firma je ta správná.

## Ruční zařazení nekategorizovaných firem přes LLM chat (--export-nezarazene)

Firmy, které nemají NACE ani obor z Wikidat, skončí v `XXX-00 Nezařazeno`
(viz [Taxonomie kategorií](#taxonomie-kategorií) níže — nástroj kategorii
záměrně nehádá z ničeho nepodloženého). Pokud máte přístup k firemnímu LLM
chatu (MS Copilot, ChatGPT…) jen jako k webovému rozhraní, bez API klíče,
dá se k doplnění použít stejný dvoukrokový princip jako u `--jen-id`:

```bash
# 1. krok - normální běh + export nekategorizovaných firem pro chat
python3 dodavatele.py vstup.csv -o vystup.xlsx --export-nezarazene nezarazene.txt

# --> obsah nezarazene.txt vložit do Copilotu/ChatGPT, odpověď uložit
#     jako CSV (Název;Kód kategorie;Zdůvodnění), např. odpoved.csv

# 2. krok - stejný běh znovu, tentokrát s ručním zařazením
python3 dodavatele.py vstup.csv -o vystup.xlsx --kategorie-mapa odpoved.csv
```

`--export-nezarazene` vypíše číselník všech kategorií a seznam nekategorizovaných
firem (se zemí a adresou, je-li známá, pro kontext) do textového souboru
připraveného na vložení do chatu i s instrukcí a požadovaným formátem odpovědi.
`--kategorie-mapa` pak načte odpověď z chatu (soubor `Název;Kód kategorie[;…]`)
a aplikuje ji na firmy, které jsou pořád `XXX-00` — nedotkne se řádků, které
už kategorii mají z NACE nebo Wikidat. Takto přiřazené řádky mají ve sloupci
**Zařazeno podle** hodnotu `rucne (LLM)`, takže je vždy vidět, co je ověřený
fakt z rejstříku a co ruční/AI odhad ke kontrole.

Žádný nový závislost, API klíč ani automatizace prohlížeče — jen soubor
na kopírování mezi nástrojem a chatem, který už máte k dispozici.

## Komparace NACE s externím zdrojem (--komparace)

Když někdo jiný (kolega, AI nástroj) doplní vlastní odhad NACE přímo do už
vygenerovaného výstupu tohoto nástroje (přidá si do souboru svůj sloupec),
jde jeho sloupec porovnat s naším:

```bash
python3 dodavatele.py --komparace vystup_s_kolegovym_sloupcem.xlsx \
    --komparace-sloupec "Kolegův NACE"
```

Řádky se berou 1:1 podle pozice (žádné párování podle jména/IČO — soubor je
už náš vlastní výstup jen s přidaným sloupcem navíc). Shoda se počítá na
úrovni **NACE divize** (první 2 číslice) — odpouští drobné rozdíly
v podrobnosti mezi dvěma různými zdroji, ne přesnou shodu celého kódu.
Výstup (výchozí `<--komparace>_komparace.<přípona>`) obsahuje všechny
původní sloupce plus nový sloupec **Shoda NACE (divize)** (ANO/NE/prázdné,
pokud jedné straně kód chybí) a na stderr vypíše souhrn — kolik řádků je
srovnatelných a jaké je procento shody.

## Zdroje dat

| zdroj | pokrytí | co dodá |
|---|---|---|
| **ARES** (ares.gov.cz) | ČR, kompletní | název, adresa, IČO, DIČ, NACE včetně *převažující činnosti*; u vymazaných firem datum a důvod výmazu (zdroj VR) |
| **RPO SR** (statistics.sk) | SR, kompletní | název, adresa, IČO, SK NACE (hlavní činnost), právní forma |
| **INSEE/INPI** (recherche-entreprises.api.gouv.fr) | Francie, kompletní | název, adresa, SIREN, NAF → NACE, DIČ (dopočteno) |
| **ACRA** (data.gov.sg) | Singapur, kompletní | název, adresa, UEN, stav (aktivní/vymazáno) |
| **GCIS** (data.gcis.nat.gov.tw) | Tchaj-wan, kompletní | název, adresa, daňové číslo, datum vzniku |
| **Handelsregister** (lokální kopie, `--pripravit-de-rejstrik`) | Německo, ~5,3 mil. firem (data k 2019) | název, adresa, číslo zápisu (HRA/HRB/…), právní forma, stav (aktivní/vymazáno) |
| **Companies House** (lokální kopie, `--pripravit-gb-rejstrik`) | Velká Británie, ~5 mil. firem (měsíční aktualizace) | název, adresa, číslo firmy, právní forma, SIC 2007 → NACE, stav |
| **GLEIF** (api.gleif.org) | svět, firmy s LEI (většina větších/kotovaných firem) | název (i v původním jazyce), adresa, národní registrační číslo, právní forma |
| **SEC EDGAR** (sec.gov) | USA, firmy registrované u SEC | název, adresa, SIC → NACE i NAICS, CIK |
| **Wikidata** | velké nadnárodní firmy | obor činnosti (viz níže), EU DIČ, LEI, sídlo |
| **VIES** (`--vies`) | EU | ověření platnosti DIČ |
| **ANAF** (webservicesp.anaf.ro) | Rumunsko, jen podle už známého DIČ | CAEN → NACE, adresa, registrační číslo (ONRC) - nelze hledat podle jména |

Vše bez API klíče a bez registrace.

**Poznámka k RPO SR:** vyhledávací pole `fullName` je nečekaně citlivé na
interpunkci – s čárkou nebo tečkovanou právní formou přímo v zadání
("Firma, a.s.", "Firma a. s.") vrátí 0 výsledků, zatímco bez právní formy
("Firma") normálně najde. Nástroj proto na dotaz posílá název zbavený
interpunkce a právní formy, přesný výběr správné firmy pak řeší až
následné porovnání skóre s původním názvem – stejně jako u ostatních
zdrojů. Hlavní ekonomická činnost (SK NACE) a právní forma navíc nejsou
součástí vyhledávacích výsledků, ale až detailu jednoho záznamu – nástroj
si ho po výběru nejlepší shody dotáhne zvlášť.

**Poznámka k Tchaj-wanu:** certifikát `data.gcis.nat.gov.tw` neobsahuje rozšíření
Subject Key Identifier, které novější Python/OpenSSL standardně vyžaduje –
nástroj proto pro tento jeden zdroj vypíná právě tuto jednu nadstandardní
kontrolu (ověření řetězce důvěry a jména serveru zůstává aktivní).

### Německo - lokální kopie Handelsregisteru

GLEIF obsahuje jen firmy s LEI (povinné hlavně pro účastníky finančních trhů),
takže běžná malá německá GmbH/UG v něm typicky vůbec není - to není chyba
dotazu, GLEIF prostě není obecný rejstřík. Německo nemá oficiální veřejné
API k Handelsregisteru vůbec (150 samostatných zemských rejstříků, žádné
jednotné rozhraní). Jediná volně dostupná alternativa je bulk export
OpenCorporates zveřejňovaný projektem **OffeneRegister.de** (OKF Deutschland,
CC BY 4.0) - jeho živé dotazovací API (`db.offeneregister.de`) je ale
dlouhodobě nedostupné (spadlý backend), proto nástroj používá přímo
stažitelnou SQLite kopii s FTS5 indexem.

Příprava (jednorázově, ~740 MB stažení / ~2,6 GB na disku):

```
python3 dodavatele.py --pripravit-de-rejstrik
```

Bez připravené databáze (`de_handelsregister.db`) se tento zdroj automaticky
přeskočí a německé firmy se hledají jen přes GLEIF + Wikidata jako dřív -
žádná chyba, jen nižší přesnost. Vypnout jde i ručně přes `--bez-de`.

**Data jsou stará** - sesbíraná do začátku roku 2019 a dál se
neaktualizují. Stav (aktivní/vymazáno), adresa i jednatelé tak mohou být
neaktuální; na rozdíl od ARES/INSEE nejde o živý rejstřík. Číslo zápisu
(např. `HRB 45109`) navíc není celostátně jedinečné - stejné číslo používají
různé rejstříkové soudy - proto se při zadání jen čísla bez názvu firmy
může vrátit víc kandidátů k ruční kontrole (stejně jako u GLEIF).

### Německo - "Gegenstand des Unternehmens" (--de-gegenstand)

Lokální kopie Handelsregisteru výše nenese obor činnosti vůbec - německý
rejstřík ho jako kód nevede (na rozdíl od ČR/SR). Jediné místo, kde je
skutečný **předmět podnikání jako volný text** k dispozici, je aktuální výpis
(dokument „AD") přímo z portálu `handelsregister.de`. Ten nemá API - je to
stará JSF aplikace se session postbacky, kterou `--de-gegenstand` replikuje
přes `urllib` (žádná nová závislost na scraping knihovně, jen `pypdf` pro
čtení staženého PDF výpisu).

```bash
# 1. krok - normální běh, ať máme německé firmy identifikované (jméno + HRB/HRA)
python3 dodavatele.py vstup.csv -o vystup.xlsx

# 2. krok - doplnit Gegenstand pro německé řádky ve vystup.xlsx
python3 dodavatele.py --de-gegenstand vystup.xlsx
```

Vyžaduje připravenou lokální kopii Handelsregisteru (`--pripravit-de-rejstrik`)
- z ní se dohledá soud potřebný k jednoznačnému výběru správného řádku na
portálu (číslo zápisu samo o sobě není jedinečné, viz výše).

**Důležité omezení:**
* Podmínky použití portálu povolují max. **60 dotazů/hodinu** (dle FAQ portálu
  hrozí při překročení i trestní odpovědnost dle §303a/b StGB) - běh proto
  vždy jede sekvenčně (bez ohledu na `--workers`) s pevnou prodlevou, počítejte
  s **~4 minutami na firmu** (4 požadavky: úvod, rozšířené hledání, vyhledání,
  stažení dokumentu).
* Text se přidá jako nový sloupec „Gegenstand (Handelsregister)" do
  výstupního souboru (`<--de-gegenstand>_gegenstand.<přípona>`) - použitelný
  i jako kontext pro ruční/LLM zařazení (`--export-nezarazene`), pokud
  automatický odhad níže nic nenajde.
* **Navíc se zkouší automatický odhad kategorie z klíčových frází v textu**
  (`taxonomie.nace_z_gegenstand()`) - sloupce „NACE (odhad z Gegenstand)",
  „Kód kategorie (odhad z Gegenstand)", „Kategorie dodavatele (odhad z
  Gegenstand)". Na rozdíl od zbytku nástroje, který kategorii z volného textu
  záměrně nehádá (viz výše), je tohle vyslovně vyžádaná výjimka - Gegenstand
  je ale povinná právní formulace předmětu podnikání ze společenské smlouvy,
  ne jen název firmy, takže je nesrovnatelně informativnější. I tak jde jen
  o shodu klíčových frází, ne skutečný kód z rejstříku - slovník
  (`GEGENSTAND_KLICOVA_SLOVA` v `taxonomie.py`) je záměrně malý a používá jen
  konkrétní, jednoznačné fráze (např. "steuerberatung", "gebäudereinigung"),
  ne obecná slova jako "Herstellung und Vertrieb" nebo "Produktion von", která
  se objevují skoro v každém Gegenstand bez ohledu na skutečný obor - takové
  fráze by vedly k nahodilé, ničím nepodložené kategorii (ověřeno na adidas
  AG: bez konkrétního produktu ve frázi raději žádný odhad než jistý špatný).
  Pokrývá tak jen menšinu běžných oborů, u zbytku sloupce zůstanou prázdné.
* Vyžaduje `pip install pypdf` (v `requirements.txt`).

### Velká Británie - lokální kopie Companies House

Na rozdíl od Německa má Companies House **oficiální bezplatný bulk export** bez
jakékoli registrace - `download.companieshouse.gov.uk`, aktualizuje se měsíčně,
~5 mil. firem. Navíc obsahuje rovnou i obor činnosti (UK SIC 2007 - číselně
stejná úroveň jako NACE Rev. 2), takže se u UK firem **nemusí čekat na
Wikidata** kvůli oboru, jen kvůli samotnému dohledání firmy podle jména.

Příprava (jednorázově, ~500 MB stažení, import ~5 mil. řádků do SQLite s
fulltextovým indexem trvá řádově minuty):

```
python3 dodavatele.py --pripravit-gb-rejstrik
```

Bez připravené databáze (`gb_companies_house.db`) se britské firmy hledají
jen přes GLEIF + Wikidata jako dřív. Vypnout jde ručně přes `--bez-gb`.

### Jak nástroj hledá dodavatele mimo ČR/SR/FR/SG/TW/DE/GB

Země bez přímo napojeného rejstříku (viz tabulka výše) se hledají přes GLEIF a
Wikidata:

1. **GLEIF** dá jméno, adresu a národní registrační číslo (obdoba IČO – např.
   `HRB 719915` u Německa, Business Registration Number v Koreji). GLEIF vede
   pravní název v národním jazyce (korejsky, japonsky, čínsky, bulharsky…) –
   nástroj proto porovnává i anglickou variantu jména (`otherNames`), jinak by
   se firmy z těchto zemí vůbec nedohledaly.
2. **Wikidata** doplní obor činnosti podle vlastní mapy ~165 oborů
   (Wikidata property *industry*, P452) na kategorii a odhad NACE – funguje
   nezávisle na jazyce, protože se srovnávají číselné identifikátory (QID),
   ne text.

Když ani jedno nedá obor, firma skončí v `XXX-00 Nezařazeno` k ruční
kontrole. Nástroj záměrně **nehádá kategorii z klíčových slov v názvu
firmy** – shoda slova v názvu není fakt o oboru činnosti a dřív vedla
i k vyloženě špatným zařazením (např. "Deutsche Akkreditierungsstelle"
– akreditační orgán – dřív skončila jako "Leasing, úvěry a financování",
protože "kredit" sedělo jako podřetězec). Radši prázdná kategorie
k doplnění než nejistý odhad.

**Pro USA** se místo NACE dohledává NAICS (americká obdoba) přes SIC kód ze
SEC EDGAR – je ve sloupci **Klasifikace (US NAICS)**, NACE se u amerických
firem jen přibližně dopočítává pro účely vlastní taxonomie.

**Známé limity.**
* GLEIF obsahuje jen entity s LEI, takže řada firem střední velikosti tam
  není (typicky se dohledají přes Wikidata, ale s méně přesnými daty).
  Pro takové dodavatele doplňte IČO/VAT do vstupu, nebo počítejte se stavem
  `NENALEZENO`/`OVERIT` a ručním doplněním. **U Německa** navíc zkuste
  `--de-gegenstand` (viz výše) - dá skutečný předmět podnikání i pro malé
  firmy bez Wikidata záznamu, jen pomaleji (limit portálu ~60 dotazů/h).
* Sloupec **NACE - zdroj** říká, jestli je NACE skutečný údaj z rejstříku,
  nebo jen odhad z oboru na Wikidatech („odhad z oboru (Wikidata)“) — u
  odhadu počítejte s nižší přesností než u NACE z ARES/INSEE.
* Turecko (TR) je nejobtížnější země v seznamu – GLEIF má z tureckých firem
  jen zlomek, hlavní subjekty tak často skončí na `OVERIT` nebo
  `NENALEZENO`. Doplnění VAT/registračního čísla do vstupu výrazně pomůže.

### Pokrytí zemí

Ověřeno na běžných dodavatelích z těchto zemí (kontrolní seznam napříč
odvětvími, 34 z 37 reálných firem se dohledalo a zařadilo do kategorie):

| země | přímý rejstřík | jinak přes |
|---|---|---|
| CZ | ARES | – |
| SK | RPO SR | – |
| FR | INSEE/INPI | – |
| SG | ACRA | – |
| TW | GCIS | – |
| US | SEC EDGAR (jen firmy registrované u SEC) | GLEIF + Wikidata |
| DE | Handelsregister, lokální kopie (`--pripravit-de-rejstrik`, data k 2019) | GLEIF + Wikidata |
| GB | Companies House, lokální kopie (`--pripravit-gb-rejstrik`, měsíční aktualizace) | GLEIF + Wikidata |
| NL, AT, BE, IT, ES, HU, IE, SE, BG, PL, RO | – | GLEIF + Wikidata |
| KR, CH, HK, JP, MY, CA, CN, TR | – | GLEIF + Wikidata |

U zemí bez přímého rejstříku (vše kromě CZ/SK/FR/SG/TW/US) závisí přesnost
adresy a NACE na tom, jestli má firma LEI (GLEIF) a/nebo je vedená na
Wikidatech – u velkých a kotovaných firem to funguje spolehlivě, u menších
dodavatelů počítejte s `OVERIT`/`NENALEZENO` a doplňte IČO/VAT do vstupu.

**Zkoumali jsme, jestli existuje volně dostupný rejstřík i pro ostatní země
(DE, NL, AT, BE, GB, IE, CH, IT, ES, HU, PL, RO, BG, SE, TR, KR, JP, CN, MY,
HK, CA)** – žádný z nich dnes nemá bezklíčové, hromadně dotazovatelné *živé*
API srovnatelné s ARES/INSEE/ACRA/GCIS, ale u několika zemí existuje aspoň
**stažitelný bulk export**, ze kterého jde postavit lokální kopii stejně jako
u DE (`--pripravit-de-rejstrik`) a GB (`--pripravit-gb-rejstrik`):

* **GB** (Companies House) – bezplatný bulk export bez jakékoli registrace,
  viz výše. Živé REST API taky existuje, ale vyžaduje klíč a je určené na
  jednotlivé dotazy, ne hromadné stahování.
* **BE** (KBO/BCE Open Data) – bezplatný měsíční bulk export vč. NACEBEL kódů,
  ale vyžaduje jednorázovou registraci e-mailu na
  `kbopub.economie.fgov.be/kbo-open-data` – zatím nezapojeno, čeká na vyřízení
  přístupu.
* **RO** (ANAF) – oficiální bezklíčové API `webservicesp.anaf.ro` vrací podle
  zadaného CUI (DIČ) i CAEN kód (rumunský NACE) a adresu - nejde ale hledat
  podle jména, jen doplnit obor k už známému DIČ (proto zapojeno jako
  doplněk k VIES, ne jako samostatný zdroj - `--bez-ro` pro vypnutí).
  **Nebylo možné ověřit** z prostředí, kde vznikl - endpoint vracel 404
  (patrně geo/WAF blokace), implementace vychází z oficiální dokumentace.
  Ověřte prvním skutečným během na RO firmě se známým DIČ.
* **PL** (GUS REGON/BIR1.1) – bezplatný `USER_KEY` na vyžádání e-mailem,
  rozhraní je ale staré SOAP se session přihlášením - zatím nezapojeno,
  nejnáročnější na implementaci ze čtveřice výše.
* **JP** (houjin-bangou.nta.go.jp, japonská daňová správa) – vede *všechny*
  registrované firmy, bezplatný `appid` se ale vyřizuje ~1 pracovní den.
* **SE** – oficiální Bolagsverket API zatím neumí hledání podle jména;
  funguje jen přes neoficiální `bolagsdataapi.se` (bezplatná registrace,
  500 dotazů/den).

U zbylých zemí (NL, AT, IE, CH, IT, ES, HU, BG, TR, KR, CN, MY, HK) je
oficiální rejstřík buď jen placený, nebo vyžaduje tuzemskou identitu, nebo
nemá žádné API ani bulk export vůbec – tam zůstává GLEIF + Wikidata jediná
volně dostupná cesta.

## Taxonomie kategorií

Dvouúrovňová: **skupina** → **kategorie s kódem** (např. `ICT-03  Cloud, hosting
a datová centra`). Je to vlastní návrh, ne převzatý standard — 95 kategorií
v 17 skupinách. Kód kategorie je zkratka skupiny + pořadové číslo.

Zařazení probíhá v tomto pořadí:

1. **podle NACE** – u českých firem se použije *převažující činnost* z registru
   RES (pole `czNacePrevazujici2008`). Seznam všech NACE, který ARES vrací,
   je řazen vzestupně podle kódu, ne podle významu, takže se na jeho pořadí
   nedá spolehnout – proto ten druhý dotaz.
2. **podle oboru z Wikidat** (strukturovaný QID) – když NACE není.
3. `XXX-00 Nezařazeno` – vyžaduje ruční doplnění. Sloupec **Zařazeno podle**
   říká, která z cest se uplatnila.

Kategorie se záměrně nehádá z klíčových slov v názvu firmy — jen ze
skutečných údajů (NACE nebo strukturovaný obor), viz vysvětlení výše
u zahraničních dodavatelů.

### Úprava taxonomie

```bash
python3 dodavatele.py --dump-taxonomy taxonomie.json    # export
# ... úprava v editoru ...
python3 dodavatele.py vstup.csv --taxonomy taxonomie.json
```

JSON obsahuje číselník kategorií, mapu NACE → kategorie, mapu oborů
z Wikidat i převod SIC → NACE/NAICS. Alternativně lze upravit přímo
`taxonomie.py`.

### Číselník kategorií

Kompletní seznam je i v listu **Číselník kategorií** ve vygenerovaném XLSX
(tam navíc s počtem dodavatelů v každé kategorii).

<details>
<summary>Zobrazit všech 95 kategorií</summary>

#### Bezpečnost

| kód | kategorie |
|---|---|
| SEC-01 | Fyzická ostraha a bezpečnostní služby |
| SEC-02 | Bezpečnostní technologie (EZS, CCTV, přístupové systémy) |

#### Energie a utility

| kód | kategorie |
|---|---|
| ENE-01 | Dodávka elektřiny a plynu |
| ENE-02 | Teplo a energetické služby |
| ENE-03 | Paliva a pohonné hmoty |
| ENE-04 | Vodné, stočné a vodohospodářské služby |

#### Finanční služby

| kód | kategorie |
|---|---|
| FIN-01 | Bankovní služby |
| FIN-02 | Platební a zúčtovací služby |
| FIN-03 | Pojištění a zajištění |
| FIN-04 | Leasing, úvěry a financování |
| FIN-05 | Ostatní finanční a investiční služby |
| FIN-06 | Inkaso pohledávek a kreditní služby |

#### ICT a technologie

| kód | kategorie |
|---|---|
| ICT-01 | Vývoj software a aplikací na zakázku |
| ICT-02 | Software, licence a SaaS |
| ICT-03 | Cloud, hosting a datová centra |
| ICT-04 | Správa IT a managed services |
| ICT-05 | IT poradenství a systémová integrace |
| ICT-06 | Kybernetická bezpečnost |
| ICT-07 | Hardware a koncová zařízení |
| ICT-08 | Síťová a komunikační infrastruktura |
| ICT-09 | Telekomunikační služby a konektivita |
| ICT-10 | Zpracování dat, BPO a sdílené služby |
| ICT-11 | Servis a likvidace výpočetní techniky |
| ICT-12 | Internetové portály a online služby |

#### Lidské zdroje

| kód | kategorie |
|---|---|
| HR-01 | Nábor a personální agentury |
| HR-02 | Agenturní zaměstnávání a dočasné přidělení |
| HR-03 | Mzdové a personální služby (payroll) |
| HR-04 | Školení a vzdělávání |
| HR-05 | Benefity a péče o zaměstnance |

#### Logistika a doprava

| kód | kategorie |
|---|---|
| LOG-01 | Silniční a železniční doprava |
| LOG-02 | Letecká a námořní přeprava |
| LOG-03 | Zasílatelství a spedice |
| LOG-04 | Skladování a logistické služby |
| LOG-05 | Kurýrní a poštovní služby |

#### Marketing a média

| kód | kategorie |
|---|---|
| MKT-01 | Reklamní a mediální agentury |
| MKT-02 | Průzkum trhu a analytika |
| MKT-03 | Tisk, polygrafie a reklamní produkce |
| MKT-04 | Eventy, konference a veletrhy |
| MKT-05 | Audiovizuální produkce a vysílání |

#### Materiál a suroviny

| kód | kategorie |
|---|---|
| MAT-01 | Kovy a hutní materiál |
| MAT-02 | Chemické látky a přípravky |
| MAT-03 | Plasty, pryž a kompozity |
| MAT-04 | Papír, obaly a obalové materiály |
| MAT-05 | Stavební hmoty a nekovové materiály |
| MAT-06 | Textil, oděvy a OOPP |
| MAT-07 | Elektronické a elektrotechnické komponenty |
| MAT-08 | Potraviny a nápoje |
| MAT-09 | Zemědělské a lesní suroviny |
| MAT-10 | Nerostné suroviny a těžba |
| MAT-11 | Dřevo a výrobky ze dřeva |

#### Nezařazeno

| kód | kategorie |
|---|---|
| XXX-00 | Nezařazeno – nutné ruční doplnění |

#### Obchod

| kód | kategorie |
|---|---|
| OBC-01 | Velkoobchod a distribuce |
| OBC-02 | Maloobchod a drobný nákup |
| OBC-03 | Prodej a servis motorových vozidel |

#### Odpady a životní prostředí

| kód | kategorie |
|---|---|
| ODP-01 | Odpadové hospodářství |
| ODP-02 | Skartace a likvidace nosičů dat |
| ODP-03 | Sanace a environmentální služby |

#### Ostatní

| kód | kategorie |
|---|---|
| OST-01 | Kultura, sport a volný čas |
| OST-02 | Ostatní osobní a podpůrné služby |

#### Profesní služby

| kód | kategorie |
|---|---|
| PRO-01 | Právní služby |
| PRO-02 | Účetní a daňové služby |
| PRO-03 | Audit a assurance |
| PRO-04 | Manažerské a procesní poradenství |
| PRO-05 | Inženýring, projekce a architektura |
| PRO-06 | Certifikace, zkušebnictví a inspekce |
| PRO-07 | Výzkum a vývoj |
| PRO-08 | Překlady, jazykové a redakční služby |
| PRO-09 | Ostatní profesní a technické služby |

#### Správa objektů a provoz

| kód | kategorie |
|---|---|
| FAC-01 | Úklidové služby |
| FAC-02 | Facility management |
| FAC-03 | Údržba budov a technických zařízení |
| FAC-04 | Stravování a catering |
| FAC-05 | Pronájem prostor a nemovitostí |
| FAC-06 | Kancelářské potřeby a drobné vybavení |
| FAC-07 | Nábytek a interiéry |
| FAC-08 | Ubytovací a cestovní služby |

#### Stavebnictví

| kód | kategorie |
|---|---|
| STA-01 | Pozemní stavby a investiční výstavba |
| STA-02 | Inženýrské stavitelství |
| STA-03 | Specializované stavební práce |
| STA-04 | Elektroinstalace a slaboproud |

#### Technologie a stroje

| kód | kategorie |
|---|---|
| TEC-01 | Výrobní stroje a zařízení |
| TEC-02 | Měřicí, řídicí a regulační technika (OT) |
| TEC-03 | Servis, opravy a instalace strojů |
| TEC-04 | Elektrická zařízení a pohony |
| TEC-05 | Dopravní prostředky a jejich díly |
| TEC-06 | Pronájem techniky a vozidel |
| TEC-07 | Kovové konstrukce a díly |

#### Veřejný a neziskový sektor

| kód | kategorie |
|---|---|
| VER-01 | Veřejná správa a státní instituce |
| VER-02 | Asociace, spolky a neziskové organizace |
| VER-03 | Vzdělávací instituce |

#### Zdravotnictví

| kód | kategorie |
|---|---|
| ZDR-01 | Zdravotní péče a pracovnělékařské služby |
| ZDR-02 | Laboratoře a diagnostika |
| ZDR-03 | Farmacie a zdravotnický materiál |
| ZDR-04 | Sociální služby |
| ZDR-05 | Veterinární služby |

</details>

## Přepínače

```
-o, --vystup SOUBOR     .xlsx nebo .csv (výchozí dodavatele_vystup.xlsx)
--kompakt               jen základní sloupce
--jen-id                jen dohledat IČO/registrační číslo, viz "Dohledání identifikátoru"
--export-nezarazene SOUBOR   export nekategorizovaných firem pro LLM chat, viz "Ruční zařazení"
--kategorie-mapa SOUBOR      aplikovat ruční zařazení (odpověď z LLM chatu) na výstup
--workers N             souběžné dotazy (výchozí 4)
--prodleva S            minimální odstup dotazů na jeden server (výchozí 0.25 s)
--pocet N               kolik kandidátů z rejstříku načíst (výchozí 30)
--prah-ok 0.90          skóre shody názvu pro automatické přijetí
--prah-overit 0.72      pod tímto skóre je záznam nenalezený
--vies                  ověřit DIČ v EU (pomalejší, jeden dotaz navíc na firmu)
--bez-ares/-sk/-fr/-sg/-tw/-de/-gb/-ro/-gleif/-edgar/-wikidata   vypnutí jednotlivých zdrojů
--pripravit-de-rejstrik   stáhnout/rozbalit lokální kopii německého Handelsregisteru a skončit
--pripravit-gb-rejstrik   stáhnout/naimportovat lokální kopii Companies House (UK) a skončit
--bez-gleif-popisy      nepřekládat kódy GLEIF (rejstřík, právní forma) na text - rychlejší
--cache SOUBOR          keš odpovědí (výchozí .dodavatele_cache.json.gz)
--sloupec NÁZEV         název sloupce se jménem firmy, když se neurčí sám
--oddelovac ;           oddělovač pro CSV výstup
--ua "..."              User-Agent; SEC vyžaduje kontaktní e-mail

--komparace SOUBOR      porovnat NACE se sloupcem, který někdo přidal do už
                        vygenerovaného výstupu (např. ruční/AI doplnění od
                        kolegy) - vyžaduje --komparace-sloupec, jen porovná
                        a skončí (žádné dohledávání)
--komparace-sloupec NÁZEV      název porovnávaného sloupce v --komparace souboru
--komparace-nas-sloupec NÁZEV  název našeho sloupce s NACE (výchozí: NACE)
--komparace-vystup SOUBOR      kam zapsat výsledek (výchozí: <--komparace>_komparace.<přípona>)

--de-gegenstand SOUBOR    doplnit "Gegenstand des Unternehmens" z handelsregister.de
                          pro německé firmy v už vygenerovaném výstupu (viz výše) -
                          sekvenční běh, ~4 min/firmu, jen doplní a skončí
--de-gegenstand-vystup SOUBOR  kam zapsat výsledek (výchozí: <--de-gegenstand>_gegenstand.<přípona>)

--pruvodce              spustit interaktivního průvodce (napovídá otázkami místo
                        přepínačů) - stane se i bez zadání žádných argumentů
```

## Poznámky k provozu

* **Keš** (`.dodavatele_cache.json.gz`) drží odpovědi rejstříků, takže opakovaný
  běh nad stejným seznamem je téměř okamžitý. Smažte ji, chcete-li čerstvá data.
* **Zatížení rejstříků** – výchozí nastavení (4 vlákna, 0,25 s na server) je
  ohleduplné. Při tisících firem spíš zvyšte `--prodleva`, než abyste přidávali
  vlákna.
* **User-Agent** – SEC EDGAR vyžaduje v hlavičce kontaktní e-mail. Nastavte
  `--ua "nazev-firmy/1.0 (vas@email.cz)"`, jinak může začít odmítat dotazy.
* Ověřujte řádky se stavem jiným než `OK` a kategorii `XXX-00`; skript je
  vypisuje na konci běhu.

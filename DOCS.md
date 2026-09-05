# Podrobná dokumentace

Referenční dokumentace k `dodavatele.py` – jak spustit a co dělá základní
běh je v [README.md](README.md), tady jsou detaily, edge case a kompletní
seznam přepínačů/kategorií.

**Obsah:**
- [Vstup](#vstup)
- [Výstup](#výstup)
- [Dohledání identifikátoru pro zahraniční firmy (--jen-id)](#dohledání-identifikátoru-pro-zahraniční-firmy---jen-id)
- [Ruční zařazení nekategorizovaných firem přes LLM chat (--export-nezarazene)](#ruční-zařazení-nekategorizovaných-firem-přes-llm-chat---export-nezarazene)
- [Plošné ověření kategorie přes LLM (--export-overeni)](#plošné-ověření-kategorie-přes-llm---export-overeni-jen-cli)
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

**Přesné číslo (IČO/DIČ) na vstupu může být samo o sobě špatně** – překlep,
špatně zkopírovaný řádek v tabulce apod. Pokud je na stejném řádku vyplněná
i adresa (ulice/PSČ/město) a jasně neodpovídá tomu, co se pod daným
IČO/DIČ v rejstříku skutečně najde, nástroj takovou shodu nebere jako
jistou `OK`, ale dá `OVERIT` s poznámkou a **zkusí to navíc dohledat i podle
jména a adresy** – u běžných jmen (typicky OSVČ) to dokáže samo najít
správnou osobu, i když číslo na vstupu patřilo někomu jinému stejného
jména. Bez zadané adresy tohle rozpoznat nejde – čím víc údajů dáte, tím
spolehlivější výsledek.

## Výstup

Sloupce podle zadání: `Jméno | Ulice | PSČ | Město | Země | IČO | DIČ`,
k tomu `Kód kategorie | Skupina | Kategorie dodavatele` a doplňkové sloupce
pro kontrolu (`--kompakt` je vypne):

* **Registrační číslo / Rejstřík** – u zahraničních firem národní registrační
  číslo (obdoba IČO, např. `HRB 719915` u Německa, `1803-01-018771` u Japonska)
  a jméno rejstříku, u kterého je vedeno.
* **NACE (všechny)** – všechny zapsané obory dané firmy z rejstříku
  (čárkou oddělený seznam kódů) – jediný sloupec s NACE ve výstupu; z něj
  se interně vybírá kód pro automatické zařazení do kategorie (viz
  "Taxonomie kategorií" níže), samotný "vybraný hlavní kód" se ale
  zvlášť nezobrazuje, aby nepůsobil jako jistota, kterou často není.
* **NACE - zdroj** – rozlišuje skutečný NACE z rejstříku (ARES, INSEE) od
  odhadu z oboru na Wikidatech, který je méně přesný.
* **NACE (LLM)** – vyplní se jen po použití `--nace-mapa`/`--overeni-mapa`
  (viz "Ruční zařazení" níže) - NACE kód, který k firmě dohledal člověk/LLM
  chat, vedle zapsaných kódů z rejstříku ve sloupci NACE (všechny).
* **Klasifikace (US NAICS)** – u amerických dodavatelů severoamerická obdoba
  NACE (NACE se u USA jen odhaduje pro účely vlastní taxonomie).

XLSX má druhý list **Číselník kategorií** s celou taxonomií a počtem
dodavatelů v každé kategorii, a třetí list **Číselník NACE** s názvy všech
NACE divizí (2místné kódy) - aby šlo kód ze sloupce NACE (všechny) dohledat
v plném znění i bez opuštění sešitu (pro klienta apod.). Jde jen o hlavní
divize, ne o kompletní podrobnou nomenklaturu (tisíce 4-6místných tříd).

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

#### Dodavatel je OSVČ (fyzická osoba) zadaná jen jménem

Jméno fyzické osoby není jednoznačný identifikátor tak jako název firmy —
běžné jméno typu "Jan Novák" má v ARES bez legrace stovky záznamů různých
lidí. Pokud vstup neobsahuje adresu ani IČO, nástroj takovou shodu (rozpozná
ji podle kódu právní formy ARES 100–108, tedy fyzická osoba podnikající)
**nikdy nevyhodnotí jako jistou `OK`**, i kdyby šlo o jediného nalezeného
kandidáta — dostane `OVERIT` s poznámkou "nalezeno jen podle jména osoby
(OSVC) bez adresy k rozlišení". Jiná stejnojmenná osoba totiž mohla zůstat
mimo načtených kandidátů (`--pocet`) a nikdy se s ní neporovnávalo.

**Řešení:** doplňte do vstupu **IČO** (nejjistější) nebo aspoň **adresu**
(město/PSČ) — u firem to adresa jen zpřesňuje, u OSVČ je to prakticky
jediný způsob, jak zaručit správnou osobu.

**Pozor ale i s doplněnou adresou:** pokud v ARES existuje víc stejnojmenných
OSVČ a zadaná adresa **nesedí na žádnou z nich** (ani na tu, kterou by
nástroj jinak vybral jako nejlepší), nástroj to nevezme jako "aspoň nějaká
shoda" — vrátí rovnou `NENALEZENO` bez propsání dat. Přesná kombinace
jméno+adresa totiž mezi nalezenými kandidáty vůbec neexistuje, takže by šlo
jen o tipování, která z několika stejnojmenných osob je ta správná — a cizí
IČO/adresa v datech by byla horší než prázdný řádek. Tohle rozlišení platí
jen pro OSVČ (fyzické osoby) — u firem se stejným jménem a nesedící adresou
zůstává chování beze změny (`VYBRANO`/`OVERIT`), protože název firmy je sám
o sobě mnohem silnější identifikátor než jméno člověka.

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
  založení, ne jako skutečnou náplň podnikání; jiné firmy jsou naopak čistě
  majetková/holdingová entita v rámci skupiny, kde je "pronájem" fakticky
  správný údaj, i když název firmy evokuje jiný byznys operující firmy ve
  skupině). Nástroj takový kód nepřehazuje za jiný ani nehádá z názvu firmy
  (obojí by bylo hádání bez záruky) — pokud má firma zapsaný i jiný kód,
  doplní do **Poznámky** upozornění a odkáže na sloupec **NACE (všechny)**
  k ručnímu porovnání. Pokud je to **jediný** zapsaný kód, nemá se s čím
  porovnat — řádek dostane stav `OVERIT` a firma se automaticky zařadí i do
  `--export-nezarazene` (viz níže), i když formálně kategorii má.

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

Firmy, které nemají spolehlivý obor, skončí buď v `XXX-00 Nezařazeno` (žádný
NACE ani obor z Wikidat), nebo dostanou kategorii ze samotného obecného/
podpůrného NACE kódu, ale se stavem `OVERIT` (viz "Firma má v ARES víc oborů
podnikání" výše — nástroj kategorii záměrně nehádá z ničeho nepodloženého,
viz [Taxonomie kategorií](#taxonomie-kategorií)). Pokud máte přístup
k firemnímu LLM chatu (MS Copilot, ChatGPT…) jen jako k webovému rozhraní,
bez API klíče, dá se k doplnění použít stejný dvoukrokový princip jako
u `--jen-id`:

```bash
# 1. krok - normální běh + export nekategorizovaných/nejistých firem pro chat
python3 dodavatele.py vstup.csv -o vystup.xlsx --export-nezarazene nezarazene.txt

# --> obsah nezarazene.txt vložit do Copilotu/ChatGPT, odpověď uložit
#     jako CSV (Název;NACE kód;Zdůvodnění), např. odpoved.csv

# 2. krok - stejný běh znovu, tentokrát s doplněným NACE
python3 dodavatele.py vstup.csv -o vystup.xlsx --nace-mapa odpoved.csv
```

**Proč se LLM ptáme na NACE, ne rovnou na naši kategorii:** aby LLM správně
vybral jednu z ~95 vlastních kategorií, musel by napřed pochopit celou naši
taxonomii jen z jednoho výpisu v promptu - reálný prostor pro chybu.
Standardní NACE klasifikaci LLM naopak dobře zná ze svých trénovacích dat,
takže dohledání skutečného oboru je pro něj spolehlivější úkol. Kategorii
z jeho odpovědi pak dopočítá **stejný ověřený mechanismus**
(`taxonomie.zarad()`), jaký se používá pro skutečný NACE z rejstříku - LLM
tak nikdy sám nevymýšlí kód naší kategorie, jen NACE.

`--export-nezarazene` vypíše seznam takových firem (se zemí, adresou a - u
firem jen s podpůrným NACE - i tím stávajícím kódem pro kontext) do
textového souboru připraveného na vložení do chatu i s instrukcí a
požadovaným formátem odpovědi. `--nace-mapa` pak načte odpověď z chatu
(soubor `Název;NACE[;…]`), pro každou firmu dopočítá kategorii přes
`taxonomie.zarad()` a zapíše i samotný LLM kód do nového sloupce
**NACE (LLM)** - takže je vždy vidět, jaký kód LLM navrhl, vedle zapsaných
kódů z rejstříku ve sloupci **NACE (všechny)**. Sloupec **Zařazeno podle**
dostane hodnotu `rucne (LLM pres NACE)`, takže je vždy jasné, co je ověřený
fakt z rejstříku a co ruční/AI odhad ke kontrole. Řádky, kde LLM napsal
"neznámo" (nebo cokoli bez rozpoznatelných číslic), zůstanou beze změny.
Na rozdíl od `--overeni-mapa` (viz níže) se `--nace-mapa` aplikuje jen na
firmy, které už `_potrebuje_llm_pomoc` označil za nejisté - u firem se
spolehlivým NACE nic nemění.

Protože teď máte v jednom souboru vedle sebe **NACE (všechny)** (rejstřík) i
**NACE (LLM)**, jde je rovnou porovnat stejným nástrojem jako cizí
zdroj - viz `--komparace` níže:

```bash
python3 dodavatele.py --komparace vystup.xlsx --komparace-sloupec "NACE (LLM)"
```

Žádná nová závislost, API klíč ani automatizace prohlížeče — jen soubor
na kopírování mezi nástrojem a chatem, který už máte k dispozici.

## Plošné ověření kategorie přes LLM (--export-overeni), jen CLI

`--export-nezarazene` výše řeší jen firmy, kde nástroj sám pozná, že si
není jistý (žádný NACE, nebo jen obecný/podpůrný kód jako pronájem či
nespecializovaný velkoobchod). Existuje ale i opačný, zákeřnější případ:
firma má v rejstříku zapsaný **specifický, důvěryhodně vypadající** NACE
kód, který je ale věcně zastaralý nebo špatný (např. firma na personalizované
reklamní předměty se zapsanou "hlavní činností" výroba oděvů, protože tak
kdysi začínala) - to žádná heuristika nepozná, protože kód sám o sobě
nevypadá podezřele.

`--export-overeni` řeší přesně tohle - na rozdíl od `--export-nezarazene`
exportuje **všechny** dodavatele (ne jen nejisté), a u každého uvede **všechny**
jeho zapsané obory (sloupec NACE (všechny)), ne jen jeden. LLM tak dostane
víc materiálu k rozhodnutí a má instrukci brát zapsané kódy jen jako nápovědu,
ne jako jistotu - a navrhnout jiný kód, pokud podle vlastní znalosti firmy
žádný z nich neodpovídá skutečnosti:

```bash
# 1. krok - normální běh + plošný export VŠECH firem k LLM overeni
python3 dodavatele.py vstup.csv -o vystup.xlsx --export-overeni overeni.txt

# u velkych seznamu (stovky+ firem) rozdelit do davek po N firmach,
# aby se kazda davka pohodlne vesla do jedne zpravy v chatu:
python3 dodavatele.py vstup.csv -o vystup.xlsx --export-overeni overeni.txt --export-davka 700
# --> vznikne overeni_01.txt, overeni_02.txt, ... - kazdy vlozit do chatu zvlast

# 2. krok - odpovedi (jeden soubor na davku) aplikovat zpet
python3 dodavatele.py vstup.csv -o vystup.xlsx --overeni-mapa odpoved_01.csv odpoved_02.csv
```

**Zásadní rozdíl oproti `--nace-mapa`:** `--overeni-mapa` přepíše kategorii
u **každé** firmy, pro kterou má odpověď - i tam, kde měl nástroj `OK` se
specifickým kódem. To je záměr (jinak by se skryté chyby jako výše nikdy
neodhalily), ale znamená to, že špatná/nejistá LLM odpověď může přepsat
i dřív správnou kategorii - proto je tenhle nástroj **jen v CLI**, ne
v desktopové appce, a hodí se hlavně tam, kde má smysl investovat čas do
plošné ruční/AI kontroly (např. seznam kritických dodavatelů), ne jako
výchozí krok pro každý běh. Mechanismus odvození kategorie z LLM navrženého
NACE je stejný jako u `--nace-mapa` (`taxonomie.zarad()`) - LLM tak i tady
nikdy nevymýšlí kód naší kategorie přímo, jen standardní NACE.

## Komparace NACE s externím zdrojem (--komparace)

Když někdo jiný (kolega, AI nástroj) doplní vlastní odhad NACE přímo do už
vygenerovaného výstupu tohoto nástroje (přidá si do souboru svůj sloupec),
jde jeho sloupec porovnat s naším:

```bash
python3 dodavatele.py --komparace vystup_s_kolegovym_sloupcem.xlsx \
    --komparace-sloupec "Kolegův NACE"
```

Ukázkový soubor `vzor_komparace.csv` (sloupce `Jméno;Země;NACE (všechny);Komparace`)
demonstruje typický výsledek – kolegův/AI odhad se často trefí jen na
hrubou kategorii nebo úplně mine:

```bash
python3 dodavatele.py --komparace vzor_komparace.csv --komparace-sloupec Komparace
```

Řádky se berou 1:1 podle pozice (žádné párování podle jména/IČO — soubor je
už náš vlastní výstup jen s přidaným sloupcem navíc). Shoda se počítá na
úrovni **NACE divize** (první 2 číslice) — odpouští drobné rozdíly
v podrobnosti mezi dvěma různými zdroji, ne přesnou shodu celého kódu.
Výstup (výchozí `<--komparace>_komparace.<přípona>`) obsahuje všechny
původní sloupce plus nový sloupec **Shoda NACE (divize)** (ANO/NE/prázdné,
pokud jedné straně kód chybí) a na stderr vypíše souhrn — kolik řádků je
srovnatelných a jaké je procento shody.

Kolegův/AI sloupec nemusí být "holý" kód - běžně jde o text jako
`26.11 Výroba počítačů... + 46.52 Velkoobchod s počítači` (tečkovaná
notace, popis, i víc kódů v jedné buňce najednou). Nástroj z takového textu
vytáhne všechny rozpoznatelné kódy a shodu bere jako "aspoň jedna společná
divize" - viz `vzor_komparace.csv` pro příklad přesně v tomhle formátu.

## Zdroje dat

| zdroj | pokrytí | co dodá |
|---|---|---|
| **ARES** (ares.gov.cz) | ČR, kompletní | název, adresa, IČO, DIČ, NACE včetně *převažující činnosti*; u vymazaných firem datum a důvod výmazu (zdroj VR) |
| **RPO SR** (statistics.sk) | SR, kompletní | název, adresa, IČO, SK NACE (hlavní činnost), právní forma |
| **INSEE/INPI** (recherche-entreprises.api.gouv.fr) | Francie, kompletní | název, adresa, SIREN, NAF → NACE, DIČ (dopočteno) |
| **ACRA** (data.gov.sg) | Singapur, kompletní | název, adresa, UEN, stav (aktivní/vymazáno) |
| **GCIS** (data.gcis.nat.gov.tw) | Tchaj-wan, kompletní | název, adresa, daňové číslo, datum vzniku |
| **Handelsregister** (lokální kopie, `--pripravit-de-rejstrik`) | Německo, ~5,3 mil. firem (data k 2019) | název, adresa, číslo zápisu (HRA/HRB/…), právní forma, stav (aktivní/vymazáno) |
| **OpenRegister.de** (`--de-api-klic`, placené API) | Německo, živá data | to samé co Handelsregister + skutečný obor činnosti (WZ2025 → NACE) a text předmětu podnikání |
| **Companies House** (lokální kopie, `--pripravit-gb-rejstrik`) | Velká Británie, ~5 mil. firem (měsíční aktualizace) | název, adresa, číslo firmy, právní forma, SIC 2007 → NACE, stav |
| **Scoris** (`--scoris-api-klic`, placené API) | Švédsko, Finsko, Estonsko, Lotyšsko, Litva, živá data | název, adresa, registrační číslo, DIČ, právní forma, skutečný NACE |
| **GLEIF** (api.gleif.org) | svět, firmy s LEI (většina větších/kotovaných firem) | název (i v původním jazyce), adresa, národní registrační číslo, právní forma |
| **SEC EDGAR** (sec.gov) | USA, firmy registrované u SEC | název, adresa, SIC → NACE i NAICS, CIK |
| **Wikidata** | velké nadnárodní firmy | obor činnosti (viz níže), EU DIČ, LEI, sídlo |
| **VIES** (`--vies`) | EU | ověření platnosti DIČ |

Vše bez API klíče a bez registrace, kromě OpenRegister.de a Scoris
(volitelné, placené, viz "Skutečný NACE u německých firem" a "Skutečný
NACE ve Švédsku/Finsku/Pobaltí" níže).

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

Hlavní limit lokální kopie ale **není stáří dat, ale to, že Handelsregister
jako takový obor činnosti vůbec nevede** - ani v aktuální podobě. Pro
skutečný NACE u německých firem je proto potřeba jiný zdroj, viz dále.

#### Skutečný NACE u německých firem - OpenRegister.de (placené API)

Handelsregister (živý ani lokální) obor činnosti neobsahuje vůbec - u
Německa proto bez dalšího zdroje zbývá jen odhad přes Wikidata (jen velké/
známé firmy). **OpenRegister.de** je komerční API třetí strany, které vede
skutečnou klasifikaci **WZ2025** (německá obdoba NACE, stejné číslování)
a text předmětu podnikání ("Gegenstand") přímo z živého Handelsregisteru:

```bash
python3 dodavatele.py vstup.csv -o vystup.xlsx --de-api-klic sk_live_...
# nebo přes proměnnou prostředí, aby klíč nebyl vidět v historii příkazů:
export OPENREGISTER_API_KEY=sk_live_...
python3 dodavatele.py vstup.csv -o vystup.xlsx
```

Když je klíč zadaný, OpenRegister.de se pro německé firmy použije **místo**
lokální kopie Handelsregisteru (`--bez-de`/lokální DB se tím pádem
ignorují) - dá totéž co lokální kopie (jméno, adresa, číslo zápisu, právní
forma) navíc se skutečným NACE. Bez klíče se chování nemění - firmy z DE
se hledají jako dřív (lokální kopie, pak GLEIF + Wikidata).

**Klíč se nikdy neukládá do repozitáře ani do keše** - předává se jen za
běhu (parametr, nebo proměnná prostředí), na disk se dostane jedině v keši
odpovědí samotného rejstříku (`.dodavatele_cache.json.gz`), ne v hlavičce
dotazu. Nový účet dostává zdarma 500 kreditů/měsíc bez nutnosti platební
karty (vyhledání jménem 1 kredit, detail firmy se skutečným NACE 10
kreditů) - to stačí na běžné dávky řádu desítek německých firem.

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

### Skutečný NACE ve Švédsku/Finsku/Pobaltí - Scoris (placené API)

Stejný problém jako u Německa - bez skutečného zdroje oboru činnosti se SE/FI/
EE/LV/LT firmy kategorizují jen přes Wikidata (jen velké/známé firmy).
**Scoris** (scoris.eu) je komerční API třetí strany se skutečnou klasifikací
NACE přímo z národních rejstříků těchto pěti zemí (plus UK, tam už ale máme
lepší bezplatný zdroj - Companies House - takže se přes Scoris nepoužívá):

```bash
python3 dodavatele.py vstup.csv -o vystup.xlsx --scoris-api-klic klic...
# nebo pres promennou prostredi:
export SCORIS_API_KEY=klic...
python3 dodavatele.py vstup.csv -o vystup.xlsx
```

**Pozor na dvě různé služby stejného jména** - `scoris.eu` (SE/FI/EE/LV/LT,
placené přes `--scoris-api-klic`) a `scoris.lt` (jen Litva, jiný účet/klíč,
zatím nezapojeno) jsou dvě samostatná API se stejným původem, ale jiným
klíčem i jinou doménou - klíč z jednoho na druhém nefunguje.

Vyhledávání jménem samo o sobě adresu ani NACE nevrací (jen jméno, zemi
a registrační číslo) - ty se dotáhnou až pro jednoho, už vybraného
nejlepšího kandidáta, aby se kredity nemrhaly na kandidáty, kteří nakonec
nejsou vybraní. Free tarif dává 100 kreditů (vyhledání zdarma, detail firmy
se skutečným NACE 1 kredit) - bez karty.

**Klíč se nikdy neukládá do repozitáře ani do keše** - stejné pravidlo jako
u OpenRegister.de výše.

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
  `NENALEZENO`/`OVERIT` a ručním doplněním.
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
| DE | Handelsregister, lokální kopie (`--pripravit-de-rejstrik`, data k 2019) - bez NACE; se `--de-api-klic` navíc skutečný NACE (OpenRegister.de, placené) | GLEIF + Wikidata |
| GB | Companies House, lokální kopie (`--pripravit-gb-rejstrik`, měsíční aktualizace) | GLEIF + Wikidata |
| SE, FI, EE, LV, LT | se `--scoris-api-klic` skutečný NACE (Scoris, placené); bez klíče | GLEIF + Wikidata |
| NL, AT, BE, IT, ES, HU, IE, BG, PL, RO | – | GLEIF + Wikidata |
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
* **RO** (ANAF) – oficiální bezklíčové API `webservicesp.anaf.ro` umí podle
  zadaného CUI (DIČ) vrátit i CAEN kód (rumunský NACE) a adresu - nejde ale
  hledat podle jména, jen doplnit obor k už známému DIČ. Zkoušená
  implementace navíc nešla z tohoto prostředí vůbec ověřit (endpoint vracel
  404, patrně geo/WAF blokace) - zatím nezapojeno, dokud to nepůjde
  spolehlivě otestovat.
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
--export-nezarazene SOUBOR   export nekategorizovaných/nejistých firem pro LLM chat, viz "Ruční zařazení"
--nace-mapa SOUBOR      aplikovat rucne/LLM dohledany NACE (odpověď z LLM chatu) na výstup
--export-overeni SOUBOR   [jen CLI] plošný export VŠECH firem pro LLM ověření, viz "Plošné ověření kategorie"
--export-davka N        rozdělit --export-overeni/--export-nezarazene do víc souborů po N firmách
--overeni-mapa SOUBOR [SOUBOR...]   aplikovat odpovědi na --export-overeni (i vícero souborů najednou)
--workers N             souběžné dotazy (výchozí 4)
--prodleva S            minimální odstup dotazů na jeden server (výchozí 0.25 s)
--pocet N               kolik kandidátů z rejstříku načíst (výchozí 30)
--prah-ok 0.90          skóre shody názvu pro automatické přijetí
--prah-overit 0.72      pod tímto skóre je záznam nenalezený
--vies                  ověřit DIČ v EU (pomalejší, jeden dotaz navíc na firmu)
--bez-ares/-sk/-fr/-sg/-tw/-de/-gb/-gleif/-edgar/-wikidata   vypnutí jednotlivých zdrojů
--pripravit-de-rejstrik   stáhnout/rozbalit lokální kopii německého Handelsregisteru a skončit
--de-api-klic KLIC      API klíč OpenRegister.de - skutečný NACE (WZ2025) pro
                        německé firmy, viz "Skutečný NACE u německých firem"
                        (nebo proměnná prostředí OPENREGISTER_API_KEY)
--pripravit-gb-rejstrik   stáhnout/naimportovat lokální kopii Companies House (UK) a skončit
--scoris-api-klic KLIC  API klíč Scoris - skutečný NACE pro SE/FI/EE/LV/LT,
                        viz "Skutečný NACE ve Švédsku/Finsku/Pobaltí"
                        (nebo proměnná prostředí SCORIS_API_KEY)
--bez-gleif-popisy      nepřekládat kódy GLEIF (rejstřík, právní forma) na text - rychlejší
--cache SOUBOR          keš odpovědí (výchozí .dodavatele_cache.json.gz)
--obnovit-nenalezene SOUBOR   dřívější výstup (bez --kompakt) - firmy s minulým
                        stavem NENALEZENO/OVERIT/CHYBA se vynuceně znovu
                        dotáží (obejde keš jen pro ně), viz "Poznámky k provozu"
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
```

## Poznámky k provozu

* **Keš** (`.dodavatele_cache.json.gz`) drží odpovědi rejstříků, takže opakovaný
  běh nad stejným seznamem je téměř okamžitý. Je trvalá – i výsledek "nic
  nenalezeno" zůstává uložený navždy, dokud keš nesmažete, takže firma, která
  se mezitím v rejstříku objevila, by se stejnou keší pořád vracela jako
  nenalezená.
* **Obnova jen nenalezených firem** (`--obnovit-nenalezene DŘÍVĚJŠÍ_VÝSTUP`) –
  řešení právě pro tenhle případ. Vezme dřívější (ne `--kompakt`) výstup,
  najde v něm firmy se stavem `NENALEZENO`/`OVERIT`/`CHYBA` a jen pro ně
  vynutí čerstvý dotaz (obejde keš), ostatní firmy zůstanou beze změny a
  rychle se vezmou z keše – nemusí se tak mazat a přepočítávat celý seznam.
* **Zatížení rejstříků** – výchozí nastavení (4 vlákna, 0,25 s na server) je
  ohleduplné. Při tisících firem spíš zvyšte `--prodleva`, než abyste přidávali
  vlákna.
* **User-Agent** – SEC EDGAR vyžaduje v hlavičce kontaktní e-mail. Nastavte
  `--ua "nazev-firmy/1.0 (vas@email.cz)"`, jinak může začít odmítat dotazy.
* Ověřujte řádky se stavem jiným než `OK` a kategorii `XXX-00`; skript je
  vypisuje na konci běhu.

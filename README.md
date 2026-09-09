# Dodavatelé – podklad pro audit dle ISO/IEC 27001

Vezme seznam kreditorů z účetnictví a připraví z něj evidenci dodavatelů pro
audit dodavatelských vztahů: kdo dodavatel doopravdy je, čím se zabývá, jestli
má vazbu na ICT a jak je pro firmu kritický.

Nástroj dělá jen tu část, která jde udělat spolehlivě a strojově — **dohledá
identitu ve veřejných rejstřících a posbírá podklady**. Zařazení do kategorie
dělá LLM v chatu, protože „co firma reálně dodává" se z rejstříku vyčíst nedá.
Vztah k vaší firmě a smluvní závazky doplníte v Excelu vy.

## Použití

```bash
pip install openpyxl

python3 dodavatele.py kreditori.xlsx     # 1. běh – dohledá a napíše dávky
#   → vložte davky/davka_01.txt … do ChatGPT/Copilotu
#   → odpovědi uložte jako CSV do složky odpovedi/
python3 dodavatele.py odpovedi/          # 2. běh – doplní je do Excelu
```

Žádné přepínače. První argument je soubor (dohledání) nebo složka (doplnění).

Prompt v dávce si o formát odpovědi řekne sám — chat vrátí CSV s řádky
`ID;Název firmy;Kód kategorie;Co dodává;Jistota`. Soubor uložte do `odpovedi/`
pod libovolným jménem. Podle ID **i názvu** se odpověď páruje zpět: kdyby chat
posunul číslování, řádky se zahodí a nástroj to nahlásí, místo aby dodavateli
tiše přiřadil cizí kategorii.

**Vstup** (CSV / XLSX / TXT): povinný je jen název. Rozpoznají se sloupce
`Kreditor`, `Název`, `Adresa`, `IČO`, `DIČ`, `Země`, `Částka` — česky, anglicky
i německy. Duplicity podle názvu a IČO se slučují.

| co dodáte | co to udělá |
|---|---|
| `Kreditor` / `Kód kreditora` | identifikátor z účetnictví projde do prvního sloupce Excelu — evidence pak jde spárovat zpátky |
| `IČO` | ověřená identita z ARES / RPO SR, včetně NACE a předmětu podnikání |
| `DIČ` | ověřená identita přes VIES — jediná bezplatná cesta u DE, NL, AT… |
| `Adresa` | rozliší firmy stejného jména, ověří nalezený web |
| `Částka` | rozpozná se, ale do evidence nevstupuje — kritičnost se z objemu záměrně nepočítá |

Samotná hlavička `Kreditor` je dvojznačná — bývá v ní jméno i číslo. Když je
vedle ní sloupec `Název`, bere se `Kreditor` jako identifikátor; když ne, jako
název firmy. Bez identifikátoru se do sloupce Kreditor doplní pořadové číslo,
pod kterým firma vystupuje i v dávkách pro chat a na listu Podklady.

## Odkud se bere identita

| zdroj | co dá | pro koho |
|---|---|---|
| **ARES** | úřední název, adresa, CZ-NACE, předmět podnikání | ČR |
| **RPO SR** | úřední název, adresa, SK-NACE | Slovensko |
| **VIES** | úřední název a adresa podle DIČ | všechny státy EU |
| **Wikidata + Wikipedie** | oficiální web, obor, popis | kdokoli, kdo tam je |
| **web firmy** | `<title>`, meta popis, `<h1>`, kus textu | kdokoli s webem |

Vše bez API klíče, bez registrace, čistý Python (`urllib`) — běží i na Windows
bez WSL a Dockeru. Vše se kešuje, takže druhý běh nejde na síť.

Sloupec **Jistota identity** říká, čemu věřit: `rejstřík` (podle IČO nebo přesné
shody jména) > `VIES (DIČ)` > `podle názvu` > `neověřeno`. Země bez veřejného
rejstříku zdarma (US, CH, JP, HK, SG, GB…) skončí jako `neověřeno` — o zařazení
tam rozhoduje web a znalosti LLM.

Záměrně **nepoužíváme GLEIF ani jiné fuzzy hledání jmenem přes hranice**: u
německých firem vracelo zahraniční dcery a holdingy místo provozní firmy
(Festo → Kanada, Rittal → Belgie). Špatně ověřená identita je pro audit horší
než žádná, protože se pozná až pozdě.

## Výstup: `dodavatele.xlsx`

Sešit je pracovní nástroj pro klienta, ne export. Každý list začíná kartou,
která říká, co na něm je a jak se používá; první list je košilka s postupem
práce a legendou barev.

| list | obsah |
|---|---|
| **Úvod** | košilka — k čemu sešit je, jak s ním pracovat, co znamenají barvy |
| **Dodavatelé** | hlavní tabulka — jeden řádek na dodavatele |
| **Číselník** | 82 kategorií v 12 skupinách + ICT příznak (zdroj pro vzorce) |
| **Souhrn** | kolik je ICT, kolik kritických, co ještě chybí vyplnit |
| **Podklady** | co se o firmě našlo a jak dohledávání dopadlo — proč LLM rozhodl takhle |
| **Metodika** | co znamená který sloupec a jeho vazba na ISO/IEC 27001 |

### OSVČ, u kterých není z čeho vyjít

Fyzická osoba není v obchodním rejstříku, takže u ní neexistuje zapsaný
předmět podnikání — a to bývá jediný konkrétní podklad k tomu, čím se
dodavatel zabývá. Když k ní nástroj nenajde ani NACE, web nebo Wikidata,
zbyde jméno člověka. To o oboru neříká nic a jazykový model by z něj vyrobil
dohad, který v sešitu vypadá jako zjištěný obor.

Takový dodavatel se proto **do dávky pro chat vůbec neposílá** a v sešitu
dostane od nástroje kód `XXX-01` — *OSVČ – obor nezjištěn*. Na listu Podklady
je u něj poznámka proč a Souhrn takové řádky počítá zvlášť, aby bylo vidět,
kolik jich čeká na ruční doplnění. Zařadit ho musíte podle toho, co pro vás
opravdu dělá.

Pozná se to podle právní formy z ARES (kódy 100–109). U slovenských
dodavatelů z RPO se právní forma vrací textem, takže se tahle značka
neuplatní — ti skončí jako `XXX-00`.

Excel je **živý dokument, ne jen export**. Kategorie, skupina a ICT relevance
nejsou zapsané hodnoty, ale `VLOOKUP` do Číselníku — když opravíte kód
kategorie, přepočítá se název, skupina, ICT příznak, kritičnost i režim dle
ISO 27001.

### Co doplníte ručně (žlutě)

Kritičnost stojí na dvou otázkách — **kam dodavatel vidí** a **jak snadno ho
nahradíte**. Obojí je rozbalovací seznam:

| Přístup k datům/systémům | znamená |
|---|---|
| 1. Žádný přístup | nevidí naše informace a nechodí do prostor |
| 2. Fyzický vstup do prostor | úklid, servis, ostraha, stěhování (A.7.2) |
| 3. Má naše data u sebe | dostane od nás exporty, dokumenty nebo osobní údaje, nebo je pro nás zpracovává ve svém prostředí — účetní, advokát, mzdová kancelář, cloud či SaaS (A.5.14, A.5.23) |
| 4. Přístup do našich systémů | má účet v našich aplikacích nebo se do nich připojuje přes API či vzdálený přístup |
| 5. Privilegovaná správa systémů | administrátorská práva, vzdálená správa — spravuje nám je, ne v nich jen pracuje (A.8.2) |

Je to **žebříček, ne výčet: vybírá se nejvyšší stupeň, který platí.** Vyšší
v sobě obsahuje nižší, takže se nikdo nemusí rozhodovat mezi překrývajícími se
možnostmi — jen kam až dodavatel dohlédne. Kdo chodí do prostor a zároveň nám
spravuje servery, patří na stupeň 5; fyzický vstup je u něj to menší z obojího.

Kritičnost zvedají stupně 3 a výš. Stupeň 5 je kritický vždycky, stupně 3–4
až u ICT dodávky.

| Nahraditelnost | znamená |
|---|---|
| 1. Běžně nahraditelný | na trhu je víc alternativ, přechod je otázka týdnů |
| 2. Obtížně nahraditelný | náhrada existuje, ale znamená migraci dat a měsíce |
| 3. Kritická závislost | prakticky nenahraditelný, výpadek zastaví provoz |

Taky stupnice, ale **jiného druhu než Přístup**: nejsou to příčky, které se
sčítají, ale tři vzájemně se vylučující stavy — vybírá se ten, který sedí, ne
nejvyšší, který platí. Ptejte se, co by se stalo, kdyby dodavatel ze dne na den
skončil, ne jak jste s ním spokojení. Stupeň 3 dělá dodavatele `KRITICKÝM` sám
o sobě, i bez jakéhokoli přístupu k datům.

Na konci řádku je revizní blok pro klienta — **Vlastník vztahu**, **Datum
posouzení**, **Datum příštího přezkoumání** a **Poznámka**. U dodavatele, který
vyjde jako `KRITICKÝ`, se chybějící vlastník nebo datum posouzení podbarví
červeně; červeně se ukáže i přezkoumání po termínu.

### Co z toho spočítají vzorce

**Kritičnost** — `KRITICKÝ`, když nám dodavatel spravuje systémy (stupeň 5),
nebo je na něm kritická závislost, nebo jde o ICT dodávku a dodavatel je přitom
aspoň na stupni 3. `VÝZNAMNÝ` při ICT vazbě, stupni 3 a výš nebo obtížné
nahraditelnosti. Jinak `BĚŽNÝ`.

Rozhoduje tedy **přístup a závislost, ne cena** — levný dodavatel se vzdálenou
správou serverů je rizikovější než drahý dodavatel kancelářských potřeb. Objem
fakturace ze vstupu se proto do evidence vůbec nepřenáší.

**Režim dle ISO 27001** — co je u dodavatele potřeba (prověření, bezpečnostní
požadavky ve smlouvě, DPA, právo auditu, monitoring). Přepočítá se s každou
změnou vstupů.

### Testy

```bash
python3 test_vzorce.py    # logika vzorců v Excelu (bez Excelu je nespustíme)
python3 test_zdroje.py    # rozpoznání sloupců vstupu, názvy, domény, stránky
python3 nahled.py         # sešit z ukázkových dat do test_vystup/ (bez sítě)
```

Všechno běží bez sítě. Testy hlídají tiché chyby, které by se v auditu poznaly pozdě —
například že „ESET" a „RESET" nesmí splynout, nebo že web uhodnutý z názvu
se nepřijme, pokud vede na parkovanou doménu.

## Soubory

| soubor | co dělá |
|---|---|
| `dodavatele.py` | CLI, čtení vstupu, orchestrace obou běhů |
| `zdroje.py` | ARES, RPO SR, VIES, Wikidata, web + keš |
| `vystup.py` | dávky pro LLM, čtení odpovědí, Excel se vzorci |
| `taxonomie.py` | čtení číselníku |
| `taxonomie_data.json` | číselník kategorií a ICT relevance |
| `nahled.py` | sešit z ukázkových dat — na posouzení podoby výstupu |
| `test_vzorce.py` | kontrola logiky vzorců a sazby sešitu |
| `test_zdroje.py` | kontrola rozpoznání sloupců, názvů a ověřování webu |
| `TAXONOMIE.md` | proč je číselník členěný takhle |

Keš je v profilu uživatele (`~/.cache/dodavatele/`), mezistav v
`.dodavatele-stav.json` vedle výstupu.

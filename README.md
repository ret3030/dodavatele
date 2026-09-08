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

**Vstup** (CSV / XLSX / TXT): povinný je jen název. Rozpoznají se sloupce
`Název`, `Adresa`, `IČO`, `DIČ`, `Země`, `Částka` — česky, anglicky i německy.
Duplicity podle názvu a IČO se slučují.

| co dodáte | co to udělá |
|---|---|
| `IČO` | ověřená identita z ARES / RPO SR, včetně NACE a předmětu podnikání |
| `DIČ` | ověřená identita přes VIES — jediná bezplatná cesta u DE, NL, AT… |
| `Adresa` | rozliší firmy stejného jména, ověří nalezený web |
| `Částka` | předvyplní objem v Excelu, nemusíte ho psát ručně |

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

| list | obsah |
|---|---|
| **Dodavatelé** | hlavní tabulka — jeden řádek na dodavatele |
| **Číselník** | 74 kategorií v 11 skupinách + ICT příznak (zdroj pro vzorce) |
| **Souhrn** | kolik je ICT, kolik kritických, jak dopadla identita |
| **Podklady** | co se o firmě našlo — dohledatelné, proč LLM rozhodl takhle |

Excel je **živý dokument, ne jen export**. Kategorie, skupina a ICT relevance
nejsou zapsané hodnoty, ale `VLOOKUP` do Číselníku — když opravíte kód
kategorie, přepočítá se název, skupina, ICT příznak, kritičnost i režim dle
ISO 27001.

### Co doplníte ručně (žlutě, s rozbalovacím seznamem)

| sloupec | hodnoty |
|---|---|
| Přístup k datům/systémům | žádný / fyzický / omezený / privilegovaný |
| Nahraditelnost | snadná / obtížná / prakticky žádná |
| Objem (ABC) | A / B / C |
| Typ vztahu | rámcová smlouva / objednávky / DPA / NDA / bez smlouvy |

### Co z toho spočítají vzorce

**Kritičnost** — `KRITICKÝ`, když má dodavatel privilegovaný přístup, nebo je
ICT dodavatel s přístupem k datům, nebo je prakticky nenahraditelný.
`VÝZNAMNÝ` při ICT vazbě, omezeném přístupu, obtížné nahraditelnosti nebo
objemu A. Jinak `BĚŽNÝ`.

Rozhoduje tedy **přístup, ne cena** — levný dodavatel se vzdálenou správou
serverů je rizikovější než drahý dodavatel kancelářských potřeb.

**Režim dle ISO 27001** — co je u dodavatele potřeba (prověření, bezpečnostní
požadavky ve smlouvě, DPA, právo auditu, monitoring). Přepočítá se s každou
změnou vstupů.

### Testy

```bash
python3 test_vzorce.py    # logika vzorců v Excelu (bez Excelu je nespustíme)
python3 test_zdroje.py    # normalizace názvů, odhad domény, ověření stránky
```

Oba běží bez sítě. Hlídají tiché chyby, které by se v auditu poznaly pozdě —
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
| `test_vzorce.py` | kontrola logiky vzorců v Excelu |
| `test_zdroje.py` | kontrola normalizace názvů a ověřování webu |
| `TAXONOMIE.md` | proč je číselník členěný takhle |

Keš je v profilu uživatele (`~/.cache/dodavatele/`), mezistav v
`.dodavatele-stav.json` vedle výstupu.

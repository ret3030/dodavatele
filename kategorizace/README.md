# kategorizace/ – deterministické zařazení dodavatele bez LLM

Samostatný, experimentální modul. **Není napojený na `dodavatele.py`** – sdílí
s ním jen čtení `../taxonomie_data.json` (číselník 74 kategorií / 11 skupin).

Cíl: u firem, kde je obor z veřejných zdrojů jednoznačný, určit kategorii
**deterministicky** (stejný vstup → stejný výstup) a obejít tak ruční LLM krok.
Nejednoznačné firmy skončí jako `LLM` (nezařazeno) a řeší se původní cestou.

Taxonomie (74 kategorií / 11 skupin, u každé příznak ICT relevance) je
**sjednocená v `../taxonomie_data.json`** – čte ji modul i `dodavatele.py`.
Odůvodnění revize: `TAXONOMIE_V2.md`.

## Zdroje – jen veřejné, bez klíče, bez služby

Žádný API klíč, žádná běžící služba, žádný kontejner. Čistý Python (`urllib`) –
běží i na Windows bez WSL, Podmanu a Dockeru.

| zdroj | co z něj bereme |
|---|---|
| **ARES** (`ares.gov.cz`) | kanonický název, IČO, DIČ, sídlo (město), CZ-NACE |
| **Wikidata** (`wikidata.org`) | firmu spáruje podle IČO (`P4156`); z entity: oficiální web (`P856`), obor (`P452`), produkt (`P1056`), typ (`P31`), popis |
| **Wikipedie** (cs, pak en) | úvodní odstavec článku – čistý popis činnosti |
| **web firmy** | `<title>`, meta popis, `<h1>`, viditelný text titulky + až 2 vnitřní stránky (`/o-nas`, `/produkty`…) |

## Jak to funguje

1. **ARES** podle názvu (nebo přímo podle IČO ze vstupu) → kanonická data
   a seznam CZ-NACE. Spáruje se jen při shodě normalizovaného názvu – radši
   nic než špatná firma.
2. **Wikidata**: nejdřív `haswbstatement:P4156=<IČO>` (přesné), jinak
   `wbsearchentities` podle názvu. Z entity se vytáhne web, obor, produkt,
   typ a popis; QID oborů se přeloží na české štítky.
3. **Doména firmy** v pořadí: sloupec `Web` ve vstupu → Wikidata `P856` →
   opatrná heuristika z názvu (`nazevfirmy.cz` a pár variant; **přijme jen
   tu, kde je na stránce IČO, nebo město + víc tokenů názvu**).
4. **Web firmy** (`web.py`) stáhne z domény meta popis (silný signál) a text
   stránek (širší, šumavější signál).
5. Ze všech signálů se poskládá text **s vahami zdrojů** – web firmy (meta)
   3,0; Wikipedie/Wikidata (knowledgeGraph) 3,0; text webu 1,6; NACE názvy 1,2.
6. `pravidla.py` je **list namapovaných klíčových slov** – pro každý kód
   kategorie sada frází s vahou (a záporné fráze na odlišení sourozeneckých
   kategorií). Skóre kategorie = `Σ váha_fráze × váha_zdroje` (každá fráze za
   jeden zdroj jednou).
7. Rozhodnutí:
   - **AUTO** – skóre ≥ 12, odstup od druhé kategorie ≥ 50 %, aspoň 3 různé
     zdroje → kategorie se převezme.
   - **OVERIT** – skóre ≥ 6 → návrh s nižší jistotou, doporučená kontrola.
   - **LLM** – jinak → `XXX-00`, nechává se na původní LLM krok.

Každá stažená odpověď (ARES, Wikidata, Wikipedie, web) se ukládá do `.cache/`
(gzip JSON, klíč = hash dotazu). Opakovaný běh nic nestahuje a je plně
deterministický. Rejstříková data se mění řádově pomaleji než SERP snippety,
takže i první běh je dobře reprodukovatelný.

## Použití

```bash
# XLSX potřebuje openpyxl → spouštět přes .venv/bin/python
.venv/bin/python -m kategorizace.kategorizuj vstup.csv -o vystup_kat.csv
.venv/bin/python -m kategorizace.kategorizuj vstup.xlsx -o vystup_kat.xlsx --rozbor rozbor.jsonl

# jen z keše, nic nestahovat
.venv/bin/python -m kategorizace.kategorizuj vstup.csv -o out.csv --offline
```

Vstup: CSV / XLSX / TXT. Povinný je jen sloupec s názvem firmy. Nepovinné, ale
**hodně zpřesní**:

| sloupec | k čemu |
|---|---|
| `Web` / `URL` | přímo doména firmy – odpadá nejisté hádání |
| `IČO` | přesné spárování s ARES i Wikidaty |
| `Město` | ověření uhádnuté domény, zúžení ARES |
| `Země` | zatím se plně řeší jen `CZ`/prázdno (ARES); ostatní jen Wikidata + web |
| `NACE` | slabý textový signál (když není z ARES) |

Přepínače: `--offline` (jen keš), `--bez-webu` (nestahovat weby firem),
`--bez-heuristiky` (nehádat doménu z názvu), `--limit N`, `--prodleva S`,
`--kes ADRESÁŘ`, `--rozbor SOUBOR.jsonl`.

Výstup (CSV `;` nebo XLSX): `Název | IČO | Doména | Zdroj domény | Kód kategorie
| Kategorie | Skupina | ICT relevance | Rozhodnutí | Skóre | Odstup | Zdrojů |
Alternativy | Skupina (skóre) | Důkaz`. Sloupec **Zdroj domény**
(`vstup` / `wikidata` / `heuristika` / prázdno) říká, jak moc doméně věřit;
**Důkaz** ukazuje, které fráze z jakého zdroje zabraly.

`--rozbor soubor.jsonl` uloží ke každé firmě kompletní rozklad pro ladění.

## Měření přesnosti

```bash
.venv/bin/python -m kategorizace.vyhodnoceni vystup_kat.csv gold.xlsx
```

`gold.xlsx` = tentýž seznam firem se správnou kategorií ve sloupci
`Kód kategorie` – klidně **dřívější výstup `dodavatele.py`** po LLM kroku.
Párování je podle názvu (bez právních forem). Vypíše top-1 přesnost listu
i skupiny, „gold mezi top-3", co by udělalo přijetí AUTO napevno (pokrytí +
přesnost), přesnost po skupinách a nejčastější záměny.

## Naměřená přesnost

> **Pozor:** čísla níže jsou z verze, která signály brala z webového
> vyhledávání (SERP přes SERPER, později SearXNG). Přechod na veřejné rejstříky
> mění zdroj i pokrytí – firmu bez vyplněného webu a bez záznamu ve Wikidatech
> teď častěji nedohledáme a spadne rovnou na LLM. **Přeměřte si to na svém gold
> seznamu** (`vyhodnoceni.py`). Pravidla i prahy jsou na konkrétní zdroj
> nezávislé; co drží, je přesnost AUTO větve (~95 % list) – ta stojí hlavně na
> textu z webu firmy, který zůstal.

| metrika (SERP verze, orientačně) | hodnota |
|---|---|
| top-1 přesnost listu, všechny firmy | ~63 % |
| top-1 přesnost skupiny, všechny firmy | ~74 % |
| pokrytí větve AUTO | ~45 % |
| přesnost listu ve větvi AUTO | ~94 % |
| shoda ICT příznaku ve větvi AUTO (vstup pro ISO 27001) | ~97 % |

**100 % nedosažitelné.** Zbývající chyby jsou víceoborové firmy (ČSOB Leasing =
finanční i operativní leasing) a sporné zařazení samo. Deterministicky se dá
spolehlivě ubrat část objemu LLM, ne celý – a s veřejnými rejstříky je ta část
menší než se SERP, výměnou za nulovou infrastrukturu.

## Kam dál

- **web ze vstupu**: největší páka na přesnost i pokrytí – doplnit sloupec
  `Web` co největšímu počtu dodavatelů,
- **SK**: doplnit RPO SR (obdoba ARES) pro slovenské firmy,
- **hybrid**: deterministicky se vezme top-3 a LLM z nich jen vybere,
- rozšířit `pravidla.py` na sourozenecké dvojice (výroba × distribuce,
  e-shop × velkoobchod) kontextovými pravidly.

## Soubory

| soubor | co dělá |
|---|---|
| `kategorizuj.py` | CLI: seznam firem → kategorie |
| `vyhodnoceni.py` | CLI: porovnání s gold seznamem |
| `zdroje.py` | klienti ARES / Wikidata / Wikipedie + dohledání domény + disková keš |
| `web.py` | stažení a čištění textu z webu firmy |
| `pravidla.py` | **list klíčových slov** pro 82 kategorií (+ XXX-00) |
| `klasifikator.py` | sběr signálů, skórování, rozhodnutí, prahy |
| `normalizace.py` | normalizace textu a názvů firem |
| `taxonomie.py` | čtení `../taxonomie_data.json` |
| `vstup.py` | čtení CSV / XLSX / TXT |

`.cache/` a `vystup_*` jsou v `.gitignore`.

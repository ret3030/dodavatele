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
| **ARES** (`ares.gov.cz`) | ČR: kanonický název, IČO, DIČ, sídlo (město), CZ-NACE |
| **RPO SR** (`api.statistics.sk`) | SK: totéž + hlavní činnost (SK-NACE + slovenský text) |
| **Wikidata** (`wikidata.org`) | firmu spáruje podle IČO (`P4156`); z entity: oficiální web (`P856`), obor (`P452`), produkt (`P1056`), typ (`P31`), popis |
| **Wikipedie** (cs, pak en) | úvodní odstavec článku – čistý popis činnosti |
| **web firmy** | `<title>`, meta popis, `<h1>`, viditelný text titulky + až 2 vnitřní stránky (`/o-nas`, `/produkty`…) |

## Jak to funguje

1. **Rejstřík** podle názvu (nebo přímo podle IČO ze vstupu) → kanonická data
   a NACE. Pro `Země = SK` **RPO SR**, jinak **ARES**. Spáruje se jen při přesné
   shodě normalizovaného názvu (nebo IČO) – radši nic než špatná firma.
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

Každá stažená odpověď (ARES, RPO SR, Wikidata, Wikipedie, web) se ukládá do
`.cache/` (gzip JSON, klíč = hash dotazu). Opakovaný běh nic nestahuje a je plně
deterministický. Rejstříková data se mění řádově pomaleji než SERP snippety,
takže i první běh je dobře reprodukovatelný. Dotazy jsou sériové s respektem
k `Retry-After` (Wikimedia API jinak vrací HTTP 429).

## Použití

### 1. běh – deterministické zařazení + prompt pro LLM na zbytek

```bash
# CSV výstup funguje bez závislostí; XLSX potřebuje openpyxl (→ .venv/bin/python)
python3 -m kategorizace.kategorizuj vstup.csv -o vystup_kat.csv --export-llm pro_llm.txt
```

- `vystup_kat.csv` – rozřazené firmy (viz sloupec **Rozhodnutí** níže),
- `pro_llm.txt` – hotový prompt pro Copilot/ChatGPT jen na firmy s rozhodnutím
  `LLM`: obsahuje celý číselník a ke každé firmě kontext, který už máme
  (IČO, zapsané obory, doména, `tip` = top-3 kandidáti deterministického kroku).

### 2. běh – domergovat odpověď z chatu

Odpověď z chatu (`Původní název;Kód kategorie;Čím se firma zabývá`) uložte jako
CSV a spusťte znovu s `--llm-mapa`:

```bash
python3 -m kategorizace.kategorizuj vstup.csv -o vystup_kat.csv --llm-mapa odpoved.csv
```

Doplněné řádky dostanou `Rozhodnutí = LLM-doplneno` a vyplněný `Popis (LLM)`.
(Rejstříky se z keše nedotazují znovu – druhý běh je okamžitý.)

### Vstup

CSV / XLSX / TXT. Povinný je jen sloupec s názvem firmy. Nepovinné, ale
**hodně zpřesní**:

| sloupec | k čemu |
|---|---|
| `Web` / `URL` | přímo doména firmy – odpadá nejisté hádání (**největší páka**) |
| `IČO` | přesné spárování s ARES / RPO SR i Wikidaty |
| `Město` | ověření uhádnuté domény, zúžení ARES |
| `Země` | `CZ`/prázdno → ARES, `SK` → RPO SR, ostatní jen Wikidata + web |
| `NACE` | slabý textový signál (když není z rejstříku) |

### Přepínače

`--export-llm SOUBOR.txt` (prompt na nezařazené), `--llm-mapa CSV…` (domergovat
odpověď), `--llm-i-overit` (do promptu i větev OVERIT), `--export-davka N`
(rozdělit prompt po N firmách), `--offline` (jen keš), `--bez-webu`,
`--bez-heuristiky`, `--limit N`, `--prodleva S`, `--kes ADRESÁŘ`,
`--rozbor SOUBOR.jsonl`.

### Výstup

`Název | IČO | Doména | Zdroj domény | Kód kategorie | Kategorie | Skupina |
ICT relevance | Rozhodnutí | Skóre | Odstup | Zdrojů | Alternativy |
Skupina (skóre) | Důkaz | Popis (LLM)`

| Rozhodnutí | co s tím |
|---|---|
| `AUTO` | kategorie převzatá rovnou (~97 % přesnost listu, 100 % shoda ICT příznaku) |
| `OVERIT` | jen našeptávač (~73 % list) – kontrola člověkem |
| `LLM` | nezařazeno – je v `pro_llm.txt` |
| `LLM-doplneno` | doplněno z `--llm-mapa` |

Sloupec **Zdroj domény** (`vstup` / `wikidata` / `heuristika` / prázdno) říká,
jak moc doméně věřit; **Důkaz** ukazuje, které fráze z jakého zdroje zabraly.
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

Test na `testset_vzorek.csv` – 246 reálných firem napříč 11 skupinami, gold
určen ručním researchem. Vstup **bez** vyplněného sloupce `Web`.

| metrika | hodnota |
|---|---|
| top-1 přesnost listu, všechny firmy | 34 % |
| top-1 přesnost skupiny, všechny firmy | 37 % |
| **pokrytí větve AUTO** | **10 %** |
| **přesnost listu ve větvi AUTO** | **97 %** |
| **shoda ICT příznaku ve větvi AUTO** (vstup pro ISO 27001) | **100 %** |
| větev OVERIT – list správně | 73 % |
| padá na LLM | 71 % |

Čtení: co modul zařadí jako `AUTO`, je spolehlivé (prahy jsou schválně přísné),
ale takových firem je zatím jen desetina. Zbytek jde přes `pro_llm.txt` do LLM.
Pro srovnání: dřívější verze přes webové vyhledávání (SERP) měla ~45 % AUTO –
platila za to běžící službou (SearXNG v kontejneru).

**Co pokrytí zvedne** (v tomto pořadí dopadu):

1. **vyplnit sloupec `Web`** ve vstupu → odhad AUTO ~35 % (zpět na úroveň SERP),
2. **ARES-VR předmět podnikání** (zatím nenapojeno) – text registrované činnosti
   česky a konkrétně, i pro firmy bez webu → odhad AUTO ~20–25 %.

**100 % nedosažitelné** ani s tím – víceoborové firmy (ČSOB Leasing = finanční
i operativní leasing) a sporné zařazení samo. Deterministicky se dá ubrat část
objemu LLM, ne celý.

## Kam dál

- **web ze vstupu** – největší páka; doplnit sloupec `Web` co nejvíce dodavatelům,
- **ARES-VR předmět podnikání** – největší jednotlivý zisk pro firmy bez webu,
- NACE kódy z rejstříku jsou teď slabý signál (číselník je anglicky) – po
  napojení ARES-VR je z klasifikátoru vyřadit nebo srazit váhu,
- **SK NACE** – RPO SR vrací i seznam `activities`, bereme jen `mainActivity`,
- **hybrid** – deterministicky se vezme top-3 a LLM z nich jen vybere,
- rozšířit `pravidla.py` na sourozenecké dvojice (výroba × distribuce,
  e-shop × velkoobchod) kontextovými pravidly.

## Soubory

| soubor | co dělá |
|---|---|
| `kategorizuj.py` | CLI: seznam firem → kategorie |
| `vyhodnoceni.py` | CLI: porovnání s gold seznamem |
| `zdroje.py` | klienti ARES / RPO SR / Wikidata / Wikipedie + dohledání domény + disková keš |
| `web.py` | stažení a čištění textu z webu firmy |
| `pravidla.py` | **list klíčových slov** pro 82 kategorií (+ XXX-00) |
| `klasifikator.py` | sběr signálů, skórování, rozhodnutí, prahy |
| `normalizace.py` | normalizace textu a názvů firem |
| `taxonomie.py` | čtení `../taxonomie_data.json` |
| `vstup.py` | čtení CSV / XLSX / TXT |

`.cache/` a `vystup_*` jsou v `.gitignore`.

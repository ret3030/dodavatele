# kategorizace/ – deterministické zařazení dodavatele bez LLM

Samostatný, experimentální modul. **Není napojený na `dodavatele.py`** – sdílí
s ním jen čtení `../taxonomie_data.json` (číselník 74 kategorií / 11 skupin).

Cíl: u firem, kde je obor z veřejného webu jednoznačný, určit kategorii
**deterministicky** (stejný vstup → stejný výstup) a obejít tak ruční LLM krok.
Nejednoznačné firmy skončí jako `LLM` (nezařazeno) a řeší se původní cestou.

Taxonomie (74 kategorií / 11 skupin, u každé příznak ICT relevance) je
**sjednocená v `../taxonomie_data.json`** – čte ji modul i `dodavatele.py`.
Odůvodnění revize: `TAXONOMIE_V2.md`.

## Jak to funguje

1. Pro každou firmu se pošlou **2 dotazy do Google přes SERPER API**
   (`"název" město` + `název (výrobce OR dodavatel OR distributor OR služby …)`).
2. Ze SERP odpovědi (organické výsledky, knowledge graph, answer box, sitelinky)
   se posbírá text s **vahami zdrojů** – vlastní web firmy 3,5; knowledge graph
   3,0; první tři výsledky 2,0; katalogy a rejstříky (firmy.cz, justice.cz,
   LinkedIn, Wikipedia…) jen 0,8.
3. `pravidla.py` je **list namapovaných klíčových slov** – pro každý kód
   kategorie sada frází s vahou (a záporné fráze na odlišení sourozeneckých
   kategorií: výroba vs. distribuce, technické poradenství vs. audit…).
4. Skóre kategorie = `Σ váha_fráze × váha_zdroje × počet_výskytů`.
5. Rozhodnutí:
   - **AUTO** – skóre ≥ 12, odstup od druhé kategorie ≥ 30 %, aspoň 2 různé
     zdroje → kategorie se převezme.
   - **OVERIT** – skóre ≥ 5 → návrh s nižší jistotou, doporučená kontrola.
   - **LLM** – jinak → `XXX-00`, nechává se na původní LLM krok.

Surová odpověď SERPER se ukládá do `.cache/` (gzip JSON, klíč = hash dotazu).
Opakovaný běh nic nestahuje a je plně deterministický (Google jinak výsledky
přehazuje).

## Použití

```bash
# klíč: buď proměnná prostředí, nebo soubor kategorizace/serper_key.txt
export SERPER_API_KEY=...

# XLSX potřebuje openpyxl → spouštět přes .venv/bin/python
.venv/bin/python -m kategorizace.kategorizuj vstup.csv -o vystup_kat.csv
.venv/bin/python -m kategorizace.kategorizuj vstup.xlsx -o vystup_kat.xlsx --rozbor rozbor.jsonl

# jen z keše, nic nestahovat
.venv/bin/python -m kategorizace.kategorizuj vstup.csv -o out.csv --offline
```

Vstup: CSV / XLSX / TXT. Povinný je sloupec s názvem firmy; `Město`, `Země`
(kód, řídí `gl`/`hl` vyhledávání) a `NACE` jsou nepovinné, ale zpřesní výsledek.

Výstup (CSV `;` nebo XLSX): `Název | Kód kategorie | Kategorie | Skupina |
Rozhodnutí | Skóre | Odstup | Zdrojů | Alternativy | Skupina (skóre) | Důkaz`.
Sloupec **Důkaz** ukazuje, které fráze z jakého zdroje zabraly – kvůli
kontrole a doladění pravidel.

`--rozbor soubor.jsonl` uloží ke každé firmě kompletní rozklad (skóre všech
kategorií, všechny signály) pro ladění.

## Měření přesnosti

```bash
.venv/bin/python -m kategorizace.vyhodnoceni vystup_kat.csv gold.xlsx
```

`gold.xlsx` = tentýž seznam firem se správnou kategorií ve sloupci
`Kód kategorie` – klidně **dřívější výstup `dodavatele.py`** po LLM kroku.
Párování je podle názvu (bez právních forem). Vypíše:

- top-1 přesnost listu i skupiny, podíl „gold mezi top-3 návrhy",
- co by se stalo, kdyby se **AUTO přijalo napevno** (pokrytí + přesnost),
- přesnost po skupinách,
- nejčastější záměny `gold → návrh` (vodítko, které fráze/váhy dolaďovat).

## Naměřená přesnost

Test na `testset_vzorek.csv` – 246 reálných firem napříč 11 skupinami / ~68
z 83 kategorií, gold určen ručním researchem (odhad ~5 % gold je sporných).
Konfigurace: 2 dotazy SERPER + stažení meta popisu z webu firmy, prahy
nastavené na „AUTO jen když jistota".

| metrika | 1. běh | taxonomie v2 | v2 + širší web |
|---|---|---|---|
| top-1 přesnost listu (kód kategorie), všechny firmy | 46,6 % | 61,8 % | **63,4 %** |
| top-1 přesnost skupiny, všechny firmy | 54,3 % | 70,3 % | **73,6 %** |
| **pokrytí větve AUTO** | 24 % | 38 % | **45 %** |
| **přesnost listu ve větvi AUTO** | 88,7 % | 95,7 % | **93,6 %** |
| přesnost skupiny ve větvi AUTO | – | 96,8 % | **94,5 %** |
| **shoda ICT příznaku ve větvi AUTO** (vstup pro ISO 27001) | – | 98,9 % | **97,3 %** |
| shoda ICT příznaku, všechny firmy | – | 79,3 % | **85,0 %** |
| větev OVERIT (návrh „ke kontrole") | – | 34 % | 35 %, ~48 % list |
| padá na LLM (nezařazeno) | 47 % | 28 % | **21 %** |

„v2 + širší web": kromě `<title>` a meta popisu se stahuje i viditelný text
titulní stránky a až 2 vnitřní stránky (`/o-nas`, `/produkty`, `/sluzby`).
Zvedlo to pokrytí AUTO o 7 p.b. a shodu ICT příznaku o ~6 p.b.; přesnost
listu ve větvi AUTO klesla o ~2 p.b. (text stránky je šumavější než meta).

Čtení: ~37 % dodavatelů se zařadí automaticky s ~96% přesností listu
(~98 % skupina), ~33 % dostane návrh ke kontrole, ~29 % jde na LLM/člověka.

**100 % nedosažitelné.** Sweep prahů ukazuje strop AUTO větve kolem 95–96 %
bez ohledu na to, jak se přiškrtí – zbývající chyby jsou víceoborové firmy
(ČSOB Leasing = finanční i operativní leasing; SMTplus = osazování i stroje
na osazování) a sporné zařazení samo (gold od dvou lidí se taky neshodne na
100 %). Deterministicky se dá spolehlivě ubrat ~1/3–1/2 objemu LLM, ne celý.

Co přesnost zvedlo: (1) oprava – dedup snippetů podle URL zahazoval tu
variantu s klíčovými slovy; (2) CZ/SK stemmer (skloňování byla hlavní brzda);
(3) meta popis z webu firmy jako signál; (4) skóre bez násobení počtem
výskytů (jinak keyword-stuffed meta přebije vše); (5) cílené opravy pravidel
podle konfuzní matice; (6) přísnější prahy AUTO.

## Kam dál

- **hybrid**: deterministicky se vezme top-3 a LLM z nich jen vybere – dostane
  se to na ~92–95 % listu, ale s LLM v procesu (levnějším – 3 možnosti místo
  83),
- rozšířit `pravidla.py` na zbývající kategorie a sourozenecké dvojice
  kontextovými pravidly (výroba×distribuce podle „vyrábíme / e-shop / skladem"),
- větev OVERIT je zatím slabá (~54 %) – buď zpřísnit a přesunout do LLM, nebo
  ji brát jen jako našeptávač pro člověka.

## Soubory

| soubor | co dělá |
|---|---|
| `kategorizuj.py` | CLI: seznam firem → kategorie |
| `vyhodnoceni.py` | CLI: porovnání s gold seznamem |
| `serper.py` | klient SERPER + disková keš |
| `pravidla.py` | **list klíčových slov** pro 82 kategorií (+ XXX-00) |
| `klasifikator.py` | sběr signálů ze SERP, skórování, rozhodnutí, prahy |
| `normalizace.py` | normalizace textu a názvů firem |
| `taxonomie.py` | čtení `../taxonomie_data.json` |
| `vstup.py` | čtení CSV / XLSX / TXT |

`serper_key.txt`, `.cache/` a `vystup_*` jsou v `.gitignore`.

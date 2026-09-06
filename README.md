# Dodavatelé – obohacení seznamu z veřejných rejstříků

Vezme seznam názvů firem a doplní k nim adresu, IČO/DIČ, obor činnosti (NACE)
a zařazení do vlastní kategorie dodavatele – z veřejných rejstříků (ARES, RPO
SR, INSEE, SEC EDGAR, GLEIF, Wikidata).

## Instalace

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

(`openpyxl` je potřeba jen pro XLSX – bez instalace čehokoli funguje CSV/TXT
vstup i výstup na čistém Pythonu 3.9+.)

## Použití

```bash
python3 dodavatele.py vstup.csv -o vystup.xlsx
```

Vstupem je jakýkoli seznam firem (`.csv`, `.xlsx` nebo `.txt`) – stačí sloupec
s názvem, IČO/DIČ/adresa jsou nepovinné, ale zpřesní a zrychlí hledání.
Hlavičku sloupců pozná automaticky, česky i anglicky. Ukázka: `vzor_dodavatele.csv`.

Výstup obsahuje `Jméno | Ulice | PSČ | Město | Země | IČO | DIČ |
Kód kategorie | Kategorie dodavatele` a kontrolní sloupce navíc (vč. NACE
(všechny)) – hlavně
**Stav** (`OK` / `VYBRANO` / `OVERIT` / `NENALEZENO`), který říká, jak moc
danému řádku věřit. XLSX má navíc dva přehledové listy s číselníkem kategorií
a číselníkem NACE.

Kategorie se z NACE určí jen tam, kde je to **jisté** — každý zapsaný obor
firmy musí určovat kategorii a všechny musí vést na tutéž. Stačí jeden obecný
nebo odporující si obor a zůstane `XXX-00 Nezařazeno` místo zavádějícího
zařazení. Na reálných datech to znamená necelých 9 % dodavatelů; zbytek se
záměrně nehádá.
Skutečnou činnost doplní krok přes LLM chat (`--export-llm` / `--llm-mapa`,
viz DOCS.md) – exportují se všichni dodavatelé, protože zapsaný obor říká, jak
je firma zaregistrovaná, ne co dodává.

## Chcete víc?

Popis všech přepínačů, zdrojů dat po jednotlivých zemích, řešení konkrétních
situací (firma se nenajde, dvě firmy stejného jména, OSVČ zadaná jen jménem,
ruční zařazení přes LLM chat, porovnání s cizím NACE…) a kompletní seznam
kategorií je v **[DOCS.md](DOCS.md)** – README je záměrně jen "jak to
spustit", zbytek je referenční dokumentace, ke které se sahá jen když je
potřeba.

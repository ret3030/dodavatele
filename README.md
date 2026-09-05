# Dodavatelé – obohacení seznamu z veřejných rejstříků

Vezme seznam názvů firem a doplní k nim adresu, IČO/DIČ, obor činnosti (NACE)
a zařazení do vlastní kategorie dodavatele – z veřejných rejstříků (ARES, RPO
SR, INSEE, Companies House, Handelsregister, GLEIF, Wikidata a dalších).

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

Výstup obsahuje `Jméno | Ulice | PSČ | Město | Země | IČO | DIČ | NACE |
Kód kategorie | Kategorie dodavatele` a kontrolní sloupce navíc – hlavně
**Stav** (`OK` / `VYBRANO` / `OVERIT` / `NENALEZENO`), který říká, jak moc
danému řádku věřit. XLSX má navíc dva přehledové listy s číselníkem kategorií
a číselníkem NACE.

Firmy, u kterých se obor činnosti nedohledá automaticky (viz Známé limity
v [DOCS.md](DOCS.md)), skončí v `XXX-00 Nezařazeno` – **teprve pak** má smysl
sáhnout po ručním zařazení přes LLM chat (`--export-nezarazene` /
`--kategorie-mapa`, viz DOCS.md), ne dřív.

## Chcete víc?

Popis všech přepínačů, zdrojů dat po jednotlivých zemích, řešení konkrétních
situací (firma se nenajde, dvě firmy stejného jména, OSVČ zadaná jen jménem,
ruční zařazení přes LLM chat, porovnání s cizím NACE…) a kompletní seznam
kategorií je v **[DOCS.md](DOCS.md)** – README je záměrně jen "jak to
spustit", zbytek je referenční dokumentace, ke které se sahá jen když je
potřeba.

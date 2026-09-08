# Dodavatelé – obohacení seznamu z veřejných rejstříků

Nástroj, který k seznamu firem doplní adresu, IČO/DIČ a obor činnosti (NACE)
z veřejných rejstříků – ARES (ČR), RPO SR (Slovensko), INSEE (Francie),
SEC EDGAR (USA), GLEIF a Wikidata (svět). Vše bez API klíče a bez registrace.

Zařazení do vlastní kategorie dodavatele a stručný popis, co firma skutečně
dělá, se doplňuje ve druhém kroku – zapsaný obor v rejstříku říká, jak je
firma zaregistrovaná, ne co dodává. Dvě cesty:

- **[Deterministické zařazení bez LLM](#deterministické-zařazení-bez-llm)** –
  část dodavatelů zařadí automaticky z webu firmy.
- **[Zařazení přes LLM chat](#zařazení-přes-llm-chat)** – zbytek přes
  Copilot/ChatGPT.

## Instalace a použití

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt   # openpyxl, jen pro čtení/zápis XLSX

python3 dodavatele.py vstup.csv -o vystup.xlsx
```

Vstupem je `.csv`, `.xlsx` nebo `.txt` se seznamem firem – stačí sloupec
s názvem, IČO/DIČ/adresa jsou nepovinné, ale zpřesní a zrychlí hledání.
Hlavičku sloupců rozpozná automaticky, česky i anglicky. Ukázka:
`vzor_dodavatele.csv`.

Výstup: `Jméno | Ulice | PSČ | Město | Země | IČO | DIČ | NACE | Stav
| Zdroj dat | Kód kategorie | Kategorie dodavatele | Popis činnosti` (+ pár
sloupců navíc, jen když mají čím být naplněné). **Stav** říká, jak moc
danému řádku věřit:

| stav | význam |
|---|---|
| `OK` | jednoznačná shoda, data lze převzít |
| `VYBRANO` | víc podobných firem – vybrána nejlepší, doporučená kontrola |
| `OVERIT` | shoda s výhradou (např. jiná adresa/země) – doporučená kontrola |
| `NENALEZENO` | nic dost podobného nenalezeno |
| `CHYBA` | prázdný řádek nebo výpadek zdrojů |

Opakovaný běh nad stejným seznamem je díky keši (uložené v profilu
uživatele) téměř okamžitý – nic se nestahuje znovu. `--obnovit` zkusí ještě
jednou dohledat firmy, které v daném běhu skončily jako nenalezené.
`--help` vypíše všechny volby.

Číselník kategorií (`taxonomie_data.json`) má **74 kategorií v 11 skupinách**
a u každé příznak ICT relevance (vstup pro navazující posouzení dle ISO 27001).
Odůvodnění revize: `kategorizace/TAXONOMIE_V2.md`.

## Deterministické zařazení bez LLM

Adresář `kategorizace/` je samostatný modul, který **kód kategorie určí
deterministicky** (stejný vstup → stejný výstup) z veřejných rejstříků a webu
firmy, a tak u části dodavatelů obejde LLM krok. Nejednoznačné firmy nechá
na LLM. Není součástí desktopové aplikace – jen příkazová řádka.

Signály se sbírají **jen z veřejných zdrojů bez API klíče a bez běžící služby**:

- **ARES** – kanonický název, IČO/DIČ, sídlo, CZ-NACE,
- **Wikidata** – firmu spáruje podle IČO (`P4156`), z ní vezme oficiální web
  (`P856`), obor, produkt a typ,
- **Wikipedie** (cs, pak en) – úvodní odstavec článku,
- **web firmy** – doménu bere ze sloupce `Web` ve vstupu, jinak z Wikidat,
  jinak ji opatrně zkusí uhodnout z názvu (přijme jen ověřenou).

Je to **čistý Python (jen `urllib`)** – běží i na Windows bez WSL, Podmanu
a Dockeru. První běh stahuje, každý další běh nad stejným seznamem jede z keše
a je bajt po bajtu shodný.

### Použití

```bash
.venv/bin/python -m kategorizace.kategorizuj vstup.csv -o vystup_kat.csv
.venv/bin/python -m kategorizace.kategorizuj vstup.csv -o out.csv --offline   # jen z keše
```

Vstup je stejný seznam firem jako pro `dodavatele.py`. **Přesnost výrazně
zvedne sloupec `Web` (nebo `URL`)** – odpadá nejisté hádání domény. Pomůže
i `IČO` (přesné spárování s Wikidaty) a `Město`.

Ve výstupu (`Název | IČO | Doména | Zdroj domény | Kód kategorie | … |
Rozhodnutí`) rozhoduje sloupec **Rozhodnutí**:

| rozhodnutí | co s tím |
|---|---|
| `AUTO` | kategorie převzata rovnou (na AUTO větvi ~95 % přesnost listu) |
| `OVERIT` | návrh s nižší jistotou, doporučená kontrola |
| `LLM` | nezařazeno, jde na LLM krok níže |

Podíl mezi větvemi závisí na tom, kolik firem má vyplněný web a je ve
Wikidatech – přeměřte si ho na svém gold seznamu (`kategorizace/vyhodnoceni.py`).
Podrobnosti a ladění pravidel: `kategorizace/README.md`.

## Zařazení přes LLM chat

**Kód kategorie**, **Kategorie dodavatele** a **Popis činnosti** zůstávají
prázdné, dokud je nedoplní tenhle krok. U firem, kde se v žádném rejstříku
nenašel žádný NACE kód, se navíc doplní i **NACE** – jako odhad LLM, ne
rejstříkový údaj (rozlišuje to sloupec **NACE - zdroj**). Tam, kde NACE
z rejstříku už je, se nikdy nepřepisuje.

```bash
python3 dodavatele.py vstup.csv -o vystup.xlsx --export-llm firmy.txt
# --> obsah firmy.txt vložit do Copilotu/ChatGPT, odpověď uložit jako CSV
python3 dodavatele.py vstup.csv -o vystup.xlsx --llm-mapa odpoved.csv
```

Když už vyplněný výstup máte (a vstupní seznam po ruce nemáte, nebo je na
jiném stroji bez keše), `--z-vystupu` nahradí `vstup` a export/import proběhne
přímo nad ním, bez jediného dotazu do rejstříku:

```bash
python3 dodavatele.py --z-vystupu vystup.xlsx --export-llm firmy.txt
python3 dodavatele.py --z-vystupu vystup.xlsx --llm-mapa odpoved.csv -o vystup2.xlsx
```

## Desktopová aplikace

`gui.py` je okenní rozhraní nad stejnou logikou, zabalené přes PyInstaller
do jednoho spustitelného souboru – spouští se dvojklikem, bez instalace Pythonu.

**Stažení hotové aplikace:**
https://github.com/ret3030/dodavatele/releases/tag/gui-latest – vždy poslední
verze. Na macOS je po rozbalení potřeba aplikaci poprvé spustit přes pravé
tlačítko → Otevřít (Gatekeeper jinak nepodepsanou aplikaci nespustí dvojklikem).

**Sestavení lokálně:**

```bash
pip install pyinstaller openpyxl
# Windows - .exe
pyinstaller --onefile --windowed --name Dodavatele --add-data "taxonomie_data.json;." gui.py
# macOS - .app
pyinstaller --windowed --name Dodavatele --add-data "taxonomie_data.json:." gui.py
```

PyInstaller neumí sestavit aplikaci pro jinou platformu, než na které běží –
proto GitHub Actions (`.github/workflows/build-gui.yml`) sestavuje zvlášť na
Windows a macOS při každé změně `dodavatele.py`/`gui.py` na `main`.

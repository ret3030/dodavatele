# Dodavatelé – obohacení seznamu z veřejných rejstříků

Nástroj, který k seznamu firem doplní adresu, IČO/DIČ a obor činnosti (NACE)
z veřejných rejstříků – ARES (ČR), RPO SR (Slovensko), INSEE (Francie),
SEC EDGAR (USA), GLEIF a Wikidata (svět). Vše bez API klíče a bez registrace.

Zařazení do vlastní kategorie dodavatele a stručný popis, co firma skutečně
dělá, se určuje ve druhém kroku přes LLM chat (Copilot/ChatGPT) – zapsaný
obor v rejstříku totiž říká, jak je firma zaregistrovaná, ne co dodává.
Viz [Zařazení přes LLM chat](#zařazení-přes-llm-chat) níže.

K dispozici jako příkazová řádka i jako desktopová aplikace bez nutnosti
instalovat Python – viz [Desktopová aplikace](#desktopová-aplikace).

## Instalace a použití

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt   # openpyxl, jen pro zápis XLSX

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
Přepínač `--help` vypíše všechny volby i s popisem.

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

## Desktopová aplikace

`gui.py` je okenní rozhraní nad stejnou logikou, zabalené přes PyInstaller
do jednoho spustitelného souboru – spouští se dvojklikem, bez nutnosti
cokoli instalovat.

**Stažení hotové aplikace:**
https://github.com/ret3030/dodavatele/releases/tag/gui-latest –
vždy poslední verze, bez přihlášení do GitHub účtu. Na macOS je po
rozbalení potřeba aplikaci poprvé spustit přes pravé tlačítko → Otevřít
(Gatekeeper jinak nepodepsanou aplikaci nespustí dvojklikem).

**Sestavení lokálně:**

```bash
pip install pyinstaller openpyxl
pyinstaller --onefile --windowed --name Dodavatele gui.py    # Windows - .exe
pyinstaller --windowed --name Dodavatele gui.py               # macOS - .app
```

PyInstaller neumí sestavit aplikaci pro jinou platformu, než na které běží –
proto GitHub Actions (`.github/workflows/build-gui.yml`) sestavuje zvlášť na
Windows a macOS při každé změně `dodavatele.py`/`gui.py` na `main`.

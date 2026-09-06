# Dodavatelé – obohacení seznamu z veřejných rejstříků

Vezme seznam názvů firem a doplní k nim adresu, IČO/DIČ a obor činnosti
(NACE) z veřejných rejstříků – ARES (ČR), RPO SR (Slovensko), INSEE
(Francie), SEC EDGAR (USA), GLEIF a Wikidata (svět). Vše bez API klíče.

Zařazení do vlastní kategorie dodavatele a stručný popis, co firma skutečně
dělá, nástroj neurčuje sám (zapsaný obor říká, jak je firma zaregistrovaná,
ne co dodává) – doplní je krok přes LLM chat (Copilot/ChatGPT), viz níže.

## Instalace a použití

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt   # openpyxl, jen pro zápis XLSX

python3 dodavatele.py vstup.csv -o vystup.xlsx
```

Vstupem je `.csv`, `.xlsx` nebo `.txt` se seznamem firem – stačí sloupec
s názvem, IČO/DIČ/adresa jsou nepovinné, ale zpřesní a zrychlí hledání.
Hlavičku sloupců pozná automaticky, česky i anglicky. Ukázka:
`vzor_dodavatele.csv`.

Výstup: `Jméno | Ulice | PSČ | Město | Země | IČO | DIČ | NACE | Stav
| Zdroj dat | Kód kategorie | Kategorie dodavatele | Popis činnosti` (+ pár
sloupců navíc, jen když mají čím být naplněné). **Stav** říká, jak moc
danému řádku věřit:

| stav | význam |
|---|---|
| `OK` | jednoznačná shoda, data lze převzít |
| `VYBRANO` | víc podobných firem – vybrána nejlepší, zkontrolujte |
| `OVERIT` | shoda s výhradou (např. jiná adresa/země) – zkontrolujte |
| `NENALEZENO` | nic dost podobného nenalezeno |
| `CHYBA` | prázdný řádek nebo výpadek zdrojů |

**Kód kategorie**, **Kategorie dodavatele** a **Popis činnosti** zůstávají
prázdné, dokud je nedoplní LLM krok:

```bash
python3 dodavatele.py vstup.csv -o vystup.xlsx --export-llm firmy.txt
# --> obsah firmy.txt vložit do Copilotu/ChatGPT, odpověď uložit jako CSV
python3 dodavatele.py vstup.csv -o vystup.xlsx --llm-mapa odpoved.csv
```

Opakovaný běh nad stejným seznamem je díky keši (v profilu uživatele) skoro
okamžitý – nic se nestahuje znovu. `--obnovit` zkusí ještě jednou dohledat
firmy, které v daném běhu skončily jako nenalezené. Přepínač `--help`
vypíše všechny volby i s popisem.

## Desktopová appka pro kolegy (bez Pythonu)

`gui.py` je tenké okenní rozhraní nad stejnou logikou, zabalené přes
PyInstaller do jednoho spustitelného souboru – kolega jen dvojklikem spustí
`.exe`/`.app`, nic neinstaluje.

**Stažení hotové appky:**
https://github.com/ret3030/dodavatele/releases/tag/gui-latest –
vždy poslední verze z `main`, bez přihlášení do GitHub účtu. Na macOS je po
rozbalení potřeba appku poprvé spustit přes pravé tlačítko → Otevřít
(Gatekeeper jinak nepodepsanou appku nespustí dvojklikem).

**Sestavení appky lokálně:**

```bash
pip install pyinstaller openpyxl
pyinstaller --onefile --windowed --name Dodavatele gui.py    # Windows - .exe
pyinstaller --windowed --name Dodavatele gui.py               # macOS - .app
```

PyInstaller neumí sestavit appku pro jinou platformu, než na které běží –
proto GitHub Actions (`.github/workflows/build-gui.yml`) sestavuje zvlášť na
Windows a macOS při každé změně `dodavatele.py`/`gui.py` na `main`.

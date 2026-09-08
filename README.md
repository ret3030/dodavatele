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
deterministicky** (stejný vstup → stejný výstup) z webového vyhledávání a webu
firmy, a tak u části dodavatelů obejde LLM krok. Nejednoznačné firmy nechá
na LLM. Není součástí desktopové aplikace – jen příkazová řádka.

Hledání jde přes **vlastní instanci [SearXNG](https://docs.searxng.org/)** –
názvy dodavatelů neopouštějí vlastní infrastrukturu, nic se neposílá do
externí vyhledávací služby.

### Aktivace

1. **Rozjeďte SearXNG.** Přes [Podman](https://podman.io/) (zdarma i pro
   firmy, na rozdíl od Docker Desktopu). Na Windows/macOS nejdřív jednou
   `podman machine init && podman machine start`, pak:

   ```bash
   podman run -d --name searxng -p 8888:8080 \
     -v "./searxng:/etc/searxng" docker.io/searxng/searxng
   ```

2. **Povolte JSON výstup** – v `searxng/settings.yml` (vytvoří se při prvním
   startu) přidejte a kontejner restartujte (`podman restart searxng`):

   ```yaml
   search:
     formats: [html, json]
   ```

3. **Řekněte modulu adresu** – proměnnou prostředí, souborem, nebo přepínačem
   `--searxng URL`:

   ```bash
   export SEARXNG_URL=http://localhost:8888
   # nebo:  echo http://localhost:8888 > kategorizace/searxng_url.txt
   ```

   Instance za HTTP Basic auth: dejte přihlášení do URL –
   `http://uzivatel:heslo@vyhledavac.interni:8080`.

4. **Spusťte kategorizaci** nad stejným seznamem firem:

   ```bash
   .venv/bin/python -m kategorizace.kategorizuj vstup.csv -o vystup_kat.csv
   .venv/bin/python -m kategorizace.kategorizuj vstup.csv -o out.csv --offline   # jen z keše
   ```

Ve výstupu (`Název | Kód kategorie | Kategorie | Skupina | … | Rozhodnutí`)
rozhoduje sloupec **Rozhodnutí**:

| rozhodnutí | podíl | co s tím |
|---|---|---|
| `AUTO` | ~37 % | kategorie převzata rovnou (~96 % přesnost listu) |
| `OVERIT` | ~33 % | návrh s nižší jistotou, doporučená kontrola |
| `LLM` | ~30 % | nezařazeno, jde na LLM krok níže |

Podrobnosti, měření přesnosti a ladění pravidel: `kategorizace/README.md`.

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

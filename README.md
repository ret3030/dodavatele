# Dodavatelé – obohacení seznamu z veřejných rejstříků

Vezme seznam názvů firem a doplní k nim identifikační a adresní údaje
z veřejných rejstříků, hlavní obor činnosti (NACE) a zařazení do vlastní
taxonomie kategorií dodavatelů.

## Rychlý start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt        # jen kvůli XLSX

.venv/bin/python dodavatele.py vzor_dodavatele.csv -o vystup.xlsx
```

Bez XLSX stačí čistý Python bez instalace čehokoli:

```bash
python3 dodavatele.py seznam.txt -o vystup.csv
```

## Vstup

`.csv`, `.xlsx` nebo `.txt` (jeden název na řádek). U CSV/XLSX se hlavička
rozpozná automaticky, rozumí česky i anglicky:

| sloupec | rozpoznávané názvy | povinný |
|---|---|---|
| název | Název, Jméno, Firma, Company, Supplier, Vendor, Lieferant … | ano* |
| IČO | IČO, IC, Company ID, Registration number | ne |
| DIČ | DIČ, VAT, VAT ID, USt-IdNr, Tax ID | ne |
| země | Země, Country, Stát, ISO | ne |

\* místo názvu stačí IČO. Když vyplníte **IČO**, přeskočí se dohledávání podle
názvu a záznam je jednoznačný — u problémových firem je to nejrychlejší oprava.
Vyplněná **země** zúží hledání na správný rejstřík a zrychlí běh.

## Výstup

Sloupce podle zadání: `Jméno | Ulice | PSČ | Město | Země | IČO | DIČ |
St.-Nr. 2 | NACE`, k tomu `Kód kategorie | Skupina | Kategorie dodavatele`
a doplňkové sloupce pro kontrolu (`--kompakt` je vypne).

XLSX má druhý list **Číselník kategorií** s celou taxonomií a počtem
dodavatelů v každé kategorii.

### Sloupec „St.-Nr. 2“

V německých systémech (SAP pole `STCD1`/`STCD2`) je to **druhé daňové nebo
registrační číslo** vedle DIČ. Protože IČO i DIČ máte ve vlastních sloupcích,
plní se ve výchozím režimu `auto` takto:

* česká firma → prázdné (IČO + DIČ už údaje pokrývají),
* zahraniční firma → národní registrační číslo (např. `HRB 719915` u Německa,
  `CIK 320193` u USA, slovenské IČO).

Jiné chování přepínačem `--stnr2 registrace|ico|dic|zadne`.

### Sloupec „Stav“

| stav | význam |
|---|---|
| `OK` | jednoznačná shoda názvu, data lze převzít |
| `VICE_SHOD` | dvě a více stejně podobných firem – vyberte ručně (kandidáti jsou v Poznámce) |
| `OVERIT` | shoda pod prahem, data převzata, ale zkontrolujte je |
| `NENALEZENO` | nic dost podobného; **datové sloupce zůstávají prázdné**, v Poznámce jsou nejbližší kandidáti |
| `CHYBA` | prázdný řádek nebo výpadek všech zdrojů |

Záznam s nízkou shodou se nikdy nepropíše do datových sloupců — raději prázdno
než údaje cizí firmy.

## Zdroje dat

| zdroj | pokrytí | co dodá |
|---|---|---|
| **ARES** (ares.gov.cz) | ČR, kompletní | název, adresa, IČO, DIČ, NACE včetně *převažující činnosti* |
| **RPO SR** (statistics.sk) | SR | název, adresa, IČO |
| **GLEIF** (api.gleif.org) | svět, ale jen firmy s LEI | název, adresa, národní registrační číslo |
| **SEC EDGAR** (sec.gov) | USA, jen firmy registrované u SEC | název, adresa, SIC → NACE, CIK |
| **Wikidata** | velké nadnárodní firmy | obor činnosti, EU DIČ, LEI, sídlo |
| **VIES** (`--vies`) | EU | ověření platnosti DIČ |

Vše bez API klíče a bez registrace.

**Známé limity.** GLEIF obsahuje jen entity s LEI, takže řada evropských firem
střední velikosti tam není (např. Robert Bosch GmbH se dohledá až přes
Wikidata). Pro takové dodavatele doplňte IČO/VAT do vstupu, nebo počítejte se
stavem `NENALEZENO` a ručním doplněním. Pro EU firmy mimo ČR a SR není veřejně
dostupný obor činnosti — NACE zůstane prázdné a kategorie se určí z názvu
firmy nebo z Wikidat.

## Taxonomie kategorií

Dvouúrovňová: **skupina** → **kategorie s kódem** (např. `ICT-03  Cloud, hosting
a datová centra`). Cca 95 kategorií ve 14 skupinách: ICT a technologie,
Profesní služby, Finanční služby, Lidské zdroje, Marketing a média, Správa
objektů a provoz, Bezpečnost, Logistika a doprava, Energie a utility, Materiál
a suroviny, Technologie a stroje, Stavebnictví, Obchod, Zdravotnictví, Odpady
a životní prostředí, Veřejný a neziskový sektor, Ostatní.

Zařazení probíhá v tomto pořadí:

1. **podle NACE** – u českých firem se použije *převažující činnost* z registru
   RES (pole `czNacePrevazujici2008`). Seznam všech NACE, který ARES vrací,
   je řazen vzestupně podle kódu, ne podle významu, takže se na jeho pořadí
   nedá spolehnout – proto ten druhý dotaz.
2. **podle klíčových slov** v názvu firmy a v oboru z Wikidat – když NACE není.
3. `XXX-00 Nezařazeno` – vyžaduje ruční doplnění. Sloupec **Zařazeno podle**
   říká, která z cest se uplatnila.

### Úprava taxonomie

```bash
python3 dodavatele.py --dump-taxonomy taxonomie.json    # export
# ... úprava v editoru ...
python3 dodavatele.py vstup.csv --taxonomy taxonomie.json
```

JSON obsahuje číselník kategorií, mapu NACE → kategorie, klíčová slova
i převod SIC → NACE. Alternativně lze upravit přímo `taxonomie.py`.

## Přepínače

```
-o, --vystup SOUBOR     .xlsx nebo .csv (výchozí dodavatele_vystup.xlsx)
--kompakt               jen základní sloupce
--workers N             souběžné dotazy (výchozí 4)
--prodleva S            minimální odstup dotazů na jeden server (výchozí 0.25 s)
--pocet N               kolik kandidátů z rejstříku načíst (výchozí 30)
--prah-ok 0.90          skóre shody názvu pro automatické přijetí
--prah-overit 0.72      pod tímto skóre je záznam nenalezený
--stnr2 REŽIM           auto | registrace | ico | dic | zadne
--vies                  ověřit DIČ v EU (pomalejší, jeden dotaz navíc na firmu)
--bez-ares/-sk/-gleif/-edgar/-wikidata    vypnutí jednotlivých zdrojů
--cache SOUBOR          keš odpovědí (výchozí .dodavatele_cache.json)
--sloupec NÁZEV         název sloupce se jménem firmy, když se neurčí sám
--oddelovac ;           oddělovač pro CSV výstup
--ua "..."              User-Agent; SEC vyžaduje kontaktní e-mail
```

## Poznámky k provozu

* **Keš** (`.dodavatele_cache.json`) drží odpovědi rejstříků, takže opakovaný
  běh nad stejným seznamem je téměř okamžitý. Smažte ji, chcete-li čerstvá data.
* **Zatížení rejstříků** – výchozí nastavení (4 vlákna, 0,25 s na server) je
  ohleduplné. Při tisících firem spíš zvyšte `--prodleva`, než abyste přidávali
  vlákna.
* **User-Agent** – SEC EDGAR vyžaduje v hlavičce kontaktní e-mail. Nastavte
  `--ua "nazev-firmy/1.0 (vas@email.cz)"`, jinak může začít odmítat dotazy.
* Ověřujte řádky se stavem jiným než `OK` a kategorii `XXX-00`; skript je
  vypisuje na konci běhu.

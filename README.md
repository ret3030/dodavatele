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
a datová centra`). Je to vlastní návrh, ne převzatý standard — 95 kategorií
v 17 skupinách. Kód kategorie je zkratka skupiny + pořadové číslo.

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

### Číselník kategorií

Kompletní seznam je i v listu **Číselník kategorií** ve vygenerovaném XLSX
(tam navíc s počtem dodavatelů v každé kategorii).

<details>
<summary>Zobrazit všech 95 kategorií</summary>

#### Bezpečnost

| kód | kategorie |
|---|---|
| SEC-01 | Fyzická ostraha a bezpečnostní služby |
| SEC-02 | Bezpečnostní technologie (EZS, CCTV, přístupové systémy) |

#### Energie a utility

| kód | kategorie |
|---|---|
| ENE-01 | Dodávka elektřiny a plynu |
| ENE-02 | Teplo a energetické služby |
| ENE-03 | Paliva a pohonné hmoty |
| ENE-04 | Vodné, stočné a vodohospodářské služby |

#### Finanční služby

| kód | kategorie |
|---|---|
| FIN-01 | Bankovní služby |
| FIN-02 | Platební a zúčtovací služby |
| FIN-03 | Pojištění a zajištění |
| FIN-04 | Leasing, úvěry a financování |
| FIN-05 | Ostatní finanční a investiční služby |
| FIN-06 | Inkaso pohledávek a kreditní služby |

#### ICT a technologie

| kód | kategorie |
|---|---|
| ICT-01 | Vývoj software a aplikací na zakázku |
| ICT-02 | Software, licence a SaaS |
| ICT-03 | Cloud, hosting a datová centra |
| ICT-04 | Správa IT a managed services |
| ICT-05 | IT poradenství a systémová integrace |
| ICT-06 | Kybernetická bezpečnost |
| ICT-07 | Hardware a koncová zařízení |
| ICT-08 | Síťová a komunikační infrastruktura |
| ICT-09 | Telekomunikační služby a konektivita |
| ICT-10 | Zpracování dat, BPO a sdílené služby |
| ICT-11 | Servis a likvidace výpočetní techniky |
| ICT-12 | Internetové portály a online služby |

#### Lidské zdroje

| kód | kategorie |
|---|---|
| HR-01 | Nábor a personální agentury |
| HR-02 | Agenturní zaměstnávání a dočasné přidělení |
| HR-03 | Mzdové a personální služby (payroll) |
| HR-04 | Školení a vzdělávání |
| HR-05 | Benefity a péče o zaměstnance |

#### Logistika a doprava

| kód | kategorie |
|---|---|
| LOG-01 | Silniční a železniční doprava |
| LOG-02 | Letecká a námořní přeprava |
| LOG-03 | Zasílatelství a spedice |
| LOG-04 | Skladování a logistické služby |
| LOG-05 | Kurýrní a poštovní služby |

#### Marketing a média

| kód | kategorie |
|---|---|
| MKT-01 | Reklamní a mediální agentury |
| MKT-02 | Průzkum trhu a analytika |
| MKT-03 | Tisk, polygrafie a reklamní produkce |
| MKT-04 | Eventy, konference a veletrhy |
| MKT-05 | Audiovizuální produkce a vysílání |

#### Materiál a suroviny

| kód | kategorie |
|---|---|
| MAT-01 | Kovy a hutní materiál |
| MAT-02 | Chemické látky a přípravky |
| MAT-03 | Plasty, pryž a kompozity |
| MAT-04 | Papír, obaly a obalové materiály |
| MAT-05 | Stavební hmoty a nekovové materiály |
| MAT-06 | Textil, oděvy a OOPP |
| MAT-07 | Elektronické a elektrotechnické komponenty |
| MAT-08 | Potraviny a nápoje |
| MAT-09 | Zemědělské a lesní suroviny |
| MAT-10 | Nerostné suroviny a těžba |
| MAT-11 | Dřevo a výrobky ze dřeva |

#### Nezařazeno

| kód | kategorie |
|---|---|
| XXX-00 | Nezařazeno – nutné ruční doplnění |

#### Obchod

| kód | kategorie |
|---|---|
| OBC-01 | Velkoobchod a distribuce |
| OBC-02 | Maloobchod a drobný nákup |
| OBC-03 | Prodej a servis motorových vozidel |

#### Odpady a životní prostředí

| kód | kategorie |
|---|---|
| ODP-01 | Odpadové hospodářství |
| ODP-02 | Skartace a likvidace nosičů dat |
| ODP-03 | Sanace a environmentální služby |

#### Ostatní

| kód | kategorie |
|---|---|
| OST-01 | Kultura, sport a volný čas |
| OST-02 | Ostatní osobní a podpůrné služby |

#### Profesní služby

| kód | kategorie |
|---|---|
| PRO-01 | Právní služby |
| PRO-02 | Účetní a daňové služby |
| PRO-03 | Audit a assurance |
| PRO-04 | Manažerské a procesní poradenství |
| PRO-05 | Inženýring, projekce a architektura |
| PRO-06 | Certifikace, zkušebnictví a inspekce |
| PRO-07 | Výzkum a vývoj |
| PRO-08 | Překlady, jazykové a redakční služby |
| PRO-09 | Ostatní profesní a technické služby |

#### Správa objektů a provoz

| kód | kategorie |
|---|---|
| FAC-01 | Úklidové služby |
| FAC-02 | Facility management |
| FAC-03 | Údržba budov a technických zařízení |
| FAC-04 | Stravování a catering |
| FAC-05 | Pronájem prostor a nemovitostí |
| FAC-06 | Kancelářské potřeby a drobné vybavení |
| FAC-07 | Nábytek a interiéry |
| FAC-08 | Ubytovací a cestovní služby |

#### Stavebnictví

| kód | kategorie |
|---|---|
| STA-01 | Pozemní stavby a investiční výstavba |
| STA-02 | Inženýrské stavitelství |
| STA-03 | Specializované stavební práce |
| STA-04 | Elektroinstalace a slaboproud |

#### Technologie a stroje

| kód | kategorie |
|---|---|
| TEC-01 | Výrobní stroje a zařízení |
| TEC-02 | Měřicí, řídicí a regulační technika (OT) |
| TEC-03 | Servis, opravy a instalace strojů |
| TEC-04 | Elektrická zařízení a pohony |
| TEC-05 | Dopravní prostředky a jejich díly |
| TEC-06 | Pronájem techniky a vozidel |
| TEC-07 | Kovové konstrukce a díly |

#### Veřejný a neziskový sektor

| kód | kategorie |
|---|---|
| VER-01 | Veřejná správa a státní instituce |
| VER-02 | Asociace, spolky a neziskové organizace |
| VER-03 | Vzdělávací instituce |

#### Zdravotnictví

| kód | kategorie |
|---|---|
| ZDR-01 | Zdravotní péče a pracovnělékařské služby |
| ZDR-02 | Laboratoře a diagnostika |
| ZDR-03 | Farmacie a zdravotnický materiál |
| ZDR-04 | Sociální služby |
| ZDR-05 | Veterinární služby |

</details>

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
--cache SOUBOR          keš odpovědí (výchozí .dodavatele_cache.json.gz)
--sloupec NÁZEV         název sloupce se jménem firmy, když se neurčí sám
--oddelovac ;           oddělovač pro CSV výstup
--ua "..."              User-Agent; SEC vyžaduje kontaktní e-mail
```

## Poznámky k provozu

* **Keš** (`.dodavatele_cache.json.gz`) drží odpovědi rejstříků, takže opakovaný
  běh nad stejným seznamem je téměř okamžitý. Smažte ji, chcete-li čerstvá data.
* **Zatížení rejstříků** – výchozí nastavení (4 vlákna, 0,25 s na server) je
  ohleduplné. Při tisících firem spíš zvyšte `--prodleva`, než abyste přidávali
  vlákna.
* **User-Agent** – SEC EDGAR vyžaduje v hlavičce kontaktní e-mail. Nastavte
  `--ua "nazev-firmy/1.0 (vas@email.cz)"`, jinak může začít odmítat dotazy.
* Ověřujte řádky se stavem jiným než `OK` a kategorii `XXX-00`; skript je
  vypisuje na konci běhu.

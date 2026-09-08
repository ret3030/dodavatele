# Revidovaná taxonomie kategorií dodavatelů (v2)

**74 kategorií v 11 skupinách** (původní kolegova taxonomie: 83 / 11).
Sjednoceno v `../taxonomie_data.json` – čte ji modul `kategorizace/` i hlavní
`dodavatele.py` (včetně číselníku v promptu pro LLM krok). `MAPA_ZE_STARE`
v témže souboru = úplný převod starý kód → nový.

## Proč revize

1. **Sourozenecké kategorie, které nešlo z webu odlišit**, se slučovaly –
   klasifikátor (ani člověk) je z webu firmy nerozezná, protože firma dělá
   obojí. Např. „součástky – výroba" × „součástky – distribuce".
2. **Navazující krok je ISO 27001** – rozhoduje se, jestli dodavatel spadá
   do ICT a jak je kritický. Proto je skupina IT vyčleněná, vyčištěná
   a rozšířená o **cloud/hosting** a **kybernetickou bezpečnost** (samostatné
   kategorie), a každá kategorie má příznak **ICT relevance** (`ano` /
   `hraniční` / `ne`).
3. **Chybějící typy dodavatelů** – přidána **Fyzická ostraha a bezpečnostní
   služby** (Securitas, G4S…), **Odpadové hospodářství** vyčleněné od energií.
4. **Zrušené odpadkové koše** – „Firemní a ostatní", „Ostatní / k ověření"
   i XXX-00 dělaly totéž; zůstává jen XXX-00.

## Skupiny (11)

| skupina | ICT relevance | kategorií |
|---|---|---|
| IT, telekomunikace a kyberbezpečnost | **ano** (celá) | 8 |
| Elektronika a elektrotechnika | hraniční (ELE-05 ano) | 9 |
| Měření, metrologie a laboratoře | ne | 3 |
| Stroje, automatizace a výrobní technologie | ne (STR-01 hraniční) | 8 |
| Výroba dílů a zpracování materiálů | ne | 9 |
| Materiál, nářadí a provozní zásobování | ne | 7 |
| Stavby, energie a facility | ne (FAC-08/09 hraniční) | 9 |
| Doprava, logistika a vozidla | ne | 4 |
| Profesní a poradenské služby | ne (PRO-01/02/05/06 hraniční) | 7 |
| Marketing, tisk, vzdělávání a firemní služby | ne (FIR-08 hraniční) | 9 |
| Nezařazeno | hraniční | 1 |

`ano` = dodavatel typicky zpracovává/uchovává naše informace nebo se
připojuje do našich systémů. `hraniční` = přístup k datům nebo do prostor
podle konkrétní smlouvy (auditor, advokát, personální agentura, ostraha,
poskytovatel benefitů, průmyslová automatizace/OT). `ne` = zboží/služby bez
přístupu k informačním aktivům.

## Hlavní změny oproti kolegově verzi

**Sloučeno** (18 → 9): součástky výroba+distribuce; konektory + kabely + VF
konektory; DPS + „elektronika a měřicí technika – výroba" rozdělené jinam;
měřicí technika + zkušební přípravky; obráběcí stroje + SMT technologie;
manipulační + zdvihací technika; kovoobrábění + přesné lisování; nářadí +
spojovací materiál; kancelářské + provozní vybavení; OOPP + značení; projekce
+ technické expertizy; vzdělávání + odborná literatura; ubytování + konference;
benefity + sport/rekreace; komory + veřejná správa + kultura.

**Nově vzniklo**: Cloud/hosting/datacentra, Kybernetická bezpečnost,
Vestavné systémy a IoT, Rozvaděče a napájecí technika, Fyzická ostraha,
Odpadové hospodářství (od energií), Nemovitosti (od facility managementu).

**Přeřazeno do IT**: identifikace/čárové kódy, síťová infrastruktura.

`MAPA_ZE_STARE` v JSONu = úplný převod starý kód → nový (pro migraci už
zařazených výstupů; `taxonomie.prevod_ze_stare()`).

## Naměřený dopad (stejný vzorek 246 firem)

| metrika | stará taxonomie | v2 |
|---|---|---|
| AUTO – pokrytí | 37 % | 38 % |
| AUTO – přesnost listu | 95,7 % | 95,7 % |
| AUTO – přesnost skupiny | 97,8 % | 96,8 % |
| **AUTO – shoda ICT příznaku** | – | **98,9 %** |
| shoda ICT příznaku (všechny firmy) | – | 79,3 % |
| top-1 list (všechny firmy) | 61,4 % | 61,8 % |

Restrukturalizace sama přesnost listu neposunula (merge sourozenců pomohl,
ale je jich na vzorku málo) – hlavní přínos je **čistá skupina IT + ICT
příznak, který navazující krok potřebuje, a ten je na AUTO větvi na 99 %**.

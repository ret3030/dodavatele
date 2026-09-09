# Revidovaná taxonomie kategorií dodavatelů (v2)

**82 kategorií v 12 skupinách** (původní kolegova taxonomie: 83 / 11).
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

## Skupiny (12)

| skupina | ICT relevance | kategorií |
|---|---|---|
| IT, telekomunikace a kyberbezpečnost | **ano** (celá) | 8 |
| Elektronika a elektrotechnika | hraniční (ELE-05 ano) | 9 |
| Měření, metrologie a laboratoře | ne | 3 |
| Stroje, automatizace a výrobní technologie | ne (STR-01 hraniční) | 8 |
| Výroba dílů a zpracování materiálů | ne | 9 |
| Materiál, nářadí a provozní zásobování | ne | 7 |
| Stavby, energie a facility | ne (FAC-08/09 hraniční) | 9 |
| Doprava, logistika a vozidla | ne | 6 |
| Profesní a poradenské služby | ne (PRO-01/02/05/06 hraniční) | 7 |
| Marketing, tisk, vzdělávání a firemní služby | ne (FIR-08/10 hraniční) | 10 |
| Obchod a ostatní odvětví | ne (OBH-03 hraniční) | 4 |
| Nezařazeno | hraniční | 2 |

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

## Doplněno po prvním ostrém běhu (v2.1)

Na reálném seznamu kreditorů se ukázalo, že sedm typů dodavatelů nemělo kam
spadnout a končily jako `XXX-00`. Přibyly proto:

| kód | kategorie | ICT | proč |
|---|---|---|---|
| LOG-05 | Letecká a dopravní technika | ne | technika, ne přepravní služba — do LOG-01 nepatří |
| LOG-06 | Paliva a PHM | ne | komoditní nákup pro vozový park, ne utilita jako FAC-05 |
| FIR-10 | Cestovní služby | hraniční | cestovka drží osobní údaje zaměstnanců (pasy, itineráře) |
| OBH-01 | Nespecializovaný obchod a zprostředkování | ne | obchodník bez oborové specializace — dřív nutně `XXX-00` |
| OBH-02 | Spotřební a drogistické zboží | ne | vedle PROV-07 (potraviny) chyběla drogerie a spotřební zboží |
| OBH-03 | Zdravotnická technika a služby | hraniční | pracovnělékařská služba zpracovává zdravotní údaje zaměstnanců |
| OBH-04 | Zemědělství, lesnictví a péče o zeleň | ne | údržba zeleně je běžný dodavatel, spadala mimo FAC i PROV |

`XXX-00` tím zůstává jen pro firmy, o kterých se opravdu nic neví — ne pro
obory, na které v číselníku nebylo místo.

## XXX-01: OSVČ, u které není z čeho vyjít

Jediný kód, který nepřiděluje model, ale nástroj — podle právní formy z ARES
(100–109 = fyzická osoba). Fyzická osoba není v obchodním rejstříku, takže
u ní neexistuje zapsaný předmět podnikání; když se nenajde ani NACE, web nebo
Wikidata, zbyde jméno člověka a to obor neprozradí. Taková firma se modelu
vůbec neposílá a `XXX-01` říká „tady se nedohledalo nic, zařaďte ručně“ —
na rozdíl od `XXX-00`, které znamená „model to nedokázal zařadit“.

Do číselníku v promptu se `XXX-01` záměrně nedává, jinak by ho model začal
přidělovat sám a značka by přestala znamenat, co znamená.

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

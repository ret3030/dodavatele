"""
Pravidla pro deterministicke zarazeni dodavatele do kategorie (taxonomie v2 -
74 kategorii / 11 skupin, viz ../taxonomie_data.json a TAXONOMIE_V2.md).

Pro kazdy kod:
  "pos": seznam (n-tice frazi, vaha) - kdyz se fraze najde v textu ze SERP
         nebo z meta popisu webu firmy, pripocte se  vaha * vaha_zdroje
         (kazda fraze za jeden zdroj jen jednou - nerozhoduje pocet vyskytu).
  "neg": totez, ale odecita - na rozliseni sourozeneckych kategorii.

Fraze se pisou cesky s diakritikou; pri nacteni se normalizuji stejne jako
text (bez diakritiky, mala pismena, lehky stemmer), takze "výrobce
kondenzátorů" sedne na "vyrob kondenzator".
"""

from .normalizace import normalizuj_frazi

# ---------------------------------------------------------------------------
# IT, TELEKOMUNIKACE A KYBERBEZPECNOST
# ---------------------------------------------------------------------------
_ICT = {
    "ICT-01": {  # IT hardware a výpočetní technika
        "pos": [
            (("výpočetní technika", "dodávky výpočetní techniky", "it hardware",
              "notebooky a počítače", "servery a úložiště", "pracovní stanice",
              "prodej počítačů", "počítačové sestavy", "dodavatel it hardware",
              "tiskárny a spotřební materiál", "it komodity", "reseller hardware"), 3.0),
            (("notebooky", "monitory", "servery", "hardware", "periferie"), 0.8),
        ],
        "neg": [
            (("vývoj software", "softwarové licence", "programování", "cloudové služby"), 2.0),
        ],
    },
    "ICT-02": {  # Software, licence a vývoj aplikací
        "pos": [
            (("vývoj software", "vývoj softwaru", "softwarová řešení", "softwarové licence",
              "software na míru", "informační systém", "erp systém", "vývoj aplikací",
              "webové aplikace", "mobilní aplikace vývoj", "software development",
              "dodavatel software", "implementace informačního systému", "tvorba software"), 3.0),
            (("software", "aplikace", "licence", "saas aplikace"), 0.8),
        ],
        "neg": [
            (("prodej počítačů", "výpočetní technika", "datové centrum", "penetrační testy"), 1.5),
            (("projekční kancelář", "projektová dokumentace", "inženýrská činnost ve výstavbě",
              "autorizovaný inženýr"), 2.5),
        ],
    },
    "ICT-03": {  # IT služby, podpora a systémová integrace
        "pos": [
            (("it služby", "it podpora", "servisní podpora it", "systémová integrace",
              "outsourcing it", "managed services", "správa it infrastruktury",
              "helpdesk a servicedesk", "provoz informačních systémů", "it konzultace",
              "implementace a integrace", "digitalizace procesů"), 3.0),
            (("servisní smlouva", "sla podpora", "administrace serverů"), 0.8),
        ],
    },
    "ICT-04": {  # Cloud, hosting a datová centra
        "pos": [
            (("cloudové služby", "cloud computing", "poskytovatel cloudu", "hosting",
              "webhosting", "serverhosting", "datové centrum", "datacentrum", "kolokace",
              "housing serverů", "privátní cloud", "public cloud", "iaas", "paas",
              "zálohování do cloudu", "cloud infrastructure", "pronájem serverů"), 3.0),
        ],
    },
    "ICT-05": {  # Kybernetická bezpečnost
        "pos": [
            (("kybernetická bezpečnost", "kyberbezpečnost", "penetrační testy",
              "bezpečnostní audit it", "soc jako služba", "security operations center",
              "řízení zranitelností", "siem", "ochrana před kybernetickými hrozbami",
              "cyber security", "etický hacking", "bezpečnost informací", "dohled nad kyberbezpečností",
              "zabezpečení sítí a dat", "iso 27001 implementace"), 3.0),
        ],
    },
    "ICT-06": {  # Telekomunikace a konektivita
        "pos": [
            (("telekomunikace", "telekomunikační služby", "mobilní operátor",
              "poskytovatel internetu", "poskytovatel připojení", "internetové připojení",
              "hlasové služby", "voip", "telefonní ústředny", "datové okruhy", "isp",
              "pronájem datových okruhů", "sim a mobilní tarify"), 3.0),
        ],
    },
    "ICT-07": {  # Síťová infrastruktura a strukturovaná kabeláž
        "pos": [
            (("síťová infrastruktura", "strukturovaná kabeláž", "datové sítě",
              "optické sítě", "aktivní síťové prvky", "switche a routery", "wifi sítě",
              "network infrastructure", "montáž datových rozvodů", "lan a wan",
              "páteřní síť", "budování počítačových sítí"), 3.0),
        ],
    },
    "ICT-08": {  # Identifikace, čárové kódy, RFID a sběr dat
        "pos": [
            (("čárové kódy", "čárový kód", "snímače čárových kódů", "čtečky čárových kódů",
              "rfid", "mobilní terminály", "tiskárny etiket", "tiskárny čárových kódů",
              "značení zboží", "identifikace zboží", "barcode", "průmyslové skenery",
              "sběr dat ve skladu", "systémy automatické identifikace"), 3.0),
        ],
    },
}

# ---------------------------------------------------------------------------
# ELEKTRONIKA A ELEKTROTECHNIKA
# ---------------------------------------------------------------------------
_ELE = {
    "ELE-01": {  # Elektronické součástky - výroba a distribuce
        "pos": [
            (("elektronické součástky", "distribuce elektronických součástek",
              "distributor součástek", "distributor elektronických součástek",
              "katalogový distributor", "součástky skladem", "electronic components",
              "pasivní součástky", "aktivní součástky", "výrobce součástek",
              "výroba kondenzátorů", "výroba rezistorů", "výroba polovodičů",
              "výroba senzorů", "výkonové kondenzátory", "výroba relé",
              "součástková základna", "polovodiče"), 3.0),
        ],
    },
    "ELE-02": {  # Osazování a výroba DPS (EMS)
        "pos": [
            (("osazování desek plošných spojů", "osazování dps", "osazení dps",
              "osazování pcb", "pcb assembly", "pcba", "pick and place", "smt osazování",
              "osazovací linka", "výroba dps", "výroba pcb", "pájení přetavením",
              "selektivní pájení", "reflow", "montáž elektroniky na desky",
              "elektronická výroba na zakázku", "ems služby"), 3.0),
            (("deska plošných spojů", "desky plošných spojů", "plošné spoje",
              "printed circuit board", "tht osazení"), 1.5),
        ],
    },
    "ELE-03": {  # Vývoj a zakázková výroba elektroniky
        "pos": [
            (("vývoj a výroba elektroniky", "zakázková výroba elektroniky",
              "návrh a výroba elektroniky", "výroba elektronických zařízení",
              "vývoj elektroniky na zakázku", "contract electronics manufacturer",
              "výroba přístrojů", "prototypová výroba elektroniky",
              "hardwarový vývoj", "návrh elektronických obvodů"), 3.0),
        ],
    },
    "ELE-04": {  # Konektory, kabely a kabelová konfekce
        "pos": [
            (("konektory", "konektorová technika", "průmyslové konektory", "svorkovnice",
              "kabelová konfekce", "výroba kabelových svazků", "kabelové svazky",
              "wire harness", "cable assembly", "crimpování", "kabely a vodiče",
              "silové kabely", "datové kabely", "koaxiální konektory", "rf konektory",
              "vysokofrekvenční konektory", "výrobce kabelů", "kabelové vývodky"), 3.0),
        ],
    },
    "ELE-05": {  # Vestavné a řídicí systémy, IoT zařízení
        "pos": [
            (("vestavné systémy", "embedded systémy", "řídicí jednotky", "řídicí systémy zařízení",
              "iot zařízení", "iot řešení", "průmyslový iot", "jednodeskové počítače",
              "telemetrie", "vzdálený monitoring zařízení", "firmware vývoj",
              "chytrá zařízení", "konektivita zařízení"), 3.0),
        ],
    },
    "ELE-06": {  # Optika, fotonika a laserová technika
        "pos": [
            (("fotonika", "laserová technika", "laserové diody", "optická vlákna",
              "optické komponenty", "optické čočky", "spektroskopie", "photonics",
              "optoelektronika", "laserové zdroje", "optická měření", "krystaly pro optiku"), 3.0),
        ],
        "neg": [
            (("řezání laserem", "laserové řezání plechu", "laserové gravírování"), 2.5),
        ],
    },
    "ELE-07": {  # Čisté prostory a ESD ochrana
        "pos": [
            (("čisté prostory", "čistý prostor", "cleanroom", "clean room",
              "laminární box", "laminární proudění", "kontrola kontaminace",
              "monitoring částic", "esd ochrana", "esd podlaha", "antistatická podlaha",
              "antistatické vybavení", "ionizátor", "esd obuv", "esd oděv", "antistatic"), 3.0),
        ],
    },
    "ELE-08": {  # Elektroinstalační materiál a silnoproud
        "pos": [
            (("elektroinstalace", "elektroinstalační materiál", "elektromontáže",
              "revize elektro", "elektrikářské práce", "silnoproud", "kabelové rozvody nn",
              "velkoobchod elektroinstalačního materiálu", "elektro velkoobchod",
              "elektroinstalační práce", "montáž elektrických rozvodů"), 3.0),
        ],
        "neg": [
            (("slaboproud", "kamerové systémy", "svítidla a osvětlení"), 1.5),
        ],
    },
    "ELE-09": {  # Rozvaděče, transformátory a napájecí technika
        "pos": [
            (("výroba rozvaděčů", "rozvaděče nn", "rozvaděče vn", "montáž rozvaděčů",
              "výroba transformátorů", "distribuční transformátory", "transformátorové stanice",
              "napájecí zdroje", "záložní zdroje", "ups systémy", "usměrňovače",
              "kompenzace jalového výkonu", "energetická zařízení nn"), 3.0),
        ],
        "neg": [
            (("ocelové konstrukce", "mostní konstrukce", "svařované konstrukce"), 2.5),
        ],
    },
}

# ---------------------------------------------------------------------------
# MERENI, METROLOGIE A LABORATORE
# ---------------------------------------------------------------------------
_MET = {
    "MET-01": {  # Měřicí a testovací technika - prodej a servis
        "pos": [
            (("měřicí technika", "měřicí přístroje", "testovací technika", "měřidla prodej a servis",
              "multimetry", "osciloskopy", "termokamery", "test and measurement",
              "měřicí systémy", "snímače a převodníky", "zkušební přípravky",
              "kontaktovací technika", "měřicí a testovací systémy"), 3.0),
            (("měření", "senzory", "dataloggery"), 0.6),
        ],
        "neg": [
            (("kalibrační laboratoř", "akreditovaná kalibrace"), 2.0),
        ],
    },
    "MET-02": {  # Kalibrace, metrologie a technické zkoušky
        "pos": [
            (("kalibrace", "kalibrační laboratoř", "akreditovaná kalibrace", "metrologie",
              "metrologické služby", "ověřování měřidel", "návaznost měřidel",
              "technické zkoušky", "zkušební laboratoř", "calibration laboratory",
              "kalibrační list", "etalon"), 3.0),
        ],
    },
    "MET-03": {  # Laboratorní a analytická technika
        "pos": [
            (("laboratorní technika", "laboratorní přístroje", "laboratorní vybavení",
              "laboratorní nábytek", "analytické přístroje", "mikroskopy", "centrifugy",
              "laboratory equipment", "spektrofotometry", "chromatografy",
              "laboratorní sklo", "reagencie a chemikálie"), 3.0),
        ],
    },
}

# ---------------------------------------------------------------------------
# STROJE, AUTOMATIZACE A VYROBNI TECHNOLOGIE
# ---------------------------------------------------------------------------
_STR = {
    "STR-01": {  # Průmyslová automatizace, robotika a řídicí systémy
        "pos": [
            (("průmyslová automatizace", "průmyslové roboty", "robotika", "robotické buňky",
              "automatizační technika", "plc programování", "řídicí systémy strojů",
              "kolaborativní roboty", "industrial automation", "jednoúčelové stroje",
              "automatizace výroby", "manipulátory", "scada systémy", "průmyslové řízení"), 3.0),
        ],
    },
    "STR-02": {  # Obráběcí stroje a výrobní technologie - prodej a servis
        "pos": [
            (("obráběcí stroje", "prodej obráběcích strojů", "cnc stroje prodej",
              "cnc soustruhy", "cnc frézky", "servis obráběcích strojů", "machine tools",
              "dodavatel obráběcích strojů", "osazovací automaty", "smt linka",
              "pájecí pece", "výrobní technologie pro elektroniku", "tvářecí stroje",
              "výrobní stroje a technologie"), 3.0),
        ],
        "neg": [
            (("zakázkové obrábění", "kovoobrábění na zakázku", "obrobna"), 2.5),
        ],
    },
    "STR-03": {  # Průmyslové stroje - servis, opravy a montáže
        "pos": [
            (("servis průmyslových strojů", "opravy strojů", "generální opravy strojů",
              "retrofit strojů", "údržba výrobních zařízení", "montáž technologických celků",
              "industrial machinery service", "stěhování strojů", "seřizování strojů",
              "servis strojních zařízení"), 3.0),
        ],
    },
    "STR-04": {  # Řezné nástroje a nástrojařství
        "pos": [
            (("řezné nástroje", "nástrojárna", "nástrojařství", "výroba forem",
              "výroba střižných nástrojů", "frézy a vrtáky", "vyměnitelné břitové destičky",
              "cutting tools", "ostření nástrojů", "monolitní nástroje", "závitníky",
              "nástroje pro obrábění"), 3.0),
        ],
    },
    "STR-05": {  # Čerpadla, armatury a regulační technika
        "pos": [
            (("čerpadla", "průmyslová čerpadla", "armatury", "průmyslové armatury",
              "regulační technika", "regulační ventily", "dávkovací čerpadla",
              "uzavírací armatury", "kulové kohouty", "pumps and valves", "šoupátka",
              "čerpací technika"), 3.0),
        ],
    },
    "STR-06": {  # Kompresory a technika stlačeného vzduchu
        "pos": [
            (("kompresory", "šroubové kompresory", "stlačený vzduch",
              "rozvody stlačeného vzduchu", "pneumatické systémy", "sušičky vzduchu",
              "úprava stlačeného vzduchu", "compressed air", "pístové kompresory",
              "vývěvy"), 3.0),
        ],
    },
    "STR-07": {  # Manipulační, skladová a zdvihací technika
        "pos": [
            (("vysokozdvižné vozíky", "manipulační technika", "paletové vozíky",
              "regálové systémy", "skladová technika", "vzv", "čelní vozíky", "forklift",
              "skladové regály", "paletové regály", "jeřáby", "mostové jeřáby",
              "zdvihací technika", "vázací prostředky", "pracovní plošiny", "kladkostroje",
              "manipulace a skladování"), 3.0),
        ],
    },
    "STR-08": {  # Vzduchotechnika, chlazení a klimatizace
        "pos": [
            (("vzduchotechnika", "klimatizace", "vzt", "rekuperace tepla", "chlazení budov",
              "servis klimatizací", "montáž vzduchotechniky", "hvac", "klimatizační jednotky",
              "větrání průmyslových hal", "průmyslové chlazení", "chladicí technika"), 3.0),
        ],
    },
}

# ---------------------------------------------------------------------------
# VYROBA DILU A ZPRACOVANI MATERIALU
# ---------------------------------------------------------------------------
_MAT = {
    "MAT-01": {  # Kovoobrábění a přesné kovové díly
        "pos": [
            (("kovoobrábění", "cnc obrábění", "zakázkové obrábění", "strojírenská výroba",
              "obrobna", "soustružení a frézování", "kooperace v obrábění", "třískové obrábění",
              "machining services", "výroba dílů na cnc", "přesné kovové díly",
              "lisování plechu", "výlisky z plechu", "přesné lisování", "kovové výlisky",
              "výroba přesných dílů"), 3.0),
        ],
        "neg": [
            (("prodej obráběcích strojů", "servis obráběcích strojů"), 2.0),
        ],
    },
    "MAT-02": {  # Kovové konstrukce, svařování a zámečnictví
        "pos": [
            (("kovové konstrukce", "ocelové konstrukce", "svařování", "svařované díly",
              "zámečnictví", "zámečnická výroba", "výroba ocelových konstrukcí", "welding",
              "kovovýroba konstrukce", "montáž ocelových konstrukcí", "svařované rámy"), 3.0),
        ],
    },
    "MAT-03": {  # Povrchové úpravy a galvanika
        "pos": [
            (("povrchové úpravy kovů", "galvanika", "galvanické pokovení", "práškové lakování",
              "žárové zinkování", "eloxování", "černění", "chromování", "niklování",
              "surface treatment", "kataforéza", "pískování a lakování"), 3.0),
        ],
    },
    "MAT-04": {  # Plastové a pryžové díly - výroba
        "pos": [
            (("vstřikování plastů", "výroba plastových dílů", "plastové výlisky", "lisování pryže",
              "pryžové díly", "technické výlisky", "gumové a pryžové výrobky", "injection moulding",
              "vytlačování plastů", "výroba těsnění z pryže", "formy pro vstřikování"), 3.0),
        ],
        "neg": [
            (("technické plasty polotovary", "desky tyče profily z plastu"), 2.0),
        ],
    },
    "MAT-05": {  # 3D tisk a aditivní výroba
        "pos": [
            (("3d tisk", "aditivní výroba", "3d tiskárny", "tisk prototypů", "rapid prototyping",
              "sls tisk", "sla tisk", "fdm tisk", "additive manufacturing", "3d skenování a tisk"), 3.0),
        ],
    },
    "MAT-06": {  # Hutní materiál a kovy
        "pos": [
            (("hutní materiál", "hutní materiály", "velkoobchod s hutním materiálem",
              "velkoobchod hutního materiálu", "prodej hutního materiálu", "velkoobchod oceli",
              "ocel a plechy", "hutní a spojovací materiál", "ocelové profily",
              "plechy a profily", "tyče a trubky", "neželezné kovy", "hliník měď mosaz",
              "pálení plechů na míru", "dělení hutního materiálu", "steel service center",
              "prodej nerezové oceli"), 3.0),
        ],
    },
    "MAT-07": {  # Technické plasty, pryž a polotovary
        "pos": [
            (("technické plasty", "plastové polotovary", "polotovary z plastů",
              "desky tyče a profily", "konstrukční plasty", "technická guma v metráži",
              "silikonové profily", "těsnicí materiály v metráži", "semi finished plastics",
              "kompozitní polotovary", "plasty v metráži"), 3.0),
        ],
    },
    "MAT-08": {  # Průmyslová chemie, maziva a lepidla
        "pos": [
            (("průmyslová chemie", "maziva", "průmyslová maziva", "lepidla a tmely",
              "technické oleje", "mazací technika", "řezné kapaliny",
              "chemické přípravky pro průmysl", "lubricants", "odmašťovací přípravky",
              "epoxidové pryskyřice"), 3.0),
        ],
    },
    "MAT-09": {  # Obaly a balicí materiál
        "pos": [
            (("obalový materiál", "výroba obalů", "kartonáž", "balicí materiál",
              "přepravní obaly", "dřevěné obaly a palety", "stretch fólie", "packaging",
              "obaly na míru", "vlnitá lepenka", "pěnové výplně", "balicí technika"), 3.0),
        ],
    },
}

# ---------------------------------------------------------------------------
# MATERIAL, NARADI A PROVOZNI ZASOBOVANI
# ---------------------------------------------------------------------------
_PROV = {
    "PROV-01": {  # Nářadí, spojovací a upevňovací materiál
        "pos": [
            (("ruční nářadí", "elektrické nářadí", "profi nářadí", "dílenské potřeby",
              "dílenské vybavení", "aku nářadí", "pneumatické nářadí", "hand tools",
              "prodejna nářadí", "spojovací materiál", "šrouby a matice", "upevňovací technika",
              "hmoždinky", "kotevní technika", "fasteners", "nýty", "spojovací technika"), 3.0),
        ],
        "neg": [
            (("vyměnitelné břitové destičky", "nástrojárna"), 1.5),
        ],
    },
    "PROV-02": {  # Technický velkoobchod a MRO materiál
        "pos": [
            (("technický velkoobchod", "velkoobchod technický materiál", "mro materiál",
              "ložiska a řemeny", "hadice a spojky", "těsnění a manžety", "pohonná technika",
              "průmyslový spotřební materiál", "industrial supplies", "technická guma a plasty",
              "obchodní zastoupení výrobců", "výhradní zastoupení", "distribuce technického sortimentu"), 3.0),
        ],
    },
    "PROV-03": {  # Kancelářské a provozní vybavení a nábytek
        "pos": [
            (("kancelářské potřeby", "kancelářský papír", "psací potřeby", "tonery a náplně",
              "office supplies", "kancelářský nábytek", "dílenský nábytek", "provozní vybavení",
              "pracovní stoly", "kovový nábytek", "šatní skříně", "vybavení provozoven",
              "nábytek do kanceláří"), 3.0),
        ],
        "neg": [
            (("skladové regály", "paletové regály"), 1.5),
        ],
    },
    "PROV-04": {  # OOPP, BOZP a bezpečnostní značení
        "pos": [
            (("osobní ochranné pracovní prostředky", "oopp", "ochranné pomůcky",
              "pracovní rukavice", "ochrana zraku", "ochrana sluchu", "respirátory",
              "bezpečnost práce", "služby bozp", "ppe", "pracovní obuv",
              "bezpečnostní značení", "bezpečnostní tabulky", "značení podlah",
              "průmyslové značení", "výstražné tabulky"), 3.0),
        ],
        "neg": [
            (("textilní servis", "praní prádla", "pronájem pracovních oděvů"), 1.5),
        ],
    },
    "PROV-05": {  # Pracovní oděvy, textilní servis a úklid
        "pos": [
            (("pracovní oděvy", "montérky", "pracovní oblečení", "textilní servis",
              "pronájem pracovních oděvů", "praní prádla", "prádelna", "úklidové služby",
              "úklid budov", "pronájem rohoží", "čištění oděvů", "profesní úklid"), 3.0),
        ],
    },
    "PROV-06": {  # Osvětlení a světelná technika
        "pos": [
            (("osvětlení", "svítidla", "led osvětlení", "světelná technika",
              "průmyslové osvětlení", "nouzové osvětlení", "veřejné osvětlení",
              "lighting", "osvětlovací technika", "světelné zdroje", "výroba svítidel"), 3.0),
        ],
    },
    "PROV-07": {  # Potraviny a nápoje - velkoobchod
        "pos": [
            (("velkoobchod s potravinami", "distribuce potravin", "distribuce nápojů",
              "výrobce a distributor potravin", "food distributor", "pekárna", "cukrárna",
              "pražírna kávy", "káva do firem", "pitná voda do firem", "barelová voda",
              "vending", "zásobování gastro provozů"), 3.0),
        ],
    },
}

# ---------------------------------------------------------------------------
# STAVBY, ENERGIE A FACILITY
# ---------------------------------------------------------------------------
_FAC = {
    "FAC-01": {  # Stavební práce a údržba budov
        "pos": [
            (("stavební práce", "stavební firma", "rekonstrukce budov", "údržba budov",
              "zednické práce", "generální dodavatel stavby", "stavební činnost",
              "opravy a údržba objektů", "malířské a natěračské práce", "construction company",
              "pozemní stavby", "výstavba a rekonstrukce"), 3.0),
        ],
    },
    "FAC-02": {  # Vytápění, vodoinstalace a topenářská technika
        "pos": [
            (("vytápění", "topenářství", "vodoinstalace", "instalatérské práce",
              "topenářská technika", "plynové kotle", "tepelná čerpadla montáž", "radiátory",
              "rozvody vody a topení", "koupelnové studio", "heating and plumbing",
              "velkoobchod topení a voda"), 3.0),
        ],
        "neg": [
            (("vzduchotechnika", "klimatizace"), 1.5),
        ],
    },
    "FAC-03": {  # Facility management a správa budov
        "pos": [
            (("facility management", "správa budov", "technická správa budov",
              "provoz budov", "údržba areálu", "integrované facility služby",
              "property services", "správa administrativních objektů", "facility služby"), 3.0),
        ],
        "neg": [
            (("realitní kancelář", "prodej nemovitostí", "developerský projekt"), 1.5),
        ],
    },
    "FAC-04": {  # Nemovitosti, pronájem a reality
        "pos": [
            (("realitní kancelář", "pronájem nemovitostí", "pronájem kancelářských prostor",
              "prodej nemovitostí", "developerská společnost", "developerský projekt",
              "správa nemovitostí", "real estate", "pronájem skladových hal",
              "investiční nemovitosti"), 3.0),
        ],
    },
    "FAC-05": {  # Energie a média (elektřina, plyn, teplo, voda)
        "pos": [
            (("dodávka elektřiny", "dodávka plynu", "obchodník s elektřinou", "obchodník s plynem",
              "dodavatel energií", "vodné a stočné", "vodárenská společnost", "teplárna",
              "dodávka tepla", "energetická skupina", "distribuce elektřiny",
              "obchod s energiemi", "dodavatel zemního plynu"), 3.0),
        ],
        "neg": [
            (("svoz odpadu", "odpadové hospodářství", "likvidace odpadu"), 2.0),
        ],
    },
    "FAC-06": {  # Odpadové hospodářství a recyklace
        "pos": [
            (("odpadové hospodářství", "svoz odpadu", "likvidace odpadu", "nakládání s odpady",
              "sběr a svoz odpadu", "recyklace odpadů", "výkup druhotných surovin", "sběrný dvůr",
              "zpracování odpadů", "ekologická likvidace", "waste management", "skládka odpadů"), 3.0),
        ],
        "neg": [
            (("dodavatel energií", "obchodník s elektřinou", "obchodník s plynem",
              "dodávka elektřiny a plynu"), 2.5),
        ],
    },
    "FAC-07": {  # Požární ochrana a revize vyhrazených zařízení
        "pos": [
            (("požární ochrana", "hasicí přístroje", "revize hasicích přístrojů",
              "požárně bezpečnostní řešení", "elektrická požární signalizace", "eps",
              "revize technických zařízení", "revize hydrantů", "servis požární techniky",
              "protipožární ucpávky", "fire protection", "revize vyhrazených zařízení"), 3.0),
        ],
    },
    "FAC-08": {  # Zabezpečovací, přístupové a slaboproudé systémy
        "pos": [
            (("zabezpečovací systémy", "elektronické zabezpečení", "ezs", "pzts",
              "kamerové systémy", "cctv", "přístupové systémy", "docházkové systémy",
              "slaboproudé systémy", "poplachové systémy", "access control", "obvodová ochrana",
              "integrace bezpečnostních technologií"), 3.0),
        ],
        "neg": [
            (("fyzická ostraha", "bezpečnostní agentura", "strážní služba"), 2.0),
        ],
    },
    "FAC-09": {  # Fyzická ostraha a bezpečnostní služby
        "pos": [
            (("fyzická ostraha", "ostraha objektů", "ostraha majetku a osob", "strážní služba",
              "bezpečnostní agentura", "bezpečnostní služba", "recepční a ostraha",
              "detektivní služby", "převoz peněz", "pult centralizované ochrany",
              "security services", "zásahová jednotka"), 3.0),
        ],
    },
}

# ---------------------------------------------------------------------------
# DOPRAVA, LOGISTIKA A VOZIDLA
# ---------------------------------------------------------------------------
_LOG = {
    "LOG-01": {  # Doprava, spedice a logistika
        "pos": [
            (("spedice", "zasilatelství", "logistické služby", "mezinárodní kamionová doprava",
              "silniční nákladní doprava", "skladová logistika", "logistické centrum",
              "freight forwarding", "3pl", "celní deklarace", "přeprava zboží", "kontraktní logistika"), 3.0),
        ],
        "neg": [
            (("kurýrní služby", "expresní balíková", "doručování balíků"), 1.5),
        ],
    },
    "LOG-02": {  # Kurýrní, expresní a poštovní služby
        "pos": [
            (("kurýrní služby", "expresní přeprava zásilek", "doručování zásilek",
              "doručování balíků", "balíková přeprava", "přepravce balíků", "poštovní služby",
              "výdejní místa", "podací místa", "express delivery", "courier",
              "same day doručení", "přeprava dokumentů"), 3.0),
        ],
        "neg": [
            (("mezinárodní kamionová doprava", "spedice", "kontraktní logistika"), 2.0),
        ],
    },
    "LOG-03": {  # Vozidla - prodej, servis a díly
        "pos": [
            (("autoservis", "autorizovaný servis vozidel", "prodej nových vozidel",
              "prodej ojetých vozidel", "autorizovaný dealer", "náhradní díly na automobily",
              "pneuservis", "autodíly", "karosářské práce", "odtahová služba", "prodejce vozů"), 3.0),
        ],
    },
    "LOG-04": {  # Správa vozového parku a mobilita
        "pos": [
            (("správa vozového parku", "fleet management", "operativní leasing vozidel",
              "operativní leasing", "full service leasing", "dlouhodobý pronájem vozidel",
              "krátkodobý pronájem vozidel", "car sharing", "sdílení vozidel",
              "firemní mobilita", "vozový park", "půjčovna automobilů", "autopůjčovna"), 3.0),
        ],
    },
}

# ---------------------------------------------------------------------------
# PROFESNI A PORADENSKE SLUZBY
# ---------------------------------------------------------------------------
_PRO = {
    "PRO-01": {  # Poradenství, audit a daně
        "pos": [
            (("daňový poradce", "daňové poradenství", "auditorská společnost", "audit účetní závěrky",
              "vedení účetnictví", "účetní kancelář", "zpracování mezd", "management consulting",
              "podnikové poradenství", "účetní a daňové služby", "účetní firma",
              "transakční poradenství", "dotační poradenství", "forenzní služby",
              "oceňování podniků"), 3.0),
            (("poradenská společnost", "poradenské služby", "auditorské a poradenské služby",
              "advisory"), 2.0),
        ],
        "neg": [
            (("technické poradenství", "znalecký posudek ve výstavbě", "technický dozor stavby"), 2.0),
        ],
    },
    "PRO-02": {  # Právní služby
        "pos": [
            (("advokátní kancelář", "advokát", "právní služby", "právní poradenství",
              "notářská kancelář", "notář", "patentový zástupce", "exekutorský úřad",
              "law firm", "zastupování před soudem"), 3.0),
        ],
    },
    "PRO-03": {  # Certifikace, inspekce a technické zkušebnictví
        "pos": [
            (("certifikační orgán", "certifikační společnost", "certifikace systémů managementu",
              "certifikace iso", "posuzování shody", "inspekční orgán", "inspekční společnost",
              "notifikovaná osoba", "autorizovaná osoba", "certification body",
              "vydávání certifikátů", "technická inspekce", "zkušebnictví a certifikace",
              "certifikace výrobků", "testování a certifikace"), 3.0),
        ],
        "neg": [
            (("daňový poradce", "vedení účetnictví", "advokátní"), 2.0),
        ],
    },
    "PRO-04": {  # Projekce, inženýrské služby a technické expertizy
        "pos": [
            (("projekční kancelář", "projektová dokumentace", "projekce staveb", "stavební projekt",
              "inženýrská činnost ve výstavbě", "autorizovaný inženýr", "projektování technologií",
              "tzb projekce", "engineering services", "generální projektant", "znalecký posudek",
              "technická expertiza", "technický dozor investora", "stavebně technický průzkum",
              "koordinátor bozp na stavbě"), 3.0),
        ],
    },
    "PRO-05": {  # Personální a agenturní služby
        "pos": [
            (("personální agentura", "agenturní zaměstnávání", "agentura práce",
              "nábor zaměstnanců", "recruitment", "vyhledávání zaměstnanců", "headhunting",
              "dočasné přidělení zaměstnanců", "pracovní agentura", "outsourcing personálu",
              "hr služby", "temporary staffing", "zprostředkování zaměstnání"), 3.0),
        ],
    },
    "PRO-06": {  # Finanční služby, leasing a pojištění
        "pos": [
            (("finanční leasing", "pojišťovna", "pojišťovací makléř", "faktoring",
              "spotřebitelský úvěr", "investiční společnost", "penzijní fond",
              "stavební spoření", "leasing a pojištění", "úvěrové produkty", "banka"), 3.0),
            (("leasing", "pojištění", "úvěr", "financování", "finanční poradenství"), 1.0),
        ],
        "neg": [
            (("operativní leasing vozidel", "operativní leasing", "fleet management",
              "správa vozového parku"), 3.0),
        ],
    },
    "PRO-07": {  # Výzkum a vývoj (smluvní)
        "pos": [
            (("výzkumná organizace", "výzkumný ústav", "výzkumný institut", "smluvní výzkum",
              "výzkumné centrum", "vědeckovýzkumné pracoviště", "akademie věd", "vysoká škola",
              "univerzita", "research institute", "aplikovaný výzkum na zakázku",
              "zakázkový výzkum a vývoj"), 3.0),
            (("výzkum a vývoj", "vývojové centrum", "research and development"), 1.0),
        ],
    },
}

# ---------------------------------------------------------------------------
# MARKETING, TISK, VZDELAVANI A FIREMNI SLUZBY
# ---------------------------------------------------------------------------
_FIR = {
    "FIR-01": {  # Reklama, marketing a PR
        "pos": [
            (("reklamní agentura", "marketingová agentura", "pr agentura", "marketingové služby",
              "online marketing", "výkonnostní marketing", "správa sociálních sítí",
              "reklamní kampaně", "brandová agentura", "digitální agentura", "seo a ppc",
              "komunikační agentura"), 3.0),
        ],
        "neg": [
            (("tiskárna", "polygrafická výroba"), 1.5),
        ],
    },
    "FIR-02": {  # Tisk, polygrafie a reklamní předměty
        "pos": [
            (("tiskárna", "polygrafie", "polygrafická výroba", "ofsetový tisk", "digitální tisk",
              "velkoformátový tisk", "potisk reklamních předmětů", "reklamní předměty",
              "výroba reklamy", "sítotisk", "tampónový tisk", "knihařství", "reklamní potisk"), 3.0),
        ],
    },
    "FIR-03": {  # Média, vydavatelství a předplatné
        "pos": [
            (("vydavatelství", "mediální dům", "inzerce v tisku", "předplatné periodik",
              "deník", "zpravodajský portál", "tisková agentura", "mediální zastupitelství",
              "časopis pro", "vydavatel novin a časopisů", "internetový zpravodajský server"), 3.0),
        ],
        "neg": [
            (("reklamní agentura", "marketingová agentura"), 1.5),
            (("odborná literatura", "odborné publikace", "právní informační systém",
              "daňová a účetní literatura"), 2.5),
        ],
    },
    "FIR-04": {  # Vzdělávání, školení a odborná literatura
        "pos": [
            (("vzdělávací agentura", "odborná školení", "firemní vzdělávání", "rekvalifikační kurzy",
              "akreditované kurzy", "profesní vzdělávání", "manažerské tréninky",
              "školení a semináře", "training company", "kurzy pro firmy", "odborná literatura",
              "odborné publikace", "odborné nakladatelství", "nakladatelství odborné literatury",
              "právnická a daňová literatura", "komentáře a příručky", "právní informační systém",
              "prodej technických norem"), 3.0),
        ],
        "neg": [
            (("jazyková škola", "výuka jazyků"), 1.5),
            (("certifikační orgán",), 1.5),
        ],
    },
    "FIR-05": {  # Překlady a jazykové služby
        "pos": [
            (("jazyková škola", "výuka jazyků", "jazykové kurzy", "překlady a tlumočení",
              "překladatelská agentura", "soudní překlady", "firemní jazykové kurzy",
              "translation services", "lokalizace textů", "tlumočnické služby"), 3.0),
        ],
    },
    "FIR-06": {  # Catering a firemní stravování
        "pos": [
            (("catering", "cateringové služby", "závodní stravování", "firemní stravování",
              "provoz jídelny", "stravovací provoz", "rauty a bankety", "výroba a rozvoz jídel",
              "gastro služby pro firmy", "provozování kantýn"), 3.0),
        ],
        "neg": [
            (("hotel", "penzion", "ubytování"), 1.5),
        ],
    },
    "FIR-07": {  # Ubytování, konference a firemní akce
        "pos": [
            (("hotel", "penzion", "ubytovací služby", "hotelové služby", "kongresové centrum",
              "konference", "kongres", "organizace konferencí", "event agentura", "firemní akce",
              "teambuilding", "pořádání akcí", "event management", "konferenční prostory"), 3.0),
        ],
    },
    "FIR-08": {  # Zaměstnanecké benefity a volnočasové služby
        "pos": [
            (("zaměstnanecké benefity", "cafeterie benefity", "stravenky", "benefitní poukázky",
              "poukázky pro zaměstnance", "multisport", "benefitní program", "employee benefits",
              "pracovnělékařské služby", "závodní lékař", "wellness a fitness", "sportoviště",
              "volnočasové aktivity", "rekreační středisko"), 3.0),
        ],
    },
    "FIR-09": {  # Veřejný sektor, instituce a nezisková sféra
        "pos": [
            (("městský úřad", "obecní úřad", "magistrát", "krajský úřad", "ministerstvo",
              "úřad práce", "státní správa", "orgán veřejné správy", "územní samospráva",
              "městská část", "hospodářská komora", "svaz průmyslu", "profesní asociace",
              "spolek", "obecně prospěšná společnost", "příspěvková organizace",
              "divadlo", "filharmonie", "muzeum", "galerie"), 3.0),
        ],
    },
}


def _slouc(*casti):
    out = {}
    for c in casti:
        out.update(c)
    return out


PRAVIDLA = _slouc(_ICT, _ELE, _MET, _STR, _MAT, _PROV, _FAC, _LOG, _PRO, _FIR)


def _normalizuj_blok(blok):
    out = []
    for fraze, vaha in blok:
        norm = tuple(sorted({normalizuj_frazi(f) for f in fraze if normalizuj_frazi(f)}))
        if norm:
            out.append((norm, float(vaha)))
    return out


def nacti_pravidla():
    hotovo = {}
    for kod, pravidlo in PRAVIDLA.items():
        hotovo[kod] = {
            "pos": _normalizuj_blok(pravidlo.get("pos", [])),
            "neg": _normalizuj_blok(pravidlo.get("neg", [])),
        }
    return hotovo


PRAVIDLA_NORM = nacti_pravidla()

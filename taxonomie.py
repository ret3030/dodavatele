# -*- coding: utf-8 -*-
"""
Vlastni taxonomie dodavatelu.

Dvouurovnova klasifikace:
    SKUPINA  (napr. "ICT a technologie")
      +- KATEGORIE s kodem (napr. "ICT-03  Cloud, hosting a datova centra")

Kategorie se urcuje primarne z kodu NACE ziskaneho z rejstriku, zalozne
z klicovych slov v nazvu firmy (pro dodavatele, u kterych NACE nezname -
typicky mimo CR).

Mapa NACE -> kategorie se prohledava od nejdelsiho prefixu, takze zaznam
pro "6201" ma prednost pred obecnym "62".
"""

# ---------------------------------------------------------------------------
# Ciselnik kategorii:  kod -> (skupina, nazev kategorie)
# ---------------------------------------------------------------------------

KATEGORIE = {
    # --- ICT a technologie -------------------------------------------------
    "ICT-01": ("ICT a technologie", "Vyvoj software a aplikaci na zakazku"),
    "ICT-02": ("ICT a technologie", "Software, licence a SaaS"),
    "ICT-03": ("ICT a technologie", "Cloud, hosting a datova centra"),
    "ICT-04": ("ICT a technologie", "Sprava IT a managed services"),
    "ICT-05": ("ICT a technologie", "IT poradenstvi a systemova integrace"),
    "ICT-06": ("ICT a technologie", "Kyberneticka bezpecnost"),
    "ICT-07": ("ICT a technologie", "Hardware a koncova zarizeni"),
    "ICT-08": ("ICT a technologie", "Sitova a komunikacni infrastruktura"),
    "ICT-09": ("ICT a technologie", "Telekomunikacni sluzby a konektivita"),
    "ICT-10": ("ICT a technologie", "Zpracovani dat, BPO a sdilene sluzby"),
    "ICT-11": ("ICT a technologie", "Servis a likvidace vypocetni techniky"),
    "ICT-12": ("ICT a technologie", "Internetove portaly a online sluzby"),

    # --- Profesni sluzby ---------------------------------------------------
    "PRO-01": ("Profesni sluzby", "Pravni sluzby"),
    "PRO-02": ("Profesni sluzby", "Ucetni a danove sluzby"),
    "PRO-03": ("Profesni sluzby", "Audit a assurance"),
    "PRO-04": ("Profesni sluzby", "Manazerske a procesni poradenstvi"),
    "PRO-05": ("Profesni sluzby", "Inzenyring, projekce a architektura"),
    "PRO-06": ("Profesni sluzby", "Certifikace, zkusebnictvi a inspekce"),
    "PRO-07": ("Profesni sluzby", "Vyzkum a vyvoj"),
    "PRO-08": ("Profesni sluzby", "Preklady, jazykove a redakcni sluzby"),
    "PRO-09": ("Profesni sluzby", "Ostatni profesni a technicke sluzby"),

    # --- Financni sluzby ---------------------------------------------------
    "FIN-01": ("Financni sluzby", "Bankovni sluzby"),
    "FIN-02": ("Financni sluzby", "Platebni a zuctovaci sluzby"),
    "FIN-03": ("Financni sluzby", "Pojisteni a zajisteni"),
    "FIN-04": ("Financni sluzby", "Leasing, uvery a financovani"),
    "FIN-05": ("Financni sluzby", "Ostatni financni a investicni sluzby"),
    "FIN-06": ("Financni sluzby", "Inkaso pohledavek a kreditni sluzby"),

    # --- Lidske zdroje -----------------------------------------------------
    "HR-01": ("Lidske zdroje", "Nabor a personalni agentury"),
    "HR-02": ("Lidske zdroje", "Agenturni zamestnavani a docasne prideleni"),
    "HR-03": ("Lidske zdroje", "Mzdove a personalni sluzby (payroll)"),
    "HR-04": ("Lidske zdroje", "Skoleni a vzdelavani"),
    "HR-05": ("Lidske zdroje", "Benefity a pece o zamestnance"),

    # --- Marketing a media -------------------------------------------------
    "MKT-01": ("Marketing a media", "Reklamni a mediani agentury"),
    "MKT-02": ("Marketing a media", "Pruzkum trhu a analytika"),
    "MKT-03": ("Marketing a media", "Tisk, polygrafie a reklamni produkce"),
    "MKT-04": ("Marketing a media", "Eventy, konference a veletrhy"),
    "MKT-05": ("Marketing a media", "Audiovizualni produkce a vysilani"),

    # --- Sprava objektu a provoz -------------------------------------------
    "FAC-01": ("Sprava objektu a provoz", "Uklidove sluzby"),
    "FAC-02": ("Sprava objektu a provoz", "Facility management"),
    "FAC-03": ("Sprava objektu a provoz", "Udrzba budov a technickych zarizeni"),
    "FAC-04": ("Sprava objektu a provoz", "Stravovani a catering"),
    "FAC-05": ("Sprava objektu a provoz", "Pronajem prostor a nemovitosti"),
    "FAC-06": ("Sprava objektu a provoz", "Kancelarske potreby a drobne vybaveni"),
    "FAC-07": ("Sprava objektu a provoz", "Nabytek a interiery"),
    "FAC-08": ("Sprava objektu a provoz", "Ubytovaci a cestovni sluzby"),

    # --- Bezpecnost --------------------------------------------------------
    "SEC-01": ("Bezpecnost", "Fyzicka ostraha a bezpecnostni sluzby"),
    "SEC-02": ("Bezpecnost", "Bezpecnostni technologie (EZS, CCTV, pristupove systemy)"),

    # --- Logistika a doprava -----------------------------------------------
    "LOG-01": ("Logistika a doprava", "Silnicni a zeleznicni doprava"),
    "LOG-02": ("Logistika a doprava", "Letecka a namorni preprava"),
    "LOG-03": ("Logistika a doprava", "Zasilatelstvi a spedice"),
    "LOG-04": ("Logistika a doprava", "Skladovani a logisticke sluzby"),
    "LOG-05": ("Logistika a doprava", "Kurynske a postovni sluzby"),

    # --- Energie a utility -------------------------------------------------
    "ENE-01": ("Energie a utility", "Dodavka elektriny a plynu"),
    "ENE-02": ("Energie a utility", "Teplo a energeticke sluzby"),
    "ENE-03": ("Energie a utility", "Paliva a pohonne hmoty"),
    "ENE-04": ("Energie a utility", "Vodne, stocne a vodohospodarske sluzby"),

    # --- Material a suroviny -----------------------------------------------
    "MAT-01": ("Material a suroviny", "Kovy a hutni material"),
    "MAT-02": ("Material a suroviny", "Chemicke latky a pripravky"),
    "MAT-03": ("Material a suroviny", "Plasty, pryz a kompozity"),
    "MAT-04": ("Material a suroviny", "Papir, obaly a obalove materialy"),
    "MAT-05": ("Material a suroviny", "Stavebni hmoty a nekovove materialy"),
    "MAT-06": ("Material a suroviny", "Textil, odevy a OOPP"),
    "MAT-07": ("Material a suroviny", "Elektronicke a elektrotechnicke komponenty"),
    "MAT-08": ("Material a suroviny", "Potraviny a napoje"),
    "MAT-09": ("Material a suroviny", "Zemedelske a lesni suroviny"),
    "MAT-10": ("Material a suroviny", "Nerostne suroviny a tezba"),
    "MAT-11": ("Material a suroviny", "Drevo a vyrobky ze dreva"),

    # --- Technologie a stroje ----------------------------------------------
    "TEC-01": ("Technologie a stroje", "Vyrobni stroje a zarizeni"),
    "TEC-02": ("Technologie a stroje", "Merici, ridici a regulacni technika (OT)"),
    "TEC-03": ("Technologie a stroje", "Servis, opravy a instalace stroju"),
    "TEC-04": ("Technologie a stroje", "Elektricka zarizeni a pohony"),
    "TEC-05": ("Technologie a stroje", "Dopravni prostredky a jejich dily"),
    "TEC-06": ("Technologie a stroje", "Pronajem techniky a vozidel"),
    "TEC-07": ("Technologie a stroje", "Kovove konstrukce a dily"),

    # --- Stavebnictvi ------------------------------------------------------
    "STA-01": ("Stavebnictvi", "Pozemni stavby a investicni vystavba"),
    "STA-02": ("Stavebnictvi", "Inzenyrske stavitelstvi"),
    "STA-03": ("Stavebnictvi", "Specializovane stavebni prace"),
    "STA-04": ("Stavebnictvi", "Elektroinstalace a slaboproud"),

    # --- Obchod ------------------------------------------------------------
    "OBC-01": ("Obchod", "Velkoobchod a distribuce"),
    "OBC-02": ("Obchod", "Maloobchod a drobny nakup"),
    "OBC-03": ("Obchod", "Prodej a servis motorovych vozidel"),

    # --- Zdravotnictvi -----------------------------------------------------
    "ZDR-01": ("Zdravotnictvi", "Zdravotni pece a pracovnelekarske sluzby"),
    "ZDR-02": ("Zdravotnictvi", "Laboratore a diagnostika"),
    "ZDR-03": ("Zdravotnictvi", "Farmacie a zdravotnicky material"),
    "ZDR-04": ("Zdravotnictvi", "Socialni sluzby"),
    "ZDR-05": ("Zdravotnictvi", "Veterinarni sluzby"),

    # --- Odpady a zivotni prostredi ----------------------------------------
    "ODP-01": ("Odpady a zivotni prostredi", "Odpadove hospodarstvi"),
    "ODP-02": ("Odpady a zivotni prostredi", "Skartace a likvidace nosicu dat"),
    "ODP-03": ("Odpady a zivotni prostredi", "Sanace a environmentalni sluzby"),

    # --- Verejny a neziskovy sektor ----------------------------------------
    "VER-01": ("Verejny a neziskovy sektor", "Verejna sprava a statni instituce"),
    "VER-02": ("Verejny a neziskovy sektor", "Asociace, spolky a neziskove organizace"),
    "VER-03": ("Verejny a neziskovy sektor", "Vzdelavaci instituce"),

    # --- Ostatni -----------------------------------------------------------
    "OST-01": ("Ostatni", "Kultura, sport a volny cas"),
    "OST-02": ("Ostatni", "Ostatni osobni a podpurne sluzby"),
    "XXX-00": ("Nezarazeno", "Nezarazeno - nutne rucni doplneni"),
}

VYCHOZI_KOD = "XXX-00"


# ---------------------------------------------------------------------------
# Mapa NACE -> kod kategorie (prefix; delsi prefix vyhrava)
# ---------------------------------------------------------------------------

NACE_MAPA = {
    # Zemedelstvi, lesnictvi, tezba
    "01": "MAT-09", "02": "MAT-11", "03": "MAT-09",
    "05": "MAT-10", "06": "ENE-03", "07": "MAT-10", "08": "MAT-05", "09": "MAT-10",

    # Zpracovatelsky prumysl
    "10": "MAT-08", "11": "MAT-08", "12": "MAT-08",
    "13": "MAT-06", "14": "MAT-06", "15": "MAT-06",
    "16": "MAT-11", "17": "MAT-04", "18": "MKT-03", "19": "ENE-03",
    "20": "MAT-02", "21": "ZDR-03", "22": "MAT-03", "23": "MAT-05",
    "24": "MAT-01", "25": "TEC-07", "2562": "TEC-03",
    "26": "MAT-07", "2611": "MAT-07", "2620": "ICT-07", "2630": "ICT-08",
    "2651": "TEC-02", "2660": "ZDR-03", "2670": "TEC-02",
    "27": "TEC-04", "28": "TEC-01", "29": "TEC-05", "30": "TEC-05",
    "31": "FAC-07", "32": "OST-02", "3250": "ZDR-03",
    "33": "TEC-03", "3312": "TEC-03", "3313": "TEC-02", "3314": "TEC-04", "3320": "TEC-03",

    # Energie, voda, odpady
    "35": "ENE-01", "3512": "ENE-01", "3513": "ENE-01", "3514": "ENE-01",
    "3521": "ENE-01", "3522": "ENE-01", "3523": "ENE-01", "3530": "ENE-02",
    "36": "ENE-04", "37": "ENE-04",
    "38": "ODP-01", "3831": "ODP-02", "39": "ODP-03",

    # Stavebnictvi
    "41": "STA-01", "42": "STA-02", "43": "STA-03", "4321": "STA-04", "4322": "FAC-03",

    # Obchod
    "45": "OBC-03", "46": "OBC-01",
    "4651": "ICT-07", "4652": "ICT-08", "4666": "FAC-06", "4671": "ENE-03",
    "4646": "ZDR-03", "4649": "OBC-01", "4665": "FAC-07",
    "47": "OBC-02", "4741": "ICT-07", "4773": "ZDR-03",

    # Doprava a skladovani
    "49": "LOG-01", "50": "LOG-02", "51": "LOG-02",
    "52": "LOG-04", "5229": "LOG-03", "53": "LOG-05",

    # Ubytovani a stravovani
    "55": "FAC-08", "56": "FAC-04",

    # Informacni a komunikacni cinnosti
    "58": "ICT-02", "5811": "MKT-03", "5813": "MKT-05", "5814": "MKT-05", "5829": "ICT-02",
    "59": "MKT-05", "60": "MKT-05", "61": "ICT-09",
    "62": "ICT-05", "6201": "ICT-01", "6202": "ICT-05", "6203": "ICT-04", "6209": "ICT-04",
    "63": "ICT-03", "6311": "ICT-03", "6312": "ICT-12", "639": "MKT-02",

    # Finance a pojisteni
    "64": "FIN-05", "6419": "FIN-01", "6491": "FIN-04", "6492": "FIN-04",
    "65": "FIN-03", "66": "FIN-05", "6611": "FIN-02", "6619": "FIN-02", "6622": "FIN-03",

    # Nemovitosti
    "68": "FAC-05",

    # Profesni, vedecke a technicke cinnosti
    "69": "PRO-01", "6910": "PRO-01", "6920": "PRO-02",
    "70": "PRO-04", "7021": "MKT-01", "7022": "PRO-04",
    "71": "PRO-05", "7111": "PRO-05", "7112": "PRO-05", "7120": "PRO-06",
    "72": "PRO-07", "73": "MKT-01", "7311": "MKT-01", "7312": "MKT-01", "732": "MKT-02",
    "74": "PRO-09", "7410": "MKT-01", "7420": "MKT-05", "7430": "PRO-08", "7490": "PRO-09",
    "75": "ZDR-05",

    # Administrativni a podpurne cinnosti
    "77": "TEC-06", "7733": "ICT-07", "7735": "LOG-02",
    "78": "HR-01", "7810": "HR-01", "7820": "HR-02", "7830": "HR-02",
    "79": "FAC-08",
    "80": "SEC-01", "8020": "SEC-02",
    "81": "FAC-02", "8121": "FAC-01", "8122": "FAC-01", "8129": "FAC-01", "8130": "FAC-02",
    "82": "ICT-10", "8211": "ICT-10", "8219": "MKT-03", "8220": "ICT-10",
    "8230": "MKT-04", "8291": "FIN-06", "8292": "MAT-04", "8299": "ICT-10",

    # Verejna sprava, vzdelavani, zdravotnictvi
    "84": "VER-01", "85": "HR-04", "8510": "VER-03", "8520": "VER-03",
    "853": "VER-03", "854": "VER-03", "8559": "HR-04",
    "86": "ZDR-01", "8690": "ZDR-02", "87": "ZDR-04", "88": "ZDR-04",

    # Ostatni
    "90": "OST-01", "91": "OST-01", "92": "OST-01", "93": "OST-01",
    "94": "VER-02", "95": "ICT-11", "9511": "ICT-11", "9512": "ICT-11", "952": "OST-02",
    "96": "OST-02", "97": "OST-02", "99": "VER-02",
}


# ---------------------------------------------------------------------------
# Zalozni zarazeni podle klicovych slov v nazvu firmy.
# Pouzije se, kdyz NACE nezname (dodavatele mimo CR).
# Poradi rozhoduje - prvni shoda vyhrava, proto jdou specificka slova driv.
# ---------------------------------------------------------------------------

KLICOVA_SLOVA = [
    (("cloud comput", "cloud", "hosting", "datacent", "data cent", "colocation", "saas",
      "webhost"), "ICT-03"),
    (("consumer electronics", "computer hardware", "spotrebni elektronika"), "ICT-07"),
    (("computer software", "software industry", "software"), "ICT-01"),
    (("petroleum", "oil and gas", "ropn", "rafin", "refinery"), "ENE-03"),
    (("electric power", "electricity", "utility", "utilities", "elektrarens"), "ENE-01"),
    (("cyber", "kyber", "security software", "infosec", "pentest"), "ICT-06"),
    (("telecom", "telekom", "telco", "mobile", "vodafone", "t-mobile", "connectivity"), "ICT-09"),
    (("software", "systems", "solutions", "it services", "informatik", "informacni systemy",
      "devops", "sap ", "erp", "digital", "technologies", "technologie", "app "), "ICT-01"),
    (("computer", "pocitac", "hardware", "notebook", "print solutions"), "ICT-07"),
    (("network", "networks", "sitove"), "ICT-08"),
    (("outsourcing", "shared service", "bpo", "call center", "kontaktni centrum"), "ICT-10"),
    (("bank", "banka", "banking"), "FIN-01"),
    (("payment", "platebni", "acquiring", "card services"), "FIN-02"),
    (("insurance", "pojist", "versicherung", "assurance"), "FIN-03"),
    (("leasing", "credit", "uverov", "factoring"), "FIN-04"),
    (("audit", "assurance"), "PRO-03"),
    (("ucetni", "accounting", "tax ", "danov", "steuerber", "payroll", "mzdov"), "PRO-02"),
    (("advokat", "legal", "law firm", "rechtsanw", "notar", "kanzlei", "pravni"), "PRO-01"),
    (("consult", "poraden", "advisory", "beratung", "management consult"), "PRO-04"),
    (("recruit", "staffing", "personal", "human resources", "agentura prace", "zeitarbeit",
      "job", "kariera"), "HR-01"),
    (("training", "skoleni", "vzdelav", "education", "academy", "akadem", "learning"), "HR-04"),
    (("energy", "energie", "energet", "power", "elektrarna", "teplarna"), "ENE-01"),
    (("gas", "plyn", "oil", "petrol", "fuel", "paliva", "benzina"), "ENE-03"),
    (("vodarn", "waterworks", "wasser"), "ENE-04"),
    (("security", "ostrah", "sicherheit", "guard", "protection service"), "SEC-01"),
    (("facility", "cleaning", "uklid", "reinigung", "sprava budov", "sprava nemovit"), "FAC-02"),
    (("catering", "restaur", "stravov", "kantyn", "gastro"), "FAC-04"),
    (("hotel", "travel", "cestovn", "reise", "tour"), "FAC-08"),
    (("shred", "skartac", "likvidace dat", "data destruction"), "ODP-02"),
    (("recycl", "recykl", "waste", "odpad", "entsorgung", "ekolog"), "ODP-01"),
    (("logistic", "logistik", "spedice", "spedition", "forwarding", "freight", "shipping",
      "transport", "doprava", "cargo"), "LOG-03"),
    (("kurier", "courier", "express", "post", "posta", "parcel", "zasilkovna"), "LOG-05"),
    (("warehouse", "sklad", "fulfillment"), "LOG-04"),
    (("pharma", "farmac", "medical", "medizin", "zdravot", "health"), "ZDR-03"),
    (("laborat", "labor ", "diagnost"), "ZDR-02"),
    (("automation", "automatizace", "control system", "ridici system", "scada", "plc",
      "measurement", "mereni"), "TEC-02"),
    (("engineering", "inzenyr", "projekce", "projekt", "design office", "architek"), "PRO-05"),
    (("certifik", "inspection", "tuv", "dekra", "bureau veritas", "zkusebn", "testing"), "PRO-06"),
    (("research", "vyzkum", "forschung", "institut", "innovation"), "PRO-07"),
    (("machin", "stroj", "maschin", "equipment", "zarizeni", "werkzeug"), "TEC-01"),
    (("service", "servis", "opravy", "wartung", "maintenance"), "TEC-03"),
    (("electric", "elektro", "elektrotech"), "TEC-04"),
    (("automotive", "motors", "vehicle", "vozidl", "auto "), "TEC-05"),
    (("rental", "pronajem", "rent ", "miet", "verleih"), "TEC-06"),
    (("steel", "ocel", "metal", "kovo", "hut", "aluminium", "hlinik", "slevarn", "foundry"), "MAT-01"),
    (("chemic", "chemie", "chemical", "chemi"), "MAT-02"),
    (("plast", "polymer", "rubber", "kaucuk", "pryz"), "MAT-03"),
    (("packaging", "obal", "verpackung", "papir", "paper", "karton"), "MAT-04"),
    (("beton", "cement", "stavebni hmoty", "kamenolom"), "MAT-05"),
    (("textil", "odev", "clothing", "workwear", "ochranne pomucky"), "MAT-06"),
    (("electronic", "elektronik", "semiconduct", "components", "komponenty"), "MAT-07"),
    (("food", "potravin", "napoj", "beverage", "lebensmittel", "pivovar", "mlekarna"), "MAT-08"),
    (("agro", "zemedel", "farm", "landwirt"), "MAT-09"),
    (("bau", "stavb", "stavebni", "construction", "building", "sanace"), "STA-01"),
    (("marketing", "reklam", "advertis", "werbung", "media", "agency", "agentura", "kreativ"), "MKT-01"),
    (("research market", "pruzkum trhu", "survey"), "MKT-02"),
    (("print", "tisk", "druck", "polygraf", "tiskarna"), "MKT-03"),
    (("event", "kongres", "veletrh", "conference", "expo"), "MKT-04"),
    (("real estate", "reality", "immobil", "nemovit", "properties", "estate"), "FAC-05"),
    (("nabytek", "furniture", "mobel", "interier"), "FAC-07"),
    (("papirnictvi", "office supplies", "kancelarsk"), "FAC-06"),
    (("wholesale", "velkoobchod", "distribut", "trading", "trade", "supply", "handel"), "OBC-01"),
    (("retail", "maloobchod", "shop", "store", "market"), "OBC-02"),
    (("univerzit", "university", "vysoka skola", "college", "gymnaz", "skola"), "VER-03"),
    (("mesto ", "obec ", "kraj ", "ministerstvo", "urad", "statni"), "VER-01"),
    (("spolek", "asociace", "association", "verband", "nadace", "obecne prospesn"), "VER-02"),
]


# ---------------------------------------------------------------------------
# Nazvy NACE divizi (2 mistne) - pro citelnost vystupu
# ---------------------------------------------------------------------------

NACE_DIVIZE = {
    "01": "Rostlinna a zivocisna vyroba, myslivost", "02": "Lesnictvi a tezba dreva",
    "03": "Rybolov a akvakultura", "05": "Tezba a uprava cerneho a hnedeho uhli",
    "06": "Tezba ropy a zemniho plynu", "07": "Tezba a uprava rud",
    "08": "Ostatni tezba a dobyvani", "09": "Podpurne cinnosti pri tezbe",
    "10": "Vyroba potravinarskych vyrobku", "11": "Vyroba napoju",
    "12": "Vyroba tabakovych vyrobku", "13": "Vyroba textilii", "14": "Vyroba odevu",
    "15": "Vyroba usni a souvisejicich vyrobku", "16": "Zpracovani dreva",
    "17": "Vyroba papiru a vyrobku z papiru", "18": "Tisk a rozmnozovani nahranych nosicu",
    "19": "Vyroba koksu a rafinovanych ropnych produktu", "20": "Vyroba chemickych latek a pripravku",
    "21": "Vyroba zakladnich farmaceutickych vyrobku", "22": "Vyroba pryzovych a plastovych vyrobku",
    "23": "Vyroba ostatnich nekovovych mineralnich vyrobku", "24": "Vyroba a hutni zpracovani kovu",
    "25": "Vyroba kovovych konstrukci a kovodelnych vyrobku",
    "26": "Vyroba pocitacu, elektronickych a optickych pristroju",
    "27": "Vyroba elektrickych zarizeni", "28": "Vyroba stroju a zarizeni j. n.",
    "29": "Vyroba motorovych vozidel a jejich dilu", "30": "Vyroba ostatnich dopravnich prostredku",
    "31": "Vyroba nabytku", "32": "Ostatni zpracovatelsky prumysl",
    "33": "Opravy a instalace stroju a zarizeni", "35": "Vyroba a rozvod elektriny, plynu a tepla",
    "36": "Shromazdovani, uprava a rozvod vody", "37": "Cinnosti souvisejici s odpadnimi vodami",
    "38": "Shromazdovani, sber a odstranovani odpadu", "39": "Sanace a jine cinnosti s odpady",
    "41": "Vystavba budov", "42": "Inzenyrske stavitelstvi", "43": "Specializovane stavebni cinnosti",
    "45": "Velkoobchod, maloobchod a opravy motorovych vozidel",
    "46": "Velkoobchod, krome motorovych vozidel", "47": "Maloobchod, krome motorovych vozidel",
    "49": "Pozemni a potrubni doprava", "50": "Vodni doprava", "51": "Letecka doprava",
    "52": "Skladovani a vedlejsi cinnosti v doprave", "53": "Postovni a kurynske cinnosti",
    "55": "Ubytovani", "56": "Stravovani a pohostinstvi", "58": "Vydavatelske cinnosti",
    "59": "Cinnosti v oblasti filmu, videa a hudby", "60": "Tvorba programu a vysilani",
    "61": "Telekomunikacni cinnosti", "62": "Cinnosti v oblasti informacnich technologii",
    "63": "Informacni cinnosti (hosting, zpracovani dat, portaly)",
    "64": "Financni zprostredkovani, krome pojistovnictvi",
    "65": "Pojisteni, zajisteni a penzijni fondy", "66": "Ostatni financni cinnosti",
    "68": "Cinnosti v oblasti nemovitosti", "69": "Pravni a ucetnicke cinnosti",
    "70": "Cinnosti vedeni podniku, poradenstvi v oblasti rizeni",
    "71": "Architektonicke a inzenyrske cinnosti, technicke zkousky",
    "72": "Vyzkum a vyvoj", "73": "Reklama a pruzkum trhu",
    "74": "Ostatni profesni, vedecke a technicke cinnosti", "75": "Veterinarni cinnosti",
    "77": "Pronajem a operativni leasing", "78": "Cinnosti souvisejici se zamestnanim",
    "79": "Cinnosti cestovnich agentur a kancelari", "80": "Bezpecnostni a patraci cinnosti",
    "81": "Cinnosti souvisejici se stavbami a upravou krajiny",
    "82": "Administrativni a podpurne cinnosti pro podnikani",
    "84": "Verejna sprava a obrana", "85": "Vzdelavani", "86": "Zdravotni pece",
    "87": "Pobytove sluzby socialni pece", "88": "Ambulantni a terenni socialni sluzby",
    "90": "Tvurci, umelecke a zabavni cinnosti", "91": "Cinnosti knihoven, archivu a muzei",
    "92": "Cinnosti heren, kasin a sazkovych kancelari", "93": "Sportovni a rekreacni cinnosti",
    "94": "Cinnosti organizaci sdruzujicich osoby se spolecnymi zajmy",
    "95": "Opravy pocitacu a vyrobku pro osobni potrebu",
    "96": "Poskytovani ostatnich osobnich sluzeb", "97": "Cinnosti domacnosti jako zamestnavatelu",
    "99": "Cinnosti exteritorialnich organizaci",
}

# Hrube mapovani US SIC -> NACE (pro data ze SEC EDGAR)
SIC_NA_NACE = {
    "01": "01", "02": "01", "07": "01", "08": "02", "09": "03", "10": "07", "12": "05",
    "13": "06", "14": "08", "15": "41", "16": "42", "17": "43", "20": "10", "21": "12",
    "22": "13", "23": "14", "24": "16", "25": "31", "26": "17", "27": "18", "28": "20",
    "283": "21", "29": "19", "30": "22", "31": "15", "32": "23", "33": "24", "34": "25",
    "35": "28", "357": "2620", "36": "27", "366": "2630", "367": "26", "37": "29",
    "372": "30", "38": "26", "382": "2651", "384": "3250", "39": "32",
    "40": "49", "41": "49", "42": "49", "44": "50", "45": "51", "46": "49", "47": "5229",
    "48": "61", "484": "60", "489": "61", "49": "35", "50": "46", "51": "46", "52": "47",
    "53": "47", "54": "47", "55": "45", "56": "47", "57": "47", "58": "56", "59": "47",
    "60": "6419", "61": "6492", "62": "66", "63": "65", "64": "6622", "65": "68", "67": "64",
    "70": "55", "72": "96", "73": "6202", "7370": "6201", "7371": "6201", "7372": "5829",
    "7374": "6311", "7375": "6312", "7379": "6209", "78": "59", "79": "93", "80": "86",
    "81": "6910", "82": "85", "83": "88", "86": "94", "87": "71", "8711": "7112",
    "8721": "6920", "8731": "72", "89": "74", "91": "84", "92": "84", "93": "84",
    "94": "84", "95": "84", "96": "84", "97": "84", "99": "8299",
}


# ---------------------------------------------------------------------------
# Funkce
# ---------------------------------------------------------------------------

def _prefix(kod, mapa):
    """Vrati hodnotu pro nejdelsi prefix kodu, ktery je v mape."""
    if not kod:
        return None
    kod = "".join(ch for ch in str(kod) if ch.isdigit())
    for delka in range(len(kod), 0, -1):
        hodnota = mapa.get(kod[:delka])
        if hodnota is not None:
            return hodnota
    return None


def sic_na_nace(sic):
    """Prevede US SIC kod na priblizny NACE."""
    return _prefix(sic, SIC_NA_NACE)


def nazev_nace(kod):
    """Cesky nazev NACE divize podle prvnich dvou cislic."""
    if not kod:
        return ""
    cislice = "".join(ch for ch in str(kod) if ch.isdigit())
    return NACE_DIVIZE.get(cislice[:2], "")


def zarad(nace=None, nazev=None, mapa=None, klicova_slova=None, kategorie=None):
    """
    Zaradi dodavatele do vlastni taxonomie.

    Vrati dict:
        kod       - kod kategorie, napr. "ICT-03"
        kategorie - nazev kategorie
        skupina   - nadrazena skupina
        zdroj     - 'nace' | 'nazev' | 'vychozi'
    """
    mapa = mapa if mapa is not None else NACE_MAPA
    klicova_slova = klicova_slova if klicova_slova is not None else KLICOVA_SLOVA
    kategorie = kategorie if kategorie is not None else KATEGORIE

    kod, zdroj = None, "vychozi"
    if nace:
        kod = _prefix(nace, mapa)
        if kod:
            zdroj = "nace"
    if not kod and nazev:
        n = " " + nazev.lower() + " "
        for slova, k in klicova_slova:
            if any(s in n for s in slova):
                kod, zdroj = k, "nazev"
                break
    if not kod:
        kod = VYCHOZI_KOD

    skupina, nazev_kat = kategorie.get(kod, kategorie[VYCHOZI_KOD])
    return {"kod": kod, "kategorie": nazev_kat, "skupina": skupina, "zdroj": zdroj}


def prehled_kategorii():
    """Serazeny seznam (kod, skupina, nazev) - pro ciselnik ve vystupu."""
    return sorted(((k, v[0], v[1]) for k, v in KATEGORIE.items()))


def jako_json():
    return {
        "kategorie": {k: list(v) for k, v in KATEGORIE.items()},
        "nace_mapa": NACE_MAPA,
        "klicova_slova": [[list(s), k] for s, k in KLICOVA_SLOVA],
        "vychozi_kod": VYCHOZI_KOD,
        "sic_na_nace": SIC_NA_NACE,
    }


def z_json(data):
    """Vrati (mapa, klicova_slova, kategorie) z JSON podoby taxonomie."""
    kat = {k: tuple(v) for k, v in data.get("kategorie", {}).items()} or KATEGORIE
    mapa = data.get("nace_mapa") or NACE_MAPA
    klic = [(tuple(s), k) for s, k in data.get("klicova_slova", [])] or KLICOVA_SLOVA
    return mapa, klic, kat

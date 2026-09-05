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
# Obory z Wikidat (P452) -> kod kategorie a odhad NACE
#
# Wikidata u firem uvadi obor cinnosti jako odkaz na polozku (QID). Je to
# stabilnejsi signal nez hadani z nazvu: QID je jazykove nezavisly, takze
# funguje pro korejskou i turecku firmu stejne. Vlastni NACE ma na Wikidatech
# jen zlomek techto polozek (P4496), proto si prirazeni vedeme sami.
#
# Format:  QID -> (kod kategorie, odhad NACE nebo "")
# ---------------------------------------------------------------------------

WIKIDATA_OBORY = {
    # --- ICT -----------------------------------------------------------------
    "Q880371": ("ICT-02", "5829"),      # software industry
    "Q638608": ("ICT-01", "6201"),      # software development
    "Q11660": ("ICT-01", "6201"),       # artificial intelligence
    "Q941594": ("ICT-02", "5821"),      # video game industry
    "Q11661": ("ICT-05", "6202"),       # information technology
    "Q110702998": ("ICT-05", "6202"),   # information technology industry
    "Q1481411": ("ICT-04", "6203"),     # IT service management
    "Q3510521": ("ICT-06", "6203"),     # computer security
    "Q73768396": ("ICT-07", "2620"),    # consumer electronics industry
    "Q112165387": ("ICT-07", "2640"),   # manufacture of consumer electronics
    "Q56604188": ("ICT-07", "2751"),    # home appliance industry
    "Q56598901": ("ICT-07", "2630"),    # mobile phone industry
    "Q112165709": ("ICT-07", "4651"),   # wholesale of computers
    "Q2401742": ("ICT-09", "61"),       # telecommunications industry
    "Q418": ("ICT-09", "61"),           # telecommunications
    "Q269415": ("ICT-12", "6312"),      # digital distribution
    "Q3390477": ("ICT-12", "6312"),     # online marketplace

    # --- Profesni sluzby -----------------------------------------------------
    "Q23699878": ("PRO-04", "7022"),    # management consulting industry
    "Q112166038": ("PRO-04", "7010"),   # activities of head offices
    "Q23700345": ("PRO-09", "74"),      # professional services industry
    "Q12271": ("PRO-05", "7111"),       # architecture
    "Q42240": ("PRO-07", "72"),         # research
    "Q7108": ("PRO-07", "7211"),        # biotechnology

    # --- Finance -------------------------------------------------------------
    "Q22687": ("FIN-01", "6419"),       # bank
    "Q806718": ("FIN-01", "6419"),      # economics of banking
    "Q837171": ("FIN-05", "64"),        # financial services
    "Q57774188": ("FIN-05", "64"),      # financial sector
    "Q29584334": ("FIN-05", "64"),      # financial service activities except insurance
    "Q16319025": ("FIN-02", "6619"),    # fintech
    "Q43183": ("FIN-03", "65"),         # insurance
    "Q2518196": ("FIN-03", "65"),       # insurance industry
    "Q1787082": ("FIN-04", "6492"),     # line of credit

    # --- Lidske zdroje, vzdelavani -------------------------------------------
    "Q8434": ("VER-03", "85"),          # education
    "Q136822": ("VER-03", "8542"),      # higher education
    "Q112166127": ("VER-03", "8520"),   # primary education

    # --- Marketing a media ---------------------------------------------------
    "Q39809": ("MKT-01", "7311"),       # marketing
    "Q969040": ("MKT-01", "73"),        # creative industries
    "Q11034": ("MKT-03", "1812"),       # printing
    "Q112165253": ("MKT-03", "1813"),   # pre-press activities
    "Q3972943": ("MKT-03", "5811"),     # publishing
    "Q1415395": ("MKT-05", "5911"),     # film industry
    "Q932586": ("MKT-05", "5911"),      # film production
    "Q746359": ("MKT-05", "5920"),      # music industry
    "Q16023726": ("MKT-05", "5920"),    # music publishing
    "Q11033": ("MKT-05", "60"),         # mass media
    "Q56611639": ("MKT-05", "60"),      # media industry
    "Q11030": ("MKT-05", "6391"),       # journalism

    # --- Sprava objektu a provoz ---------------------------------------------
    "Q1660132": ("FAC-05", "68"),       # real estate industry
    "Q112166025": ("FAC-05", "6820"),   # accommodation rental
    "Q11707": ("FAC-04", "5610"),       # restaurant
    "Q1495452": ("FAC-08", "55"),       # hospitality industry
    "Q49389": ("FAC-08", "79"),         # tourism
    "Q112165478": ("FAC-07", "3109"),   # manufacture of other furniture
    "Q112165469": ("FAC-07", "3101"),   # office and shop furniture

    # --- Logistika -----------------------------------------------------------
    "Q7590": ("LOG-01", "49"),          # transport
    "Q3565868": ("LOG-01", "4920"),     # rail transport
    "Q178512": ("LOG-01", "4931"),      # public transport
    "Q155930": ("LOG-02", "50"),        # water transport
    "Q177777": ("LOG-04", "5210"),      # logistics

    # --- Energie -------------------------------------------------------------
    "Q862571": ("ENE-03", "19"),        # petroleum industry
    "Q1778629": ("MAT-10", "05"),       # coal industry
    "Q383973": ("ENE-01", "3511"),      # electricity generation
    "Q1304795": ("ENE-01", "35"),       # energy sector
    "Q2151621": ("ENE-01", "35"),       # energy industry
    "Q1341477": ("ENE-01", "35"),       # energy supply
    "Q1786253": ("ENE-02", "3530"),     # power plant technology

    # --- Material a suroviny -------------------------------------------------
    "Q44497": ("MAT-10", "07"),         # mining
    "Q2285982": ("MAT-01", "241"),      # iron and steel industry
    "Q1924906": ("MAT-01", "24"),       # metal industry
    "Q112165364": ("MAT-01", "2561"),   # metal treatment and coating
    "Q207652": ("MAT-02", "20"),        # chemical industry
    "Q12752882": ("MAT-02", "2042"),    # cosmetics industry
    "Q112165275": ("MAT-02", "2042"),   # perfumes and toiletries
    "Q607081": ("MAT-06", "13"),        # textile industry
    "Q11828862": ("MAT-06", "14"),      # clothing industry
    "Q107601662": ("MAT-06", "13"),     # textile and clothing industry
    "Q12684": ("MAT-06", "14"),         # fashion
    "Q112165215": ("MAT-06", "1413"),   # manufacture of outerwear
    "Q112165225": ("MAT-06", "1512"),   # leather goods
    "Q2986369": ("MAT-07", "2611"),     # semiconductor industry
    "Q5358497": ("MAT-07", "26"),       # electronics industry
    "Q11650": ("MAT-07", "26"),         # electronics
    "Q112165382": ("MAT-07", "2611"),   # manufacture of electronic components
    "Q112165711": ("MAT-07", "4652"),   # wholesale of electronic equipment
    "Q540912": ("MAT-08", "10"),        # food industry
    "Q107601756": ("MAT-08", "10"),     # food and tobacco industry
    "Q4899370": ("MAT-08", "11"),       # beverage industry
    "Q11644505": ("MAT-08", "1105"),    # brewing industry
    "Q112165131": ("MAT-08", "1011"),   # meat processing
    "Q112165152": ("MAT-08", "1051"),   # cheesemaking
    "Q112165155": ("MAT-08", "1052"),   # ice creams and sorbets
    "Q112165171": ("MAT-08", "1082"),   # cocoa, chocolate, confectionery
    "Q112165691": ("MAT-08", "4638"),   # food distributor
    "Q112165678": ("MAT-08", "4633"),   # wholesale dairy products
    "Q1187656": ("MAT-08", "10"),       # fast-moving consumer goods
    "Q11451": ("MAT-09", "01"),         # agriculture
    "Q1283714": ("MAT-09", "0111"),     # crop production

    # --- Technologie a stroje ------------------------------------------------
    "Q101333": ("TEC-01", "28"),        # mechanical engineering
    "Q187939": ("TEC-01", "28"),        # industrial manufacturing
    "Q170978": ("TEC-01", "2899"),      # robotics
    "Q112165723": ("TEC-01", "28"),     # industrial parts manufacturer
    "Q112165421": ("TEC-01", "2822"),   # lifting and handling equipment
    "Q112165425": ("TEC-01", "2825"),   # industrial refrigeration equipment
    "Q392933": ("TEC-01", "2540"),      # weapons industry
    "Q112165390": ("TEC-02", "2651"),   # scientific and technical instruments
    "Q112165518": ("TEC-03", "3320"),   # installation of mechanical machines
    "Q112165507": ("TEC-03", "3314"),   # electrical equipment repair
    "Q112165510": ("TEC-03", "3316"),   # repair and maintenance of aircraft
    "Q43035": ("TEC-04", "27"),         # electrical engineering
    "Q1326885": ("TEC-04", "27"),       # electrical industry
    "Q99529212": ("TEC-04", "2720"),    # battery industry
    "Q17177506": ("TEC-04", "2740"),    # lighting technique
    "Q112165400": ("TEC-04", "2712"),   # electrical distribution equipment
    "Q190117": ("TEC-05", "29"),        # automotive industry
    "Q786820": ("TEC-05", "2910"),      # automobile manufacturer
    "Q108428104": ("TEC-05", "2910"),   # car manufacturing
    "Q3477381": ("TEC-05", "2932"),     # automotive supplier
    "Q609131": ("TEC-05", "2910"),      # powertrain technology
    "Q3477363": ("TEC-05", "3030"),     # aerospace industry
    "Q112165459": ("TEC-05", "3030"),   # aircraft and space construction
    "Q474200": ("TEC-05", "3011"),      # shipbuilding
    "Q112165456": ("TEC-05", "3012"),   # construction of pleasure boats
    "Q112165363": ("TEC-07", "2550"),   # cutting, stamping
    "Q112165373": ("TEC-07", "2573"),   # manufacture of other tools

    # --- Stavebnictvi --------------------------------------------------------
    "Q385378": ("STA-01", "41"),        # construction
    "Q13405640": ("STA-01", "41"),      # construction industry
    "Q112165582": ("STA-03", "4312"),   # site preparation industry

    # --- Obchod --------------------------------------------------------------
    "Q220695": ("OBC-01", "46"),        # wholesale
    "Q112165707": ("OBC-01", "4690"),   # wholesale B2B, other
    "Q112165713": ("OBC-01", "4690"),   # wholesale B2B
    "Q112165696": ("OBC-01", "4690"),   # wholesale B2B
    "Q112165659": ("OBC-01", "4619"),   # intermediaries in trade
    "Q112165656": ("OBC-01", "4618"),   # specialized trade agents
    "Q112165649": ("OBC-01", "4616"),   # intermediaries, textiles
    "Q126793": ("OBC-02", "47"),        # retail
    "Q484847": ("OBC-02", "4791"),      # e-commerce

    # --- Zdravotnictvi -------------------------------------------------------
    "Q31207": ("ZDR-01", "86"),         # health care
    "Q15067276": ("ZDR-01", "86"),      # health care industry
    "Q112166139": ("ZDR-01", "8610"),   # hospital activities
    "Q130370834": ("ZDR-01", "8610"),   # hospitals and rehabilitation
    "Q507443": ("ZDR-03", "21"),        # pharmaceutical industry
    "Q112165702": ("ZDR-03", "4646"),   # wholesale of pharmaceuticals
    "Q6554101": ("ZDR-03", "3250"),     # medical device
    "Q327092": ("ZDR-03", "3250"),      # biomedical engineering
    "Q112165495": ("ZDR-03", "3250"),   # glasses manufacturing
    "Q112166168": ("ZDR-04", "88"),     # outpatient social services

    # --- Odpady a zivotni prostredi ------------------------------------------
    "Q180388": ("ODP-01", "38"),        # waste management
    "Q112165543": ("ODP-01", "3811"),   # collection of non-hazardous waste
    "Q130370849": ("ODP-03", "39"),     # environment

    # --- Verejny a neziskovy sektor ------------------------------------------
    "Q112166113": ("VER-01", "8411"),   # general public administration
    "Q112166115": ("VER-01", "8412"),   # public administration, health & social
    "Q112166116": ("VER-01", "8413"),   # public administration, economy
    "Q130370871": ("VER-02", "9411"),   # business and professional associations
    "Q29586079": ("VER-02", "9499"),    # other membership organisations
    "Q112166193": ("VER-02", "9499"),   # voluntary membership organizations
    "Q130370869": ("VER-02", "9491"),   # religious congregations
    "Q1021488": ("VER-02", "9499"),     # community foundation

    # --- Ostatni -------------------------------------------------------------
    "Q173799": ("OST-01", "90"),        # entertainment
    "Q124022875": ("OST-01", "9311"),   # sporting activities
    "Q112166176": ("OST-01", "9102"),   # museum management
    "Q4373046": ("OST-01", "5911"),     # pornography industry
    "Q112165482": ("OST-02", "3212"),   # jewelry manufacturing
    "Q112165492": ("OST-02", "3240"),   # games and toys
    "Q112165489": ("OST-02", "3230"),   # sports goods
    "Q112166206": ("OST-02", "9603"),   # funeral services
}


# ---------------------------------------------------------------------------
# US: SIC -> NAICS (hrube, na urovni odvetvi). Slouzi k tomu, aby vystup
# nesl i americkou obdobu NACE - firmy v USA vlastni "NACE" nemaji, oficialni
# klasifikace je NAICS, SEC u kazdeho subjektu vede starsi SIC.
# ---------------------------------------------------------------------------

SIC_NA_NAICS = {
    "01": "111", "02": "112", "07": "115", "08": "113", "09": "114",
    "10": "2122", "12": "2121", "13": "211", "14": "2123",
    "15": "236", "16": "237", "17": "238",
    "20": "311", "21": "312230", "22": "313", "23": "315", "24": "321", "25": "337",
    "26": "322", "27": "323", "28": "325", "283": "3254", "29": "324",
    "30": "326", "31": "316", "32": "327", "33": "331", "34": "332",
    "35": "333", "357": "334110", "36": "335", "366": "3342", "367": "3344",
    "37": "336", "372": "33641", "38": "3345", "382": "334513", "384": "3391", "39": "339",
    "40": "482", "41": "485", "42": "484", "44": "483", "45": "481", "46": "486",
    "47": "488", "48": "517", "484": "515", "49": "221",
    "50": "423", "51": "424", "52": "444", "53": "455", "54": "445", "55": "441",
    "56": "458", "57": "449", "58": "722", "59": "459",
    "60": "5221", "61": "5222", "62": "523", "63": "524", "64": "5242", "65": "531",
    "67": "5511", "70": "721", "72": "812", "73": "5415", "7370": "541511",
    "7371": "541511", "7372": "5132", "7374": "518210", "7375": "519290", "7379": "541519",
    "78": "512", "79": "713", "80": "622", "81": "5411", "82": "611", "83": "624",
    "86": "813", "87": "5413", "8711": "541330", "8721": "541211", "8731": "5417",
    "89": "5419", "91": "921", "92": "922", "93": "921", "94": "923", "95": "924",
    "96": "926", "97": "928", "99": "5614",
}

# Nazvy NAICS sektoru (2 mistne) - popis do vystupu u americkych subjektu
NAICS_SEKTORY = {
    "11": "Zemedelstvi, lesnictvi, rybolov a lov",
    "21": "Tezba a dobyvani",
    "22": "Energetika a vodni hospodarstvi",
    "23": "Stavebnictvi",
    "31": "Zpracovatelsky prumysl", "32": "Zpracovatelsky prumysl",
    "33": "Zpracovatelsky prumysl",
    "42": "Velkoobchod",
    "44": "Maloobchod", "45": "Maloobchod",
    "48": "Doprava a skladovani", "49": "Doprava a skladovani",
    "51": "Informacni a mediani cinnosti",
    "52": "Finance a pojistovnictvi",
    "53": "Nemovitosti, pronajem a leasing",
    "54": "Profesni, vedecke a technicke sluzby",
    "55": "Rizeni podniku a holdingy",
    "56": "Administrativni, podpurne a odpadove sluzby",
    "61": "Vzdelavani",
    "62": "Zdravotni a socialni pece",
    "71": "Umeni, zabava a rekreace",
    "72": "Ubytovani a stravovani",
    "81": "Ostatni sluzby",
    "92": "Verejna sprava",
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


def sic_na_naics(sic):
    """Prevede US SIC kod na priblizny NAICS (americka obdoba NACE)."""
    return _prefix(sic, SIC_NA_NAICS)


def nazev_naics(kod):
    """Cesky nazev NAICS sektoru podle prvnich dvou cislic."""
    if not kod:
        return ""
    cislice = "".join(ch for ch in str(kod) if ch.isdigit())
    return NAICS_SEKTORY.get(cislice[:2], "")


def naf_na_nace(naf):
    """
    Francouzsky NAF (APE) je NACE rev. 2 s pismenem na konci - "62.02A" je
    NACE 6202. Staci tedy zahodit oddelovace a koncove pismeno.
    """
    if not naf:
        return ""
    return "".join(ch for ch in str(naf) if ch.isdigit())


# Obory, ktere same o sobe nic neurcuji - pouziji se, jen kdyz Wikidata
# u firmy zadny konkretnejsi obor neuvadi.
OBECNE_OBORY = {
    "Q8148", "Q7406919", "Q187939", "Q11661", "Q110702998", "Q57774188",
    "Q837171", "Q23700345", "Q2151621", "Q1304795", "Q1341477", "Q112166038",
    "Q969040", "Q126793", "Q220695",
}


def obor_na_kategorii(qidy, mapa_oboru=None):
    """
    Z Wikidata oboru cinnosti (seznam QID) vybere kod kategorie a odhad NACE.
    Konkretni obor ma prednost pred obecnym ("energy industry", "retail"),
    protoze velke firmy maji casto vyjmenovanych oboru nekolik.
    """
    mapa_oboru = mapa_oboru if mapa_oboru is not None else WIKIDATA_OBORY
    znamy = [(q, mapa_oboru[q]) for q in (qidy or []) if q in mapa_oboru]
    if not znamy:
        return None, ""
    konkretni = [z for z in znamy if z[0] not in OBECNE_OBORY]
    kod, nace = (konkretni or znamy)[0][1]
    return kod, nace


def nazev_nace(kod):
    """Cesky nazev NACE divize podle prvnich dvou cislic."""
    if not kod:
        return ""
    cislice = "".join(ch for ch in str(kod) if ch.isdigit())
    return NACE_DIVIZE.get(cislice[:2], "")


def zarad(nace=None, mapa=None, kategorie=None, obory=None, mapa_oboru=None):
    """
    Zaradi dodavatele do vlastni taxonomie.

    Poradi duveryhodnosti podkladu:
        1. NACE z rejstriku (CZ, FR, ...)  - nejpresnejsi, skutecny udaj
        2. obor cinnosti z Wikidat (QID)   - strukturovany udaj, ne odhad z
                                             textu; jazykove nezavisly, funguje
                                             i pro korejskou nebo tureckou firmu

    Zamerne se NEODHADUJE kategorie z klicovych slov v nazvu firmy - shoda
    slova v nazvu neni fakt o oboru cinnosti a muze byt vylozene mylna
    (napr. "Deutsche Akkreditierungsstelle" nema nic spolecneho s uverem,
    i kdyz "kredit" jako podretezec sedi). Bez NACE nebo oboru z Wikidat
    jde zaznam do XXX-00 k rucnimu dohledani, misto nejisteho odhadu.

    Vrati dict:
        kod       - kod kategorie, napr. "ICT-03"
        kategorie - nazev kategorie
        skupina   - nadrazena skupina
        zdroj     - 'nace' | 'obor' | 'vychozi'
        nace      - odhad NACE z oboru, pokud zadny NACE na vstupu nebyl
    """
    mapa = mapa if mapa is not None else NACE_MAPA
    kategorie = kategorie if kategorie is not None else KATEGORIE

    kod, zdroj, nace_odhad = None, "vychozi", ""
    if nace:
        kod = _prefix(nace, mapa)
        if kod:
            zdroj = "nace"
    if not kod and obory:
        kod, nace_odhad = obor_na_kategorii(obory, mapa_oboru)
        if kod:
            zdroj = "obor"
    if not kod:
        kod = VYCHOZI_KOD

    skupina, nazev_kat = kategorie.get(kod, kategorie[VYCHOZI_KOD])
    return {"kod": kod, "kategorie": nazev_kat, "skupina": skupina, "zdroj": zdroj,
            "nace": nace_odhad}


def prehled_kategorii():
    """Serazeny seznam (kod, skupina, nazev) - pro ciselnik ve vystupu."""
    return sorted(((k, v[0], v[1]) for k, v in KATEGORIE.items()))


def prehled_nace_divizi():
    """Serazeny seznam (kod, nazev) NACE divizi (2 cislice) - pro ciselnik ve vystupu."""
    return sorted(NACE_DIVIZE.items())


# ---------------------------------------------------------------------------
# Odhad NACE z textu "Gegenstand des Unternehmens" (nemecky, viz
# --de-gegenstand v dodavatele.py). Zbytek teto taxonomie zamerne NEHADA
# obor z volneho textu ci nazvu firmy (viz zarad() vyse) - tohle je vyslovne
# pozadovana vyjimka jen pro tento pripad, protoze Gegenstand je povinna
# pravni formulace predmetu podnikani ze spolecenske smlouvy, ne jen nazev
# firmy, a je tedy nesrovnatelne informativnejsi. I tak jde o odhad z
# klicovych frazi, ne skutecny kod z rejstriku - volajici (dodavatele.py)
# ho proto vzdy oznacuje zvlast, nikdy ho nepleta se skutecnym NACE.
#
# Zamerne se vyhyba obecnym slovum, ktera se objevuji temer v kazdem
# Gegenstand bez ohledu na skutecny obor (Gesellschaft, Erwerb, Beteiligung,
# Zweck, Handlungen...) - stejne riziko falesne shody jako u nazvu firem
# (viz PRAVNI_FORMY / normalizuj_nazev v dodavatele.py). Poradi zaleza:
# konkretnejsi fraze jsou napred, aby se napr. "Grosshandel mit
# Lebensmitteln" nezastavilo uz na obecnejsim "Grosshandel".
# ---------------------------------------------------------------------------

GEGENSTAND_KLICOVA_SLOVA = (
    ("softwareentwicklung", "6201"), ("erstellung von software", "6201"),
    ("it-dienstleistung", "6202"), ("informationstechnologie", "6202"),
    ("personalvermittlung", "7820"), ("zeitarbeit", "7820"),
    ("arbeitnehmerueberlassung", "7820"), ("arbeitnehmerüberlassung", "7820"),
    ("gebaeudereinigung", "8121"), ("gebäudereinigung", "8121"),
    ("sicherheitsdienst", "8010"), ("bewachung", "8010"),
    ("spedition", "5229"), ("gueterbefoerderung", "4941"), ("güterbeförderung", "4941"),
    ("personenbefoerderung", "4931"), ("personenbeförderung", "4931"),
    ("steuerberatung", "6920"), ("wirtschaftspruefung", "6920"), ("wirtschaftsprüfung", "6920"),
    ("rechtsberatung", "6910"), ("rechtsanwalt", "6910"),
    ("unternehmensberatung", "7022"),
    ("werbeagentur", "7311"), ("werbung und marketing", "7311"),
    ("pflegedienst", "8710"), ("ambulante pflege", "8710"), ("seniorenpflege", "8710"),
    ("arztpraxis", "8621"), ("aerztliche leistung", "8621"), ("ärztliche leistung", "8621"),
    ("betrieb von restaurants", "5610"), ("gastronomiebetrieb", "5610"),
    ("gaststaette", "5610"), ("gaststätte", "5610"),
    ("hotelbetrieb", "5510"), ("beherbergung", "5510"),
    ("vermietung von grundstuecken", "6820"), ("vermietung von grundstücken", "6820"),
    ("vermietung von immobilien", "6820"), ("immobilienverwaltung", "6820"),
    ("versicherungsvermittlung", "6622"), ("versicherungsmakler", "6622"),
    ("kreditinstitut", "6419"), ("bankgeschaeft", "6419"), ("bankgeschäft", "6419"),
    ("maschinenbau", "28"), ("herstellung von maschinen", "28"),
    ("fahrzeugbau", "29"), ("herstellung von kraftfahrzeug", "29"),
    ("elektroinstallation", "4321"),
    ("hochbau", "4120"), ("tiefbau", "4221"),
    ("import und grosshandel", "46"), ("import und großhandel", "46"),
    ("grosshandel", "46"), ("großhandel", "46"),
    ("einzelhandel", "47"),
    # POZOR: zamerne tu NEJSOU obecne fraze jako "herstellung und vertrieb"
    # nebo "produktion von" - rikaji jen, ze firma neco vyrabi, ne CO -
    # takova shoda by ukazovala na nahodny kod bez ohledu na skutecny obor
    # (presne overeno na adidas AG - "Herstellung und der Vertrieb von
    # Textilien..." by bez konkretniho produktu v klicovem slovu skoncilo
    # na spatnem NACE). Radeji zadny odhad nez jisty spatny.
)


def nace_z_gegenstand(text):
    """
    Odhad NACE divize/tridy z nemeckeho textu "Gegenstand des Unternehmens"
    podle klicovych frazi - viz komentar u GEGENSTAND_KLICOVA_SLOVA. Vraci
    prazdny retezec, kdyz zadna fraze nesedi (radeji nic nez spatny odhad).
    """
    t = (text or "").lower()
    for fraze, nace in GEGENSTAND_KLICOVA_SLOVA:
        if fraze in t:
            return nace
    return ""


def jako_json():
    return {
        "kategorie": {k: list(v) for k, v in KATEGORIE.items()},
        "nace_mapa": NACE_MAPA,
        "vychozi_kod": VYCHOZI_KOD,
        "sic_na_nace": SIC_NA_NACE,
        "sic_na_naics": SIC_NA_NAICS,
        "wikidata_obory": {k: list(v) for k, v in WIKIDATA_OBORY.items()},
    }


def z_json(data):
    """Vrati (mapa, kategorie, mapa_oboru) z JSON podoby taxonomie."""
    kat = {k: tuple(v) for k, v in data.get("kategorie", {}).items()} or KATEGORIE
    mapa = data.get("nace_mapa") or NACE_MAPA
    oboru = ({k: tuple(v) for k, v in data.get("wikidata_obory", {}).items()}
             or WIKIDATA_OBORY)
    return mapa, kat, oboru

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

import nace_nomenklatura

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
# Co ktery NACE kod znamena pro zarazeni dodavatele
# ---------------------------------------------------------------------------
#
# Kod -> kategorie, nebo None, kdyz kod o predmetu dodavky nerika nic pouzitelneho
# (obecne a formalni registrace jako pronajem nemovitosti nebo "ostatni podpurne
# cinnosti", a narodni pseudo-kody jako britske "99999 Dormant company").
#
# Tabulka je UPLNA - obsahuje kazdy kod z nomenklatury (nace_nomenklatura.py),
# takze nepritomnost kodu je chyba k nahlaseni, ne tiche "plati neco obecneho".
# Kdyz kod v tabulce chybi, chova se jako None.

NACE_KATEGORIE = {

    # --- ?  kody mimo nomenklaturu / narodni ---
    "00": None,        # 
    "0000": None,      # 

    # --- A  Agriculture, forestry and fishing ---
    "01": "MAT-09",    # Crop and animal production, hunting and related service acti
    "011": "MAT-09",   # Growing of non-perennial crops
    "0111": "MAT-09",  # Growing of cereals, other than rice, leguminous crops and oi
    "0112": "MAT-09",  # Growing of rice
    "0113": "MAT-09",  # Growing of vegetables and melons, roots and tubers
    "0114": "MAT-09",  # Growing of sugar cane
    "0115": "MAT-09",  # Growing of tobacco
    "0116": "MAT-09",  # Growing of fibre crops
    "0119": "MAT-09",  # Growing of other non-perennial crops
    "012": "MAT-09",   # Growing of perennial crops
    "0121": "MAT-09",  # Growing of grapes
    "0122": "MAT-09",  # Growing of tropical and subtropical fruits
    "0123": "MAT-09",  # Growing of citrus fruits
    "0124": "MAT-09",  # Growing of pome fruits and stone fruits
    "0125": "MAT-09",  # Growing of other tree and bush fruits and nuts
    "0126": "MAT-09",  # Growing of oleaginous fruits
    "0127": "MAT-09",  # Growing of beverage crops
    "0128": "MAT-09",  # Growing of spices, aromatic, drug and pharmaceutical crops
    "0129": "MAT-09",  # Growing of other perennial crops
    "013": "MAT-09",   # Plant propagation
    "0130": "MAT-09",  # Plant propagation
    "014": "MAT-09",   # Animal production
    "0141": "MAT-09",  # Raising of dairy cattle
    "0142": "MAT-09",  # Raising of other cattle and buffaloes
    "0143": "MAT-09",  # Raising of horses and other equines
    "0144": "MAT-09",  # Raising of camels and camelids
    "0145": "MAT-09",  # Raising of sheep and goats
    "0146": "MAT-09",  # Raising of swine and pigs
    "0147": "MAT-09",  # Raising of poultry
    "0148": "MAT-09",  # Raising of other animals
    "0149": "MAT-09",  # Raising of other animals
    "015": "MAT-09",   # Mixed farming
    "0150": "MAT-09",  # Mixed farming
    "016": "MAT-09",   # Support activities to agriculture and post-harvest crop acti
    "0161": "MAT-09",  # Support activities for crop production
    "0162": "MAT-09",  # Support activities for animal production
    "0163": "MAT-09",  # Post-harvest crop activities and seed processing for propaga
    "0164": "MAT-09",  # Seed processing for propagation
    "017": "MAT-09",   # Hunting, trapping and related service activities
    "0170": "MAT-09",  # Hunting, trapping and related service activities
    "02": "MAT-11",    # Forestry and logging
    "021": "MAT-11",   # Silviculture and other forestry activities
    "0210": "MAT-11",  # Silviculture and other forestry activities
    "022": "MAT-11",   # Logging
    "0220": "MAT-11",  # Logging
    "023": "MAT-11",   # Gathering of wild growing non-wood products
    "0230": "MAT-11",  # Gathering of wild growing non-wood products
    "024": "MAT-11",   # Support services to forestry
    "0240": "MAT-11",  # Support services to forestry
    "03": "MAT-09",    # Fishing and aquaculture
    "031": "MAT-09",   # Fishing
    "0311": "MAT-09",  # Marine fishing
    "0312": "MAT-09",  # Freshwater fishing
    "032": "MAT-09",   # Aquaculture
    "0321": "MAT-09",  # Marine aquaculture
    "0322": "MAT-09",  # Freshwater aquaculture
    "033": "MAT-09",   # Support activities for fishing and aquaculture
    "0330": "MAT-09",  # Support activities for fishing and aquaculture

    # --- B  Mining and quarrying ---
    "05": "MAT-10",    # Mining of coal and lignite
    "051": "MAT-10",   # Mining of hard coal
    "0510": "MAT-10",  # Mining of hard coal
    "052": "MAT-10",   # Mining of lignite
    "0520": "MAT-10",  # Mining of lignite
    "06": "ENE-03",    # Extraction of crude petroleum and natural gas
    "061": "ENE-03",   # Extraction of crude petroleum
    "0610": "ENE-03",  # Extraction of crude petroleum
    "062": "ENE-03",   # Extraction of natural gas
    "0620": "ENE-03",  # Extraction of natural gas
    "07": "MAT-10",    # Mining of metal ores
    "071": "MAT-10",   # Mining of iron ores
    "0710": "MAT-10",  # Mining of iron ores
    "072": "MAT-10",   # Mining of non-ferrous metal ores
    "0721": "MAT-10",  # Mining of uranium and thorium ores
    "0729": "MAT-10",  # Mining of other non-ferrous metal ores
    "08": "MAT-05",    # Other mining and quarrying
    "081": "MAT-05",   # Quarrying of stone, sand and clay
    "0811": "MAT-05",  # Quarrying of ornamental stone, limestone, gypsum, slate and 
    "0812": "MAT-05",  # Operation of gravel and sand pits and mining of clay and kao
    "089": "MAT-05",   # Mining and quarrying n.e.c.
    "0891": "MAT-05",  # Mining of chemical and fertiliser minerals
    "0892": "MAT-05",  # Extraction of peat
    "0893": "MAT-05",  # Extraction of salt
    "0899": "MAT-05",  # Other mining and quarrying n.e.c.
    "09": "MAT-10",    # Mining support service activities
    "091": "MAT-10",   # Support activities for petroleum and natural gas extraction
    "0910": "MAT-10",  # Support activities for petroleum and natural gas extraction
    "099": "MAT-10",   # Support activities for other mining and quarrying
    "0990": "MAT-10",  # Support activities for other mining and quarrying

    # --- C  Manufacturing ---
    "10": "MAT-08",    # Manufacture of food products
    "101": "MAT-08",   # Processing and preserving of meat and production of meat pro
    "1011": "MAT-08",  # Processing and preserving of meat, except of poultry meat
    "1012": "MAT-08",  # Processing and preserving of poultry meat
    "1013": "MAT-08",  # Production of meat and poultry meat products
    "102": "MAT-08",   # Processing and preserving of fish, crustaceans and molluscs
    "1020": "MAT-08",  # Processing and preserving of fish, crustaceans and molluscs
    "103": "MAT-08",   # Processing and preserving of fruit and vegetables
    "1031": "MAT-08",  # Processing and preserving of potatoes
    "1032": "MAT-08",  # Manufacture of fruit and vegetable juice
    "1039": "MAT-08",  # Other processing and preserving of fruit and vegetables
    "104": "MAT-08",   # Manufacture of vegetable and animal oils and fats
    "1041": "MAT-08",  # Manufacture of oils and fats
    "1042": "MAT-08",  # Manufacture of margarine and similar edible fats
    "105": "MAT-08",   # Manufacture of dairy products and edible ice
    "1051": "MAT-08",  # Manufacture of dairy products
    "1052": "MAT-08",  # Manufacture of ice cream and other edible ice
    "106": "MAT-08",   # Manufacture of grain mill products, starches and starch prod
    "1061": "MAT-08",  # Manufacture of grain mill products
    "1062": "MAT-08",  # Manufacture of starches and starch products
    "107": "MAT-08",   # Manufacture of bakery and farinaceous products
    "1071": "MAT-08",  # Manufacture of bread; manufacture of fresh pastry goods and 
    "1072": "MAT-08",  # Manufacture of rusks, biscuits, preserved pastries and cakes
    "1073": "MAT-08",  # Manufacture of farinaceous products
    "108": "MAT-08",   # Manufacture of other food products
    "1081": "MAT-08",  # Manufacture of sugar
    "1082": "MAT-08",  # Manufacture of cocoa, chocolate and sugar confectionery
    "1083": "MAT-08",  # Processing of tea and coffee
    "1084": "MAT-08",  # Manufacture of condiments and seasonings
    "1085": "MAT-08",  # Manufacture of prepared meals and dishes
    "1086": "MAT-08",  # Manufacture of homogenised food preparations and dietetic fo
    "1089": "MAT-08",  # Manufacture of other food products n.e.c.
    "109": "MAT-08",   # Manufacture of prepared animal feeds
    "1091": "MAT-08",  # Manufacture of prepared feeds for farm animals
    "1092": "MAT-08",  # Manufacture of prepared pet foods
    "11": "MAT-08",    # Manufacture of beverages
    "110": "MAT-08",   # Manufacture of beverages
    "1101": "MAT-08",  # Distilling, rectifying and blending of spirits
    "1102": "MAT-08",  # Manufacture of wine from grape
    "1103": "MAT-08",  # Manufacture of cider and other fruit fermented beverages
    "1104": "MAT-08",  # Manufacture of other non-distilled fermented beverages
    "1105": "MAT-08",  # Manufacture of beer
    "1106": "MAT-08",  # Manufacture of malt
    "1107": "MAT-08",  # Manufacture of soft drinks and bottled waters
    "12": "MAT-08",    # Manufacture of tobacco products
    "120": "MAT-08",   # Manufacture of tobacco products
    "1200": "MAT-08",  # Manufacture of tobacco products
    "13": "MAT-06",    # Manufacture of textiles
    "131": "MAT-06",   # Preparation and spinning of textile fibres
    "1310": "MAT-06",  # Preparation and spinning of textile fibres
    "132": "MAT-06",   # Weaving of textiles
    "1320": "MAT-06",  # Weaving of textiles
    "133": "MAT-06",   # Finishing of textiles
    "1330": "MAT-06",  # Finishing of textiles
    "139": "MAT-06",   # Manufacture of other textiles
    "1391": "MAT-06",  # Manufacture of knitted and crocheted fabrics
    "1392": "MAT-06",  # Manufacture of household textiles and made-up furnishing art
    "1393": "MAT-06",  # Manufacture of carpets and rugs
    "1394": "MAT-06",  # Manufacture of cordage, rope, twine and netting
    "1395": "MAT-06",  # Manufacture of non-wovens and non-woven articles
    "1396": "MAT-06",  # Manufacture of other technical and industrial textiles
    "1399": "MAT-06",  # Manufacture of other textiles n.e.c.
    "14": "MAT-06",    # Manufacture of wearing apparel
    "141": "MAT-06",   # Manufacture of knitted and crocheted apparel
    "1410": "MAT-06",  # Manufacture of knitted and crocheted apparel
    "1411": "MAT-06",  # Manufacture of leather clothes
    "1412": "MAT-06",  # Manufacture of workwear
    "1413": "MAT-06",  # Manufacture of other outerwear
    "1414": "MAT-06",  # Manufacture of underwear
    "1419": "MAT-06",  # Manufacture of other wearing apparel and accessories
    "142": "MAT-06",   # Manufacture of other wearing apparel and accessories
    "1420": "MAT-06",  # Manufacture of articles of fur
    "1421": "MAT-06",  # Manufacture of outerwear
    "1422": "MAT-06",  # Manufacture of underwear
    "1423": "MAT-06",  # Manufacture of workwear
    "1424": "MAT-06",  # Manufacture of leather clothes and fur apparel
    "1429": "MAT-06",  # Manufacture of other wearing apparel and accessories n.e.c.
    "143": "MAT-06",   # Manufacture of knitted and crocheted apparel
    "1431": "MAT-06",  # Manufacture of knitted and crocheted hosiery
    "1439": "MAT-06",  # Manufacture of other knitted and crocheted apparel
    "15": "MAT-06",    # Manufacture of leather and related products of other materia
    "151": "MAT-06",   # Tanning, dyeing, dressing of leather and fur; manufacture of
    "1511": "MAT-06",  # Tanning, dressing, dyeing of leather and fur
    "1512": "MAT-06",  # Manufacture of luggage, handbags, saddlery and harness of an
    "152": "MAT-06",   # Manufacture of footwear
    "1520": "MAT-06",  # Manufacture of footwear
    "16": None,        # Manufacture of wood and of products of wood and cork, except
    "161": "MAT-11",   # Sawmilling and planing of wood; processing and finishing of 
    "1610": "MAT-11",  # Sawmilling and planing of wood
    "1611": "MAT-11",  # Sawmilling and planing of wood
    "1612": "MAT-11",  # Processing and finishing of wood
    "162": None,       # Manufacture of products of wood, cork, straw and plaiting ma
    "1621": "MAT-11",  # Manufacture of veneer sheets and wood-based panels
    "1622": "MAT-11",  # Manufacture of assembled parquet floors
    "1623": "MAT-11",  # Manufacture of other builders' carpentry and joinery
    "1624": "MAT-11",  # Manufacture of wooden containers
    "1625": "MAT-11",  # Manufacture of doors and windows of wood
    "1626": "ENE-03",  # Manufacture of solid fuels from vegetable biomass
    "1627": "MAT-11",  # Finishing of wooden products
    "1628": "MAT-11",  # Manufacture of other products of wood and articles of cork, 
    "1629": "MAT-11",  # Manufacture of other products of wood; manufacture of articl
    "17": "MAT-04",    # Manufacture of paper and paper products
    "171": "MAT-04",   # Manufacture of pulp, paper and paperboard
    "1711": "MAT-04",  # Manufacture of pulp
    "1712": "MAT-04",  # Manufacture of paper and paperboard
    "172": "MAT-04",   # Manufacture of articles of paper and paperboard
    "1721": "MAT-04",  # Manufacture of corrugated paper, paperboard and containers o
    "1722": "MAT-04",  # Manufacture of household and sanitary goods and of toilet re
    "1723": "MAT-04",  # Manufacture of paper stationery
    "1724": "MAT-04",  # Manufacture of wallpaper
    "1725": "MAT-04",  # Manufacture of other articles of paper and paperboard
    "1729": "MAT-04",  # Manufacture of other articles of paper and paperboard
    "18": "MKT-03",    # Printing and reproduction of recorded media
    "181": "MKT-03",   # Printing and service activities related to printing
    "1811": "MKT-03",  # Printing of newspapers
    "1812": "MKT-03",  # Other printing
    "1813": "MKT-03",  # Pre-press and pre-media services
    "1814": "MKT-03",  # Binding and related services
    "182": "MKT-03",   # Reproduction of recorded media
    "1820": "MKT-03",  # Reproduction of recorded media
    "19": "ENE-03",    # Manufacture of coke and refined petroleum products
    "191": "ENE-03",   # Manufacture of coke oven products
    "1910": "ENE-03",  # Manufacture of coke oven products
    "192": "ENE-03",   # Manufacture of refined petroleum products and fossil fuel pr
    "1920": "ENE-03",  # Manufacture of refined petroleum products and fossil fuel pr
    "20": "MAT-02",    # Manufacture of chemicals and chemical products
    "201": "MAT-02",   # Manufacture of basic chemicals, fertilisers and nitrogen com
    "2011": "MAT-02",  # Manufacture of industrial gases
    "2012": "MAT-02",  # Manufacture of dyes and pigments
    "2013": "MAT-02",  # Manufacture of other inorganic basic chemicals
    "2014": "MAT-02",  # Manufacture of other organic basic chemicals
    "2015": "MAT-02",  # Manufacture of fertilisers and nitrogen compounds
    "2016": "MAT-02",  # Manufacture of plastics in primary forms
    "2017": "MAT-02",  # Manufacture of synthetic rubber in primary forms
    "202": "MAT-02",   # Manufacture of pesticides, disinfectants and other agrochemi
    "2020": "MAT-02",  # Manufacture of pesticides, disinfectants and other agrochemi
    "203": "MAT-02",   # Manufacture of paints, varnishes and similar coatings, print
    "2030": "MAT-02",  # Manufacture of paints, varnishes and similar coatings, print
    "204": "MAT-02",   # Manufacture of washing, cleaning and polishing preparations
    "2041": "MAT-02",  # Manufacture of soap and detergents, cleaning and polishing p
    "2042": "MAT-02",  # Manufacture of perfumes and toilet preparations
    "205": "MAT-02",   # Manufacture of other chemical products
    "2051": "MAT-02",  # Manufacture of liquid biofuels
    "2052": "MAT-02",  # Manufacture of glues
    "2053": "MAT-02",  # Manufacture of essential oils
    "2059": "MAT-02",  # Manufacture of other chemical products n.e.c.
    "206": "MAT-02",   # Manufacture of man-made fibres
    "2060": "MAT-02",  # Manufacture of man-made fibres
    "21": "ZDR-03",    # Manufacture of basic pharmaceutical products and pharmaceuti
    "211": "ZDR-03",   # Manufacture of basic pharmaceutical products
    "2110": "ZDR-03",  # Manufacture of basic pharmaceutical products
    "212": "ZDR-03",   # Manufacture of pharmaceutical preparations
    "2120": "ZDR-03",  # Manufacture of pharmaceutical preparations
    "22": None,        # Manufacture of rubber and plastic products
    "221": "MAT-03",   # Manufacture of rubber products
    "2211": "MAT-03",  # Manufacture, retreading and rebuilding of rubber tyres and m
    "2212": "MAT-03",  # Manufacture of other rubber products
    "2219": "MAT-03",  # Manufacture of other rubber products
    "222": None,       # Manufacture of plastics products
    "2221": "MAT-03",  # Manufacture of plastic plates, sheets, tubes and profiles
    "2222": "MAT-04",  # Manufacture of plastic packing goods
    "2223": "MAT-05",  # Manufacture of doors and windows of plastic
    "2224": "MAT-05",  # Manufacture of builders’ ware of plastic
    "2225": "MAT-03",  # Processing and finishing of plastic products
    "2226": "MAT-03",  # Manufacture of other plastic products
    "2229": "MAT-03",  # Manufacture of other plastic products
    "23": "MAT-05",    # Manufacture of other non-metallic mineral products
    "231": "MAT-05",   # Manufacture of glass and glass products
    "2311": "MAT-05",  # Manufacture of flat glass
    "2312": "MAT-05",  # Shaping and processing of flat glass
    "2313": "MAT-05",  # Manufacture of hollow glass
    "2314": "MAT-05",  # Manufacture of glass fibres
    "2315": "MAT-05",  # Manufacture and processing of other glass, including technic
    "2319": "MAT-05",  # Manufacture and processing of other glass, including technic
    "232": "MAT-05",   # Manufacture of refractory products
    "2320": "MAT-05",  # Manufacture of refractory products
    "233": "MAT-05",   # Manufacture of clay building materials
    "2331": "MAT-05",  # Manufacture of ceramic tiles and flags
    "2332": "MAT-05",  # Manufacture of bricks, tiles and construction products, in b
    "234": "MAT-05",   # Manufacture of other porcelain and ceramic products
    "2341": "MAT-05",  # Manufacture of ceramic household and ornamental articles
    "2342": "MAT-05",  # Manufacture of ceramic sanitary fixtures
    "2343": "MAT-05",  # Manufacture of ceramic insulators and insulating fittings
    "2344": "MAT-05",  # Manufacture of other technical ceramic products
    "2345": "MAT-05",  # Manufacture of other ceramic products
    "2349": "MAT-05",  # Manufacture of other ceramic products
    "235": "MAT-05",   # Manufacture of cement, lime and plaster
    "2351": "MAT-05",  # Manufacture of cement
    "2352": "MAT-05",  # Manufacture of lime and plaster
    "236": "MAT-05",   # Manufacture of articles of concrete, cement and plaster
    "2361": "MAT-05",  # Manufacture of concrete products for construction purposes
    "2362": "MAT-05",  # Manufacture of plaster products for construction purposes
    "2363": "MAT-05",  # Manufacture of ready-mixed concrete
    "2364": "MAT-05",  # Manufacture of mortars
    "2365": "MAT-05",  # Manufacture of fibre cement
    "2366": "MAT-05",  # Manufacture of other articles of concrete, plaster and cemen
    "2369": "MAT-05",  # Manufacture of other articles of concrete, plaster and cemen
    "237": "MAT-05",   # Cutting, shaping and finishing of stone
    "2370": "MAT-05",  # Cutting, shaping and finishing of stone
    "239": "MAT-05",   # Manufacture of abrasive products and non-metallic mineral pr
    "2391": "MAT-05",  # Manufacture of abrasive products
    "2399": "MAT-05",  # Manufacture of other non-metallic mineral products n.e.c.
    "24": "MAT-01",    # Manufacture of basic metals
    "241": "MAT-01",   # Manufacture of basic iron and steel and of ferro-alloys
    "2410": "MAT-01",  # Manufacture of basic iron and steel and of ferro-alloys
    "242": "MAT-01",   # Manufacture of tubes, pipes, hollow profiles and related fit
    "2420": "MAT-01",  # Manufacture of tubes, pipes, hollow profiles and related fit
    "243": "MAT-01",   # Manufacture of other products of first processing of steel
    "2431": "MAT-01",  # Cold drawing of bars
    "2432": "MAT-01",  # Cold rolling of narrow strip
    "2433": "MAT-01",  # Cold forming or folding
    "2434": "MAT-01",  # Cold drawing of wire
    "244": "MAT-01",   # Manufacture of basic precious and other non-ferrous metals
    "2441": "MAT-01",  # Precious metals production
    "2442": "MAT-01",  # Aluminium production
    "2443": "MAT-01",  # Lead, zinc and tin production
    "2444": "MAT-01",  # Copper production
    "2445": "MAT-01",  # Other non-ferrous metal production
    "2446": "MAT-01",  # Processing of nuclear fuel
    "245": "MAT-01",   # Casting of metals
    "2451": "MAT-01",  # Casting of iron
    "2452": "MAT-01",  # Casting of steel
    "2453": "MAT-01",  # Casting of light metals
    "2454": "MAT-01",  # Casting of other non-ferrous metals
    "25": None,        # Manufacture of fabricated metal products, except machinery a
    "251": "TEC-07",   # Manufacture of structural metal products
    "2511": "TEC-07",  # Manufacture of metal structures and parts of structures
    "2512": "TEC-07",  # Manufacture of doors and windows of metal
    "252": "TEC-07",   # Manufacture of tanks, reservoirs and containers of metal
    "2521": "TEC-07",  # Manufacture of central heating radiators, steam generators a
    "2522": "TEC-07",  # Manufacture of other tanks, reservoirs and containers of met
    "2529": "TEC-07",  # Manufacture of other tanks, reservoirs and containers of met
    "253": "TEC-07",   # Manufacture of weapons and ammunition
    "2530": "TEC-07",  # Manufacture of weapons and ammunition
    "254": "TEC-07",   # Forging and shaping metal and powder metallurgy
    "2540": "TEC-07",  # Forging and shaping metal and powder metallurgy
    "255": "TEC-07",   # Treatment and coating of metals; machining
    "2550": "TEC-07",  # Forging, pressing, stamping and roll-forming of metal; powde
    "2551": "TEC-07",  # Coating of metals
    "2552": "TEC-07",  # Heat treatment of metals
    "2553": "TEC-07",  # Machining of metals
    "256": "TEC-07",   # Manufacture of cutlery, tools and general hardware
    "2561": "TEC-07",  # Manufacture of cutlery
    "2562": "TEC-07",  # Manufacture of locks and hinges
    "2563": "TEC-07",  # Manufacture of tools
    "257": "TEC-07",   # Manufacture of cutlery, tools and general hardware
    "2571": "TEC-07",  # Manufacture of cutlery
    "2572": "TEC-07",  # Manufacture of locks and hinges
    "2573": "TEC-07",  # Manufacture of tools
    "259": None,       # Manufacture of other fabricated metal products
    "2591": "MAT-04",  # Manufacture of steel drums and similar containers
    "2592": "MAT-04",  # Manufacture of light metal packaging
    "2593": "TEC-07",  # Manufacture of wire products, chain and springs
    "2594": "TEC-07",  # Manufacture of fasteners and screw machine products
    "2599": "TEC-07",  # Manufacture of other fabricated metal products n.e.c.
    "26": None,        # Manufacture of computer, electronic and optical products
    "261": "MAT-07",   # Manufacture of electronic components and boards
    "2611": "MAT-07",  # Manufacture of electronic components
    "2612": "MAT-07",  # Manufacture of loaded electronic boards
    "262": "ICT-07",   # Manufacture of computers and peripheral equipment
    "2620": "ICT-07",  # Manufacture of computers and peripheral equipment
    "263": "ICT-08",   # Manufacture of communication equipment
    "2630": "ICT-08",  # Manufacture of communication equipment
    "264": "ICT-07",   # Manufacture of consumer electronics
    "2640": "ICT-07",  # Manufacture of consumer electronics
    "265": None,       # Manufacture of measuring testing instruments, clocks and wat
    "2651": "TEC-02",  # Manufacture of instruments and appliances for measuring, tes
    "2652": "OST-02",  # Manufacture of watches and clocks
    "266": "ZDR-03",   # Manufacture of irradiation, electromedical and electrotherap
    "2660": "ZDR-03",  # Manufacture of irradiation, electromedical and electrotherap
    "267": "MAT-07",   # Manufacture of optical instruments, magnetic and optical med
    "2670": "MAT-07",  # Manufacture of optical instruments, magnetic and optical med
    "268": "MAT-07",   # Manufacture of magnetic and optical media
    "2680": "MAT-07",  # Manufacture of magnetic and optical media
    "27": None,        # Manufacture of electrical equipment
    "271": "TEC-04",   # Manufacture of electric motors, generators, transformers and
    "2711": "TEC-04",  # Manufacture of electric motors, generators and transformers
    "2712": "TEC-04",  # Manufacture of electricity distribution and control apparatu
    "272": "TEC-04",   # Manufacture of batteries and accumulators
    "2720": "TEC-04",  # Manufacture of batteries and accumulators
    "273": "MAT-07",   # Manufacture of wiring and wiring devices
    "2731": "MAT-07",  # Manufacture of fibre optic cables
    "2732": "MAT-07",  # Manufacture of other electronic and electric wires and cable
    "2733": "MAT-07",  # Manufacture of wiring devices
    "274": "TEC-04",   # Manufacture of lighting equipment
    "2740": "TEC-04",  # Manufacture of lighting equipment
    "275": "TEC-04",   # Manufacture of domestic appliances
    "2751": "TEC-04",  # Manufacture of electric domestic appliances
    "2752": "TEC-04",  # Manufacture of non-electric domestic appliances
    "279": "TEC-04",   # Manufacture of other electrical equipment
    "2790": "TEC-04",  # Manufacture of other electrical equipment
    "28": "TEC-01",    # Manufacture of machinery and equipment n.e.c.
    "281": "TEC-01",   # Manufacture of general-purpose machinery
    "2811": "TEC-01",  # Manufacture of engines and turbines, except aircraft, vehicl
    "2812": "TEC-01",  # Manufacture of fluid power equipment
    "2813": "TEC-01",  # Manufacture of other pumps and compressors
    "2814": "TEC-01",  # Manufacture of other taps and valves
    "2815": "TEC-01",  # Manufacture of bearings, gears, gearing and driving elements
    "282": "TEC-01",   # Manufacture of other general-purpose machinery
    "2821": "TEC-01",  # Manufacture of ovens, furnaces and permanent household heati
    "2822": "TEC-01",  # Manufacture of lifting and handling equipment
    "2823": "TEC-01",  # Manufacture of office machinery and equipment, except comput
    "2824": "TEC-01",  # Manufacture of power-driven hand tools
    "2825": "TEC-01",  # Manufacture of non-domestic air conditioning equipment
    "2829": "TEC-01",  # Manufacture of other general-purpose machinery n.e.c.
    "283": "TEC-01",   # Manufacture of agricultural and forestry machinery
    "2830": "TEC-01",  # Manufacture of agricultural and forestry machinery
    "284": "TEC-01",   # Manufacture of metal forming machinery and machine tools
    "2841": "TEC-01",  # Manufacture of metal forming machinery and machine tools for
    "2842": "TEC-01",  # Manufacture of other machine tools
    "2849": "TEC-01",  # Manufacture of other machine tools
    "289": "TEC-01",   # Manufacture of other special-purpose machinery
    "2891": "TEC-01",  # Manufacture of machinery for metallurgy
    "2892": "TEC-01",  # Manufacture of machinery for mining, quarrying and construct
    "2893": "TEC-01",  # Manufacture of machinery for food, beverage and tobacco proc
    "2894": "TEC-01",  # Manufacture of machinery for textile, apparel and leather pr
    "2895": "TEC-01",  # Manufacture of machinery for paper and paperboard production
    "2896": "TEC-01",  # Manufacture of plastics and rubber machinery
    "2897": "TEC-01",  # Manufacture of additive manufacturing machinery
    "2899": "TEC-01",  # Manufacture of other special-purpose machinery n.e.c.
    "29": "TEC-05",    # Manufacture of motor vehicles, trailers and semi-trailers
    "291": "TEC-05",   # Manufacture of motor vehicles
    "2910": "TEC-05",  # Manufacture of motor vehicles
    "292": "TEC-05",   # Manufacture of bodies and coachwork for motor vehicles; manu
    "2920": "TEC-05",  # Manufacture of bodies and coachwork for motor vehicles; manu
    "293": "TEC-05",   # Manufacture of motor vehicle parts and accessories
    "2931": "TEC-05",  # Manufacture of electrical and electronic equipment for motor
    "2932": "TEC-05",  # Manufacture of other parts and accessories for motor vehicle
    "30": "TEC-05",    # Manufacture of other transport equipment
    "301": "TEC-05",   # Building of ships and boats
    "3011": "TEC-05",  # Building of civilian ships and floating structures
    "3012": "TEC-05",  # Building of pleasure and sporting boats
    "3013": "TEC-05",  # Building of military ships and vessels
    "302": "TEC-05",   # Manufacture of railway locomotives and rolling stock
    "3020": "TEC-05",  # Manufacture of railway locomotives and rolling stock
    "303": "TEC-05",   # Manufacture of air and spacecraft and related machinery
    "3030": "TEC-05",  # Manufacture of air and spacecraft and related machinery
    "3031": "TEC-05",  # Manufacture of civilian air and spacecraft and related machi
    "3032": "TEC-05",  # Manufacture of military air and spacecraft and related machi
    "304": "TEC-05",   # Manufacture of military fighting vehicles
    "3040": "TEC-05",  # Manufacture of military fighting vehicles
    "309": "TEC-05",   # Manufacture of transport equipment n.e.c.
    "3091": "TEC-05",  # Manufacture of motorcycles
    "3092": "TEC-05",  # Manufacture of bicycles and invalid carriages
    "3099": "TEC-05",  # Manufacture of other transport equipment n.e.c.
    "31": "FAC-07",    # Manufacture of furniture
    "310": "FAC-07",   # Manufacture of furniture
    "3100": "FAC-07",  # Manufacture of furniture
    "3101": "FAC-07",  # Manufacture of office and shop furniture
    "3102": "FAC-07",  # Manufacture of kitchen furniture
    "3103": "FAC-07",  # Manufacture of mattresses
    "3109": "FAC-07",  # Manufacture of other furniture
    "32": None,        # Other manufacturing
    "321": "OST-02",   # Manufacture of jewellery, bijouterie and related articles
    "3211": "OST-02",  # Striking of coins
    "3212": "OST-02",  # Manufacture of jewellery and related articles
    "3213": "OST-02",  # Manufacture of imitation jewellery and related articles
    "322": "OST-02",   # Manufacture of musical instruments
    "3220": "OST-02",  # Manufacture of musical instruments
    "323": "OST-02",   # Manufacture of sports goods
    "3230": "OST-02",  # Manufacture of sports goods
    "324": "OST-02",   # Manufacture of games and toys
    "3240": "OST-02",  # Manufacture of games and toys
    "325": "ZDR-03",   # Manufacture of medical and dental instruments and supplies
    "3250": "ZDR-03",  # Manufacture of medical and dental instruments and supplies
    "329": "OST-02",   # Manufacturing n.e.c.
    "3291": "OST-02",  # Manufacture of brooms and brushes
    "3299": "OST-02",  # Other manufacturing n.e.c.
    "33": "TEC-03",    # Repair, maintenance and installation of machinery and equipm
    "331": "TEC-03",   # Repair and maintenance of fabricated metal products, machine
    "3311": "TEC-03",  # Repair and maintenance of fabricated metal products
    "3312": "TEC-03",  # Repair and maintenance of machinery
    "3313": "TEC-03",  # Repair and maintenance of electronic and optical equipment
    "3314": "TEC-03",  # Repair and maintenance of electrical equipment
    "3315": "TEC-03",  # Repair and maintenance of civilian ships and boats
    "3316": "TEC-03",  # Repair and maintenance of civilian air and spacecraft
    "3317": "TEC-03",  # Repair and maintenance of other civilian transport equipment
    "3318": "TEC-03",  # Repair and maintenance of military fighting vehicles, ships,
    "3319": "TEC-03",  # Repair and maintenance of other equipment
    "332": "TEC-03",   # Installation of industrial machinery and equipment
    "3320": "TEC-03",  # Installation of industrial machinery and equipment

    # --- D  Electricity, gas, steam and air conditioning supply ---
    "35": None,        # Electricity, gas, steam and air conditioning supply
    "351": "ENE-01",   # Electric power generation, transmission and distribution
    "3511": "ENE-01",  # Production of electricity from non-renewable sources
    "3512": "ENE-01",  # Production of electricity from renewable sources
    "3513": "ENE-01",  # Transmission of electricity
    "3514": "ENE-01",  # Distribution of electricity
    "3515": "ENE-01",  # Trade of electricity
    "3516": "ENE-01",  # Storage of electricity
    "352": "ENE-01",   # Manufacture of gas, and distribution of gaseous fuels throug
    "3521": "ENE-01",  # Manufacture of gas
    "3522": "ENE-01",  # Distribution of gaseous fuels through mains
    "3523": "ENE-01",  # Trade of gas through mains
    "3524": "ENE-01",  # Storage of gas as part of network supply services
    "353": "ENE-02",   # Steam and air conditioning supply
    "3530": "ENE-02",  # Steam and air conditioning supply
    "354": "ENE-01",   # Activities of brokers and agents for electric power and natu
    "3540": "ENE-01",  # Activities of brokers and agents for electric power and natu

    # --- E  Water supply; sewerage, waste management and remediation activities ---
    "36": "ENE-04",    # Water collection, treatment and supply
    "360": "ENE-04",   # Water collection, treatment and supply
    "3600": "ENE-04",  # Water collection, treatment and supply
    "37": "ENE-04",    # Sewerage
    "370": "ENE-04",   # Sewerage
    "3700": "ENE-04",  # Sewerage
    "38": None,        # Waste collection, recovery and disposal activities
    "381": "ODP-01",   # Waste collection
    "3811": "ODP-01",  # Collection of non-hazardous waste
    "3812": "ODP-01",  # Collection of hazardous waste
    "382": None,       # Waste recovery
    "3821": "ODP-01",  # Materials recovery
    "3822": "ENE-02",  # Energy recovery
    "3823": "ODP-01",  # Other waste recovery
    "383": "ODP-01",   # Waste disposal without recovery
    "3831": "ODP-01",  # Incineration without energy recovery
    "3832": "ODP-01",  # Landfilling or permanent storage
    "3833": "ODP-01",  # Other waste disposal
    "39": "ODP-03",    # Remediation activities and other waste management service ac
    "390": "ODP-03",   # Remediation activities and other waste management service ac
    "3900": "ODP-03",  # Remediation activities and other waste management service ac

    # --- F  Construction ---
    "41": "STA-01",    # Construction of residential and non-residential buildings
    "410": "STA-01",   # Construction of residential and non-residential buildings
    "4100": "STA-01",  # Construction of residential and non-residential buildings
    "411": "STA-01",   # Development of building projects
    "4110": "STA-01",  # Development of building projects
    "412": "STA-01",   # Construction of residential and non-residential buildings
    "4120": "STA-01",  # Construction of residential and non-residential buildings
    "42": "STA-02",    # Civil engineering
    "421": "STA-02",   # Construction of roads and railways
    "4211": "STA-02",  # Construction of roads and motorways
    "4212": "STA-02",  # Construction of railways and underground railways
    "4213": "STA-02",  # Construction of bridges and tunnels
    "422": "STA-02",   # Construction of utility projects
    "4221": "STA-02",  # Construction of utility projects for fluids
    "4222": "STA-02",  # Construction of utility projects for electricity and telecom
    "429": "STA-02",   # Construction of other civil engineering projects
    "4291": "STA-02",  # Construction of water projects
    "4299": "STA-02",  # Construction of other civil engineering projects n.e.c.
    "43": None,        # Specialised construction activities
    "431": "STA-03",   # Demolition and site preparation
    "4311": "STA-03",  # Demolition
    "4312": "STA-03",  # Site preparation
    "4313": "STA-03",  # Test drilling and boring
    "432": None,       # Electrical, plumbing and other construction installation act
    "4321": "STA-04",  # Electrical installation
    "4322": "STA-03",  # Plumbing, heat and air-conditioning installation
    "4323": "STA-03",  # Installation of insulation
    "4324": "STA-03",  # Other construction installation
    "4329": "STA-03",  # Other construction installation
    "433": "STA-03",   # Building completion and finishing
    "4331": "STA-03",  # Plastering
    "4332": "STA-03",  # Joinery installation
    "4333": "STA-03",  # Floor and wall covering
    "4334": "STA-03",  # Painting and glazing
    "4335": "STA-03",  # Other building completion and finishing
    "4339": "STA-03",  # Other building completion and finishing
    "434": "STA-03",   # Specialised construction activities in construction of build
    "4341": "STA-03",  # Roofing activities
    "4342": "STA-03",  # Other specialised construction activities in construction of
    "435": "STA-03",   # Specialised construction activities in civil engineering
    "4350": "STA-03",  # Specialised construction activities in civil engineering
    "436": None,       # Intermediation service activities for specialised constructi
    "4360": None,      # Intermediation service activities for specialised constructi
    "439": None,       # Other specialised construction activities
    "4391": "STA-03",  # Masonry and bricklaying activities
    "4399": None,      # Other specialised construction activities n.e.c.

    # --- G  Wholesale and retail trade ---
    "45": "OBC-03",    # Wholesale and retail trade and repair of motor vehicles and 
    "451": "OBC-03",   # Sale of motor vehicles
    "4511": "OBC-03",  # Sale of cars and light motor vehicles
    "4519": "OBC-03",  # Sale of other motor vehicles
    "452": "OBC-03",   # Maintenance and repair of motor vehicles
    "4520": "OBC-03",  # Maintenance and repair of motor vehicles
    "453": "OBC-03",   # Sale of motor vehicle parts and accessories
    "4531": "OBC-03",  # Wholesale trade of motor vehicle parts and accessories
    "4532": "OBC-03",  # Retail trade of motor vehicle parts and accessories
    "454": "OBC-03",   # Sale, maintenance and repair of motorcycles and related part
    "4540": "OBC-03",  # Sale, maintenance and repair of motorcycles and related part
    "46": None,        # Wholesale trade
    "461": None,     # Wholesale on a fee or contract basis
    "4611": "OBC-01",  # Activities of agents involved in the wholesale of agricultur
    "4612": "OBC-01",  # Activities of agents involved in the wholesale of fuels, ore
    "4613": "OBC-01",  # Activities of agents involved in the wholesale of timber and
    "4614": "OBC-01",  # Activities of agents involved in the wholesale of machinery,
    "4615": "OBC-01",  # Activities of agents involved in the wholesale of furniture,
    "4616": "OBC-01",  # Activities of agents involved in the wholesale of textiles, 
    "4617": "OBC-01",  # Activities of agents involved in the wholesale of food, beve
    "4618": "OBC-01",  # Activities of agents involved in the wholesale of other part
    "4619": None,      # Activities of agents involved in non-specialised wholesale
    "462": None,       # Wholesale of agricultural raw materials and live animals
    "4621": "MAT-08",  # Wholesale of grain, unmanufactured tobacco, seeds and animal
    "4622": "MAT-09",  # Wholesale of flowers and plants
    "4623": "MAT-09",  # Wholesale of live animals
    "4624": "MAT-06",  # Wholesale of hides, skins and leather
    "463": "MAT-08",   # Wholesale of food, beverages and tobacco
    "4631": "MAT-08",  # Wholesale of fruit and vegetables
    "4632": "MAT-08",  # Wholesale of meat, meat products, fish and fish products
    "4633": "MAT-08",  # Wholesale of dairy products, eggs and edible oils and fats
    "4634": "MAT-08",  # Wholesale of beverages
    "4635": "MAT-08",  # Wholesale of tobacco products
    "4636": "MAT-08",  # Wholesale of sugar, chocolate and sugar confectionery
    "4637": "MAT-08",  # Wholesale of coffee, tea, cocoa and spices
    "4638": "MAT-08",  # Wholesale of other food
    "4639": "MAT-08",  # Non-specialised wholesale of food, beverages and tobacco
    "464": None,       # Wholesale of household goods
    "4641": "MAT-06",  # Wholesale of textiles
    "4642": "MAT-06",  # Wholesale of clothing and footwear
    "4643": "OBC-01",  # Wholesale of electrical household appliances
    "4644": "OBC-01",  # Wholesale of china and glassware and cleaning materials
    "4645": "OBC-01",  # Wholesale of perfume and cosmetics
    "4646": "ZDR-03",  # Wholesale of pharmaceutical and medical goods
    "4647": "FAC-07",  # Wholesale of household, office and shop furniture, carpets a
    "4648": "OBC-01",  # Wholesale of watches and jewellery
    "4649": "OBC-01",  # Wholesale of other household goods
    "465": None,       # Wholesale of information and communication equipment
    "4650": "ICT-07",  # Wholesale of information and communication equipment
    "4651": "ICT-07",  # Wholesale of computers, computer peripheral equipment and so
    "4652": "MAT-07",  # Wholesale of electronic and telecommunications equipment and
    "466": None,       # Wholesale of other machinery, equipment and supplies
    "4661": "TEC-01",  # Wholesale of agricultural machinery, equipment and supplies
    "4662": "TEC-01",  # Wholesale of machine tools
    "4663": "TEC-01",  # Wholesale of mining, construction and civil engineering mach
    "4664": "TEC-01",  # Wholesale of other machinery and equipment
    "4665": "FAC-07",  # Wholesale of office furniture
    "4666": "FAC-06",  # Wholesale of other office machinery and equipment
    "4669": "TEC-01",  # Wholesale of other machinery and equipment
    "467": None,       # Wholesale of motor vehicles, motorcycles and related parts a
    "4671": "OBC-03",  # Wholesale of motor vehicles
    "4672": "OBC-03",  # Wholesale of motor vehicle parts and accessories
    "4673": "OBC-03",  # Wholesale of motorcycles, motorcycle parts and accessories
    "4674": "MAT-05",  # Wholesale of hardware, plumbing and heating equipment and su
    "4675": "MAT-02",  # Wholesale of chemical products
    "4676": "OBC-01",  # Wholesale of other intermediate products
    "4677": "ODP-01",  # Wholesale of waste and scrap
    "468": None,       # Other specialised wholesale
    "4681": "ENE-03",  # Wholesale of solid, liquid and gaseous fuels and related pro
    "4682": "MAT-01",  # Wholesale of metals and metal ores
    "4683": "MAT-05",  # Wholesale of wood, construction materials and sanitary equip
    "4684": "MAT-05",  # Wholesale of hardware, plumbing and heating equipment and su
    "4685": "MAT-02",  # Wholesale of chemical products
    "4686": "OBC-01",  # Wholesale of other intermediate products
    "4687": "ODP-01",  # Wholesale of waste and scrap
    "4689": "OBC-01",  # Other specialised wholesale n.e.c.
    "469": None,       # Non-specialised wholesale trade
    "4690": None,      # Non-specialised wholesale trade
    "47": None,        # Retail trade
    "471": None,       # Non-specialised retail sale
    "4711": "OBC-02",  # Non-specialised retail sale of predominately food, beverages
    "4712": None,      # Other non-specialised retail sale
    "4719": None,      # Other retail sale in non-specialised stores
    "472": "MAT-08",   # Retail sale of food, beverages and tobacco
    "4721": "MAT-08",  # Retail sale of fruit and vegetables
    "4722": "MAT-08",  # Retail sale of meat and meat products
    "4723": "MAT-08",  # Retail sale of fish, crustaceans and molluscs
    "4724": "MAT-08",  # Retail sale of bread, cake and confectionery
    "4725": "MAT-08",  # Retail sale of beverages
    "4726": "MAT-08",  # Retail sale of tobacco products
    "4727": "MAT-08",  # Retail sale of other food
    "4729": "MAT-08",  # Other retail sale of food in specialised stores
    "473": "ENE-03",   # Retail sale of automotive fuel
    "4730": "ENE-03",  # Retail sale of automotive fuel
    "474": None,       # Retail sale of information and communication equipment
    "4740": "ICT-07",  # Retail sale of information and communication equipment
    "4741": "ICT-07",  # Retail sale of computers, peripheral units and software in s
    "4742": "ICT-07",  # Retail sale of telecommunications equipment in specialised s
    "4743": "OBC-02",  # Retail sale of audio and video equipment in specialised stor
    "475": None,       # Retail sale of other household equipment
    "4751": "MAT-06",  # Retail sale of textiles
    "4752": "MAT-05",  # Retail sale of hardware, building materials, paints and glas
    "4753": "FAC-07",  # Retail sale of carpets, rugs, wall and floor coverings
    "4754": "OBC-02",  # Retail sale of electrical household appliances
    "4755": "FAC-07",  # Retail sale of furniture, lighting equipment, tableware and 
    "4759": "FAC-07",  # Retail sale of furniture, lighting equipment and other house
    "476": "OBC-02",   # Retail sale of cultural and recreational goods
    "4761": "OBC-02",  # Retail sale of books
    "4762": "OBC-02",  # Retail sale of newspapers, and other periodical publications
    "4763": "OBC-02",  # Retail sale of sporting equipment
    "4764": "OBC-02",  # Retail sale of games and toys
    "4765": "OBC-02",  # Retail sale of games and toys in specialised stores
    "4769": "OBC-02",  # Retail sale of cultural and recreational goods n.e.c.
    "477": None,       # Retail sale of other goods, except motor vehicles and motorc
    "4771": "MAT-06",  # Retail sale of clothing
    "4772": "MAT-06",  # Retail sale of footwear and leather goods
    "4773": "ZDR-03",  # Retail sale of pharmaceutical products
    "4774": "ZDR-03",  # Retail sale of medical and orthopaedic goods
    "4775": "OBC-02",  # Retail sale of cosmetic and toilet articles
    "4776": "OBC-02",  # Retail sale of flowers, plants, fertilisers, pets and pet fo
    "4777": "OBC-02",  # Retail sale of watches and jewellery
    "4778": None,      # Retail sale of other new goods
    "4779": "OBC-02",  # Retail sale of second-hand goods
    "478": "OBC-03",   # Retail sale of motor vehicles, motorcycles and related parts
    "4781": "OBC-03",  # Retail sale of motor vehicles
    "4782": "OBC-03",  # Retail sale of motor vehicle parts and accessories
    "4783": "OBC-03",  # Retail sale of motorcycles, motorcycle parts and accessories
    "4789": None,      # Retail sale via stalls and markets of other goods
    "479": None,       # Intermediation service activities for retail sale
    "4791": None,      # Intermediation service activities for non-specialised retail
    "4792": None,      # Intermediation service activities for specialised retail sal
    "4799": None,      # Other retail sale not in stores, stalls or markets

    # --- H  Transportation and storage ---
    "49": "LOG-01",    # Land transport and transport via pipelines
    "491": "LOG-01",   # Passenger rail transport
    "4910": "LOG-01",  # Passenger rail transport, interurban
    "4911": "LOG-01",  # Passenger heavy rail transport
    "4912": "LOG-01",  # Other passenger rail transport
    "492": "LOG-01",   # Freight rail transport
    "4920": "LOG-01",  # Freight rail transport
    "493": "LOG-01",   # Other passenger land transport
    "4931": "LOG-01",  # Scheduled passenger transport by road
    "4932": "LOG-01",  # Non-scheduled passenger transport by road
    "4933": "LOG-01",  # On-demand passenger transport service activities by vehicle 
    "4934": "LOG-01",  # Passenger transport by cableways and ski lifts
    "4939": "LOG-01",  # Other passenger land transport n.e.c.
    "494": "LOG-01",   # Freight transport by road and removal services
    "4941": "LOG-01",  # Freight transport by road
    "4942": "LOG-01",  # Removal services
    "495": "LOG-01",   # Transport via pipeline
    "4950": "LOG-01",  # Transport via pipeline
    "50": "LOG-02",    # Water transport
    "501": "LOG-02",   # Sea and coastal passenger water transport
    "5010": "LOG-02",  # Sea and coastal passenger water transport
    "502": "LOG-02",   # Sea and coastal freight water transport
    "5020": "LOG-02",  # Sea and coastal freight water transport
    "503": "LOG-02",   # Inland passenger water transport
    "5030": "LOG-02",  # Inland passenger water transport
    "504": "LOG-02",   # Inland freight water transport
    "5040": "LOG-02",  # Inland freight water transport
    "51": "LOG-02",    # Air transport
    "511": "LOG-02",   # Passenger air transport
    "5110": "LOG-02",  # Passenger air transport
    "512": "LOG-02",   # Freight air transport and space transport
    "5121": "LOG-02",  # Freight air transport
    "5122": "LOG-02",  # Space transport
    "52": None,        # Warehousing, storage and support activities for transportati
    "521": "LOG-04",   # Warehousing and storage
    "5210": None,    # Warehousing and storage
    "522": "LOG-04",   # Support activities for transportation
    "5221": "LOG-04",  # Service activities incidental to land transportation
    "5222": "LOG-04",  # Service activities incidental to water transportation
    "5223": "LOG-04",  # Service activities incidental to air transportation
    "5224": "LOG-04",  # Cargo handling
    "5225": "LOG-04",  # Logistics service activities
    "5226": "LOG-04",  # Other support activities for transportation
    "5229": "LOG-04",  # Other transportation support activities
    "523": "LOG-03",   # Intermediation service activities for transportation
    "5231": "LOG-03",  # Intermediation service activities for freight transportation
    "5232": "LOG-03",  # Intermediation service activities for passenger transportati
    "53": "LOG-05",    # Postal and courier activities
    "531": "LOG-05",   # Postal activities under universal service obligation
    "5310": "LOG-05",  # Postal activities under universal service obligation
    "532": "LOG-05",   # Other postal and courier activities
    "5320": "LOG-05",  # Other postal and courier activities
    "533": "LOG-05",   # Intermediation service activities for postal and courier act
    "5330": "LOG-05",  # Intermediation service activities for postal and courier act

    # --- I  Accommodation and food service activities ---
    "55": "FAC-08",    # Accommodation
    "551": "FAC-08",   # Hotels and similar accommodation
    "5510": "FAC-08",  # Hotels and similar accommodation
    "552": "FAC-08",   # Holiday and other short-stay accommodation
    "5520": "FAC-08",  # Holiday and other short-stay accommodation
    "553": "FAC-08",   # Camping grounds and recreational vehicle parks
    "5530": "FAC-08",  # Camping grounds and recreational vehicle parks
    "554": "FAC-08",   # Intermediation service activities for accommodation
    "5540": "FAC-08",  # Intermediation service activities for accommodation
    "559": "FAC-08",   # Other accommodation
    "5590": "FAC-08",  # Other accommodation
    "56": "FAC-04",    # Food and beverage service activities
    "561": "FAC-04",   # Restaurants and mobile food service activities
    "5610": "FAC-04",  # Restaurants and mobile food service activities
    "5611": "FAC-04",  # Restaurant activities
    "5612": "FAC-04",  # Mobile food service activities
    "562": "FAC-04",   # Event catering, contract catering service activities and oth
    "5621": "FAC-04",  # Event catering activities
    "5622": "FAC-04",  # Contract catering service activities and other food service 
    "5629": "FAC-04",  # Other food service activities
    "563": "FAC-04",   # Beverage serving activities
    "5630": "FAC-04",  # Beverage serving activities
    "564": "FAC-04",   # Intermediation service activities for food and beverage serv
    "5640": "FAC-04",  # Intermediation service activities for food and beverage serv

    # --- J  Publishing, broadcasting, and content production and distribution activities ---
    "58": None,        # Publishing activities
    "581": "MKT-03",   # Publishing of books, newspapers and other publishing activit
    "5811": "MKT-03",  # Publishing of books
    "5812": "MKT-03",  # Publishing of newspapers
    "5813": "MKT-03",  # Publishing of journals and periodicals
    "5814": "MKT-03",  # Publishing of journals and periodicals
    "5819": "MKT-03",  # Other publishing activities, except software publishing
    "582": "ICT-02",   # Software publishing
    "5821": "ICT-02",  # Publishing of video games
    "5829": "ICT-02",  # Other software publishing
    "59": "MKT-05",    # Motion picture, video and television programme production, s
    "591": "MKT-05",   # Motion picture, video and television programme activities
    "5911": "MKT-05",  # Motion picture, video and television programme production ac
    "5912": "MKT-05",  # Motion picture, video and television programme post-producti
    "5913": "MKT-05",  # Motion picture and video distribution activities
    "5914": "MKT-05",  # Motion picture projection activities
    "592": "MKT-05",   # Sound recording and music publishing activities
    "5920": "MKT-05",  # Sound recording and music publishing activities
    "60": "MKT-05",    # Programming, broadcasting, news agency and other content dis
    "601": "MKT-05",   # Radio broadcasting and audio distribution activities
    "6010": "MKT-05",  # Radio broadcasting and audio distribution activities
    "602": "MKT-05",   # Television programming, broadcasting and video distribution 
    "6020": "MKT-05",  # Television programming, broadcasting and video distribution 
    "603": "MKT-05",   # News agency and other content distribution activities
    "6031": "MKT-05",  # News agency activities
    "6039": "MKT-05",  # Other content distribution activities

    # --- K  Telecommunication, computer programming, consulting, computing infrastructure and other information service activities ---
    "61": "ICT-09",    # Telecommunication
    "611": "ICT-09",   # Wired, wireless, and satellite telecommunication activities
    "6110": "ICT-09",  # Wired, wireless, and satellite telecommunication activities
    "612": "ICT-09",   # Telecommunication reselling activities and intermediation se
    "6120": "ICT-09",  # Telecommunication reselling activities and intermediation se

    # --- J  Publishing, broadcasting, and content production and distribution activities ---
    "613": "ICT-09",   # Satellite telecommunications activities
    "6130": "ICT-09",  # Satellite telecommunications activities

    # --- K  Telecommunication, computer programming, consulting, computing infrastructure and other information service activities ---
    "619": "ICT-09",   # Other telecommunications activities
    "6190": "ICT-09",  # Other telecommunications activities
    "62": None,        # Computer programming, consultancy and related activities

    # --- J  Publishing, broadcasting, and content production and distribution activities ---
    "620": None,       # Computer programming, consultancy and related activities
    "6201": "ICT-01",  # Computer programming activities
    "6202": "ICT-05",  # Computer consultancy activities
    "6203": "ICT-04",  # Computer facilities management activities
    "6209": "ICT-04",  # Other information technology and computer service activities

    # --- K  Telecommunication, computer programming, consulting, computing infrastructure and other information service activities ---
    "621": "ICT-01",   # Computer programming activities
    "6210": "ICT-01",  # Computer programming activities
    "622": None,       # Computer consultancy and computer facilities management acti
    "6220": None,      # Computer consultancy and computer facilities management acti
    "629": "ICT-04",   # Other information technology and computer service activities
    "6290": "ICT-04",  # Other information technology and computer service activities
    "63": None,        # Computing infrastructure, data processing, hosting and other
    "631": None,       # Computing infrastructure, data processing, hosting and relat
    "6310": "ICT-03",  # Computing infrastructure, data processing, hosting and relat

    # --- J  Publishing, broadcasting, and content production and distribution activities ---
    "6311": "ICT-03",  # Data processing, hosting and related activities
    "6312": "ICT-12",  # Web portals

    # --- K  Telecommunication, computer programming, consulting, computing infrastructure and other information service activities ---
    "639": "ICT-12",   # Web search portal activities and other information service a
    "6391": "ICT-12",  # Web search portal activities
    "6392": "ICT-12",  # Other information service activities

    # --- J  Publishing, broadcasting, and content production and distribution activities ---
    "6399": "ICT-12",  # Other information service activities n.e.c.

    # --- L  Financial and insurance activities ---
    "64": None,        # Financial service activities, except insurance and pension f
    "641": "FIN-01",   # Monetary intermediation
    "6411": "FIN-01",  # Central banking
    "6419": "FIN-01",  # Other monetary intermediation
    "642": None,       # Activities of holding companies and financing conduits

    # --- K  Telecommunication, computer programming, consulting, computing infrastructure and other information service activities ---
    "6420": None,      # Activities of holding companies

    # --- L  Financial and insurance activities ---
    "6421": None,      # Activities of holding companies
    "6422": "FIN-05",  # Activities of financing conduits
    "643": "FIN-05",   # Activities of trusts, funds and similar financial entities

    # --- K  Telecommunication, computer programming, consulting, computing infrastructure and other information service activities ---
    "6430": "FIN-05",  # Trusts, funds and similar financial entities

    # --- L  Financial and insurance activities ---
    "6431": "FIN-05",  # Activities of money market and non-money market investments 
    "6432": "FIN-05",  # Activities of trust, estate and agency accounts
    "649": None,       # Other financial service activities, except insurance and pen
    "6491": "FIN-04",  # Financial leasing
    "6492": "FIN-04",  # Other credit granting
    "6499": "FIN-05",  # Other financial service activities, except insurance and pen
    "65": "FIN-03",    # Insurance, reinsurance and pension funding, except compulsor
    "651": "FIN-03",   # Insurance
    "6511": "FIN-03",  # Life insurance
    "6512": "FIN-03",  # Non-life insurance
    "652": "FIN-03",   # Reinsurance
    "6520": "FIN-03",  # Reinsurance
    "653": "FIN-03",   # Pension funding
    "6530": "FIN-03",  # Pension funding
    "66": None,        # Activities auxiliary to financial services and insurance act
    "661": "FIN-05",   # Activities auxiliary to financial services, except insurance
    "6611": "FIN-05",  # Administration of financial markets
    "6612": "FIN-05",  # Security and commodity contracts brokerage
    "6619": "FIN-05",  # Other activities auxiliary to financial services, except ins
    "662": "FIN-03",   # Activities auxiliary to insurance and pension funding
    "6621": "FIN-03",  # Risk and damage evaluation
    "6622": "FIN-03",  # Activities of insurance agents and brokers
    "6629": "FIN-03",  # Activities auxiliary to insurance and pension funding n.e.c.
    "663": "FIN-05",   # Fund management activities
    "6630": "FIN-05",  # Fund management activities

    # --- M  Real estate activities ---
    "68": None,        # Real estate activities
    "681": None,       # Real estate activities with own property and development of

    # --- L  Financial and insurance activities ---
    "6810": None,      # Buying and selling of own real estate

    # --- M  Real estate activities ---
    "6811": None,      # Buying and selling of own real estate
    "6812": "STA-01",  # Development of building projects
    "682": None,       # Rental and operating of own or leased real estate
    "6820": None,      # Rental and operating of own or leased real estate

    # --- ?  kody mimo nomenklaturu / narodni ---
    "68200": None,     # 

    # --- M  Real estate activities ---
    "683": None,       # Real estate activities on a fee or contract basis
    "6831": "FAC-05",  # Intermediation service activities for real estate activities
    "6832": "FAC-02",  # Other real estate activities on a fee or contract basis

    # --- N  Professional, scientific and technical activities ---
    "69": None,        # Legal and accounting activities
    "691": "PRO-01",   # Legal activities
    "6910": "PRO-01",  # Legal activities
    "692": "PRO-02",   # Accounting, bookkeeping and auditing activities; tax consult
    "6920": "PRO-02",  # Accounting, bookkeeping and auditing activities; tax consult
    "70": None,        # Activities of head offices and management consultancy
    "701": None,       # Activities of head offices
    "7010": None,      # Activities of head offices
    "702": None,       # Business and other management consultancy activities
    "7020": None,    # Business and other management consultancy activities

    # --- M  Real estate activities ---
    "7021": "MKT-01",  # Public relations and communication activities
    "7022": "PRO-04",  # Business and other management consultancy activities

    # --- N  Professional, scientific and technical activities ---
    "71": None,        # Architectural and engineering activities; technical testing 
    "711": "PRO-05",   # Architectural and engineering activities and related technic
    "7111": "PRO-05",  # Architectural activities
    "7112": "PRO-05",  # Engineering activities and related technical consultancy
    "712": "PRO-06",   # Technical testing and analysis
    "7120": "PRO-06",  # Technical testing and analysis
    "72": "PRO-07",    # Scientific research and development
    "721": "PRO-07",   # Research and experimental development on natural sciences an
    "7210": "PRO-07",  # Research and experimental development on natural sciences an

    # --- M  Real estate activities ---
    "7211": "PRO-07",  # Research and experimental development on biotechnology
    "7219": "PRO-07",  # Other research and experimental development on natural scien

    # --- N  Professional, scientific and technical activities ---
    "722": "PRO-07",   # Research and experimental development on social sciences and
    "7220": "PRO-07",  # Research and experimental development on social sciences and
    "73": None,        # Activities of advertising, market research and public relati
    "731": "MKT-01",   # Advertising
    "7311": "MKT-01",  # Activities of advertising agencies
    "7312": "MKT-01",  # Media representation
    "732": "MKT-02",   # Market research and public opinion polling
    "7320": "MKT-02",  # Market research and public opinion polling
    "733": "MKT-01",   # Public relations and communication activities
    "7330": "MKT-01",  # Public relations and communication activities
    "74": None,        # Other professional, scientific and technical activities
    "741": None,       # Specialised design activities

    # --- M  Real estate activities ---
    "7410": "PRO-09",  # Specialised design activities

    # --- N  Professional, scientific and technical activities ---
    "7411": "PRO-09",  # Industrial product and fashion design activities
    "7412": "MKT-01",  # Graphic design and visual communication activities
    "7413": "FAC-07",  # Interior design activities
    "7414": "PRO-09",  # Other specialised design activities
    "742": "MKT-05",   # Photographic activities
    "7420": "MKT-05",  # Photographic activities
    "743": "PRO-08",   # Translation and interpretation activities
    "7430": "PRO-08",  # Translation and interpretation activities
    "749": None,       # Other professional, scientific and technical activities n.e.

    # --- M  Real estate activities ---
    "7490": None,      # Other professional, scientific and technical activities n.e.

    # --- N  Professional, scientific and technical activities ---
    "7491": "PRO-01",  # Patent brokering and marketing service activities
    "7499": None,      # All other professional, scientific and technical activities 
    "75": "ZDR-05",    # Veterinary activities
    "750": "ZDR-05",   # Veterinary activities
    "7500": "ZDR-05",  # Veterinary activities

    # --- O  Administrative and support service activities ---
    "77": None,        # Rental and leasing activities
    "771": "TEC-06",   # Rental and leasing of motor vehicles
    "7711": "TEC-06",  # Rental and leasing of cars and light motor vehicles
    "7712": "TEC-06",  # Rental and leasing of trucks
    "772": "TEC-06",   # Rental and leasing of personal and household goods
    "7721": "TEC-06",  # Rental and leasing of recreational and sports goods
    "7722": "TEC-06",  # Rental and leasing of other personal and household goods

    # --- N  Professional, scientific and technical activities ---
    "7729": "TEC-06",  # Renting and leasing of other personal and household goods

    # --- O  Administrative and support service activities ---
    "773": None,       # Rental and leasing of other machinery, equipment and tangibl
    "7731": "TEC-06",  # Rental and leasing of agricultural machinery and equipment
    "7732": "TEC-06",  # Rental and leasing of construction and civil engineering mac
    "7733": "ICT-07",  # Rental and leasing of office machinery, equipment and comput
    "7734": "TEC-06",  # Rental and leasing of water transport equipment
    "7735": "TEC-06",  # Rental and leasing of air transport equipment
    "7739": "TEC-06",  # Rental and leasing of other machinery, equipment and tangibl
    "774": "FIN-05",   # Leasing of intellectual property and similar products, excep
    "7740": "FIN-05",  # Leasing of intellectual property and similar products, excep
    "775": "TEC-06",   # Intermediation service activities for rental and leasing of 
    "7751": "TEC-06",  # Intermediation service activities for rental and leasing of 
    "7752": "TEC-06",  # Intermediation service activities for rental and leasing of 
    "78": None,        # Employment activities
    "781": "HR-01",    # Activities of employment placement agencies
    "7810": "HR-01",   # Activities of employment placement agencies
    "782": "HR-02",    # Temporary employment agency activities and other human resou
    "7820": "HR-02",   # Temporary employment agency activities and other human resou

    # --- N  Professional, scientific and technical activities ---
    "783": "HR-02",    # Other human resources provision
    "7830": "HR-02",   # Other human resources provision

    # --- O  Administrative and support service activities ---
    "79": "FAC-08",    # Travel agency, tour operator and other reservation service a
    "791": "FAC-08",   # Travel agency and tour operator activities
    "7911": "FAC-08",  # Travel agency activities
    "7912": "FAC-08",  # Tour operator activities
    "799": "FAC-08",   # Other reservation service and related activities
    "7990": "FAC-08",  # Other reservation service and related activities
    "80": None,        # Investigation and security activities
    "800": None,       # Investigation and security activities
    "8001": "SEC-01",  # Investigation and private security activities
    "8009": "SEC-02",  # Security activities n.e.c.

    # --- N  Professional, scientific and technical activities ---
    "801": "SEC-01",   # Private security activities
    "8010": "SEC-01",  # Private security activities
    "802": "SEC-02",   # Security systems service activities
    "8020": "SEC-02",  # Security systems service activities
    "803": "SEC-01",   # Investigation activities
    "8030": "SEC-01",  # Investigation activities

    # --- O  Administrative and support service activities ---
    "81": None,        # Services to buildings and landscape activities
    "811": "FAC-02",   # Combined facilities support activities
    "8110": "FAC-02",  # Combined facilities support activities
    "812": "FAC-01",   # Cleaning activities
    "8121": "FAC-01",  # General cleaning of buildings
    "8122": "FAC-01",  # Other building and industrial cleaning activities
    "8123": "FAC-01",  # Other cleaning activities

    # --- N  Professional, scientific and technical activities ---
    "8129": "FAC-01",  # Other cleaning activities

    # --- O  Administrative and support service activities ---
    "813": "FAC-03",   # Landscape service activities
    "8130": "FAC-03",  # Landscape service activities
    "82": None,        # Office administrative, office support and other business sup
    "821": None,       # Office administrative and support activities
    "8210": None,      # Office administrative and support activities

    # --- N  Professional, scientific and technical activities ---
    "8211": None,      # Combined office administrative service activities
    "8219": "MKT-03",  # Photocopying, document preparation and other specialised off

    # --- O  Administrative and support service activities ---
    "822": "ICT-10",   # Activities of call centres
    "8220": "ICT-10",  # Activities of call centres
    "823": "MKT-04",   # Organisation of conventions and trade shows
    "8230": "MKT-04",  # Organisation of conventions and trade shows
    "824": None,       # Intermediation service activities for business support servi
    "8240": None,      # Intermediation service activities for business support servi
    "829": None,       # Business support service activities n.e.c.
    "8291": "FIN-06",  # Activities of collection agencies and credit bureaus
    "8292": "MAT-04",  # Packaging activities
    "8299": None,      # Other business support service activities n.e.c.

    # --- P  Public administration and defence; compulsory social security ---
    "84": "VER-01",    # Public administration and defence; compulsory social securit
    "841": "VER-01",   # Administration of the State and the economic, social and env
    "8411": "VER-01",  # General public administration activities
    "8412": "VER-01",  # Regulation of health care, education, cultural services and 
    "8413": "VER-01",  # Regulation of and contribution to more efficient operation o
    "842": "VER-01",   # Provision of services to the community as a whole
    "8421": "VER-01",  # Foreign affairs
    "8422": "VER-01",  # Defence activities
    "8423": "VER-01",  # Justice and judicial activities
    "8424": "VER-01",  # Public order and safety activities
    "8425": "VER-01",  # Fire service activities
    "843": "VER-01",   # Compulsory social security activities
    "8430": "VER-01",  # Compulsory social security activities

    # --- Q  Education ---
    "85": None,        # Education
    "851": "VER-03",   # Pre-primary education
    "8510": "VER-03",  # Pre-primary education
    "852": "VER-03",   # Primary education
    "8520": "VER-03",  # Primary education
    "853": "VER-03",   # Secondary and post-secondary non-tertiary education
    "8531": "VER-03",  # General secondary education
    "8532": "VER-03",  # Vocational secondary education
    "8533": "VER-03",  # Post-secondary non-tertiary education
    "854": "VER-03",   # Tertiary education
    "8540": "VER-03",  # Tertiary education

    # --- P  Public administration and defence; compulsory social security ---
    "8541": "VER-03",  # Post-secondary non-tertiary education
    "8542": "VER-03",  # Tertiary education

    # --- Q  Education ---
    "855": "HR-04",    # Other education
    "8551": "HR-04",   # Sports and recreation education
    "8552": "HR-04",   # Cultural education
    "8553": "HR-04",   # Driving school activities
    "8559": "HR-04",   # Other education n.e.c.
    "856": "HR-04",    # Educational support activities

    # --- P  Public administration and defence; compulsory social security ---
    "8560": "HR-04",   # Educational support activities

    # --- Q  Education ---
    "8561": "HR-04",   # Intermediation service activities for courses and tutors
    "8569": "HR-04",   # Educational support activities n.e.c.

    # --- R  Human health and social work activities ---
    "86": None,        # Human health activities
    "861": "ZDR-01",   # Hospital activities
    "8610": "ZDR-01",  # Hospital activities
    "862": "ZDR-01",   # Medical and dental practice activities
    "8621": "ZDR-01",  # General medical practice activities
    "8622": "ZDR-01",  # Medical specialists activities
    "8623": "ZDR-01",  # Dental practice care activities
    "869": None,       # Other human health activities

    # --- Q  Education ---
    "8690": "ZDR-01",  # Other human health activities

    # --- R  Human health and social work activities ---
    "8691": "ZDR-02",  # Diagnostic imaging services and medical laboratory activitie
    "8692": "ZDR-01",  # Patient transportation by ambulance
    "8693": "ZDR-01",  # Activities of psychologists and psychotherapists, except med
    "8694": "ZDR-01",  # Nursing and midwifery activities
    "8695": "ZDR-01",  # Physiotherapy activities
    "8696": "ZDR-01",  # Traditional, complementary and alternative medicine activiti
    "8697": "ZDR-01",  # Intermediation service activities for medical, dental and ot
    "8699": "ZDR-01",  # Other human health activities n.e.c.
    "87": "ZDR-04",    # Residential care activities
    "871": "ZDR-04",   # Residential nursing care activities
    "8710": "ZDR-04",  # Residential nursing care activities
    "872": "ZDR-04",   # Residential care activities for persons living with or havin
    "8720": "ZDR-04",  # Residential care activities for persons living with or havin
    "873": "ZDR-04",   # Residential care activities for older persons or persons wit
    "8730": "ZDR-04",  # Residential care activities for older persons or persons wit
    "879": "ZDR-04",   # Other residential care activities

    # --- Q  Education ---
    "8790": "ZDR-04",  # Other residential care activities

    # --- R  Human health and social work activities ---
    "8791": "ZDR-04",  # Intermediation service activities for residential care activ
    "8799": "ZDR-04",  # Other residential care activities n.e.c.
    "88": "ZDR-04",    # Social work activities without accommodation
    "881": "ZDR-04",   # Social work activities without accommodation for older perso
    "8810": "ZDR-04",  # Social work activities without accommodation for older perso
    "889": "ZDR-04",   # Other social work activities without accommodation
    "8891": "ZDR-04",  # Child day-care activities
    "8899": "ZDR-04",  # Other social work activities without accommodation n.e.c.

    # --- S  Arts, sports and recreation ---
    "90": "OST-01",    # Arts creation and performing arts activities

    # --- R  Human health and social work activities ---
    "900": "OST-01",   # Creative, arts and entertainment activities
    "9001": "OST-01",  # Performing arts
    "9002": "OST-01",  # Support activities to performing arts
    "9003": "OST-01",  # Artistic creation
    "9004": "OST-01",  # Operation of arts facilities

    # --- S  Arts, sports and recreation ---
    "901": "OST-01",   # Arts creation activities
    "9011": "OST-01",  # Literary creation and musical composition activities
    "9012": "OST-01",  # Visual arts creation activities
    "9013": "OST-01",  # Other arts creation activities
    "902": "OST-01",   # Activities of performing arts
    "9020": "OST-01",  # Activities of performing arts
    "903": "OST-01",   # Support activities to arts creation and performing arts
    "9031": "OST-01",  # Operation of arts facilities and sites
    "9039": "OST-01",  # Other support activities to arts and performing arts
    "91": "OST-01",    # Libraries, archives, museums and other cultural activities

    # --- R  Human health and social work activities ---
    "910": "OST-01",   # Libraries, archives, museums and other cultural activities
    "9101": "OST-01",  # Library and archives activities
    "9102": "OST-01",  # Museums activities
    "9103": "OST-01",  # Operation of historical sites and buildings and similar visi
    "9104": "OST-01",  # Botanical and zoological gardens and nature reserves activit

    # --- S  Arts, sports and recreation ---
    "911": "OST-01",   # Library and archive activities
    "9111": "OST-01",  # Library activities
    "9112": "OST-01",  # Archive activities
    "912": "OST-01",   # Museum, collection, historical site and monument activities
    "9121": "OST-01",  # Museum and collection activities
    "9122": "OST-01",  # Historical site and monument activities
    "913": "OST-01",   # Conservation, restoration and other support activities for c
    "9130": "OST-01",  # Conservation, restoration and other support activities for c
    "914": "OST-01",   # Botanical and zoological garden and nature reserve activitie
    "9141": "OST-01",  # Botanical and zoological garden activities
    "9142": "OST-01",  # Nature reserve activities
    "92": "OST-01",    # Gambling and betting activities
    "920": "OST-01",   # Gambling and betting activities
    "9200": "OST-01",  # Gambling and betting activities
    "93": "OST-01",    # Sports activities and amusement and recreation activities
    "931": "OST-01",   # Sports activities
    "9311": "OST-01",  # Operation of sports facilities
    "9312": "OST-01",  # Activities of sport clubs
    "9313": "OST-01",  # Activities of fitness centres
    "9319": "OST-01",  # Sports activities n.e.c.
    "932": "OST-01",   # Amusement and recreation activities
    "9321": "OST-01",  # Activities of amusement parks and theme parks
    "9329": "OST-01",  # Amusement and recreation activities n.e.c.

    # --- T  Other service activities ---
    "94": "VER-02",    # Activities of membership organisations
    "941": "VER-02",   # Activities of business, employers and professional membershi
    "9411": "VER-02",  # Activities of business and employers membership organisation
    "9412": "VER-02",  # Activities of professional membership organisations
    "942": "VER-02",   # Activities of trade unions
    "9420": "VER-02",  # Activities of trade unions
    "949": "VER-02",   # Activities of other membership organisations
    "9491": "VER-02",  # Activities of religious organisations
    "9492": "VER-02",  # Activities of political organisations
    "9499": "VER-02",  # Activities of other membership organisations n.e.c.
    "95": None,        # Repair and maintenance of computers, personal and household 
    "951": "ICT-11",   # Repair and maintenance of computers and communication equipm
    "9510": "ICT-11",  # Repair and maintenance of computers and communication equipm

    # --- S  Arts, sports and recreation ---
    "9511": "ICT-11",  # Repair of computers and peripheral equipment
    "9512": "ICT-11",  # Repair of communication equipment

    # --- T  Other service activities ---
    "952": None,       # Repair and maintenance of personal and household goods
    "9521": "ICT-11",  # Repair and maintenance of consumer electronics
    "9522": "OST-02",  # Repair and maintenance of household appliances and home and 
    "9523": "OST-02",  # Repair and maintenance of footwear and leather goods
    "9524": "OST-02",  # Repair and maintenance of furniture and home furnishings
    "9525": "OST-02",  # Repair and maintenance of watches, clocks and jewellery
    "9529": "OST-02",  # Repair and maintenance of personal and household goods n.e.c
    "953": "OBC-03",   # Repair and maintenance of motor vehicles and motorcycles
    "9531": "OBC-03",  # Repair and maintenance of motor vehicles
    "9532": "OBC-03",  # Repair and maintenance of motorcycles
    "954": "OST-02",   # Intermediation service activities for repair and maintenance
    "9540": "OST-02",  # Intermediation service activities for repair and maintenance
    "96": "OST-02",    # Personal service activities

    # --- S  Arts, sports and recreation ---
    "960": "OST-02",   # Other personal service activities
    "9601": "OST-02",  # Washing and (dry-)cleaning of textile and fur products
    "9602": "OST-02",  # Hairdressing and other beauty treatment
    "9603": "OST-02",  # Funeral and related activities
    "9604": "OST-02",  # Physical well-being activities
    "9609": "OST-02",  # Other personal service activities n.e.c.

    # --- T  Other service activities ---
    "961": "OST-02",   # Washing and cleaning of textile and fur products
    "9610": "OST-02",  # Washing and cleaning of textile and fur products
    "962": "OST-02",   # Hairdressing, beauty treatment, day spa and similar activiti
    "9621": "OST-02",  # Hairdressing and barber activities
    "9622": "OST-02",  # Beauty care and other beauty treatment activities
    "9623": "OST-02",  # Day spa, sauna and steam bath activities
    "963": "OST-02",   # Funeral and related activities
    "9630": "OST-02",  # Funeral and related activities
    "964": "OST-02",   # Intermediation service activities for personal services
    "9640": "OST-02",  # Intermediation service activities for personal services
    "969": "OST-02",   # Other personal service activities
    "9691": "OST-02",  # Provision of domestic personal service activities
    "9699": "OST-02",  # Other personal service activities n.e.c.

    # --- U  Activities of households as employers and undifferentiated goods- and service-producing activities of households for own use ---
    "97": None,        # Activities of households as employers of domestic personnel
    "970": None,       # Activities of households as employers of domestic personnel
    "9700": None,      # Activities of households as employers of domestic personnel
    "98": None,        # Undifferentiated goods- and service-producing activities of 
    "981": None,       # Undifferentiated goods-producing activities of private house
    "9810": None,      # Undifferentiated goods-producing activities of private house
    "982": None,       # Undifferentiated service-producing activities of private hou
    "9820": None,      # Undifferentiated service-producing activities of private hou
    "99": "VER-02",    # Activities of extraterritorial organisations and bodies
    "990": "VER-02",   # Activities of extraterritorial organisations and bodies
    "9900": "VER-02",  # Activities of extraterritorial organisations and bodies

    # --- ?  kody mimo nomenklaturu / narodni ---
    "99999": None,     # 
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
    """
    Vrati hodnotu pro nejdelsi prefix kodu, ktery je v mape. Pouziva se uz jen
    pro prevodniky US SIC (SIC_NA_NACE, SIC_NA_NAICS), kde jsou klice na urovni
    odvetvi a prefixove hledani je tam na miste - zarazeni dodavatele se timhle
    zpusobem uz nedela, o tom rozhoduje kategorie_kodu() nad NACE_KATEGORIE.
    """
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
    """Uredni nazev cinnosti z nomenklatury (anglicky, viz nace_nomenklatura)."""
    return nace_nomenklatura.nazev(kod)


def kategorie_kodu(kod, mapa=None):
    """
    Kategorie pro NACE kod, nebo None kdyz kod kategorii neurcuje.

    Prochazi se od nejdelsiho prefixu kvuli narodnim kodum s cislici navic -
    britska UK SIC "62012" i nemecka WZ "62.01.0" vedou na tridu "6210".
    """
    mapa = mapa if mapa is not None else NACE_KATEGORIE
    cislice = "".join(ch for ch in str(kod or "") if ch.isdigit())
    for delka in range(len(cislice), 1, -1):
        if cislice[:delka] in mapa:
            return mapa[cislice[:delka]]
    return None


def zarad(kody=None, obory=None, nace=None, mapa=None, kategorie=None, mapa_oboru=None):
    """
    Zaradi dodavatele do vlastni taxonomie. Kategorii priradi, jen kdyz je
    jista - jinak vrati XXX-00 a skutecnou cinnost dohleda krok --export-llm.

    Pravidlo je jedno jedine:

        KAZDY zapsany obor firmy musi urcovat kategorii a vsechny musi vest
        na tutez. Staci jeden obor, ktery kategorii neurcuje nebo ukazuje
        jinam, a zaznam jde k overeni.

    Neurcujici obor tedy zaznam NEDISKVALIFIKUJE jen sam za sebe - bere se jako
    znamka, ze zapis firmy je "ozdobny" (kody nabrane pri zalozeni pro jistotu),
    a pak nejde verit ani tem konkretnim. Merenim to sedi: na 25 rucne overenych
    firmach toto pravidlo odchytilo VSECH 9 pripadu, kde zapsany kod neodpovidal
    skutecne cinnosti (hudebni klub zapsany jako destilace lihovin, truhlarstvi
    jako vystavba budov, penzion jako restaurace).

    Firma nema jeden hlavni obor - ma jich zapsanych vic (Asseco Central Europe
    23, CEZ 36) a rejstriky mezi nimi nerozlisuji. Prevazujici cinnost z ceskeho
    RES je proto jen dalsi kod v mnozine, ne autorita: merenim se ukazalo, ze
    i ona casto neodpovida tomu, co firma opravdu dela (viz DOCS.md).

    Kdyz zadny zapsany obor kategorii neurci, zkusi se jeste obor cinnosti
    z Wikidat (QID) - mapa oboru je psana po jednom QID, takze je to tvrzeni
    o oboru firmy, ne dopocet z odvetvi.

    Kategorie se NEHADA z nazvu firmy: shoda slova v nazvu neni fakt o oboru
    cinnosti a muze byt vylozene mylna (napr. "Deutsche Akkreditierungsstelle"
    nema nic spolecneho s uverem, i kdyz "kredit" jako podretezec sedi).

    Argumenty:
        kody  - vsechny zapsane NACE kody firmy
        obory - QID oboru cinnosti z Wikidat
        nace  - zkratka pro jediny kod (kody=[nace])

    Vrati dict: kod, kategorie, skupina, zdroj ('nace' | 'obor' | 'vychozi'),
    nace (odhad NACE z oboru, pokud zadny NACE na vstupu nebyl).
    """
    mapa = mapa if mapa is not None else NACE_KATEGORIE
    kategorie = kategorie if kategorie is not None else KATEGORIE
    kody = list(kody or ([nace] if nace else []))

    kod, zdroj, nace_odhad = None, "vychozi", ""

    nalezene = {kategorie_kodu(c, mapa) for c in kody}
    if kody and len(nalezene) == 1 and None not in nalezene:
        kod, zdroj = nalezene.pop(), "nace"

    if not kod and obory:
        kod, nace_odhad = obor_na_kategorii(obory, mapa_oboru)
        if kod:
            zdroj = "obor"

    if not kod:
        kod = VYCHOZI_KOD

    skupina, nazev_kat = kategorie.get(kod, kategorie[VYCHOZI_KOD])
    return {"kod": kod, "kategorie": nazev_kat, "skupina": skupina,
            "zdroj": zdroj, "nace": nace_odhad}


def nedosazitelne_kategorie(mapa=None, kategorie=None):
    """
    Kategorie, na ktere nevede zadny NACE kod - tedy ty, ktere se pres NACE
    vyjadrit nedaji, at uz je kod jakkoli spravny.

    Mnozina se ODVOZUJE z tabulky, nevypisuje se rucne: kdyz nejaky kod dostane
    kategorii nebo se prida nova kategorie, odpoved se zmeni sama (plati i pro
    vlastni taxonomii nactenou pres --taxonomie).

    Vznikaji proto, ze nase taxonomie je misty jemnejsi nez NACE: 6920 je
    "Accounting, bookkeeping and auditing activities" - jeden kod pro nase
    PRO-02 i PRO-03, vest muze jen na jednu z nich. Pro kyberbezpecnost, payroll
    nebo skartaci nosicu dat NACE zvlastni kod vubec nema.

    Prave u techto kategorii ma smysl vzit primy navrh kategorie od LLM misto
    kategorie z NACE - viz pouzij_llm_mapu() v dodavatele.py.
    """
    mapa = mapa if mapa is not None else NACE_KATEGORIE
    kategorie = kategorie if kategorie is not None else KATEGORIE
    dosazitelne = {k for k in mapa.values() if k}
    return {k for k in kategorie if k not in dosazitelne and k != VYCHOZI_KOD}


def prehled_kategorii():
    """Serazeny seznam (kod, skupina, nazev) - pro ciselnik ve vystupu."""
    return sorted(((k, v[0], v[1]) for k, v in KATEGORIE.items()))


def chybejici_kody(mapa=None):
    """
    Kody z nomenklatury, ktere v tabulce nejsou. Tabulka ma byt UPLNA, takze
    neprazdny vysledek je defekt, ne varianta chovani.
    """
    mapa = mapa if mapa is not None else NACE_KATEGORIE
    return sorted(k for k in nace_nomenklatura.NACE if k not in mapa)


def pokryti(mapa=None):
    """Kolik kodu kategorii urcuje a kolik ne, + kolik jich v tabulce chybi."""
    mapa = mapa if mapa is not None else NACE_KATEGORIE
    urcuje = sum(1 for k in mapa.values() if k)
    return {"urcuje": urcuje, "neurcuje": len(mapa) - urcuje,
            "chybi": len(chybejici_kody(mapa))}


def prehled_nace(mapa=None):
    """
    Cela nomenklatura NACE pro list ve vystupu: seznam
    (kod, uroven, nazev, sekce, revize, kategorie). Prazdna kategorie znamena,
    ze kod o predmetu dodavky nerika nic pouzitelneho.
    """
    mapa = mapa if mapa is not None else NACE_KATEGORIE
    return [(kod, nace_nomenklatura.uroven(kod), nazev,
             "%s - %s" % (sekce, nace_nomenklatura.SEKCE.get(sekce, "")),
             revize, mapa.get(kod) or "")
            for kod, nazev, sekce, revize in nace_nomenklatura.vsechny()]


def jako_json():
    return {
        "kategorie": {k: list(v) for k, v in KATEGORIE.items()},
        "nace_kategorie": NACE_KATEGORIE,
        "vychozi_kod": VYCHOZI_KOD,
        "sic_na_nace": SIC_NA_NACE,
        "sic_na_naics": SIC_NA_NAICS,
        "wikidata_obory": {k: list(v) for k, v in WIKIDATA_OBORY.items()},
    }


def z_json(data):
    """Vrati (mapa NACE, kategorie, mapa_oboru) z JSON podoby taxonomie."""
    kat = {k: tuple(v) for k, v in data.get("kategorie", {}).items()} or KATEGORIE
    mapa = data.get("nace_kategorie") or NACE_KATEGORIE
    oboru = ({k: tuple(v) for k, v in data.get("wikidata_obory", {}).items()}
             or WIKIDATA_OBORY)
    return mapa, kat, oboru

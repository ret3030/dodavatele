"""
Nezavisly modul: deterministicke zarazeni dodavatele do kategorie z ciselniku
na zaklade verejnych rejstriku (ARES, Wikidata, Wikipedie) a webu firmy,
vyhodnocene listem namapovanych klicovych slov.

Cil: obejit rucni LLM krok u firem, kde je obor jednoznacny. Nejasne pripady
skonci jako "LLM" (nezarazeno) k doreseni puvodni cestou. Zadny API klic,
zadna behova sluzba, cisty Python - bezi i na Windows bez WSL. Prvni beh
stahuje, kazdy dalsi jede z kese a je deterministicky.

Neni napojen na dodavatele.py - sdili s nim jen cteni taxonomie_data.json.
"""

__all__ = ["klasifikator", "zdroje", "pravidla", "normalizace", "taxonomie", "vstup"]

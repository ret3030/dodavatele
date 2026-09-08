"""
Nezavisly modul: deterministicke zarazeni dodavatele do kategorie z ciselniku
na zaklade weboveho vyhledavani (vlastni instance SearXNG) a listu namapovanych
klicovych slov.

Cil: obejit rucni LLM krok u firem, kde je obor jednoznacny. Nejasne pripady
skonci jako "LLM" (nezarazeno) k doreseni puvodni cestou. Hledani jde pres
vlastni SearXNG - nazvy dodavatelu neopousteji vlastni infrastrukturu.

Neni napojen na dodavatele.py - sdili s nim jen cteni taxonomie_data.json.
"""

__all__ = ["klasifikator", "searxng", "pravidla", "normalizace", "taxonomie", "vstup"]

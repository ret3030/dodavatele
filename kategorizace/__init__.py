"""
Nezavisly modul: deterministicke zarazeni dodavatele do kategorie z ciselniku
na zaklade Google vyhledavani (SERPER API) a listu namapovanych klicovych slov.

Cil: obejit rucni LLM krok u firem, kde je obor jednoznacny. Nejasne pripady
skonci jako "LLM" (nezarazeno) k dorešení puvodni cestou.

Neni napojen na dodavatele.py - sdili s nim jen cteni taxonomie_data.json.
"""

__all__ = ["klasifikator", "serper", "pravidla", "normalizace", "taxonomie", "vstup"]

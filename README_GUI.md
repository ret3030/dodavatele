# Desktopová appka pro kolegy (bez Pythonu)

Tenká GUI nadstavba (`gui.py`) nad stejnou logikou jako `dodavatele.py` -
pro kolegy, kteří nechtějí/neumí pracovat s příkazovou řádkou. Zabaluje se
do jednoho spustitelného souboru (PyInstaller), takže kolega jen dvojklikem
spustí `.exe`/`.app` - Python ani žádné knihovny instalovat nemusí.

Vytvořil: Robert Plevač (robert.plevac@cz.ey.com), EY s.r.o., IČO 26705338.

## Jak appku dostat hotovou (bez buildování)

**Stálý odkaz ke stažení (doporučeno pro kolegy):**
https://github.com/ret3030/dodavatele/releases/tag/gui-latest

Vždy obsahuje poslední úspěšně sestavenou verzi z branche `gui-desktop`
(`Dodavatele.exe` pro Windows, `Dodavatele-macOS.zip` pro macOS) - stažení
funguje **bez přihlášení do GitHub účtu** a odkaz se při dalších verzích
nemění. Aktualizuje se automaticky při každé změně `gui.py`/`dodavatele.py`
na této branchi.

Alternativa (vyžaduje přihlášený GitHub účet): záložka **Actions** →
workflow **Build desktop GUI** → poslední úspěšný běh → sekce **Artifacts**
dole. Na rozdíl od Release tyhle soubory po čase automaticky mizí a ke
stažení je nutné být přihlášený - pro rozesílání kolegům použijte raději
odkaz na Release výše.

Na macOS je potřeba po rozbalení zipu appku poprvé spustit přes pravé
tlačítko → Otevřít (Gatekeeper jinak nepodepsanou appku odmítne spustit
dvojklikem).

## Jak appku sestavit sám (lokálně)

Vyžaduje Python 3.9+ (stejně jako CLI nástroj):

```bash
pip install pyinstaller openpyxl

# Windows - jeden .exe
pyinstaller --onefile --windowed --name Dodavatele gui.py

# macOS - .app balíček
pyinstaller --windowed --name Dodavatele gui.py
```

Výsledek je v `dist/`. PyInstaller neumí sestavit appku pro jinou platformu,
než na které zrovna běží (Windows appku nelze sestavit na macOS a naopak) -
proto GitHub Actions workflow běží zvlášť na `windows-latest` a
`macos-latest`.

## Co appka umí a co ne

Stejná logika jako CLI (`dodavatele.py spustit()`), jen s okny místo
přepínačů:

* výběr vstupního/výstupního souboru,
* zapnutí/vypnutí jednotlivých zdrojů (odpovídá `--bez-*`),
* volitelné API klíče pro OpenRegister.de a Scoris,
* tlačítka na přípravu místních databází (Německo/UK) - jde o desítky
  minut a gigabajty stažených dat, appka jen spustí totéž, co
  `--pripravit-de-rejstrik`/`--pripravit-gb-rejstrik` na CLI,
* průběžný log a souhrn po doběhnutí.

Pokročilé přepínače (`--workers`, `--pocet`, `--prah-ok`, `--taxonomy`,
`--komparace`, `--export-nezarazene`, `--obnovit-nenalezene`...) appka
zatím nenabízí - na to pořád slouží CLI, viz [DOCS.md](DOCS.md). Appka je
zamýšlená jako rychlá cesta pro běžné použití, ne náhrada CLI pro
pokročilé scénáře.

## Bezpečnost API klíčů

Klíče zadané v appce se nikam neukládají (ani do souboru, ani do keše) -
platí přesně stejné pravidlo jako pro CLI (viz DOCS.md), jen se zadávají
do textového pole místo parametru příkazové řádky.

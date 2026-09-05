"""
Jednoduche desktopove GUI k dodavatele.py pro kolegy, kteri neumi s Pythonem/
prikazovou radkou. Zabaluje se do jednoho spustitelneho souboru pres
PyInstaller (viz build.spec a README_GUI.md) - kolega jen dvojklikem spusti
.exe/.app, nic neinstaluje.

Logika obohaceni je beze zmeny v dodavatele.py (funkce spustit()) - tenhle
soubor je jen tenka nadstavba, ktera si postavi stejny objekt argumentu,
jaky by vznikl z prikazove radky, a spusti beh na pozadi s prubeznym
hlasenim postupu do okna.
"""
from __future__ import annotations

import argparse
import io
import os
import queue
import sys
import threading
import traceback
import webbrowser
from tkinter import (
    BOTH, END, LEFT, X, BooleanVar, StringVar, Tk, ttk,
    filedialog, messagebox, scrolledtext,
)

# PyInstaller s --windowed/--noconsole nastavi sys.stdout/stderr na None -
# dodavatele.py pouziva print(..., file=sys.stderr) pro prubezne hlaseni,
# bez tohohle by prvni print() shodil cely program (AttributeError).
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

import dodavatele as d  # noqa: E402 (musi byt az po oprave sys.stdout/stderr)

NAZEV_OKNA = "Dodavatelé – obohacení seznamu"

ZDROJE = [
    ("Ares", "bez_ares", "ARES (ČR)", True),
    ("Sk", "bez_sk", "RPO SR (Slovensko)", True),
    ("Fr", "bez_fr", "INSEE (Francie)", True),
    ("Sg", "bez_sg", "ACRA (Singapur)", True),
    ("Tw", "bez_tw", "GCIS (Tchaj-wan)", True),
    ("De", "bez_de", "Handelsregister – místní kopie (Německo)", True),
    ("Gb", "bez_gb", "Companies House – místní kopie (UK)", True),
    ("Edgar", "bez_edgar", "SEC EDGAR (USA)", True),
    ("Gleif", "bez_gleif", "GLEIF (svět, firmy s LEI)", True),
    ("Wikidata", "bez_wikidata", "Wikidata (obor u velkých firem)", True),
]


def vychozi_argumenty():
    """
    Stejne vychozi hodnoty jako ma CLI (main() v dodavatele.py). export_overeni/
    export_davka/overeni_mapa jsou zamerne CLI-only funkce (plosne LLM overeni
    kategorie muze prepsat i dosud spravnou kategorii, viz DOCS.md) - GUI pro
    ne nema ovladaci prvky, ale spustit() na tyhle atributy sahaje vzdy, takze
    tu musi byt aspon prazdne/vychozi, jinak by beh z GUI spadl na AttributeError.
    """
    return argparse.Namespace(
        vstup=None, vystup="dodavatele_vystup.xlsx", sloupec=None, oddelovac=";",
        kompakt=False, jen_id=False, export_nezarazene=None, nace_mapa=None,
        export_overeni=None, export_davka=None, overeni_mapa=None,
        workers=4, prodleva=0.25, pocet=30, prah_ok=0.90, prah_overit=0.72,
        vies=False, bez_ares=False, bez_sk=False, bez_fr=False, bez_sg=False,
        bez_tw=False, bez_de=False, de_api_klic="", scoris_api_klic="",
        bez_gb=False, bez_gleif=False, bez_gleif_popisy=False, bez_edgar=False,
        bez_wikidata=False, cache=".dodavatele_cache.json.gz",
        obnovit_nenalezene=None, taxonomy=None, ua=d.UA,
    )


class Aplikace:
    def __init__(self, root):
        self.root = root
        root.title(NAZEV_OKNA)
        root.geometry("720x640")
        root.minsize(640, 560)

        self.fronta = queue.Queue()
        self.bezi = False
        self.cesta_vystup = None

        self.var_vstup = StringVar()
        self.var_vystup = StringVar()
        self.var_vies = BooleanVar(value=False)
        self.var_zdroje = {}
        for klic, _attr, _popis, vychozi in ZDROJE:
            self.var_zdroje[klic] = BooleanVar(value=vychozi)
        self.var_de_klic = StringVar()
        self.var_scoris_klic = StringVar()

        self._sestav_ui()
        self.root.after(150, self._kontroluj_frontu)

    # -- sestaveni okna ----------------------------------------------------

    def _sestav_ui(self):
        pad = {"padx": 10, "pady": 6}

        ramec_soubory = ttk.LabelFrame(self.root, text="Vstup a výstup")
        ramec_soubory.pack(fill=X, **pad)

        radek1 = ttk.Frame(ramec_soubory)
        radek1.pack(fill=X, padx=8, pady=4)
        ttk.Label(radek1, text="Vstupní soubor:", width=16).pack(side=LEFT)
        ttk.Entry(radek1, textvariable=self.var_vstup).pack(side=LEFT, fill=X, expand=True)
        ttk.Button(radek1, text="Vybrat…", command=self._vyber_vstup).pack(side=LEFT, padx=(6, 0))

        radek2 = ttk.Frame(ramec_soubory)
        radek2.pack(fill=X, padx=8, pady=4)
        ttk.Label(radek2, text="Výstupní soubor:", width=16).pack(side=LEFT)
        ttk.Entry(radek2, textvariable=self.var_vystup).pack(side=LEFT, fill=X, expand=True)
        ttk.Button(radek2, text="Uložit jako…", command=self._vyber_vystup).pack(side=LEFT, padx=(6, 0))

        ramec_zdroje = ttk.LabelFrame(self.root, text="Zdroje dat (odškrtněte, co nechcete použít)")
        ramec_zdroje.pack(fill=X, **pad)
        mrizka = ttk.Frame(ramec_zdroje)
        mrizka.pack(fill=X, padx=8, pady=4)
        for i, (klic, _attr, popis, _vychozi) in enumerate(ZDROJE):
            ttk.Checkbutton(mrizka, text=popis, variable=self.var_zdroje[klic]).grid(
                row=i // 2, column=i % 2, sticky="w", padx=4, pady=2)
        ttk.Checkbutton(
            ramec_zdroje, text="Ověřit DIČ v EU přes VIES (o dost pomalejší)",
            variable=self.var_vies,
        ).pack(anchor="w", padx=8, pady=(0, 6))

        ramec_klice = ttk.LabelFrame(
            self.root, text="Volitelné placené API klíče (nechte prázdné, pokud je nemáte)")
        ramec_klice.pack(fill=X, **pad)
        radek3 = ttk.Frame(ramec_klice)
        radek3.pack(fill=X, padx=8, pady=4)
        ttk.Label(radek3, text="OpenRegister.de klíč:", width=20).pack(side=LEFT)
        ttk.Entry(radek3, textvariable=self.var_de_klic, show="•").pack(side=LEFT, fill=X, expand=True)
        radek4 = ttk.Frame(ramec_klice)
        radek4.pack(fill=X, padx=8, pady=4)
        ttk.Label(radek4, text="Scoris klíč:", width=20).pack(side=LEFT)
        ttk.Entry(radek4, textvariable=self.var_scoris_klic, show="•").pack(side=LEFT, fill=X, expand=True)
        ttk.Label(
            ramec_klice,
            text="OpenRegister.de = skutečný obor pro Německo, Scoris = pro Švédsko/"
                 "Finsko/Estonsko/Lotyšsko/Litvu. Klíče se nikam neukládají.",
            foreground="#666", wraplength=660, justify=LEFT,
        ).pack(anchor="w", padx=8, pady=(0, 6))

        ramec_db = ttk.LabelFrame(self.root, text="Místní databáze (jednorázová příprava, velké stažení)")
        ramec_db.pack(fill=X, **pad)
        radek5 = ttk.Frame(ramec_db)
        radek5.pack(fill=X, padx=8, pady=4)
        ttk.Button(radek5, text="Připravit Německo (~2,6 GB)",
                   command=lambda: self._priprav_db("de")).pack(side=LEFT)
        ttk.Button(radek5, text="Připravit UK (~500 MB)",
                   command=lambda: self._priprav_db("gb")).pack(side=LEFT, padx=(8, 0))

        ramec_beh = ttk.Frame(self.root)
        ramec_beh.pack(fill=X, **pad)
        self.tlacitko_spustit = ttk.Button(ramec_beh, text="Spustit", command=self._spustit)
        self.tlacitko_spustit.pack(side=LEFT)
        self.tlacitko_otevrit = ttk.Button(
            ramec_beh, text="Otevřít výstup", command=self._otevri_vystup, state="disabled")
        self.tlacitko_otevrit.pack(side=LEFT, padx=(8, 0))
        self.progress = ttk.Progressbar(ramec_beh, mode="determinate")
        self.progress.pack(side=LEFT, fill=X, expand=True, padx=(10, 0))

        ttk.Label(
            self.root, text="EY s.r.o., IČO 26705338 — vytvořil Robert Plevač "
                            "(robert.plevac@cz.ey.com)",
            foreground="#888", anchor="center",
        ).pack(side="bottom", fill=X, pady=(0, 4))

        ramec_log = ttk.LabelFrame(self.root, text="Průběh")
        ramec_log.pack(fill=BOTH, expand=True, **pad)
        self.log = scrolledtext.ScrolledText(ramec_log, height=12, state="disabled", wrap="word")
        self.log.pack(fill=BOTH, expand=True, padx=6, pady=6)

    # -- pomocne akce --------------------------------------------------------

    def _vyber_vstup(self):
        cesta = filedialog.askopenfilename(
            title="Vyberte vstupní seznam firem",
            filetypes=[("Podporované soubory", "*.csv *.xlsx *.txt"), ("Všechny soubory", "*.*")])
        if cesta:
            self.var_vstup.set(cesta)
            if not self.var_vystup.get():
                zaklad, _ = os.path.splitext(cesta)
                self.var_vystup.set(zaklad + "_vystup.xlsx")

    def _vyber_vystup(self):
        cesta = filedialog.asksaveasfilename(
            title="Kam uložit výstup", defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")])
        if cesta:
            self.var_vystup.set(cesta)

    def _pridej_log(self, text):
        self.log.configure(state="normal")
        self.log.insert(END, text + "\n")
        self.log.see(END)
        self.log.configure(state="disabled")

    def _otevri_vystup(self):
        if self.cesta_vystup and os.path.exists(self.cesta_vystup):
            if sys.platform.startswith("win"):
                os.startfile(self.cesta_vystup)  # noqa: S606 (uzivatelem vybrany soubor)
            elif sys.platform == "darwin":
                os.system('open "%s"' % self.cesta_vystup)
            else:
                webbrowser.open(self.cesta_vystup)

    # -- priprava mistnich databazi -----------------------------------------

    def _priprav_db(self, druh):
        if self.bezi:
            return
        self.bezi = True
        self._nastav_stav_behu(True)
        self._pridej_log("Připravuji místní databázi (%s) – může to trvat i desítky minut…" % druh.upper())

        def uloha():
            try:
                if druh == "de":
                    d.de_pripravit_databazi()
                else:
                    d.gb_pripravit_databazi()
                self.fronta.put(("db_hotovo", druh))
            except Exception as e:
                self.fronta.put(("chyba", "Příprava databáze selhala: %s" % e))

        threading.Thread(target=uloha, daemon=True).start()

    # -- samotny beh ----------------------------------------------------------

    def _sestav_argumenty(self):
        a = vychozi_argumenty()
        a.vstup = self.var_vstup.get().strip()
        a.vystup = self.var_vystup.get().strip() or "dodavatele_vystup.xlsx"
        a.vies = self.var_vies.get()
        a.de_api_klic = self.var_de_klic.get().strip()
        a.scoris_api_klic = self.var_scoris_klic.get().strip()
        for klic, attr, _popis, _vychozi in ZDROJE:
            setattr(a, attr, not self.var_zdroje[klic].get())
        return a

    def _spustit(self):
        if self.bezi:
            return
        a = self._sestav_argumenty()
        if not a.vstup:
            messagebox.showwarning(NAZEV_OKNA, "Nejdřív vyberte vstupní soubor.")
            return
        if not os.path.exists(a.vstup):
            messagebox.showerror(NAZEV_OKNA, "Vstupní soubor neexistuje:\n%s" % a.vstup)
            return

        self.bezi = True
        self._nastav_stav_behu(True)
        self.progress.configure(mode="indeterminate")
        self.progress.start(12)
        self.log.configure(state="normal")
        self.log.delete("1.0", END)
        self.log.configure(state="disabled")
        self._pridej_log("Spouštím zpracování %s…" % a.vstup)

        def na_radek(hotovo, celkem, z):
            self.fronta.put(("radek", (hotovo, celkem, z.hledany_nazev, z.stav)))

        def uloha():
            try:
                zaznamy = d.spustit(a, na_radek=na_radek)
                self.fronta.put(("hotovo", (a.vystup, zaznamy)))
            except RuntimeError as e:
                self.fronta.put(("chyba", str(e)))
            except Exception:
                self.fronta.put(("chyba", "Neočekávaná chyba:\n" + traceback.format_exc()))

        threading.Thread(target=uloha, daemon=True).start()

    def _nastav_stav_behu(self, bezi):
        stav = "disabled" if bezi else "normal"
        self.tlacitko_spustit.configure(state=stav)

    # -- zpracovani hlaseni z pozadi ----------------------------------------

    def _kontroluj_frontu(self):
        try:
            while True:
                druh, obsah = self.fronta.get_nowait()
                if druh == "radek":
                    hotovo, celkem, nazev, stav = obsah
                    if self.progress["mode"] != "determinate":
                        self.progress.stop()
                        self.progress.configure(mode="determinate", maximum=celkem)
                    self.progress["value"] = hotovo
                    self._pridej_log("[%d/%d] %s -> %s" % (hotovo, celkem, nazev, stav))
                elif druh == "hotovo":
                    cesta, zaznamy = obsah
                    self.cesta_vystup = cesta
                    self.progress.stop()
                    self.progress.configure(mode="determinate")
                    self.progress["value"] = self.progress["maximum"]
                    souhrn = {}
                    for z in zaznamy:
                        souhrn[z.stav] = souhrn.get(z.stav, 0) + 1
                    self._pridej_log("\nHotovo -> %s" % cesta)
                    self._pridej_log("Souhrn: " + ", ".join(
                        "%s=%d" % kv for kv in sorted(souhrn.items())))
                    self.bezi = False
                    self._nastav_stav_behu(False)
                    self.tlacitko_otevrit.configure(state="normal")
                    messagebox.showinfo(NAZEV_OKNA, "Hotovo. Výstup uložen do:\n%s" % cesta)
                elif druh == "db_hotovo":
                    self._pridej_log("Místní databáze (%s) je připravená." % obsah.upper())
                    self.bezi = False
                    self._nastav_stav_behu(False)
                    self.progress.stop()
                    self.progress.configure(mode="determinate")
                elif druh == "chyba":
                    self.progress.stop()
                    self.progress.configure(mode="determinate")
                    self._pridej_log("CHYBA: %s" % obsah)
                    self.bezi = False
                    self._nastav_stav_behu(False)
                    messagebox.showerror(NAZEV_OKNA, str(obsah))
        except queue.Empty:
            pass
        self.root.after(150, self._kontroluj_frontu)


def main():
    root = Tk()
    try:
        ttk.Style().theme_use("clam")
    except Exception:
        pass
    Aplikace(root)
    root.mainloop()


if __name__ == "__main__":
    main()

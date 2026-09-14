# -*- coding: utf-8 -*-
"""
Generatorul de harta: o fereastra pentru toate uneltele (cladire, rand de cladiri, strazi, cartier), cu toate
setarile, setari prestabilite si setarile tale salvate (tools/generator_setari.json). Porneste din
GENERATOR.bat (Python-ul sistemului, tkinter); generarea ruleaza Blender fara interfata, ca .bat-urile.
"""
import json
import os
import queue
import re
import subprocess
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
USER_PRESETS = TOOLS / "generator_setari.json"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
TEX = ("texturi", "Texturi", ["gta", "simple"], "gta")
SEED = ("seed", "Seed (0 = la intamplare)", int, 0)

# camp: (cheie = argumentul --cheie, eticheta, tip sau lista de variante, implicit)
TABS = [
    {"name": "Cladire", "script": "gen_cladire.py", "out": "output/cladiri", "fixed": [],
     "fields": [("tip", "Tip", ["vila", "casa", "bloc", "magazin", "hala"], "casa"),
                ("etaje", "Etaje (0 = dupa tip)", int, 0),
                ("latime", "Latime m (0 = dupa tip)", float, 0.0),
                ("adancime", "Adancime m (0 = dupa tip)", float, 0.0),
                ("inaltime", "Inaltime etaj m (0 = dupa tip)", float, 0.0),
                ("acoperis", "Acoperis", ["auto", "patru", "doua", "plat"], "auto"),
                ("interior", "Cu interior", bool, False),
                ("fara_magazin", "Bloc fara magazine la parter", bool, False), TEX, SEED],
     "presets": {
         "Casa mica de suburbie": {"tip": "casa", "etaje": 1, "latime": 10, "adancime": 8, "acoperis": "doua"},
         "Casa cu etaj": {"tip": "casa", "etaje": 2, "latime": 12, "adancime": 9},
         "Vila Vinewood": {"tip": "vila", "etaje": 2, "latime": 20, "adancime": 13, "acoperis": "patru"},
         "Vila mare": {"tip": "vila", "etaje": 3, "latime": 26, "adancime": 16},
         "Bloc Liberty City mic": {"tip": "bloc", "etaje": 4, "latime": 12, "adancime": 16},
         "Bloc Liberty City": {"tip": "bloc", "etaje": 6, "latime": 16, "adancime": 20},
         "Bloc Liberty City inalt": {"tip": "bloc", "etaje": 9, "latime": 20, "adancime": 24},
         "Bloc de locuinte": {"tip": "bloc", "etaje": 5, "latime": 18, "adancime": 14, "fara_magazin": True},
         "Magazin de cartier": {"tip": "magazin", "latime": 14, "adancime": 12},
         "Supermarket": {"tip": "magazin", "latime": 30, "adancime": 22},
         "Hala / depozit": {"tip": "hala", "latime": 30, "adancime": 40},
         "Casa cu interior": {"tip": "casa", "etaje": 2, "latime": 12, "adancime": 10, "interior": True}}},
    {"name": "Rand de cladiri", "script": "gen_cladire.py", "out": "output/cladiri", "fixed": ["--rand"],
     "fields": [("lungime", "Lungime (m)", float, 60.0), ("adancime", "Adancime (m)", float, 16.0),
                ("etaje_min", "Etaje minim", int, 3), ("etaje_max", "Etaje maxim", int, 7),
                ("alei", "Alei intre cladiri (0 - 1)", float, 0.25),
                ("interior", "Cu interior", bool, False), TEX, SEED],
     "presets": {"Rand Liberty City 60 m": {},
                 "Rand lung 100 m": {"lungime": 100, "etaje_min": 4, "etaje_max": 9},
                 "Rand de blocuri joase": {"etaje_min": 2, "etaje_max": 4},
                 "Rand lipit, fara alei": {"alei": 0.0},
                 "Rand aerisit, multe alei": {"alei": 0.7}}},
    {"name": "Strazi", "script": "gen_strada.py", "out": "output/strazi", "fixed": [],
     "fields": [("tip", "Tip", ["strada", "artera", "alee"], "strada"),
                ("piesa", "Piesa", ["kit", "drept20", "drept10", "trecere", "cruce", "T", "curba", "capat"], "kit"),
                TEX],
     "presets": {"Kit strada 2 benzi": {"tip": "strada"}, "Kit artera 4 benzi": {"tip": "artera"},
                 "Kit alee": {"tip": "alee"}}},
    {"name": "Cartier", "script": "gen_cartier.py", "out": "output/cartiere", "fixed": [],
     "fields": [("x", "Cvartale pe X", int, 3), ("y", "Cvartale pe Y", int, 2),
                ("cvartal", "Marimea unui cvartal (X x Y, m)", str, "80x50"),
                ("bulevard", "Drumurile pe Y", ["artera", "strada", "alee"], "artera"),
                ("strada", "Drumurile pe X", ["strada", "artera", "alee"], "strada"),
                ("etaje_min", "Etaje minim", int, 3), ("etaje_max", "Etaje maxim", int, 9),
                ("alei", "Alei intre cladiri (0 - 1)", float, 0.3),
                ("doua_randuri", "Cvartale cu alee pe mijloc (0 - 1)", float, 0.2),
                ("turnuri", "Cvartale cu turn (0 - 1)", float, 0.06),
                ("parcari", "Parcari (0 - 1)", float, 0.06),
                ("parcuri", "Parcuri (0 - 1)", float, 0.12),
                ("relief", "Relief: cat urca / coboara (m, 0 = plat)", float, 0.0),
                ("netezime", "Lungimea dealurilor (m, mai mare = mai lin)", float, 250.0), TEX, SEED],
     "presets": {"Liberty City dens": {},
                 "Cartier mic de test": {"x": 2, "y": 2},
                 "Centru cu turnuri": {"x": 4, "y": 3, "etaje_min": 5, "etaje_max": 14, "turnuri": 0.3,
                                       "parcuri": 0.08},
                 "Cartier pe deal": {"x": 3, "y": 3, "etaje_min": 2, "etaje_max": 6, "relief": 10.0,
                                     "netezime": 220.0, "parcuri": 0.15},
                 "Deal abrupt (San Fierro)": {"x": 3, "y": 2, "etaje_min": 2, "etaje_max": 5, "relief": 18.0,
                                              "netezime": 180.0},
                 "Cartier jos si aerisit": {"etaje_min": 2, "etaje_max": 4, "alei": 0.6, "doua_randuri": 0.4,
                                            "parcari": 0.15, "parcuri": 0.2},
                 "Cvartale lungi Manhattan": {"cvartal": "150x45", "x": 2, "y": 4, "doua_randuri": 0.35}}},
]
SHOW = re.compile(r"^(CLADIRE|STRADA|CARTIER)|Error|Traceback|^\s+File |rror:")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Generator harta (cladiri, strazi, cartiere)")
        self.geometry("760x820")
        self.user = self._load_user()
        self.proc, self.q, self.last_file, self.started = None, queue.Queue(), None, 0.0
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="x", padx=8, pady=8)
        self.tabs = []
        for spec in TABS:
            frame = ttk.Frame(self.nb, padding=10)
            self.nb.add(frame, text=spec["name"])
            self.tabs.append(self._build_tab(frame, spec))
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=8)
        self.btn_gen = ttk.Button(bar, text="Genereaza", command=self.generate)
        self.btn_gen.pack(side="left")
        self.btn_blend = ttk.Button(bar, text="Deschide in Blender", command=self.open_blender, state="disabled")
        self.btn_blend.pack(side="left", padx=6)
        ttk.Button(bar, text="Deschide folderul", command=self.open_dir).pack(side="left")
        ttk.Button(bar, text="Editor de oras (desenezi tu)",
                   command=lambda: os.startfile(ROOT / "EDITOR_ORAS.bat")).pack(side="left", padx=6)
        self.status = ttk.Label(bar, text="")
        self.status.pack(side="left", padx=10)
        self.log = tk.Text(self, height=12, wrap="word")
        self.log.pack(fill="both", expand=True, padx=8, pady=8)
        self._write("Alegi un tab, o setare prestabilita (sau le schimbi tu), apoi Genereaza.\n"
                    "Rezultatul (.glb + .blend) il tragi in Blender sau apesi Deschide in Blender.\n")
        self.after(150, self._poll)

    # ------------------------------------------------------------------ formular si setari
    def _build_tab(self, frame, spec):
        tab = {"spec": spec, "vars": {}}
        top = ttk.Frame(frame)
        top.pack(fill="x", pady=(0, 10))
        ttk.Label(top, text="Setari prestabilite:").pack(side="left")
        tab["combo"] = ttk.Combobox(top, state="readonly", width=32)
        tab["combo"].pack(side="left", padx=4)
        tab["combo"].bind("<<ComboboxSelected>>", lambda _e: self.apply_preset(tab))
        ttk.Button(top, text="Salveaza ca...", command=lambda: self.save_preset(tab)).pack(side="left")
        ttk.Button(top, text="Sterge", command=lambda: self.delete_preset(tab)).pack(side="left", padx=4)
        ttk.Button(top, text="Implicit", command=lambda: self.set_values(tab, {})).pack(side="left")
        form = ttk.Frame(frame)
        form.pack(fill="x")
        for r, (key, label, kind, default) in enumerate(spec["fields"]):
            ttk.Label(form, text=label).grid(row=r, column=0, sticky="w", pady=2)
            if isinstance(kind, list):
                var = tk.StringVar(value=default)
                widget = ttk.Combobox(form, textvariable=var, values=kind, state="readonly", width=14)
            elif kind is bool:
                var = tk.BooleanVar(value=default)
                widget = ttk.Checkbutton(form, variable=var)
            else:
                var = tk.StringVar(value=str(default))
                widget = ttk.Entry(form, textvariable=var, width=16)
            widget.grid(row=r, column=1, sticky="w", padx=10)
            tab["vars"][key] = var
        self._refresh(tab)
        return tab

    def _load_user(self):
        try:
            return json.loads(USER_PRESETS.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _refresh(self, tab):
        name = tab["spec"]["name"]
        tab["combo"]["values"] = list(tab["spec"]["presets"]) + [f"(al meu) {n}" for n in self.user.get(name, {})]

    def set_values(self, tab, values):
        for key, _label, kind, default in tab["spec"]["fields"]:
            value = values.get(key, default)
            tab["vars"][key].set(value if kind is bool or isinstance(kind, list) else str(value))

    def apply_preset(self, tab):
        choice = tab["combo"].get()
        if choice.startswith("(al meu) "):
            values = self.user.get(tab["spec"]["name"], {}).get(choice[9:], {})
        else:
            values = tab["spec"]["presets"].get(choice, {})
        self.set_values(tab, values)

    def values(self, tab):
        out = {}
        for key, label, kind, _default in tab["spec"]["fields"]:
            raw = tab["vars"][key].get()
            try:
                if kind is int:
                    out[key] = int(float(str(raw).replace(",", ".")))
                elif kind is float:
                    out[key] = float(str(raw).replace(",", "."))
                else:
                    out[key] = raw
            except ValueError:
                raise ValueError(f"'{label}' trebuie sa fie un numar (ai scris: {raw})")
        return out

    def save_preset(self, tab):
        try:
            values = self.values(tab)
        except ValueError as error:
            messagebox.showerror("Setare gresita", str(error))
            return
        name = simpledialog.askstring("Salveaza setarile", "Numele setarii:", parent=self)
        if not name:
            return
        self.user.setdefault(tab["spec"]["name"], {})[name.strip()] = values
        USER_PRESETS.write_text(json.dumps(self.user, indent=1, ensure_ascii=False), encoding="utf-8")
        self._refresh(tab)
        tab["combo"].set(f"(al meu) {name.strip()}")

    def delete_preset(self, tab):
        choice = tab["combo"].get()
        if not choice.startswith("(al meu) "):
            messagebox.showinfo("Sterge", "Poti sterge doar setarile salvate de tine (cele cu \"(al meu)\").")
            return
        self.user.get(tab["spec"]["name"], {}).pop(choice[9:], None)
        USER_PRESETS.write_text(json.dumps(self.user, indent=1, ensure_ascii=False), encoding="utf-8")
        self._refresh(tab)
        tab["combo"].set("")

    # ------------------------------------------------------------------ generare
    def current(self):
        return self.tabs[self.nb.index("current")]

    def generate(self):
        if self.proc is not None:
            return
        tab = self.current()
        try:
            values = self.values(tab)
        except ValueError as error:
            messagebox.showerror("Setare gresita", str(error))
            return
        args = list(tab["spec"]["fixed"])
        for key, value in values.items():
            flag = "--" + key.replace("_", "-")
            if isinstance(value, bool):
                if value:
                    args.append(flag)
            else:
                args += [flag, str(value)]
        cmd = ["cmd", "/c", str(TOOLS / "_blender.bat"), "-b", "-P", str(TOOLS / tab["spec"]["script"]), "--"] + args
        self._write(f"\n> {tab['spec']['name']}: {' '.join(args)}\n")
        self.proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                     encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
        self.started = time.time()
        self.btn_gen.state(["disabled"])
        threading.Thread(target=self._reader, args=(self.proc,), daemon=True).start()

    def _reader(self, proc):
        for line in proc.stdout:
            self.q.put(line)
        proc.wait()
        self.q.put(None)

    def _poll(self):
        try:
            while True:
                line = self.q.get_nowait()
                if line is None:
                    code = self.proc.returncode
                    self.proc = None
                    self.btn_gen.state(["!disabled"])
                    self.status["text"] = "gata" if code == 0 else f"eroare (cod {code})"
                    continue
                if "_FISIER " in line:
                    self.last_file = Path(line.split("_FISIER ", 1)[1].strip())
                    self.btn_blend.state(["!disabled"])
                if SHOW.search(line):
                    self._write(line if line.endswith("\n") else line + "\n")
        except queue.Empty:
            pass
        if self.proc is not None:
            self.status["text"] = f"lucrez... {time.time() - self.started:.0f} s"
        self.after(150, self._poll)

    def _write(self, text):
        self.log.insert("end", text)
        self.log.see("end")

    def open_blender(self):
        if self.last_file is None:
            return
        blend = self.last_file.with_suffix(".blend")
        subprocess.Popen(["cmd", "/c", str(TOOLS / "_blender.bat"), str(blend)], cwd=ROOT, creationflags=NO_WINDOW)

    def open_dir(self):
        path = ROOT / self.current()["spec"]["out"]
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)


if __name__ == "__main__":
    App().mainloop()

# -*- coding: utf-8 -*-
"""
DayZ Map Studio - interfata grafica (tkinter) pentru generatorul de harta DayZ -> GTA V.

Ruleaza cu Python-ul de sistem (3.10+, are nevoie doar de numpy si tkinter):
    python map_studio.py          sau      MAP_STUDIO.bat

Stanga: setarile (aceleasi campuri ca in map.json). Dreapta: previzualizarea hartii.
Jos: log-ul si butoanele (previzualizare, generare in Blender, instalare in server, export obiecte).
"""
import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from dayzgen.config import MapConfig, PRESETS  # noqa: E402

MAP_JSON = HERE / "map.json"
PREVIEW_PX = 620

# gruparea campurilor in formular; ce nu apare aici ajunge in "Avansat"
GROUPS = [
    ("Harta", ["name", "seed", "size", "origin_x", "origin_y", "max_height"]),
    ("Sate / drumuri / campuri", ["num_villages", "village_radius", "houses_per_village",
                                  "road_half_width", "fields_per_village"]),
    ("Vegetatie (densitati: 1 obiect la N m2)",
     ["forest_coverage", "tree_spacing", "lone_tree_area", "bush_edge_area", "bush_open_area",
      "rock_slope_area", "rock_open_area", "forest_debris_area"]),
    ("Distante LOD (m)", ["lod_dist_terrain", "lod_dist_tree", "lod_dist_bush", "lod_dist_rock",
                          "lod_dist_building", "lod_dist_small_prop"]),
    ("Texturi", ["terrain_tex_size", "building_tex_size", "terrain_uv_scale"]),
    ("Cai", ["fivem_resources_dir", "custom_objects_file"]),
]
LABELS = {
    "name": "Nume (prefix fisiere)", "seed": "Seed", "size": "Latura hartii (m)",
    "origin_x": "Origine X (GTA V)", "origin_y": "Origine Y (GTA V)", "max_height": "Inaltime maxima (m)",
    "num_villages": "Numar de sate", "village_radius": "Raza sat (min, max)",
    "houses_per_village": "Case per sat (min, max)", "road_half_width": "Jumatate latime drum (m)",
    "fields_per_village": "Campuri per sat (min, max)",
    "forest_coverage": "Acoperire padure (0-1)", "tree_spacing": "Distanta intre copaci (m)",
    "lone_tree_area": "Copaci izolati", "bush_edge_area": "Tufisuri la margine de padure",
    "bush_open_area": "Tufisuri in camp deschis", "rock_slope_area": "Stanci pe panta",
    "rock_open_area": "Stanci in camp deschis", "forest_debris_area": "Busteni / cioturi",
    "lod_dist_terrain": "Teren", "lod_dist_tree": "Copaci", "lod_dist_bush": "Tufisuri",
    "lod_dist_rock": "Stanci", "lod_dist_building": "Cladiri", "lod_dist_small_prop": "Props mici",
    "terrain_tex_size": "Textura teren (px)", "building_tex_size": "Textura cladiri (px)",
    "terrain_uv_scale": "Repetare textura teren (m)",
    "fivem_resources_dir": "Folder resurse FiveM", "custom_objects_file": "Fisier obiecte editor",
    "cell": "Distanta intre vertecsi (m)", "tile_size": "Latura tile teren (m)",
    "sea_depth": "Adancime mare (m)", "chunk_size": "Latura chunk ymap (m)",
    "export_gen9": "Exporta si gen9 (GTA V Enhanced)", "package_ragemp": "Construieste si dlc.rpf (RAGE:MP)",
    "keep_scene": "Salveaza scena .blend", "write_preview_png": "Scrie PNG-uri de previzualizare",
    "preset": "Preset",
}


class Studio:
    def __init__(self, root):
        self.root = root
        root.title("DayZ Map Studio")
        root.geometry("1360x900")
        self.vars = {}
        self.proc = None
        self.busy = False
        self.msgq = queue.Queue()
        self.world = None
        self.cfg_preview = None
        self.photo = None
        self.preview_size = PREVIEW_PX
        self._build_ui()
        self._load_initial()
        self.root.after(120, self._pump)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        top = ttk.Frame(self.root)
        top.pack(fill="both", expand=True, padx=8, pady=8)

        # --- stanga: formular ---
        left = ttk.Frame(top)
        left.pack(side="left", fill="y")
        head = ttk.Frame(left)
        head.pack(fill="x", pady=(0, 6))
        ttk.Label(head, text="Preset:").pack(side="left")
        self.preset_var = tk.StringVar(value="demo")
        self.preset_box = ttk.Combobox(head, textvariable=self.preset_var, values=sorted(PRESETS),
                                       width=8, state="readonly")
        self.preset_box.pack(side="left", padx=4)
        self.btn_preset = ttk.Button(head, text="Incarca preset", command=self.on_load_preset)
        self.btn_preset.pack(side="left", padx=4)

        canvas = tk.Canvas(left, width=420, highlightthickness=0)
        scroll = ttk.Scrollbar(left, orient="vertical", command=canvas.yview)
        form = ttk.Frame(canvas)
        form.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=form, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="y", expand=True)
        scroll.pack(side="left", fill="y")
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

        used = set()
        for title, names in GROUPS:
            used.update(names)
            self._group(form, title, names)
        rest = [f for f in MapConfig.field_names() if f not in used and f != "preset"]
        if rest:
            self._group(form, "Avansat", rest)

        # --- dreapta: previzualizare ---
        right = ttk.Frame(top)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))
        self.preview = tk.Canvas(right, width=PREVIEW_PX, height=PREVIEW_PX, bg="#1b1b1b",
                                 highlightthickness=1, highlightbackground="#555")
        self.preview.pack(anchor="n")
        self.preview.bind("<Button-1>", self.on_click_map)
        self.stats = ttk.Label(right, text="Apasa 'Previzualizare' ca sa vezi harta.", justify="left")
        self.stats.pack(anchor="w", pady=6)
        self.coord = ttk.Label(right, text="", foreground="#0a5", justify="left")
        self.coord.pack(anchor="w")

        # --- jos: butoane + log ---
        bottom = ttk.Frame(self.root)
        bottom.pack(fill="both", expand=False, padx=8, pady=(0, 8))
        bar = ttk.Frame(bottom)
        bar.pack(fill="x", pady=4)
        self.buttons = []
        for text, cmd in (("Salveaza map.json", self.on_save),
                          ("Previzualizare", self.on_preview),
                          ("Genereaza", self.on_generate),
                          ("Instaleaza in server", self.on_install),
                          ("Exporta obiectele", self.on_export_objects),
                          ("Deschide REZUMAT.txt", self.on_open_summary)):
            b = ttk.Button(bar, text=text, command=cmd)
            b.pack(side="left", padx=3)
            self.buttons.append(b)
        self.buttons.append(self.btn_preset)

        logf = ttk.LabelFrame(bottom, text="Log")
        logf.pack(fill="both", expand=True)
        self.logbox = tk.Text(logf, height=11, wrap="none", bg="#111", fg="#ddd", insertbackground="#ddd")
        sb = ttk.Scrollbar(logf, orient="vertical", command=self.logbox.yview)
        self.logbox.configure(yscrollcommand=sb.set)
        self.logbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")

    def _group(self, parent, title, names):
        fr = ttk.LabelFrame(parent, text=title)
        fr.pack(fill="x", padx=4, pady=4)
        for r, fname in enumerate(names):
            default = getattr(PRESETS["demo"], fname)
            label = LABELS.get(fname, fname)
            ttk.Label(fr, text=label, width=28, anchor="w").grid(row=r, column=0, sticky="w", padx=4, pady=2)
            if isinstance(default, bool):
                var = tk.BooleanVar(value=default)
                ttk.Checkbutton(fr, variable=var).grid(row=r, column=1, sticky="w", padx=4)
            else:
                var = tk.StringVar(value=self._fmt(default))
                ent = ttk.Entry(fr, textvariable=var, width=24)
                ent.grid(row=r, column=1, sticky="we", padx=4)
                if fname == "seed":
                    ttk.Button(fr, text="Seed aleator", width=13,
                               command=self.on_random_seed).grid(row=r, column=2, padx=2)
                elif fname == "fivem_resources_dir":
                    ttk.Button(fr, text="...", width=3,
                               command=lambda v=var: self._pick_dir(v)).grid(row=r, column=2, padx=2)
            self.vars[fname] = var
        fr.columnconfigure(1, weight=1)

    @staticmethod
    def _fmt(v):
        if isinstance(v, (tuple, list)):
            return ", ".join(str(x) for x in v)
        return str(v)

    def _pick_dir(self, var):
        d = filedialog.askdirectory(initialdir=var.get() or "C:\\")
        if d:
            var.set(os.path.normpath(d))

    # ------------------------------------------------------------------ log
    def log(self, msg):
        self.msgq.put(str(msg))

    def _pump(self):
        try:
            while True:
                line = self.msgq.get_nowait()
                if isinstance(line, tuple):
                    line[0](*line[1:])
                    continue
                self.logbox.insert("end", line.rstrip("\n") + "\n")
                self.logbox.see("end")
        except queue.Empty:
            pass
        self.root.after(120, self._pump)

    def ui(self, fn, *a):
        """Cheama `fn(*a)` pe firul de interfata."""
        self.msgq.put((fn,) + a)

    def set_busy(self, busy):
        self.busy = busy
        for b in self.buttons:
            b.state(["disabled"] if busy else ["!disabled"])

    # ------------------------------------------------------------------ config
    def _load_initial(self):
        if MAP_JSON.is_file():
            try:
                cfg = MapConfig.from_json(MAP_JSON)
                self.apply_cfg(cfg)
                self.log(f"Am incarcat setarile din {MAP_JSON}")
                return
            except ValueError as e:
                self.log(f"map.json nu a putut fi citit: {e}")
        self.apply_cfg(PRESETS["demo"])
        self.log("Setari implicite (preset demo). Apasa 'Salveaza map.json' ca sa le pastrezi.")

    def apply_cfg(self, cfg: MapConfig):
        self.preset_var.set(cfg.preset)
        for k, v in cfg.to_dict().items():
            if k == "preset" or k not in self.vars:
                continue
            var = self.vars[k]
            if isinstance(var, tk.BooleanVar):
                var.set(bool(v))
            else:
                var.set(self._fmt(v))

    def collect_cfg(self) -> MapConfig:
        """Formular -> MapConfig (arunca ValueError cu mesaj clar)."""
        data = {"preset": self.preset_var.get()}
        ref = PRESETS[data["preset"]]
        for k, var in self.vars.items():
            raw = var.get()
            default = getattr(ref, k)
            label = LABELS.get(k, k)
            if isinstance(default, bool):
                data[k] = bool(raw)
            elif isinstance(default, tuple):
                parts = [p.strip() for p in str(raw).replace(";", ",").split(",") if p.strip()]
                if len(parts) != len(default):
                    raise ValueError(f"'{label}' are nevoie de {len(default)} valori separate prin virgula")
                try:
                    data[k] = [type(default[i])(float(p)) for i, p in enumerate(parts)]
                except ValueError:
                    raise ValueError(f"'{label}': valori numerice invalide ({raw!r})")
            elif isinstance(default, int):
                try:
                    data[k] = int(float(str(raw).strip()))
                except ValueError:
                    raise ValueError(f"'{label}': trebuie un numar intreg ({raw!r})")
            elif isinstance(default, float):
                try:
                    data[k] = float(str(raw).strip().replace(",", "."))
                except ValueError:
                    raise ValueError(f"'{label}': trebuie un numar ({raw!r})")
            else:
                data[k] = str(raw).strip()
        cfg = MapConfig.from_dict(data)
        try:
            cfg.validate()
        except AssertionError as e:
            raise ValueError(f"Setari invalide: {e}")
        return cfg

    def try_cfg(self):
        try:
            return self.collect_cfg()
        except ValueError as e:
            messagebox.showerror("Setari invalide", str(e))
            self.log(f"EROARE: {e}")
            return None

    # ------------------------------------------------------------------ butoane
    def on_load_preset(self):
        name = self.preset_var.get()
        self.apply_cfg(PRESETS[name])
        self.log(f"Preset incarcat: {name}")

    def on_random_seed(self):
        import random
        self.vars["seed"].set(str(random.randrange(1, 2 ** 31 - 1)))

    def on_save(self):
        cfg = self.try_cfg()
        if cfg is None:
            return
        cfg.to_json(MAP_JSON)
        self.log(f"Setari salvate in {MAP_JSON}")

    def on_preview(self):
        cfg = self.try_cfg()
        if cfg is None or self.busy:
            return
        self.set_busy(True)
        self.log(f"Previzualizare: {cfg.name} {cfg.size:.0f} m, seed {cfg.seed} ...")
        threading.Thread(target=self._preview_worker, args=(cfg,), daemon=True).start()

    def _preview_worker(self, cfg):
        try:
            from dayzgen import buildings, terrain
            from dayzgen.preview import render_map_preview
            radii = {k: v["radius"] for k, v in buildings.build_all().items()}
            world = terrain.World(cfg, radii, log=self.log).generate()
            tmp = HERE / "output" / cfg.name
            tmp.mkdir(parents=True, exist_ok=True)
            png = tmp / "studio_preview.png"
            render_map_preview(world, str(png), size=self.preview_size)
            self.world = world
            self.cfg_preview = cfg
            sx, sy, sz = world.spawn_point()
            stats = (f"Sate: {len(world.villages)}   Cladiri: {len(world.buildings)}   "
                     f"Props: {len(world.props)}   Drumuri: {len(world.roads)}\n"
                     f"SPAWN: X={sx + cfg.origin_x:.1f}  Y={sy + cfg.origin_y:.1f}  Z={sz:.1f}\n"
                     f"Zona in lumea GTA V: X {cfg.origin_x:.0f}..{cfg.origin_x + cfg.size:.0f}   "
                     f"Y {cfg.origin_y:.0f}..{cfg.origin_y + cfg.size:.0f}")
            self.ui(self._show_preview, str(png), stats)
            self.log(f"Previzualizare gata: {png}")
        except Exception as e:  # noqa
            import traceback
            self.log("EROARE la previzualizare: " + traceback.format_exc())
        finally:
            self.ui(self.set_busy, False)

    def _show_preview(self, png, stats):
        self.photo = tk.PhotoImage(file=png)
        self.preview.delete("all")
        self.preview.create_image(0, 0, anchor="nw", image=self.photo)
        self.stats.configure(text=stats)

    def on_click_map(self, ev):
        if self.world is None or self.cfg_preview is None:
            return
        cfg = self.cfg_preview
        s = self.preview_size
        if not (0 <= ev.x < s and 0 <= ev.y < s):
            return
        lx = ev.x / s * cfg.size                      # coloana 0 = vest
        ly = (1.0 - ev.y / s) * cfg.size              # randul 0 = nord
        wx, wy = lx + cfg.origin_x, ly + cfg.origin_y
        try:
            import numpy as np
            z = float(self.world.sample(self.world.h, np.array([[lx]]), np.array([[ly]]))[0, 0])
        except Exception:  # noqa
            z = 0.0
        txt = f"/gotoxyz {wx:.1f} {wy:.1f} {z + 1.5:.1f}"
        self.coord.configure(text=txt)
        self.log(f"Pozitie pe harta: X={wx:.1f} Y={wy:.1f} Z={z:.1f}   ->   {txt}")

    def on_generate(self):
        cfg = self.try_cfg()
        if cfg is None or self.busy:
            return
        cfg.to_json(MAP_JSON)
        bat = HERE / "tools" / "_run.bat"
        if not bat.is_file():
            messagebox.showerror("Lipseste", f"Nu gasesc {bat}")
            return
        self.log(f"Generez harta ({cfg.preset}) in Blender... poate dura cateva minute.")
        self._run_cmd([str(bat), cfg.preset, "--config", str(MAP_JSON)])

    def on_install(self):
        cfg = self.try_cfg()
        if cfg is None or self.busy:
            return
        src = HERE / "output" / cfg.name / "fivem" / cfg.name
        dst = Path(cfg.fivem_resources_dir) / cfg.name
        if not src.is_dir():
            messagebox.showerror("Lipseste", f"Nu exista {src}\nGenereaza harta mai intai.")
            return
        if not messagebox.askyesno("Confirmare", f"Copiez\n{src}\npeste\n{dst}\n\nContinui?"):
            return
        try:
            import shutil
            rel = cfg.custom_objects_file.replace("\\", "/")
            objp = dst / rel
            keep = json.loads(objp.read_text(encoding="utf-8-sig")) if objp.is_file() else None
            if keep is not None:
                self.log("Pastrez editor/objects.json existent din server.")
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            if keep is not None:
                # pastram obiectele/removed din server, dar luam "exportedAt" cel mai nou
                new = {}
                if (src / rel).is_file():
                    new = json.loads((src / rel).read_text(encoding="utf-8-sig"))
                keep["exportedAt"] = max(int(keep.get("exportedAt") or 0), int(new.get("exportedAt") or 0))
                objp.parent.mkdir(parents=True, exist_ok=True)
                objp.write_text(json.dumps(keep, indent=1, ensure_ascii=False), encoding="utf-8")
            self.log(f"Instalat in {dst}")
            messagebox.showinfo("Gata", f"Resursa a fost copiata in\n{dst}\n\n"
                                        f"Adauga 'ensure {cfg.name}' in server.cfg si "
                                        f"fa RESTART COMPLET de server.")
        except Exception as e:  # noqa
            self.log(f"EROARE la instalare: {e!r}")
            messagebox.showerror("Eroare", str(e))

    def on_export_objects(self):
        cfg = self.try_cfg()
        if cfg is None or self.busy:
            return
        cfg.to_json(MAP_JSON)
        self.log("Export obiecte manuale -> .ymap ...")
        self._run_cmd([sys.executable, str(HERE / "export_custom_ymap.py"), "--config", str(MAP_JSON)])

    def on_open_summary(self):
        cfg = self.try_cfg()
        if cfg is None:
            return
        p = HERE / "output" / cfg.name / "REZUMAT.txt"
        if not p.is_file():
            messagebox.showinfo("Lipseste", f"Nu exista inca {p}.\nGenereaza harta mai intai.")
            return
        os.startfile(str(p))  # noqa

    # ------------------------------------------------------------------ procese
    def _run_cmd(self, cmd):
        self.set_busy(True)
        threading.Thread(target=self._cmd_worker, args=(cmd,), daemon=True).start()

    def _cmd_worker(self, cmd):
        try:
            env = dict(os.environ, DAYZGEN_NOPAUSE="1", PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
            self.proc = subprocess.Popen(cmd, cwd=str(HERE), stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                         errors="replace", bufsize=1, env=env)
            for line in self.proc.stdout:
                if "nanobind" in line or "leaked" in line or "refleaks" in line:
                    continue
                self.log(line)
            code = self.proc.wait()
            self.log(f"--- proces terminat (cod {code}) ---")
        except Exception as e:  # noqa
            self.log(f"EROARE: {e!r}")
        finally:
            self.proc = None
            self.ui(self.set_busy, False)


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    Studio(root)
    root.mainloop()


if __name__ == "__main__":
    main()

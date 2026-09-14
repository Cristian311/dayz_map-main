# -*- coding: utf-8 -*-
"""
Serverul editorului de oras (EDITOR_ORAS.bat): pagina din tools/oras/web + API pentru planuri, analiza
(plan_geom.py, aceeasi ca la generare), generare in Blender (tools/gen_oras.py) si deschiderea rezultatului.

    python tools/oras/server.py [--port 8765] [--no-browser]
"""
import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
ROOT = TOOLS.parent
WEB = HERE / "web"
PLANS = ROOT / "output" / "orase"
sys.path.insert(0, str(HERE))
import plan_geom as G  # noqa: E402
import layout as L  # noqa: E402
import park_plan as PP  # noqa: E402

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
MIME = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8", ".png": "image/png",
        ".jpg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}
IMAGE_EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}
BACKGROUNDS = PLANS / "fundal"   # imaginile de fundal importate in editor (harti, schite)
JOB = {"proc": None, "lines": [], "file": None, "code": None}
LOCK = threading.Lock()


def plan_path(name):
    safe = "".join(c for c in name if c.isalnum() or c in "-_/").strip("/") or "oras"
    path = (PLANS / f"{safe}.json").resolve()
    if PLANS.resolve() not in path.parents:
        raise ValueError("nume de plan invalid")
    return path


def empty_plan():
    return {"version": 1, "seed": 1, "texturi": "gta", "panta_max": 0.10, "zona_implicita": "lc_caramida",
            "nodes": [], "roads": [], "zones": [], "altitudini": []}


# In ocean, la est de Los Santos, la nord de Cayo Perico (insula sta cam la X 4400..5200, Y -5800..-4400 si de la
# build 2189 e incarcata mereu: la 5500,-5500 dealurile si jungla ei treceau prin oras) si departe de harta dzdemo
# (X 7000..8024, Y -8000..-6976). 25 m deasupra marii: in larg valurile trec de 3-4 m si ar iesi prin strazi.
DEFAULT_JOC = {"x": 6000.0, "y": -2600.0, "z": 25.0}
CATALOG = ROOT / "dayzgen" / "data" / "catalog.json"
_catalog = []


def start_job(cmd, kind, keep, result=None, then=None, chained=False):
    """Marcheaza lucrarea ca pornita INAINTE de raspuns (altfel pagina intreaba prea devreme, afla ca nu ruleaza
    nimic si crede ca a esuat, iar un al doilea click porneste inca un Blender pe acelasi fisier). False = ocupat.
    then = ce porneste dupa, daca lucrarea iese bine (Trimite in joc: generare, apoi export); chained = pornita de
    lucrarea de dinainte: jurnalul continua, iar pagina nu vede nicio pauza intre ele."""
    with LOCK:
        if JOB["proc"] is not None and not chained:
            return False
        JOB.update(proc="porneste", lines=JOB["lines"] if chained else [],
                   file=None if kind == "generate" else JOB["file"], code=None, kind=kind,
                   result=None, progress=0.0, stage="pornesc Blender", ended=None, stopped=False, steps=None,
                   started=JOB.get("started") if chained else time.time(), chain=chained or then is not None)
    threading.Thread(target=run_job, args=(cmd, kind, keep, result, then), daemon=True).start()
    return True


def keep_gen(line):
    return line.startswith("ORAS")


def generate_cmd(name, full=False):
    """gen_oras.py in Blender. Implicit deschide .blend-ul de data trecuta si reface doar strazile, cvartalele si
    terenul schimbate (--incremental); full = tot orasul de la zero."""
    path = plan_path(name)
    blend = PLANS / f"{path.stem}.blend"
    inc = not full and blend.is_file()
    return (["cmd", "/c", str(TOOLS / "_blender.bat"), "-b"] + ([str(blend)] if inc else [])
            + ["-P", str(TOOLS / "gen_oras.py"), "--", "--plan", str(path)] + (["--incremental"] if inc else []))


def export_job(name, full=False):
    """(cmd, keep, fisierul cu rezultatul, resursa, .blend) pentru blender_fivem_export.py: orasul generat ->
    resursa FiveM, mutat in ocean (joc.x, joc.y) si ridicat la joc.z peste mare. full = fara export incremental."""
    path = plan_path(name)
    blend = PLANS / f"{path.stem}.blend"
    plan = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    joc = dict(DEFAULT_JOC, **{k: v for k, v in (plan.get("joc") or {}).items() if k in ("x", "y", "z")})
    result = PLANS / f"{path.stem}_export.json"
    result.unlink(missing_ok=True)
    cmd = ["cmd", "/c", str(TOOLS / "_blender.bat"), "-b", str(blend), "-P",
           str(TOOLS / "blender_fivem_export.py"), "--", "--name", resource_name(name, plan),
           "--offset", f"{float(joc['x']):.3f},{float(joc['y']):.3f},{float(joc['z']):.3f}",
           "--lod", "600", "--result", str(result)] + (["--full"] if full else [])      # cladirile: de la 600 m
    keep = lambda line: ((line.startswith("  ") or line.startswith("[") or "export" in line.lower())
                         and "successfully exported" not in line.lower())
    return cmd, keep, result, resource_name(name, plan), blend


def run_job(cmd, kind, keep, result=None, then=None):
    """Ruleaza Blender in fundal; liniile pastrate (keep) ajung in jurnalul din pagina."""
    try:
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
    except OSError as error:
        with LOCK:
            JOB["lines"].append(f"Eroare: Blender nu a pornit ({error})")
            JOB.update(proc=None, code=-1, ended=time.time())
        return
    with LOCK:
        JOB["proc"] = proc
        stop_now = JOB["stopped"]       # Opreste apasat cat Blender inca pornea
    if stop_now:
        kill_tree(proc)
    for line in proc.stdout:
        line = line.rstrip()
        if line.startswith("PROGRES"):
            progress_line(line)
            continue
        low = line.lower()
        if "successfully exported" in low:
            with LOCK:
                steps = JOB["steps"]
                if steps:
                    # Sollumz scrie fiecare fisier de doua ori (INFO: si Info:): numar numele, nu liniile
                    steps[5].add(low.split("successfully exported", 1)[1].strip())
                    steps[3] = len(steps[5])
                    JOB["progress"] = steps[0] + (steps[1] - steps[0]) * min(steps[3] / max(steps[2], 1), 1.0)
                    JOB["stage"] = f"{steps[4]}: {steps[3]} din {steps[2]}"
        if keep(line) or "Error" in line or "Traceback" in line or line.startswith("  File"):
            with LOCK:
                JOB["lines"].append(line)
                if line.startswith("ORAS_FISIER "):
                    JOB["file"] = line[len("ORAS_FISIER "):].strip()
    proc.wait()
    res = None
    if result is not None and Path(result).is_file():
        try:
            res = json.loads(Path(result).read_text(encoding="utf-8"))
        except ValueError:
            res = None
    with LOCK:
        ok = not JOB["stopped"] and proc.returncode == 0
        if not (ok and then):
            JOB.update(proc=None, code=proc.returncode, result=res, ended=time.time())
            if ok:
                JOB.update(progress=1.0, stage="gata")
    if ok and then:
        then()      # urmatoarea lucrare din lant (JOB["proc"] ramane ocupat pana porneste ea)


def progress_line(line):
    """PROGRES <0..1> <etapa>, sau PROGRES_PASI <de la> <pana la> <n> <etapa>: de acolo fiecare fisier scris de
    Sollumz ("successfully exported") muta bara cu (pana la - de la) / n."""
    parts = line.split(" ", 4 if line.startswith("PROGRES_PASI ") else 2)
    try:
        with LOCK:
            if parts[0] == "PROGRES_PASI":
                JOB["steps"] = [float(parts[1]), float(parts[2]), int(parts[3]), 0, parts[4] if len(parts) > 4 else "",
                                set()]
                JOB["progress"], JOB["stage"] = float(parts[1]), JOB["steps"][4]
            else:
                JOB.update(progress=float(parts[1]), stage=parts[2] if len(parts) > 2 else "", steps=None)
    except (ValueError, IndexError):
        pass


def kill_tree(proc):
    """Opreste cmd /c _blender.bat impreuna cu blender.exe pornit de el."""
    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, creationflags=NO_WINDOW)


def job_times():
    """(secunde trecute, secunde ramase estimate sau None) pentru lucrarea curenta."""
    if not JOB.get("started"):
        return 0.0, None
    elapsed = (JOB.get("ended") or time.time()) - JOB["started"]
    f = JOB.get("progress") or 0.0
    if JOB["proc"] is None or f < 0.04 or elapsed < 5:
        return elapsed, None
    return elapsed, elapsed * (1.0 - f) / f


def resource_name(name, plan):
    joc = plan.get("joc") or {}
    raw = (joc.get("resursa") or f"oras_{Path(name).name}").lower()
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in raw)


def server_cfg():
    """server.cfg al serverului FiveM: deasupra folderului de resurse din map.json."""
    try:
        res = json.loads((ROOT / "map.json").read_text(encoding="utf-8")).get("fivem_resources_dir")
    except (OSError, ValueError):
        res = None
    if not res:
        return None
    for folder in [Path(res)] + list(Path(res).parents):
        if (folder / "server.cfg").is_file():
            return folder / "server.cfg"
    return None


def catalog():
    """Cladirile GTA intregi (masurate 'solid') cu marimea lor, pentru unealta Cladire din editor."""
    if not _catalog and CATALOG.is_file():
        data = json.loads(CATALOG.read_text(encoding="utf-8")).get("archetypes", [])
        for a in data:
            if "solid" not in (a.get("tags") or []):
                continue
            mn, mx = a.get("min", [0, 0, 0]), a.get("max", [0, 0, 0])
            _catalog.append({"m": a["name"], "cat": a.get("cat", ""), "w": round(mx[0] - mn[0], 1),
                             "d": round(mx[1] - mn[1], 1), "h": round(mx[2] - mn[2], 1)})
        _catalog.sort(key=lambda c: (c["cat"], c["m"]))
    return _catalog


def plan_offset(name):
    """Unde sta orasul in joc (joc.x, joc.y, joc.z din plan, altfel DEFAULT_JOC): joc = plan + offset."""
    path = plan_path(name)
    plan = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    joc = dict(DEFAULT_JOC, **{k: v for k, v in (plan.get("joc") or {}).items() if k in ("x", "y", "z")})
    return float(joc["x"]), float(joc["y"]), float(joc["z"])


def carari_reply(name, joc):
    """Cararile planului (<plan>_carari.json); joc = in coordonatele din joc (pentru unealta Carare din /mapeditor)."""
    ox, oy, _oz = plan_offset(name) if joc else (0.0, 0.0, 0.0)
    return {"carari": [dict(c, puncte=[[round(p[0] + ox, 2), round(p[1] + oy, 2)] for p in c["puncte"]])
                       for c in PP.load_carari(plan_path(name))]}


def carari_change(name, body):
    """{"add": {"puncte": [[x, y], ...], "latime": m}} si/sau {"remove": id}; "joc": true = puncte din joc."""
    joc = bool(body.get("joc"))
    carari = PP.load_carari(plan_path(name))
    add = body.get("add") or {}
    if len(add.get("puncte") or []) >= 2:
        ox, oy, _oz = plan_offset(name) if joc else (0.0, 0.0, 0.0)
        ids = {c.get("id") for c in carari}
        k = 1
        while f"c{k}" in ids:
            k += 1
        carari.append({"id": f"c{k}", "latime": round(min(8.0, max(1.0, float(add.get("latime") or PP.LATIME))), 2),
                       "puncte": [[round(float(p[0]) - ox, 2), round(float(p[1]) - oy, 2)] for p in add["puncte"][:200]]})
    if body.get("remove"):
        carari = [c for c in carari if c.get("id") != str(body["remove"])]
    path = PP.carari_file(plan_path(name))
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"carari": carari}, indent=1), encoding="utf-8")
    os.replace(tmp, path)
    return carari_reply(name, joc)


def park_preview(plan, A, carari):
    """Aleile parcurilor ca la generare (gen_oras: acelasi seed si acelasi rng pe parc, park_plan.park_paths):
    [{"auto", "plaza": [cx, cy, r] | None, "paths": [[puncte, latime], ...]}]."""
    import random
    seed = int(plan.get("seed", 1))
    out = []

    def add(poly, rng, auto):
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        paths, (cx, cy), plaza = PP.park_paths(min(xs), min(ys), max(xs), max(ys), rng, poly, auto,
                                               PP.near(carari, poly))
        out.append({"auto": auto, "plaza": [round(cx, 2), round(cy, 2), round(plaza, 2)] if plaza > 0 else None,
                    "paths": [[[[round(p[0], 2), round(p[1], 2)] for p in pts], w] for pts, w in paths]})

    def is_park(zona):
        return (L.ZONES.get(zona) or {}).get("mod") == "parc"
    for block in A.get("blocks", []):
        poly = [tuple(p[:2]) for p in block.get("poligon") or []]
        if len(poly) < 3 or block.get("zona") == "apa":
            continue
        for i in block.get("suprafete", []):
            sf = A["suprafete"][i]
            if is_park(sf.get("tip")):
                add([tuple(p[:2]) for p in sf["poligon"]],
                    random.Random(seed * 7919 + block["id"] * 31 + len(sf["poligon"])), sf.get("poteci") != "manual")
        if block.get("valid") and is_park(block.get("zona")):
            add(poly, random.Random(seed * 1000 + block["id"]),
                (block.get("poteci") or (block.get("marcaj") or {}).get("poteci")) != "manual")
    return out


def analysis_for_web(plan, cladiri=False, name=None):
    A = G.analyze(plan)
    if cladiri:     # cladirile pe care le va pune generatorul (pagina le cere separat, cand te opresti din desenat)
        try:
            A["cladiri_auto"] = L.preview(plan, A)
        except Exception as error:  # noqa: BLE001 - analiza strazilor merge si fara
            A["cladiri_auto"] = []
            print(f"previzualizarea cladirilor a esuat: {error}")
        # aleile parcurilor, ale generatorului sau ale tale (unealta Carare din joc)
        A["carari"] = PP.load_carari(plan_path(name)) if name else []
        try:
            A["poteci"] = park_preview(plan, A, A["carari"])
        except Exception as error:  # noqa: BLE001
            A["poteci"] = []
            print(f"previzualizarea aleilor a esuat: {error}")
    if A["roads"]:
        grid = G.terrain(plan, A, step=8.0)
        A["teren"] = {"x0": grid["x0"], "y0": grid["y0"], "step": grid["step"],
                      "z": [[round(float(v), 2) for v in row] for row in grid["z"]]}
    for r in A["roads"].values():   # mai putine puncte si rotunjite: raspunsul ramane mic si pe planuri mari
        smp = r["samples"]
        r["samples"] = [[round(v, 2) for v in s[:3]] for s in smp[::3] + ([smp[-1]] if (len(smp) - 1) % 3 else [])]
        r["pts"] = [[round(p[0], 2), round(p[1], 2)] for p in r["pts"]]
    return A


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path == "/api/plans":
                names = sorted(p.relative_to(PLANS).with_suffix("").as_posix() for p in PLANS.rglob("*.json"))
                return self._send(200, {"plans": names})
            if u.path == "/api/plan":
                path = plan_path(q.get("name", ["oras"])[0])
                return self._send(200, json.loads(path.read_text(encoding="utf-8")) if path.is_file() else empty_plan())
            if u.path == "/api/log":
                start = int(q.get("from", ["0"])[0])
                with LOCK:
                    elapsed, eta = job_times()
                    return self._send(200, {"lines": JOB["lines"][start:], "total": len(JOB["lines"]),
                                            "running": JOB["proc"] is not None, "file": JOB["file"], "code": JOB["code"],
                                            "kind": JOB.get("kind"), "result": JOB.get("result"),
                                            "progress": JOB.get("progress"), "stage": JOB.get("stage", ""),
                                            "elapsed": round(elapsed, 1), "eta": None if eta is None else round(eta, 1),
                                            "stopped": JOB.get("stopped", False), "chain": JOB.get("chain", False)})
            if u.path == "/api/status":
                name = q.get("name", ["oras"])[0]
                path = plan_path(name)
                exp = PLANS / f"{path.stem}_export.json"
                cfg = server_cfg()
                plan = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
                res = resource_name(name, plan)
                listed = bool(cfg) and any(line.split("#")[0].split() == ["ensure", res]
                                           for line in cfg.read_text(encoding="utf-8", errors="replace").splitlines())
                # gen_oras.py scrie <nume>.blend direct in output/orase, si pentru planurile din subfoldere
                return self._send(200, {"blend": (PLANS / f"{path.stem}.blend").is_file(), "resursa": res,
                                        "export": json.loads(exp.read_text(encoding="utf-8")) if exp.is_file() else None,
                                        "server_cfg": str(cfg) if cfg else None, "in_cfg": listed,
                                        "joc_implicit": DEFAULT_JOC})
            if u.path == "/api/catalog":
                return self._send(200, {"cladiri": catalog()})
            if u.path == "/api/cladiri":
                # contururile cladirilor din ultima generare (gen_oras.py scrie <nume>_cladiri.json langa .blend)
                foot = PLANS / f"{plan_path(q.get('name', ['oras'])[0]).stem}_cladiri.json"
                return self._send(200, {"cladiri": json.loads(foot.read_text(encoding="utf-8")) if foot.is_file() else []})
            if u.path == "/api/carari":
                # cararile planului (<plan>_carari.json); joc=1 = in coordonatele din joc, pentru /mapeditor
                return self._send(200, carari_reply(q.get("name", ["oras"])[0], q.get("joc", ["0"])[0] == "1"))
            if u.path.startswith("/fundal/"):
                path = (BACKGROUNDS / Path(u.path[len("/fundal/"):]).name).resolve()
                if path.is_file():
                    return self._send(200, path.read_bytes(), MIME.get(path.suffix.lower(), "application/octet-stream"))
                return self._send(404, {"eroare": "imaginea nu exista"})
            path = (WEB / ("index.html" if u.path in ("", "/") else u.path.lstrip("/"))).resolve()
            if WEB.resolve() in path.parents and path.is_file():
                return self._send(200, path.read_bytes(), MIME.get(path.suffix, "application/octet-stream"))
            self._send(404, {"eroare": "nu exista"})
        except Exception as error:  # noqa: BLE001 - raspunsul catre pagina
            self._send(500, {"eroare": str(error)})

    def do_POST(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path == "/api/plan":
                path = plan_path(q.get("name", ["oras"])[0])
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(".tmp")
                tmp.write_text(json.dumps(self._body(), indent=1, ensure_ascii=False), encoding="utf-8")
                os.replace(tmp, path)
                return self._send(200, {"ok": True, "path": str(path)})
            if u.path == "/api/fundal":
                ext = IMAGE_EXT.get(self.headers.get("Content-Type", "").split(";")[0].strip())
                if ext is None:
                    return self._send(400, {"eroare": "doar imagini PNG, JPG, WEBP sau GIF"})
                data = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                BACKGROUNDS.mkdir(parents=True, exist_ok=True)
                name = Path(plan_path(q.get("name", ["oras"])[0]).stem).name + ext
                (BACKGROUNDS / name).write_bytes(data)
                return self._send(200, {"ok": True, "fisier": name})
            if u.path == "/api/analyze":
                return self._send(200, analysis_for_web(self._body(), q.get("cladiri", ["0"])[0] == "1",
                                                        q.get("name", [None])[0]))
            if u.path == "/api/carari":
                # unealta Carare din /mapeditor (prin rrp_mapeditor): adauga / sterge o carare, raspunde cu toate
                return self._send(200, carari_change(q.get("name", ["oras"])[0], self._body()))
            full = q.get("full", ["0"])[0] == "1"
            busy = {"eroare": "Blender lucreaza deja (generare sau export): asteapta sa termine"}
            if u.path == "/api/generate":
                if not start_job(generate_cmd(q.get("name", ["oras"])[0], full), "generate", keep_gen):
                    return self._send(409, busy)
                return self._send(200, {"ok": True})
            if u.path == "/api/export":
                cmd, keep, result, res, blend = export_job(q.get("name", ["oras"])[0], full)
                if not blend.is_file():
                    return self._send(404, {"eroare": "genereaza intai orasul"})
                if not start_job(cmd, "export", keep, result):
                    return self._send(409, busy)
                return self._send(200, {"ok": True, "resursa": res})
            if u.path == "/api/build":
                # Trimite in joc: generare (doar ce s-a schimbat), export (doar modelele schimbate), iar rrp_mapeditor
                # vede editor/export_done.json si reporneste harta in joc
                name = q.get("name", ["oras"])[0]
                cmd, keep, result, res, _blend = export_job(name, full)
                if not start_job(generate_cmd(name, full), "generate", keep_gen,
                                 then=lambda: start_job(cmd, "export", keep, result, chained=True)):
                    return self._send(409, busy)
                return self._send(200, {"ok": True, "resursa": res})
            if u.path == "/api/stop":
                # butonul Opreste: omoara Blender (si cmd-ul care l-a pornit); ce era scris inainte ramane
                with LOCK:
                    proc = JOB["proc"]
                    if proc is None:
                        return self._send(200, {"ok": True, "oprit": False})
                    JOB["stopped"] = True
                    JOB["lines"].append("Oprit de tine." + (" Resursa din FiveM e incompleta pana exporti din nou."
                                                            if JOB.get("kind") == "export" else ""))
                if not isinstance(proc, str):      # "porneste": run_job il opreste imediat ce exista
                    kill_tree(proc)
                return self._send(200, {"ok": True, "oprit": True})
            if u.path == "/api/servercfg":
                # adauga "ensure <resursa>" in server.cfg (o singura data), ca FiveM sa incarce orasul
                res = "".join(c for c in q.get("res", [""])[0] if c.isalnum() or c in "_-")
                cfg = server_cfg()
                if not res or cfg is None:
                    return self._send(404, {"eroare": "nu gasesc server.cfg (fivem_resources_dir in map.json)"})
                text = cfg.read_text(encoding="utf-8", errors="replace")
                if any(line.split("#")[0].split() == ["ensure", res] for line in text.splitlines()):
                    return self._send(200, {"ok": True, "adaugat": False, "path": str(cfg)})
                with cfg.open("a", encoding="utf-8") as fh:
                    fh.write(("" if text.endswith("\n") else "\n") + f"ensure {res}   # oras generat in editorul de oras\n")
                return self._send(200, {"ok": True, "adaugat": True, "path": str(cfg)})
            if u.path == "/api/open":
                name = Path(q.get("name", ["oras"])[0]).name
                with LOCK:
                    made = JOB["file"]
                blend = Path(made).with_suffix(".blend") if made else PLANS / f"{name}.blend"
                if not blend.is_file():
                    return self._send(404, {"eroare": "genereaza intai orasul"})
                # la deschidere aduce si ce ai schimbat in joc cu /mapeditor (colectia "Obiecte din joc")
                subprocess.Popen(["cmd", "/c", str(TOOLS / "_blender.bat"), str(blend), "-P",
                                  str(TOOLS / "import_din_joc.py"), "--", "--plan", str(plan_path(name))],
                                 cwd=ROOT, creationflags=NO_WINDOW)
                return self._send(200, {"ok": True})
            self._send(404, {"eroare": "nu exista"})
        except Exception as error:  # noqa: BLE001
            self._send(500, {"eroare": str(error)})


def main():
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"   # nu "localhost": pe Windows incearca intai IPv6 si pierde 2 s
    print(f"Editorul de oras: {url}  (inchide fereastra asta ca sa-l opresti)")
    if "--no-browser" not in sys.argv:
        webbrowser.open(url)
    server.serve_forever()


if __name__ == "__main__":
    main()

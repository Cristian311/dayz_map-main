"""Asezarea cladirilor pe cvartale, aceeasi pentru generator (tools/gen_oras.py, in Blender) si pentru editorul de
pe web (server.py o arata inainte de generare): Python pur, aceeasi zona + acelasi seed = aceleasi cladiri."""
import json
import math
import random

import plan_geom as G

# stilul fiecarei zone: cladirile variaza doar in latime, etaje (+-1), magazine si alei
ZONES = {
    "lc_caramida": {"mod": "rand", "tipuri": ["bloc"], "etaje": (4, 7), "adancime": (14.0, 18.0),
                    "latime": (8.0, 15.0), "alei": 0.12, "pereti": ["perete_caramida"], "magazine": 0.7,
                    "rezervor": 0.25, "scara": 0.75, "inaltime": (3.0, 3.2), "sol": "trotuar"},
    # turnurile din centru: hotel de caramida, birouri cu benzi de geam, sticla (blender_gen_buildings.build_tower)
    "centru": {"mod": "rand", "tipuri": ["turn", "turn", "bloc"], "stiluri": ["hotel", "birouri", "sticla"],
               "etaje": (10, 20), "adancime": (20.0, 28.0),
               "latime": (18.0, 30.0), "alei": 0.08, "pereti": ["perete_beton", "perete_vila"], "magazine": 0.9,
               "rezervor": 0.08, "scara": 0.0, "inaltime": (3.3, 3.5), "sol": "trotuar"},
    # blocurile-turn de caramida din Bohan / Bronx ("projects"): izolate, pe gazon, cu copaci intre ele
    "proiecte": {"mod": "case", "tipuri": ["bloc"], "etaje": (12, 18), "adancime": (15.0, 20.0),
                 "latime": (26.0, 40.0), "retragere": 9.0, "spatiu": (14.0, 22.0), "sol": "iarba",
                 "pereti": ["perete_caramida"], "magazine": 0.0, "rezervor": 0.1, "scara": 0.0, "copaci": 1.5},
    "suburbie": {"mod": "case", "tipuri": ["casa", "casa", "vila"], "etaje": (1, 2), "adancime": (9.0, 13.0),
                 "latime": (10.0, 16.0), "retragere": 6.0, "spatiu": (3.0, 6.0), "sol": "iarba", "copaci": 1.5},
    "industrial": {"mod": "case", "tipuri": ["hala"], "etaje": (1, 1), "adancime": (25.0, 38.0),
                   "latime": (20.0, 36.0), "retragere": 8.0, "spatiu": (6.0, 12.0), "sol": "asfalt"},
    # placa de sub parc e tot iarba: iarba GTA (normal.sps cu HardAlphaBlend) are gauri dupa alfa texturii, iar
    # prin ele se vedea trotuarul de dedesubt ca bucati de alee rupte
    "parc": {"mod": "parc", "sol": "iarba"},
    "piateta": {"mod": "piateta", "sol": "trotuar"},
    "parcare": {"mod": "parcare", "sol": "asfalt"},
    "sport": {"mod": "sport", "sol": "asfalt"},
    "gazon": {"mod": "gazon", "sol": "iarba"},
    "gol": {"mod": "gol", "sol": "trotuar"},
    "apa": {"mod": "apa", "sol": "trotuar"},
}


# "Magazine la parter" ales pe zona / cvartal in editorul web (marcajul de zona al cvartalului): cota blocurilor cu
# vitrine si firme; lipsa = cota tipului de zona ("magazine" din ZONES)
MAGAZINE = {"niciunul": 0.0, "unele": 0.5, "toate": 1.0}


def zone_for(block, Z=None):
    """Stilul zonei cvartalului, cu ce a ales utilizatorul pe marcajul lui (deocamdata: magazinele)."""
    if Z is None:
        Z = ZONES.get(block["zona"], ZONES["gol"]) if block.get("valid", True) else ZONES["gol"]
    pick = ((block.get("marcaj") or {}).get("magazine") or "")
    if pick in MAGAZINE:
        Z = dict(Z, magazine=MAGAZINE[pick])
    return Z


def rect(c, t, n, w, d):
    return [G.add(G.add(c, G.mul(t, sx * w / 2)), G.mul(n, sy * d / 2)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def overlap(A, B, tol=0.05):
    """Dreptunghiurile (colturi) se suprapun (cele doar lipite nu)."""
    for poly in (A, B):
        for i in range(4):
            e = G.sub(poly[(i + 1) % 4], poly[i])
            ax = G.norm((-e[1], e[0]))
            pa = [G.dot(p, ax) for p in A]
            pb = [G.dot(p, ax) for p in B]
            if max(pa) <= min(pb) + tol or max(pb) <= min(pa) + tol:
                return False
    return True


def poly_overlap(R, P):
    """Un poligon (dreptunghiul unei cladiri) se suprapune cu altul oarecare."""
    if any(G.inside(p, P) for p in R) or any(G.inside(p, R) for p in P):
        return True
    return any(G.seg_hit(a, b, c, d) for a, b in zip(R, R[1:] + R[:1]) for c, d in zip(P, P[1:] + P[:1]))


def in_rect(pt, b):
    v = G.sub(pt, b["c"])
    return abs(G.dot(v, b["t"])) < b["w"] / 2 and abs(G.dot(v, b["n"])) < b["d"] / 2


def seg_dist(p, a, b):
    ab = G.sub(b, a)
    t = max(0.0, min(1.0, G.dot(G.sub(p, a), ab) / max(G.dot(ab, ab), 1e-12)))
    return G.length(G.sub(p, G.add(a, G.mul(ab, t))))


def fast_inside(poly):
    """G.inside cu muchiile pregatite o data (acelasi rezultat): cvartalele de langa strazi curbe au sute de colturi,
    iar testul se face pentru fiecare colt al fiecarei cladiri incercate. In afara dreptunghiului poligonului: nu."""
    n = len(poly)
    edges = [(poly[i][0], poly[i][1], poly[(i + 1) % n][0], poly[(i + 1) % n][1]) for i in range(n)]
    x0, x1 = min(p[0] for p in poly), max(p[0] for p in poly)
    y0, y1 = min(p[1] for p in poly), max(p[1] for p in poly)

    def test(pt):
        x, y = pt[0], pt[1]
        if x < x0 or x > x1 or y < y0 or y > y1:
            return False
        hit = False
        for ax, ay, bx, by in edges:
            if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
                hit = not hit
        return hit
    return test


def fill_block(poly, Z, rng, tex, avoid=None, edges_on=None, heights=None):
    """Cladirile de pe marginile poligonului: fata spre strada, laturile lungi intai; ce nu incape, se suprapune
    sau cade pe ce e de ocolit (avoid(R)) se micsoreaza sau se sare. edges_on = conturul cvartalului: doar
    laturile de pe el primesc cladiri (o zona desenata in interiorul unui cvartal). Intoarce [{c, t, n, w, d, p}]."""
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    shrink = [(p[0] + (cx - p[0]) * 0.002, p[1] + (cy - p[1]) * 0.002) for p in poly]
    in_shrink = fast_inside(shrink)
    edges = sorted(((poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))),
                   key=lambda e: -G.length(G.sub(e[1], e[0])))
    if edges_on:
        ring = list(zip(edges_on, edges_on[1:] + edges_on[:1]))
        edges = [(a, b) for a, b in edges
                 if min(seg_dist(G.mul(G.add(a, b), 0.5), p, q) for p, q in ring) < 1.5]
    rand = Z["mod"] == "rand"
    setback = 0.3 if rand else Z["retragere"]
    base = rng.randint(*Z["etaje"])
    palette = rng.sample(Z.get("pereti", [None]), min(2, len(Z.get("pereti", [None]))))
    placed = []
    for a, b in edges:
        L = G.length(G.sub(b, a))
        if L < 7.0:
            continue
        t = G.norm(G.sub(b, a))
        n = G.left(t)
        u = 0.0 if rand else rng.uniform(1.0, 3.0)
        while u < L - 6.0:
            w = rng.uniform(*Z["latime"])
            if rand and L - u - w < 7.0:
                w = L - u
            w = min(w, L - u)
            d = rng.uniform(*Z["adancime"])
            fit = None
            for ww in (w, w * 0.75, w * 0.55):
                if ww < 6.0:
                    break
                for dd in (d, d * 0.75, d * 0.55):
                    if dd < 7.0:
                        break
                    c = G.add(G.add(a, G.mul(t, u + ww / 2)), G.mul(n, setback + dd / 2))
                    R = rect(c, t, n, ww, dd)
                    if (all(in_shrink(pt) for pt in R) and not any(overlap(R, o["R"]) for o in placed)
                            and not (avoid and avoid(R))):
                        fit = (ww, dd, c, R)
                        break
                if fit:
                    break
            if fit is None:
                u += 0.5
                continue
            ww, dd, c, R = fit
            tip = rng.choice(Z["tipuri"])
            floors = min(max(base + rng.choice((-1, 0, 0, 1)), Z["etaje"][0]), Z["etaje"][1])
            p = {"tip": tip, "latime": round(ww, 2), "adancime": round(dd, 2), "etaje": floors,
                 "inaltime": round(rng.uniform(*Z.get("inaltime", (3.0, 3.0))), 2) if rand else (heights or {}).get(tip, 3.0),
                 "acoperis": "plat" if rand else "auto", "interior": False,
                 "comercial": rng.random() < Z.get("magazine", 0.0), "texturi": tex, "seed": rng.randrange(1, 99999),
                 "perete": rng.choice(palette), "rezervor": Z.get("rezervor", 0.55),
                 "scara_incendiu": Z.get("scara", 0.75)}
            if tip == "turn":
                p["stil"] = rng.choice(Z.get("stiluri", ["hotel"]))
            placed.append({"c": c, "t": t, "n": n, "w": ww, "d": dd, "R": R, "p": p})
            u += ww + (rng.uniform(3.0, 5.0) if rand and rng.random() < Z.get("alei", 0.0)
                       else 0.0 if rand else rng.uniform(*Z["spatiu"]))
    if rand:
        for b in placed:
            b["p"]["lipit"] = [side for side, sgn in (("stanga", -1), ("dreapta", 1))
                               if any(in_rect(G.add(G.add(b["c"], G.mul(b["t"], sgn * (b["w"] / 2 + 0.3))),
                                                    G.mul(b["n"], k * b["d"])), o)
                                      for o in placed if o is not b for k in (-0.3, 0.0, 0.3))]
    return placed


# latime, adancime implicite (ca DEFAULTS din tools/blender_gen_buildings.py) pentru cladirile puse de mana
DEFAULT_SIZE = {"vila": (20.0, 13.0), "casa": (12.0, 9.0), "bloc": (16.0, 20.0), "magazin": (14.0, 12.0),
                "hala": (30.0, 40.0), "turn": (26.0, 24.0)}


def custom_rects(plan):
    """Cladirile puse de mana (plan["cladiri"]): dreptunghiul fiecareia, ocolit de cele generate."""
    out = []
    for k in plan.get("cladiri", []):
        ang = math.radians(float(k.get("r", -90.0)))
        nn = (-math.cos(ang), -math.sin(ang))
        tt = G.right(nn)
        if k.get("tip") == "gta":
            w, d = float(k.get("w", 12.0)), float(k.get("d", 12.0))
        else:
            q = k.get("p", {})
            tip = q.get("tip") if q.get("tip") in DEFAULT_SIZE else "bloc"
            w, d = float(q.get("latime", DEFAULT_SIZE[tip][0])), float(q.get("adancime", DEFAULT_SIZE[tip][1]))
        c = (float(k["x"]), float(k["y"]))
        out.append({"k": k, "c": c, "t": tt, "n": nn, "w": w, "d": d, "R": rect(c, tt, nn, w, d)})
    return out


def inner_roads(A, poly):
    """Strazile de la sol care intra in cvartal fara sa-l imparta: (puncte, jumatate de latime cu trotuar)."""
    out = []
    inside = fast_inside(poly)
    x0, x1 = min(p[0] for p in poly), max(p[0] for p in poly)
    y0, y1 = min(p[1] for p in poly), max(p[1] for p in poly)
    for r in A["roads"].values():
        if r["nivel"] != "sol" or not r["samples"]:
            continue
        pts = [(s[0], s[1]) for s in r["samples"]]
        if (max(p[0] for p in pts) < x0 or min(p[0] for p in pts) > x1
                or max(p[1] for p in pts) < y0 or min(p[1] for p in pts) > y1):
            continue
        if any(inside(p) for p in pts):
            out.append((pts, r["W"]))
    return out


_CACHE = {}     # asezarea fiecarui cvartal, dupa tot ce o schimba: la o strada mutata se refac doar cvartalele ei


def preview(plan, A):
    """Cladirile pe care le va pune generatorul, fara Blender: aceleasi cvartale, zone, seed-uri si ocoliri ca in
    gen_oras.py (fara coridoarele podurilor si tunelurilor). [{R, x, y, r, tip, w, d, etaje, comercial, sters}]"""
    seed = int(plan.get("seed", 1))
    removed = [tuple(p[:2]) for p in plan.get("cladiri_sterse", [])]
    waters = [s["poligon"] for s in A["suprafete"] if s["tip"] == "apa"]
    custom = custom_rects(plan)
    common = json.dumps([seed, waters, [cb["R"] for cb in custom]])

    def avoid_for(own, lines=()):
        # dreptunghiul fiecarei strazi din cvartal (cu marginea de ocolit): cele departe nu se mai masoara
        boxes = [(min(p[0] for p in road) - half - 1.0, min(p[1] for p in road) - half - 1.0,
                  max(p[0] for p in road) + half + 1.0, max(p[1] for p in road) + half + 1.0, road, half)
                 for road, half in lines]

        def avoid(R):
            cx, cy = sum(p[0] for p in R) / 4, sum(p[1] for p in R) / 4
            pts = R + [(cx, cy)] + [G.mul(G.add(p, q), 0.5) for p, q in zip(R, R[1:] + R[:1])]
            if any(G.inside(p, w) for w in waters for p in pts) or any(poly_overlap(R, o) for o in own):
                return True
            px0, px1 = min(p[0] for p in pts), max(p[0] for p in pts)
            py0, py1 = min(p[1] for p in pts), max(p[1] for p in pts)
            for bx0, by0, bx1, by1, road, half in boxes:
                if px1 < bx0 or px0 > bx1 or py1 < by0 or py0 > by1:
                    continue
                if any(seg_dist(p, a, b) < half + 1.0 for a, b in zip(road, road[1:]) for p in pts):
                    return True
            return any(poly_overlap(R, cb["R"]) for cb in custom)
        return avoid

    out = []

    def run(key, poly, Z, make_rng, make_avoid, edges_on=None):
        key = common + key
        if key not in _CACHE:
            if len(_CACHE) > 4000:
                _CACHE.clear()
            rows = []
            for b in fill_block(poly, Z, make_rng(), None, make_avoid(), edges_on):
                c, n, p = b["c"], b["n"], b["p"]
                rows.append({"R": [[round(x, 1), round(y, 1)] for x, y in b["R"]], "x": round(c[0], 1),
                             "y": round(c[1], 1), "r": round(math.degrees(math.atan2(-n[1], -n[0])), 1), "tip": p["tip"],
                             "w": round(b["w"], 1), "d": round(b["d"], 1), "etaje": p["etaje"],
                             "comercial": bool(p["comercial"])})
            _CACHE[key] = rows
        for row in _CACHE[key]:
            out.append(dict(row, sters=any(G.inside(pt, row["R"]) for pt in removed)))

    for block in A["blocks"]:
        poly = [tuple(p) for p in block["poligon"]]
        if len(poly) < 3 or block["zona"] == "apa":
            continue
        Z = zone_for(block)
        areas = [A["suprafete"][i] for i in block.get("suprafete", [])]
        for sf in areas:
            Zs = ZONES.get(sf["tip"], ZONES["gol"])
            if Zs["mod"] in ("rand", "case"):
                sp = [tuple(p) for p in sf["poligon"]]
                run(json.dumps(["s", block["id"], sf["tip"], sp, poly]), sp, Zs,
                    lambda sf=sf, bid=block["id"]: random.Random(seed * 7919 + bid * 31 + len(sf["poligon"])),
                    lambda: avoid_for([]), poly)
        if not block["valid"] or Z["mod"] not in ("rand", "case"):
            continue
        inner = inner_roads(A, poly)
        holes = [a["poligon"] for a in areas]
        run(json.dumps(["b", block["id"], block["zona"], poly, holes, inner]), poly, Z,
            lambda bid=block["id"]: random.Random(seed * 1000 + bid), lambda: avoid_for(holes, inner))
    return out

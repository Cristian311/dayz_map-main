# -*- coding: utf-8 -*-
"""
Geometria unui plan de oras desenat in editor (output/orase/<nume>.json): strazi in orice unghi, intersectii,
cvartale, pante, teren, avertismente. Python pur (numpy doar pentru teren), folosit si de serverul editorului
(previzualizare), si de tools/gen_oras.py in Blender (generare), deci editorul arata exact ce se construieste.

Planul:
    {"nodes": [{"id", "x", "y", "z"}], "roads": [{"id", "a", "b", "tip", "puncte": [[x, y]]}],
     "zones": [{"x", "y", "tip", ...}], "altitudini": [{"x", "y", "z"}], "panta_max": 0.10,
     "zona_implicita": "lc_caramida"}

analyze(plan) -> dict (doar liste si numere, se poate trimite ca JSON):
    roads      {id: tip, r, s, W, pts (centrul), L, s0, s1 (portiunea dintre intersectii), samples, panta}
    junctions  {nod: x, y, z, asfalt (poligon), trotuare [{poligon, bordura}], brate [{road, E, e, h, W, zebra}]}
    blocks     [{id, poligon, zona, arie, valid, marcaj}]
    warnings   [{tip, mesaj, x, y}]
    bounds     [x0, y0, x1, y1]
"""
import bisect
import math

ROAD_TYPES = {"strada": {"r": 8.0, "s": 3.0, "raza": 6.0, "benzi": 1, "marcaj": True},
              "artera": {"r": 14.0, "s": 3.5, "raza": 8.0, "benzi": 2, "marcaj": True},
              "alee": {"r": 5.0, "s": 1.5, "raza": 4.0, "benzi": 1, "marcaj": False}}
ZEBRA = 3.0          # adancimea trecerii de pietoni de la capatul fiecarui brat
# natura: se deseneaza oriunde (si departe de strazi), nu devine cvartal; harta se intinde pana la ea
NATURAL = ("plaja", "camp", "padure")
SHORE_LAND = 35.0    # plaja / malul natural: pe cel putin atatia metri terenul coboara lin spre apa,
SHORE_GRADE = 0.10   # cu panta medie asta (orasul sta implicit la 25 m peste mare: coasta de ~250 m, nu faleza),
SHORE_MAX = 320.0    # dar nu mai departe de atat de apa
SHORE_SLOPE = 0.12   # si sub apa fundul coboara cu panta asta pana la fundul obisnuit (nu zid de chei)
MIN_ANGLE = 25.0     # grade intre doua strazi care pleaca din acelasi nod
MERGE_DIST = 6.0     # m: doua noduri legate de o strada mai scurta de atat devin unul (vezi analyze)
MIN_ROAD = 2.0       # m de strada care raman intre doua intersectii (colturile se strang daca e nevoie)
MIN_BLOCK = 60.0     # m2, sub asta cvartalul nu se umple
CLEARANCE = 4.5      # m intre doua strazi care se trec una peste alta fara intersectie (pod / tunel)
# inaltimile calculate singure pentru capetele "pe teren" ale podurilor si tunelurilor (auto_heights)
BRIDGE_CLEAR = 6.6   # m de la strada de dedesubt la asfaltul podului: 5.5 m gabarit + 1.1 m grosimea podului
TUNNEL_COVER = 8.0   # m de la strada de deasupra la asfaltul tunelului: 6.5 m inaltime libera + tavan si pamant
WATER_CLEAR = 7.0    # m peste nivelul marii, pentru podurile peste apa
SEA_Z = 25.0         # implicit: orasul (z = 0) sta la 25 m deasupra marii (valurile din larg trec de 3-4 m)
AREA_TYPES = ("parc", "piateta", "parcare", "sport", "gazon", "apa")


def road_types(plan):
    """Tipurile de strada: cele trei de baza plus profilurile facute in editor (plan["profile"]).
    Un profil: carosabil (m, cu mediana si parcarile), trotuar, benzi pe sens, parcare (bool), mediana (m),
    mediana_tip (iarba / beton), marcaj, copaci (pe trotuar), stalpi (m intre stalpi, 0 = fara)."""
    out = {k: dict(v) for k, v in ROAD_TYPES.items()}
    for k, t in (plan.get("profile") or {}).items():
        try:
            r, s = max(3.0, float(t.get("carosabil", 8.0))), max(0.5, float(t.get("trotuar", 3.0)))
        except (TypeError, ValueError):
            continue
        out[k] = {"r": r, "s": s, "raza": float(t.get("raza") or min(10.0, max(4.0, r / 2 + 2.0))),
                  "benzi": int(t.get("benzi", 1)), "parcare": bool(t.get("parcare")),
                  "mediana": float(t.get("mediana", 0.0) or 0.0), "mediana_tip": t.get("mediana_tip", "iarba"),
                  "marcaj": bool(t.get("marcaj", True)), "copaci": bool(t.get("copaci")),
                  "stalpi": float(t.get("stalpi", 28.0) or 0.0), "nume": t.get("nume", k)}
    return out


def painted(plan):
    """Terenul pictat cu pensula din editor (plan["teren"] = {x0, y0, step, nx, ny, h: lista pe randuri}) ca
    functie h(x, y), interpolata biliniar; in afara lui 0. Fara teren pictat: None."""
    t = plan.get("teren")
    if not t or not t.get("h"):
        return None
    x0, y0, s, nx, ny, H = float(t["x0"]), float(t["y0"]), float(t["step"]), int(t["nx"]), int(t["ny"]), t["h"]

    def h(x, y):
        fx, fy = (x - x0) / s, (y - y0) / s
        if fx < 0 or fy < 0 or fx > nx - 1 or fy > ny - 1:
            return 0.0
        i, j = min(int(fx), nx - 2), min(int(fy), ny - 2)
        tx, ty = fx - i, fy - j
        return (H[j * nx + i] * (1 - tx) * (1 - ty) + H[j * nx + i + 1] * tx * (1 - ty)
                + H[(j + 1) * nx + i] * (1 - tx) * ty + H[(j + 1) * nx + i + 1] * tx * ty)
    return h


def node_heights(plan):
    """{nod: z}. Nodurile "auto" (implicit la cele noi) stau pe terenul pictat; celelalte au inaltimea scrisa
    (poduri, rampe, planuri vechi)."""
    h = painted(plan)
    out = {}
    for n in plan.get("nodes", []):
        if n.get("auto") or "z" not in n:
            out[n["id"]] = round(h(n["x"], n["y"]), 2) if h else 0.0
        else:
            out[n["id"]] = float(n.get("z", 0.0))
    return out


def sea_level(plan):
    """Nivelul marii in coordonatele planului (orasul e la joc.z metri deasupra ei)."""
    return -float((plan.get("joc") or {}).get("z", SEA_Z))


def clamp_inside(p, poly, margin):
    """Punctul p adus in poligon (sens trigonometric), la cel putin `margin` m de margine. Langa un colt, o
    singura mutare il lasa pe latura vecina: se repeta pana e inauntru."""
    p = tuple(p)
    for _ in range(4):
        best = None
        for a, b in zip(poly, poly[1:] + poly[:1]):
            ab = sub(b, a)
            t = max(0.0, min(1.0, dot(sub(p, a), ab) / max(dot(ab, ab), 1e-12)))
            q = add(a, mul(ab, t))
            d = length(sub(p, q))
            if best is None or d < best[0]:
                best = (d, q, ab)
        if inside(p, poly) and best[0] >= margin - 1e-6:
            return p
        p = add(best[1], mul(left(norm(best[2])), margin))
    return p


# ------------------------------------------------------------------------------------------ vectori (tupluri)

def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def run_u(trim, step=1.0):
    """Distantele de la nod ale punctelor lui offset_run."""
    return [k * step for k in range(int(trim / step) + 1) if k * step < trim] + [trim]


def offset_run(road, at_a, trim, W, side, step=1.0):
    """Marginea exterioara a trotuarului de pe un brat: puncte la W de ax (side 1 = stanga bratului, -1 = dreapta),
    de la nod pana la capatul bratului (trim), la fiecare `step` m, deci si pe strazile curbe."""
    out = []
    for u in run_u(trim, step):
        E, d = road.point_at(u if at_a else road.L - u)
        e = d if at_a else mul(d, -1)
        out.append(add(E, mul(left(e) if side > 0 else right(e), W)))
    return out


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def mul(a, k):
    return (a[0] * k, a[1] * k)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def length(a):
    return math.hypot(a[0], a[1])


def norm(a):
    n = length(a)
    return (a[0] / n, a[1] / n) if n > 1e-12 else (1.0, 0.0)


def left(d):
    return (-d[1], d[0])


def right(d):
    return (d[1], -d[0])


def angle(d):
    return math.atan2(d[1], d[0])


def line_hit(p, d, q, e):
    """Parametrul t pe dreapta p + t*d unde o taie dreapta q + u*e (None daca sunt paralele)."""
    c = cross(d, e)
    if abs(c) < 1e-9:
        return None
    return cross(sub(q, p), e) / c


def seg_hit(a, b, c, d):
    """Punctul in care segmentele ab si cd se taie strict in interior (None altfel)."""
    r, s = sub(b, a), sub(d, c)
    den = cross(r, s)
    if abs(den) < 1e-12:
        return None
    t, u = cross(sub(c, a), s) / den, cross(sub(c, a), r) / den
    if 1e-6 < t < 1 - 1e-6 and 1e-6 < u < 1 - 1e-6:
        return add(a, mul(r, t))
    return None


def area(poly):
    return 0.5 * sum(cross(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def ccw(poly):
    return poly if area(poly) >= 0 else poly[::-1]


def inside(pt, poly):
    x, y, hit = pt[0], pt[1], False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


def _boxes(pts, closed):
    n = len(pts)
    m = n if closed else n - 1
    return [(min(pts[i][0], pts[(i + 1) % n][0]), min(pts[i][1], pts[(i + 1) % n][1]),
             max(pts[i][0], pts[(i + 1) % n][0]), max(pts[i][1], pts[(i + 1) % n][1])) for i in range(m)]


def simple(poly):
    """Poligonul nu se autointersecteaza (verificare cu cutii, suficient de rapida pentru cateva sute de laturi)."""
    n = len(poly)
    edges = [(poly[i], poly[(i + 1) % n]) for i in range(n)]
    boxes = _boxes(poly, True)
    order = sorted(range(n), key=lambda i: boxes[i][0])
    for oi, i in enumerate(order):     # baleiere dupa x: se compara doar laturile care se suprapun pe x
        bi = boxes[i]
        for j in order[oi + 1:]:
            bj = boxes[j]
            if bj[0] > bi[2]:
                break
            if abs(i - j) < 2 or abs(i - j) == n - 1 or bi[3] < bj[1] or bj[3] < bi[1]:
                continue
            if seg_hit(*edges[i], *edges[j]):
                return False
    return True


def untangle(poly, window=90, max_iter=40):
    """Taie buclele mici pe care le face o polilinie curba mutata spre interior langa un colt ascutit: unde doua
    laturi apropiate (in ordine) se taie, varfurile dintre ele dispar si raman cu punctul de intersectie."""
    for _ in range(max_iter):
        n = len(poly)
        if n < 4:
            return poly
        found = None
        boxes = _boxes(poly, True)
        for i in range(n):
            bi = boxes[i]
            for k in range(2, min(window, n - 1)):
                j = (i + k) % n
                bj = boxes[j]
                if bi[2] < bj[0] or bj[2] < bi[0] or bi[3] < bj[1] or bj[3] < bi[1]:
                    continue
                h = seg_hit(poly[i], poly[(i + 1) % n], poly[j], poly[(j + 1) % n])
                if h:
                    found = (i, k, h)
                    break
            if found:
                break
        if not found:
            return poly
        i, k, h = found
        rot = poly[i + 1:] + poly[:i + 1]          # rot[-1] = poly[i], rot[0..k-1] = bucla
        poly = [h] + rot[k:]
    return poly


def arc_points(center, r, a0, a1, step_deg=10.0):
    """Puncte pe arc de la unghiul a0 la a1, pe drumul cel mai scurt."""
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    n = max(1, int(abs(math.degrees(da)) / step_deg))
    return [(center[0] + r * math.cos(a0 + da * k / n), center[1] + r * math.sin(a0 + da * k / n))
            for k in range(n + 1)]


def spline(pts, step=1.0):
    """Centrul strazii: drept intre capete sau curba Catmull-Rom prin punctele de forma, esantionata la ~step m."""
    pts = [tuple(p) for p in pts]
    if len(pts) == 2:
        return pts
    P = [pts[0]] + pts + [pts[-1]]
    out = [pts[0]]
    for k in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[k - 1], P[k], P[k + 1], P[k + 2]
        n = max(2, int(math.ceil(length(sub(p2, p1)) / step)))
        for m in range(1, n + 1):
            t = m / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[i] + (p2[i] - p0[i]) * t + (2 * p0[i] - 5 * p1[i] + 4 * p2[i] - p3[i]) * t2
                                    + (3 * p1[i] - p0[i] - 3 * p2[i] + p3[i]) * t3) for i in (0, 1)))
    return out


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------------------------------ strazi

class Road:
    def __init__(self, data, nodes, types=None):
        types = types or ROAD_TYPES
        self.id, self.a, self.b = data["id"], data["a"], data["b"]
        self.tip = data.get("tip", "strada") if data.get("tip") in types else "strada"
        t = dict(types[self.tip])
        # "benzi" pe strada (editor: Benzi pe sens) schimba latimea reala: pastreaza latimea unei benzi a tipului
        # (cel mult 3.5 m cand adaugi benzi), parcarile si mediana raman
        try:
            benzi = int(data.get("benzi") or 0)
        except (TypeError, ValueError):
            benzi = 0
        if 1 <= benzi <= 4 and benzi != int(t.get("benzi", 1)):
            extra = (4.8 if t.get("parcare") else 0.0) + float(t.get("mediana", 0.0) or 0.0)
            banda = (t["r"] - extra) / (2 * max(1, int(t.get("benzi", 1))))
            banda = max(2.75, min(3.5, banda) if benzi > int(t.get("benzi", 1)) else banda)
            t["benzi"], t["r"] = benzi, round(2 * benzi * banda + extra, 2)
            t["raza"] = min(10.0, max(t["raza"], t["r"] / 2 + 2.0))
        self.t = t
        self.r, self.s, self.raza = t["r"], t["s"], t["raza"]
        self.nivel = data.get("nivel") if data.get("nivel") in ("pod", "tunel") else "sol"
        # marcajele puse pe strada in editor (linia din mijloc, benzi, sageti, stop, trecere, parcare, bordura);
        # {} = ce da tipul strazii. Vezi gen_oras.profile_for / road_marks.
        self.marcaje = data.get("marcaje") if isinstance(data.get("marcaje"), dict) else {}
        self.h, self.W = self.r / 2, self.r / 2 + self.s
        na, nb = nodes[self.a], nodes[self.b]
        self.pts = spline([(na["x"], na["y"])] + [tuple(p) for p in data.get("puncte", [])] + [(nb["x"], nb["y"])])
        self.cum = [0.0]
        for p, q in zip(self.pts, self.pts[1:]):
            self.cum.append(self.cum[-1] + length(sub(q, p)))
        self.L = self.cum[-1]
        self.za, self.zb = float(na.get("z", 0.0)), float(nb.get("z", 0.0))
        self.s0, self.s1 = 0.0, self.L
        # terenul pictat h(x, y), la strazile de sol cu capetele pe teren: strada urca si coboara cu el si pe
        # lungimea ei, nu doar intre intersectii (pus de analyze); None = doar curba dintre capete
        self.ground_h = None

    def point_at(self, s):
        """(punct, directie) la s metri de la capatul a."""
        s = min(max(s, 0.0), self.L)
        k = min(max(bisect.bisect_right(self.cum, s) - 1, 0), len(self.pts) - 2)
        p, q = self.pts[k], self.pts[k + 1]
        seg = self.cum[k + 1] - self.cum[k]
        t = (s - self.cum[k]) / seg if seg > 1e-9 else 0.0
        return add(p, mul(sub(q, p), t)), norm(sub(q, p))

    def follows(self):
        return self.ground_h is not None and self.s1 - self.s0 >= 20.0

    def _profile(self):
        """Profilul unei strazi pe teren, din 2 in 2 m: terenul mediat pe 12 m (estompat spre capete, unde strada
        intra la inaltimea intersectiei), cu panta taiata la gmax (inainte si inapoi, capetele fixe), apoi netezit.
        -> (s0, pas, [z]); refacut doar cand se schimba capetele."""
        key = (self.s0, self.s1, self.za, self.zb)
        if getattr(self, "_prof_key", None) == key:
            return self._prof
        span = self.s1 - self.s0
        n = max(2, int(math.ceil(span / 2.0)))
        ds = span / n
        z = []
        for k in range(n + 1):
            s = self.s0 + ds * k
            hs = sum(self.ground_h(*self.point_at(s + d)[0]) for d in (-6.0, -3.0, 0.0, 3.0, 6.0)) / 5.0
            base = self.za + (self.zb - self.za) * smooth(k / n)
            z.append(base + (hs - base) * smooth(min(s - self.s0, self.s1 - s) / 10.0))
        for _ in range(2):      # fara frangeri: media pe 10 m, inainte de taiere (taierea ramane ultima: panta sigura)
            z = [z[0]] + [sum(z[max(0, k - 2):k + 3]) / len(z[max(0, k - 2):k + 3]) for k in range(1, n)] + [z[-1]]
        step = self.gmax * ds
        for _ in range(3):
            z[0] = self.za
            for k in range(1, n + 1):
                z[k] = min(max(z[k], z[k - 1] - step), z[k - 1] + step)
            z[-1] = self.zb
            for k in range(n - 1, -1, -1):
                z[k] = min(max(z[k], z[k + 1] - step), z[k + 1] + step)
        z[0] = self.za
        self._prof_key, self._prof = key, (self.s0, ds, z)
        return self._prof

    def z_at(self, s):
        """Urcare lina intre intersectii (plat la capete, unde strada intra in intersectie); pe teren strada
        urmeaza si dealurile dintre ele (_profile)."""
        span = self.s1 - self.s0
        if not self.follows():
            return self.za + (self.zb - self.za) * smooth((s - self.s0) / span if span > 1e-6 else 0.0)
        s0, ds, z = self._profile()
        f = min(max((s - s0) / ds, 0.0), len(z) - 1.0)
        k = min(int(f), len(z) - 2)
        return z[k] + (z[k + 1] - z[k]) * (f - k)

    def arm_dir(self, at_a):
        """Directia strazii cand pleaca din nodul a (at_a) sau b, masurata pe primii metri."""
        d = min(3.0, self.L * 0.3)
        if at_a:
            return norm(sub(self.point_at(d)[0], self.pts[0]))
        return norm(sub(self.point_at(self.L - d)[0], self.pts[-1]))

    def grade(self):
        """Panta cea mai mare a strazii (1.5 = panta maxima a curbei line dintre capete)."""
        span = self.s1 - self.s0
        if span <= 1e-6:
            return 0.0
        if not self.follows():
            return 1.5 * abs(self.zb - self.za) / span
        _s0, ds, z = self._profile()
        return max(abs(b - a) for a, b in zip(z, z[1:])) / ds

    def samples(self, step=1.0):
        """[x, y, z, tx, ty, s] intre s0 si s1: pe drepte doar la ~step m ca sa urmeze panta."""
        n = max(1, int(math.ceil((self.s1 - self.s0) / step)))
        out = []
        for k in range(n + 1):
            s = self.s0 + (self.s1 - self.s0) * k / n
            p, d = self.point_at(s)
            out.append([p[0], p[1], self.z_at(s), d[0], d[1], s])
        return out

    def half(self, forward):
        """Polilinia strazii in sensul a -> b (forward) sau invers."""
        return self.pts if forward else self.pts[::-1]


# ------------------------------------------------------------------------------------------ analiza

def simplify(poly, tol=0.3):
    """Douglas-Peucker pe un poligon inchis: o latura dreapta luata la fiecare 2 m ramane o singura latura (cladirile
    se pun doar pe laturi de cel putin 7 m), pe curbe raman colturile care conteaza."""
    if len(poly) < 4:
        return poly

    def dp(pts):
        if len(pts) < 3:
            return pts
        a, b = pts[0], pts[-1]
        ab = sub(b, a)
        L = length(ab)
        best, idx = -1.0, 0
        for i in range(1, len(pts) - 1):
            d = abs(cross(ab, sub(pts[i], a))) / L if L > 1e-9 else length(sub(pts[i], a))
            if d > best:
                best, idx = d, i
        if best <= tol:
            return [a, b]
        return dp(pts[:idx + 1])[:-1] + dp(pts[idx:])

    k = max(range(len(poly)), key=lambda i: length(sub(poly[i], poly[0])))     # al doilea capat al impartirii
    return dp(list(poly[:k + 1]))[:-1] + dp(list(poly[k:]) + [poly[0]])[:-1]


def free_area(pts, roads, gap=0.3):
    """Suprafata desenata in afara cvartalelor (o zona de cladiri, un parc la marginea orasului): conturul, luat la
    fiecare 2 m, se lipeste de marginea trotuarului unde intra peste o strada (si pe strazile curbe). None daca
    suprafata trece peste o strada, e prea mica sau se autointersecteaza."""
    near = []
    for r in roads.values():
        if r.nivel != "sol" or len(r.pts) < 2:
            continue
        reach = r.W + gap
        near.append((min(p[0] for p in r.pts) - reach, min(p[1] for p in r.pts) - reach,
                     max(p[0] for p in r.pts) + reach, max(p[1] for p in r.pts) + reach, r, reach))
    cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    dense = []
    for p, q in zip(pts, pts[1:] + pts[:1]):
        n = max(1, int(length(sub(q, p)) / 2.0))
        dense += [add(p, mul(sub(q, p), k / n)) for k in range(n)]
    out = []
    for p in dense:
        for _ in range(3):      # impins de pe o strada, poate cadea pe alta (colt de intersectie)
            hit = None
            for x0, y0, x1, y1, r, reach in near:
                if not (x0 <= p[0] <= x1 and y0 <= p[1] <= y1):
                    continue
                for a, b in zip(r.pts, r.pts[1:]):
                    ab = sub(b, a)
                    t = max(0.0, min(1.0, dot(sub(p, a), ab) / max(dot(ab, ab), 1e-12)))
                    q = add(a, mul(ab, t))
                    d = length(sub(p, q))
                    if d < reach and (hit is None or d < hit[0]):
                        hit = (d, q, reach)
            if hit is None:
                break
            d, q, reach = hit
            away = norm(sub(p, q)) if d > 1e-6 else norm(sub((cx, cy), q))
            p = add(q, mul(away, reach))
        out.append(p)
    clean = [out[0]]
    for p in out[1:]:
        if length(sub(p, clean[-1])) > 0.2:
            clean.append(p)
    if len(clean) < 3:
        return None
    poly = ccw(simplify(untangle(clean)))
    if len(poly) < 3 or area(poly) < MIN_BLOCK or not simple(poly):
        return None
    if any(inside(p, poly) for _x0, _y0, _x1, _y1, r, _reach in near for p in r.pts[::4]):
        return None             # o strada trece prin ea: nu se poate lipi de o singura parte
    return poly


def _crossing(r, g):
    """Primul punct unde strada r o taie pe g (fara nod comun): (punct, metri pe g de la capatul ei a) sau None."""
    x0, x1 = min(p[0] for p in g.pts), max(p[0] for p in g.pts)
    y0, y1 = min(p[1] for p in g.pts), max(p[1] for p in g.pts)
    for p, q in zip(r.pts, r.pts[1:]):
        if max(p[0], q[0]) < x0 or min(p[0], q[0]) > x1 or max(p[1], q[1]) < y0 or min(p[1], q[1]) > y1:
            continue
        for j, (u, v) in enumerate(zip(g.pts, g.pts[1:])):
            h = seg_hit(p, q, u, v)
            if h:
                return h, g.cum[j] + length(sub(h, u))
    return None


def auto_heights(plan, roads, nodes, warn):
    """Podurile si tunelurile cu capetele "pe teren" (fara inaltime aleasa): nodurile lor urca cat trebuie ca strada
    sa treaca cu BRIDGE_CLEAR peste strazile de sol si apa pe care le taie (tunelul: coboara TUNNEL_COVER sub ele);
    un pod fara nimic dedesubt ia inaltimea podului vecin (tablier drept). Rampele (strazile de sol legate de un nod
    ridicat) se verifica la panta maxima, cu lungimea de care ar avea nevoie. -> ({nod: z}, {strazi rampa})."""
    auto = {n["id"] for n in plan.get("nodes", []) if n.get("auto") or "z" not in n}
    waters = [ccw([tuple(p) for p in sf.get("puncte", [])]) for sf in plan.get("suprafete", [])
              if sf.get("tip") == "apa" and len(sf.get("puncte", [])) >= 3]
    ground = [g for g in roads.values() if g.nivel == "sol"]
    need = {}
    for r in roads.values():
        if r.nivel == "sol" or not ({r.a, r.b} & auto):
            continue
        up = r.nivel == "pod"
        req = None
        for g in ground:
            if {g.a, g.b} & {r.a, r.b}:
                continue
            hit = _crossing(r, g)
            if hit is None:
                continue
            z = g.z_at(hit[1]) + (BRIDGE_CLEAR if up else -TUNNEL_COVER)
            req = z if req is None else (max(req, z) if up else min(req, z))
        if up:
            for w in waters:
                edges = list(zip(w, w[1:] + w[:1]))
                if any(inside(p, w) for p in r.pts) or any(seg_hit(p, q, u, v) for p, q in zip(r.pts, r.pts[1:])
                                                           for u, v in edges):
                    z = sea_level(plan) + WATER_CLEAR
                    req = z if req is None else max(req, z)
        if req is None:
            continue
        for n in (r.a, r.b):
            if n in auto and n in nodes:
                need[n] = req if n not in need else (max(need[n], req) if up else min(need[n], req))
    # tablier drept: o bucata de pod / tunel fara nimic dedesubt ia inaltimea capatului deja calculat
    for _ in range(len(roads)):
        grew = False
        for r in roads.values():
            if r.nivel == "sol":
                continue
            for x, y in ((r.a, r.b), (r.b, r.a)):
                if x in need and y in auto and y not in need and y in nodes:
                    need[y] = need[x]
                    grew = True
        if not grew:
            break
    for nid, z in need.items():
        nodes[nid]["z"] = round(z, 2)
    for r in roads.values():
        r.za, r.zb = float(nodes[r.a]["z"]), float(nodes[r.b]["z"])
    ramps = set()
    pmax = plan.get("panta_max", 0.10)
    for g in ground:
        if (g.a in need or g.b in need) and g.L > 1e-6:
            dz = abs(g.zb - g.za)
            if 1.5 * dz / g.L > pmax + 1e-9:
                ramps.add(g.id)
                warn("rampa", f"rampa {g.id} urca {dz:.1f} m pe {g.L:.0f} m: la panta de {pmax * 100:.0f}% ii trebuie "
                     f"~{1.5 * dz / pmax:.0f} m (lungeste-o sau muta mai departe nodul de jos)", g.point_at(g.L / 2)[0])
    return {n: round(z, 2) for n, z in need.items()}, ramps


def relax_nodes(roads, z, gmax):
    """Intersectiile sunt plate: doua apropiate, pe panta, lasa strazii dintre ele prea putin loc sa urce. Se
    apropie una de alta pana strada incape in panta (portiunea ei reala, s0..s1; curba lina scurta urca de 1.5 ori
    mai abrupt decat media). Repetat: un nod are mai multe strazi. z = {nod: inaltime}, schimbat pe loc -> mutate."""
    moved = set()
    for _ in range(60):
        changed = False
        for r in roads:
            span = r.s1 - r.s0
            room = gmax * span / (1.5 if span < 20.0 else 1.05)
            over = abs(z[r.b] - z[r.a]) - room
            if over > 0.01:
                d = over / 2 * (1.0 if z[r.b] > z[r.a] else -1.0)
                z[r.a] += d
                z[r.b] -= d
                moved.update((r.a, r.b))
                changed = True
        if not changed:
            break
    return moved


def analyze(plan, _fix=None):
    """_fix = {nod: z} de la relax_nodes (a doua trecere, pe teren pictat)."""
    warnings = []

    def warn(tip, msg, pt):
        warnings.append({"tip": tip, "mesaj": msg, "x": round(pt[0], 2), "y": round(pt[1], 2)})

    zs = node_heights(plan)
    if _fix:
        zs.update(_fix)
    nodes = {n["id"]: dict(n, z=zs[n["id"]]) for n in plan.get("nodes", [])}
    types = road_types(plan)
    # doua noduri la cativa metri unul de altul, legate de o strada dreapta, la aceeasi inaltime: devin un singur
    # nod (la mijloc). Altfel cele doua intersectii se suprapun si trotuarele lor se amesteca.
    alias = {}

    def root(nid):
        while nid in alias:
            nid = alias[nid]
        return nid

    for rd in plan.get("roads", []):
        a, b = root(rd.get("a")), root(rd.get("b"))
        if a not in nodes or b not in nodes or a == b or rd.get("puncte"):
            continue
        na, nb = nodes[a], nodes[b]
        # sub 1 m strada e oricum ignorata (L < 1), iar nodurile suprapuse raman ca pana acum
        if 1.0 <= math.hypot(na["x"] - nb["x"], na["y"] - nb["y"]) < MERGE_DIST and abs(na["z"] - nb["z"]) < 1.0:
            alias[b] = a
            nodes[a] = dict(na, x=(na["x"] + nb["x"]) / 2, y=(na["y"] + nb["y"]) / 2, z=(na["z"] + nb["z"]) / 2)
    roads = {}
    for rd in plan.get("roads", []):
        if rd.get("a") not in nodes or rd.get("b") not in nodes:
            continue
        if alias:
            rd = dict(rd, a=root(rd["a"]), b=root(rd["b"]))
            if rd["a"] == rd["b"] and not rd.get("puncte"):
                continue            # strada de cativa metri dintre doua noduri unite
        if rd["a"] == rd["b"]:
            warn("strada", "strada care pleaca si ajunge in acelasi nod (ignorata)", (nodes[rd["a"]]["x"], nodes[rd["a"]]["y"]))
            continue
        road = Road(rd, nodes, types)
        if road.L < 1.0:
            continue
        roads[road.id] = road
    # podurile si tunelurile cu capetele pe teren: inaltimea lor se calculeaza din ce trece dedesubt / deasupra
    bridge_z, ramps = auto_heights(plan, roads, nodes, warn)
    zs.update(bridge_z)
    # strazile de sol cu ambele capete pe teren (nu si rampele podurilor) urmeaza terenul pictat pe toata lungimea
    h_ground = painted(plan)
    followers, gmax = [], plan.get("panta_max", 0.10) * 0.9
    if h_ground:
        on_ground = {n["id"] for n in plan.get("nodes", []) if n.get("auto") or "z" not in n}
        for road in roads.values():
            if (road.nivel == "sol" and road.a in on_ground and road.b in on_ground
                    and road.a not in bridge_z and road.b not in bridge_z):
                road.ground_h, road.gmax = h_ground, gmax
                followers.append(road)

    # bratele fiecarui nod, sortate trigonometric
    arms = {nid: [] for nid in nodes}
    for road in roads.values():
        arms[road.a].append({"road": road, "at_a": True, "d": road.arm_dir(True)})
        arms[road.b].append({"road": road, "at_a": False, "d": road.arm_dir(False)})
    for lst in arms.values():
        lst.sort(key=lambda arm: angle(arm["d"]))

    # ---- intersectii: taieturi, asfalt, colturi de trotuar
    junctions = {}
    trims = {}
    caps = {}       # (strada, capat a?) -> cat poate taia intersectia de acolo (strazile prea scurte)
    redo = None     # a doua trecere: doar intersectiile de la capetele strazilor prea scurte
    for _pass in (1, 2):
        for nid, lst in (arms.items() if redo is None else [(n, arms[n]) for n in redo]):
            k = len(lst)
            if k < 2:
                continue
            node = nodes[nid]
            P = (node["x"], node["y"])
            need = [0.5] * k
            corners = []
            for i in range(k):
                j = (i + 1) % k
                A, B = lst[i], lst[j]
                phi = (angle(B["d"]) - angle(A["d"])) % (2 * math.pi)
                if k == 2 and i == 1 and phi == 0:
                    phi = 2 * math.pi
                info = {"phi": phi, "fillet": False}
                if phi < math.radians(170):
                    if math.degrees(phi) < MIN_ANGLE:
                        warn("unghi", f"unghi prea ascutit intre strazi ({math.degrees(phi):.0f} grade)", P)
                    ra, rb = A["road"], B["road"]
                    pa = add(P, mul(left(A["d"]), ra.h))
                    pb = add(P, mul(right(B["d"]), rb.h))
                    t = line_hit(pa, A["d"], pb, B["d"])
                    if t is not None:
                        C = add(pa, mul(A["d"], t))
                        R = min(ra.raza, rb.raza)
                        ca, cb = dot(sub(C, P), A["d"]), dot(sub(C, P), B["d"])
                        # strada prea scurta pentru intersectiile de la ambele capete (caps, a doua trecere): coltul
                        # se strange cat sa-i ramana loc; sub 30 cm ramane colt drept, fara arc
                        for lim, c0 in ((caps.get((ra.id, A["at_a"])), ca), (caps.get((rb.id, B["at_a"])), cb)):
                            if lim is not None:
                                R = min(R, max(0.0, (lim - c0) * math.tan(phi / 2)))
                        if R >= 0.3:
                            lf = R / math.tan(phi / 2)
                            ta, tb = ca + lf, cb + lf
                            need[i], need[j] = max(need[i], ta), max(need[j], tb)
                            bis = norm(add(A["d"], B["d"]))
                            center = add(C, mul(bis, R / math.sin(phi / 2)))
                            info.update(fillet=True, ta=ta, tb=tb, center=center, R=R)
                        else:
                            need[i], need[j] = max(need[i], ca), max(need[j], cb)
                corners.append(info)
            # doua strazi de latimi diferite cap la cap (fara cot mare): strada lata se taie mai din scurt si
            # asfaltul / trotuarul intersectiei se ingusteaza lin pe lungimea aia, nu cu o treapta la nod
            taper = False
            if k == 2 and all(c["phi"] >= math.radians(170) for c in corners):
                ra, rb = lst[0]["road"], lst[1]["road"]
                dw = max(abs(ra.h - rb.h), abs(ra.W - rb.W))
                if dw > 0.05:
                    wide = 0 if ra.W + ra.h >= rb.W + rb.h else 1
                    L = min(40.0, max(4.0, 6.0 * dw))
                    cap = caps.get((lst[wide]["road"].id, lst[wide]["at_a"]))
                    if cap is not None:
                        L = min(L, cap)
                    need[wide] = max(need[wide], L)
                    taper = True
            brate = []
            for i, arm in enumerate(lst):
                road = arm["road"]
                cap = caps.get((road.id, arm["at_a"]))
                fits = cap is None or need[i] + ZEBRA <= cap        # pe o strada prea scurta: fara trecere
                zebra = k >= 3 and fits
                # trecerea ceruta pe strada, la capatul ei din intersectia asta: "zebra", "linii" (doua linii) sau "niciuna"
                want = (road.marcaje.get("zebra") or {}).get("a" if arm["at_a"] else "b")
                if want == "niciuna":
                    zebra = False
                elif want in ("zebra", "linii"):
                    zebra = k >= 2 and fits
                trim = need[i] + (ZEBRA if zebra else 0.0)
                trims[(road.id, arm["at_a"])] = trim
                s = trim if arm["at_a"] else road.L - trim
                E, d = road.point_at(s)
                e = d if arm["at_a"] else mul(d, -1)
                brate.append({"road": road.id, "E": list(E), "e": list(e), "h": road.h, "W": road.W,
                              "zebra": zebra, "zebra_stil": "linii" if want == "linii" else "zebra", "trim": trim})
            asphalt, walks = [], []
            for i in range(k):
                j = (i + 1) % k
                A, B, info = lst[i], lst[j], corners[i]
                bi, bj = brate[i], brate[j]
                ai_r = add(bi["E"], mul(right(bi["e"]), bi["h"]))
                ai_l = add(bi["E"], mul(left(bi["e"]), bi["h"]))
                bj_r = add(bj["E"], mul(right(bj["e"]), bj["h"]))
                asphalt += [ai_r, ai_l]
                ra, rb = A["road"], B["road"]
                reflex = info["phi"] > math.radians(180.5)
                curb = [ai_l]
                if info["fillet"]:
                    ta_pt = add(add(P, mul(left(A["d"]), ra.h)), mul(A["d"], info["ta"]))
                    tb_pt = add(add(P, mul(right(B["d"]), rb.h)), mul(B["d"], info["tb"]))
                    c = info["center"]
                    curb += arc_points(c, info["R"], angle(sub(ta_pt, c)), angle(sub(tb_pt, c)))
                elif reflex and not taper:
                    # partea exterioara a unui cot: bordura ocoleste nodul pe un arc
                    curb += ([add(P, mul(left(A["d"]), ra.h))]
                             + arc_points(P, (ra.h + rb.h) / 2, angle(left(A["d"])), angle(right(B["d"])))[1:-1]
                             + [add(P, mul(right(B["d"]), rb.h))])
                curb.append(bj_r)
                asphalt += curb[1:-1]
                # trotuarul din colt: bordura spre asfalt, marginea exterioara spre cvartal
                oi_l = add(bi["E"], mul(left(bi["e"]), bi["W"]))
                oj_r = add(bj["E"], mul(right(bj["e"]), bj["W"]))
                outer = [oj_r, oi_l]
                if reflex and not taper:
                    outer = ([oj_r, add(P, mul(right(B["d"]), rb.W))]
                             + arc_points(P, (ra.W + rb.W) / 2, angle(right(B["d"])), angle(left(A["d"])))[1:-1]
                             + [add(P, mul(left(A["d"]), ra.W)), oi_l])
                elif info["phi"] < math.radians(170):
                    # marginea exterioara urmeaza strazile (si pe cele curbe) pana in coltul lor, exact ca poligonul
                    # cvartalului; dreptele trase de la capatul bratelor nimereau alt colt pe strazile curbe si iarba
                    # cvartalului intra peste trotuar
                    run_a = offset_run(ra, A["at_a"], bi["trim"], bi["W"], 1)
                    run_b = offset_run(rb, B["at_a"], bj["trim"], bj["W"], -1)
                    da, db = sub(run_a[1], run_a[0]), sub(run_b[1], run_b[0])
                    t = line_hit(run_a[0], da, run_b[0], db) if length(da) > 1e-6 and length(db) > 1e-6 else None
                    if t is not None:
                        X = add(run_a[0], mul(da, t))
                        if length(sub(X, P)) < 4 * max(bi["W"], bj["W"]):
                            ua, ub = dot(sub(X, P), A["d"]), dot(sub(X, P), B["d"])
                            keep_a = [p for u, p in zip(run_u(bi["trim"]), run_a) if u > ua + 0.1]
                            keep_b = [p for u, p in zip(run_u(bj["trim"]), run_b) if u > ub + 0.1]
                            outer = keep_b[::-1] + [X] + keep_a
                            if not keep_b or keep_b[-1] != oj_r:
                                outer = [oj_r] + [p for p in outer if p != oj_r]
                            if not keep_a or keep_a[-1] != oi_l:
                                outer = [p for p in outer if p != oi_l] + [oi_l]
                walks.append({"poligon": [list(p) for p in ccw(curb + outer)], "bordura": [list(p) for p in curb]})
            levels = {arm["road"].nivel for arm in lst}
            junctions[nid] = {"x": P[0], "y": P[1], "z": float(node.get("z", 0.0)),
                              "asfalt": [list(p) for p in ccw(asphalt)], "trotuare": walks, "brate": brate,
                              # intersectie suspendata (doar poduri) sau sub pamant (doar tuneluri)
                              "nivel": "sol" if "sol" in levels else ("pod" if "pod" in levels else "tunel")}
        if redo is not None:
            break
        # strazi prea scurte pentru intersectiile de la ambele capete: colturile de acolo se strang (si pierd
        # trecerea de pietoni) cat sa ramana MIN_ROAD m de strada; cele doua intersectii se refac
        redo = set()
        for road in roads.values():
            ta, tb = trims.get((road.id, True), 0.0), trims.get((road.id, False), 0.0)
            if ta + tb > road.L - MIN_ROAD and ta + tb > 0:
                avail = max(road.L - MIN_ROAD, 0.0)
                caps[(road.id, True)], caps[(road.id, False)] = avail * ta / (ta + tb), avail * tb / (ta + tb)
                redo |= {road.a, road.b}
        if not redo:
            break

    # ---- portiunile de strada dintre intersectii
    for road in roads.values():
        road.s0 = trims.get((road.id, True), 0.0)
        road.s1 = road.L - trims.get((road.id, False), 0.0)
        if road.s1 - road.s0 < 1.0:
            warn("scurta", f"strada {road.id} e prea scurta pentru intersectiile de la capete", road.point_at(road.L / 2)[0])
            mid = (road.s0 + road.s1) / 2
            road.s0, road.s1 = mid - 0.5, mid + 0.5
        if road.grade() > plan.get("panta_max", 0.10) + 1e-9 and road.id not in ramps:     # rampele: avertismentul lor
            warn("panta", f"panta {road.grade() * 100:.0f}% pe strada {road.id} (max {plan.get('panta_max', 0.10) * 100:.0f}%)",
                 road.point_at(road.L / 2)[0])

    # ---- strazi care se taie fara intersectie: pasaj (una trece pe sus) daca sunt destul de departe pe verticala
    pasaje = []
    rlist = list(roads.values())
    boxes = {r.id: (min(p[0] for p in r.pts) - 1, min(p[1] for p in r.pts) - 1,
                    max(p[0] for p in r.pts) + 1, max(p[1] for p in r.pts) + 1) for r in rlist}
    for i, ra in enumerate(rlist):
        for rb in rlist[i + 1:]:
            ba, bb = boxes[ra.id], boxes[rb.id]
            if ba[2] < bb[0] or bb[2] < ba[0] or ba[3] < bb[1] or bb[3] < ba[1]:
                continue
            # doar segmentele fiecarei strazi care intra in cutia celeilalte
            sa = [(k, p, q) for k, (p, q) in enumerate(zip(ra.pts, ra.pts[1:]))
                  if not (max(p[0], q[0]) < bb[0] or min(p[0], q[0]) > bb[2] or max(p[1], q[1]) < bb[1] or min(p[1], q[1]) > bb[3])]
            sb = [(k, u, v) for k, (u, v) in enumerate(zip(rb.pts, rb.pts[1:]))
                  if not (max(u[0], v[0]) < ba[0] or min(u[0], v[0]) > ba[2] or max(u[1], v[1]) < ba[1] or min(u[1], v[1]) > ba[3])]
            # langa nodul lor comun doua strazi se pot atinge fara sa se taie (o curba care porneste putin inapoi
            # dintr-un punct de curba pus aproape de nod): acolo e intersectia lor, nu o incrucisare
            shared = [(nodes[n]["x"], nodes[n]["y"]) for n in {ra.a, ra.b} & {rb.a, rb.b}]
            reach = max(ra.W, rb.W)
            hit = next(((h, i, j) for i, p, q in sa for j, u, v in sb
                        if not (max(p[0], q[0]) < min(u[0], v[0]) or min(p[0], q[0]) > max(u[0], v[0])
                                or max(p[1], q[1]) < min(u[1], v[1]) or min(p[1], q[1]) > max(u[1], v[1]))
                        for h in [seg_hit(p, q, u, v)] if h and not any(length(sub(h, s)) < reach for s in shared)),
                       None)
            if hit:
                h, i, j = hit
                za = ra.z_at(ra.cum[i] + length(sub(h, ra.pts[i])))
                zb = rb.z_at(rb.cum[j] + length(sub(h, rb.pts[j])))
                if abs(za - zb) >= CLEARANCE and (ra.nivel != "sol" or rb.nivel != "sol"):
                    up, down = (ra, rb) if za > zb else (rb, ra)
                    pasaje.append({"x": round(h[0], 2), "y": round(h[1], 2), "sus": up.id, "jos": down.id,
                                   "dz": round(abs(za - zb), 2)})
                elif ra.nivel != "sol" or rb.nivel != "sol":
                    warn("pasaj", f"strazile {ra.id} si {rb.id} se trec una peste alta la doar {abs(za - zb):.1f} m "
                         f"(minim {CLEARANCE:.1f} m: urca podul sau coboara tunelul)", h)
                elif abs(za - zb) >= CLEARANCE:
                    warn("incrucisare", f"strazile {ra.id} si {rb.id} se trec la {abs(za - zb):.1f} m una de alta: "
                         f"fa-o pe una pod sau tunel (Nivel, in dreapta)", h)
                else:
                    warn("incrucisare", f"strazile {ra.id} si {rb.id} se taie fara intersectie (pune un nod acolo)", h)

    # ---- cvartale = fetele grafului (fata in stanga), micsorate cu latimea strazilor
    # podurile si tunelurile nu impart cvartalele (trec pe deasupra / pe dedesubt)
    farms = {nid: [arm for arm in lst if arm["road"].nivel == "sol"] for nid, lst in arms.items()}
    index = {}
    for nid, lst in farms.items():
        for k, arm in enumerate(lst):
            index[(arm["road"].id, arm["at_a"])] = (nid, k)
    visited, faces = set(), []
    for road in roads.values():
        if road.nivel != "sol":
            continue
        for forward in (True, False):
            if (road.id, forward) in visited:
                continue
            face, cur = [], (road.id, forward)
            while cur not in visited:
                visited.add(cur)
                face.append(cur)
                rd = roads[cur[0]]
                # sosesc in nodul de la capatul opus; bratul pe care am venit e (rd, not forward)
                nid, k = index[(rd.id, not cur[1])]
                lst = farms[nid]
                nxt = lst[(k - 1) % len(lst)]
                cur = (nxt["road"].id, nxt["at_a"])
            faces.append(face)
    blocks = []
    zones = plan.get("zones", [])
    for face in faces:
        # scot strazile fara iesire (parcurse dus-intors una dupa alta)
        changed = True
        while changed and len(face) > 2:
            changed = False
            for i in range(len(face)):
                a, b = face[i], face[(i + 1) % len(face)]
                if a[0] == b[0] and a[1] != b[1]:
                    face = [h for k, h in enumerate(face) if k not in (i, (i + 1) % len(face))]
                    changed = True
                    break
        if len(face) < 2:
            continue
        center = [p for rid, fw in face for p in roads[rid].half(fw)[:-1]]
        if len(center) < 3 or area(center) <= 0:
            continue    # fata exterioara (sens orar)
        # fiecare segment mutat spre stanga cu W, apoi unite prin intersectia dreptelor
        segs = []
        for rid, fw in face:
            rd = roads[rid]
            pts = rd.half(fw)
            for p, q in zip(pts, pts[1:]):
                if length(sub(q, p)) < 1e-6:
                    continue
                n = left(norm(sub(q, p)))
                segs.append((add(p, mul(n, rd.W)), add(q, mul(n, rd.W)), q, rd.W))
        poly = []
        for i, (p, q, orig, W) in enumerate(segs):
            p2, q2, _o, W2 = segs[(i + 1) % len(segs)]
            t = line_hit(p, sub(q, p), p2, sub(q2, p2))
            X = add(p, mul(sub(q, p), t)) if t is not None else q
            convex = cross(sub(q, p), sub(q2, p2)) > 0     # la stanga: coltul lung e corect, se pastreaza
            if t is None or (not convex and length(sub(X, orig)) > 4 * max(W, W2)):
                poly += [q, p2]
            else:
                poly.append(X)
        clean = [poly[0]]
        for p in poly[1:]:
            if length(sub(p, clean[-1])) > 0.05:
                clean.append(p)
        poly = untangle(clean)
        a_poly = area(poly) if len(poly) >= 3 else 0.0
        valid = a_poly > MIN_BLOCK and simple(poly)
        marker = next((z for z in zones if inside((z["x"], z["y"]), poly)), None) if valid else None
        if marker is None and valid:
            marker = next((z for z in zones if inside((z["x"], z["y"]), center)), None)
        cx = sum(p[0] for p in center) / len(center)
        cy = sum(p[1] for p in center) / len(center)
        if not valid:
            warn("cvartal", "cvartal prea mic sau cu forma imposibila (ramane curte)", (cx, cy))
        blocks.append({"id": len(blocks), "poligon": [list(p) for p in poly], "arie": round(a_poly, 1),
                       "valid": valid, "zona": (marker or {}).get("tip", plan.get("zona_implicita", "lc_caramida")),
                       "marcaj": marker, "centru": [cx, cy], "strazi": sorted({rid for rid, _fw in face})})

    # ---- suprafete desenate: apa oriunde, restul (parc, piateta, parcare, sport, gazon, zone de cladiri) in
    #      cvartalul in care sunt desenate, aduse inauntrul lui
    waters, areas, nature = [], [], []
    for sf in plan.get("suprafete", []):
        pts = [tuple(p) for p in sf.get("puncte", [])]
        if len(pts) < 3 or abs(area(pts)) < 4.0:
            continue
        pts = ccw(pts)
        if sf.get("tip") == "apa":
            waters.append(pts)
            # mal: "chei" (beton, ca pana acum), "plaja" (nisip care intra in apa), "natural" (mal cu iarba)
            areas.append({"id": sf.get("id"), "tip": "apa", "poligon": [list(p) for p in pts], "bloc": None,
                          "mal": sf.get("mal") if sf.get("mal") in ("plaja", "natural") else "chei",
                          "nivel": "mare" if sf.get("nivel") == "mare" else "teren"})
            continue
        if sf.get("tip") in NATURAL:
            nature.append(pts)
            areas.append({"id": sf.get("id"), "tip": sf["tip"], "poligon": [list(p) for p in pts], "bloc": None})
            continue
        cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        blk = next((b for b in blocks if b["valid"] and inside((cx, cy), b["poligon"])), None)
        if blk is None:
            blk = max((b for b in blocks if b["valid"]), default=None,
                      key=lambda b: sum(inside(p, b["poligon"]) for p in pts))
            if blk is None or not any(inside(p, blk["poligon"]) for p in pts):
                # in afara cvartalelor: devine un cvartal al ei, lipit de trotuarele de langa
                free = free_area(pts, roads)
                if free is None:
                    warn("suprafata", "suprafata din afara cvartalelor trece peste o strada sau e prea mica (ignorata)",
                         (cx, cy))
                    continue
                blocks.append({"id": len(blocks), "poligon": [list(p) for p in free], "arie": round(area(free), 1),
                               "valid": True, "zona": sf.get("tip", "parc"), "marcaj": None, "centru": [cx, cy],
                               "strazi": [], "liber": True, "poteci": sf.get("poteci")})
                continue
        bp = [tuple(p) for p in blk["poligon"]]
        poly = [clamp_inside(p, bp, 0.3) for p in pts]
        clean = [poly[0]]
        for p in poly[1:]:
            if length(sub(p, clean[-1])) > 0.2:
                clean.append(p)
        if len(clean) < 3 or area(clean) < 20.0:
            continue
        if not simple(clean):
            warn("suprafata", "suprafata care se autointersecteaza (ignorata)", (cx, cy))
            continue
        areas.append({"id": sf.get("id"), "tip": sf.get("tip", "parc"), "poligon": [list(p) for p in clean],
                      "bloc": blk["id"], "poteci": sf.get("poteci")})
        blk.setdefault("suprafete", []).append(len(areas) - 1)
    for b in blocks:
        if b["valid"] and any(inside(b["centru"], w) for w in waters):
            b["zona"] = "apa"      # cvartal inundat: bazin, fara cladiri

    xs = [p[0] for r in roads.values() for p in r.pts] + [a["x"] for a in plan.get("altitudini", [])]
    ys = [p[1] for r in roads.values() for p in r.pts] + [a["y"] for a in plan.get("altitudini", [])]
    xs += [p[0] for w in waters + nature for p in w]
    ys += [p[1] for w in waters + nature for p in w]
    bounds = [min(xs), min(ys), max(xs), max(ys)] if xs else [0.0, 0.0, 0.0, 0.0]
    # pe teren pictat: intersectiile apropiate prea diferite ca inaltime se apropie (cu portiunile reale ale
    # strazilor, stiute abia acum) si analiza se reface o data cu inaltimile lor
    if followers and _fix is None:
        z = {nid: float(n["z"]) for nid, n in nodes.items()}
        moved = relax_nodes(followers, z, gmax)
        if moved:
            return analyze(plan, {nid: round(z[nid], 2) for nid in moved})
    return {"roads": {r.id: {"tip": r.tip, "T": r.t, "benzi": int(r.t.get("benzi", 1)),
                             "r": r.r, "s": r.s, "W": r.W, "pts": [list(p) for p in r.pts],
                             "L": r.L, "s0": r.s0, "s1": r.s1, "samples": r.samples(), "panta": r.grade(),
                             "a": r.a, "b": r.b, "nivel": r.nivel, "marcaje": r.marcaje}
                      for r in roads.values()},
            "junctions": junctions, "blocks": blocks, "warnings": warnings, "bounds": bounds,
            "suprafete": areas, "pasaje": pasaje, "mare": sea_level(plan), "tipuri": types, "noduri": zs,
            "noduri_pod": bridge_z}


# ------------------------------------------------------------------------------------------ teren

def painted_grid(plan, X, Y):
    """Terenul pictat esantionat pe grila X, Y (numpy), 0 unde nu e pictat."""
    import numpy as np
    t = plan.get("teren")
    if not t or not t.get("h"):
        return np.zeros_like(X)
    nx, ny, s = int(t["nx"]), int(t["ny"]), float(t["step"])
    H = np.asarray(t["h"], float).reshape(ny, nx)
    fx, fy = (X - float(t["x0"])) / s, (Y - float(t["y0"])) / s
    out = (fx < 0) | (fy < 0) | (fx > nx - 1) | (fy > ny - 1)
    i, j = np.clip(fx.astype(int), 0, nx - 2), np.clip(fy.astype(int), 0, ny - 2)
    tx, ty = np.clip(fx - i, 0, 1), np.clip(fy - j, 0, 1)
    v = (H[j, i] * (1 - tx) * (1 - ty) + H[j, i + 1] * tx * (1 - ty) + H[j + 1, i] * (1 - tx) * ty
         + H[j + 1, i + 1] * tx * ty)
    return np.where(out, 0.0, v)


def terrain(plan, analysis, step=4.0, margin=60.0):
    """Grila de inaltimi (numpy): terenul pictat, corectat lin acolo unde strazile au inaltimea scrisa de mana
    (rampe, planuri vechi) si la punctele de altitudine. Intoarce {x0, y0, step, z (ny x nx)}."""
    import numpy as np
    h = painted(plan) or (lambda _x, _y: 0.0)
    pts = []
    for r in analysis["roads"].values():
        if r.get("nivel", "sol") != "sol":
            continue      # podurile si tunelurile nu ridica / nu sapa terenul
        smp = r["samples"]
        pts += [(p[0], p[1], p[2], 1.0) for p in smp[::10] + [smp[-1]]]
    for j in analysis["junctions"].values():
        if j.get("nivel", "sol") == "sol":
            pts.append((j["x"], j["y"], j["z"], 2.0))
    for a in plan.get("altitudini", []):
        pts.append((a["x"], a["y"], float(a.get("z", 0.0)), 4.0))
    x0, y0, x1, y1 = analysis["bounds"]
    t = plan.get("teren")
    if t and t.get("h"):   # terenul pictat intra in grila chiar si unde nu sunt strazi
        tx1, ty1 = float(t["x0"]) + float(t["step"]) * (int(t["nx"]) - 1), float(t["y0"]) + float(t["step"]) * (int(t["ny"]) - 1)
        if x0 == x1 == 0.0 and y0 == y1 == 0.0:
            x0, y0, x1, y1 = float(t["x0"]), float(t["y0"]), tx1, ty1
        else:
            x0, y0, x1, y1 = min(x0, float(t["x0"])), min(y0, float(t["y0"])), max(x1, tx1), max(y1, ty1)
    x0, y0, x1, y1 = x0 - margin, y0 - margin, x1 + margin, y1 + margin
    nx, ny = int((x1 - x0) / step) + 2, int((y1 - y0) / step) + 2
    X, Y = np.meshgrid(x0 + np.arange(nx) * step, y0 + np.arange(ny) * step)
    base = painted_grid(plan, X, Y)
    if not pts:
        return {"x0": x0, "y0": y0, "step": step, "z": base}
    # corectiile (inaltimea dorita minus terenul pictat) se intind lin; strazile puse pe teren au corectie 0
    P = np.array([(x, y, z - h(x, y), w) for x, y, z, w in pts])
    num = np.zeros_like(X)
    den = np.zeros_like(X)
    near = np.full(X.shape, 1e18)
    for chunk in range(0, len(P), 256):
        c = P[chunk:chunk + 256]
        d2 = (X[..., None] - c[:, 0]) ** 2 + (Y[..., None] - c[:, 1]) ** 2 + 25.0
        w = c[:, 3] / d2
        num += (w * c[:, 2]).sum(-1)
        den += w.sum(-1)
        near = np.minimum(near, d2.min(-1))
    Z = base + num / den
    droad = np.sqrt(np.maximum(near - 25.0, 0.0))     # cat de departe de strazi (malul nu coboara sub oras)
    for _ in range(3):   # netezire 3x3
        pad = np.pad(Z, 1, mode="edge")
        Z = sum(pad[1 + dy:1 + dy + ny, 1 + dx:1 + dx + nx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)) / 9.0
    # sub apa: fundul la 5 m sub nivelul marii, la un lac (apa la nivelul solului, implicit) la LAKE_DEPTH m sub
    # nivelul lui. La plaja / malul natural terenul coboara lin spre apa (SHORE_LAND m) si continua in panta sub apa
    # (SHORE_SLOPE) pana la fund, fara zidul cheiului
    sea0 = analysis.get("mare", sea_level(plan))
    here = {"x0": x0, "y0": y0, "step": step}
    for sf in analysis.get("suprafete", []):
        if sf["tip"] != "apa":
            continue
        poly = sf["poligon"]
        if sf.get("nivel") == "mare":
            sea, bed = sea0, sea0 - 5.0
        else:   # lac / rau: apa la 40 cm sub cel mai jos punct al malului (terenul de pe contur, inainte de bazin)
            sea = lake_level(dict(here, z=Z), poly) - 0.4
            bed = sea - LAKE_DEPTH
        sf["nivel_z"] = round(float(sea), 2)     # gen_oras si exportul FiveM (water.xml) iau nivelul de aici
        inside_w = np.zeros(X.shape, bool)
        for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1]):
            inside_w ^= ((ay > Y) != (by > Y)) & (X < ax + (Y - ay) * (bx - ax) / (by - ay + 1e-12))
        if sf.get("mal", "chei") == "chei":
            Z = np.where(inside_w, np.minimum(Z, bed), Z)
            continue
        d = np.full(X.shape, 1e9)
        for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1]):
            ex, ey = bx - ax, by - ay
            t = np.clip(((X - ax) * ex + (Y - ay) * ey) / (ex * ex + ey * ey + 1e-12), 0.0, 1.0)
            d = np.minimum(d, np.hypot(ax + ex * t - X, ay + ey * t - Y))
        shore = sea + 0.3
        # cat de departe incepe coborarea: dupa cat are de coborat terenul de acolo (curba lina: la apa aproape plat)
        reach = np.clip(np.maximum(Z - shore, 0.0) / SHORE_GRADE, SHORE_LAND, SHORE_MAX)
        k = np.clip(d / reach, 0.0, 1.0)
        k = k * k * (3.0 - 2.0 * k)
        land = ~inside_w & (d < reach)
        # langa oras terenul ramane la nivelul lui (20 m), apoi incepe coborarea lin (40 m); cu apa aproape de oras
        # iese un taluz mai abrupt intre oras si plaja, dar plaja de langa apa ramane lina
        hold = np.clip((droad - 20.0) / 40.0, 0.0, 1.0)
        hold = hold * hold * (3.0 - 2.0 * hold)
        low = shore + (np.maximum(Z, shore) - shore) * k
        Z = np.where(land, Z + (low - Z) * hold, Z)
        Z = np.where(inside_w, np.minimum(Z, np.maximum(bed, shore - 0.3 - d * SHORE_SLOPE)), Z)
    return {"x0": x0, "y0": y0, "step": step, "z": Z}


LAKE_DEPTH = 3.0     # cat de adanc e un lac / rau (apa la nivelul solului) sub nivelul apei


def lake_level(grid, poly, every=2.0):
    """Cel mai jos punct al malului: terenul pe conturul apei, din `every` in `every` m."""
    zs = []
    for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1]):
        n = max(1, int(math.hypot(bx - ax, by - ay) / every))
        zs += [height(grid, ax + (bx - ax) * k / n, ay + (by - ay) * k / n) for k in range(n)]
    return min(zs)


def height(grid, x, y):
    """Inaltimea terenului in (x, y), interpolata biliniar din grila."""
    Z, s = grid["z"], grid["step"]
    fx, fy = (x - grid["x0"]) / s, (y - grid["y0"]) / s
    i = min(max(int(fx), 0), Z.shape[1] - 2)
    j = min(max(int(fy), 0), Z.shape[0] - 2)
    tx, ty = min(max(fx - i, 0.0), 1.0), min(max(fy - j, 0.0), 1.0)
    return float(Z[j, i] * (1 - tx) * (1 - ty) + Z[j, i + 1] * tx * (1 - ty) + Z[j + 1, i] * (1 - tx) * ty
                 + Z[j + 1, i + 1] * tx * ty)

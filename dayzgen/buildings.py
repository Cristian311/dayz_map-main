# -*- coding: utf-8 -*-
"""
Cladiri low-poly procedurale (stil sat est-european / DayZ): casa mica, casa cu etaj, hambar, sopron.
Produce geometrie numpy (vertecsi, fete, UV-uri, id material) + mesh de coliziune.
"""
import math
import numpy as np

# id-urile materialelor (sloturile din mesh)
MAT_WALL = 0
MAT_ROOF = 1
MAT_WINDOW = 2
MAT_DOOR = 3
MAT_BRICK = 4

# textura folosita de fiecare slot, per tip de cladire (cheia din textures.py) si marimea in lume (m / repetare)
WALL_TEX_SIZE = {"plaster": 3.0, "wood": 2.4, "brick": 2.0}
ROOF_TEX_SIZE = {"rooftile": 2.0, "metal": 2.0}


class MeshBuilder:
    def __init__(self):
        self.verts = []
        self.faces = []      # liste de indici (3 sau 4)
        self.uvs = []        # per fata: lista de (u,v) per colt
        self.mats = []
        self.collision = []  # bool per fata: intra in coliziune

    def add_face(self, pts, uvs, mat, collision=True):
        base = len(self.verts)
        self.verts.extend([tuple(map(float, p)) for p in pts])
        self.faces.append([base + i for i in range(len(pts))])
        self.uvs.append([tuple(map(float, t)) for t in uvs])
        self.mats.append(mat)
        self.collision.append(collision)

    def wall(self, a, b, z0, z1, mat, tex, u0=0.0):
        """Perete vertical de la punctul a la b (in plan), normala spre exterior = (b-a) x Z."""
        ax, ay = a
        bx, by = b
        L = math.hypot(bx - ax, by - ay)
        pts = [(ax, ay, z0), (bx, by, z0), (bx, by, z1), (ax, ay, z1)]
        uvs = [(u0, z0 / tex), (u0 + L / tex, z0 / tex), (u0 + L / tex, z1 / tex), (u0, z1 / tex)]
        self.add_face(pts, uvs, mat)

    def gable(self, a, b, z_wall, z_ridge, mat, tex, flip=False):
        """Triunghi de fronton deasupra peretelui a->b."""
        ax, ay = a
        bx, by = b
        L = math.hypot(bx - ax, by - ay)
        mx, my = (ax + bx) / 2, (ay + by) / 2
        pts = [(ax, ay, z_wall), (bx, by, z_wall), (mx, my, z_ridge)]
        uvs = [(0, z_wall / tex), (L / tex, z_wall / tex), (L / (2 * tex), z_ridge / tex)]
        if flip:
            pts = pts[::-1]
            uvs = uvs[::-1]
        self.add_face(pts, uvs, mat)

    def quad_on_wall(self, a, b, t, w, h, z0, mat, offset=0.02, collision=False):
        """Un dreptunghi (fereastra/usa) pe peretele a->b la pozitia relativa t (0..1), usor in fata peretelui."""
        ax, ay = a
        bx, by = b
        L = math.hypot(bx - ax, by - ay)
        dx, dy = (bx - ax) / L, (by - ay) / L
        nx, ny = dy, -dx  # (b-a) x Z
        c = t * L
        p0 = (ax + dx * (c - w / 2) + nx * offset, ay + dy * (c - w / 2) + ny * offset)
        p1 = (ax + dx * (c + w / 2) + nx * offset, ay + dy * (c + w / 2) + ny * offset)
        pts = [(p0[0], p0[1], z0), (p1[0], p1[1], z0), (p1[0], p1[1], z0 + h), (p0[0], p0[1], z0 + h)]
        uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
        self.add_face(pts, uvs, mat, collision=collision)

    def box(self, cx, cy, sx, sy, z0, z1, mat, tex):
        hx, hy = sx / 2, sy / 2
        corners = [(cx - hx, cy - hy), (cx + hx, cy - hy), (cx + hx, cy + hy), (cx - hx, cy + hy)]
        for i in range(4):
            self.wall(corners[i], corners[(i + 1) % 4], z0, z1, mat, tex)
        top = [(cx - hx, cy - hy, z1), (cx + hx, cy - hy, z1), (cx + hx, cy + hy, z1), (cx - hx, cy + hy, z1)]
        self.add_face(top, [(0, 0), (sx / tex, 0), (sx / tex, sy / tex), (0, sy / tex)], mat)

    def to_arrays(self):
        return {
            "verts": np.array(self.verts, dtype=np.float64),
            "faces": self.faces,
            "uvs": self.uvs,
            "mats": self.mats,
            "collision": self.collision,
        }


def gable_house(length, width, wall_h, roof_h, overhang, wall_tex, roof_tex, windows_front=2,
                windows_side=1, floors=1, door_t=0.3, chimney=True, big_door=False):
    """
    Casa cu acoperis in doua ape, coama de-a lungul axei X. Fata = latura -Y.
    length = pe X, width = pe Y.
    """
    B = MeshBuilder()
    hx, hy = length / 2, width / 2
    tw = WALL_TEX_SIZE[wall_tex]
    tr = ROOF_TEX_SIZE[roof_tex]
    z_ridge = wall_h + roof_h
    corners = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]  # CCW de sus
    # pereti
    for i in range(4):
        B.wall(corners[i], corners[(i + 1) % 4], 0.0, wall_h, MAT_WALL, tw)
    # frontoane pe laturile +X si -X
    B.gable(corners[1], corners[2], wall_h, z_ridge, MAT_WALL, tw)            # x = +hx
    B.gable(corners[3], corners[0], wall_h, z_ridge, MAT_WALL, tw)            # x = -hx
    # acoperis
    o = overhang
    slope_len = math.hypot(hy + o, roof_h + o * (roof_h / hy))
    z_eave = wall_h - o * (roof_h / hy)
    # panta +Y
    B.add_face([(-hx - o, 0, z_ridge), (hx + o, 0, z_ridge), (hx + o, hy + o, z_eave), (-hx - o, hy + o, z_eave)],
               [(0, 0), ((length + 2 * o) / tr, 0), ((length + 2 * o) / tr, slope_len / tr), (0, slope_len / tr)],
               MAT_ROOF)
    # panta -Y
    B.add_face([(hx + o, 0, z_ridge), (-hx - o, 0, z_ridge), (-hx - o, -hy - o, z_eave), (hx + o, -hy - o, z_eave)],
               [(0, 0), ((length + 2 * o) / tr, 0), ((length + 2 * o) / tr, slope_len / tr), (0, slope_len / tr)],
               MAT_ROOF)
    # grosimea acoperisului (placa vizibila de jos la streasina)
    th = 0.15
    for sgn in (1, -1):
        y_e = sgn * (hy + o)
        p = [(-hx - o, y_e, z_eave), (hx + o, y_e, z_eave), (hx + o, y_e, z_eave - th), (-hx - o, y_e, z_eave - th)]
        if sgn < 0:
            p = [p[1], p[0], p[3], p[2]]
        B.add_face(p, [(0, 0), ((length + 2 * o) / tr, 0), ((length + 2 * o) / tr, th / tr), (0, th / tr)], MAT_ROOF, collision=False)
        # dedesubtul streasinii
        under = [(-hx - o, y_e, z_eave - th), (hx + o, y_e, z_eave - th), (hx + o, sgn * hy, z_eave - th), (-hx - o, sgn * hy, z_eave - th)]
        if sgn > 0:
            under = [under[1], under[0], under[3], under[2]]
        B.add_face(under, [(0, 0), (1, 0), (1, 1), (0, 1)], MAT_ROOF, collision=False)
    # ferestre & usa
    win_w, win_h = 1.0, 1.25
    door_w, door_h = (2.8, 3.2) if big_door else (1.0, 2.1)
    for f in range(floors):
        zb = 1.0 + f * (wall_h / floors)
        for k in range(windows_front):
            t = (k + 1) / (windows_front + 1)
            if f == 0 and abs(t - door_t) < 0.12:
                continue
            B.quad_on_wall(corners[0], corners[1], t, win_w, win_h, zb, MAT_WINDOW)
            B.quad_on_wall(corners[2], corners[3], t, win_w, win_h, zb, MAT_WINDOW)
        for k in range(windows_side):
            t = (k + 1) / (windows_side + 1)
            B.quad_on_wall(corners[1], corners[2], t, win_w, win_h, zb, MAT_WINDOW)
            B.quad_on_wall(corners[3], corners[0], t, win_w, win_h, zb, MAT_WINDOW)
    B.quad_on_wall(corners[0], corners[1], door_t, door_w, door_h, 0.0, MAT_DOOR)
    if chimney:
        B.box(hx * 0.45, hy * 0.35, 0.7, 0.7, wall_h + roof_h * 0.55, z_ridge + 0.7, MAT_BRICK, 1.0)
    return B.to_arrays()


def shed(length, width, wall_h, wall_tex, roof_tex):
    """Sopron cu acoperis intr-o singura apa (mai inalt in spate)."""
    B = MeshBuilder()
    hx, hy = length / 2, width / 2
    tw = WALL_TEX_SIZE[wall_tex]
    tr = ROOF_TEX_SIZE[roof_tex]
    z_front = wall_h
    z_back = wall_h + 0.6
    corners = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    B.wall(corners[0], corners[1], 0.0, z_front, MAT_WALL, tw)  # fata
    B.wall(corners[2], corners[3], 0.0, z_back, MAT_WALL, tw)   # spate
    # laturile: trapez
    for a, b, za, zb in ((corners[1], corners[2], z_front, z_back), (corners[3], corners[0], z_back, z_front)):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        B.add_face([(a[0], a[1], 0), (b[0], b[1], 0), (b[0], b[1], zb), (a[0], a[1], za)],
                   [(0, 0), (L / tw, 0), (L / tw, zb / tw), (0, za / tw)], MAT_WALL)
    o = 0.3
    B.add_face([(-hx - o, hy + o, z_back + 0.05), (hx + o, hy + o, z_back + 0.05),
                (hx + o, -hy - o, z_front - 0.05), (-hx - o, -hy - o, z_front - 0.05)],
               [(0, 0), ((length + 2 * o) / tr, 0), ((length + 2 * o) / tr, (width + 2 * o) / tr), (0, (width + 2 * o) / tr)],
               MAT_ROOF)
    B.quad_on_wall(corners[0], corners[1], 0.5, 1.0, 2.0, 0.0, MAT_DOOR)
    return B.to_arrays()


def build_all():
    """
    Returneaza {cheie: {"mesh": arrays, "wall_tex": ..., "roof_tex": ..., "radius": raza amprentei}}.
    Cheile trebuie sa corespunda cu config.BUILDING_KEYS.
    """
    out = {}
    m = gable_house(9.0, 7.0, 3.0, 2.2, 0.45, "plaster", "rooftile", windows_front=3, windows_side=1)
    out["house_a"] = {"mesh": m, "wall_tex": "plaster", "roof_tex": "rooftile", "radius": math.hypot(4.5, 3.5) + 0.5}
    m = gable_house(12.0, 8.5, 6.0, 2.6, 0.5, "brick", "rooftile", windows_front=3, windows_side=2, floors=2, door_t=0.5)
    out["house_b"] = {"mesh": m, "wall_tex": "brick", "roof_tex": "rooftile", "radius": math.hypot(6.0, 4.25) + 0.5}
    m = gable_house(15.0, 9.0, 4.6, 2.8, 0.5, "wood", "metal", windows_front=0, windows_side=2, door_t=0.5,
                    chimney=False, big_door=True)
    out["barn"] = {"mesh": m, "wall_tex": "wood", "roof_tex": "metal", "radius": math.hypot(7.5, 4.5) + 0.5}
    m = shed(4.0, 3.0, 2.4, "wood", "metal")
    out["shed"] = {"mesh": m, "wall_tex": "wood", "roof_tex": "metal", "radius": math.hypot(2.0, 1.5) + 0.5}
    return out

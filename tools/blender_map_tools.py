# -*- coding: utf-8 -*-
"""
Tab-ul "Harta" din Blender: unelte ca sa construiesti harta fara sa stii Blender.

Pornit de BLENDER_EDITOR.bat (-P). La pornire aranjeaza ecranul: viewport cu texturile vizibile, Asset
Browser jos deschis pe biblioteca "GTA V (generator)", bara laterala deschisa. Taste noi: J = pune pe sol,
F = centreaza vederea pe selectie.

Unelte (in ordinea in care le folosesti):
  Harta noua ............ teren plat din placi de 100 m, punctul de spawn si limitele hartii
  Pune pe sol (J) ....... asaza obiectele selectate pe teren
  Roteste 90 ............ rotire in pasi de 90 de grade, fiecare obiect in jurul lui
  Lipeste de vecin ...... aliniaza si lipeste obiectul activ de cel mai apropiat obiect (siruri de cladiri)
  Deseneaza linie ....... click-uri pe teren, Enter = gata (garduri, stalpi, zone)
  Multiplica ............ copii ale obiectului activ de-a lungul liniei selectate, la pas fix
  Imprastie in zona ..... copii la intamplare ale obiectelor selectate, in interiorul unei linii inchise
  Masoara ............... rigla din Blender
"""
import importlib.util
import math
import random
import sys
from pathlib import Path

import bpy
import numpy as np
from bpy_extras import view3d_utils
from mathutils import Matrix, Vector

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parent.parent
LIBRARY_NAME = "GTA V (generator)"
GROUND = "Teren"
LINES = "Linii"
TILE = 100.0           # m; fiecare placa de teren e un model separat (se incarca pe bucati in joc)
GRID = 5.0             # m; rezolutia placilor (pentru pictat si denivelat mai tarziu)
UV_REPEAT = 8.0        # m; o repetare a texturii de iarba
GROUND_LOD = 1500.0    # m; terenul se vede de departe
TEX_DIR = ROOT / "output" / "harta_texturi"
MAX_COPIES = 2000


def _load_tool(name):
    spec = importlib.util.spec_from_file_location(f"harta_{name}", ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FX = _load_tool("blender_fivem_export")      # classify / gta_info: ce e model GTA si ce e model nou


# ------------------------------------------------------------------------------------------ utilitare

def ensure_collection(context, name):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
    if coll.name not in context.scene.collection.children:
        context.scene.collection.children.link(coll)
    return coll


def yaw_of(obj) -> float:
    return obj.matrix_world.to_quaternion().to_euler("XYZ").z


def local_box(obj):
    """Cutia modelului in coordonatele lui: din datele GTA daca e model din joc, altfel din geometrie."""
    info = FX.gta_info(obj)
    if info and info.get("bb_min") and info.get("bb_max"):
        return Vector(info["bb_min"]), Vector(info["bb_max"])
    corners = [Vector(c) for c in obj.bound_box]
    return (Vector(tuple(min(c[i] for c in corners) for i in range(3))),
            Vector(tuple(max(c[i] for c in corners) for i in range(3))))


def is_placeable(obj) -> bool:
    """Obiectele pe care le asezi (cladiri, props, modele proprii); nu terenul, liniile sau reperele."""
    return obj.type in FX.MESH_TYPES and obj.get("harta_tip") not in ("teren", "linie", "strada")


class Ground:
    """Terenul (placile din colectia Teren si strazile) pentru aflarea cotei solului intr-un punct."""

    def __init__(self, context):
        self.depsgraph = context.evaluated_depsgraph_get()
        self.items = []
        for obj in context.scene.objects:
            if obj.type != "MESH" or obj.get("harta_tip") not in ("teren", "strada") or not obj.visible_get():
                continue
            corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
            self.items.append((obj, obj.matrix_world.inverted(), min(c.x for c in corners),
                               max(c.x for c in corners), min(c.y for c in corners), max(c.y for c in corners)))

    def __bool__(self):
        return bool(self.items)

    def z(self, x: float, y: float):
        """Cota cea mai de sus a terenului in (x, y), sau None daca acolo nu e teren."""
        best = None
        for obj, inv, x0, x1, y0, y1 in self.items:
            if not (x0 - 0.5 <= x <= x1 + 0.5 and y0 - 0.5 <= y <= y1 + 0.5):
                continue
            origin = inv @ Vector((x, y, 100000.0))
            direction = (inv.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()
            hit, loc, _normal, _index = obj.ray_cast(origin, direction, depsgraph=self.depsgraph)
            if hit:
                z = (obj.matrix_world @ loc).z
                best = z if best is None else max(best, z)
        return best


def drop_to_ground(objs, ground) -> int:
    """Asaza obiectele pe teren, cu baza cutiei pe punctul cel mai de jos al solului de sub ele (ca
    generatorul de oras). La 682 din 754 de cladiri GTA intregi originea e la mijlocul cutiei; doar cele
    cu originea langa baza (fundatie sub sol) stau cu originea pe punctul cel mai inalt al solului."""
    moved = 0
    for obj in objs:
        if not is_placeable(obj):
            continue
        lo, hi = local_box(obj)
        mw = obj.matrix_world
        samples = [mw @ Vector((x, y, lo.z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y)] + [mw.translation]
        hits = [z for z in (ground.z(p.x, p.y) for p in samples) if z is not None]
        if not hits:
            continue
        height = max(hi.z - lo.z, 0.01)
        if FX.classify(obj) == "gta" and lo.z > -0.35 * height:
            dz = max(hits) - mw.translation.z
        else:
            # model propriu, sau model GTA cu originea la mijloc: baza pe sol
            bottom = min((mw @ Vector((x, y, lo.z))).z for x in (lo.x, hi.x) for y in (lo.y, hi.y))
            dz = min(hits) - bottom
        new = mw.copy()
        new.translation.z += dz
        obj.matrix_world = new
        moved += 1
    return moved


def place_copy(src, pos, yaw, scale=None):
    """Copie care foloseste acelasi model (ca Alt+D), cu pozitia si rotatia date."""
    obj = src.copy()
    for coll in src.users_collection:
        coll.objects.link(obj)
    s = src.matrix_world.to_scale() if scale is None else scale
    obj.matrix_world = Matrix.Translation(pos) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Diagonal((s[0], s[1], s[2], 1.0))
    return obj


def line_points(context, line):
    """Punctele liniei (in ordine, coordonate mondiale) si daca e inchisa."""
    cyclic = any(sp.use_cyclic_u for sp in line.data.splines) if line.type == "CURVE" else False
    evaluated = line.evaluated_get(context.evaluated_depsgraph_get())
    me = evaluated.to_mesh()
    try:
        pts = [line.matrix_world @ v.co for v in me.vertices]
    finally:
        evaluated.to_mesh_clear()
    return pts, cyclic


def sample_polyline(pts, cyclic, step):
    """(pozitie, directie) la fiecare `step` metri de-a lungul liniei."""
    if cyclic and len(pts) > 2:
        pts = pts + [pts[0]]
    out = []
    carry = 0.0
    for a, b in zip(pts, pts[1:]):
        seg = b - a
        length = seg.length
        if length < 1e-6:
            continue
        direction = seg / length
        d = carry
        while d <= length + 1e-6 and len(out) < MAX_COPIES:
            out.append((a + direction * d, direction))
            d += step
        carry = d - length
    return out


def point_in_polygon(x, y, poly) -> bool:
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def select_only(context, objs):
    for obj in context.selected_objects:
        obj.select_set(False)
    for obj in objs:
        obj.select_set(True)
    if objs:
        context.view_layer.objects.active = objs[-1]


# ------------------------------------------------------------------------------------------ teren

def grid_mesh(name, cx, cy):
    """Placa de TILE x TILE m cu ochiuri de GRID m, UV-uri continue intre placi (texturi fara cusaturi)."""
    n = int(round(TILE / GRID))
    xs = np.linspace(-TILE / 2, TILE / 2, n + 1)
    vx, vy = np.meshgrid(xs, xs, indexing="xy")
    verts = np.stack([vx.ravel(), vy.ravel(), np.zeros(vx.size)], 1)
    faces = [(j * (n + 1) + i, j * (n + 1) + i + 1, (j + 1) * (n + 1) + i + 1, (j + 1) * (n + 1) + i)
             for j in range(n) for i in range(n)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts.tolist(), [], faces)
    loop_v = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", loop_v)
    # UV-uri mici (fata de centrul placii), dar cu acelasi rest modulo repetare: texturi continue
    ox, oy = cx % UV_REPEAT, cy % UV_REPEAT
    uv = me.uv_layers.new(name="UVMap 0")
    uvs = np.stack([(verts[loop_v, 0] + ox) / UV_REPEAT, (verts[loop_v, 1] + oy) / UV_REPEAT], 1)
    uv.data.foreach_set("uv", uvs.astype(np.float32).ravel())
    col = me.color_attributes.new(name="Color 1", type="BYTE_COLOR", domain="CORNER")
    col.data.foreach_set("color_srgb", np.ones(len(me.loops) * 4, dtype=np.float32))
    me.update()
    return me


def ground_material():
    mat = bpy.data.materials.get("harta_iarba")
    if mat is not None:
        return mat
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    path = TEX_DIR / "harta_iarba.dds"
    if not path.is_file():
        from dayzgen.dds_writer import write_dds
        from dayzgen.textures import tex_grass
        TEX_DIR.mkdir(parents=True, exist_ok=True)
        rgb, _normal = tex_grass(512, 7)
        write_dds(str(path), rgb, "DXT1")
    from dayzgen.blender_build import SollumzAPI
    mat = SollumzAPI().sm.create_shader("default.sps")
    mat.name = "harta_iarba"
    img = bpy.data.images.load(str(path), check_existing=True)
    node = mat.node_tree.nodes.get("DiffuseSampler")
    if node is not None:
        node.image = img
    return mat


# ------------------------------------------------------------------------------------------ operatori

class HartaSettings(bpy.types.PropertyGroup):
    center: bpy.props.FloatVectorProperty(
        name="Centru", size=2, default=(7500.0, -5500.0), subtype="XYZ",
        description="Centrul hartii in coordonatele GTA (implicit: ocean liber, la nord de harta dzdemo)")
    size: bpy.props.FloatProperty(name="Latura", default=1000.0, min=100.0, max=4000.0, step=10000,
                                  subtype="DISTANCE", description="Latura terenului, in metri")
    z: bpy.props.FloatProperty(name="Cota", default=20.0, subtype="DISTANCE",
                               description="Inaltimea terenului deasupra marii")
    spacing: bpy.props.FloatProperty(name="Pas", default=0.0, min=0.0, subtype="DISTANCE",
                                     description="Distanta dintre copii; 0 = lungimea obiectului (garduri lipite)")
    offset: bpy.props.FloatProperty(name="Departare de linie", default=0.0, subtype="DISTANCE",
                                    description="Copiile stau la aceasta distanta in lateral fata de linie")
    both_sides: bpy.props.BoolProperty(name="Pe ambele parti", default=False)
    count: bpy.props.IntProperty(name="Copii (fara linie)", default=10, min=2, max=500,
                                 description="Fara linie selectata, copiile merg in linie dreapta, in fata obiectului")
    scatter_count: bpy.props.IntProperty(name="Cate", default=30, min=1, max=MAX_COPIES)
    min_dist: bpy.props.FloatProperty(name="Distanta minima", default=3.0, min=0.0, subtype="DISTANCE")
    random_yaw: bpy.props.BoolProperty(name="Rotire la intamplare", default=True)
    random_scale: bpy.props.FloatProperty(name="Marime variabila", default=0.1, min=0.0, max=0.5,
                                          subtype="FACTOR", description="Cat de mult variaza marimea copiilor")
    seed: bpy.props.IntProperty(name="Seed", default=1, min=0)


class HARTA_OT_new_map(bpy.types.Operator):
    bl_idname = "harta.new_map"
    bl_label = "Harta noua"
    bl_description = "Teren plat din placi de 100 m, punctul de spawn si limitele hartii"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = context.scene.harta
        if any(o.get("harta_tip") == "teren" for o in context.scene.objects):
            self.report({"WARNING"}, "Harta are deja teren (colectia Teren). Sterge-o ca sa faci alta.")
            return {"CANCELLED"}
        coll = ensure_collection(context, GROUND)
        mat = ground_material()
        n = max(1, round(s.size / TILE))
        half = n * TILE / 2
        cx0, cy0 = s.center
        for i in range(n):
            for j in range(n):
                cx = cx0 - half + (i + 0.5) * TILE
                cy = cy0 - half + (j + 0.5) * TILE
                me = grid_mesh(f"teren_{i:02d}_{j:02d}", cx, cy)
                me.materials.append(mat)
                obj = bpy.data.objects.new(me.name, me)
                obj.location = (cx, cy, s.z)
                obj["harta_tip"] = "teren"
                obj["fivem_lod"] = GROUND_LOD
                obj.hide_select = True          # sa nu-l prinzi din greseala cand selectezi cladiri
                coll.objects.link(obj)
        spawn = bpy.data.objects.new("Spawn", None)
        spawn.empty_display_type = "SINGLE_ARROW"
        spawn.empty_display_size = 4.0
        spawn.location = (cx0, cy0, s.z + 1.0)
        spawn["harta_tip"] = "spawn"
        limits = bpy.data.objects.new("Limite harta", None)
        limits.empty_display_type = "CUBE"
        limits.location = (cx0, cy0, s.z)
        limits.scale = (half, half, 60.0)
        limits.hide_select = True
        limits["harta_tip"] = "limite"
        coll.objects.link(spawn)
        coll.objects.link(limits)
        self._frame(context)
        self.report({"INFO"}, f"Teren {n * TILE:.0f} x {n * TILE:.0f} m, {n * n} placi, la cota {s.z:.0f} m")
        return {"FINISHED"}

    @staticmethod
    def _frame(context):
        for area in context.screen.areas if context.screen else ():
            if area.type != "VIEW_3D":
                continue
            region = next((r for r in area.regions if r.type == "WINDOW"), None)
            if region is not None:
                with context.temp_override(area=area, region=region):
                    bpy.ops.view3d.view_all()
                area.spaces.active.clip_end = 10000.0


class HARTA_OT_drop(bpy.types.Operator):
    bl_idname = "harta.drop"
    bl_label = "Pune pe sol"
    bl_description = "Asaza obiectele selectate pe teren (tasta J)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(context.selected_objects)

    def execute(self, context):
        ground = Ground(context)
        if not ground:
            self.report({"WARNING"}, "Nu exista teren: fa intai o Harta noua")
            return {"CANCELLED"}
        moved = drop_to_ground(context.selected_objects, ground)
        self.report({"INFO"}, f"{moved} obiecte asezate pe sol")
        return {"FINISHED"}


class HARTA_OT_rotate90(bpy.types.Operator):
    bl_idname = "harta.rotate90"
    bl_label = "Roteste 90"
    bl_description = "Roteste obiectele selectate cu 90 de grade, fiecare in jurul lui"
    bl_options = {"REGISTER", "UNDO"}
    direction: bpy.props.IntProperty(default=1)

    @classmethod
    def poll(cls, context):
        return bool(context.selected_objects)

    def execute(self, context):
        rot = Matrix.Rotation(math.radians(90.0 * self.direction), 4, "Z")
        for obj in context.selected_objects:
            loc = obj.matrix_world.translation.copy()
            obj.matrix_world = Matrix.Translation(loc) @ rot @ Matrix.Translation(-loc) @ obj.matrix_world
        return {"FINISHED"}


class HARTA_OT_snap(bpy.types.Operator):
    bl_idname = "harta.snap"
    bl_label = "Lipeste de vecin"
    bl_description = ("Roteste obiectul activ la fel ca cel mai apropiat obiect si il lipeste de el, "
                      "cu fatadele aliniate (siruri de cladiri fara goluri)")
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        a = context.active_object
        if not is_placeable(a):
            self.report({"WARNING"}, "Selecteaza o cladire sau un obiect")
            return {"CANCELLED"}

        def xy_box(obj):
            lo, hi = local_box(obj)
            pts = [obj.matrix_world @ Vector((x, y, 0.0)) for x in (lo.x, hi.x) for y in (lo.y, hi.y)]
            return min(p.x for p in pts), max(p.x for p in pts), min(p.y for p in pts), max(p.y for p in pts)

        ax0, ax1, ay0, ay1 = xy_box(a)
        best, best_d = None, 60.0
        for obj in context.visible_objects:
            if obj is a or not is_placeable(obj):
                continue
            bx0, bx1, by0, by1 = xy_box(obj)
            d = math.hypot(max(0.0, bx0 - ax1, ax0 - bx1), max(0.0, by0 - ay1, ay0 - by1))
            if d < best_d:
                best, best_d = obj, d
        if best is None:
            self.report({"WARNING"}, "Niciun obiect la mai putin de 60 m")
            return {"CANCELLED"}

        # 1) aceeasi orientare ca vecinul (cea mai apropiata, din 90 in 90 de grade)
        yaw_n = yaw_of(best)
        delta = yaw_n + round((yaw_of(a) - yaw_n) / (math.pi / 2)) * (math.pi / 2) - yaw_of(a)
        loc = a.matrix_world.translation.copy()
        a.matrix_world = Matrix.Translation(loc) @ Matrix.Rotation(delta, 4, "Z") @ Matrix.Translation(-loc) @ a.matrix_world

        # 2) cutiile, in sistemul vecinului
        to_n = Matrix.Rotation(-yaw_n, 4, "Z") @ Matrix.Translation(-best.matrix_world.translation)

        def frame_box(obj):
            lo, hi = local_box(obj)
            pts = [to_n @ (obj.matrix_world @ Vector((x, y, lo.z))) for x in (lo.x, hi.x) for y in (lo.y, hi.y)]
            return [min(p[i] for p in pts) for i in (0, 1)], [max(p[i] for p in pts) for i in (0, 1)]

        alo, ahi = frame_box(a)
        nlo, nhi = frame_box(best)
        options = []
        for axis in (0, 1):
            if alo[axis] + ahi[axis] >= nlo[axis] + nhi[axis]:
                options.append((alo[axis] - nhi[axis], axis, -1.0))    # activul e dupa vecin: vine inapoi
            else:
                options.append((nlo[axis] - ahi[axis], axis, 1.0))     # activul e inainte: vine inainte
        gap, axis, sign = max(options)          # axa pe care stau unul langa altul
        move = [0.0, 0.0]
        move[axis] = sign * gap
        other = 1 - axis
        # fatadele in linie pe cealalta axa, cand sunt deja aproape
        d_lo, d_hi = nlo[other] - alo[other], nhi[other] - ahi[other]
        d = d_lo if abs(d_lo) <= abs(d_hi) else d_hi
        if abs(d) < 0.5 * (ahi[other] - alo[other]):
            move[other] = d
        world = Matrix.Rotation(yaw_n, 3, "Z") @ Vector((move[0], move[1], 0.0))
        a.matrix_world = Matrix.Translation(world) @ a.matrix_world
        self.report({"INFO"}, f"Lipit de {best.name}")
        return {"FINISHED"}


class HARTA_OT_draw_line(bpy.types.Operator):
    bl_idname = "harta.draw_line"
    bl_label = "Deseneaza linie"
    bl_description = ("Click stanga pe teren pune puncte; Backspace sterge ultimul punct, C inchide linia "
                      "(zona), Enter termina, Esc renunta")
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        if context.area is None or context.area.type != "VIEW_3D":
            self.report({"WARNING"}, "Porneste unealta din viewport")
            return {"CANCELLED"}
        self.points = []
        self.obj = None
        self.cyclic = False
        context.window_manager.modal_handler_add(self)
        self._header(context)
        return {"RUNNING_MODAL"}

    def _header(self, context):
        context.area.header_text_set(
            f"Linie: {len(self.points)} puncte   |   click = punct   Backspace = sterge ultimul   "
            f"C = inchide zona   Enter = gata   Esc = renunta   (rotita si butonul din mijloc misca vederea)")

    def _hit(self, context, event):
        region, rv3d = context.region, context.region_data
        coord = (event.mouse_region_x, event.mouse_region_y)
        origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        hit, loc, *_rest = context.scene.ray_cast(context.evaluated_depsgraph_get(), origin, direction)
        if hit:
            return loc
        if abs(direction.z) < 1e-6:
            return None
        t = (context.scene.harta.z - origin.z) / direction.z
        return origin + direction * t if t > 0 else None

    def _update(self, context):
        if not self.points:
            if self.obj is not None:
                bpy.data.objects.remove(self.obj)
                self.obj = None
            return
        if self.obj is None:
            curve = bpy.data.curves.new("linie", "CURVE")
            curve.dimensions = "3D"
            self.obj = bpy.data.objects.new("Linie", curve)
            self.obj["harta_tip"] = "linie"
            self.obj.show_in_front = True
            ensure_collection(context, LINES).objects.link(self.obj)
        curve = self.obj.data
        curve.splines.clear()
        spline = curve.splines.new("POLY")
        spline.points.add(len(self.points) - 1)
        for point, co in zip(spline.points, self.points):
            point.co = (co.x, co.y, co.z + 0.1, 1.0)
        spline.use_cyclic_u = self.cyclic

    def modal(self, context, event):
        if event.type in {"MIDDLEMOUSE", "WHEELUPMOUSE", "WHEELDOWNMOUSE", "TRACKPADPAN", "TRACKPADZOOM",
                          "MOUSEMOVE", "INBETWEEN_MOUSEMOVE"} or event.type.startswith("NDOF"):
            return {"PASS_THROUGH"}
        if event.value == "PRESS":
            if event.type == "LEFTMOUSE":
                hit = self._hit(context, event)
                if hit is not None:
                    self.points.append(hit.copy())
                    self._update(context)
            elif event.type == "BACK_SPACE" and self.points:
                self.points.pop()
                self._update(context)
            elif event.type == "C" and len(self.points) >= 3:
                self.cyclic = not self.cyclic
                self._update(context)
            elif event.type in {"RET", "NUMPAD_ENTER", "SPACE"}:
                return self._finish(context, keep=True)
            elif event.type in {"ESC", "RIGHTMOUSE"}:
                return self._finish(context, keep=False)
        self._header(context)
        return {"RUNNING_MODAL"}

    def _finish(self, context, keep):
        context.area.header_text_set(None)
        if self.obj is not None and (not keep or len(self.points) < 2):
            bpy.data.objects.remove(self.obj)
            self.obj = None
        if self.obj is None:
            return {"CANCELLED"}
        select_only(context, [self.obj])
        return {"FINISHED"}


class HARTA_OT_array(bpy.types.Operator):
    bl_idname = "harta.array"
    bl_label = "Multiplica"
    bl_description = ("Copii ale obiectului activ de-a lungul liniei selectate (selecteaza linia, apoi "
                      "obiectul, cu Shift). Fara linie, copiile merg drept in fata obiectului")
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        s = context.scene.harta
        src = context.active_object
        if not is_placeable(src):
            self.report({"WARNING"}, "Obiectul activ (ultimul selectat) trebuie sa fie cel de multiplicat")
            return {"CANCELLED"}
        lines = [o for o in context.selected_objects if o.get("harta_tip") == "linie"]
        lo, hi = local_box(src)
        step = s.spacing or max((hi.x - lo.x) * src.matrix_world.to_scale().x, 0.5)
        yaw0 = yaw_of(src)
        copies = []
        if lines:
            pts, cyclic = line_points(context, lines[0])
            for pos, direction in sample_polyline(pts, cyclic, step):
                # rotatia obiectului fata de axa X devine rotatia fata de linie
                yaw = math.atan2(direction.y, direction.x) + yaw0
                side = Vector((-direction.y, direction.x, 0.0))
                for k in ((1.0, -1.0) if s.both_sides else (1.0,)):
                    copies.append(place_copy(src, pos + side * (s.offset * k), yaw + (math.pi if k < 0 else 0.0)))
        else:
            forward = src.matrix_world.to_quaternion() @ Vector((1.0, 0.0, 0.0))
            forward.z = 0.0
            forward.normalize()
            for k in range(1, s.count):
                copies.append(place_copy(src, src.matrix_world.translation + forward * step * k, yaw0))
        ground = Ground(context)
        if ground:
            drop_to_ground(copies, ground)
        select_only(context, copies)
        self.report({"INFO"}, f"{len(copies)} copii, la {step:.1f} m una de alta")
        return {"FINISHED"}


class HARTA_OT_scatter(bpy.types.Operator):
    bl_idname = "harta.scatter"
    bl_label = "Imprastie in zona"
    bl_description = ("Copii la intamplare ale obiectelor selectate in interiorul liniei inchise selectate "
                      "(copaci, tufe, pietre, tomberoane)")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = context.scene.harta
        zones = [o for o in context.selected_objects if o.get("harta_tip") == "linie"]
        palette = [o for o in context.selected_objects if is_placeable(o)]
        if not zones or not palette:
            self.report({"WARNING"}, "Selecteaza o linie inchisa (zona) si obiectele de imprastiat")
            return {"CANCELLED"}
        pts, _cyclic = line_points(context, zones[0])
        poly = [(p.x, p.y) for p in pts]
        if len(poly) < 3:
            self.report({"WARNING"}, "Zona are nevoie de cel putin 3 puncte")
            return {"CANCELLED"}
        rng = random.Random(s.seed)
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        placed = []
        tries = 0
        min_d2 = s.min_dist ** 2
        while len(placed) < s.scatter_count and tries < s.scatter_count * 60:
            tries += 1
            x, y = rng.uniform(min(xs), max(xs)), rng.uniform(min(ys), max(ys))
            if point_in_polygon(x, y, poly) and all((x - px) ** 2 + (y - py) ** 2 >= min_d2 for px, py in placed):
                placed.append((x, y))
        copies = []
        for x, y in placed:
            src = rng.choice(palette)
            yaw = rng.uniform(0.0, 2.0 * math.pi) if s.random_yaw else yaw_of(src)
            scale = src.matrix_world.to_scale() * (1.0 + rng.uniform(-s.random_scale, s.random_scale))
            copies.append(place_copy(src, Vector((x, y, src.matrix_world.translation.z)), yaw, scale))
        ground = Ground(context)
        if ground:
            drop_to_ground(copies, ground)
        select_only(context, copies)
        self.report({"INFO"}, f"{len(copies)} copii in zona")
        return {"FINISHED"}


class HARTA_OT_open_library(bpy.types.Operator):
    bl_idname = "harta.open_library"
    bl_label = "Deschide biblioteca GTA"
    bl_description = "Asset Browser jos, pe biblioteca GTA V (generator): de acolo tragi modelele in scena"

    def execute(self, context):
        if open_asset_browser(context.window, context.screen) is None:
            self.report({"WARNING"}, "Nu am gasit loc pentru Asset Browser")
            return {"CANCELLED"}
        _TRIES["assets"] = 0
        bpy.app.timers.register(_set_library, first_interval=0.2)
        return {"FINISHED"}


class HARTA_OT_tool(bpy.types.Operator):
    bl_idname = "harta.tool"
    bl_label = "Unealta"
    tool: bpy.props.StringProperty()

    def execute(self, context):
        bpy.ops.wm.tool_set_by_id(name=self.tool)
        return {"FINISHED"}


class HARTA_PT_main(bpy.types.Panel):
    bl_label = "Harta"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Harta"
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        s = context.scene.harta

        box = layout.box()
        box.label(text="1. Terenul", icon="WORLD")
        if any(o.get("harta_tip") == "teren" for o in context.scene.objects):
            box.label(text="Terenul exista (colectia Teren)")
        else:
            col = box.column(align=True)
            col.prop(s, "center")
            col.prop(s, "size")
            col.prop(s, "z")
            box.operator("harta.new_map", icon="ADD")

        box = layout.box()
        box.label(text="2. Cladiri si obiecte", icon="HOME")
        box.operator("harta.open_library", icon="FILEBROWSER")
        box.label(text="Tragi modelele din Asset Browser (jos)")
        obj = context.active_object
        if obj is not None and obj.select_get():
            kind = FX.classify(obj)
            d = obj.dimensions
            text = {"gta": "model GTA", "nou": "model nou", "mlo": "interior GTA"}.get(kind, "nu se exporta")
            box.label(text=f"{obj.name}: {d.x:.1f} x {d.y:.1f} x {d.z:.1f} m ({text})")
        row = box.row(align=True)
        row.operator("harta.drop", text="Pune pe sol (J)", icon="TRIA_DOWN")
        row = box.row(align=True)
        row.operator("harta.rotate90", text="90 stanga", icon="LOOP_BACK").direction = 1
        row.operator("harta.rotate90", text="90 dreapta", icon="LOOP_FORWARDS").direction = -1
        box.operator("harta.snap", icon="SNAP_ON")

        box = layout.box()
        box.label(text="3. Linii, siruri si zone", icon="CURVE_BEZCURVE")
        box.operator("harta.draw_line", icon="CURVE_PATH")
        col = box.column(align=True)
        col.prop(s, "spacing")
        col.prop(s, "offset")
        col.prop(s, "both_sides")
        col.prop(s, "count")
        box.operator("harta.array", icon="MOD_ARRAY")
        col = box.column(align=True)
        col.prop(s, "scatter_count")
        col.prop(s, "min_dist")
        col.prop(s, "random_scale")
        col.prop(s, "random_yaw")
        col.prop(s, "seed")
        box.operator("harta.scatter", icon="PARTICLES")

        box = layout.box()
        box.label(text="4. Masurare", icon="DRIVER_DISTANCE")
        row = box.row(align=True)
        row.operator("harta.tool", text="Rigla", icon="DRIVER_DISTANCE").tool = "builtin.measure"
        row.operator("harta.tool", text="Selectie", icon="RESTRICT_SELECT_OFF").tool = "builtin.select_box"


# ------------------------------------------------------------------------------------------ ecranul

_TRIES = {"screen": 0, "assets": 0}


def _try(step, fn, *args):
    """Un pas din aranjarea ecranului; o eroare se scrie in consola si nu opreste pasii urmatori."""
    try:
        return fn(*args)
    except Exception:
        import traceback
        print(f"[harta] {step}:")
        traceback.print_exc()
        return None


def open_asset_browser(window, screen):
    """Asset Browser jos: unul existent, altfel fereastra lata de jos (Timeline in ecranul implicit)
    devine Asset Browser, altfel viewport-ul se imparte in doua. Intoarce zona sau None."""
    assets = next((a for a in screen.areas if a.ui_type == "ASSETS"), None)
    if assets is not None:
        return assets
    wide = [a for a in screen.areas if a.type != "VIEW_3D" and a.width >= window.width * 0.5]
    bottom = min(wide, key=lambda a: a.y, default=None)
    if bottom is None:
        view = max((a for a in screen.areas if a.type == "VIEW_3D"), key=lambda a: a.width * a.height, default=None)
        if view is None:
            return None
        with bpy.context.temp_override(window=window, screen=screen, area=view):
            bpy.ops.screen.area_split(direction="HORIZONTAL", factor=0.3)
        bottom = min((a for a in screen.areas if a.type == "VIEW_3D"), key=lambda a: a.y)
    with bpy.context.temp_override(window=window, screen=screen, area=bottom):
        bottom.ui_type = "ASSETS"
    target = int(window.height * 0.33)          # mai inalt, ca sa se vada miniaturile
    if bottom.height < target:
        with bpy.context.temp_override(window=window, screen=screen, area=bottom):
            _try("marit Asset Browser", bpy.ops.screen.area_move, x=bottom.x + bottom.width // 2,
                 y=bottom.y + bottom.height + 1, delta=target - bottom.height)
    return bottom


def _set_library():
    """Biblioteca GTA in Asset Browser (zona are parametri abia dupa ce s-a desenat o data)."""
    pending = False
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.ui_type != "ASSETS":
                continue
            params = getattr(area.spaces.active, "params", None)
            if params is None:
                pending = True
                continue
            if getattr(params, "asset_library_reference", None) != LIBRARY_NAME:
                _try("aleasa biblioteca GTA", setattr, params, "asset_library_reference", LIBRARY_NAME)
            area.tag_redraw()
    _TRIES["assets"] += 1
    return 0.3 if pending and _TRIES["assets"] < 30 else None


def _setup_viewport(area):
    space = area.spaces.active
    space.clip_start = 0.1
    space.clip_end = 10000.0
    space.shading.type = "SOLID"
    space.shading.color_type = "TEXTURE"
    space.show_region_ui = True


def _setup_import_method():
    lib = bpy.context.preferences.filepaths.asset_libraries.get(LIBRARY_NAME)
    if lib is not None and getattr(lib, "import_method", "APPEND_REUSE") != "APPEND_REUSE":
        lib.import_method = "APPEND_REUSE"      # tras in scena, modelul GTA se poate muta (cu Link nu)


def _setup_screen():
    """La pornire si la fiecare fisier deschis: viewport cu texturi, Asset Browser jos, biblioteca GTA."""
    windows = list(bpy.context.window_manager.windows)
    if not windows or any(w.screen is None for w in windows):
        _TRIES["screen"] += 1                   # fereastra nu e gata inca
        return 0.5 if _TRIES["screen"] < 40 else None
    _try("metoda de import", _setup_import_method)
    for window in windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                _try("viewport", _setup_viewport, area)
        _try("Asset Browser", open_asset_browser, window, window.screen)
    _TRIES["assets"] = 0
    bpy.app.timers.register(_set_library, first_interval=0.3, persistent=True)
    return None


@bpy.app.handlers.persistent
def _on_load(_dummy):
    _TRIES["screen"] = 0
    bpy.app.timers.register(_setup_screen, first_interval=0.3, persistent=True)


KEYMAPS = []


def _register_keys():
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc is None:
        return
    km = kc.keymaps.new(name="Object Mode", space_type="EMPTY")
    KEYMAPS.append((km, km.keymap_items.new("harta.drop", "J", "PRESS")))
    KEYMAPS.append((km, km.keymap_items.new("view3d.view_selected", "F", "PRESS")))


CLASSES = (HartaSettings, HARTA_OT_new_map, HARTA_OT_drop, HARTA_OT_rotate90, HARTA_OT_snap, HARTA_OT_draw_line,
           HARTA_OT_array, HARTA_OT_scatter, HARTA_OT_open_library, HARTA_OT_tool, HARTA_PT_main)


def register():
    for cls in CLASSES:
        old = getattr(bpy.types, cls.__name__, None)
        if old is not None:
            try:
                bpy.utils.unregister_class(old)
            except RuntimeError:
                pass
        bpy.utils.register_class(cls)
    bpy.types.Scene.harta = bpy.props.PointerProperty(type=HartaSettings)
    _register_keys()
    if not bpy.app.background:
        handlers = bpy.app.handlers.load_post
        for handler in [h for h in handlers if getattr(h, "__name__", "") == "_on_load"]:
            handlers.remove(handler)
        handlers.append(_on_load)
        bpy.app.timers.register(_setup_screen, first_interval=0.5, persistent=True)


if __name__ == "__main__":
    register()

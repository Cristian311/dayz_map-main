# -*- coding: utf-8 -*-
"""
Construieste obiectele Blender (teren pe tile-uri cu LOD-uri, cladiri), materialele Sollumz
(shader de teren cu 4 straturi, normal.sps pentru cladiri), coliziunile si exporta .ydr binar.
Ruleaza DOAR in Blender, cu Sollumz + szio + pymateria disponibile.
"""
import importlib
import os
import numpy as np
import bpy

from . import config as C
from .buildings import MAT_WALL, MAT_ROOF, MAT_WINDOW, MAT_DOOR, MAT_BRICK

TERRAIN_SHADER = "terrain_cb_w_4lyr.sps"
BUILDING_SHADER = "normal.sps"
LAYER_ORDER = ["grass", "dirt", "rock", "sand"]           # layer0..3 din shader-ul de teren
COL_MAT_BY_LAYER = ["GRASS", "DIRT_TRACK", "ROCK", "SAND_LOOSE"]
COL_MAT_WALL = {"plaster": "PLASTER_SOLID", "wood": "WOOD_SOLID_MEDIUM", "brick": "BRICK"}
COL_MAT_ROOF = {"rooftile": "ROOF_TILE", "metal": "METAL_CORRUGATED_IRON"}
DEFAULT_FLAGS1 = ["map_weapon", "map_dynamic", "map_animal", "map_cover", "map_vehicle"]
DEFAULT_FLAGS2 = ["vehicle_non_bvh", "vehicle_bvh", "ped", "ragdoll", "animal", "animal_ragdoll",
                  "object", "object_env_cloth", "plant", "projectile", "explosion", "pickup", "foliage",
                  "forklift_forks", "test_weapon", "test_camera", "test_ai", "test_script",
                  "test_vehicle_wheel", "glass", "river", "smoke", "unsmashed", "stair_slope", "deep_surface"]


class SollumzAPI:
    """Gaseste si activeaza Sollumz (extensie sau addon legacy) si expune modulele de care avem nevoie."""

    def __init__(self, log=print):
        import addon_utils
        pkg = None
        for mod in addon_utils.modules():
            nm = mod.__name__
            if nm.split(".")[-1].lower() in ("sollumz", "sollumz_dev"):
                pkg = nm
                break
        if pkg is None:
            raise RuntimeError("Sollumz nu a fost gasit. Ruleaza INSTALEAZA_TOOLS.bat sau instaleaza Sollumz in Blender.")
        if pkg not in bpy.context.preferences.addons:
            log(f"  activez {pkg} ...")
            bpy.ops.preferences.addon_enable(module=pkg)
        self.pkg = pkg
        imp = lambda m: importlib.import_module(f"{pkg}.{m}")
        self.deps = imp("dependencies")
        if not self.deps.IS_SZIO_AVAILABLE:
            raise RuntimeError("Dependinta 'szio' lipseste (Sollumz -> Install Dependencies sau INSTALEAZA_TOOLS.bat).")
        if not self.deps.IS_SZIO_NATIVE_AVAILABLE:
            raise RuntimeError("Dependinta 'pymateria' lipseste: fara ea nu se pot scrie fisiere binare GTA V.")
        self.props = imp("sollumz_properties")
        self.sm = imp("ydr.shader_materials")
        self.dh = imp("tools.drawablehelper")
        self.bh = imp("tools.boundhelper")
        self.blh = imp("tools.blenderhelper")
        self.cm = imp("ybn.collision_materials")
        self.SollumType = self.props.SollumType
        self.LODLevel = self.props.LODLevel
        self._col_cache = {}
        self._col_index = {m.name: i for i, m in enumerate(self.cm.collisionmats)}

    def collision_material(self, name: str):
        if name not in self._col_cache:
            idx = self._col_index.get(name, 0)
            mat = self.cm.create_collision_material_from_index(idx)
            mat.name = f"col_{name.lower()}"
            self._col_cache[name] = mat
        return self._col_cache[name]


# ------------------------------------------------------------------------------------------ mesh utils

def _flat(a):
    return np.ascontiguousarray(a, dtype=np.float32).ravel()


def new_mesh(name, verts, faces, uv_loop=None, uv1_loop=None, color2_loop=None, normals=None,
             mat_index=None, smooth=True):
    """
    verts: (V,3); faces: lista de liste de indici; uv_loop: (L,2) per colt de fata (ordinea from_pydata);
    color2_loop: (L,4) sRGB; normals: (V,3) normale custom per vertex; mat_index: (F,) int.
    """
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [list(map(int, f)) for f in faces])
    me.update()
    nloops = len(me.loops)
    c1 = me.attributes.new(name="Color 1", type="BYTE_COLOR", domain="CORNER")
    c1.data.foreach_set("color_srgb", np.ones(nloops * 4, dtype=np.float32))
    if color2_loop is not None:
        c2 = me.attributes.new(name="Color 2", type="BYTE_COLOR", domain="CORNER")
        c2.data.foreach_set("color_srgb", _flat(color2_loop))
    if uv_loop is not None:
        uv0 = me.attributes.new(name="UVMap 0", type="FLOAT2", domain="CORNER")
        uv0.data.foreach_set("vector", _flat(uv_loop))
    if uv1_loop is not None:
        uv1 = me.attributes.new(name="UVMap 1", type="FLOAT2", domain="CORNER")
        uv1.data.foreach_set("vector", _flat(uv1_loop))
    if mat_index is not None:
        me.polygons.foreach_set("material_index", np.asarray(mat_index, dtype=np.int32))
    if smooth:
        me.shade_smooth()
    if normals is not None:
        me.normals_split_custom_set_from_vertices([tuple(map(float, n)) for n in normals])
    me.update()
    return me


def link_object(name, mesh, collection):
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


# ------------------------------------------------------------------------------------------ builder

class BlenderBuilder:
    def __init__(self, cfg: C.MapConfig, world, texs: dict, bdefs: dict, log=print):
        self.cfg = cfg
        self.world = world
        self.texs = texs
        self.bdefs = bdefs
        self.log = log
        self.sz = SollumzAPI(log)
        self.collection = None
        self.images = {}
        self.terrain_mat = None
        self.building_mats = {}
        self.bounds = {}        # nume drawable -> (bbmin, bbmax) numpy
        self.tile_names = {}    # (ti,tj) -> nume drawable
        self.building_names = {}  # cheie -> nume drawable
        self.drawables = []
        self.tile_col_meshes = {}      # (ti,tj) -> mesh de coliziune al tile-ului (coordonate locale)
        self.building_col_meshes = {}  # cheie cladire -> mesh de coliziune (coordonate locale)
        self.composites = []           # obiectele BOUND_COMPOSITE de nivel superior (-> .ybn)
        self.col_names = {}            # (ti,tj) -> numele fisierului .ybn (fara extensie)

    # ---------------------------------------------------------------- scena
    def setup_scene(self):
        bpy.ops.wm.read_homefile(use_empty=True)
        scene = bpy.context.scene
        scene.unit_settings.system = "METRIC"
        self.collection = bpy.data.collections.new(self.cfg.name)
        scene.collection.children.link(self.collection)
        # setari Sollumz relevante
        scene.create_seperate_drawables = True
        scene.auto_create_embedded_col = False
        scene.center_drawable_to_selection = False

    # ---------------------------------------------------------------- imagini / materiale
    def _image(self, key: str, normal: bool = False):
        info = self.texs[key]
        name = info["name_n"] if normal else info["name"]
        if name in self.images:
            return self.images[name]
        path = info["normal"] if normal else info["diffuse"]
        png = os.path.splitext(path)[0] + ".png"
        # Blender incarca mai sigur PNG-ul; numele texturii (fara extensie) este identic cu al DDS-ului
        load_path = png if os.path.exists(png) else path
        img = bpy.data.images.load(load_path, check_existing=True)
        img.name = name
        if normal:
            img.colorspace_settings.name = "Non-Color"
        self.images[name] = img
        return img

    def _set_node_image(self, mat, node_name, img):
        node = mat.node_tree.nodes.get(node_name)
        if node is None:
            return False
        node.image = img
        node.texture_properties.embedded = False
        return True

    def make_terrain_material(self):
        if self.terrain_mat:
            return self.terrain_mat
        mat = self.sz.sm.create_shader(TERRAIN_SHADER)
        mat.name = f"{self.cfg.name}_terrain"
        for i, key in enumerate(LAYER_ORDER):
            self._set_node_image(mat, f"TextureSampler_layer{i}", self._image(key))
            self._set_node_image(mat, f"BumpSampler_layer{i}", self._image(key, normal=True))
        self.terrain_mat = mat
        return mat

    def make_building_material(self, tex_key: str):
        if tex_key in self.building_mats:
            return self.building_mats[tex_key]
        mat = self.sz.sm.create_shader(BUILDING_SHADER)
        mat.name = f"{self.cfg.name}_{tex_key}"
        self._set_node_image(mat, "DiffuseSampler", self._image(tex_key))
        self._set_node_image(mat, "BumpSampler", self._image(tex_key, normal=True))
        self.building_mats[tex_key] = mat
        return mat

    # ---------------------------------------------------------------- drawable helpers
    def _make_drawable(self, name, mesh_high, mesh_med=None, mesh_low=None, lod_dists=(9998, 9998, 9998, 9998)):
        obj = link_object(name, mesh_high, self.collection)
        drawable = self.sz.dh.convert_obj_to_drawable(obj)
        drawable.name = name
        obj.name = f"{name}.model"
        lods = obj.sz_lods
        if mesh_med is not None:
            lods.get_lod(self.sz.LODLevel.MEDIUM).mesh = mesh_med
        if mesh_low is not None:
            lods.get_lod(self.sz.LODLevel.LOW).mesh = mesh_low
        lods.active_lod_level = self.sz.LODLevel.HIGH
        dp = drawable.drawable_properties
        dp.lod_dist_high, dp.lod_dist_med, dp.lod_dist_low, dp.lod_dist_vlow = lod_dists
        return drawable, obj

    # ---------------------------------------------------------------- coliziuni (.ybn)
    def _new_composite(self, name):
        """Un BOUND_COMPOSITE de nivel superior (fara parinte) -> Sollumz il exporta ca <name>.ybn."""
        obj = bpy.data.objects.new(name, None)
        obj.empty_display_size = 0
        obj.sollum_type = self.sz.SollumType.BOUND_COMPOSITE
        self.collection.objects.link(obj)
        # compozitul si copiii BVH stau la 0,0,0; pozitiile mondiale sunt in vertecsii mesh-urilor (vezi _add_bvh)
        obj.location = (0.0, 0.0, 0.0)
        return obj

    def _add_bvh(self, composite, name, mesh_col, world_pos, yaw=0.0):
        """
        Un copil BOUND_GEOMETRYBVH la 0,0,0; mesh-ul de coliziune e COPIAT si mutat in coordonate mondiale.
        Regula Sollumz (tutorial "Creating Static Collisions"): compozitul si BVH-urile stau la origine, doar
        vertecsii poarta pozitia. Daca BVH-ul e pozitionat prin transform, exportul scrie AABB-urile copiilor
        in spatiul local (in jurul lui 0,0,0) si jocul nu gaseste niciodata coliziunea la pozitia reala.
        """
        from mathutils import Matrix
        me = mesh_col.copy()
        me.name = f"{name}.colmesh"
        me.transform(Matrix.Translation((float(world_pos[0]), float(world_pos[1]), float(world_pos[2])))
                     @ Matrix.Rotation(float(yaw or 0.0), 4, "Z"))
        me.update()
        poly = link_object(name, me, self.collection)
        poly.location = (0.0, 0.0, 0.0)
        bvh = self.sz.bh.convert_obj_to_bvh(poly, bpy.context.scene.sz_default_flag_preset_name)
        bvh.name = f"{name}.bvh"
        bvh.parent = composite
        bvh.location = (0.0, 0.0, 0.0)
        return bvh

    def build_collisions(self):
        """
        Cate un .ybn per tile de teren: teren + cladirile care cad in tile, in coordonate mondiale.
        GTA activeaza fizica statica pe o zona doar daca exista bounds statice (.ybn) care o acopera,
        de aceea coliziunea NU mai sta in .ydr.
        """
        cfg = self.cfg
        ox, oy = cfg.origin_x, cfg.origin_y
        ts = cfg.tile_size
        nt = self.world.tile_count()
        # cladirile grupate pe tile
        per_tile = {}
        for b in self.world.buildings:
            ti = min(max(int(b.x // ts), 0), nt - 1)
            tj = min(max(int(b.y // ts), 0), nt - 1)
            per_tile.setdefault((ti, tj), []).append(b)

        nb = 0
        for (ti, tj), tname in self.tile_names.items():
            col_name = f"{tname}_col"
            composite = self._new_composite(col_name)
            cx = (ti + 0.5) * ts
            cy = (tj + 0.5) * ts
            self._add_bvh(composite, f"{tname}_terrain", self.tile_col_meshes[(ti, tj)], (ox + cx, oy + cy, 0.0))
            for k, b in enumerate(per_tile.get((ti, tj), [])):
                me = self.building_col_meshes.get(b.name)
                if me is None:
                    continue
                self._add_bvh(composite, f"{tname}_b{k:03d}_{b.name}", me,
                              (ox + b.x, oy + b.y, b.z), yaw=b.yaw)
                nb += 1
            self._ensure_bound_flags(composite)
            self.col_names[(ti, tj)] = col_name
            self.composites.append(composite)
        bpy.context.view_layer.update()
        self.log(f"  coliziuni: {len(self.composites)} compozite .ybn ({nb} cladiri incluse)")

    def _ensure_bound_flags(self, composite):
        """Daca preset-ul de flags nu s-a aplicat (headless), setam flag-urile standard de coliziune statica."""
        for child in composite.children_recursive:
            if not hasattr(child, "composite_flags1"):
                continue
            names = list(type(child.composite_flags1).__annotations__.keys())
            if any(getattr(child.composite_flags1, n) for n in names):
                continue
            for n in DEFAULT_FLAGS1:
                if n in names:
                    setattr(child.composite_flags1, n, True)
            for n in DEFAULT_FLAGS2:
                if n in names:
                    setattr(child.composite_flags2, n, True)

    # ---------------------------------------------------------------- teren
    def _tile_arrays(self, tg, cx, cy):
        h = tg["h"]
        n = h.shape[0]
        xs = tg["x"] - cx
        ys = tg["y"] - cy
        X, Y = np.meshgrid(xs, ys)
        verts = np.stack([X.ravel(), Y.ravel(), h.ravel()], axis=1)
        i, j = np.meshgrid(np.arange(n - 1), np.arange(n - 1), indexing="ij")
        v00 = (i * n + j).ravel()
        faces = np.stack([v00, v00 + 1, v00 + n + 1, v00 + n], axis=1)  # CCW vazut de sus (+Z)
        s = self.cfg.terrain_uv_scale
        uv_vert = np.stack([(X.ravel() + cx) / s, (Y.ravel() + cy) / s], axis=1)
        uv_loop = uv_vert[faces.ravel()]
        uv1_loop = uv_loop * 0.25
        g = tg["g"].ravel()
        b = tg["b"].ravel()
        col_vert = np.stack([np.zeros_like(g), g, b, np.ones_like(g)], axis=1)
        col_loop = col_vert[faces.ravel()]
        normals = tg["n"].reshape(-1, 3)
        dom = tg["dom"].ravel()[v00]  # materialul de coliziune dupa stratul dominant al primului colt
        return verts, faces, uv_loop, uv1_loop, col_loop, normals, dom

    def build_tiles(self):
        cfg = self.cfg
        mat = self.make_terrain_material()
        col_mats = [self.sz.collision_material(n) for n in COL_MAT_BY_LAYER]
        nt = self.world.tile_count()
        total = nt * nt
        k = 0
        for tj in range(nt):
            for ti in range(nt):
                k += 1
                name = f"{cfg.name}_t_{ti:02d}_{tj:02d}"
                cx = (ti + 0.5) * cfg.tile_size
                cy = (tj + 0.5) * cfg.tile_size
                meshes = []
                for lvl, step in (("high", 1), ("med", 2), ("low", 4)):
                    tg = self.world.tile_grid(ti, tj, step)
                    verts, faces, uv, uv1, col, nrm, dom = self._tile_arrays(tg, cx, cy)
                    me = new_mesh(f"{name}_{lvl}", verts, faces, uv, uv1, col, nrm)
                    me.materials.append(mat)
                    meshes.append(me)
                    if lvl == "high":
                        self.bounds[name] = (verts.min(axis=0), verts.max(axis=0))
                        me_col = new_mesh(f"{name}_col", verts, faces, mat_index=dom, smooth=False)
                        for cm in col_mats:
                            me_col.materials.append(cm)
                drawable, obj = self._make_drawable(name, meshes[0], meshes[1], meshes[2],
                                                    (220.0, 480.0, 9998.0, 9998.0))
                # coliziunea NU se pune in .ydr; merge in .ybn-ul tile-ului (vezi build_collisions)
                self.tile_col_meshes[(ti, tj)] = me_col
                self.tile_names[(ti, tj)] = name
                self.drawables.append(drawable)
                if k % 8 == 0 or k == total:
                    self.log(f"  tile-uri: {k}/{total}")

    # ---------------------------------------------------------------- cladiri
    def build_buildings(self):
        cfg = self.cfg
        for key, bdef in self.bdefs.items():
            m = bdef["mesh"]
            name = f"{cfg.name}_{key}"
            verts = m["verts"]
            faces = m["faces"]
            uv_loop = np.array([t for face_uv in m["uvs"] for t in face_uv], dtype=np.float32)
            mats = np.array(m["mats"], dtype=np.int32)
            me = new_mesh(name + "_high", verts, faces, uv_loop, uv_loop.copy(), None, None, mats, smooth=False)
            slot_mats = [self.make_building_material(bdef["wall_tex"]), self.make_building_material(bdef["roof_tex"]),
                         self.make_building_material("window"), self.make_building_material("door"),
                         self.make_building_material("brick")]
            for sm in slot_mats:
                me.materials.append(sm)
            # coliziune: doar fetele marcate (pereti, acoperis, cos)
            col_faces = [f for f, c in zip(faces, m["collision"]) if c]
            col_mats_idx = [mi for mi, c in zip(m["mats"], m["collision"]) if c]
            col_slot_names = [COL_MAT_WALL[bdef["wall_tex"]], COL_MAT_ROOF[bdef["roof_tex"]], "GLASS_SHOOT_THROUGH",
                              "WOOD_SOLID_MEDIUM", "BRICK"]
            me_col = new_mesh(name + "_col", verts, col_faces, mat_index=col_mats_idx, smooth=False)
            for cn in col_slot_names:
                me_col.materials.append(self.sz.collision_material(cn))
            drawable, obj = self._make_drawable(name, me, None, None, (9998.0, 9998.0, 9998.0, 9998.0))
            # coliziunea merge in .ybn-ul tile-ului in care e plasata cladirea
            self.building_col_meshes[key] = me_col
            self.bounds[name] = (verts.min(axis=0), verts.max(axis=0))
            self.building_names[key] = name
            self.drawables.append(drawable)
        self.log(f"  cladiri: {len(self.bdefs)} arhetipuri")

    # ---------------------------------------------------------------- export
    def export_drawables(self, out_dir: str, gen9: bool = False):
        os.makedirs(out_dir, exist_ok=True)
        versions = {"GEN9"} if gen9 else {"GEN8"}
        self.log(f"  export Sollumz ({'gen9' if gen9 else 'gen8'}) -> {out_dir}")
        res = bpy.ops.sollumz.export_assets(directory=out_dir, direct_export=True, use_custom_settings=True,
                                            target_formats={"NATIVE"}, target_versions=versions,
                                            limit_to_selected=False, apply_transforms=False)
        missing = [d.name for d in self.drawables if not os.path.exists(os.path.join(out_dir, d.name.lower() + ".ydr"))]
        if missing:
            raise RuntimeError(f"Export esuat pentru {len(missing)} drawable-uri, ex: {missing[:5]} (rezultat {res})")
        missing_col = [c.name for c in self.composites
                       if not os.path.exists(os.path.join(out_dir, c.name.lower() + ".ybn"))]
        if missing_col:
            raise RuntimeError(f"Export esuat pentru {len(missing_col)} coliziuni .ybn, ex: {missing_col[:5]} "
                               f"(rezultat {res}) - fara .ybn nimic nu e solid in joc")
        self.log(f"  export OK: {len(self.drawables)} fisiere .ydr, {len(self.composites)} fisiere .ybn")

    def save_blend(self, path: str):
        bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
        self.log(f"  scena salvata: {path}")

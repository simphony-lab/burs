"""Shared building blocks for the blocky movie: textures, flat materials, voxel world with all locations,
characters with actions, held items, particle effects, cameras and rendering/projection export.
Runs inside the Blender Python module (bpy)."""
import json
import math
import os
import random

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Euler, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "unifont.otf")
FPS = 24
PX = 0.9 / 16  # one skin pixel in world units

SKY_TOP = (110, 160, 248)
SKY_HORIZON = (196, 222, 252)
HAZE = (214, 226, 240)
FOG = dict(start=24.0, end=85.0)
OCEAN_X = 1000.0  # ocean location, far from the land

rng = np.random.default_rng(7)


def srgb_to_lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lin(rgb):
    return tuple(srgb_to_lin(v) for v in rgb) + (1.0,)


# ============================================================================ textures

def new_image(name, arr):
    arr = np.asarray(arr)
    h, w = arr.shape[:2]
    if arr.shape[2] == 3:
        arr = np.concatenate([arr, np.full((h, w, 1), 255, np.uint8)], axis=2)
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set((np.flipud(arr).astype(np.float32) / 255.0).ravel())
    img.pack()
    return img


def noisy(base, var, size=(16, 16)):
    return np.array(base, np.float32)[None, None, :] + rng.uniform(-var, var, size + (1,))


def clip(a):
    return np.clip(a, 0, 255).astype(np.uint8)


def t_grass_top():
    a = noisy((96, 158, 56), 14)
    a[rng.random((16, 16)) < 0.18] *= 0.82
    return clip(a)


def t_dirt():
    a = noisy((134, 96, 67), 10)
    a[rng.random((16, 16)) < 0.15] = (100, 72, 50)
    return clip(a)


def t_grass_side():
    a = t_dirt().astype(np.float32)
    g = noisy((96, 158, 56), 12)
    a[:3] = g[:3]
    drip = rng.random(16) < 0.5
    a[3][drip] = g[3][drip]
    return clip(a)


def t_tile():
    a = noisy((196, 192, 184), 6)
    a[0, :] = a[:, 0] = (156, 152, 146)
    a[8, :] = a[:, 8] = (170, 166, 160)
    return clip(a)


def t_pave():
    a = noisy((176, 160, 150), 10)
    for r in range(16):
        if r % 4 == 0:
            a[r, :] = (128, 116, 110)
        off = 0 if (r // 4) % 2 == 0 else 4
        for c in range(16):
            if (c + off) % 8 == 0:
                a[r, c] = (128, 116, 110)
    return clip(a)


def t_planks(base=(168, 134, 82), dark=(112, 86, 52)):
    a = noisy(base, 8)
    for r in range(16):
        if r % 4 == 3:
            a[r, :] = dark
    for i, r0 in enumerate(range(0, 16, 4)):
        a[r0:r0 + 3, (5 + i * 7) % 16] = np.array(dark) * 1.15
    return clip(a)


def t_log_side():
    a = noisy((104, 82, 50), 8)
    a[:, ::3] *= 0.8
    return clip(a)


def t_log_top():
    a = np.zeros((16, 16, 3), np.float32)
    for r in range(16):
        for c in range(16):
            d = max(abs(r - 7.5), abs(c - 7.5))
            a[r, c] = (104, 82, 50) if d > 6.5 else ((178, 146, 92) if int(d) % 2 else (150, 120, 74))
    return clip(a + rng.uniform(-6, 6, (16, 16, 1)))


def t_leaves():
    a = noisy((62, 128, 44), 16)
    a[rng.random((16, 16)) < 0.3] = (40, 88, 30)
    return clip(a)


def t_bricks(base=(132, 132, 132), mortar=(92, 92, 92)):
    a = noisy(base, 8)
    for r in range(16):
        if r % 8 == 7:
            a[r, :] = mortar
        off = 0 if (r // 8) % 2 == 0 else 8
        a[r, (15 - off) % 16] = mortar
    return clip(a)


def t_cobble():
    a = noisy((122, 122, 122), 12)
    for _ in range(14):
        y, x = rng.integers(0, 16, 2)
        a[max(0, y - 1):y + 2, max(0, x - 2):x + 2] = rng.uniform(95, 150)
    a[rng.random((16, 16)) < 0.12] = (80, 80, 80)
    return clip(a)


def t_water():
    a = noisy((52, 96, 214), 10)
    for r in range(0, 16, 5):
        s = int(rng.integers(0, 10))
        a[r, s:s + 5] = (110, 150, 240)
    return clip(a)


def t_glass():
    a = noisy((196, 226, 240), 4)
    a[0, :] = a[15, :] = a[:, 0] = a[:, 15] = (236, 240, 244)
    a[3:6, 10] = (250, 252, 255)
    a[4, 9:12] = (250, 252, 255)
    return clip(a)


def t_lamp():
    a = noisy((250, 214, 120), 8)
    a[0, :] = a[15, :] = a[:, 0] = a[:, 15] = (70, 60, 50)
    return clip(a)


def t_sand():
    a = noisy((222, 206, 150), 10)
    a[rng.random((16, 16)) < 0.12] = (200, 182, 128)
    return clip(a)


def t_farmland():
    a = noisy((96, 64, 40), 8)
    for r in range(16):
        if r % 4 == 1:
            a[r, :] *= 0.75
    for _ in range(10):
        y, x = rng.integers(1, 15, 2)
        a[y, x] = (90, 190, 60)
        a[y - 1, x] = (120, 210, 70)
    return clip(a)


def t_craft_top():
    a = t_planks().astype(np.float32)
    a[2:14, 2:14] = (150, 112, 64)
    a[2:14, 7:9] = (90, 66, 40)
    a[7:9, 2:14] = (90, 66, 40)
    return clip(a)


def t_chest():
    a = noisy((160, 110, 50), 8)
    a[0, :] = a[15, :] = a[:, 0] = a[:, 15] = (70, 46, 20)
    a[6, :] = (70, 46, 20)
    a[5:9, 7:9] = (200, 200, 200)
    return clip(a)


def t_wool(rgb):
    a = noisy(rgb, 8)
    a[rng.random((16, 16)) < 0.2] *= 0.88
    return clip(a)


def t_seat():
    return t_planks((120, 84, 52), (80, 56, 34))


# ============================================================================ materials

def flat_material(name, image=None, color=None, fog=True, unlit=False, hurt=False, strength=1.0, dark=True):
    """Texture * fixed per-face brightness (Minecraft-like), darkened underground, faded into haze.
    hurt=True adds a value node 'hurt' (0..1) that tints the material red."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = strength
    if image is not None:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = image
        tex.interpolation = "Closest"
        col = tex.outputs["Color"]
    else:
        rgbn = nt.nodes.new("ShaderNodeRGB")
        rgbn.outputs[0].default_value = lin(color)
        col = rgbn.outputs[0]

    def mathnode(op, a=None, b=None, c=None):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        for i, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                nt.links.new(v, n.inputs[i])
        return n.outputs[0]

    def mix_rgb(fac, a, b, blend="MIX"):
        m = nt.nodes.new("ShaderNodeMix")
        m.data_type = "RGBA"
        m.blend_type = blend
        if isinstance(fac, (int, float)):
            m.inputs[0].default_value = fac
        else:
            nt.links.new(fac, m.inputs[0])
        for idx, v in ((6, a), (7, b)):
            if isinstance(v, tuple):
                m.inputs[idx].default_value = v
            else:
                nt.links.new(v, m.inputs[idx])
        return m.outputs[2]

    if hurt:
        hv = nt.nodes.new("ShaderNodeValue")
        hv.name = "hurt"
        hv.outputs[0].default_value = 0.0
        fac = mathnode("MULTIPLY", hv.outputs[0], 0.65)
        col = mix_rgb(fac, col, (0.9, 0.02, 0.02, 1.0))

    if not unlit:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Normal"], sep.inputs[0])
        top = mathnode("MULTIPLY_ADD", sep.outputs["Z"], 0.22, 0.80)
        ax = mathnode("ABSOLUTE", sep.outputs["X"])
        b = mathnode("MULTIPLY_ADD", ax, -0.10, top)
        if dark:
            psep = nt.nodes.new("ShaderNodeSeparateXYZ")
            nt.links.new(geo.outputs["Position"], psep.inputs[0])
            mr = nt.nodes.new("ShaderNodeMapRange")
            mr.inputs["From Min"].default_value = -5.0
            mr.inputs["From Max"].default_value = -1.2
            mr.inputs["To Min"].default_value = 0.42
            mr.inputs["To Max"].default_value = 1.0
            nt.links.new(psep.outputs["Z"], mr.inputs["Value"])
            b = mathnode("MULTIPLY", b, mr.outputs[0])
        comb = nt.nodes.new("ShaderNodeCombineXYZ")
        for i in range(3):
            nt.links.new(b, comb.inputs[i])
        col = mix_rgb(1.0, col, comb.outputs[0], blend="MULTIPLY")

    if fog:
        cam = nt.nodes.new("ShaderNodeCameraData")
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = FOG["start"]
        mr.inputs["From Max"].default_value = FOG["end"]
        mr.inputs["To Max"].default_value = 0.94
        nt.links.new(cam.outputs["View Distance"], mr.inputs["Value"])
        col = mix_rgb(mr.outputs[0], col, lin(HAZE))
    nt.links.new(col, emit.inputs["Color"])
    nt.links.new(emit.outputs[0], out.inputs[0])
    return mat


# ============================================================================ voxel meshing

FACES = {
    "py": ((0, 1, 0), [(1, 1, 0), (0, 1, 0), (0, 1, 1), (1, 1, 1)]),
    "ny": ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
    "px": ((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]),
    "nx": ((-1, 0, 0), [(0, 1, 0), (0, 0, 0), (0, 0, 1), (0, 1, 1)]),
    "pz": ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]),
    "nz": ((0, 0, -1), [(0, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0)]),
}
UV4 = [(0, 0), (1, 0), (1, 1), (0, 1)]


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def build_mesh(name, verts, faces, uvs, mat_idx, materials):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    uvl = me.uv_layers.new(name="UV")
    uvl.data.foreach_set("uv", [c for f in uvs for uv in f for c in uv])
    for m in materials:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", mat_idx)
    me.update()
    return link(bpy.data.objects.new(name, me))


def mesh_voxels(name, blocks, block_tex, mats, scale=1.0, origin=(0.0, 0.0, 0.0)):
    mat_names = sorted({n for t in block_tex.values() for n in t.values()})
    mindex = {n: i for i, n in enumerate(mat_names)}
    verts, faces, uvs, midx = [], [], [], []
    ox, oy, oz = origin
    for (x, y, z), t in blocks.items():
        for key, (n, corners) in FACES.items():
            if (x + n[0], y + n[1], z + n[2]) in blocks:
                continue
            slot = "top" if key == "pz" else ("bottom" if key == "nz" else "side")
            i0 = len(verts)
            for cx, cy, cz in corners:
                verts.append(((x + cx) * scale + ox, (y + cy) * scale + oy, (z + cz) * scale + oz))
            faces.append((i0, i0 + 1, i0 + 2, i0 + 3))
            uvs.append(UV4)
            midx.append(mindex[block_tex[t][slot]])
    return build_mesh(name, verts, faces, uvs, midx, [mats[n] for n in mat_names])


def cube_mesh(name, size, mat, center=True):
    """Plain cube (used for particles), shares mesh data per material."""
    key = f"cube_{mat.name}_{size:.4f}"
    me = bpy.data.meshes.get(key)
    if me is None:
        h = size / 2 if center else 0
        verts, faces, uvs = [], [], []
        for k, (n, corners) in FACES.items():
            i0 = len(verts)
            for cx, cy, cz in corners:
                verts.append((cx * size - h, cy * size - h, cz * size - h))
            faces.append((i0, i0 + 1, i0 + 2, i0 + 3))
            uvs.append(UV4)
        me = bpy.data.meshes.new(key)
        me.from_pydata(verts, [], faces)
        me.uv_layers.new(name="UV").data.foreach_set("uv", [c for f in uvs for uv in f for c in uv])
        me.materials.append(mat)
        me.update()
    return link(bpy.data.objects.new(name, me))


# ============================================================================ keyframes

class Keys:
    """Collects keyframes; 'tween' holds the previous value until the transition starts."""

    def __init__(self):
        self.tracks = {}
        self.nodes = []

    def set(self, obj, path, f, val):
        self.tracks.setdefault((obj.name, path), {})[int(round(f))] = tuple(val) if hasattr(val, "__len__") else val

    def value_at(self, obj, path, f):
        tr = self.tracks.get((obj.name, path), {})
        prev = [k for k in tr if k <= f]
        if prev:
            return tr[max(prev)]
        v = getattr(obj, path)
        return tuple(v) if hasattr(v, "__len__") else v

    def tween(self, obj, path, f0, f1, val):
        self.set(obj, path, f0, self.value_at(obj, path, f0))
        self.set(obj, path, f1, val)

    def hold(self, obj, path, f):
        self.set(obj, path, f, self.value_at(obj, path, f))

    def node(self, mat, node, f, v):
        self.nodes.append((mat, node, int(round(f)), v))

    def flush(self):
        for (name, path), tr in self.tracks.items():
            obj = bpy.data.objects[name]
            for f in sorted(tr):
                setattr(obj, path, tr[f])
                obj.keyframe_insert(path, frame=f)
        for mat, node, f, v in sorted(self.nodes, key=lambda x: x[2]):
            sock = mat.node_tree.nodes[node].outputs[0]
            sock.default_value = v
            sock.keyframe_insert("default_value", frame=f)


K = Keys()


def reset_keys():
    global K
    K.tracks.clear()
    K.nodes.clear()


# ============================================================================ helpers

def empty(name, parent=None, loc=(0, 0, 0)):
    e = link(bpy.data.objects.new(name, None))
    e.parent = parent
    e.location = loc
    return e


def yaw_to(src, dst):
    return math.atan2(dst[0] - src[0], -(dst[1] - src[1]))


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def V(*a):
    return Vector(a if len(a) == 3 else a[0])


# ============================================================================ characters

LAYOUT = {
    "head": (0, 0, 8, 8, 8), "body": (16, 16, 8, 12, 4), "rarm": (40, 16, 4, 12, 4),
    "rleg": (0, 16, 4, 12, 4), "larm": (32, 48, 4, 12, 4), "lleg": (16, 48, 4, 12, 4),
}


def face_rects(u, v, w, h, d):
    return {"pz": (u + d, v, w, d), "nz": (u + d + w, v, w, d), "nx": (u, v + d, d, h),
            "ny": (u + d, v + d, w, h), "px": (u + d + w, v + d, d, h), "py": (u + 2 * d + w, v + d, w, h)}


class Skin:
    def __init__(self):
        self.a = np.zeros((64, 64, 3), np.float32)

    def view(self, part, face):
        x, y, w, h = face_rects(*LAYOUT[part])[face]
        return self.a[y:y + h, x:x + w]

    def fill(self, part, faces, rgb, var=5, rows=None):
        for f in faces:
            v = self.view(part, f)
            r0, r1 = rows if rows else (0, v.shape[0])
            sub = v[r0:r1]
            sub[:] = noisy(rgb, var, size=sub.shape[:2])

    def px(self, part, face, r, c, rgb):
        self.view(part, face)[r, c] = rgb


ALL = ["pz", "nz", "nx", "ny", "px", "py"]
SIDES = ["nx", "ny", "px", "py"]


def base_skin(skin, shirt, pants, shoes, hair, eyes, sleeve_rows=4):
    s = Skin()
    s.fill("head", ALL, skin, 4)
    s.fill("head", ["pz"], hair, 6)
    s.fill("head", ["nx", "px", "py"], hair, 6, rows=(0, 3))
    s.fill("head", ["py"], hair, 6, rows=(0, 5))
    s.fill("head", ["ny"], hair, 6, rows=(0, 2))
    for c, col in ((1, (250, 250, 250)), (2, eyes), (5, eyes), (6, (250, 250, 250))):
        s.px("head", "ny", 4, c, col)
    for c in (1, 2, 5, 6):
        s.px("head", "ny", 3, c, tuple(v * 0.8 for v in hair))
    for c in (3, 4):
        s.px("head", "ny", 6, c, tuple(v * 0.75 for v in skin))
    s.fill("body", ALL, shirt, 5)
    s.fill("body", SIDES, pants, 4, rows=(10, 12))
    for arm in ("rarm", "larm"):
        s.fill(arm, ALL, skin, 4)
        s.fill(arm, ["pz"] + SIDES, shirt, 5, rows=(0, sleeve_rows))
    for leg in ("rleg", "lleg"):
        s.fill(leg, ALL, pants, 4)
        s.fill(leg, SIDES + ["nz"], shoes, 3, rows=(10, 12))
        s.fill(leg, ["nz"], shoes, 3)
    return s


def skin_brohacker():
    hood, green = (34, 36, 42), (70, 230, 100)
    s = base_skin((196, 146, 104), hood, (46, 48, 58), (228, 228, 228), (52, 36, 26), (40, 40, 40), sleeve_rows=12)
    s.fill("head", ["pz", "nx", "px", "py"], hood, 4)
    v = s.view("head", "ny")
    v[0] = hood
    v[:, 0] = hood
    v[:, 7] = hood
    v[1, 1:7] = (52, 36, 26)
    v[3, 1:7] = (14, 14, 16)
    v[4, 1:7] = (14, 14, 16)
    v[4, 1:3] = (24, 110, 50)
    v[4, 5:7] = (24, 110, 50)
    v[3, 1] = (140, 255, 170)
    v[3, 5] = (140, 255, 170)
    v[6, 3:6] = (196, 146, 104)
    v[6, 3:5] = (110, 60, 46)
    v[5, 5] = (110, 60, 46)
    b = s.view("body", "ny")
    b[0:3, 3] = green
    b[0:3, 4] = green
    for r, c in ((5, 1), (6, 0), (7, 1), (5, 6), (6, 7), (7, 6), (5, 4), (6, 4), (7, 3)):
        b[r, c] = green
    b[8:10, 2:6] = (26, 28, 32)
    for arm in ("rarm", "larm"):
        s.fill(arm, SIDES, green, 3, rows=(9, 10))
    return s


def skin_masha():
    hair = (206, 96, 44)
    s = base_skin((242, 204, 174), (236, 112, 164), (66, 86, 156), (244, 244, 244), hair, (60, 160, 90))
    s.fill("head", ["nx", "px"], hair, 6, rows=(0, 7))
    s.fill("head", ["py"], hair, 6)
    v = s.view("head", "ny")
    v[2:6, 0] = hair
    v[2:6, 7] = hair
    s.fill("body", ["py"], hair, 6, rows=(0, 4))
    b = s.view("body", "ny")
    for r, c in ((3, 2), (3, 5), (4, 2), (4, 3), (4, 4), (4, 5), (5, 3), (5, 4), (3, 3)):
        b[r, c] = (250, 240, 245)
    b[3, 3] = (236, 112, 164)
    return s


def skin_dimon():
    s = base_skin((226, 182, 142), (52, 112, 212), (70, 72, 84), (34, 34, 36), (86, 58, 36), (70, 110, 200))
    s.fill("head", ["pz"], (214, 48, 48), 5)
    s.fill("head", SIDES, (214, 48, 48), 5, rows=(0, 2))
    b = s.view("body", "ny")
    b[4, :] = (240, 240, 240)
    b[5, :] = (240, 240, 240)
    return s


def skin_lava():
    gold = (252, 202, 46)
    s = base_skin((150, 100, 70), (222, 82, 30), (30, 30, 34), (60, 40, 30), (24, 20, 20), (120, 70, 30))
    s.fill("head", SIDES, gold, 6, rows=(0, 1))
    s.px("head", "ny", 0, 3, (60, 200, 240))
    s.px("head", "ny", 0, 4, (60, 200, 240))
    b = s.view("body", "ny")
    for c in range(8):
        h = 2 + (c * 5) % 3
        b[10 - h:10, c] = gold if c % 2 else (255, 150, 30)
    return s


def skin_snow():
    s = base_skin((246, 218, 198), (152, 202, 242), (120, 124, 140), (240, 240, 244), (240, 234, 216),
                  (70, 140, 230), sleeve_rows=12)
    s.fill("head", ["nx", "px", "py"], (240, 234, 216), 5, rows=(0, 6))
    b = s.view("body", "ny")
    b[6:9, 1:7] = (128, 180, 228)
    b[0:6, 3:5] = (236, 240, 250)
    return s


def skin_kotik():
    s = base_skin((230, 190, 150), (84, 172, 72), (112, 80, 50), (60, 60, 64), (128, 128, 132), (240, 180, 40))
    b = s.view("body", "ny")
    b[2:4, 2:6] = (250, 250, 250)
    b[3, 3] = (40, 40, 40)
    b[3, 4] = (40, 40, 40)
    return s


def skin_random(seed):
    r = random.Random(seed)
    skins = [(242, 204, 174), (226, 182, 142), (196, 146, 104), (150, 100, 70), (246, 218, 198)]
    shirt = tuple(r.randint(40, 230) for _ in range(3))
    pants = tuple(r.randint(30, 140) for _ in range(3))
    hair = r.choice([(40, 30, 20), (90, 60, 30), (200, 160, 80), (20, 20, 20), (150, 60, 30), (230, 220, 200)])
    eyes = r.choice([(40, 80, 160), (60, 140, 60), (90, 60, 30), (30, 30, 30)])
    s = base_skin(r.choice(skins), shirt, pants, (r.randint(20, 80),) * 3, hair, eyes, sleeve_rows=r.choice([4, 12]))
    b = s.view("body", "ny")
    if r.random() < 0.5:
        b[r.randint(2, 6), :] = tuple(min(255, c + 60) for c in shirt)
    return s


SKINS = {"brohacker": skin_brohacker, "pixel_masha": skin_masha, "dimon_pro": skin_dimon, "lavaKing": skin_lava,
         "snowbunny": skin_snow, "kotik_777": skin_kotik}

NPC_NAMES = ["Vanya_2012", "pro100_gamer", "Kisa_Murka", "NoobMaster", "tolik_pvp", "Lena_cat", "Sanya_K",
             "minecrafter07", "Dasha_bee", "kirill_top", "Zhenya42", "Artem_lol", "polina_q", "Grisha_TNT",
             "Nikitos", "katyaaa", "BigBoris", "MiloLapka", "Stas_bro", "Olya_mur"]


def box_mesh(name, w, h, d, offset, part, mat):
    rects = face_rects(*LAYOUT[part]) if part else None
    verts, faces, uvs = [], [], []
    for key, (n, corners) in FACES.items():
        i0 = len(verts)
        for cx, cy, cz in corners:
            verts.append(((offset[0] + cx * w) * PX, (offset[1] + cy * d) * PX, (offset[2] + cz * h) * PX))
        faces.append((i0, i0 + 1, i0 + 2, i0 + 3))
        if rects:
            x, y, rw, rh = rects[key]
            uvs.append([(x / 64, 1 - (y + rh) / 64), ((x + rw) / 64, 1 - (y + rh) / 64),
                        ((x + rw) / 64, 1 - y / 64), (x / 64, 1 - y / 64)])
        else:
            uvs.append(UV4)
    return build_mesh(name, verts, faces, uvs, [0] * 6, [mat])


class Char:
    def __init__(self, world, name, skin, pos=(0, 0, 0), yaw=0.0):
        self.w = world
        self.name = name
        img = new_image(f"skin_{name}", clip(skin.a))
        self.mat = flat_material(f"mat_{name}", image=img, hurt=True)
        r = self.root = empty(f"{name}_root", loc=pos)
        r.rotation_euler = (0, 0, yaw)
        mat = self.mat
        self.body = box_mesh(f"{name}_body", 8, 12, 4, (-4, -2, 0), "body", mat)
        self.body.parent = r
        self.body.location = (0, 0, 12 * PX)
        self.head = box_mesh(f"{name}_head", 8, 8, 8, (-4, -4, 0), "head", mat)
        self.head.parent = r
        self.head.location = (0, 0, 24 * PX)
        self.rarm = box_mesh(f"{name}_rarm", 4, 12, 4, (-2, -2, -10), "rarm", mat)
        self.rarm.parent = r
        self.rarm.location = (-6 * PX, 0, 22 * PX)
        self.larm = box_mesh(f"{name}_larm", 4, 12, 4, (-2, -2, -10), "larm", mat)
        self.larm.parent = r
        self.larm.location = (6 * PX, 0, 22 * PX)
        self.rleg = box_mesh(f"{name}_rleg", 4, 12, 4, (-2, -2, -12), "rleg", mat)
        self.rleg.parent = r
        self.rleg.location = (-2 * PX, 0, 12 * PX)
        self.lleg = box_mesh(f"{name}_lleg", 4, 12, 4, (-2, -2, -12), "lleg", mat)
        self.lleg.parent = r
        self.lleg.location = (2 * PX, 0, 12 * PX)
        self.mouth = box_mesh(f"{name}_mouth", 2, 2, 0.6, (-1, -4.5, 1), None, world.mats["mouth"])
        self.mouth.parent = self.head
        self.mouth.scale = (0, 0, 0)
        self.limbs = (self.rarm, self.larm, self.rleg, self.lleg)
        for o in (self.root, self.head) + self.limbs:
            o.rotation_mode = "XYZ"
        self.items = {}
        self.visible_ranges = None
        self._accessories()

    def _accessories(self):
        m = self.w.mats
        if self.name == "dimon_pro":
            self.acc("brim", 8, 1, 3, (-4, -7, 6), m["brim"])
        elif self.name == "lavaKing":
            for dx in (-3, -0.5, 2):
                self.acc(f"crown{dx}", 1, 2, 1, (dx, -4, 8), m["gold_acc"])
        elif self.name == "kotik_777":
            for side in (-1, 1):
                self.acc(f"ear{side}", 2, 2, 1, (side * 2.5 - 1, -1, 8), m["ear"])
                self.acc(f"earin{side}", 1, 1, 0.3, (side * 2.5 - 0.5, -1.2, 8), m["ear_in"])

    def acc(self, name, w, h, d, offset, mat, parent=None):
        ob = box_mesh(f"{self.name}_{name}", w, h, d, offset, None, mat)
        ob.parent = parent or self.head
        return ob

    # ---------------------------------------------------------------- state helpers
    def p(self, f):
        return Vector(K.value_at(self.root, "location", f))

    def yaw(self, f):
        return K.value_at(self.root, "rotation_euler", f)[2]

    def head_pos(self, f):
        p = self.p(f)
        return (p.x, p.y, p.z + 1.6)

    def forward(self, f):
        y = self.yaw(f)
        return Vector((math.sin(y), -math.cos(y), 0))

    # ---------------------------------------------------------------- items
    def hold(self, kind, hand="r"):
        """Attach an item mesh to a hand. Returns the item object (scale 0/1 keys toggle it)."""
        arm = self.rarm if hand == "r" else self.larm
        ob = self.w.item(kind, f"{self.name}_{kind}_{hand}")
        ob.parent = arm
        if kind == "shield":
            ob.location = (2.4 * PX if hand == "l" else -2.4 * PX, -1 * PX, -8 * PX)
        else:
            ob.location = (0, -1.5 * PX, -9.5 * PX)
        self.items[(kind, hand)] = ob
        return ob

    def show_item(self, kind, f, on, hand="r"):
        ob = self.items[(kind, hand)]
        K.set(ob, "scale", f - 1, K.value_at(ob, "scale", f - 1))
        K.set(ob, "scale", f, (1, 1, 1) if on else (0, 0, 0))

    # ---------------------------------------------------------------- motion
    def place(self, f, pos, yaw=None):
        K.set(self.root, "location", f, tuple(pos))
        if yaw is not None:
            K.set(self.root, "rotation_euler", f, (0, 0, yaw))

    def appear(self, f, flash=True):
        K.set(self.root, "scale", 0, (0, 0, 0))
        K.set(self.root, "scale", f - 1, (0, 0, 0))
        K.set(self.root, "scale", f, (1, 1, 1))
        if flash:
            p = self.p(f)
            self.w.fx.teleport(p + Vector((0, 0, 1.0)), f - 2)

    def vanish(self, f):
        K.set(self.root, "scale", f - 1, K.value_at(self.root, "scale", f - 1))
        K.set(self.root, "scale", f, (0, 0, 0))

    def walk(self, f0, f1, p1, swing=0.6, step=6, face=True):
        p0 = tuple(self.p(f0))
        K.set(self.root, "location", f0, p0)
        K.set(self.root, "location", f1, tuple(p1))
        if face:
            y = yaw_to(p0, p1)
            K.set(self.root, "rotation_euler", f0, (0, 0, y))
            K.set(self.root, "rotation_euler", f1, (0, 0, y))
        sign = 1
        f = f0
        while f <= f1:
            a = swing * sign if f not in (f0, f1) else 0.0
            K.set(self.rleg, "rotation_euler", f, (a, 0, 0))
            K.set(self.lleg, "rotation_euler", f, (-a, 0, 0))
            K.set(self.rarm, "rotation_euler", f, (-a * 0.8, 0, 0))
            K.set(self.larm, "rotation_euler", f, (a * 0.8, 0, 0))
            sign = -sign
            f = min(f + step, f1) if f < f1 else f1 + 1

    def run(self, f0, f1, p1):
        self.walk(f0, f1, p1, swing=0.95, step=4)

    def idle(self, f0, f1, phase=0.0):
        for f in range(f0, f1 + 1, 16):
            s = math.sin(f / 8.0 + phase)
            K.set(self.rarm, "rotation_euler", f, (0.05 * s, 0, -0.04))
            K.set(self.larm, "rotation_euler", f, (-0.05 * s, 0, 0.04))

    def talk(self, f0, f1, phase=0.0):
        for i, f in enumerate(range(f0, f1 + 1, 8)):
            a = -0.45 - 0.25 * math.sin(i * 1.7 + phase)
            K.set(self.rarm, "rotation_euler", f, (a, 0, -0.15))
            K.set(self.head, "rotation_euler", f, (0.06 * math.sin(i * 2.1), 0, K.value_at(self.head, "rotation_euler", f)[2]))
        K.set(self.rarm, "rotation_euler", f1 + 6, (0, 0, -0.04))

    def look(self, f0, f1, target, body_follow=0.0):
        p = self.p(f1)
        ry = self.yaw(f1)
        want = yaw_to(p, target)
        new_root = ry + wrap(want - ry) * body_follow
        if body_follow:
            K.tween(self.root, "rotation_euler", f0, f1, (0, 0, new_root))
        rel = max(-1.2, min(1.2, wrap(want - new_root)))
        dist = math.hypot(target[0] - p.x, target[1] - p.y)
        pitch = max(-0.9, min(0.9, math.atan2(target[2] - (p.z + 1.6), dist)))
        K.tween(self.head, "rotation_euler", f0, f1, (-pitch, 0, rel))

    def turn(self, f0, f1, yaw):
        K.tween(self.root, "rotation_euler", f0, f1, (0, 0, yaw))

    def head_rot(self, f0, f1, pitch=0.0, yaw=0.0):
        K.tween(self.head, "rotation_euler", f0, f1, (-pitch, 0, yaw))

    def jump(self, f0, h=0.5):
        p = self.p(f0)
        K.set(self.root, "location", f0, tuple(p))
        K.set(self.root, "location", f0 + 4, (p.x, p.y, p.z + h))
        K.set(self.root, "location", f0 + 9, tuple(p))

    def surprised(self, f, symbol="?"):
        K.tween(self.mouth, "scale", f, f + 3, (1, 1, 1))
        K.tween(self.rarm, "rotation_euler", f, f + 4, (-0.35, 0, -0.35))
        K.tween(self.larm, "rotation_euler", f, f + 4, (-0.35, 0, 0.35))
        if symbol:
            self.w.fx.symbol(self, f + 1, symbol)

    def calm(self, f):
        K.tween(self.mouth, "scale", f, f + 3, (0, 0, 0))
        K.tween(self.rarm, "rotation_euler", f, f + 5, (0, 0, -0.04))
        K.tween(self.larm, "rotation_euler", f, f + 5, (0, 0, 0.04))

    def swing(self, f, sweep=False, crit=False, target=None):
        """1.9 style swing with the right arm (sword/axe)."""
        K.hold(self.rarm, "rotation_euler", f)
        K.set(self.rarm, "rotation_euler", f + 2, (-2.5, 0, -0.3))
        K.set(self.rarm, "rotation_euler", f + 5, (-0.7, 0, 0.35))
        K.set(self.rarm, "rotation_euler", f + 10, (-0.35, 0, 0))
        if sweep:
            self.w.fx.sweep(self.p(f) + self.forward(f) * 1.1 + Vector((0, 0, 1.1)), self.yaw(f), f + 2)
        if crit and target is not None:
            self.w.fx.crit(target.p(f + 3) + Vector((0, 0, 1.2)), f + 3)

    def block(self, f0, f1):
        """Raise the shield in the left hand."""
        K.tween(self.larm, "rotation_euler", f0, f0 + 3, (-1.25, 0, -0.55))
        K.tween(self.larm, "rotation_euler", f1, f1 + 3, (0, 0, 0.04))

    def hurt(self, f, src=None, kb=1.1):
        K.node(self.mat, "hurt", f - 1, 0.0)
        K.node(self.mat, "hurt", f, 1.0)
        K.node(self.mat, "hurt", f + 7, 0.0)
        if src is not None and kb:
            p = self.p(f)
            d = (p - src.p(f))
            d.z = 0
            d = d.normalized() if d.length > 1e-3 else Vector((0, 1, 0))
            K.set(self.root, "location", f, tuple(p))
            K.set(self.root, "location", f + 4, tuple(p + d * kb * 0.6 + Vector((0, 0, 0.35))))
            K.set(self.root, "location", f + 9, tuple(p + d * kb))

    def die(self, f, src=None, drops=False):
        """Hit, fall over sideways, puff of smoke, gone."""
        self.hurt(f, src)
        K.hold(self.root, "rotation_euler", f + 1)
        y = K.value_at(self.root, "rotation_euler", f + 1)[2]
        K.set(self.root, "rotation_euler", f + 12, (0, math.radians(90), y))
        K.node(self.mat, "hurt", f + 8, 0.9)
        K.node(self.mat, "hurt", f + 20, 0.9)
        K.set(self.root, "scale", f + 19, (1, 1, 1))
        K.set(self.root, "scale", f + 20, (0, 0, 0))
        p = self.p(f + 12)
        self.w.fx.smoke(p + Vector((0, 0, 0.4)), f + 19)
        if drops:
            self.w.fx.drops(p + Vector((0, 0, 0.5)), f + 19)

    def fly_pose(self, f0, f1):
        for f in range(f0, f1 + 1, 14):
            s = math.sin(f / 7.0)
            K.set(self.rleg, "rotation_euler", f, (0.22 + 0.06 * s, 0, 0))
            K.set(self.lleg, "rotation_euler", f, (0.1 - 0.06 * s, 0, 0))

    def hover(self, f0, f1, pos, amp=0.08):
        for f in range(f0, f1 + 1, 12):
            K.set(self.root, "location", f, (pos[0], pos[1], pos[2] + amp * math.sin(f / 6.0)))

    def sit(self, f0, pos, yaw):
        self.place(f0, (pos[0], pos[1], pos[2] - 12 * PX), yaw)
        K.set(self.rleg, "rotation_euler", f0, (-1.5, 0, 0.05))
        K.set(self.lleg, "rotation_euler", f0, (-1.5, 0, -0.05))

    def swim(self, f0, f1, pos, phase=0.0):
        for f in range(f0, f1 + 1, 8):
            s = math.sin(f / 5.0 + phase)
            K.set(self.root, "location", f, (pos[0], pos[1], pos[2] - 1.45 + 0.07 * s))
            K.set(self.rarm, "rotation_euler", f, (-2.6 + 0.4 * s, 0, -0.3))
            K.set(self.larm, "rotation_euler", f, (-2.6 - 0.4 * s, 0, 0.3))

    def fall(self, f0, f1, p0, p1):
        """Free fall (accelerating) from p0 to p1."""
        n = 6
        for i in range(n + 1):
            t = i / n
            f = f0 + (f1 - f0) * t
            pos = Vector(p0).lerp(Vector(p1), t * t)
            K.set(self.root, "location", f, tuple(pos))
        K.set(self.rarm, "rotation_euler", f0 + 2, (-2.8, 0, -0.5))
        K.set(self.larm, "rotation_euler", f0 + 2, (-2.8, 0, 0.5))
        for i, f in enumerate(range(f0 + 2, f1, 4)):
            K.set(self.rleg, "rotation_euler", f, (0.5 if i % 2 else -0.5, 0, 0))
            K.set(self.lleg, "rotation_euler", f, (-0.5 if i % 2 else 0.5, 0, 0))


# ============================================================================ items (sprites -> voxels)

from sprites import SPRITES  # noqa: E402  (pixel-art item sprites, shared with compose.py)


# ============================================================================ particle effects

class FX:
    def __init__(self, world):
        self.w = world
        self.n = 0
        self.r = random.Random(11)

    def _cube(self, mat, size):
        self.n += 1
        return cube_mesh(f"fx{self.n}", size, mat)

    def burst(self, center, f, n, mats, size=0.1, speed=1.5, up=0.8, life=16, gravity=0.0, spread_z=1.0,
              shrink=True, ground=None):
        c = Vector(center)
        for i in range(n):
            ob = self._cube(mats[i % len(mats)], size)
            ob.scale = (0, 0, 0)
            a = self.r.uniform(0, 2 * math.pi)
            el = self.r.uniform(-0.3, 1.0) * spread_z
            d = Vector((math.cos(a), math.sin(a), el)).normalized() * speed * self.r.uniform(0.5, 1.0)
            d.z += up
            L = life * self.r.uniform(0.7, 1.1)
            K.set(ob, "scale", f - 1, (0, 0, 0))
            K.set(ob, "scale", f, (1, 1, 1))
            K.set(ob, "location", f, tuple(c))
            mid = c + d * 0.5
            end = c + d
            if gravity:
                mid.z += 0.0
                end.z -= gravity
            if ground is not None:
                end.z = max(end.z, ground)
            K.set(ob, "location", f + L * 0.5, tuple(mid))
            K.set(ob, "location", f + L, tuple(end))
            K.set(ob, "scale", f + L * 0.7, (0.8, 0.8, 0.8))
            K.set(ob, "scale", f + L, (0, 0, 0) if shrink else (1, 1, 1))
            ob.rotation_euler = (self.r.random(), self.r.random(), self.r.random())

    def teleport(self, center, f):
        m = self.w.mats
        self.burst(center, f, 22, [m["purple"], m["purple2"], m["pink"]], size=0.09, speed=1.6, up=0.4, life=14)

    def crit(self, center, f):
        m = self.w.mats
        self.burst(center, f, 12, [m["star"], m["white"]], size=0.08, speed=1.2, up=0.6, life=10)

    def smoke(self, center, f):
        m = self.w.mats
        self.burst(center, f, 12, [m["smoke"], m["smoke2"]], size=0.22, speed=0.7, up=0.9, life=18)

    def splash(self, center, f):
        m = self.w.mats
        self.burst(center, f, 18, [m["white"], m["foam"]], size=0.14, speed=1.0, up=1.8, life=16, gravity=1.6)

    def totem(self, center, f):
        m = self.w.mats
        self.burst(center, f, 40, [m["totem_g"], m["totem_y"]], size=0.07, speed=1.8, up=1.0, life=22)

    def drops(self, center, f, n=8):
        m = self.w.mats
        c = Vector(center)
        mats = [m["diamond"], m["gold_acc"], m["iron"], m["purple2"], m["planks_item"]]
        for i in range(n):
            ob = self._cube(mats[i % len(mats)], 0.18)
            ob.scale = (0, 0, 0)
            a = self.r.uniform(0, 2 * math.pi)
            d = Vector((math.cos(a), math.sin(a), 0)) * self.r.uniform(0.4, 1.2)
            gz = c.z - 0.5 + 0.12
            K.set(ob, "scale", f - 1, (0, 0, 0))
            K.set(ob, "scale", f, (1, 1, 1))
            K.set(ob, "location", f, tuple(c))
            K.set(ob, "location", f + 5, tuple(c + d * 0.5 + Vector((0, 0, 0.6))))
            K.set(ob, "location", f + 11, (c.x + d.x, c.y + d.y, gz))
            for j in range(4):
                K.set(ob, "location", f + 20 + j * 14, (c.x + d.x, c.y + d.y, gz + (0.08 if j % 2 == 0 else 0.0)))
            ob.rotation_euler = (0, 0, self.r.random())

    def sweep(self, center, yaw, f):
        ob = self.w.sweep_arc(f"sweep{self.n}")
        self.n += 1
        ob.location = tuple(center)
        ob.rotation_euler = (0, 0, yaw)
        K.set(ob, "scale", f - 1, (0, 0, 0))
        K.set(ob, "scale", f, (0.6, 0.6, 0.6))
        K.set(ob, "scale", f + 3, (1.3, 1.3, 1.3))
        K.set(ob, "scale", f + 6, (1.6, 1.6, 0.0))

    def swirl(self, char, f0, f1):
        sw = empty(f"{char.name}_swirl{f0}", parent=char.root)
        sw.scale = (0, 0, 0)
        m = self.w.mats
        for i in range(18):
            a = 2 * math.pi * i / 18 * 2.5
            ob = self._cube(m["purple"] if i % 2 else m["purple2"], 2.4 * PX)
            ob.parent = sw
            ob.location = (0.62 * math.cos(a), 0.62 * math.sin(a), 0.1 + 1.9 * i / 18)
        K.set(sw, "scale", f0, (0, 0, 0))
        K.set(sw, "scale", f0 + 4, (1.15, 1.15, 1.15))
        K.set(sw, "scale", f1 - 6, (1.0, 1.0, 1.0))
        K.set(sw, "scale", f1, (0, 0, 0))
        self.w.spinners.append((sw, f0, f1, 0.4))
        return sw

    def symbol(self, char, f, kind="?"):
        sym = self.w.symbol_mesh(f"{char.name}_sym{f}", kind)
        sym.parent = char.root
        sym.location = (0, 0, 2.25)
        sym.scale = (0, 0, 0)
        K.set(sym, "scale", f, (0, 0, 0))
        K.set(sym, "scale", f + 4, (1.35, 1.35, 1.35))
        K.set(sym, "scale", f + 7, (1.0, 1.0, 1.0))
        self.w.wobblers.append(sym)
        return sym

    def hide_symbol_after(self, sym, f):
        K.set(sym, "scale", f, (1, 1, 1))
        K.set(sym, "scale", f + 4, (0, 0, 0))


# ============================================================================ world

QMARK = [".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."]
EXCL = ["..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."]

FLAT_ZONES = [(-24, 24, -24, 24), (-17, 17, 26, 56), (8, 24, -6, 14)]  # spawn, arena, masha house


def ground_height(x, y):
    d = 99
    for x0, x1, y0, y1 in FLAT_ZONES:
        dx = max(x0 - x, 0, x - x1)
        dy = max(y0 - y, 0, y - y1)
        d = min(d, math.hypot(dx, dy))
    if d <= 0:
        return 0
    k = d / 7.0
    h = k * (1.0 + 0.8 * math.sin(x * 0.17) + 0.8 * math.cos(y * 0.13 + 1.0))
    return int(max(0, min(6, h)))


class World:
    def __init__(self, land=True, ocean=False):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        reset_keys()
        self.scene = bpy.context.scene
        self.scene.render.fps = FPS
        self.spinners, self.wobblers = [], []
        self.chars = {}
        self._sky()
        self._materials()
        self.fx = FX(self)
        self.npc_i = 0
        if land:
            self._land()
            self._clouds((0, 20))
        if ocean:
            self._ocean()
            self._clouds((OCEAN_X, 0))

    # ---------------------------------------------------------------- setup
    def _sky(self):
        world = bpy.data.worlds.new("sky")
        self.scene.world = world
        world.use_nodes = True
        nt = world.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputWorld")
        bg = nt.nodes.new("ShaderNodeBackground")
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Generated"], sep.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = 0.0
        mr.inputs["From Max"].default_value = 0.55
        nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        nt.links.new(mr.outputs[0], mix.inputs[0])
        mix.inputs[6].default_value = lin(SKY_HORIZON)
        mix.inputs[7].default_value = lin(SKY_TOP)
        nt.links.new(mix.outputs[2], bg.inputs["Color"])
        nt.links.new(bg.outputs[0], out.inputs[0])

    def _materials(self):
        texs = {
            "grass_top": t_grass_top(), "dirt": t_dirt(), "grass_side": t_grass_side(), "tile": t_tile(),
            "pave": t_pave(), "planks": t_planks(), "log_side": t_log_side(), "log_top": t_log_top(),
            "leaves": t_leaves(), "stonebrick": t_bricks(), "water": t_water(), "glass": t_glass(),
            "roof": t_planks((96, 64, 40), (62, 40, 24)), "sand": t_sand(), "farmland": t_farmland(),
            "craft_top": t_craft_top(), "chest": t_chest(), "wool_red": t_wool((190, 40, 40)),
            "wool_white": t_wool((236, 236, 236)), "cobble": t_cobble(), "seat": t_seat(),
            "redbrick": t_bricks((160, 80, 64), (190, 180, 170)), "wool_purple": t_wool((130, 60, 190)),
        }
        m = self.mats = {k: flat_material(k, image=new_image(k, v)) for k, v in texs.items()}
        m["lamp"] = flat_material("lamp", image=new_image("lampt", t_lamp()), unlit=True)
        m["cloud"] = flat_material("cloud", color=(250, 250, 252), fog=False, unlit=True)
        m["mouth"] = flat_material("mouth", color=(60, 26, 26), fog=False)
        m["purple"] = flat_material("purple", color=(196, 92, 255), fog=False, unlit=True)
        m["purple2"] = flat_material("purple2", color=(120, 40, 200), fog=False, unlit=True)
        m["pink"] = flat_material("pink", color=(255, 160, 255), fog=False, unlit=True)
        m["gold"] = flat_material("gold", color=(255, 176, 0), fog=False)
        m["gold_acc"] = flat_material("gold_acc", color=(252, 202, 46))
        m["brim"] = flat_material("brim", color=(180, 36, 36))
        m["ear"] = flat_material("ear", color=(128, 128, 132))
        m["ear_in"] = flat_material("ear_in", color=(240, 160, 170))
        m["star"] = flat_material("star", color=(255, 236, 140), fog=False, unlit=True)
        m["white"] = flat_material("white", color=(250, 250, 255), fog=False, unlit=True)
        m["foam"] = flat_material("foam", color=(170, 210, 255), fog=False, unlit=True)
        m["smoke"] = flat_material("smoke", color=(200, 200, 200), fog=False)
        m["smoke2"] = flat_material("smoke2", color=(150, 150, 150), fog=False)
        m["totem_g"] = flat_material("totem_g", color=(120, 230, 60), fog=False, unlit=True)
        m["totem_y"] = flat_material("totem_y", color=(250, 220, 60), fog=False, unlit=True)
        m["diamond"] = flat_material("diamond", color=(110, 230, 220), fog=False)
        m["iron"] = flat_material("iron", color=(216, 216, 216), fog=False)
        m["planks_item"] = flat_material("planks_item", color=(168, 134, 82), fog=False)
        m["torch_stick"] = flat_material("torch_stick", color=(110, 80, 40))
        m["torch_fire"] = flat_material("torch_fire", color=(255, 220, 110), fog=False, unlit=True)
        m["dummy"] = flat_material("dummy", color=(170, 140, 100))
        m["sweep"] = flat_material("sweep", color=(250, 250, 255), fog=False, unlit=True)
        for kind, fn in SPRITES.items():
            _, pal = fn()
            for key, rgb in pal.items():
                m[f"{kind}_{key}"] = flat_material(f"{kind}_{key}", color=rgb, fog=False)
        m["shield_wood"] = flat_material("shield_wood", color=(150, 108, 60), fog=False)
        m["shield_rim"] = flat_material("shield_rim", color=(170, 170, 176), fog=False)
        m["shield_face"] = flat_material("shield_face", color=(222, 82, 30), fog=False)

    # ---------------------------------------------------------------- land
    def _land(self):
        B = {}
        R = 66
        heights = {}
        for x in range(-R, R + 1):
            for y in range(-R, R + 1):
                h = ground_height(x, y)
                heights[(x, y)] = h
                for z in range(-3, h):
                    B[(x, y, z)] = "grass" if z == h - 1 else "dirt"
        # spawn plaza
        for x in range(-10, 11):
            for y in range(-10, 11):
                m = max(abs(x), abs(y))
                B[(x, y, -1)] = "pave" if (m in (4, 10) or abs(x) <= 1 or abs(y) <= 1) else "tile"
        for y in range(11, 16):
            for x in range(-8, -5):
                B[(x, y, -1)] = "pave"
        # path to the arena
        for y in range(11, 31):
            for x in range(-1, 2):
                B[(x, y, -1)] = "pave"
        # well
        for x in range(-2, 3):
            for y in range(-2, 3):
                if max(abs(x), abs(y)) == 2:
                    B[(x, y, 0)] = "stonebrick"
                else:
                    B[(x, y, -1)] = "water"
        for x, y in ((-9, -9), (9, -9), (-9, 9), (9, 9)):
            B[(x, y, 0)] = B[(x, y, 1)] = "log"
            B[(x, y, 2)] = "lamp"
        self._house(B, -11, -3, 10, 16, door=(-7, 10))           # kotik
        self._interior_kotik(B)
        self._house(B, 12, 19, 1, 7, door=(12, 4), door_side="x", wall="redbrick")  # masha
        self._basement(B)
        self._farm(B)
        self._arena(B)
        self._trees(B, heights)
        tex = {
            "grass": dict(top="grass_top", bottom="dirt", side="grass_side"),
            "dirt": dict(top="dirt", bottom="dirt", side="dirt"),
            "log": dict(top="log_top", bottom="log_top", side="log_side"),
            "craft": dict(top="craft_top", bottom="planks", side="planks"),
        }
        for k in ("tile", "pave", "planks", "leaves", "stonebrick", "water", "glass", "roof", "lamp", "sand",
                  "farmland", "chest", "wool_red", "wool_white", "cobble", "seat", "redbrick", "wool_purple"):
            tex.setdefault(k, dict(top=k, bottom=k, side=k))
        tex["farmland"] = dict(top="farmland", bottom="dirt", side="dirt")
        mesh_voxels("land", B, tex, self.mats, origin=(-0.5, -0.5, 0.0))
        self.blocks = B
        for pos in self.torch_spots:
            self.torch(pos)

    def _house(self, B, x0, x1, y0, y1, door, door_side="y", wall="planks"):
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                B[(x, y, -1)] = "planks"
                ex, ey = x in (x0, x1), y in (y0, y1)
                if ex or ey:
                    for z in range(0, 4):
                        B[(x, y, z)] = "log" if (ex and ey) else wall
        for z in (0, 1):
            B.pop((door[0], door[1], z), None)
        if door_side == "y":
            for x in (x0 + 2, x1 - 2):
                for z in (1, 2):
                    B[(x, y0, z)] = "glass"
            for y in (y0 + 2, y1 - 2):
                for z in (1, 2):
                    B[(x1, y, z)] = "glass"
        else:
            for y in (y0 + 1, y1 - 1):
                for z in (1, 2):
                    B[(x0, y, z)] = "glass"
        for i, z in enumerate(range(4, 8)):
            for x in range(x0 - 1 + i, x1 + 2 - i):
                for y in range(y0 - 1 + i, y1 + 2 - i):
                    if x0 - 1 + i > x1 + 1 - i or y0 - 1 + i > y1 + 1 - i:
                        continue
                    if i == 3 or x in (x0 - 1 + i, x1 + 1 - i) or y in (y0 - 1 + i, y1 + 1 - i):
                        B[(x, y, z)] = "roof"

    def _interior_kotik(self, B):
        B[(-10, 15, 0)] = "craft"
        B[(-4, 15, 0)] = "chest"
        B[(-5, 15, 0)] = "chest"
        B[(-10, 11, 0)] = "wool_red"
        B[(-10, 12, 0)] = "wool_white"
        self.torch_spots = [(-9.5, 15.35, 2.2), (-4.5, 10.65, 2.2)]

    def _basement(self, B):
        # room under masha's house: x 13..18, y 2..6, z -5..-2 air; walls cobble
        for x in range(12, 20):
            for y in range(1, 8):
                for z in range(-6, -1):
                    edge = x in (12, 19) or y in (1, 7) or z == -6
                    if edge:
                        B[(x, y, z)] = "cobble" if z > -6 else "planks"
                    else:
                        B.pop((x, y, z), None)
        B[(18, 6, -5)] = "chest"
        B[(13, 6, -5)] = "craft"
        self.torch_spots += [(12.65, 3.0, -3.3), (18.35, 5.0, -3.3), (15.5, 6.35, -3.3), (15.5, 1.65, -3.3)]

    def _farm(self, B):
        for x in range(-17, -12):
            for y in range(10, 17):
                B[(x, y, -1)] = "water" if x == -15 else "farmland"
        self.sprouts = [(x + 0.0, y + 0.0) for x in (-17, -16, -14, -13) for y in range(10, 17)]

    def _arena(self, B):
        cx, cy = 0, 41
        for x in range(cx - 9, cx + 10):
            for y in range(cy - 9, cy + 10):
                B[(x, y, -1)] = "sand"
                if max(abs(x - cx), abs(y - cy)) == 9:
                    B[(x, y, 0)] = "stonebrick"
        for z in (0,):
            B.pop((cx, cy - 9, z), None)  # entrance
        B[(cx - 1, cy - 9, 0)] = "wool_red"
        B[(cx + 1, cy - 9, 0)] = "wool_red"
        # tribunes on the east and west sides
        for side in (-1, 1):
            for step in range(4):
                x = cx + side * (10 + step)
                for y in range(cy - 8, cy + 9):
                    for z in range(0, step + 1):
                        B[(x, y, z)] = "stonebrick" if z < step else "seat"
        # back tribune (north)
        for step in range(3):
            y = cy + 10 + step
            for x in range(cx - 8, cx + 9):
                for z in range(0, step + 1):
                    B[(x, y, z)] = "stonebrick" if z < step else "seat"
        # ledge for the jump crit
        for x in (cx + 5, cx + 6):
            for y in (cy + 4, cy + 5):
                B[(x, y, 0)] = "stonebrick"
                B[(x, y, 1)] = "stonebrick"
        # banners
        for x in (cx - 9, cx + 9):
            for z in (1, 2):
                B[(x, cy - 9, z)] = "wool_purple"
        self.arena = Vector((cx, cy, 0))

    def _trees(self, B, heights):
        r = random.Random(7)
        keep_out = [(-12, 20, -20, 30), (-18, 18, 25, 58), (6, 26, -8, 16), (-20, -10, 8, 18)]
        trees = []
        tries = 0
        while len(trees) < 80 and tries < 5000:
            tries += 1
            x, y = r.randint(-58, 58), r.randint(-58, 58)
            if math.hypot(x, y) < 14:
                continue
            if any(a <= x <= b and c <= y <= d for a, b, c, d in keep_out):
                continue
            if y < -8 and -10 < x < 12:
                continue
            if any(math.hypot(x - tx, y - ty) < 5 for tx, ty in trees):
                continue
            trees.append((x, y))
        for x, y in trees:
            h0 = heights.get((x, y), 0)
            th = r.randint(4, 6)
            for z in range(h0, h0 + th):
                B[(x, y, z)] = "log"
            top = h0 + th
            for dz, rad in ((-2, 2), (-1, 2), (0, 1), (1, 1)):
                for dx in range(-rad, rad + 1):
                    for dy in range(-rad, rad + 1):
                        if abs(dx) == rad and abs(dy) == rad and (rad == 1 or r.random() < 0.6):
                            continue
                        B.setdefault((x + dx, y + dy, top + dz), "leaves")

    def _clouds(self, center):
        r = random.Random(int(center[0]) + 3)
        blocks = {}
        for i in range(18):
            cx, cy = r.randint(-70, 70), r.randint(-60, 90)
            w, d = r.randint(6, 14), r.randint(4, 9)
            for x in range(w):
                for y in range(d):
                    if x in (0, w - 1) and y in (0, d - 1):
                        continue
                    blocks[(cx + x, cy + y, 0)] = "c"
        mesh_voxels(f"clouds{center[0]}", blocks, {"c": dict(top="cloud", bottom="cloud", side="cloud")},
                    self.mats, scale=1.6, origin=(center[0], center[1], 34))

    def _ocean(self):
        S = 400.0
        verts = [(OCEAN_X - S, -S, -0.1), (OCEAN_X + S, -S, -0.1), (OCEAN_X + S, S, -0.1), (OCEAN_X - S, S, -0.1)]
        build_mesh("ocean", verts, [(0, 1, 2, 3)], [[(0, 0), (2 * S, 0), (2 * S, 2 * S), (0, 2 * S)]], [0],
                   [self.mats["water"]])

    def torch(self, pos):
        x, y, z = pos
        st = cube_mesh(f"torch{x}{y}", 1.0, self.mats["torch_stick"])
        st.location = (x, y, z)
        st.scale = (0.12, 0.12, 0.55)
        fi = cube_mesh(f"torchf{x}{y}", 1.0, self.mats["torch_fire"])
        fi.location = (x, y, z + 0.33)
        fi.scale = (0.14, 0.14, 0.14)

    def sprout_meshes(self):
        blocks = {}
        for x, y in self.sprouts:
            for k in range(3):
                bx, by = int((x - 0.5) * 8) + 1 + k * 3, int((y - 0.5) * 8) + 2 + (k % 2) * 3
                blocks[(bx, by, 0)] = "s"
                blocks[(bx, by, 1)] = "s"
        self.mats["sprout"] = flat_material("sprout", color=(90, 200, 70))
        mesh_voxels("sprouts", blocks, {"s": dict(top="sprout", bottom="sprout", side="sprout")}, self.mats,
                    scale=1 / 8, origin=(0, 0, 0.0))

    # ---------------------------------------------------------------- props
    def item(self, kind, name):
        if kind == "shield":
            par = empty(name)
            m = self.mats
            for nm, (w, h, d, off, mat) in {
                "rim": (12, 22, 1, (-6, -0.5, -11), m["shield_rim"]),
                "face": (10, 20, 0.4, (-5, -0.95, -10), m["shield_face"]),
                "back": (10, 20, 0.4, (-5, 0.55, -10), m["shield_wood"]),
            }.items():
                ob = box_mesh(f"{name}_{nm}", w, h, d, off, None, mat)
                ob.parent = par
            par.rotation_euler = (0, 0, math.radians(90))
            return par
        sprite, pal = SPRITES[kind]()
        blocks = {(x, 0, 15 - y): k for (x, y), k in sprite.items()}
        tex = {k: dict(top=f"{kind}_{k}", bottom=f"{kind}_{k}", side=f"{kind}_{k}") for k in pal}
        # grip pixel at sprite (2,13) -> origin; sprite lies in the YZ plane, blade pointing forward-up
        ob = mesh_voxels(name, blocks, tex, self.mats, scale=PX * 0.95, origin=(0, 0, 0))
        me = ob.data
        g = Vector((2.5, 0.5, 15 - 13 + 0.5)) * PX * 0.95
        for v in me.vertices:
            x, y, z = v.co - g
            v.co = (y, -x, z)  # sprite x -> -Y (forward)
        return ob

    def sweep_arc(self, name):
        blocks = {}
        for i in range(-10, 11):
            a = i / 10 * 1.2
            for rr in (13, 14):
                blocks[(int(round(math.sin(a) * rr)), int(round(-math.cos(a) * rr)), 0)] = "s"
        return mesh_voxels(name, blocks, {"s": dict(top="sweep", bottom="sweep", side="sweep")}, self.mats,
                           scale=0.08, origin=(0, 0, 0))

    def symbol_mesh(self, name, kind):
        rows = QMARK if kind == "?" else EXCL
        blocks = {}
        for r, line in enumerate(rows):
            for c, ch in enumerate(line):
                if ch == "#":
                    blocks[(c, 0, len(rows) - 1 - r)] = "s"
        s = 0.075
        return mesh_voxels(name, blocks, {"s": dict(top="gold", bottom="gold", side="gold")}, self.mats, scale=s,
                           origin=(-2.5 * s, -0.5 * s, 0))

    def dummy(self, pos, yaw=0.0):
        root = empty("dummy_root", loc=pos)
        root.rotation_euler = (0, 0, yaw)
        for nm, (w, h, d, off) in {"post": (2, 26, 2, (-1, -1, 0)), "arms": (14, 2, 2, (-7, -1, 18)),
                                   "head": (6, 6, 6, (-3, -3, 26)), "body": (8, 10, 3, (-4, -1.5, 10))}.items():
            ob = box_mesh(f"dummy_{nm}", w, h, d, off, None, self.mats["dummy"])
            ob.parent = root
        return root

    # ---------------------------------------------------------------- characters
    def char(self, name, pos=(0, 0, 0), yaw=0.0):
        if name not in self.chars:
            skin = SKINS[name]() if name in SKINS else skin_random(name)
            self.chars[name] = Char(self, name, skin, pos, yaw)
        return self.chars[name]

    def npc(self, pos=(0, 0, 0), yaw=0.0):
        name = NPC_NAMES[self.npc_i % len(NPC_NAMES)]
        self.npc_i += 1
        return self.char(name, pos, yaw)

    # ---------------------------------------------------------------- cameras
    def cam(self, name, lens=24):
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.sensor_fit = "VERTICAL"
        cd.sensor_height = 24
        cd.clip_start = 0.05
        cd.clip_end = 600
        cam = link(bpy.data.objects.new(name, cd))
        tgt = empty(name + "_t")
        con = cam.constraints.new("TRACK_TO")
        con.target = tgt
        con.track_axis = "TRACK_NEGATIVE_Z"
        con.up_axis = "UP_Y"
        cam["target"] = tgt.name
        return cam, tgt

    def fp_rig(self, cam, items=("sword",)):
        """First-person hand + held items attached to a camera. Returns (hand_empty, {kind: obj})."""
        hand = empty(cam.name + "_hand", parent=cam, loc=(0.15, -0.30, -0.62))
        hand.rotation_mode = "XYZ"
        hand.rotation_euler = (0.0, 0.0, 0.0)
        arm = box_mesh(cam.name + "_arm", 4, 12, 4, (-2, -2, -12), "rarm", self.chars["brohacker"].mat)
        arm.parent = hand
        arm.rotation_euler = (math.radians(8), math.radians(-6), math.radians(18))
        arm.scale = (0.62, 0.62, 0.62)
        objs = {}
        for kind in items:
            if kind == "shield":
                continue
            ob = self.item(kind, f"{cam.name}_{kind}")
            ob.parent = arm
            ob.location = (0, 0.5 * PX, -11 * PX)
            ob.rotation_euler = (math.pi - math.radians(20), 0, math.radians(-25))
            ob.scale = (1, 1, 1) if kind == items[0] else (0, 0, 0)
            objs[kind] = ob
        return hand, objs

    # ---------------------------------------------------------------- render
    def finish(self, frames):
        for sw, f0, f1, speed in self.spinners:
            for f in range(f0, min(frames, f1) + 1, 2):
                sw.rotation_euler = (0, 0, (f - f0) * speed)
                sw.keyframe_insert("rotation_euler", frame=f)
        K.flush()
        for sym in self.wobblers:
            for f in range(1, frames + 1, 3):
                sym.rotation_euler = (0, 0, 0.35 * math.sin(f / 5.0))
                sym.keyframe_insert("rotation_euler", frame=f)
        sc = self.scene
        sc.frame_start, sc.frame_end = 1, frames
        r = sc.render
        r.engine = "CYCLES"
        sc.cycles.device = "CPU"
        sc.cycles.use_denoising = False
        sc.cycles.use_adaptive_sampling = False
        sc.cycles.max_bounces = 0
        sc.cycles.transparent_max_bounces = 4
        sc.cycles.filter_width = 1.2
        r.use_persistent_data = True
        if os.environ.get("THREADS"):
            r.threads_mode = "FIXED"
            r.threads = int(os.environ["THREADS"])
        r.image_settings.file_format = "PNG"
        r.image_settings.color_mode = "RGB"
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.look = "None"

    def export_and_render(self, out, frames, cam_for, res=(720, 1280), samples=8, only=None, tag_chars=None):
        os.makedirs(out, exist_ok=True)
        sc = self.scene
        sc.cycles.samples = samples
        sc.render.resolution_x, sc.render.resolution_y = res
        sc.render.resolution_percentage = 100
        w, h = res
        meta = {"frames": frames, "res": list(res), "f": {}}
        names = tag_chars if tag_chars is not None else list(self.chars)
        for f in range(1, frames + 1):
            sc.frame_set(f)
            cam = cam_for(f)
            sc.camera = cam
            bpy.context.view_layer.update()
            cam_up = cam.matrix_world.to_3x3() @ Vector((0, 1, 0))
            tags, boxes = [], []
            for n in names:
                c = self.chars[n]
                if c.root.scale.x < 0.5:
                    continue
                mw = c.root.matrix_world
                p = mw @ Vector((0, 0, 2.02))
                co = world_to_camera_view(sc, cam, p)
                if co.z <= 0.3:
                    continue
                co2 = world_to_camera_view(sc, cam, p + cam_up * 0.25)
                tags.append({"name": n, "x": co.x * w, "y": (1 - co.y) * h, "size": abs(co2.y - co.y) * h,
                             "depth": co.z})
                xs, ys = [], []
                for cx in (-0.38, 0.38):
                    for cy in (-0.38, 0.38):
                        for cz in (0.0, 1.9):
                            q = world_to_camera_view(sc, cam, mw @ Vector((cx, cy, cz)))
                            xs.append(q.x * w)
                            ys.append((1 - q.y) * h)
                boxes.append({"name": n, "x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys), "depth": co.z})
            meta["f"][f] = {"cam": cam.name, "tags": tags, "boxes": boxes}
        with open(os.path.join(out, "meta.json"), "w") as fh:
            json.dump(meta, fh)
        todo = only if only else range(1, frames + 1)
        for f in todo:
            path = os.path.join(out, f"f{f:04d}.png")
            if os.path.exists(path):
                continue
            sc.frame_set(f)
            sc.camera = cam_for(f)
            sc.render.filepath = path + ".tmp.png"
            bpy.ops.render.render(write_still=True)
            os.replace(path + ".tmp.png", path)

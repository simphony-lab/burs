"""Blocky spawn scene: the cheater "brohacker" fires MassTPA and everyone at spawn is confused.

Builds the whole scene procedurally in Blender (bpy module), animates it and renders PNG frames.
Also writes meta.json with screen positions of the nametags for the overlay step.

    python scene.py --out frames --res 720x1280 --samples 16 [--frames 1-150]
"""
import argparse
import json
import math
import os
import random
import sys

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "unifont.otf")
FPS = 30
FRAMES = 240
PX = 0.9 / 16  # one skin pixel in world units (character is 32px = 1.8 blocks tall)

# shot ranges (inclusive)
SHOTS = [("A", 1, 62), ("B", 63, 150), ("C", 151, 240)]

rng = np.random.default_rng(7)
random.seed(7)


def srgb_to_lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lin(rgb):
    return tuple(srgb_to_lin(v) for v in rgb) + (1.0,)


# ----------------------------------------------------------------------------- textures

def new_image(name, arr):
    """arr: HxWx3/4 uint8 in sRGB, row 0 = top."""
    arr = np.asarray(arr)
    h, w = arr.shape[:2]
    if arr.shape[2] == 3:
        arr = np.concatenate([arr, np.full((h, w, 1), 255, np.uint8)], axis=2)
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set((np.flipud(arr).astype(np.float32) / 255.0).ravel())
    img.pack()
    return img


def noisy(base, var, size=(16, 16), seed=None):
    r = np.random.default_rng(seed) if seed is not None else rng
    a = np.array(base, np.float32)[None, None, :] + r.uniform(-var, var, size + (1,))
    return a


def clip(a):
    return np.clip(a, 0, 255).astype(np.uint8)


def tex_grass_top():
    a = noisy((96, 158, 56), 14)
    m = rng.random((16, 16)) < 0.18
    a[m] *= 0.82
    return clip(a)


def tex_dirt():
    a = noisy((134, 96, 67), 10)
    m = rng.random((16, 16)) < 0.15
    a[m] = (100, 72, 50)
    return clip(a)


def tex_grass_side():
    a = tex_dirt().astype(np.float32)
    g = noisy((96, 158, 56), 12)
    a[:3] = g[:3]
    drip = rng.random(16) < 0.5
    a[3][drip] = g[3][drip]
    return clip(a)


def tex_tile():
    a = noisy((196, 192, 184), 6)
    a[0, :] = (156, 152, 146)
    a[:, 0] = (156, 152, 146)
    a[8, :] = (170, 166, 160)
    a[:, 8] = (170, 166, 160)
    return clip(a)


def tex_pave():
    a = noisy((176, 160, 150), 10)
    mortar = (128, 116, 110)
    for r in range(16):
        if r % 4 == 0:
            a[r, :] = mortar
        off = 0 if (r // 4) % 2 == 0 else 4
        for c in range(16):
            if (c + off) % 8 == 0:
                a[r, c] = mortar
    return clip(a)


def tex_planks():
    a = noisy((168, 134, 82), 8)
    for r in range(16):
        if r % 4 == 3:
            a[r, :] = (112, 86, 52)
    for i, r0 in enumerate(range(0, 16, 4)):
        c = (5 + i * 7) % 16
        a[r0:r0 + 3, c] = (128, 98, 60)
    return clip(a)


def tex_log_side():
    a = noisy((104, 82, 50), 8)
    for c in range(16):
        if c % 3 == 0:
            a[:, c] *= 0.8
    return clip(a)


def tex_log_top():
    a = np.zeros((16, 16, 3), np.float32)
    for r in range(16):
        for c in range(16):
            d = max(abs(r - 7.5), abs(c - 7.5))
            a[r, c] = (104, 82, 50) if d > 6.5 else ((178, 146, 92) if int(d) % 2 else (150, 120, 74))
    return clip(a + rng.uniform(-6, 6, (16, 16, 1)))


def tex_leaves():
    a = noisy((62, 128, 44), 16)
    m = rng.random((16, 16)) < 0.3
    a[m] = (40, 88, 30)
    return clip(a)


def tex_stonebrick():
    a = noisy((132, 132, 132), 8)
    for r in range(16):
        if r % 8 == 7:
            a[r, :] = (92, 92, 92)
        off = 0 if (r // 8) % 2 == 0 else 8
        a[r, (15 - off) % 16] = (92, 92, 92)
    return clip(a)


def tex_water():
    a = noisy((52, 96, 214), 10)
    for r in range(0, 16, 5):
        a[r, rng.integers(0, 10):][:5] = (110, 150, 240)
    return clip(a)


def tex_glass():
    a = noisy((196, 226, 240), 4)
    a[0, :] = a[15, :] = a[:, 0] = a[:, 15] = (236, 240, 244)
    a[3:6, 10] = (250, 252, 255)
    a[4, 9:12] = (250, 252, 255)
    return clip(a)


def tex_roof():
    a = noisy((96, 64, 40), 8)
    for r in range(16):
        if r % 4 == 3:
            a[r, :] = (62, 40, 24)
    return clip(a)


def tex_lamp():
    a = noisy((250, 214, 120), 8)
    a[0, :] = a[15, :] = a[:, 0] = a[:, 15] = (70, 60, 50)
    return clip(a)


def tex_flat(rgb):
    return clip(noisy(rgb, 0))


# ----------------------------------------------------------------------------- materials

FOG = dict(start=18.0, end=80.0)
HAZE = (226, 226, 222)
SKY_TOP = (110, 160, 248)
SKY_HORIZON = (196, 222, 252)


FLAT = False  # --fast: flat Minecraft-like shading (emission only, very fast), no sun/DOF


def flat_material(name, image=None, color=None, fog=True, unlit=False):
    """Fast look: texture * fixed per-face brightness, faded into the haze with distance."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    if image is not None:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = image
        tex.interpolation = "Closest"
        col_socket = tex.outputs["Color"]
    else:
        rgbn = nt.nodes.new("ShaderNodeRGB")
        rgbn.outputs[0].default_value = lin(color)
        col_socket = rgbn.outputs[0]
    if not unlit:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Normal"], sep.inputs[0])
        top = nt.nodes.new("ShaderNodeMath")
        top.operation = "MULTIPLY_ADD"
        top.inputs[1].default_value = 0.22
        top.inputs[2].default_value = 0.80
        nt.links.new(sep.outputs["Z"], top.inputs[0])
        ax = nt.nodes.new("ShaderNodeMath")
        ax.operation = "ABSOLUTE"
        nt.links.new(sep.outputs["X"], ax.inputs[0])
        side = nt.nodes.new("ShaderNodeMath")
        side.operation = "MULTIPLY_ADD"
        side.inputs[1].default_value = -0.10
        nt.links.new(ax.outputs[0], side.inputs[0])
        nt.links.new(top.outputs[0], side.inputs[2])
        comb = nt.nodes.new("ShaderNodeCombineXYZ")
        for i in range(3):
            nt.links.new(side.outputs[0], comb.inputs[i])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(col_socket, mul.inputs[6])
        nt.links.new(comb.outputs[0], mul.inputs[7])
        col_socket = mul.outputs[2]
    if fog:
        cam = nt.nodes.new("ShaderNodeCameraData")
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = FOG["start"]
        mr.inputs["From Max"].default_value = FOG["end"]
        mr.inputs["To Max"].default_value = 0.92
        nt.links.new(cam.outputs["View Distance"], mr.inputs["Value"])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        nt.links.new(mr.outputs[0], mix.inputs[0])
        nt.links.new(col_socket, mix.inputs[6])
        mix.inputs[7].default_value = lin(HAZE)
        col_socket = mix.outputs[2]
    nt.links.new(col_socket, emit.inputs["Color"])
    nt.links.new(emit.outputs[0], out.inputs[0])
    return mat


def shading_material(name, image=None, color=None, fog=True, unlit=False, rough=0.9, spec=0.2, glow=0.0):
    """Lit material: pixel texture on a Principled BSDF (sun + sky light, soft shadows, bounce light),
    faded into the horizon haze with distance."""
    if FLAT:
        return flat_material(name, image, color, fog, unlit)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    if image is not None:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = image
        tex.interpolation = "Closest"
        col_socket = tex.outputs["Color"]
    else:
        rgbn = nt.nodes.new("ShaderNodeRGB")
        rgbn.outputs[0].default_value = lin(color)
        col_socket = rgbn.outputs[0]

    if unlit:
        sh = nt.nodes.new("ShaderNodeEmission")
        sh.inputs["Strength"].default_value = glow or 1.0
        nt.links.new(col_socket, sh.inputs["Color"])
    else:
        sh = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(col_socket, sh.inputs["Base Color"])
        sh.inputs["Roughness"].default_value = rough
        sh.inputs["Specular IOR Level"].default_value = spec
        if glow:
            nt.links.new(col_socket, sh.inputs["Emission Color"])
            sh.inputs["Emission Strength"].default_value = glow
    shader = sh.outputs[0]

    if fog:
        cam = nt.nodes.new("ShaderNodeCameraData")
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = FOG["start"]
        mr.inputs["From Max"].default_value = FOG["end"]
        mr.inputs["To Max"].default_value = 0.92
        nt.links.new(cam.outputs["View Distance"], mr.inputs["Value"])
        haze = nt.nodes.new("ShaderNodeEmission")
        haze.inputs["Color"].default_value = lin(HAZE)
        haze.inputs["Strength"].default_value = 1.0
        ms = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(mr.outputs[0], ms.inputs[0])
        nt.links.new(shader, ms.inputs[1])
        nt.links.new(haze.outputs[0], ms.inputs[2])
        shader = ms.outputs[0]

    nt.links.new(shader, out.inputs[0])
    return mat


def panel_material(name, img_off, img_on):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    t1 = nt.nodes.new("ShaderNodeTexImage")
    t1.image = img_off
    t2 = nt.nodes.new("ShaderNodeTexImage")
    t2.image = img_on
    for t in (t1, t2):
        t.interpolation = "Closest"
    mixc = nt.nodes.new("ShaderNodeMix")
    mixc.data_type = "RGBA"
    mixc.name = "switch"
    nt.links.new(t1.outputs["Color"], mixc.inputs[6])
    nt.links.new(t2.outputs["Color"], mixc.inputs[7])
    mixa = nt.nodes.new("ShaderNodeMix")
    mixa.data_type = "FLOAT"
    mixa.name = "switch_a"
    nt.links.new(t1.outputs["Alpha"], mixa.inputs[2])
    nt.links.new(t2.outputs["Alpha"], mixa.inputs[3])
    emit = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(mixc.outputs[2], emit.inputs["Color"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    ms = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(mixa.outputs[0], ms.inputs[0])
    nt.links.new(tr.outputs[0], ms.inputs[1])
    nt.links.new(emit.outputs[0], ms.inputs[2])
    nt.links.new(ms.outputs[0], out.inputs[0])
    return mat


# ----------------------------------------------------------------------------- voxel meshing

# per face: normal, corners (BL, BR, TR, TL) seen from outside, with "up" = +Z for side faces
FACES = {
    "py": ((0, 1, 0), [(1, 1, 0), (0, 1, 0), (0, 1, 1), (1, 1, 1)]),
    "ny": ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
    "px": ((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]),
    "nx": ((-1, 0, 0), [(0, 1, 0), (0, 0, 0), (0, 0, 1), (0, 1, 1)]),
    "pz": ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]),
    "nz": ((0, 0, -1), [(0, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0)]),
}
UV4 = [(0, 0), (1, 0), (1, 1), (0, 1)]


def build_mesh(name, verts, faces, uvs, mat_idx, materials):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    uvl = me.uv_layers.new(name="UV")
    flat = [c for f in uvs for uv in f for c in uv]
    uvl.data.foreach_set("uv", flat)
    for m in materials:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", mat_idx)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def mesh_voxels(name, blocks, block_tex, mats, scale=1.0, origin=(0.0, 0.0, 0.0)):
    """blocks: {(x,y,z): type}; block_tex: type -> {'top','bottom','side'} material names."""
    mat_names = sorted({n for t in block_tex.values() for n in t.values()})
    mindex = {n: i for i, n in enumerate(mat_names)}
    verts, faces, uvs, midx = [], [], [], []
    ox, oy, oz = origin
    for (x, y, z), t in blocks.items():
        for key, (n, corners) in FACES.items():
            nb = (x + n[0], y + n[1], z + n[2])
            if nb in blocks:
                continue
            slot = "top" if key == "pz" else ("bottom" if key == "nz" else "side")
            i0 = len(verts)
            for cx, cy, cz in corners:
                verts.append(((x + cx) * scale + ox, (y + cy) * scale + oy, (z + cz) * scale + oz))
            faces.append((i0, i0 + 1, i0 + 2, i0 + 3))
            uvs.append(UV4)
            midx.append(mindex[block_tex[t][slot]])
    return build_mesh(name, verts, faces, uvs, midx, [mats[n] for n in mat_names])


# ----------------------------------------------------------------------------- characters

LAYOUT = {
    "head": (0, 0, 8, 8, 8),
    "body": (16, 16, 8, 12, 4),
    "rarm": (40, 16, 4, 12, 4),
    "rleg": (0, 16, 4, 12, 4),
    "larm": (32, 48, 4, 12, 4),
    "lleg": (16, 48, 4, 12, 4),
}


def face_rects(u, v, w, h, d):
    return {
        "pz": (u + d, v, w, d),
        "nz": (u + d + w, v, w, d),
        "nx": (u, v + d, d, h),
        "ny": (u + d, v + d, w, h),
        "px": (u + d + w, v + d, d, h),
        "py": (u + 2 * d + w, v + d, w, h),
    }


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

    def image(self, name):
        return new_image(name, clip(self.a))


ALL = ["pz", "nz", "nx", "ny", "px", "py"]
SIDES = ["nx", "ny", "px", "py"]


def base_skin(skin, shirt, pants, shoes, hair, eyes, sleeve_rows=4):
    s = Skin()
    s.fill("head", ALL, skin, 4)
    s.fill("head", ["pz"], hair, 6)
    s.fill("head", ["nx", "px", "py"], hair, 6, rows=(0, 3))
    s.fill("head", ["py"], hair, 6, rows=(0, 5))
    s.fill("head", ["ny"], hair, 6, rows=(0, 2))
    # eyes, brows, mouth
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
    # hood around the face
    s.fill("head", ["pz", "nx", "px", "py"], hood, 4)
    v = s.view("head", "ny")
    v[0] = hood
    v[:, 0] = hood
    v[:, 7] = hood
    v[1, 1:7] = (52, 36, 26)
    # sunglasses with green lenses
    v[3, 1:7] = (14, 14, 16)
    v[4, 1:7] = (14, 14, 16)
    v[4, 1:3] = (24, 110, 50)
    v[4, 5:7] = (24, 110, 50)
    v[3, 1] = (140, 255, 170)
    v[3, 5] = (140, 255, 170)
    # smirk
    v[6, 3:6] = (196, 146, 104)
    v[6, 3:5] = (110, 60, 46)
    v[5, 5] = (110, 60, 46)
    # hoodie: green strings + chest logo "</>"
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
    cap = (214, 48, 48)
    s = base_skin((226, 182, 142), (52, 112, 212), (70, 72, 84), (34, 34, 36), (86, 58, 36), (70, 110, 200))
    s.fill("head", ["pz"], cap, 5)
    s.fill("head", SIDES, cap, 5, rows=(0, 2))
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
    s = base_skin((246, 218, 198), (152, 202, 242), (120, 124, 140), (240, 240, 244), (240, 234, 216), (70, 140, 230), sleeve_rows=12)
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


def box_mesh(name, w, h, d, offset, part, mat):
    """Box of w(x) h(z) d(y) skin pixels, min corner at offset (px), UVs from the skin layout."""
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


def empty(name, parent=None, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.parent = parent
    e.location = loc
    return e


def yaw_to(src, dst):
    return math.atan2(dst[0] - src[0], -(dst[1] - src[1]))


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


# ----------------------------------------------------------------------------- keyframes

class Keys:
    """Collects keyframes so 'tween' can hold the previous value until the transition starts."""

    def __init__(self):
        self.tracks = {}

    def set(self, obj, path, f, val):
        self.tracks.setdefault((obj.name, path), {})[f] = tuple(val) if hasattr(val, "__len__") else val

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

    def flush(self):
        for (name, path), tr in self.tracks.items():
            obj = bpy.data.objects[name]
            for f in sorted(tr):
                setattr(obj, path, tr[f])
                obj.keyframe_insert(path, frame=f)


K = Keys()


class Char:
    def __init__(self, name, skin, pos, yaw, mats_cache):
        self.name = name
        img = skin.image(f"skin_{name}")
        mat = shading_material(f"mat_{name}", image=img)
        self.mat = mat
        self.root = empty(f"{name}_root", loc=pos)
        self.root.rotation_euler = (0, 0, yaw)
        r = self.root
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
        # surprised "O" mouth, hidden (scale 0) until needed
        self.mouth = box_mesh(f"{name}_mouth", 2, 2, 0.6, (-1, -4.5, 1), None, mats_cache["mouth"])
        self.mouth.parent = self.head
        self.mouth.scale = (0, 0, 0)
        self.limbs = (self.rarm, self.larm, self.rleg, self.lleg)
        for o in (self.root, self.head) + self.limbs:
            o.rotation_mode = "XYZ"

    @property
    def pos(self):
        return tuple(self.root.location)

    def accessory(self, name, w, h, d, offset, mat, parent=None):
        ob = box_mesh(f"{self.name}_{name}", w, h, d, offset, None, mat)
        ob.parent = parent or self.head
        return ob

    def head_pos(self, f=None):
        p = K.value_at(self.root, "location", f) if f is not None else self.pos
        return (p[0], p[1], p[2] + 1.6)

    def look(self, f0, f1, target, body_follow=0.0, pitch_extra=0.0):
        """Turn head (and optionally part of the body) toward a world point."""
        p = K.value_at(self.root, "location", f1)
        ry = K.value_at(self.root, "rotation_euler", f1)[2]
        want = yaw_to(p, target)
        new_root = ry + wrap(want - ry) * body_follow
        if body_follow:
            K.tween(self.root, "rotation_euler", f0, f1, (0, 0, new_root))
        rel = max(-1.2, min(1.2, wrap(want - new_root)))
        hp = (p[0], p[1], p[2] + 1.6)
        dist = math.hypot(target[0] - hp[0], target[1] - hp[1])
        pitch = math.atan2(target[2] - hp[2], dist) + pitch_extra
        pitch = max(-0.9, min(0.9, pitch))
        K.tween(self.head, "rotation_euler", f0, f1, (-pitch, 0, rel))

    def walk(self, f0, f1, p1, swing=0.6):
        p0 = K.value_at(self.root, "location", f0)
        K.set(self.root, "location", f0, p0)
        K.set(self.root, "location", f1, p1)
        y = yaw_to(p0, p1)
        K.set(self.root, "rotation_euler", f0, (0, 0, y))
        K.set(self.root, "rotation_euler", f1, (0, 0, y))
        step = 7
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

    def idle_arms(self, f0, f1, phase=0.0):
        for f in range(f0, f1 + 1, 20):
            s = math.sin(f / 9.0 + phase)
            K.set(self.rarm, "rotation_euler", f, (0.05 * s, 0, -0.04))
            K.set(self.larm, "rotation_euler", f, (-0.05 * s, 0, 0.04))

    def jump(self, f0, h=0.45):
        p = K.value_at(self.root, "location", f0)
        K.set(self.root, "location", f0, p)
        K.set(self.root, "location", f0 + 5, (p[0], p[1], p[2] + h))
        K.set(self.root, "location", f0 + 10, p)

    def surprised(self, f):
        K.tween(self.mouth, "scale", f, f + 3, (1, 1, 1))
        K.tween(self.rarm, "rotation_euler", f, f + 4, (-0.35, 0, -0.35))
        K.tween(self.larm, "rotation_euler", f, f + 4, (-0.35, 0, 0.35))


# ----------------------------------------------------------------------------- world

def ground_height(x, y):
    r = math.hypot(x, y)
    if r < 22:
        return 0
    k = (r - 22) / 9.0
    h = k * (1.0 + 0.8 * math.sin(x * 0.17) + 0.8 * math.cos(y * 0.13 + 1.0))
    return int(max(0, min(6, h)))


def build_world(mats):
    B = {}
    R = 62
    heights = {}
    for x in range(-R, R + 1):
        for y in range(-R, R + 1):
            h = ground_height(x, y)
            heights[(x, y)] = h
            for z in range(-3, h):
                B[(x, y, z)] = "grass" if z == h - 1 else "dirt"
    # plaza
    for x in range(-10, 11):
        for y in range(-10, 11):
            m = max(abs(x), abs(y))
            pave = m in (4, 10) or abs(x) <= 1 or abs(y) <= 1
            B[(x, y, -1)] = "pave" if pave else "tile"
    # path to the house
    for y in range(11, 16):
        for x in range(-8, -5):
            B[(x, y, -1)] = "pave"
    # well
    for x in range(-2, 3):
        for y in range(-2, 3):
            if max(abs(x), abs(y)) == 2:
                B[(x, y, 0)] = "stonebrick"
            else:
                B[(x, y, -1)] = "water"
    # lamp posts
    for x, y in ((-9, -9), (9, -9), (-9, 9), (9, 9)):
        B[(x, y, 0)] = "log"
        B[(x, y, 1)] = "log"
        B[(x, y, 2)] = "lamp"
    # house
    x0, x1, y0, y1 = -11, -3, 10, 16
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            B[(x, y, -1)] = "planks"
            edge_x, edge_y = x in (x0, x1), y in (y0, y1)
            if edge_x or edge_y:
                for z in range(0, 4):
                    B[(x, y, z)] = "log" if (edge_x and edge_y) else "planks"
    for z in (0, 1):
        B.pop((-7, y0, z), None)  # door
    for x in (-9, -5):
        for z in (1, 2):
            B[(x, y0, z)] = "glass"
    for y in (12, 14):
        for z in (1, 2):
            B[(x1, y, z)] = "glass"
    for i, z in enumerate(range(4, 8)):
        for x in range(x0 - 1 + i, x1 + 2 - i):
            for y in range(y0 - 1 + i, y1 + 2 - i):
                if i == 3 or x in (x0 - 1 + i, x1 + 1 - i) or y in (y0 - 1 + i, y1 + 1 - i):
                    B[(x, y, z)] = "roof"
    # trees
    cams = [(1.5, -12.5), (0.1, -7.2)]
    trees = []
    tries = 0
    while len(trees) < 70 and tries < 4000:
        tries += 1
        x, y = random.randint(-52, 52), random.randint(-52, 52)
        r = math.hypot(x, y)
        if r < 14:
            continue
        if x0 - 4 <= x <= x1 + 4 and y0 - 4 <= y <= y1 + 4:
            continue
        if y < -8 and -9 < x < 10:
            continue  # keep the camera side clear
        if any(math.hypot(x - cx, y - cy) < 5 for cx, cy in cams):
            continue
        if any(math.hypot(x - tx, y - ty) < 5 for tx, ty in trees):
            continue
        trees.append((x, y))
    for x, y in trees:
        h0 = heights.get((x, y), 0)
        th = random.randint(4, 6)
        for z in range(h0, h0 + th):
            B[(x, y, z)] = "log"
        top = h0 + th
        for dz, rad in ((-2, 2), (-1, 2), (0, 1), (1, 1)):
            for dx in range(-rad, rad + 1):
                for dy in range(-rad, rad + 1):
                    if abs(dx) == rad and abs(dy) == rad and (rad == 1 or random.random() < 0.6):
                        continue
                    p = (x + dx, y + dy, top + dz)
                    if p not in B:
                        B[p] = "leaves"
    block_tex = {
        "grass": dict(top="grass_top", bottom="dirt", side="grass_side"),
        "dirt": dict(top="dirt", bottom="dirt", side="dirt"),
        "tile": dict(top="tile", bottom="tile", side="tile"),
        "pave": dict(top="pave", bottom="pave", side="pave"),
        "planks": dict(top="planks", bottom="planks", side="planks"),
        "log": dict(top="log_top", bottom="log_top", side="log_side"),
        "leaves": dict(top="leaves", bottom="leaves", side="leaves"),
        "stonebrick": dict(top="stonebrick", bottom="stonebrick", side="stonebrick"),
        "water": dict(top="water", bottom="water", side="water"),
        "glass": dict(top="glass", bottom="glass", side="glass"),
        "roof": dict(top="roof", bottom="roof", side="roof"),
        "lamp": dict(top="lamp", bottom="lamp", side="lamp"),
    }
    world = mesh_voxels("world", B, block_tex, mats, origin=(-0.5, -0.5, 0.0))
    return world


def build_clouds(mat):
    blocks = {}
    for i in range(16):
        cx, cy = random.randint(-70, 70), random.randint(-40, 90)
        w, d = random.randint(6, 14), random.randint(4, 9)
        for x in range(w):
            for y in range(d):
                if (x in (0, w - 1) and y in (0, d - 1)):
                    continue
                blocks[(cx + x, cy + y, 0)] = "c"
                if random.random() < 0.15 and 0 < x < w - 1 and 0 < y < d - 1:
                    blocks[(cx + x, cy + y, 1)] = "c"
    ob = mesh_voxels("clouds", blocks, {"c": dict(top="cloud", bottom="cloud", side="cloud")}, {"cloud": mat},
                     scale=1.6, origin=(0, 0, 34))
    return ob


QMARK = [".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."]
EXCL = ["..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."]


def voxel_symbol(name, rows, mat, size=0.075):
    blocks = {}
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch == "#":
                blocks[(c, 0, len(rows) - 1 - r)] = "s"
    ob = mesh_voxels(name, blocks, {"s": dict(top="m", bottom="m", side="m")}, {"m": mat}, scale=size,
                     origin=(-2.5 * size, -0.5 * size, 0))
    return ob


# ----------------------------------------------------------------------------- panel (cheat client GUI)

def make_panel_images(font_path, tmpdir):
    from PIL import Image, ImageDraw, ImageFont

    imgs = []
    for on in (False, True):
        W, H = 400, 300
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W - 1, H - 1], fill=(8, 14, 10, 215), outline=(70, 230, 100, 255), width=6)
        d.rectangle([0, 0, W - 1, 58], fill=(70, 230, 100, 255))
        ft = ImageFont.truetype(font_path, 32)
        fb = ImageFont.truetype(font_path, 32)
        d.text((18, 12), "БРО-КЛИЕНТ v6.6", font=ft, fill=(8, 14, 10, 255))
        rows = [("Полёт", True), ("Без урона", True), ("Скорость", False), ("MassTPA", on)]
        for i, (label, state) in enumerate(rows):
            y = 76 + i * 54
            hl = label == "MassTPA"
            if hl:
                d.rectangle([10, y - 4, W - 11, y + 44], fill=(70, 230, 100, 255) if on else (40, 60, 48, 255))
            col = (8, 14, 10, 255) if (hl and on) else (220, 240, 225, 255)
            d.text((24, y), ("> " if hl else "") + label, font=fb, fill=col)
            st = "ВКЛ" if state else "ВЫКЛ"
            scol = (8, 14, 10, 255) if (hl and on) else ((70, 230, 100, 255) if state else (230, 80, 80, 255))
            d.text((W - 100, y), st, font=fb, fill=scol)
        p = os.path.join(tmpdir, f"panel_{int(on)}.png")
        im.save(p)
        img = bpy.data.images.load(p)
        img.pack()
        imgs.append(img)
    return imgs


# ----------------------------------------------------------------------------- scene assembly

def build(args):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, FRAMES

    # world sky gradient
    world = bpy.data.worlds.new("sky")
    scene.world = world
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
    bg.inputs["Strength"].default_value = 1.1

    # warm afternoon sun with soft shadows
    sun_d = bpy.data.lights.new("sun", "SUN")
    sun_d.energy = 4.2
    sun_d.angle = math.radians(4.0)
    sun_d.color = (1.0, 0.86, 0.68)
    sun = bpy.data.objects.new("sun", sun_d)
    scene.collection.objects.link(sun)
    sun.rotation_euler = Vector((0.75, -0.55, 0.62)).to_track_quat("Z", "Y").to_euler()

    texs = {
        "grass_top": tex_grass_top(), "dirt": tex_dirt(), "grass_side": tex_grass_side(), "tile": tex_tile(),
        "pave": tex_pave(), "planks": tex_planks(), "log_side": tex_log_side(), "log_top": tex_log_top(),
        "leaves": tex_leaves(), "stonebrick": tex_stonebrick(), "water": tex_water(), "glass": tex_glass(),
        "roof": tex_roof(), "lamp": tex_lamp(),
    }
    mats = {k: shading_material(k, image=new_image(k, v)) for k, v in texs.items()}
    mats["water"] = shading_material("water_g", image=new_image("water2", texs["water"]), rough=0.08, spec=0.6)
    mats["glass"] = shading_material("glass_g", image=new_image("glass2", texs["glass"]), rough=0.05, spec=0.8)
    mats["lamp"] = shading_material("lamp_u", image=new_image("lamp2", texs["lamp"]), glow=3.0)
    cloud_mat = shading_material("cloud", color=(250, 250, 252), fog=False, unlit=True, glow=1.15)
    mats["mouth"] = shading_material("mouth", color=(60, 26, 26), fog=False)
    purple = shading_material("purple", color=(170, 50, 255), fog=False, unlit=True, glow=1.6)
    purple2 = shading_material("purple2", color=(110, 20, 210), fog=False, unlit=True, glow=1.2)
    gold = shading_material("gold", color=(255, 176, 0), fog=False, rough=0.4, spec=0.5, glow=0.08)
    gold_acc = shading_material("gold_acc", color=(252, 202, 46))
    brim = shading_material("brim", color=(180, 36, 36))
    ear = shading_material("ear", color=(128, 128, 132))
    ear_in = shading_material("ear_in", color=(240, 160, 170))

    build_world(mats)
    build_clouds(cloud_mat)

    # ---- characters
    HOVER = (-0.6, 4.0, 7.6)
    bro = Char("brohacker", skin_brohacker(), HOVER, math.radians(14), mats)
    masha = Char("pixel_masha", skin_masha(), (-1.1, -3.7, 0), 0.0, mats)
    dimon = Char("dimon_pro", skin_dimon(), (0.5, -4.2, 0), 0.0, mats)
    lava = Char("lavaKing", skin_lava(), (4.6, -7.6, 0), 0.0, mats)
    snow = Char("snowbunny", skin_snow(), (-3.3, 0.4, 0), math.radians(-90), mats)
    kotik = Char("kotik_777", skin_kotik(), (4.2, 4.5, 0), 0.0, mats)
    players = [masha, dimon, snow, lava, kotik]
    chars = [bro] + players

    dimon.accessory("brim", 8, 1, 3, (-4, -7, 6), brim)
    for dx in (-3, -0.5, 2):
        lava.accessory(f"crown{dx}", 1, 2, 1, (dx, -4, 8), gold_acc)
    for side in (-1, 1):
        e = kotik.accessory(f"ear{side}", 2, 2, 1, (side * 2.5 - 1, -1, 8), ear)
        kotik.accessory(f"earin{side}", 1, 1, 0.3, (side * 2.5 - 0.5, -1.2, 8), ear_in)

    # initial facing
    masha.root.rotation_euler = (0, 0, yaw_to(masha.pos, dimon.pos))
    dimon.root.rotation_euler = (0, 0, yaw_to(dimon.pos, masha.pos))

    # ---- cheat panel next to brohacker (faces camera A)
    tmpdir = args.out
    off_img, on_img = make_panel_images(FONT, tmpdir)
    pmat = panel_material("panel", off_img, on_img)
    bpy.ops.mesh.primitive_plane_add(size=1)
    panel = bpy.context.active_object
    panel.name = "panel"
    panel.scale = (0.0, 0.0, 0.0)
    panel.data.materials.append(pmat)
    panel.location = (HOVER[0] + 0.9, HOVER[1] - 0.45, HOVER[2] + 2.0)

    # ---- cameras
    def make_cam(name, lens):
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.sensor_fit = "VERTICAL"
        cd.sensor_height = 24
        cd.clip_end = 400
        cam = bpy.data.objects.new(name, cd)
        scene.collection.objects.link(cam)
        tgt = empty(name + "_target")
        con = cam.constraints.new("TRACK_TO")
        con.target = tgt
        con.track_axis = "TRACK_NEGATIVE_Z"
        con.up_axis = "UP_Y"
        return cam, tgt

    camA, tA = make_cam("camA", 30)
    camB, tB = make_cam("camB", 22)
    camC, tC = make_cam("camC", 20)
    cams = {"A": camA, "B": camB, "C": camC}
    for cam, focus, fstop in () if FLAT else ((camA, bro.head, 1.6), (camB, dimon.head, 2.4), (camC, bro.head, 1.8)):
        cam.data.dof.use_dof = True
        cam.data.dof.focus_object = focus
        cam.data.dof.aperture_fstop = fstop

    # shot A: slow orbit around the cheater
    hx, hy, hz = HOVER
    K.set(camA, "location", 1, (hx + 1.6, hy - 4.3, hz + 1.0))
    K.set(camA, "location", 62, (hx + 0.6, hy - 3.9, hz + 0.9))
    K.set(tA, "location", 1, (hx + 0.5, hy - 0.3, hz + 1.3))
    K.set(tA, "location", 62, (hx + 0.45, hy - 0.3, hz + 1.25))
    # shot B: wide on the spawn, slow push-in
    K.set(camB, "location", 63, (1.6, -13.0, 3.4))
    K.set(camB, "location", 150, (0.9, -10.6, 3.1))
    K.set(tB, "location", 63, (-0.4, 2.0, 3.4))
    K.set(tB, "location", 150, (-0.4, 2.0, 3.8))
    # shot C: low over-the-shoulder, everyone staring at the cheater
    K.set(camC, "location", 151, (0.2, -7.5, 0.8))
    K.set(camC, "location", 240, (-0.2, -6.6, 1.0))
    K.set(tC, "location", 151, (-0.5, 2.5, 5.0))
    K.set(tC, "location", 240, (-0.5, 2.9, 5.4))

    # panel faces camera A
    con = panel.constraints.new("TRACK_TO")
    con.target = camA
    con.track_axis = "TRACK_Z"
    con.up_axis = "UP_Y"

    # ---- brohacker animation
    for f in range(1, FRAMES + 1, 15):
        K.set(bro.root, "location", f, (hx, hy, hz + 0.09 * math.sin(f / 7.0)))
    for f in range(1, FRAMES + 1, 20):
        s = math.sin(f / 8.0)
        K.set(bro.rleg, "rotation_euler", f, (0.18 + 0.08 * s, 0, 0))
        K.set(bro.lleg, "rotation_euler", f, (-0.08 - 0.08 * s, 0, 0))
    K.set(bro.rarm, "rotation_euler", 1, (0.1, 0, -0.1))
    K.set(bro.larm, "rotation_euler", 1, (0, 0, 0.1))
    K.set(bro.head, "rotation_euler", 1, (0.05, 0, 0.35))
    K.set(bro.head, "rotation_euler", 12, (0.05, 0, 0.55))  # glances at the panel
    # click
    K.set(bro.larm, "rotation_euler", 14, (0, 0, 0.1))
    K.set(bro.larm, "rotation_euler", 20, (-1.75, 0, 0.55))
    K.set(bro.larm, "rotation_euler", 24, (-1.45, 0, 0.55))
    K.set(bro.larm, "rotation_euler", 27, (-1.75, 0, 0.55))
    K.set(bro.larm, "rotation_euler", 40, (-1.7, 0, 0.5))
    K.set(bro.larm, "rotation_euler", 48, (0, 0, 0.1))
    # laugh
    K.set(bro.head, "rotation_euler", 30, (0.0, 0, 0.1))
    for i, f in enumerate(range(34, 60, 4)):
        K.set(bro.head, "rotation_euler", f, ((-0.22 if i % 2 == 0 else -0.05), 0, 0.05))
    K.set(bro.rarm, "rotation_euler", 34, (0.1, 0, -0.1))
    K.set(bro.rarm, "rotation_euler", 40, (-0.6, 0, -0.5))
    K.set(bro.rarm, "rotation_euler", 56, (-0.6, 0, -0.5))
    K.set(bro.rarm, "rotation_euler", 62, (0.1, 0, -0.1))
    # after the cut he looks down at the spawn
    K.set(bro.head, "rotation_euler", 63, (0.45, 0, -0.1))
    K.set(bro.root, "rotation_euler", 1, (0, 0, math.radians(14)))
    K.set(bro.root, "rotation_euler", 62, (0, 0, math.radians(14)))
    K.set(bro.root, "rotation_euler", 63, (0, 0, math.radians(-12)))
    K.set(bro.head, "rotation_euler", 160, (0.45, 0, -0.1))
    # waves at everyone in shot C
    K.set(bro.rarm, "rotation_euler", 176, (0.1, 0, -0.1))
    K.set(bro.rarm, "rotation_euler", 182, (0, 2.45, 0))
    for i, f in enumerate(range(186, 241, 5)):
        K.set(bro.rarm, "rotation_euler", f, (0, 2.2 if i % 2 == 0 else 2.65, 0))
    K.set(bro.head, "rotation_euler", 170, (0.35, 0, -0.25))

    # panel pop-in and the switch to ON
    K.set(panel, "scale", 4, (0, 0, 0))
    K.set(panel, "scale", 9, (0.92, 0.69, 1))
    K.set(panel, "scale", 11, (0.82, 0.615, 1))
    K.set(panel, "scale", 50, (0.82, 0.615, 1))
    K.set(panel, "scale", 56, (0, 0, 0))
    sw = pmat.node_tree.nodes["switch"].inputs[0]
    swa = pmat.node_tree.nodes["switch_a"].inputs[0]
    for f, v in ((1, 0.0), (23, 0.0), (24, 1.0)):
        for sock in (sw, swa):
            sock.default_value = v
            sock.keyframe_insert("default_value", frame=f)

    # purple fountain of teleport requests flying out of the cheater into the sky
    prng = random.Random(3)
    for i in range(44):
        a = 2 * math.pi * i / 44 + prng.uniform(-0.1, 0.1)
        ob = box_mesh(f"burst{i}", 2, 2, 2, (-1, -1, -1), None, purple if i % 2 else purple2)
        ob.scale = (0, 0, 0)
        start = 30 + (i % 4) * 3
        dur = prng.randint(18, 26)
        c = Vector((hx, hy, hz + 1.1))
        rad = prng.uniform(1.0, 2.4)
        end = c + Vector((math.cos(a) * rad, math.sin(a) * rad * 0.6 + 0.8, prng.uniform(3.5, 6.5)))
        K.set(ob, "location", start, tuple(c))
        K.set(ob, "location", start + dur, tuple(end))
        K.set(ob, "scale", start - 1, (0, 0, 0))
        K.set(ob, "scale", start + 2, (1.3, 1.3, 1.3))
        K.set(ob, "scale", start + dur, (0.3, 0.3, 0.3))
        K.set(ob, "scale", start + dur + 1, (0, 0, 0))

    # ---- players before the requests arrive
    for c in players:
        K.set(c.root, "location", 63, c.pos)
        K.set(c.root, "rotation_euler", 63, tuple(c.root.rotation_euler))
    masha.idle_arms(63, 66, 0.0)
    snow.idle_arms(63, 70, 1.0)
    dimon.idle_arms(63, 66, 2.0)
    # dimon talking with hand gestures
    K.set(dimon.rarm, "rotation_euler", 63, (-0.5, 0, -0.1))
    K.set(dimon.rarm, "rotation_euler", 67, (-0.8, 0, -0.1))
    lava.walk(63, 80, (1.9, -7.1, 0))
    kotik.walk(63, 84, (3.0, 0.2, 0))

    requests = {masha: 68, dimon: 71, snow: 74, lava: 80, kotik: 84}
    camB_pos = (1.4, -12.2, 3.3)
    swirls = []
    symbols = []
    for c, fr in requests.items():
        # purple teleport-request particles spinning around the player
        sw_e = empty(f"{c.name}_swirl", parent=c.root)
        sw_e.scale = (0, 0, 0)
        for i in range(18):
            a = 2 * math.pi * i / 18 * 2.5
            z = 0.1 + 1.9 * i / 18
            ob = box_mesh(f"{c.name}_p{i}", 2.4, 2.4, 2.4, (-1.2, -1.2, -1.2), None, purple if i % 2 else purple2)
            ob.parent = sw_e
            ob.location = (0.62 * math.cos(a), 0.62 * math.sin(a), z)
        K.set(sw_e, "scale", fr, (0, 0, 0))
        K.set(sw_e, "scale", fr + 4, (1.15, 1.15, 1.15))
        K.set(sw_e, "scale", fr + 26, (1.0, 1.0, 1.0))
        K.set(sw_e, "scale", fr + 32, (0, 0, 0))
        swirls.append((sw_e, fr))
        # "?" or "!" above the head
        sym = voxel_symbol(f"{c.name}_q", EXCL if c is lava else QMARK, gold)
        sym.parent = c.root
        sym.location = (0, 0, 2.25)
        sym.scale = (0, 0, 0)
        K.set(sym, "scale", fr + 5, (0, 0, 0))
        K.set(sym, "scale", fr + 9, (1.35, 1.35, 1.35))
        K.set(sym, "scale", fr + 12, (1.0, 1.0, 1.0))
        symbols.append(sym)
        c.surprised(fr + 4)

    # reactions
    masha.look(70, 76, camB_pos)
    dimon.jump(76)
    dimon.look(73, 79, masha.head_pos(73))
    snow.look(76, 82, dimon.head_pos(76), body_follow=0.5)
    lava.jump(83)
    lava.look(82, 88, camB_pos, body_follow=0.4)
    kotik.look(86, 92, masha.head_pos(86), body_follow=0.4)
    # everyone looks up at the cheater
    bro_head = (hx, hy, hz + 1.6)
    for i, c in enumerate(players):
        c.look(134 + i * 3, 142 + i * 3, bro_head, body_follow=0.7)
    # kotik points at him
    K.tween(kotik.rarm, "rotation_euler", 156, 162, (-2.3, 0, 0.0))
    K.tween(masha.larm, "rotation_euler", 196, 202, (-0.35, 0, 0.35))

    K.flush()

    # linear rotation for spinning swirls / symbols (keys every frame)
    for sw_e, fr in swirls:
        for f in range(fr, min(FRAMES, fr + 34) + 1):
            sw_e.rotation_euler = (0, 0, (f - fr) * 0.32)
            sw_e.keyframe_insert("rotation_euler", frame=f)
    for sym in symbols:
        for f in range(1, FRAMES + 1, 2):
            sym.rotation_euler = (0, 0, 0.35 * math.sin(f / 6.0))
            sym.keyframe_insert("rotation_euler", frame=f)

    # ---- render settings
    r = scene.render
    r.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.02
    scene.cycles.max_bounces = 4
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 2
    scene.cycles.sample_clamp_indirect = 6.0
    scene.cycles.transparent_max_bounces = 8
    scene.cycles.caustics_reflective = False
    scene.cycles.caustics_refractive = False
    scene.cycles.filter_width = 1.2
    r.use_persistent_data = True
    w, h = map(int, args.res.split("x"))
    r.resolution_x, r.resolution_y = w, h
    r.resolution_percentage = 100
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    if FLAT:
        scene.cycles.use_denoising = False
        scene.cycles.max_bounces = 0
        sun_d.energy = 0.0
    scene.view_settings.view_transform = "Standard" if FLAT else "AgX"
    try:
        scene.view_settings.look = "None" if FLAT else "AgX - Medium High Contrast"
    except TypeError:
        pass
    scene.view_settings.exposure = 0.0 if FLAT else 0.15

    return scene, cams, chars


def cam_for(f):
    for name, a, b in SHOTS:
        if a <= f <= b:
            return name
    return "C"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--res", default="720x1280")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--frames", default=f"1-{FRAMES}", help="e.g. 1-150 or 10,70,130")
    ap.add_argument("--blend", help="also save the .blend file here")
    ap.add_argument("--fast", action="store_true", help="flat shading, renders in ~1 s/frame")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    global FLAT
    FLAT = args.fast

    scene, cams, chars = build(args)
    if args.blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.blend))

    if "-" in args.frames:
        a, b = map(int, args.frames.split("-"))
        frames = list(range(a, b + 1))
    else:
        frames = [int(x) for x in args.frames.split(",")]

    # nametag positions for the overlay
    w, h = scene.render.resolution_x, scene.render.resolution_y
    meta = {"fps": FPS, "frames": FRAMES, "res": [w, h], "shots": SHOTS, "tags": {}}
    for f in range(1, FRAMES + 1):
        scene.frame_set(f)
        cam = cams[cam_for(f)]
        scene.camera = cam
        bpy.context.view_layer.update()
        cam_up = cam.matrix_world.to_3x3() @ Vector((0, 1, 0))
        tags = []
        for c in chars:
            p = c.root.matrix_world @ Vector((0, 0, 2.02))
            co = world_to_camera_view(scene, cam, p)
            if co.z <= 0.3:
                continue
            co2 = world_to_camera_view(scene, cam, p + cam_up * 0.25)
            size = abs(co2.y - co.y) * h
            tags.append({"name": c.name, "x": co.x * w, "y": (1 - co.y) * h, "size": size, "depth": co.z})
        meta["tags"][f] = tags
    with open(os.path.join(args.out, "meta.json"), "w") as fh:
        json.dump(meta, fh)

    for f in frames:
        path = os.path.join(args.out, f"f{f:04d}.png")
        if os.path.exists(path) and os.environ.get("SKIP_EXISTING"):
            continue
        scene.frame_set(f)
        scene.camera = cams[cam_for(f)]
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print(f"rendered {f}", flush=True)


if __name__ == "__main__":
    main()

"""Realistic-ish humans for LUNCH MONEY, built by our own code from MakeHuman CC0 *data* (base mesh, morph
targets, skins, proxies, rig + weights). No MakeHuman/MPFB code is executed.

Paths: LM_MPFB (MPFB data dir with 3dobjs/targets/rigs) and LM_ASSETS (makehuman_system_assets_cc0).
"""
import gzip
import json
import math
import os
import random

import bpy
import numpy as np
from mathutils import Matrix, Vector

SCR = "/tmp/claude-0/-home-user-burs/50d68f62-1d58-507a-905b-8de2613f55c7/scratchpad/dl"
MPFB = os.environ.get("LM_MPFB", os.path.join(SCR, "mpfb", "data"))
ASSETS = os.environ.get("LM_ASSETS", os.path.join(SCR, "mhassets"))
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.environ.get("LM_TEX", os.path.join(os.path.dirname(SCR), "tex"))

_cache = {}


# ============================================================================ parsing

def load_obj(path):
    """Returns verts (N,3), uvs (M,2), faces [(vidx tuple, uvidx tuple, group)], groups {name: set(vidx)}."""
    if path in _cache:
        return _cache[path]
    vs, vts, faces, groups = [], [], [], {}
    g = None
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if line.startswith("v "):
                vs.append([float(x) for x in line.split()[1:4]])
            elif line.startswith("vt "):
                vts.append([float(x) for x in line.split()[1:3]])
            elif line.startswith("g "):
                g = line.split(None, 1)[1].strip()
            elif line.startswith("f "):
                vi, ti = [], []
                for tok in line.split()[1:]:
                    p = tok.split("/")
                    vi.append(int(p[0]) - 1)
                    ti.append(int(p[1]) - 1 if len(p) > 1 and p[1] else -1)
                faces.append((tuple(vi), tuple(ti), g))
                if g:
                    groups.setdefault(g, set()).update(vi)
    res = (np.array(vs, np.float64), np.array(vts, np.float64) if vts else np.zeros((0, 2)), faces, groups)
    _cache[path] = res
    return res


def load_target(rel):
    if rel in _cache:
        return _cache[rel]
    path = os.path.join(MPFB, "targets", rel)
    idx, d = [], []
    with gzip.open(path, "rt") as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            p = line.split()
            idx.append(int(p[0]))
            d.append([float(p[1]), float(p[2]), float(p[3])])
    res = (np.array(idx, np.int64), np.array(d, np.float64).reshape(-1, 3))
    _cache[rel] = res
    return res


def parse_kv(path):
    out = {}
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            p = line.split(None, 1)
            out.setdefault(p[0], p[1] if len(p) > 1 else "")
    return out


def load_mhclo(path):
    if path in _cache:
        return _cache[path]
    hdr, refs, w, off, scales = {}, [], [], [], {}
    mode = None
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            s = line.strip()
            if not s or s.startswith("#"):
                if mode == "verts" and not s:
                    mode = None
                continue
            p = s.split()
            if p[0] == "verts":
                mode = "verts"
                continue
            if p[0] in ("delete_verts", "weights", "faces"):
                mode = None
                continue
            if mode == "verts" and (p[0].lstrip("-").isdigit()):
                if len(p) == 1:
                    refs.append([int(p[0])] * 3)
                    w.append([1.0, 0.0, 0.0])
                    off.append([0, 0, 0])
                else:
                    refs.append([int(p[0]), int(p[1]), int(p[2])])
                    w.append([float(p[3]), float(p[4]), float(p[5])])
                    off.append([float(p[6]), float(p[7]), float(p[8])])
                continue
            if p[0] in ("x_scale", "y_scale", "z_scale"):
                scales[p[0][0]] = (int(p[1]), int(p[2]), float(p[3]))
            else:
                hdr.setdefault(p[0], " ".join(p[1:]))
    res = {"hdr": hdr, "refs": np.array(refs), "w": np.array(w), "off": np.array(off), "scales": scales,
           "dir": os.path.dirname(path)}
    _cache[path] = res
    return res


# ============================================================================ shape

BASE_OBJ = os.path.join(MPFB, "3dobjs", "base.obj")


def base():
    return load_obj(BASE_OBJ)


def _tri(v):
    """1D weights for min/average/max given v in [0,1]"""
    if v < 0.5:
        return {"min": (0.5 - v) * 2, "average": 1 - (0.5 - v) * 2, "max": 0.0}
    return {"min": 0.0, "average": 1 - (v - 0.5) * 2, "max": (v - 0.5) * 2}


FACE_TARGETS = [
    "nose/nose-scale-horiz-{}.target.gz", "nose/nose-scale-vert-{}.target.gz", "nose/nose-width1-{}.target.gz",
    "nose/nose-hump-{}.target.gz", "nose/nose-point-width-{}.target.gz",
    "chin/chin-width-{}.target.gz", "chin/chin-prominent-{}.target.gz", "chin/chin-height-{}.target.gz",
    "cheek/l-cheek-bones-{}.target.gz", "cheek/r-cheek-bones-{}.target.gz",
    "mouth/mouth-scale-horiz-{}.target.gz", "mouth/mouth-lowerlip-volume-{}.target.gz",
    "mouth/mouth-upperlip-volume-{}.target.gz",
    "eyes/l-eye-size-{}.target.gz", "eyes/r-eye-size-{}.target.gz",
    "head/head-square.target.gz", "head/head-oval.target.gz",
    "forehead/forehead-scale-vert-{}.target.gz", "eyebrows/eyebrows-trans-down.target.gz",
    "neck/neck-scale-horiz-{}.target.gz",
]


def shape(spec):
    """spec: child (0..1 share of 'child' vs 'young'), muscle, weight (0..1), height (-1..1), seed, face (0..1)."""
    V, _, _, _ = base()
    V = V.copy()
    ages = {"child": spec.get("child", 0.0), "young": 1 - spec.get("child", 0.0)}
    mus = _tri(spec.get("muscle", 0.5))
    wei = _tri(spec.get("weight", 0.5))
    h = spec.get("height", 0.0)

    def add(rel, wt):
        if abs(wt) < 1e-4:
            return
        p = os.path.join(MPFB, "targets", rel)
        if not os.path.exists(p):
            return
        idx, d = load_target(rel)
        V[idx] += d * wt

    for age, aw in ages.items():
        if aw <= 0:
            continue
        add(f"macrodetails/caucasian-male-{age}.target.gz", aw)
        for m, mw in mus.items():
            for wk, ww in wei.items():
                k = aw * mw * ww
                if k <= 0:
                    continue
                add(f"macrodetails/universal-male-{age}-{m}muscle-{wk}weight.target.gz", k)
                if h:
                    add(f"macrodetails/height/male-{age}-{m}muscle-{wk}weight-{'max' if h > 0 else 'min'}height.target.gz",
                        k * abs(h))
                add(f"macrodetails/proportions/male-{age}-{m}muscle-{wk}weight-idealproportions.target.gz",
                    k * spec.get("ideal", 0.5))
    r = random.Random(spec.get("seed", 1))
    amt = spec.get("face", 0.6)
    for t in FACE_TARGETS:
        v = r.uniform(-1, 1) * amt
        if "{}" in t:
            add(t.format("incr" if v > 0 else "decr"), abs(v))
        elif v > 0:
            add(t, v)
    for rel, wt in spec.get("extra", []):
        add(rel, wt)
    return V


def mh2bl(V, ground):
    """MakeHuman (decimeters, Y up) -> Blender (meters, Z up, facing -Y), feet on z=0."""
    out = np.empty_like(V)
    out[:, 0] = V[:, 0] * 0.1
    out[:, 1] = -V[:, 2] * 0.1
    out[:, 2] = (V[:, 1] - ground) * 0.1
    return out


# ============================================================================ materials

_imgs = {}


def img(path, colorspace="sRGB"):
    key = (path, colorspace)
    if key in _imgs:
        try:
            _imgs[key].name
        except ReferenceError:
            del _imgs[key]
    if key not in _imgs:
        im = bpy.data.images.load(path, check_existing=True)
        im.colorspace_settings.name = colorspace
        _imgs[key] = im
    return _imgs[key]


def node_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    return m, nt, bsdf


def tex_node(nt, path, cs="sRGB", interp="Linear"):
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img(path, cs)
    t.interpolation = interp
    return t


def lin3(rgb):
    """sRGB-ish colour (as picked by eye) -> linear values for shader inputs."""
    return tuple(max(0.0, c) ** 2.2 for c in rgb)


def tint(nt, col_socket, tint_rgb, desat=1.0, gain=1.0):
    """Desaturate a texture and multiply by a tint colour (to recolour clothes)."""
    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    hsv.inputs["Saturation"].default_value = 1 - desat
    hsv.inputs["Value"].default_value = gain
    nt.links.new(col_socket, hsv.inputs["Color"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 1.0
    nt.links.new(hsv.outputs[0], mix.inputs[6])
    mix.inputs[7].default_value = tuple(c * 4.0 for c in lin3(tint_rgb)) + (1.0,)
    return mix.outputs[2]


def skin_material(name, skin_dir, tone=(1.0, 1.0, 1.0)):
    kv = parse_kv([os.path.join(skin_dir, f) for f in os.listdir(skin_dir) if f.endswith(".mhmat")][0])
    m, nt, b = node_mat(name)
    t = tex_node(nt, os.path.join(skin_dir, kv["diffuseTexture"]))
    col = tint(nt, t.outputs[0], tone, desat=0.0)
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.52
    b.inputs["Specular IOR Level"].default_value = 0.35
    b.inputs["Subsurface Weight"].default_value = 0.03
    b.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.2)
    b.inputs["Subsurface Scale"].default_value = 0.004
    # pores / micro bump
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 900.0
    nz.inputs["Detail"].default_value = 4.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.06
    bump.inputs["Distance"].default_value = 0.0005
    nt.links.new(nz.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs[0], b.inputs["Normal"])
    return m


def proxy_material(name, proxy_dir, mhmat, tint_rgb=None, desat=1.0, gain=1.0, rough=0.8, alpha=False, sheen=0.0):
    kv = parse_kv(os.path.join(proxy_dir, mhmat)) if mhmat and os.path.exists(os.path.join(proxy_dir, mhmat)) else {}
    m, nt, b = node_mat(name)
    dt = kv.get("diffuseTexture")
    col = None
    if dt and os.path.exists(os.path.join(proxy_dir, dt)):
        t = tex_node(nt, os.path.join(proxy_dir, dt))
        col = t.outputs[0]
        if tint_rgb is not None:
            col = tint(nt, col, tint_rgb, desat, gain)
        nt.links.new(col, b.inputs["Base Color"])
        if alpha:
            nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
    elif tint_rgb is not None:
        b.inputs["Base Color"].default_value = tuple(tint_rgb) + (1,)
    nm = kv.get("normalmapTexture")
    if nm and os.path.exists(os.path.join(proxy_dir, nm)):
        tn = tex_node(nt, os.path.join(proxy_dir, nm), "Non-Color")
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = 0.8
        nt.links.new(tn.outputs[0], nmap.inputs["Color"])
        nt.links.new(nmap.outputs[0], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = rough
    if sheen:
        b.inputs["Sheen Weight"].default_value = sheen
    if alpha:
        m.blend_method = "HASHED" if hasattr(m, "blend_method") else None
    return m


def plain_material(name, rgb, rough=0.7, spec=0.4, sheen=0.0, coat=0.0, noise=0.0, noise_scale=40.0, bump=0.0):
    rgb = lin3(rgb)
    m, nt, b = node_mat(name)
    b.inputs["Base Color"].default_value = tuple(rgb) + (1,)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = spec
    if sheen:
        b.inputs["Sheen Weight"].default_value = sheen
        b.inputs["Sheen Tint"].default_value = tuple(min(1.0, c * 1.6) for c in rgb) + (1,)
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    if noise or bump:
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = noise_scale
        nz.inputs["Detail"].default_value = 8.0
        if noise:
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MULTIPLY"
            mix.inputs[0].default_value = noise
            mix.inputs[6].default_value = tuple(rgb) + (1,)
            ramp = nt.nodes.new("ShaderNodeValToRGB")
            ramp.color_ramp.elements[0].color = (0.55, 0.55, 0.55, 1)
            ramp.color_ramp.elements[1].color = (1.3, 1.3, 1.3, 1)
            nt.links.new(nz.outputs[0], ramp.inputs[0])
            nt.links.new(ramp.outputs[0], mix.inputs[7])
            nt.links.new(mix.outputs[2], b.inputs["Base Color"])
        if bump:
            bp = nt.nodes.new("ShaderNodeBump")
            bp.inputs["Strength"].default_value = bump
            nt.links.new(nz.outputs[0], bp.inputs["Height"])
            nt.links.new(bp.outputs[0], b.inputs["Normal"])
    return m


# ============================================================================ mesh helpers

def make_mesh(name, verts, faces, uv_faces=None, uvs=None, mats=None, mat_idx=None, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    if uv_faces is not None and uvs is not None and len(uvs):
        layer = me.uv_layers.new(name="UV")
        flat = []
        for tf in uv_faces:
            for t in tf:
                flat.extend(uvs[t] if t >= 0 else (0.0, 0.0))
        layer.data.foreach_set("uv", flat)
    for m in mats or []:
        me.materials.append(m)
    if mat_idx is not None:
        me.polygons.foreach_set("material_index", list(mat_idx))
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def fit_proxy(clo, V):
    refs, w, off = clo["refs"], clo["w"], clo["off"]
    P = (V[refs] * w[..., None]).sum(axis=1)
    sc = np.ones(3)
    for ax, i in (("x", 0), ("y", 1), ("z", 2)):
        if ax in clo["scales"]:
            a, b, dist = clo["scales"][ax]
            sc[i] = abs(V[a, i] - V[b, i]) / dist
    return P + off * sc


# ============================================================================ rig

RIG = os.path.join(MPFB, "rigs", "standard", "rig.game_engine.json")
WEIGHTS = os.path.join(MPFB, "rigs", "standard", "weights.game_engine.json")


def joint_pos(spec, V, groups):
    st = spec.get("strategy")
    if st == "CUBE" and spec.get("cube_name") in groups:
        idx = list(groups[spec["cube_name"]])
        return V[idx].mean(axis=0)
    if st == "MEAN":
        return V[spec["vertex_indices"]].mean(axis=0)
    if st == "VERTEX":
        return V[spec["vertex_index"]]
    return None


def build_armature(name, Vmh, Vbl, ground):
    _, _, _, groups = base()
    rig = json.load(open(RIG))
    arm_data = bpy.data.armatures.new(name + "_rig")
    arm = bpy.data.objects.new(name + "_rig", arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")

    def tobl(p):
        return Vector((p[0] * 0.1, -p[2] * 0.1, (p[1] - ground) * 0.1))

    ebs = {}
    for bname, b in rig.items():
        eb = arm_data.edit_bones.new(bname)
        h = joint_pos(b["head"], Vmh, groups)
        t = joint_pos(b["tail"], Vmh, groups)
        eb.head = tobl(h) if h is not None else Vector(b["head"]["default_position"]) + Vector((0, 0, 0))
        eb.tail = tobl(t) if t is not None else Vector(b["tail"]["default_position"])
        if (eb.tail - eb.head).length < 1e-4:
            eb.tail = eb.head + Vector((0, 0, 0.05))
        eb.roll = b.get("roll", 0.0)
        ebs[bname] = eb
    for bname, b in rig.items():
        if b.get("parent"):
            ebs[bname].parent = ebs[b["parent"]]
            ebs[bname].use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
    return arm


def weight_matrix(nverts):
    wj = json.load(open(WEIGHTS))["weights"]
    bones = list(wj)
    W = np.zeros((nverts, len(bones)), np.float32)
    for j, bn in enumerate(bones):
        for vi, wt in wj[bn]:
            if vi < nverts:
                W[vi, j] = wt
    s = W.sum(axis=1, keepdims=True)
    s[s == 0] = 1
    return bones, W / s


def apply_weights(ob, bones, W, thresh=0.01):
    for j, bn in enumerate(bones):
        idx = np.nonzero(W[:, j] > thresh)[0]
        if not len(idx):
            continue
        vg = ob.vertex_groups.new(name=bn)
        for i in idx:
            vg.add([int(i)], float(W[i, j]), "REPLACE")


def bind(ob, arm):
    ob.parent = arm
    mod = ob.modifiers.new("arm", "ARMATURE")
    mod.object = arm


# ============================================================================ the human

class Human:
    """A dressed, rigged human. Pose controls via pose(bone, f, rot_world_xyz)."""

    def __init__(self, name, spec, outfit):
        self.name = name
        self.spec = spec
        V0, UV, faces, groups = base()
        Vmh = shape(spec)
        ground = float(Vmh[list(groups.get("joint-ground", [0]))].mean(axis=0)[1]) if "joint-ground" in groups else \
            float(Vmh[:, 1].min())
        self.ground = ground
        self.Vmh = Vmh
        Vbl = mh2bl(Vmh, ground)
        self.Vbl = Vbl
        self.arm = build_armature(name, Vmh, Vbl, ground)
        bones, W = weight_matrix(len(V0))
        self.bones, self.W = bones, W
        # body: all verts (indices preserved), body faces only
        bf = [(vi, ti) for vi, ti, g in faces if g == "body"]
        skin_dir = os.path.join(ASSETS, "skins", spec.get("skin", "young_caucasian_male"))
        self.skin_mat = skin_material(name + "_skin", skin_dir, spec.get("tone", (1, 1, 1)))
        body = make_mesh(name + "_body", Vbl, [f for f, _ in bf], [t for _, t in bf], UV, [self.skin_mat])
        apply_weights(body, bones, W)
        bind(body, self.arm)
        self.body = body
        self._shape_keys()
        self.parts = [body]
        self.hidden_faces = None
        # eyes, brows, lashes, hair, clothes
        eye_col = spec.get("eyes", "brown")
        self.add_proxy("eyes/high-poly/high-poly.mhclo", mat=self._eye_material(eye_col))
        self.add_proxy(f"eyebrows/{spec.get('brows', 'eyebrow001')}/{spec.get('brows', 'eyebrow001')}.mhclo",
                       alpha=True, tint_rgb=spec.get("hair_rgb"), desat=0.0)
        self.add_proxy("eyelashes/eyelashes01/eyelashes01.mhclo", alpha=True)
        if spec.get("hair"):
            hp = spec["hair"]
            self.hair = self.add_proxy(f"hair/{hp}/{hp}.mhclo", alpha=True, tint_rgb=spec.get("hair_rgb"), desat=0.6,
                                       rough=0.55)
        else:
            self.hair = None
        for item in outfit:
            item(self)

    # ---------------------------------------------------------------- body extras
    def _eye_material(self, col):
        p = os.path.join(ASSETS, "eyes", "materials", f"{col}_eye.png")
        if not os.path.exists(p):
            p = os.path.join(ASSETS, "eyes", "materials", "brown_eye.png") if os.path.exists(
                os.path.join(ASSETS, "eyes", "materials", "brown_eye.png")) else [
                os.path.join(ASSETS, "eyes", "materials", f) for f in os.listdir(os.path.join(ASSETS, "eyes", "materials"))
                if f.endswith(".png")][0]
        m, nt, b = node_mat(self.name + "_eye")
        t = tex_node(nt, p)
        nt.links.new(t.outputs[0], b.inputs["Base Color"])
        b.inputs["Roughness"].default_value = 0.05
        b.inputs["Specular IOR Level"].default_value = 0.8
        b.inputs["Coat Weight"].default_value = 1.0
        return m

    def _shape_keys(self):
        b = self.body
        b.shape_key_add(name="Basis")
        self.keys = {}
        for nm in ("mouth-open", "mouth-pursing", "mouth-retraction", "mouth-corner-puller", "eye-left-closure",
                   "eye-right-closure", "eyebrows-left-down", "eyebrows-right-down", "eyebrows-left-inner-up",
                   "eyebrows-right-inner-up", "mouth-depression"):
            rel = f"expression/units/caucasian/{nm}.target.gz"
            if not os.path.exists(os.path.join(MPFB, "targets", rel)):
                continue
            idx, d = load_target(rel)
            sk = b.shape_key_add(name=nm, from_mix=False)
            co = np.empty(len(b.data.vertices) * 3, np.float32)
            sk.data.foreach_get("co", co)
            co = co.reshape(-1, 3)
            dd = np.zeros_like(co)
            dd[idx, 0] = d[:, 0] * 0.1
            dd[idx, 1] = -d[:, 2] * 0.1
            dd[idx, 2] = d[:, 1] * 0.1
            co += dd
            sk.data.foreach_set("co", co.ravel())
            sk.value = 0.0
            self.keys[nm] = sk

    def add_proxy(self, rel, mat=None, tint_rgb=None, desat=1.0, gain=1.0, rough=0.8, alpha=False, split=None,
                  mats_split=None, offset=0.0):
        path = os.path.join(ASSETS, rel)
        clo = load_mhclo(path)
        P = fit_proxy(clo, self.Vmh)
        Pbl = mh2bl(P, self.ground)
        objf = os.path.join(clo["dir"], clo["hdr"].get("obj_file", os.path.basename(path).replace(".mhclo", ".obj")))
        _, uvs, faces, _ = load_obj(objf)
        if offset:
            # push outwards from the body a little (layering)
            c = np.array([0, 0, 1.0])
            ctr = Pbl.mean(axis=0)
            dirs = Pbl - ctr
            dirs[:, 2] *= 0.2
            n = np.linalg.norm(dirs, axis=1, keepdims=True) + 1e-6
            Pbl = Pbl + dirs / n * offset
        if mat is None:
            mat = proxy_material(f"{self.name}_{os.path.basename(path)}", clo["dir"], clo["hdr"].get("material"),
                                 tint_rgb=tint_rgb, desat=desat, gain=gain, rough=rough, alpha=alpha)
        mats = [mat]
        mat_idx = None
        if split is not None:
            # split faces between materials by which bones dominate their reference vertices
            Wp = self.proxy_weights(clo)
            bset = [self.bones.index(b) for b in split if b in self.bones]
            leg = Wp[:, bset].sum(axis=1) > 0.5
            mat_idx = [1 if all(leg[v] for v in f) else 0 for f, _, _ in faces]
            mats = [mat, mats_split]
        ob = make_mesh(f"{self.name}_{os.path.basename(path)[:-6]}", Pbl, [f for f, _, _ in faces],
                       [t for _, t, _ in faces], uvs, mats, mat_idx)
        Wp = self.proxy_weights(clo)
        apply_weights(ob, self.bones, Wp)
        bind(ob, self.arm)
        self.parts.append(ob)
        return ob

    def proxy_weights(self, clo):
        refs, w = clo["refs"], clo["w"]
        Wp = (self.W[refs] * w[..., None]).sum(axis=1)
        s = Wp.sum(axis=1, keepdims=True)
        s[s == 0] = 1
        return Wp / s

    # ---------------------------------------------------------------- anchors
    def head_top(self):
        _, _, _, groups = base()
        head_idx = np.nonzero(self.W[:, self.bones.index("head")] > 0.9)[0]
        P = self.Vbl[head_idx]
        top = P[P[:, 2].argmax()]
        ctr = P.mean(axis=0)
        return Vector(top), Vector(ctr), P

    def attach_to_bone(self, ob, bone):
        """Rigidly skin an accessory (built in rest-pose world coords) to one bone."""
        vg = ob.vertex_groups.new(name=bone)
        vg.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")
        mod = ob.modifiers.new("arm", "ARMATURE")
        mod.object = self.arm
        ob.parent = self.arm
        self.parts.append(ob)

    # ---------------------------------------------------------------- posing
    def rot(self, bone, f, xyz_deg, interp=None):
        """Rotation of a bone expressed in armature rest axes (X right, Y back, Z up), degrees."""
        pb = self.arm.pose.bones[bone]
        B = pb.bone.matrix_local.to_3x3()
        R = (Matrix.Rotation(math.radians(xyz_deg[2]), 3, "Z") @ Matrix.Rotation(math.radians(xyz_deg[1]), 3, "Y") @
             Matrix.Rotation(math.radians(xyz_deg[0]), 3, "X"))
        L = B.inverted() @ R @ B
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = L.to_quaternion()
        pb.keyframe_insert("rotation_quaternion", frame=f)

    def place(self, f, loc, yaw_deg=0.0):
        self.arm.location = loc
        self.arm.rotation_euler = (0, 0, math.radians(yaw_deg))
        self.arm.keyframe_insert("location", frame=f)
        self.arm.keyframe_insert("rotation_euler", frame=f)

    def key(self, name, f, v):
        if name in self.keys:
            self.keys[name].value = v
            self.keys[name].keyframe_insert("value", frame=f)


FINGERS = ("index", "middle", "ring", "pinky")


def relax(h, f, arm_down=38, elbow=-4, curl=(22, 30, 20), thumb=6, spread=1.0):
    """Natural standing pose from MakeHuman's A-pose: arms down, slight elbow bend, fingers loosely closed."""
    close = {"index": 5, "middle": 0, "ring": -5, "pinky": -10}
    for side, s in (("l", 1), ("r", -1)):
        h.rot(f"upperarm_{side}", f, (4, arm_down * s, 0))
        h.rot(f"lowerarm_{side}", f, (-elbow, 0, 0))
        h.rot(f"hand_{side}", f, (0, 0, -6 * s))
        for fi, fn in enumerate(FINGERS):
            for k in (1, 2, 3):
                c = curl[k - 1] * (1 + 0.15 * fi) * spread
                z = close[fn] * s if k == 1 else 0
                h.rot(f"{fn}_0{k}_{side}", f, (0, c * s, z))
        h.rot(f"thumb_01_{side}", f, (thumb, 0, -thumb * s))
        h.rot(f"thumb_02_{side}", f, (0, 12 * s, 0))

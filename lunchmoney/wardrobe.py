"""Outfits for LUNCH MONEY characters: CC0 MakeHuman garments recoloured + our own procedural headwear,
collars and the long coat skirt."""
import math

import bpy
import numpy as np
from mathutils import Vector

import human as H

# uv rules telling which faces of a garment are the trousers (u, v of the face centre)
LEG_UV = {
    "male_casualsuit05": lambda u, v: v < 0.42 and u < 0.62,
    "male_casualsuit02": lambda u, v: v < 0.50 and u < 0.86,
    "male_casualsuit01": lambda u, v: v < 0.50,
    "male_casualsuit03": lambda u, v: v < 0.50,
    "male_casualsuit04": lambda u, v: v < 0.50 and u < 0.86,
    "male_casualsuit06": lambda u, v: v < 0.50,
}


def garment(suit, top=None, legs=None, top_rough=0.85, legs_rough=0.9, top_coat=0.0, top_desat=1.0, legs_desat=1.0,
            top_gain=1.0, legs_gain=1.0):
    """Add a casual suit; top / legs = tint colours (None keeps the original texture)."""

    def f(h):
        rel = f"clothes/{suit}/{suit}.mhclo"
        clo = H.load_mhclo(f"{H.ASSETS}/{rel}")
        mt = H.proxy_material(f"{h.name}_{suit}_top", clo["dir"], clo["hdr"].get("material"), tint_rgb=top,
                              desat=top_desat if top else 0, gain=top_gain, rough=top_rough)
        if top_coat:
            mt.node_tree.nodes["Principled BSDF"].inputs["Coat Weight"].default_value = top_coat
        ml = H.proxy_material(f"{h.name}_{suit}_legs", clo["dir"], clo["hdr"].get("material"), tint_rgb=legs,
                              desat=legs_desat if legs else 0, gain=legs_gain, rough=legs_rough)
        ob = h.add_proxy(rel, mat=mt)
        # assign legs material by uv region
        rule = LEG_UV.get(suit)
        if rule:
            me = ob.data
            me.materials.append(ml)
            uv = me.uv_layers[0].data
            idx = []
            for p in me.polygons:
                us = [uv[li].uv for li in p.loop_indices]
                u = sum(x[0] for x in us) / len(us)
                v = sum(x[1] for x in us) / len(us)
                idx.append(1 if rule(u, v) else 0)
            me.polygons.foreach_set("material_index", idx)
        h.top = ob
        return ob

    return f


def shoes(kind="shoes01", rgb=None):
    def f(h):
        h.add_proxy(f"clothes/{kind}/{kind}.mhclo", tint_rgb=rgb, desat=1.0 if rgb else 0, rough=0.5)
    return f


# ---------------------------------------------------------------------------- procedural headwear

def _lathe(name, profile, segs=48, scale_xy=(1.0, 1.0), radial_mod=None):
    """profile: list of (radius, z) from bottom rim to top. Returns verts, faces."""
    verts, faces = [], []
    for j, (r, z) in enumerate(profile):
        for i in range(segs):
            a = 2 * math.pi * i / segs
            rr = r * (radial_mod(a, j / max(1, len(profile) - 1)) if radial_mod else 1.0)
            verts.append((math.sin(a) * rr * scale_xy[0], -math.cos(a) * rr * scale_xy[1], z))
    for j in range(len(profile) - 1):
        for i in range(segs):
            a = j * segs + i
            b = j * segs + (i + 1) % segs
            faces.append((a, b, b + segs, a + segs))
    top = len(verts)
    verts.append((0, 0, profile[-1][1]))
    last = (len(profile) - 1) * segs
    for i in range(segs):
        faces.append((last + i, last + (i + 1) % segs, top))
    return verts, faces


def _head_frame(h):
    """Top of the head (or of the hair, squashed under a hat), centre and radii."""
    top, ctr, P = h.head_top()
    rx = (P[:, 0].max() - P[:, 0].min()) / 2
    ry = (P[:, 1].max() - P[:, 1].min()) / 2
    if getattr(h, "hair", None) is not None:
        hv = np.array([v.co[:] for v in h.hair.data.vertices])
        hz = hv[:, 2].max()
        top = Vector((top.x, top.y, top.z + (hz - top.z) * 0.35))
        rx = max(rx, (hv[:, 0].max() - hv[:, 0].min()) / 2 * 0.92)
        ry = max(ry, (hv[:, 1].max() - hv[:, 1].min()) / 2 * 0.92)
    return top, ctr, rx, ry


def _obj(name, verts, faces, mat, smooth=True, solid=0.0, subsurf=1):
    ob = H.make_mesh(name, verts, faces, mats=[mat], smooth=smooth)
    if solid:
        m = ob.modifiers.new("solid", "SOLIDIFY")
        m.thickness = solid
    if subsurf:
        m = ob.modifiers.new("sub", "SUBSURF")
        m.levels = subsurf
        m.render_levels = subsurf
    return ob


def wool(name, rgb, scale=320.0):
    return H.plain_material(name, rgb, rough=0.92, spec=0.2, sheen=0.2, noise=0.35, noise_scale=scale, bump=0.25)


def fur(name, rgb):
    m, nt, b = H.node_mat(name)
    b.inputs["Roughness"].default_value = 0.85
    b.inputs["Sheen Weight"].default_value = 0.35
    b.inputs["Sheen Roughness"].default_value = 0.6
    b.inputs["Sheen Tint"].default_value = tuple(min(1.0, c * 1.8) for c in rgb) + (1,)
    b.inputs["Specular IOR Level"].default_value = 0.15
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 260.0
    nz.inputs["Detail"].default_value = 12.0
    nz.inputs["Distortion"].default_value = 2.5
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    lr = H.lin3(rgb)
    ramp.color_ramp.elements[0].color = tuple(c * 0.4 for c in lr) + (1,)
    ramp.color_ramp.elements[1].color = tuple(min(1, c * 1.7) for c in lr) + (1,)
    nt.links.new(nz.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.9
    bp.inputs["Distance"].default_value = 0.004
    nt.links.new(nz.outputs[0], bp.inputs["Height"])
    nt.links.new(bp.outputs[0], b.inputs["Normal"])
    return m


def cap8(rgb=(0.1, 0.095, 0.09)):
    """90s eight-panel cap: full crown overhanging a short stiff visor, flat-ish top, button."""

    def f(h):
        top, ctr, rx, ry = _head_frame(h)
        base_z = top.z - 0.085
        R = max(rx, ry) * 1.04
        # (radius factor, height, forward shift) from the headband up
        prof = [(1.0, 0.0, 0.0), (1.1, 0.02, 0.006), (1.22, 0.045, 0.016), (1.26, 0.062, 0.024),
                (1.18, 0.075, 0.026), (0.95, 0.086, 0.022), (0.55, 0.093, 0.016), (0.12, 0.096, 0.012)]
        segs = 72
        verts, faces = [], []
        for j, (rf, z, fwd) in enumerate(prof):
            for i in range(segs):
                a = 2 * math.pi * i / segs
                seam = 1.0 - 0.025 * (0.5 + 0.5 * math.cos(8 * a)) * (1 if 0 < j < len(prof) - 1 else 0)
                front = max(0.0, math.cos(a))  # a=0 is the front (-Y)
                rr = R * rf * seam * (1 + 0.06 * front * min(1, j / 3))
                verts.append((ctr.x + math.sin(a) * rr, ctr.y + 0.01 - math.cos(a) * rr * 1.07 - fwd * front * 1.6,
                              base_z + z))
        for j in range(len(prof) - 1):
            for i in range(segs):
                a = j * segs + i
                b = j * segs + (i + 1) % segs
                faces.append((a, b, b + segs, a + segs))
        topi = len(verts)
        verts.append((ctr.x, ctr.y + 0.01 - 0.02, base_z + 0.097))
        last = (len(prof) - 1) * segs
        for i in range(segs):
            faces.append((last + i, last + (i + 1) % segs, topi))
        mat = wool(h.name + "_cap", rgb, 420.0)
        crown = _obj(h.name + "_cap", verts, faces, mat, solid=0.004)
        # visor: stiff, slightly curved down, tucked under the overhang
        vv, ff = [], []
        n = 28
        for i in range(n + 1):
            a = -math.pi * 0.36 + math.pi * 0.72 * i / n
            for k, (rr, dz) in enumerate(((R * 0.99, 0.004), (R * 1.0 + 0.05, -0.014))):
                bend = -0.008 * (abs(a) / (math.pi * 0.36)) ** 2 if k else 0.0
                vv.append((ctr.x + math.sin(a) * rr, ctr.y + 0.01 - math.cos(a) * rr * 1.07, base_z + dz + bend))
        for i in range(n):
            a = i * 2
            ff.append((a, a + 2, a + 3, a + 1))
        visor = _obj(h.name + "_visor", vv, ff, wool(h.name + "_visorm", tuple(c * 0.8 for c in rgb), 500.0),
                     solid=0.006, subsurf=1)
        bv, bf = _lathe("b", [(0.011, 0.0), (0.009, 0.005), (0.003, 0.008)], 16)
        btn_ob = _obj(h.name + "_btn", [(x + ctr.x, y + ctr.y - 0.01, z + base_z + 0.094) for x, y, z in bv], bf, mat,
                      subsurf=0)
        for ob in (crown, visor, btn_ob):
            h.attach_to_bone(ob, "head")
    return f


def fur_hat(rgb=(0.11, 0.075, 0.05)):
    """Brown fur hat (not an ushanka): tall rounded 'pirozhok'."""

    def f(h):
        top, ctr, rx, ry = _head_frame(h)
        base_z = top.z - 0.09
        R = max(rx, ry) * 1.1
        prof = [(R * 1.0, 0.0), (R * 1.08, 0.03), (R * 1.13, 0.08), (R * 1.15, 0.12), (R * 1.08, 0.15),
                (R * 0.75, 0.162), (R * 0.2, 0.166)]

        def mod(a, t):
            return 1.0 + 0.02 * math.sin(a * 13 + t * 5) + 0.015 * math.sin(a * 29)

        v, fcs = _lathe("hat", prof, 72, (1.0, 1.12), mod)
        v = [(x + ctr.x, y + ctr.y + 0.01, z + base_z) for x, y, z in v]
        ob = _obj(h.name + "_furhat", v, fcs, fur(h.name + "_fur", rgb), solid=0.006)
        h.attach_to_bone(ob, "head")
    return f


def beanie(rgb=(0.035, 0.035, 0.04)):
    def f(h):
        top, ctr, rx, ry = _head_frame(h)
        base_z = top.z - 0.128
        R = max(rx, ry) * 1.02
        prof = [(R * 1.02, 0.0), (R * 1.07, 0.02), (R * 1.07, 0.045), (R * 1.03, 0.05), (R * 1.03, 0.09),
                (R * 0.85, 0.125), (R * 0.45, 0.143), (R * 0.1, 0.147)]
        v, fcs = _lathe("beanie", prof, 64, (1.0, 1.08))
        v = [(x + ctr.x, y + ctr.y + 0.008, z + base_z) for x, y, z in v]
        m, nt, b = H.node_mat(h.name + "_knit")
        b.inputs["Base Color"].default_value = H.lin3(rgb) + (1,)
        b.inputs["Roughness"].default_value = 0.95
        b.inputs["Sheen Weight"].default_value = 0.2
        b.inputs["Sheen Tint"].default_value = (0.3, 0.3, 0.32, 1)
        wv = nt.nodes.new("ShaderNodeTexWave")
        wv.wave_type = "BANDS"
        wv.bands_direction = "X"
        wv.inputs["Scale"].default_value = 60.0
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = 0.6
        nt.links.new(wv.outputs[1], bp.inputs["Height"])
        nt.links.new(bp.outputs[0], b.inputs["Normal"])
        ob = _obj(h.name + "_beanie", v, fcs, m, solid=0.005)
        h.attach_to_bone(ob, "head")
    return f


def _neck_frame(h):
    arm = h.arm
    nb = arm.data.bones["neck_01"]
    head = arm.data.bones["head"]
    p0 = Vector(nb.head_local)
    p1 = Vector(head.head_local)
    neck_idx = np.nonzero(h.W[:, h.bones.index("neck_01")] > 0.6)[0]
    P = h.Vbl[neck_idx]
    r = float(np.median(np.linalg.norm((P - np.array(p0))[:, :2], axis=1)))
    return p0, p1, r


def ring(name, center, rx, ry, minor, mat, segs=48, msegs=12, z_squash=0.7):
    verts, faces = [], []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        for j in range(msegs):
            b = 2 * math.pi * j / msegs
            rr = 1 + minor * math.cos(b) / max(rx, ry)
            verts.append((center.x + math.sin(a) * rx * rr, center.y - math.cos(a) * ry * rr,
                          center.z + minor * math.sin(b) * z_squash))
    for i in range(segs):
        for j in range(msegs):
            a = i * msegs + j
            b = ((i + 1) % segs) * msegs + j
            c = ((i + 1) % segs) * msegs + (j + 1) % msegs
            d = i * msegs + (j + 1) % msegs
            faces.append((a, b, c, d))
    return _obj(name, verts, faces, mat, subsurf=1)


def fur_collar(rgb=(0.24, 0.16, 0.1)):
    def f(h):
        p0, p1, r = _neck_frame(h)
        c = Vector((p0.x, p0.y + 0.015, p0.z - 0.055))
        ob = ring(h.name + "_collar", c, r + 0.085, r + 0.075, 0.045, fur(h.name + "_collarfur", rgb), z_squash=0.55)
        h.attach_to_bone(ob, "spine_03")
    return f


def turtleneck(rgb=(0.03, 0.03, 0.035)):
    def f(h):
        p0, p1, r = _neck_frame(h)
        n = 40
        verts, faces = [], []
        zs = [p0.z - 0.03, p0.z + 0.02, p0.z + 0.055, p0.z + 0.075]
        rs = [r + 0.035, r + 0.018, r + 0.014, r + 0.016]
        for z, rr in zip(zs, rs):
            for i in range(n):
                a = 2 * math.pi * i / n
                verts.append((p0.x + math.sin(a) * rr, p0.y + 0.008 - math.cos(a) * rr * 1.05, z))
        for j in range(len(zs) - 1):
            for i in range(n):
                a = j * n + i
                b = j * n + (i + 1) % n
                faces.append((a, b, b + n, a + n))
        m = wool(h.name + "_tneck", rgb, 500.0)
        ob = _obj(h.name + "_tneck", verts, faces, m, solid=0.006)
        h.attach_to_bone(ob, "neck_01")
    return f


def sweater_collar(rgb=(0.32, 0.3, 0.26)):
    def f(h):
        p0, p1, r = _neck_frame(h)
        c = Vector((p0.x, p0.y - 0.005, p0.z - 0.035))
        ob = ring(h.name + "_swcollar", c, r + 0.03, r + 0.035, 0.018, wool(h.name + "_sweater", rgb, 600.0),
                  z_squash=1.2)
        h.attach_to_bone(ob, "spine_03")
    return f


def coat_skirt(rgb=(0.025, 0.022, 0.02), length=0.42):
    """Lower part of a long leather coat: from the jacket hem down to above the knees, open at the front,
    skinned to pelvis and thighs so it follows the walk."""

    def f(h):
        arm = h.arm.data
        hip = Vector(arm.bones["pelvis"].head_local)
        knee_l = Vector(arm.bones["calf_l"].head_local)
        z0 = hip.z + 0.03
        z1 = z0 - length
        # body extents at hip height
        legs = h.W[:, [h.bones.index(b) for b in ("pelvis", "thigh_l", "thigh_r", "spine_01")]].sum(axis=1) > 0.5
        band = (h.Vbl[:, 2] > z0 - 0.06) & (h.Vbl[:, 2] < z0 + 0.02) & legs
        P = h.Vbl[band]
        cx, cy = float(P[:, 0].mean()), float(P[:, 1].mean())
        rx = float((P[:, 0].max() - P[:, 0].min()) / 2) + 0.035
        ry = float((P[:, 1].max() - P[:, 1].min()) / 2) + 0.035
        rows, segs = 10, 56
        gap = math.radians(14)
        verts, faces = [], []
        for j in range(rows + 1):
            t = j / rows
            z = z0 + (z1 - z0) * t
            flare = 1 + 0.09 * t
            for i in range(segs + 1):
                a = gap + (2 * math.pi - 2 * gap) * i / segs
                wob = 1 + (0.012 + 0.02 * t) * math.sin(a * 7 + t * 2.5)
                verts.append((cx + math.sin(a) * rx * flare * wob, cy - math.cos(a) * ry * flare * wob, z))
        for j in range(rows):
            for i in range(segs):
                a = j * (segs + 1) + i
                faces.append((a, a + 1, a + segs + 2, a + segs + 1))
        m = H.plain_material(h.name + "_leather", rgb, rough=0.55, spec=0.4, coat=0.08, noise=0.25, noise_scale=90,
                             bump=0.15)
        ob = _obj(h.name + "_coatskirt", verts, faces, m, solid=0.008, subsurf=1)
        # weights
        vg = {n: ob.vertex_groups.new(name=n) for n in ("pelvis", "thigh_l", "thigh_r")}
        for k, v in enumerate(ob.data.vertices):
            t = (z0 - v.co.z) / (z0 - z1)
            side = (v.co.x - cx) / rx
            wl = max(0.0, min(1.0, 0.5 + side)) * t
            wr = max(0.0, min(1.0, 0.5 - side)) * t
            vg["pelvis"].add([k], 1 - t * 0.85, "REPLACE")
            vg["thigh_l"].add([k], wl * 0.85, "REPLACE")
            vg["thigh_r"].add([k], wr * 0.85, "REPLACE")
        H.bind(ob, h.arm)
        h.parts.append(ob)
    return f



# ---------------------------------------------------------------------------- the cast

CAST = {
    "bob": dict(spec={"muscle": 0.7, "weight": 0.78, "height": 0.6, "seed": 11, "hair": "short04",
                      "hair_rgb": (0.04, 0.03, 0.022), "brows": "eyebrow007", "eyes": "brown",
                      "skin": "young_caucasian_male2", "face": 0.7},
                outfit=[garment("male_casualsuit05", top=(0.05, 0.045, 0.042), legs=(0.06, 0.06, 0.065), top_rough=0.5,
                                top_coat=0.12, top_gain=1.0),
                        coat_skirt(), sweater_collar((0.12, 0.11, 0.1)), fur_hat(), shoes("shoes01", (0.05, 0.04, 0.035))]),
    "john": dict(spec={"muscle": 0.55, "weight": 0.5, "height": 0.35, "seed": 23, "hair": "short02",
                       "hair_rgb": (0.08, 0.06, 0.05), "brows": "eyebrow010", "eyes": "grey",
                       "skin": "young_caucasian_male", "face": 0.8},
                 outfit=[garment("male_casualsuit05", top=(0.07, 0.08, 0.13), legs=(0.08, 0.08, 0.1), top_rough=0.75),
                         fur_collar(), beanie(), shoes("shoes05", (0.06, 0.06, 0.06))]),
    "karim": dict(spec={"muscle": 0.5, "weight": 0.45, "height": 0.1, "seed": 37, "hair": "short02",
                        "hair_rgb": (0.07, 0.05, 0.04), "brows": "eyebrow003", "eyes": "brown",
                        "skin": "young_caucasian_male2", "face": 0.7},
                  outfit=[garment("male_casualsuit05", top=(0.16, 0.16, 0.12), legs=(0.12, 0.13, 0.17), top_rough=0.8),
                          cap8((0.14, 0.12, 0.1)), shoes("shoes02")]),
    "artem": dict(spec={"muscle": 0.45, "weight": 0.35, "height": 0.0, "seed": 41, "hair": "short02",
                        "hair_rgb": (0.15, 0.1, 0.06), "brows": "eyebrow005", "eyes": "blue",
                        "skin": "young_caucasian_male", "face": 0.75},
                  outfit=[garment("male_casualsuit02", top=(0.035, 0.035, 0.04), legs=(0.04, 0.04, 0.045),
                                  top_rough=0.9, top_gain=0.8, legs_gain=0.9),
                          turtleneck(), cap8((0.05, 0.05, 0.055)), shoes("shoes05", (0.05, 0.05, 0.05))]),
    "maxim": dict(spec={"muscle": 0.4, "weight": 0.4, "height": -0.1, "seed": 53, "hair": "short03",
                        "hair_rgb": (0.32, 0.22, 0.12), "brows": "eyebrow002", "eyes": "blue",
                        "skin": "young_caucasian_male", "face": 0.6, "child": 0.15},
                  outfit=[garment("male_casualsuit01"), shoes("shoes02")]),
}


def extra(name, seed, child=0.6):
    import random
    r = random.Random(seed)
    suit = r.choice(["male_casualsuit01", "male_casualsuit02", "male_casualsuit03", "male_casualsuit04",
                     "male_casualsuit06"])
    hair = r.choice(["short01", "short02", "short03", "short04"])
    hr = r.choice([(0.08, 0.06, 0.04), (0.25, 0.17, 0.09), (0.42, 0.3, 0.16), (0.12, 0.09, 0.06)])
    spec = {"muscle": r.uniform(0.3, 0.5), "weight": r.uniform(0.3, 0.6), "height": r.uniform(-0.6, 0.0),
            "seed": seed, "hair": hair, "hair_rgb": hr, "brows": f"eyebrow00{r.randint(1, 9)}",
            "eyes": r.choice(["brown", "blue", "grey"]),
            "skin": r.choice(["young_caucasian_male", "young_caucasian_male2"]), "child": child, "face": 0.6}
    top = r.choice([None, (0.5, 0.1, 0.1), (0.15, 0.3, 0.15), (0.3, 0.3, 0.32), (0.1, 0.12, 0.3)])
    return dict(spec=spec, outfit=[garment(suit, top=top, top_desat=0.6), shoes(r.choice(["shoes02", "shoes03",
                                                                                          "shoes06"]))])


def build(name, entry=None):
    e = entry or CAST[name]
    return H.Human(name, e["spec"], e["outfit"])

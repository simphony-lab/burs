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


class HeadFit:
    """Slices the real head (+ compressed hair) above a brow line that slopes down to the back, so headwear
    can be built to sit on the forehead and hug the skull."""

    def __init__(self, h, brow_gap=0.012, back_drop=0.055, hair_squash=0.45):
        top, ctr, P = h.head_top()
        brows = [p for p in h.parts if "eyebrow" in p.name]
        bz = max(v.co.z for v in brows[0].data.vertices) if brows else top.z - 0.1
        self.front_y = float(P[:, 1].min())
        self.back_y = float(P[:, 1].max())
        self.z_front = bz + brow_gap
        self.back_drop = back_drop
        pts = P
        if getattr(h, "hair", None) is not None:
            hv = np.array([v.co[:] for v in h.hair.data.vertices])
            # pull the hair volume towards the scalp (a hat presses it down)
            c = np.array([ctr.x, ctr.y, ctr.z])
            hv = c + (hv - c) * (1 - hair_squash) + (hv - c) / (np.linalg.norm(hv - c, axis=1, keepdims=True) + 1e-6) * \
                np.linalg.norm(hv - c, axis=1, keepdims=True) * hair_squash * 0.93
            pts = np.vstack([P, hv])
        self.pts = pts
        self.top_z = float(P[:, 2].max())
        u = pts[:, 2] - self.zcut(pts[:, 1])
        self.sections = []
        umax = float(u.max())
        for k in range(12):
            u0 = umax * k / 12
            sel = pts[(u >= u0 - 0.006) & (u <= u0 + 0.006)]
            if len(sel) < 8:
                continue
            cx, cy = float(np.median(sel[:, 0])), float((np.percentile(sel[:, 1], 98) + np.percentile(sel[:, 1], 2)) / 2)
            rx = float((np.percentile(sel[:, 0], 99) - np.percentile(sel[:, 0], 1)) / 2)
            ry = float((np.percentile(sel[:, 1], 99) - np.percentile(sel[:, 1], 1)) / 2)
            self.sections.append((u0, cx, cy, rx, ry))
        self.umax = umax
        self.ctr = ctr

    def zcut(self, y):
        t = np.clip((np.asarray(y) - self.front_y) / (self.back_y - self.front_y), 0, 1)
        return self.z_front - self.back_drop * t

    def section(self, u):
        s = self.sections
        if u <= s[0][0]:
            return s[0][1:]
        for a, b in zip(s, s[1:]):
            if a[0] <= u <= b[0]:
                k = (u - a[0]) / (b[0] - a[0] + 1e-9)
                return tuple(a[i] + (b[i] - a[i]) * k for i in range(1, 5))
        return s[-1][1:]

    def ring(self, u, extra=0.0, segs=72, fwd=0.0, z_override=None, scale=1.0):
        cx, cy, rx, ry = self.section(min(u, self.umax))
        out = []
        for i in range(segs):
            a = 2 * math.pi * i / segs
            x = cx + math.sin(a) * (rx * scale + extra)
            y = cy - math.cos(a) * (ry * scale + extra) - fwd * max(0.0, math.cos(a))
            z = (z_override if z_override is not None else float(self.zcut(y)) + u)
            out.append((x, y, z))
        return out


def _rings_to_mesh(rings, close_top=True):
    segs = len(rings[0])
    verts = [v for r in rings for v in r]
    faces = []
    for j in range(len(rings) - 1):
        for i in range(segs):
            a = j * segs + i
            b = j * segs + (i + 1) % segs
            faces.append((a, b, b + segs, a + segs))
    if close_top:
        last = rings[-1]
        c = tuple(sum(v[k] for v in last) / segs for k in range(3))
        ci = len(verts)
        verts.append(c)
        base = (len(rings) - 1) * segs
        for i in range(segs):
            faces.append((base + i, base + (i + 1) % segs, ci))
    return verts, faces


def hide_hair_under(h, fit, margin=0.004):
    """Delete hair faces that would poke through the hat."""
    hair = getattr(h, "hair", None)
    if hair is None:
        return
    me = hair.data
    co = np.array([v.co[:] for v in me.vertices])
    above = co[:, 2] > fit.zcut(co[:, 1]) - margin
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    kill = [f for f in bm.faces if all(above[v.index] for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(me)
    bm.free()


def hide_scalp_under(h, fit, margin=0.012):
    """Remove the (never visible) top of the head under a cap so the cap can be lower than the skull."""
    import bmesh
    me = h.body.data
    hw = h.W[:, h.bones.index("head")] > 0.5
    bm = bmesh.new()
    bm.from_mesh(me)
    kill = []
    for f in bm.faces:
        ok = True
        for v in f.verts:
            if not hw[v.index] or v.co.z < float(fit.zcut(v.co.y)) + margin:
                ok = False
                break
        if ok:
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES_ONLY")
    bm.to_mesh(me)
    bm.free()


def visor_mesh(fit, extra, length=0.052, droop=0.012, span=0.38, segs=26):
    """Stiff cap visor along the front of the brow line."""
    cx, cy, rx, ry = fit.section(0.0)
    vv, ff = [], []
    for i in range(segs + 1):
        a = -math.pi * span + 2 * math.pi * span * i / segs
        edge = abs(a) / (math.pi * span)
        L = length * (1 - 0.55 * edge ** 2)
        for k, (d, dz) in enumerate(((0.0, 0.0), (L, -droop * (1 - 0.3 * edge)))):
            rr_x, rr_y = rx + extra + d, ry + extra + d
            x = cx + math.sin(a) * rr_x
            y = cy - math.cos(a) * rr_y
            z = float(fit.zcut(cy - math.cos(a) * (ry + extra))) + 0.004 + dz
            vv.append((x, y, z))
    for i in range(segs):
        a = i * 2
        ff.append((a, a + 2, a + 3, a + 1))
    return vv, ff


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
    """'Khuliganka' eight-panel cap: low band on the forehead, wide flat crown that overhangs the sides and
    droops forward over a short visor."""

    def f(h):
        fit = HeadFit(h, brow_gap=0.02, back_drop=0.05, hair_squash=0.6)
        hide_hair_under(h, fit)
        hide_scalp_under(h, fit)
        cx, cy, rx, ry = fit.section(fit.umax * 0.45)
        ztop = min(fit.top_z + 0.002, fit.z_front + 0.088)
        segs = 72
        prof_rings = []
        # band: hugs the head for ~2.5 cm
        for u, ex in ((0.0, 0.009), (0.025, 0.011)):
            prof_rings.append(fit.ring(u, extra=ex, segs=segs))
        band_top = prof_rings[-1]
        # crown: the wide rim sits low (just above the band, over the temples), then a soft flat dome on top
        rings_spec = [  # (radius factor, height above band top at the rim .. dome)
            (0.92, 0.005), (1.0, 0.014), (0.98, 0.024), (0.86, None), (0.62, None), (0.32, None), (0.1, None)]
        crown = []
        for k, (rf, dz) in enumerate(rings_spec):
            r = []
            for i in range(segs):
                a_ = 2 * math.pi * i / segs
                front = max(0.0, math.cos(a_))
                Rx = (rx + 0.036 + 0.008 * front) * rf
                Ry = (ry + 0.032 + 0.018 * front) * rf
                x = cx + math.sin(a_) * Rx
                y = cy - 0.01 - math.cos(a_) * Ry - 0.02 * front * rf
                zb = band_top[i][2]
                if dz is not None:
                    z = zb + dz - 0.012 * front
                else:
                    tdome = {0.86: 0.55, 0.62: 0.85, 0.32: 0.97, 0.1: 1.0}[rf]
                    z0 = zb + 0.024 - 0.012 * front
                    z = z0 + (ztop - 0.008 * front - z0) * tdome
                r.append((x, y, z))
            crown.append(r)
        rings = prof_rings + crown
        # 8 seams: tiny radial dips
        out = []
        for j, r in enumerate(rings):
            if j < 2:
                out.append(r)
                continue
            rr = []
            for i, (x, y, z) in enumerate(r):
                s = 1 - 0.006 * (0.5 + 0.5 * math.cos(8 * 2 * math.pi * i / segs))
                rr.append((cx + (x - cx) * s, cy + (y - cy) * s, z - 0.002 * (0.5 + 0.5 * math.cos(8 * 2 * math.pi * i / segs))))
            out.append(rr)
        v, fcs = _rings_to_mesh(out)
        mat = wool(h.name + "_cap", rgb, 420.0)
        crown_ob = _obj(h.name + "_cap", v, fcs, mat, solid=0.003, subsurf=2)
        vv, ff = visor_mesh(fit, 0.011, length=0.05, droop=0.016, span=0.34)
        visor = _obj(h.name + "_visor", vv, ff, wool(h.name + "_visorm", tuple(c * 0.85 for c in rgb), 500.0),
                     solid=0.005, subsurf=1)
        top = out[-1]
        tx = sum(p[0] for p in top) / len(top)
        ty = sum(p[1] for p in top) / len(top)
        tz = max(p[2] for p in top)
        bv, bf = _lathe("b", [(0.008, 0.0), (0.007, 0.003), (0.002, 0.005)], 16)
        btn = _obj(h.name + "_btn", [(x + tx, y + ty, z + tz - 0.002) for x, y, z in bv], bf, mat, subsurf=0)
        for ob in (crown_ob, visor, btn):
            h.attach_to_bone(ob, "head")
    return f


def fur_hat(rgb=(0.11, 0.075, 0.05)):
    """Round brown fur hat sitting low on the forehead, straight walls, soft rounded top."""

    def f(h):
        fit = HeadFit(h, brow_gap=0.022, back_drop=0.06)
        hide_hair_under(h, fit)
        cx, cy, rx, ry = fit.section(0.0)
        base_extra = 0.028
        R = max(rx, ry * 0.92)
        rings = []
        height = (fit.top_z - fit.z_front) + 0.03
        n = 16
        for j in range(n):
            t = j / (n - 1)
            if t < 0.82:
                r = fit.ring(0.0, extra=base_extra + 0.012 * t)
                # walls go straight up from the brow ring
                r = [(x, y, z + height * t / 0.82 * (1 - 0.15 * (z - fit.z_front + fit.back_drop) / 0.2))
                     for x, y, z in r]
            else:
                k = min(1.0, (t - 0.82) / 0.18)
                rr = max(0.0, math.cos(k * math.pi / 2)) ** 0.7
                base = fit.ring(0.0, extra=base_extra + 0.012)
                ztop = fit.z_front + height + 0.018 * math.sin(k * math.pi / 2)
                r = [(cx + (x - cx) * rr, cy + (y - cy) * rr, ztop) for x, y, z in base]
            rings.append(r)
        # fur unevenness
        rnd = [0.0015 * math.sin(i * 1.7) + 0.001 * math.sin(i * 4.3) for i in range(len(rings[0]))]
        rings = [[(cx + (x - cx) * (1 + rnd[i] / R), cy + (y - cy) * (1 + rnd[i] / R), z) for i, (x, y, z) in enumerate(r)]
                 for r in rings]
        v, fcs = _rings_to_mesh(rings)
        ob = _obj(h.name + "_furhat", v, fcs, fur(h.name + "_fur", rgb), solid=0.008)
        h.attach_to_bone(ob, "head")
    return f


def beanie(rgb=(0.035, 0.035, 0.04)):
    """Knit beanie pulled over the head with a folded cuff."""

    def f(h):
        fit = HeadFit(h, brow_gap=0.02, back_drop=0.07)
        hide_hair_under(h, fit)
        rings = [fit.ring(0.0, extra=0.016), fit.ring(0.028, extra=0.017), fit.ring(0.03, extra=0.011)]
        n = 8
        for j in range(1, n + 1):
            t = j / n
            u = 0.03 + (fit.umax - 0.03) * t
            rings.append(fit.ring(u, extra=0.011 + 0.006 * t))
        base = rings[-1]
        cx_ = sum(p[0] for p in base) / len(base)
        cy_ = sum(p[1] for p in base) / len(base)
        zt = max(p[2] for p in base)
        for s_, dz in ((0.8, 0.01), (0.55, 0.018), (0.25, 0.022)):
            rings.append([(cx_ + (x - cx_) * s_, cy_ + (y - cy_) * s_, zt + dz) for x, y, z in base])
        v, fcs = _rings_to_mesh(rings)
        m, nt, b = H.node_mat(h.name + "_knit")
        b.inputs["Base Color"].default_value = H.lin3(rgb) + (1,)
        b.inputs["Roughness"].default_value = 0.95
        b.inputs["Sheen Weight"].default_value = 0.2
        b.inputs["Sheen Tint"].default_value = (0.3, 0.3, 0.32, 1)
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sub = nt.nodes.new("ShaderNodeVectorMath")
        sub.operation = "SUBTRACT"
        sub.inputs[1].default_value = (0.5, 0.5, 0.5)
        nt.links.new(tc.outputs["Generated"], sub.inputs[0])
        grad = nt.nodes.new("ShaderNodeTexGradient")
        grad.gradient_type = "RADIAL"
        nt.links.new(sub.outputs[0], grad.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        mul.inputs[1].default_value = 2 * math.pi * 90
        nt.links.new(grad.outputs["Fac"], mul.inputs[0])
        sn = nt.nodes.new("ShaderNodeMath")
        sn.operation = "SINE"
        nt.links.new(mul.outputs[0], sn.inputs[0])
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = 0.35
        bp.inputs["Distance"].default_value = 0.002
        nt.links.new(sn.outputs[0], bp.inputs["Height"])
        nt.links.new(bp.outputs[0], b.inputs["Normal"])
        ob = _obj(h.name + "_beanie", v, fcs, m, solid=0.004)
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
                      "skin": "young_caucasian_male2", "face": 0.7, "tone": (1.0, 0.9, 0.84)},
                outfit=[garment("male_casualsuit05", top=(0.05, 0.045, 0.042), legs=(0.06, 0.06, 0.065), top_rough=0.5,
                                top_coat=0.12, top_gain=1.0),
                        coat_skirt(), sweater_collar((0.12, 0.11, 0.1)), fur_hat(), shoes("shoes01", (0.05, 0.04, 0.035))]),
    "john": dict(spec={"muscle": 0.55, "weight": 0.5, "height": 0.35, "seed": 23, "hair": "short02",
                       "hair_rgb": (0.08, 0.06, 0.05), "brows": "eyebrow010", "eyes": "grey",
                       "skin": "young_caucasian_male", "face": 0.8, "tone": (1.0, 0.9, 0.84)},
                 outfit=[garment("male_casualsuit05", top=(0.07, 0.08, 0.13), legs=(0.08, 0.08, 0.1), top_rough=0.75),
                         fur_collar(), beanie(), shoes("shoes05", (0.06, 0.06, 0.06))]),
    "karim": dict(spec={"muscle": 0.5, "weight": 0.45, "height": 0.1, "seed": 37,
                        "extra": [("head/head-scale-vert-decr.target.gz", 0.55)], "hair": "short02",
                        "hair_rgb": (0.07, 0.05, 0.04), "brows": "eyebrow003", "eyes": "brown",
                        "skin": "young_caucasian_male2", "face": 0.7, "tone": (1.0, 0.9, 0.84)},
                  outfit=[garment("male_casualsuit05", top=(0.16, 0.16, 0.12), legs=(0.12, 0.13, 0.17), top_rough=0.8),
                          cap8((0.14, 0.12, 0.1)), shoes("shoes02")]),
    "artem": dict(spec={"muscle": 0.45, "weight": 0.35, "height": 0.0, "seed": 41, "hair": "short02",
                        "hair_rgb": (0.15, 0.1, 0.06), "brows": "eyebrow005", "eyes": "blue",
                        "skin": "young_caucasian_male", "face": 0.75, "tone": (1.0, 0.9, 0.84)},
                  outfit=[garment("male_casualsuit02", top=(0.035, 0.035, 0.04), legs=(0.04, 0.04, 0.045),
                                  top_rough=0.9, top_gain=0.8, legs_gain=0.9),
                          turtleneck(), cap8((0.05, 0.05, 0.055)), shoes("shoes05", (0.05, 0.05, 0.05))]),
    "maxim": dict(spec={"muscle": 0.4, "weight": 0.4, "height": -0.1, "seed": 53, "hair": "short03",
                        "hair_rgb": (0.32, 0.22, 0.12), "brows": "eyebrow002", "eyes": "blue",
                        "skin": "young_caucasian_male", "face": 0.6, "child": 0.15, "tone": (1.0, 0.91, 0.86)},
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

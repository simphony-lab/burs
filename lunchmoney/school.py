"""Procedural Russian school interior (corridor by the gym) with photo-scanned CC0 materials (ambientCG)."""
import math
import os
import random

import bpy
from mathutils import Vector

import human as H

TEX = H.TEX
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def pbr(name, tid, tint=None, scale=1.0, rough_mul=1.0, bump=0.4, desat=0.0):
    """Box-projected PBR material from an ambientCG 1K set."""
    d = os.path.join(TEX, tid)
    files = {f.split("_")[-1].split(".")[0]: os.path.join(d, f) for f in os.listdir(d) if f.endswith(".jpg")}
    m, nt, b = H.node_mat(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])

    def tex(key, cs):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = H.img(files[key], cs)
        t.projection = "BOX"
        t.projection_blend = 0.2
        nt.links.new(mp.outputs[0], t.inputs["Vector"])
        return t

    col = tex("Color", "sRGB").outputs[0]
    if tint is not None:
        col = H.tint(nt, col, tint, desat=desat)
    nt.links.new(col, b.inputs["Base Color"])
    if "Roughness" in files:
        r = tex("Roughness", "Non-Color").outputs[0]
        if rough_mul != 1.0:
            mm = nt.nodes.new("ShaderNodeMath")
            mm.operation = "MULTIPLY"
            mm.inputs[1].default_value = rough_mul
            nt.links.new(r, mm.inputs[0])
            r = mm.outputs[0]
        nt.links.new(r, b.inputs["Roughness"])
    if "NormalGL" in files:
        n = tex("NormalGL", "Non-Color")
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = bump
        nt.links.new(n.outputs[0], nm.inputs["Color"])
        nt.links.new(nm.outputs[0], b.inputs["Normal"])
    return m


def box(name, x0, x1, y0, y1, z0, z1, mat, bevel=0.0):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = H.make_mesh(name, v, f, mats=[mat], smooth=False)
    if bevel:
        m = ob.modifiers.new("bevel", "BEVEL")
        m.width = bevel
        m.segments = 2
    return ob


def text(body, loc, rot, size, mat, align="CENTER"):
    cu = bpy.data.curves.new("txt", "FONT")
    cu.body = body
    cu.font = bpy.data.fonts.load(FONT, check_existing=True)
    cu.size = size
    cu.align_x = align
    cu.extrude = 0.001
    ob = bpy.data.objects.new("txt", cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot
    ob.data.materials.append(mat)
    return ob


class Corridor:
    """Corridor along +Y. West wall (x=-W) has the gym doors and lockers, east wall (x=+W) has windows."""
    W = 2.0
    Y0, Y1 = -9.0, 22.0
    HGT = 3.2
    PANEL = 1.45  # height of the painted lower part of the walls

    def __init__(self):
        self.m = {}
        m = self.m
        m["floor"] = pbr("floor", "WoodFloor051", tint=(0.48, 0.38, 0.3), scale=0.9, rough_mul=1.15, bump=0.5,
                         desat=0.45)
        m["paint"] = pbr("paint", "PaintedPlaster017", tint=(0.5, 0.66, 0.66), scale=0.5, rough_mul=0.7, desat=1.0)
        m["white"] = pbr("white", "Plaster001", tint=(0.86, 0.86, 0.83), scale=0.4, desat=1.0)
        m["ceiling"] = pbr("ceiling", "Plaster001", tint=(0.9, 0.9, 0.88), scale=0.3, desat=1.0)
        m["door"] = pbr("door", "Wood051", tint=(0.55, 0.38, 0.25), scale=1.2, rough_mul=0.8)
        m["locker"] = pbr("locker", "Metal032", tint=(0.42, 0.5, 0.45), scale=1.5, desat=1.0, rough_mul=0.9)
        m["frame"] = pbr("frame", "Metal049A", tint=(0.9, 0.9, 0.88), scale=1.0, desat=1.0)
        m["base"] = H.plain_material("baseboard", (0.25, 0.18, 0.12), rough=0.6)
        m["line"] = H.plain_material("paintline", (0.25, 0.32, 0.32), rough=0.6)
        m["glass"] = self._glass()
        m["lamp"] = self._emit("lamp", (0.95, 1.0, 0.92), 6.0)
        m["lamp_body"] = H.plain_material("lamp_body", (0.85, 0.85, 0.83), rough=0.4)
        m["black"] = H.plain_material("blackpaint", (0.06, 0.06, 0.06), rough=0.5)
        m["sign"] = H.plain_material("sign", (0.92, 0.92, 0.9), rough=0.5)
        m["cork"] = H.plain_material("cork", (0.6, 0.45, 0.3), rough=0.95, noise=0.4, noise_scale=300, bump=0.3)
        m["paper"] = H.plain_material("paper", (0.95, 0.95, 0.93), rough=0.9)
        m["red"] = H.plain_material("red", (0.7, 0.05, 0.04), rough=0.3, coat=0.3)
        m["bench"] = pbr("bench", "Wood051", tint=(0.7, 0.55, 0.35), scale=2.0)
        m["metal"] = H.plain_material("metal", (0.3, 0.3, 0.32), rough=0.35, spec=0.6)
        self.build()

    def _glass(self):
        m = bpy.data.materials.new("glass")
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        gl = nt.nodes.new("ShaderNodeBsdfGlossy")
        gl.inputs["Roughness"].default_value = 0.05
        mx = nt.nodes.new("ShaderNodeMixShader")
        mx.inputs[0].default_value = 0.12
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(gl.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs[0])
        return m

    def _emit(self, name, rgb, strength):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        e = nt.nodes.new("ShaderNodeEmission")
        e.inputs["Color"].default_value = tuple(rgb) + (1,)
        e.inputs["Strength"].default_value = strength
        nt.links.new(e.outputs[0], out.inputs[0])
        return m

    # ---------------------------------------------------------------- build
    def build(self):
        W, Y0, Y1, Hh, P = self.W, self.Y0, self.Y1, self.HGT, self.PANEL
        m = self.m
        box("floor", -W, W, Y0, Y1, -0.05, 0.0, m["floor"])
        box("ceiling", -W, W, Y0, Y1, Hh, Hh + 0.05, m["ceiling"])
        box("end_wall_n", -W, W, Y1, Y1 + 0.1, 0, Hh, m["white"])
        box("end_wall_s", -W, W, Y0 - 0.1, Y0, 0, Hh, m["white"])
        # walls with door / window openings
        doors = [(1.1, 2.9)]  # gym double door, y range on the west wall
        self._wall(-W, -1, doors, opening_h=2.35)
        windows = [(y, y + 1.7) for y in (-6.0, -1.5, 3.0, 7.5, 12.0, 16.5)]
        self._wall(W, 1, [], windows=windows)
        self._gym_doors(-W, 1.1, 2.9)
        self._lockers(-W, 5.0, 11.0)
        self._board(-W, -4.0)
        self._extinguisher(-W, 4.2)
        self._bench(-W, 13.0)
        for y0, y1 in windows:
            self._window(W, y0, y1)
            self._radiator(W, (y0 + y1) / 2)
        for y in range(-7, 22, 3):
            self._lamp(0.0, y + 0.5)
        self._daylight()

    def _wall(self, x, side, doors, windows=(), opening_h=2.3):
        """A wall split into strips around openings; painted lower part + white upper part + baseboard."""
        m, P, Hh = self.m, self.PANEL, self.HGT
        t = 0.15
        x0, x1 = (x - t, x) if side < 0 else (x, x + t)
        cuts = sorted([(a, b, 0.0, opening_h) for a, b in doors] + [(a, b, 0.9, 2.55) for a, b in windows])
        y = self.Y0
        segs = []
        for a, b, z0, z1 in cuts:
            segs.append((y, a, None))
            segs.append((a, b, (z0, z1)))
            y = b
        segs.append((y, self.Y1, None))
        for a, b, hole in segs:
            if b - a < 1e-3:
                continue
            if hole is None:
                parts = [(0, P), (P, Hh)]
            else:
                parts = [(0, hole[0]), (hole[1], Hh)] if hole[0] > 0 else [(hole[1], Hh)]
            for z0, z1 in parts:
                if z1 - z0 < 1e-3:
                    continue
                if z1 <= P:
                    box("wall_lo", x0, x1, a, b, z0, z1, m["paint"])
                elif z0 >= P:
                    box("wall_hi", x0, x1, a, b, z0, z1, m["white"])
                else:
                    box("wall_lo", x0, x1, a, b, z0, P, m["paint"])
                    box("wall_hi", x0, x1, a, b, P, z1, m["white"])
            # paint line + baseboard (not across door openings)
            if hole is None or hole[0] > 0:
                inner = x if side < 0 else x
                d = 0.012 * (1 if side < 0 else -1)
                xa, xb = (inner, inner + d) if side < 0 else (inner + d, inner)
                box("line", min(xa, xb), max(xa, xb), a, b, P - 0.012, P + 0.012, m["line"])
                if hole is None:
                    box("base", min(xa, xb) - (0.006 if side > 0 else 0), max(xa, xb) + (0.006 if side < 0 else 0), a, b,
                        0, 0.1, m["base"])

    def _gym_doors(self, x, y0, y1):
        m = self.m
        fr = 0.07
        box("door_frame_l", x, x + 0.04, y0, y0 + fr, 0, 2.35, m["door"])
        box("door_frame_r", x, x + 0.04, y1 - fr, y1, 0, 2.35, m["door"])
        box("door_frame_t", x, x + 0.04, y0, y1, 2.28, 2.35, m["door"])
        mid = (y0 + y1) / 2
        for a, b, nm in ((y0 + fr, mid - 0.005, "door_l"), (mid + 0.005, y1 - fr, "door_r")):
            box(nm, x - 0.02, x + 0.015, a, b, 0.01, 2.27, m["door"], bevel=0.004)
            # small window in each leaf
            box(nm + "_win", x + 0.016, x + 0.02, a + 0.18, b - 0.18, 1.35, 1.95, m["glass"])
            box(nm + "_handle", x + 0.02, x + 0.07, (b - 0.1) if nm == "door_l" else (a + 0.06),
                (b - 0.04) if nm == "door_l" else (a + 0.12), 1.0, 1.03, m["metal"])
        box("sign", x, x + 0.015, mid - 0.45, mid + 0.45, 2.48, 2.72, m["sign"])
        text("СПОРТЗАЛ", (x + 0.018, mid, 2.545), (math.pi / 2, 0, math.pi / 2), 0.15, m["black"])
        # lit gym behind the door windows
        box("gym_back", x - 2.0, x - 1.98, y0 - 1, y1 + 1, 0, 3.2, self._emit("gymlight", (0.8, 0.82, 0.8), 1.2))

    def _lockers(self, x, y0, y1):
        m = self.m
        n = int((y1 - y0) / 0.42)
        self.locker_doors = []
        dep = 0.45
        box("locker_body", x, x + dep, y0, y0 + n * 0.42, 0.1, 1.95, m["locker"])
        box("locker_plinth", x, x + dep - 0.02, y0, y0 + n * 0.42, 0, 0.1, m["black"])
        for i in range(n):
            a = y0 + i * 0.42
            # door as separate object hinged at its +y edge so it can swing open
            door = box(f"locker_door_{i}", 0, 0.018, -0.4, 0, 0.13, 1.92, m["locker"])
            door.location = (x + dep, a + 0.41, 0)
            for k, z in enumerate((1.7, 1.66, 1.62, 1.58, 0.5, 0.46, 0.42)):
                vent = box(f"vent{i}_{k}", 0.018, 0.022, -0.3, -0.1, z, z + 0.015, m["black"])
                vent.parent = door
            hd = box(f"handle{i}", 0.018, 0.04, -0.37, -0.33, 1.0, 1.08, m["metal"])
            hd.parent = door
            self.locker_doors.append(door)
        self.locker_x = x + dep

    def _board(self, x, y):
        m = self.m
        box("board", x, x + 0.03, y - 0.8, y + 0.8, 1.15, 2.0, m["cork"])
        r = random.Random(4)
        for i in range(9):
            py = y - 0.7 + r.random() * 1.2
            pz = 1.22 + r.random() * 0.6
            box(f"paper{i}", x + 0.03, x + 0.034, py, py + 0.21, pz, pz + 0.29, m["paper"])

    def _extinguisher(self, x, y):
        m = self.m
        bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=0.5, location=(x + 0.12, y, 0.75))
        ob = bpy.context.active_object
        ob.data.materials.append(m["red"])
        bpy.ops.object.shade_smooth()

    def _bench(self, x, y):
        m = self.m
        box("bench_seat", x + 0.08, x + 0.42, y, y + 1.8, 0.42, 0.46, m["bench"], bevel=0.01)
        for yy in (y + 0.1, y + 1.65):
            box("bench_leg", x + 0.12, x + 0.38, yy, yy + 0.05, 0, 0.42, m["metal"])

    def _window(self, x, y0, y1):
        m = self.m
        z0, z1 = 0.9, 2.55
        t = 0.06
        box("win_sill", x - 0.25, x, y0 - 0.05, y1 + 0.05, z0 - 0.04, z0, m["frame"])
        for a, b in ((y0, y0 + t), (y1 - t, y1), ((y0 + y1) / 2 - t / 2, (y0 + y1) / 2 + t / 2)):
            box("win_post", x + 0.05, x + 0.12, a, b, z0, z1, m["frame"])
        for a, b in ((z0, z0 + t), (z1 - t, z1), (2.05, 2.05 + t)):
            box("win_bar", x + 0.05, x + 0.12, y0, y1, a, b, m["frame"])
        box("win_glass", x + 0.08, x + 0.085, y0, y1, z0, z1, m["glass"])

    def _radiator(self, x, y):
        m = self.m
        for i in range(14):
            yy = y - 0.5 + i * 0.075
            box(f"rad{i}", x - 0.13, x - 0.05, yy, yy + 0.05, 0.18, 0.78, m["frame"], bevel=0.01)

    def _lamp(self, x, y):
        m = self.m
        box("lamp_body", x - 0.15, x + 0.15, y - 0.65, y + 0.65, self.HGT - 0.08, self.HGT, m["lamp_body"])
        box("lamp_tube", x - 0.09, x + 0.09, y - 0.6, y + 0.6, self.HGT - 0.085, self.HGT - 0.08, m["lamp"])
        ld = bpy.data.lights.new("lamp", "AREA")
        ld.shape = "RECTANGLE"
        ld.size = 0.18
        ld.size_y = 1.2
        ld.energy = 70
        ld.color = (0.95, 1.0, 0.92)
        lo = bpy.data.objects.new("lamp", ld)
        bpy.context.scene.collection.objects.link(lo)
        lo.location = (x, y, self.HGT - 0.1)

    def _daylight(self):
        sc = bpy.context.scene
        w = bpy.data.worlds.new("overcast")
        sc.world = w
        w.use_nodes = True
        bg = w.node_tree.nodes["Background"]
        bg.inputs[0].default_value = (0.75, 0.8, 0.88, 1)
        bg.inputs[1].default_value = 1.6
        sd = bpy.data.lights.new("sun", "SUN")
        sd.energy = 2.0
        sd.angle = math.radians(25)
        sd.color = (0.92, 0.95, 1.0)
        so = bpy.data.objects.new("sun", sd)
        sc.collection.objects.link(so)
        so.rotation_euler = Vector((0.9, 0.25, 0.7)).to_track_quat("Z", "Y").to_euler()
        # big soft window light (portal-like) per window, from outside
        for y in (-5.15, -0.65, 3.85, 8.35, 12.85, 17.35):
            ld = bpy.data.lights.new("winlight", "AREA")
            ld.shape = "RECTANGLE"
            ld.size = 1.6
            ld.size_y = 1.6
            ld.energy = 200
            ld.color = (0.88, 0.92, 1.0)
            lo = bpy.data.objects.new("winlight", ld)
            sc.collection.objects.link(lo)
            lo.location = (self.W + 0.4, y, 1.75)
            lo.rotation_euler = (0, math.pi / 2, 0)

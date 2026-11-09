"""Locations for the episode: the school yard (scene 1) and the main school hall (scenes 2-5)."""
import math
import random

import bpy
from mathutils import Vector

import human as H
from school import box, pbr, text


def emit(name, rgb, strength):
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


def glass():
    m = bpy.data.materials.new("glass")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    g = nt.nodes.new("ShaderNodeBsdfPrincipled")
    g.inputs["Base Color"].default_value = (0.02, 0.025, 0.03, 1)
    g.inputs["Roughness"].default_value = 0.05
    g.inputs["Specular IOR Level"].default_value = 0.8
    nt.links.new(g.outputs[0], out.inputs[0])
    return m


def cyl(name, p0, p1, r, mat, verts=10):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d.length, location=(p0 + p1) / 2)
    ob = bpy.context.active_object
    ob.name = name
    ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    ob.data.materials.append(mat)
    return ob


def sun_and_sky(elev=15, azim=-35, energy=4.5, sky=((0.22, 0.42, 0.85), (0.78, 0.84, 0.92)), strength=1.0):
    sc = bpy.context.scene
    w = bpy.data.worlds.new("sky")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 0.6
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(mr.outputs[0], mix.inputs[0])
    mix.inputs[6].default_value = tuple(sky[1]) + (1,)
    mix.inputs[7].default_value = tuple(sky[0]) + (1,)
    nt.links.new(mix.outputs[2], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    nt.links.new(bg.outputs[0], out.inputs[0])
    sd = bpy.data.lights.new("sun", "SUN")
    sd.energy = energy
    sd.angle = math.radians(0.8)
    sd.color = (1.0, 0.9, 0.78)
    so = bpy.data.objects.new("sun", sd)
    sc.collection.objects.link(so)
    e, a = math.radians(elev), math.radians(azim)
    d = Vector((math.cos(e) * math.sin(a), math.cos(e) * math.cos(a), math.sin(e)))
    so.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    return so


# ============================================================================ street (scene 1)

class Street:
    """School on the left (x<0), fence on the right, outdoor gym ahead (+y), blocks of flats behind."""
    SCHOOL_X = -6.0
    FENCE_X = 7.0

    def __init__(self, seed=3):
        self.r = random.Random(seed)
        m = self.m = {}
        m["snow"] = pbr("snow", "Snow010A", tint=(0.92, 0.94, 0.98), scale=0.35, rough_mul=0.9, bump=0.6, desat=0.0)
        m["snowpath"] = pbr("snowpath", "Snow013", tint=(0.82, 0.83, 0.86), scale=0.6, bump=0.7, desat=0.3)
        m["asphalt"] = pbr("asphalt", "Asphalt031", tint=(0.42, 0.42, 0.43), scale=0.4)
        m["facade"] = pbr("facade", "PaintedPlaster006", tint=(0.86, 0.78, 0.55), scale=0.25, desat=0.7)
        m["plinth"] = pbr("plinth", "PaintedPlaster006", tint=(0.45, 0.43, 0.42), scale=0.3, desat=1.0)
        m["frame"] = H.plain_material("winframe", (0.9, 0.9, 0.88), rough=0.5)
        m["glass"] = glass()
        m["door"] = pbr("door", "PaintedMetal004", tint=(0.35, 0.22, 0.14), scale=1.0, desat=1.0)
        m["fence"] = pbr("fence", "PaintedMetal004", tint=(0.12, 0.3, 0.2), scale=2.0, desat=1.0)
        m["gym"] = pbr("gym", "PaintedMetal004", tint=(0.15, 0.32, 0.6), scale=2.0, desat=1.0)
        m["rust"] = pbr("rust", "Metal063", scale=1.5)
        m["flats"] = pbr("flats", "Facade018A", tint=(0.8, 0.75, 0.7), scale=0.09, desat=0.3)
        m["roof"] = H.plain_material("roof", (0.3, 0.3, 0.32), rough=0.8)
        m["birch"] = self._birch()
        m["twig"] = H.plain_material("twig", (0.22, 0.18, 0.16), rough=0.9)
        m["sign"] = H.plain_material("sign", (0.92, 0.92, 0.9), rough=0.5)
        m["black"] = H.plain_material("black", (0.05, 0.05, 0.05), rough=0.5)
        m["concrete"] = pbr("concrete", "Concrete034", tint=(0.6, 0.6, 0.6), scale=0.5)
        self.build()

    def _birch(self):
        m, nt, b = H.node_mat("birch")
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 6.0
        nz.inputs["Detail"].default_value = 3.0
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (1.0, 1.0, 0.15)
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
        nt.links.new(mp.outputs[0], nz.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.55
        ramp.color_ramp.elements[0].color = (0.75, 0.74, 0.7, 1)
        ramp.color_ramp.elements[1].position = 0.62
        ramp.color_ramp.elements[1].color = (0.04, 0.04, 0.04, 1)
        nt.links.new(nz.outputs[0], ramp.inputs[0])
        nt.links.new(ramp.outputs[0], b.inputs["Base Color"])
        b.inputs["Roughness"].default_value = 0.8
        return m

    def build(self):
        m = self.m
        box("ground", -80, 80, -80, 80, -0.05, 0.0, m["snow"])
        box("path", self.SCHOOL_X, self.SCHOOL_X + 4.5, -30, 40, 0.0, 0.012, m["snowpath"])
        box("asphalt", self.SCHOOL_X + 0.2, self.SCHOOL_X + 2.8, -30, 40, 0.012, 0.02, m["asphalt"])
        self._school()
        self._fence()
        self._outdoor_gym(0.5, 19.0)
        self._flats()
        for x, y in ((9.0, -4), (10.5, 6), (9.5, 15), (11.0, 24), (-1.5, 30), (4.5, 31), (12.0, 33), (8.5, -14)):
            self.birch((x, y, 0), 9 + self.r.uniform(-2, 3))
        for y in (-8, 12, 30):
            self._lamp_post((self.SCHOOL_X + 3.2, y))
        for i in range(10):
            x, y = self.r.uniform(1, 6.5), self.r.uniform(-20, 35)
            bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=1, location=(x, y, -0.25))
            ob = bpy.context.active_object
            ob.scale = (self.r.uniform(0.8, 2.0), self.r.uniform(1.0, 3.0), 0.4)
            ob.data.materials.append(m["snow"])
            bpy.ops.object.shade_smooth()
        self.sun = sun_and_sky()

    def _school(self):
        m, X = self.m, self.SCHOOL_X
        box("school", X - 14, X, -40, 45, 0, 9.6, m["facade"])
        box("plinth", X - 0.03, X + 0.06, -40, 45, 0, 0.8, m["plinth"])
        box("cornice", X - 0.02, X + 0.25, -40, 45, 9.4, 9.6, m["plinth"])
        gym = (-2.0, 14.0)
        for y in range(-38, 44, 3):
            if gym[0] - 1 < y < gym[1] + 1:
                continue
            for z0 in (1.3, 4.4, 7.4):
                self._window(X, y + 0.6, y + 2.2, z0, z0 + 1.6)
        for y in range(int(gym[0]), int(gym[1]), 4):
            self._window(X, y + 0.3, y + 3.5, 3.0, 4.6, bars=4)
            for z0 in (6.6,):
                self._window(X, y + 0.6, y + 3.2, z0, z0 + 1.6)
        # gym door with canopy and sign
        dy = 6.0
        box("door_l", X + 0.02, X + 0.08, dy - 0.75, dy - 0.01, 0, 2.2, m["door"], bevel=0.005)
        box("door_r", X + 0.02, X + 0.08, dy + 0.01, dy + 0.75, 0, 2.2, m["door"], bevel=0.005)
        box("canopy", X, X + 1.3, dy - 1.3, dy + 1.3, 2.55, 2.68, m["concrete"])
        box("step", X, X + 1.2, dy - 1.2, dy + 1.2, 0, 0.15, m["concrete"])
        box("sign", X + 0.02, X + 0.05, dy - 0.7, dy + 0.7, 2.25, 2.5, m["sign"])
        text("СПОРТЗАЛ", (X + 0.055, dy, 2.31), (math.pi / 2, 0, math.pi / 2), 0.15, m["black"])

    def _window(self, X, y0, y1, z0, z1, bars=2):
        m = self.m
        box("glass", X - 0.08, X - 0.06, y0, y1, z0, z1, m["glass"])
        t = 0.07
        for a, b in ((y0 - t, y0), (y1, y1 + t)):
            box("wf", X - 0.08, X + 0.02, a, b, z0 - t, z1 + t, m["frame"])
        for a, b in ((z0 - t, z0), (z1, z1 + t)):
            box("wf", X - 0.08, X + 0.02, y0, y1, a, b, m["frame"])
        for k in range(1, bars):
            y = y0 + (y1 - y0) * k / bars
            box("wm", X - 0.07, X + 0.0, y - 0.025, y + 0.025, z0, z1, m["frame"])
        box("sill", X - 0.02, X + 0.12, y0 - 0.1, y1 + 0.1, z0 - 0.12, z0 - 0.07, m["plinth"])

    def _fence(self):
        m, X = self.m, self.FENCE_X
        y0, y1 = -40, 45
        y = y0
        while y <= y1:
            box("post", X - 0.04, X + 0.04, y - 0.04, y + 0.04, 0, 1.95, m["fence"])
            y += 2.5
        for z in (0.15, 1.75):
            box("rail", X - 0.02, X + 0.02, y0, y1, z, z + 0.05, m["fence"])
        bar = box("bar", X - 0.01, X + 0.01, y0, y0 + 0.02, 0.15, 1.8, m["fence"])
        arr = bar.modifiers.new("arr", "ARRAY")
        arr.count = int((y1 - y0) / 0.16)
        arr.use_relative_offset = False
        arr.use_constant_offset = True
        arr.constant_offset_displace = (0, 0.16, 0)

    def _outdoor_gym(self, x, y):
        m = self.m
        for i, (hgt, dx) in enumerate(((1.95, 0.0), (2.25, 1.6), (2.5, 3.2))):
            p = x + dx
            cyl(f"tpost{i}a", (p, y, 0), (p, y, hgt + 0.05), 0.045, m["gym"])
            cyl(f"tpost{i}b", (p, y + 1.3, 0), (p, y + 1.3, hgt + 0.05), 0.045, m["gym"])
            cyl(f"tbar{i}", (p, y, hgt), (p, y + 1.3, hgt), 0.018, m["rust"])
        # parallel bars
        bx, by = x - 2.2, y + 2.5
        for k in (0, 0.55):
            for yy in (by, by + 2.2):
                cyl("ppost", (bx + k, yy, 0), (bx + k, yy, 1.3), 0.04, m["gym"])
            cyl("pbar", (bx + k, by - 0.2, 1.3), (bx + k, by + 2.4, 1.3), 0.025, m["rust"])
        # wall bars (shvedskaya stenka)
        wx, wy = x + 5.0, y + 0.5
        for yy in (wy, wy + 0.9):
            cyl("wpost", (wx, yy, 0), (wx, yy, 2.6), 0.04, m["gym"])
        for k in range(10):
            cyl("rung", (wx, wy, 0.3 + k * 0.24), (wx, wy + 0.9, 0.3 + k * 0.24), 0.015, m["rust"])
        self.turnik = Vector((x, y + 0.65, 1.95))

    def _flats(self):
        m = self.m
        for i, (x, y, L) in enumerate(((28, -10, 60), (26, 52, 50), (-10, 70, 70))):
            if i < 2:
                box(f"flats{i}", x, x + 12, y - L / 2, y + L / 2, 0, 15.5, m["flats"])
                box(f"flatsroof{i}", x - 0.2, x + 12.2, y - L / 2 - 0.2, y + L / 2 + 0.2, 15.5, 15.8, m["roof"])
            else:
                box(f"flats{i}", x - L / 2, x + L / 2, y, y + 12, 0, 15.5, m["flats"])
                box(f"flatsroof{i}", x - L / 2 - 0.2, x + L / 2 + 0.2, y - 0.2, y + 12.2, 15.5, 15.8, m["roof"])

    def birch(self, p, h):
        """Whole tree as one mesh (trunk + branches + twigs) built with bmesh: fast."""
        import bmesh
        from mathutils import Matrix
        m = self.m
        p = Vector(p)
        bm = bmesh.new()
        twig_faces = []

        def add(p0, p1, r, segs, twig=False):
            d = p1 - p0
            if d.length < 1e-4:
                return
            rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
            mat = Matrix.Translation((p0 + p1) / 2) @ rot
            res = bmesh.ops.create_cone(bm, cap_ends=False, segments=segs, radius1=r, radius2=r * 0.6,
                                        depth=d.length, matrix=mat)
            if twig:
                faces = {f for v in res["verts"] for f in v.link_faces}
                twig_faces.extend(faces)

        top = p + Vector((self.r.uniform(-0.3, 0.3), self.r.uniform(-0.3, 0.3), h))
        add(p, top, 0.13, 12)
        for k in range(26):
            t = self.r.uniform(0.35, 0.95)
            base = p + (top - p) * t
            a = self.r.uniform(0, 2 * math.pi)
            L = (1 - t) * h * 0.55 + 0.6
            d = Vector((math.cos(a), math.sin(a), self.r.uniform(0.6, 1.4))).normalized()
            end = base + d * L
            add(base, end, 0.04 * (1 - t) + 0.012, 6, twig=t >= 0.6)
            for j in range(3):
                b2 = base + (end - base) * self.r.uniform(0.4, 0.9)
                d2 = (d + Vector((self.r.uniform(-0.8, 0.8), self.r.uniform(-0.8, 0.8),
                                  self.r.uniform(-0.6, 0.2)))).normalized()
                add(b2, b2 + d2 * L * 0.35, 0.008, 4, twig=True)
        me = bpy.data.meshes.new("birch")
        for f in twig_faces:
            if f.is_valid:
                f.material_index = 1
        bm.to_mesh(me)
        bm.free()
        me.materials.append(m["birch"])
        me.materials.append(m["twig"])
        ob = bpy.data.objects.new("birch", me)
        bpy.context.scene.collection.objects.link(ob)

    def _lamp_post(self, p):
        m = self.m
        x, y = p
        cyl("lpost", (x, y, 0), (x, y, 6.5), 0.09, m["concrete"], 10)
        cyl("larm", (x, y, 6.4), (x + 1.2, y, 6.6), 0.04, m["concrete"], 8)
        box("lhead", x + 1.0, x + 1.5, y - 0.15, y + 0.15, 6.45, 6.6, m["plinth"])


# ============================================================================ main school hall (scenes 2-5)

class Hall:
    """One large recreation hall of the gang's own school: entrance at the south (y=Y0), lockers along the west
    wall (scene 4), vending machines on the east wall, tables of the common zone in the north half
    (scenes 3 and 5), canteen serving hatch on the north wall."""
    X0, X1 = -5.0, 5.0
    Y0, Y1 = -8.0, 26.0
    HGT = 3.3
    PANEL = 1.5

    def __init__(self, seed=5):
        self.r = random.Random(seed)
        m = self.m = {}
        m["floor"] = pbr("hfloor", "Tiles138", tint=(0.55, 0.47, 0.4), scale=0.8, rough_mul=0.9, desat=0.5)
        m["paint"] = pbr("hpaint", "PaintedPlaster017", tint=(0.62, 0.7, 0.55), scale=0.5, rough_mul=0.7, desat=1.0)
        m["white"] = pbr("hwhite", "Plaster001", tint=(0.87, 0.86, 0.82), scale=0.4, desat=1.0)
        m["ceiling"] = pbr("hceil", "Plaster001", tint=(0.9, 0.9, 0.88), scale=0.3, desat=1.0)
        m["locker"] = pbr("hlocker", "Metal032", tint=(0.32, 0.42, 0.55), scale=1.5, desat=1.0, rough_mul=0.9)
        m["table"] = pbr("htable", "Wood051", tint=(0.75, 0.6, 0.42), scale=2.0)
        m["metal"] = H.plain_material("hmetal", (0.35, 0.35, 0.37), rough=0.35, spec=0.6)
        m["frame"] = H.plain_material("hframe", (0.9, 0.9, 0.88), rough=0.5)
        m["glass"] = glass()
        m["door"] = pbr("hdoor", "Wood051", tint=(0.55, 0.38, 0.25), scale=1.2)
        m["black"] = H.plain_material("hblack", (0.05, 0.05, 0.05), rough=0.5)
        m["vend"] = H.plain_material("vend", (0.6, 0.06, 0.05), rough=0.3, coat=0.4)
        m["vend2"] = H.plain_material("vend2", (0.08, 0.2, 0.5), rough=0.3, coat=0.4)
        m["vendlit"] = emit("vendlit", (0.95, 0.95, 0.9), 2.5)
        m["lamp"] = emit("hlamp", (0.95, 1.0, 0.92), 6.0)
        m["tray"] = H.plain_material("tray", (0.75, 0.68, 0.5), rough=0.4)
        m["plate"] = H.plain_material("plate", (0.95, 0.95, 0.93), rough=0.25)
        m["food"] = H.plain_material("food", (0.75, 0.55, 0.3), rough=0.7)
        m["sign"] = H.plain_material("hsign", (0.92, 0.92, 0.9), rough=0.5)
        m["red"] = H.plain_material("hred", (0.7, 0.05, 0.04), rough=0.3)
        m["snow"] = H.plain_material("hsnow", (0.86, 0.88, 0.92), rough=0.6)
        self.tables = []
        self.locker_doors = []
        self.build()

    def build(self):
        m = self
        mt = self.m
        X0, X1, Y0, Y1, Hh, P = self.X0, self.X1, self.Y0, self.Y1, self.HGT, self.PANEL
        box("hfloor", X0, X1, Y0, Y1, -0.05, 0, mt["floor"])
        box("hceiling", X0, X1, Y0, Y1, Hh, Hh + 0.05, mt["ceiling"])
        DX0, DX1, DZ = -0.82, 0.82, 2.25  # entrance opening in the south wall
        for (a0, a1, b0, b1) in ((X0 - 0.15, X0, Y0, Y1), (X1, X1 + 0.15, Y0, Y1), (X0, X1, Y1, Y1 + 0.15)):
            box("hwall_lo", a0, a1, b0, b1, 0, P, mt["paint"])
            box("hwall_hi", a0, a1, b0, b1, P, Hh, mt["white"])
        for (a0, a1) in ((X0, DX0), (DX1, X1)):
            box("hwall_lo", a0, a1, Y0 - 0.15, Y0, 0, P, mt["paint"])
            box("hwall_hi", a0, a1, Y0 - 0.15, Y0, P, Hh, mt["white"])
        box("hwall_hi", DX0, DX1, Y0 - 0.15, Y0, DZ, Hh, mt["white"])
        # door frame
        for a0, a1 in ((DX0 - 0.06, DX0), (DX1, DX1 + 0.06)):
            box("hdframe", a0, a1, Y0 - 0.17, Y0 + 0.02, 0, DZ + 0.06, mt["frame"])
        box("hdframe", DX0 - 0.06, DX1 + 0.06, Y0 - 0.17, Y0 + 0.02, DZ, DZ + 0.06, mt["frame"])
        # two door leaves hinged at the frame, opening inwards (rotate the hinge empties)
        self.entrance_doors = []
        for x_h, sgn in ((DX0, 1), (DX1, -1)):
            hinge = bpy.data.objects.new("hdoor_hinge", None)
            bpy.context.scene.collection.objects.link(hinge)
            hinge.location = (x_h, Y0 - 0.06, 0)
            w = (DX1 - DX0) / 2 - 0.01
            xa, xb = (0.0, w) if sgn > 0 else (-w, 0.0)
            leaf = box("hdoor", xa, xb, -0.025, 0.025, 0.01, DZ - 0.01, mt["door"], bevel=0.004)
            win = box("hdoorwin", xa + 0.15, xb - 0.15, -0.03, 0.03, 1.15, 1.95, mt["glass"])
            for ob in (leaf, win):
                ob.parent = hinge
            self.entrance_doors.append((hinge, sgn))
        # outside: snowy porch and bright winter daylight behind the doors
        box("hporch", -3.0, 3.0, Y0 - 6.0, Y0 - 0.15, -0.05, 0, mt["snow"])
        box("hsky_out", -6.0, 6.0, Y0 - 6.2, Y0 - 6.0, -0.5, 4.0, emit("hout", (0.85, 0.88, 0.95), 2.2))
        lamp = bpy.data.lights.new("hout_l", "AREA")
        lamp.energy = 400
        lamp.size = 2.0
        lamp.color = (0.85, 0.9, 1.0)
        lo = bpy.data.objects.new("hout_l", lamp)
        bpy.context.scene.collection.objects.link(lo)
        lo.location = (0, Y0 - 1.5, 2.4)
        lo.rotation_euler = (math.radians(-70), 0, 0)
        self.entrance = Vector((0.0, Y0 + 0.4, 0))
        # windows on the east wall
        for y in range(int(Y0) + 2, int(Y1) - 1, 5):
            box("hwin", X1 - 0.01, X1, y, y + 2.2, 1.0, 2.7, emit("hsky", (0.85, 0.9, 1.0), 1.6))
            for a, b in ((y - 0.06, y), (y + 2.2, y + 2.26), (y + 1.07, y + 1.13)):
                box("hwf", X1 - 0.08, X1, a, b, 1.0, 2.7, mt["frame"])
            box("hwsill", X1 - 0.25, X1, y - 0.05, y + 2.25, 0.96, 1.0, mt["frame"])
        # lockers along the west wall (scene 4)
        self._lockers(X0, 0.0, 10.0)
        # vending machines on the east wall
        for i, y in enumerate((5.0, 6.1)):
            box(f"vend{i}", X1 - 0.85, X1 - 0.05, y, y + 0.95, 0, 1.9, mt["vend" if i == 0 else "vend2"], bevel=0.01)
            box(f"vendwin{i}", X1 - 0.86, X1 - 0.85, y + 0.1, y + 0.65, 0.8, 1.75, mt["vendlit"])
        # tables of the common zone
        for i, (x, y) in enumerate(((-2.4, 14.0), (1.8, 14.5), (-2.2, 19.0), (2.0, 19.5), (-0.2, 23.5))):
            self._table(x, y, i)
        # canteen hatch
        box("hatch", -1.5, 1.5, Y1 - 0.02, Y1, 0.9, 1.6, emit("hatchlit", (0.9, 0.85, 0.7), 1.2))
        box("hatchsign", -0.8, 0.8, Y1 - 0.03, Y1 - 0.02, 2.0, 2.35, mt["sign"])
        text("СТОЛОВАЯ", (0, Y1 - 0.035, 2.09), (math.pi / 2, 0, math.pi), 0.16, mt["black"])
        # ceiling lamps (emissive) + a few area lights
        for y in range(int(Y0) + 2, int(Y1), 4):
            for x in (-2.5, 2.5):
                box("hlamp", x - 0.15, x + 0.15, y - 0.6, y + 0.6, Hh - 0.03, Hh, mt["lamp"])
        for y in (0.0, 9.0, 17.0, 23.0):
            ld = bpy.data.lights.new("hl", "AREA")
            ld.shape = "RECTANGLE"
            ld.size = 4.0
            ld.size_y = 3.0
            ld.energy = 420
            ld.color = (0.95, 1.0, 0.92)
            lo = bpy.data.objects.new("hl", ld)
            bpy.context.scene.collection.objects.link(lo)
            lo.location = (0, y, Hh - 0.1)
        for y in (0.0, 10.0, 20.0):
            ld = bpy.data.lights.new("hwinl", "AREA")
            ld.size = 4.0
            ld.energy = 300
            ld.color = (0.85, 0.9, 1.0)
            lo = bpy.data.objects.new("hwinl", ld)
            bpy.context.scene.collection.objects.link(lo)
            lo.location = (X1 - 0.3, y, 1.9)
            lo.rotation_euler = (0, math.pi / 2, 0)
            lo.data.use_shadow = False
        sc = bpy.context.scene
        w = bpy.data.worlds.new("hw")
        sc.world = w
        w.use_nodes = True
        w.node_tree.nodes["Background"].inputs[0].default_value = (0.7, 0.75, 0.82, 1)
        w.node_tree.nodes["Background"].inputs[1].default_value = 0.35

    def open_doors(self, f_open, f_close, angle=80.0):
        """Entrance doors swing in (8 frames), stay open, swing shut (10 frames)."""
        for hinge, sgn in self.entrance_doors:
            for f, a in ((1, 0.0), (f_open, 0.0), (f_open + 8, angle), (f_close, angle), (f_close + 10, 0.0)):
                hinge.rotation_euler = (0, 0, math.radians(a * sgn))
                hinge.keyframe_insert("rotation_euler", frame=f)

    def _lockers(self, x, y0, y1):
        mt = self.m
        n = int((y1 - y0) / 0.42)
        dep = 0.45
        box("hlocker_body", x, x + dep, y0, y0 + n * 0.42, 0.1, 1.95, mt["locker"])
        box("hlocker_plinth", x, x + dep - 0.02, y0, y0 + n * 0.42, 0, 0.1, mt["black"])
        for i in range(n):
            a = y0 + i * 0.42
            door = box(f"hlocker_door_{i}", 0, 0.018, -0.4, 0, 0.13, 1.92, mt["locker"])
            door.location = (x + dep, a + 0.41, 0)
            for k, z in enumerate((1.7, 1.66, 1.62, 0.5, 0.46)):
                vent = box(f"hvent{i}_{k}", 0.018, 0.022, -0.3, -0.1, z, z + 0.015, mt["black"])
                vent.parent = door
            hd = box(f"hhandle{i}", 0.018, 0.04, -0.37, -0.33, 1.0, 1.08, mt["metal"])
            hd.parent = door
            self.locker_doors.append(door)
        self.locker_x = x + dep

    def _table(self, x, y, i):
        mt = self.m
        box(f"table{i}", x - 0.8, x + 0.8, y - 0.4, y + 0.4, 0.72, 0.76, mt["table"], bevel=0.01)
        for dx in (-0.7, 0.7):
            box(f"tleg{i}", x + dx - 0.03, x + dx + 0.03, y - 0.03, y + 0.03, 0, 0.72, mt["metal"])
        for side in (-1, 1):
            yy = y + side * 0.62
            box(f"bench{i}", x - 0.8, x + 0.8, yy - 0.15, yy + 0.15, 0.42, 0.46, mt["table"], bevel=0.01)
            for dx in (-0.7, 0.7):
                box(f"bleg{i}", x + dx - 0.03, x + dx + 0.03, yy - 0.03, yy + 0.03, 0, 0.42, mt["metal"])
        # trays with plates
        for k in range(4):
            tx = x - 0.55 + k * 0.37
            for side in (-1, 1):
                ty = y + side * 0.2
                if self.r.random() < 0.3:
                    continue
                box("tray", tx - 0.15, tx + 0.15, ty - 0.11, ty + 0.11, 0.76, 0.775, mt["tray"])
                bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.09, depth=0.02, location=(tx, ty, 0.79))
                ob = bpy.context.active_object
                ob.data.materials.append(mt["plate"])
                bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.05, depth=0.03, location=(tx + 0.01, ty, 0.81))
                ob = bpy.context.active_object
                ob.data.materials.append(mt["food"])
        self.tables.append(Vector((x, y, 0)))

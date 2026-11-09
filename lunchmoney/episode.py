"""3D staging of the episode: builds a scene (location, cast, animation, one handheld camera per shot) on the
timeline from episode_plan. render_episode.py renders frame ranges of the shots."""
import math
import random

import bpy
from mathutils import Vector

import act as A
import human as H
import locations as L
import wardrobe as W
from episode_plan import LINES, SCENES

F = A.F


def V(*a):
    return Vector(a)


class Stage:
    def __init__(self, plan):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = bpy.context.scene
        sc.render.fps = 24
        self.plan = plan
        self.n = plan.frames
        sc.frame_start, sc.frame_end = 1, self.n
        self.actors = {}
        self.cams = {}
        self.r = random.Random(hash(plan.name) % 1000)

    # ---------------------------------------------------------------- cast
    def main(self, name, pos, yaw=0.0):
        a = A.Actor(W.build(name), pos, yaw, seed=hash(name) % 100)
        a.stand(1)
        self.actors[name] = a
        return a

    def extra(self, name, seed, pos, yaw=0.0, child=0.6, outfit=None):
        e = W.extra(name, seed, child=child)
        if outfit:
            e["outfit"] = outfit
        h = H.Human(name, e["spec"], e["outfit"])
        a = A.Actor(h, pos, yaw, seed=seed)
        a.stand(1)
        self.actors[name] = a
        return a

    def head(self, name, dz=1.6):
        a = self.actors[name]
        return (a.pos.x, a.pos.y, a.pos.z + dz)

    # ---------------------------------------------------------------- dialogue
    def say(self, lid, to=None, gesture=False, listeners=None):
        t0, t1 = self.plan.cues[lid]
        who = LINES[lid]["who"]
        a = self.actors.get(who)
        if a is not None:
            a.lipsync(LINES[lid]["env"], t0)
            if to:
                a.look(F(t0 - 0.25), F(t0 + 0.1), self.head(to))
            if gesture:
                a.gesture(F(t0 + 0.25), F(t1 - 0.15), "r", energy=0.8)
        for ln in listeners or []:
            if ln in self.actors and ln != who and a is not None:
                self.actors[ln].look(F(t0 - 0.1 + 0.08 * self.r.random()), F(t0 + 0.35), self.head(who))
        return t0, t1

    # ---------------------------------------------------------------- finish
    def finish(self):
        for a in self.actors.values():
            a.idle(1, self.n, amp=0.7)
            a.blinks(1, self.n)
            A.fix_quaternions(a.h.arm)

    def cam(self, sid, lens=20, fstop=2.8):
        c = A.HandheldCam(f"cam_{sid}", lens=lens, fstop=fstop)
        self.cams[sid] = c
        return c

    def cam_for(self, f):
        t = (f - 1) / 24
        for sid, a, b in self.plan.shots:
            if a <= t < b:
                return self.cams[sid].cam
        return self.cams[self.plan.shots[-1][0]].cam


# ============================================================================ scene 1: street

def build_s1(plan):
    st = Stage(plan)
    L.Street()
    c = plan.cues
    john = st.main("john", (-5.5, 7.4, 0))
    bob = st.main("bob", (-4.15, 6.5, 0))
    maxim = st.main("maxim", (-2.9, 7.0, 0))
    karim = st.main("karim", (-4.8, 5.0, 0))
    artem = st.main("artem", (-4.1, 4.55, 0))
    f0 = st.extra("friend0", 71, (-2.35, 7.85, 0), child=0.3)
    f1 = st.extra("friend1", 72, (-2.3, 6.15, 0), child=0.3)
    k1 = st.extra("yardkid1", 91, (0.0, 18.4, 0), child=0.55)
    k2 = st.extra("yardkid2", 92, (1.1, 18.9, 0), child=0.55)
    k3 = st.extra("yardkid3", 93, (5.5, -8.0, 0), child=0.55)
    for a, tgt in ((john, bob), (bob, maxim), (maxim, bob), (karim, bob), (artem, bob), (f0, bob), (f1, bob),
                   (k1, k2), (k2, k1)):
        yaw = A.yaw_to(a.pos, tgt.pos)
        a.yaw = yaw
        a.h.place(1, a.pos, yaw)
    # John leans on the school wall, hands in pockets
    john.h.arm.rotation_euler = (math.radians(-5), 0, math.radians(john.yaw))
    john.h.arm.keyframe_insert("rotation_euler", frame=1)
    john.pockets(1)
    karim.pockets(1)
    artem.pockets(1, "l")
    k3.walk(F(2.0), F(16.0), (5.6, 14.0, 0))
    k1.gesture(F(4.0), F(7.0), "r", 0.6)
    k2.gesture(F(9.0), F(12.0), "r", 0.6)
    # dialogue
    crowd = ["maxim", "friend0", "friend1", "karim", "artem", "john"]
    st.say("s1_01", to="john", listeners=crowd)
    st.say("s1_02", to="bob", listeners=["bob", "maxim"])
    st.say("s1_03", to="john", gesture=True, listeners=["maxim", "karim", "artem"])
    st.say("s1_04", to="bob", listeners=["bob"])
    st.say("s1_05", to="john", gesture=True, listeners=["maxim", "friend0", "friend1"])
    st.say("s1_06", to="bob", listeners=["bob", "john", "friend0"])
    t0, t1 = st.say("s1_07", to="maxim", listeners=["maxim", "bob", "friend0", "friend1"])
    # John pushes off the wall towards Maxim on "Я не тебе вопрос задавал"
    john.h.arm.keyframe_insert("rotation_euler", frame=F(t0 - 0.6))
    john.h.arm.location = john.pos
    john.h.arm.keyframe_insert("location", frame=F(t0 - 0.6))
    newp = john.pos + (maxim.pos - john.pos).normalized() * 0.55
    john.yaw = A.yaw_to(newp, maxim.pos)
    john.h.arm.rotation_euler = (0, 0, math.radians(john.yaw))
    john.h.arm.keyframe_insert("rotation_euler", frame=F(t0 - 0.1))
    john.h.arm.location = newp
    john.h.arm.keyframe_insert("location", frame=F(t0 - 0.1))
    john.pos = newp
    maxim.expr(F(t1), eyebrows_left_inner_up=0.0, eyebrows_right_inner_up=0.0)
    maxim.expr(F(t1 + 0.3), eyebrows_left_inner_up=0.5, eyebrows_right_inner_up=0.5)
    # Bob calms John: hand on his shoulder
    b0, b1 = st.say("s1_08", to="john", listeners=["john", "maxim"])
    bob.arm("l", F(b0), 0, 38, 0)
    bob.arm("l", F(b0 + 0.6), 55, 18, 25, out=-10)
    bob.arm("l", F(b1 - 0.3), 55, 18, 25, out=-10)
    bob.arm("l", F(b1 + 0.4), 0, 38, 0)
    st.say("s1_09", to="bob", listeners=["bob"])
    st.say("s1_10", to="maxim", gesture=True, listeners=["maxim", "john"])
    st.say("s1_11", to="bob", listeners=["bob"])
    # Bob adjusts the fur hat and zips up the coat
    th = plan.ev["hat"]
    bob.arm("r", F(th), 0, 38, 0)
    bob.arm("r", F(th + 0.5), 75, 10, 125, out=10)
    bob.arm("r", F(th + 1.0), 75, 10, 125, out=10)
    bob.arm("r", F(th + 1.3), 35, 30, 70)
    bob.arm("l", F(th + 1.3), 35, 30, 70)
    bob.arm("r", F(th + 2.0), 30, 32, 60)
    bob.arm("l", F(th + 2.0), 30, 32, 60)
    bob.arm("r", F(th + 2.4), 0, 38, 0)
    bob.arm("l", F(th + 2.4), 0, 38, 0)
    bob.look(F(th), F(th + 0.3), (bob.pos.x - 0.5, bob.pos.y - 1.5, 0.9))
    st.say("s1_12", to="bob", listeners=["bob", "artem"])
    st.say("s1_13", to="karim", listeners=["karim", "artem"])
    # the three leave along the school wall, past the camera
    tl = plan.ev["leave"]
    for i, a in enumerate((bob, karim, artem)):
        dest = (-3.4 - 0.6 * i, -12.0 - 0.8 * i, 0)
        a.walk(F(tl + 0.15 * i), F(tl + 12.0 + 0.2 * i), dest)
    st.say("s1_14", to="bob")
    st.say("s1_15", to="artem")
    john.look(F(tl + 0.5), F(tl + 1.2), (-3.5, -2.0, 1.6))
    maxim.look(F(tl + 0.8), F(tl + 1.5), (-3.5, -2.0, 1.6))
    st.finish()
    # ---------------------------------------------------------------- cameras
    cu = plan.cues
    J = V(-5.5, 7.4, 1.55)
    B = V(-4.15, 6.5, 1.7)
    M = V(-2.9, 7.0, 1.5)
    c = st.cam("1A", 20)
    c.at(1, (0.6, -1.2, 1.66), (-4.2, 6.6, 1.45), B)
    c.at(F(cu["s1_01"][1]), (-0.4, 1.9, 1.63), (-4.4, 6.9, 1.5), B)
    c.at(F(cu["s1_02"][0] + 0.15), (-0.5, 2.1, 1.63), (-5.2, 7.3, 1.52), J)
    c.at(F(cu["s1_03"][0] + 0.2), (-0.6, 2.3, 1.63), (-4.2, 6.6, 1.62), B)
    c.at(F(cu["s1_04"][0] + 0.15), (-0.7, 2.5, 1.63), (-5.3, 7.3, 1.52), J)
    c.at(F(cu["s1_05"][0] + 0.2), (-0.9, 2.8, 1.63), (-4.1, 6.6, 1.64), B)
    c.at(F(cu["s1_05"][1] + 0.25), (-1.3, 3.6, 1.62), (-4.0, 6.7, 1.62), B)
    c.shake(1, F(cu["s1_05"][1] + 0.3), 0.012)
    c = st.cam("1B", 26)
    t = cu["s1_06"][0]
    c.at(F(t - 0.4), (-1.7, 5.4, 1.58), (-2.9, 7.0, 1.48), M)
    c.at(F(cu["s1_07"][0] - 0.35), (-1.75, 5.5, 1.58), (-2.9, 7.0, 1.48), M)
    c.at(F(cu["s1_07"][0] - 0.05), (-1.8, 5.6, 1.6), (-4.9, 7.25, 1.55), V(-4.95, 7.25, 1.55))
    c.at(F(cu["s1_07"][1] + 0.6), (-1.9, 5.75, 1.6), (-4.9, 7.25, 1.55), V(-4.95, 7.25, 1.55))
    c.shake(F(t - 0.5), F(cu["s1_07"][1] + 0.7), 0.014)
    c = st.cam("1C", 24)
    t = cu["s1_08"][0]
    c.at(F(t - 1.0), (-3.2, 9.2, 1.62), (-4.6, 6.8, 1.6), V(-4.6, 6.9, 1.6))
    c.at(F(cu["s1_09"][1] + 0.3), (-3.0, 9.0, 1.6), (-4.6, 6.8, 1.6), V(-4.6, 6.9, 1.6))
    c.shake(F(t - 1.1), F(cu["s1_09"][1] + 0.4), 0.012)
    c = st.cam("1D", 26)
    t = cu["s1_10"][0]
    c.at(F(t - 0.4), (-2.35, 7.75, 1.6), (-4.15, 6.5, 1.66), B)
    c.at(F(plan.ev["hat"] + 2.4), (-2.3, 7.65, 1.58), (-4.15, 6.5, 1.6), B)
    c.shake(F(t - 0.5), F(plan.ev["hat"] + 2.5), 0.012)
    c = st.cam("1E", 20)
    t = cu["s1_12"][0]
    c.at(F(t - 0.3), (-1.4, -3.6, 1.55), (-4.4, 5.5, 1.45), V(-4.4, 5.5, 1.45))
    c.at(F(plan.ev["leave"] + 3.0), (-1.4, -3.8, 1.55), (-3.9, 2.5, 1.5), V(-3.9, 2.5, 1.5))
    c.at(F(plan.ev["leave"] + 7.5), (-1.3, -4.1, 1.55), (-4.6, -6.0, 1.5), V(-5.3, 7.2, 1.55))
    c.at(F(plan.length), (-1.3, -4.2, 1.55), (-4.8, 4.5, 1.5), V(-5.3, 7.2, 1.55))
    c.shake(F(t - 0.4), st.n, 0.012)
    return st


# ============================================================================ hall helpers

def hide_entrance_doors():
    for ob in bpy.data.objects:
        if ob.name.startswith("hdoor"):
            ob.hide_render = True


def seat_kids(st, hall, ti, layout, seeds, names=None):
    """Seat kids at table ti. layout: list of (dx, side) side=-1 south bench (facing north), +1 north bench."""
    tx, ty, _ = hall.tables[ti]
    out = []
    for k, (dx, side) in enumerate(layout):
        name = names[k] if names and k < len(names) and names[k] else f"t{ti}k{k}"
        a = st.extra(name, seeds[k], (tx + dx, ty + side * 0.62, 0), child=0.62)
        yaw = 180.0 if side < 0 else 0.0
        A.seat(a, 1, (tx + dx, ty + side * 0.66), 0.46, yaw)
        a.seated = True
        out.append(a)
    return out


def eat(st, kids, f0, f1):
    for a in kids:
        r = random.Random(a.seed)
        f = f0 + r.randint(0, 40)
        while f < f1 - 30:
            a.arm("r", f, 42, 30, 62, out=-8)
            a.arm("r", f + 10, 70, 18, 120, out=-4)
            a.arm("r", f + 22, 42, 30, 62, out=-8)
            f += r.randint(70, 140)


def stand_up(a, f):
    h = a.h
    h.arm.keyframe_insert("location", frame=f)
    for s in ("l", "r"):
        h.rot(f"thigh_{s}", f, (-86, 0, 0))
        h.rot(f"calf_{s}", f, (84, 0, 0))
    h.arm.location = (a.pos.x, a.pos.y + (0.35 if a.yaw == 180.0 else -0.35), 0)
    h.arm.keyframe_insert("location", frame=f + 14)
    for s in ("l", "r"):
        h.rot(f"thigh_{s}", f + 14, (0, 0, 0))
        h.rot(f"calf_{s}", f + 14, (0, 0, 0))
        h.rot(f"foot_{s}", f + 14, (0, 0, 0))
    a.arm("l", f + 14, 0, 38, 0)
    a.arm("r", f + 14, 0, 38, 0)
    a.pos = Vector(h.arm.location)


def hall_crowd(st, seeds, spots, t0=0.0, t1=10.0):
    for i, ((p0, p1), sd) in enumerate(zip(spots, seeds)):
        a = st.extra(f"walker{i}", sd, p0, A.yaw_to(p0, p1), child=0.6)
        a.walk(F(t0 + 0.6 * i), F(t0 + 0.6 * i + (Vector(p1) - Vector(p0)).length / 1.2 * 1.0), p1)


# ============================================================================ scene 2: entering the main school

def build_s2(plan):
    st = Stage(plan)
    hall = L.Hall()
    hide_entrance_doors()
    te = plan.ev["enter"]
    bob = st.main("bob", (0.0, -9.2, 0), 0)
    karim = st.main("karim", (-0.6, -9.8, 0), 0)
    artem = st.main("artem", (0.6, -9.9, 0), 0)
    for a in (bob, karim, artem):
        a.yaw = 180.0
        a.h.place(1, a.pos, 180.0)
    bob.walk(F(te), F(te + 4.2), (0.0, -3.4, 0))
    karim.walk(F(te + 0.2), F(te + 4.5), (-0.8, -3.9, 0))
    artem.walk(F(te + 0.1), F(te + 4.4), (0.9, -4.0, 0))
    hall_crowd(st, [101, 102, 103, 104, 105, 106, 107],
               [((-3.0, 2.0, 0), (-2.0, 12.0, 0)), ((3.0, -2.0, 0), (3.6, 5.5, 0)), ((-1.0, -5.0, 0), (1.5, 13.0, 0)),
                ((2.0, 3.0, 0), (-1.5, 16.0, 0)), ((-3.5, -4.0, 0), (-3.2, 9.0, 0)), ((1.0, 0.0, 0), (2.5, 18.0, 0)),
                ((-2.0, -1.0, 0), (0.5, 20.0, 0))], 0.3, 10.0)
    # some kids already sitting at tables (they become the tables of scene 3)
    seat_kids(st, hall, 0, [(-0.45, -1), (0.45, -1), (-0.45, 1), (0.45, 1)], [111, 112, 113, 114])
    seat_kids(st, hall, 1, [(-0.4, -1), (0.4, -1), (0.0, 1)], [121, 122, 123])
    seat_kids(st, hall, 2, [(-0.5, -1), (0.0, -1), (0.5, -1), (-0.3, 1), (0.3, 1)], [131, 132, 133, 134, 135])
    st.say("s2_01", to="bob", listeners=["bob", "karim"])
    st.say("s2_02", to="bob", listeners=["bob", "artem"])
    st.say("s2_03")
    tl = plan.ev["look"]
    for a in (bob, karim, artem):
        a.look(F(tl), F(tl + 0.5), (-1.0, 14.0, 1.0))
    st.say("s2_04", to="artem", listeners=["karim", "artem"])
    st.say("s2_05", to="bob")
    bob.walk(F(plan.ev["go"]), F(plan.ev["go"] + 3.5), (-1.4, 0.8, 0))
    st.finish()
    c = st.cam("2A", 20)
    c.at(1, (1.3, 3.5, 1.62), (0.0, -7.5, 1.4), V(0.0, -6.5, 1.4))
    c.at(F(te + 1.6), (1.2, 3.2, 1.62), (0.1, -6.0, 1.5), V(0.0, -6.0, 1.5))
    c.shake(1, F(te + 1.7), 0.012)
    c = st.cam("2B", 22)
    t = te + 1.6
    c.at(F(t), (1.0, -0.4, 1.62), (0.0, -5.0, 1.6), V(0.0, -5.0, 1.6))
    c.at(F(plan.cues["s2_03"][1]), (1.1, -0.1, 1.62), (0.0, -3.6, 1.65), V(0.0, -3.6, 1.65))
    c.at(F(plan.ev["look"] + 0.5), (1.4, -1.0, 1.62), (-0.2, -3.6, 1.65), V(0.0, -3.5, 1.65))
    c.at(F(plan.length), (1.6, -1.4, 1.62), (-0.8, 0.5, 1.5), V(-1.0, 0.5, 1.5))
    c.shake(F(t), st.n, 0.012)
    return st


# ============================================================================ scene 3: three tables

def build_s3(plan):
    st = Stage(plan)
    hall = L.Hall()
    hide_entrance_doors()
    k1 = seat_kids(st, hall, 0, [(-0.45, -1), (0.45, -1), (-0.45, 1), (0.45, 1)], [111, 112, 113, 114],
                   ["kid1", "kid2", "t0k2", "t0k3"])
    k2 = seat_kids(st, hall, 1, [(-0.4, -1), (0.4, -1), (0.0, 1)], [121, 122, 123], ["kid3", "t1k1", "t1k2"])
    k3 = seat_kids(st, hall, 2, [(-0.5, -1), (0.0, -1), (0.5, -1), (-0.3, 1), (0.3, 1)], [131, 132, 133, 134, 135],
                   ["t2k0", "kid4", "t2k2", "kid5", "t2k4"])
    k4 = seat_kids(st, hall, 3, [(-0.4, -1), (0.4, 1)], [141, 142])
    eat(st, k1 + k2 + k3 + k4, 1, st.n)
    T = hall.tables
    bob = st.main("bob", (-1.0, 9.5, 0), 0)
    artem = st.main("artem", (-1.6, 9.0, 0), 0)
    karim = st.main("karim", (-0.4, 9.0, 0), 0)
    # table 1: they stand at its east end
    p1 = {"bob": (T[0].x + 1.15, T[0].y - 0.15, 0), "artem": (T[0].x + 1.1, T[0].y + 0.65, 0),
          "karim": (T[0].x + 1.55, T[0].y - 0.75, 0)}
    for n, a in (("bob", bob), ("artem", artem), ("karim", karim)):
        a.walk(F(0.1), F(2.0), p1[n])
        a.turn(F(2.0), F(2.3), A.yaw_to(p1[n], T[0]))
    ally = ["kid1", "kid2", "t0k2", "t0k3"]
    st.say("s3_01", to="kid1", listeners=ally)
    st.say("s3_02", to="bob", listeners=["bob"])
    st.say("s3_03", to="kid2", listeners=ally)
    st.say("s3_04", to="bob")
    for a in k1:
        a.look(F(plan.cues["s3_04"][1]), F(plan.cues["s3_04"][1] + 0.4), st.head("t0k2" if a.h.name != "t0k2" else "kid1", 1.1))
    st.say("s3_05", to="kid2", listeners=ally)
    tp = plan.ev["pay1"]
    for i, a in enumerate(k1):
        A.reach_seated(a, "r", F(tp + 0.25 * i), 10, 6)
        a.look(F(tp + 0.25 * i - 0.2), F(tp + 0.25 * i + 0.1), st.head("artem"))
    A.reach(artem, "r", F(tp + 0.1), 10, 14, fwd=55, down=24, elbow=30)
    artem.arm("r", F(tp + 1.4), 40, 30, 80)
    artem.arm("l", F(tp + 1.4), 40, 30, 80)
    for k in range(5):
        artem.arm("r", F(tp + 1.6 + 0.25 * k), 44 if k % 2 else 38, 30, 85)
    artem.look(F(tp + 1.3), F(tp + 1.6), (artem.pos.x - 0.2, artem.pos.y - 0.3, 1.0))
    st.say("s3_06", to="bob")
    artem.arm("r", F(plan.cues["s3_06"][1] + 0.3), 0, 38, 0)
    artem.arm("l", F(plan.cues["s3_06"][1] + 0.3), 0, 38, 0)
    st.say("s3_07", to="kid1", listeners=ally)
    # table 2
    tw = plan.ev["walk2"]
    p2 = {"bob": (T[1].x + 1.15, T[1].y - 0.1, 0), "artem": (T[1].x + 1.1, T[1].y + 0.7, 0),
          "karim": (T[1].x + 1.5, T[1].y - 0.75, 0)}
    for i, (n, a) in enumerate((("bob", bob), ("artem", artem), ("karim", karim))):
        a.walk(F(tw + 0.1 * i), F(tw + 2.5), p2[n])
        a.turn(F(tw + 2.5), F(tw + 2.8), A.yaw_to(p2[n], T[1]))
    al2 = ["kid3", "t1k1", "t1k2"]
    st.say("s3_08", to="kid3", listeners=al2)
    st.say("s3_09", to="bob")
    st.say("s3_10", to="kid3", listeners=al2)
    tp = plan.ev["pay2"]
    for i, a in enumerate(k2):
        A.reach_seated(a, "r", F(tp + 0.2 * i), 9, 5)
    A.reach(karim, "r", F(tp + 0.1), 9, 10)
    st.say("s3_11", to="bob")
    st.say("s3_12", to="artem")
    # table 3
    tw = plan.ev["walk3"]
    p3 = {"bob": (T[2].x + 1.15, T[2].y - 0.1, 0), "artem": (T[2].x + 1.1, T[2].y + 0.7, 0),
          "karim": (T[2].x + 1.5, T[2].y - 0.8, 0)}
    for i, (n, a) in enumerate((("bob", bob), ("artem", artem), ("karim", karim))):
        a.walk(F(tw + 0.1 * i), F(tw + 2.5), p3[n])
        a.turn(F(tw + 2.5), F(tw + 2.8), A.yaw_to(p3[n], T[2]))
    kid4 = st.actors["kid4"]
    th = plan.ev["hide"]
    kid4.arm("r", F(th), 42, 30, 62, out=-8)
    kid4.arm("r", F(th + 0.5), 20, 30, 115, out=-20)
    kid4.look(F(th), F(th + 0.4), (kid4.pos.x, kid4.pos.y + 0.3, 0.7))
    al3 = ["t2k0", "kid4", "t2k2", "kid5", "t2k4"]
    st.say("s3_13", to="kid4", listeners=al3)
    st.say("s3_14", to="artem")
    st.say("s3_15", to="kid4", listeners=al3)
    tp = plan.ev["pay3"]
    kid4.arm("r", F(tp), 20, 30, 115, out=-20)
    kid4.arm("r", F(tp + 0.5), 75, 22, 25, out=-5)
    kid4.arm("r", F(tp + 1.2), 75, 22, 25, out=-5)
    kid4.arm("r", F(tp + 1.6), 42, 30, 62, out=-8)
    A.reach(karim, "r", F(tp + 0.4), 9, 8)
    st.say("s3_16", to="kid4", listeners=al3)
    kid5 = st.actors["kid5"]
    t0, t1 = st.say("s3_17", to="t2k4")
    kid5.h.rot("spine_02", F(t0 - 0.2), (0, 0, 0))
    kid5.h.rot("spine_02", F(t0 + 0.1), (6, 0, -12))
    kid5.h.rot("spine_02", F(t1 + 0.3), (0, 0, 0))
    st.say("s3_18", to="kid5", listeners=al3)
    st.say("s3_19", to="artem")
    st.say("s3_20", to="kid5", listeners=al3)
    # walking away north-east
    tw = plan.ev["walk4"]
    for i, (a, dest) in enumerate(((bob, (2.6, 21.5, 0)), (artem, (2.0, 22.1, 0)), (karim, (3.2, 21.0, 0)))):
        a.walk(F(tw + 0.1 * i), F(tw + 6.5), dest)
    st.say("s3_21", to="bob")
    st.say("s3_22", to="bob")
    st.say("s3_23", to="artem")
    st.finish()
    # cameras
    cu = plan.cues
    c = st.cam("3A", 20)
    c.at(1, (-0.6, 11.0, 1.62), (-1.3, 14.0, 1.4), V(-1.3, 14.0, 1.4))
    c.at(F(2.2), (-3.9, 12.6, 1.35), (-1.25, 14.0, 1.5), V(-1.25, 13.9, 1.55))
    c.at(F(cu["s3_02"][0]), (-3.95, 12.7, 1.3), (-2.6, 13.4, 1.0), V(-2.85, 13.4, 1.0))
    c.at(F(cu["s3_03"][0] + 0.1), (-3.9, 12.6, 1.35), (-1.25, 14.0, 1.55), V(-1.25, 13.9, 1.6))
    c.at(F(plan.ev["pay1"]), (-3.8, 12.8, 1.3), (-1.8, 14.1, 1.05), V(-1.5, 14.2, 1.1))
    c.at(F(cu["s3_06"][0]), (-3.7, 12.9, 1.35), (-1.3, 14.6, 1.45), V(-1.3, 14.65, 1.5))
    c.at(F(cu["s3_07"][1] + 0.3), (-3.6, 13.0, 1.4), (-1.25, 13.9, 1.55), V(-1.25, 13.9, 1.6))
    c.shake(1, F(cu["s3_07"][1] + 0.4), 0.012)
    c = st.cam("3B", 22)
    t = cu["s3_07"][1] + 0.3
    c.at(F(t), (-0.6, 12.2, 1.6), (1.0, 13.0, 1.5), V(1.0, 13.0, 1.5))
    c.at(F(plan.ev["walk2"] + 2.6), (0.3, 12.6, 1.55), (2.95, 14.4, 1.55), V(2.95, 14.4, 1.6))
    c.at(F(plan.ev["pay2"]), (0.4, 12.7, 1.5), (2.3, 14.4, 1.1), V(2.3, 14.4, 1.1))
    c.at(F(cu["s3_12"][1] + 0.2), (0.5, 12.8, 1.55), (2.95, 14.4, 1.55), V(2.95, 14.4, 1.6))
    c.shake(F(t), F(cu["s3_12"][1] + 0.3), 0.013)
    c = st.cam("3C", 26)
    t = cu["s3_12"][1] + 0.2
    c.at(F(t), (-2.45, 17.75, 1.2), (-1.0, 18.9, 1.5), V(-1.05, 18.9, 1.55))
    c.at(F(plan.ev["hide"] + 0.6), (-2.5, 17.7, 1.15), (-2.2, 18.5, 0.85), V(-2.2, 18.4, 0.9))
    c.at(F(cu["s3_13"][0] + 0.1), (-2.45, 17.75, 1.2), (-1.0, 18.9, 1.55), V(-1.05, 18.9, 1.6))
    c.at(F(plan.ev["pay3"] + 0.5), (-2.4, 17.8, 1.2), (-1.5, 18.7, 1.1), V(-1.6, 18.7, 1.1))
    c.at(F(cu["s3_16"][1] + 0.2), (-2.4, 17.8, 1.2), (-1.0, 18.9, 1.55), V(-1.05, 18.9, 1.6))
    c.shake(F(t), F(cu["s3_16"][1] + 0.6), 0.012)
    c = st.cam("3D", 30)
    t = cu["s3_17"][0] - 0.15
    c.at(F(t), (-3.25, 20.5, 1.2), (-2.5, 19.6, 1.05), V(-2.5, 19.6, 1.05))
    c.at(F(cu["s3_17"][1] + 0.1), (-3.2, 20.45, 1.2), (-2.5, 19.6, 1.05), V(-2.5, 19.6, 1.05))
    c.at(F(cu["s3_18"][0]), (-3.25, 20.5, 1.3), (-1.3, 19.6, 1.6), V(-1.15, 19.6, 1.65))
    c.at(F(cu["s3_19"][0]), (-3.2, 20.45, 1.2), (-2.5, 19.6, 1.05), V(-2.5, 19.6, 1.05))
    c.at(F(cu["s3_20"][0]), (-3.25, 20.5, 1.3), (-1.2, 18.95, 1.6), V(-1.05, 18.9, 1.65))
    c.shake(F(t), F(cu["s3_20"][1] + 0.4), 0.012)
    c = st.cam("3E", 22)
    t = cu["s3_20"][1] + 0.3
    c.at(F(t), (0.4, 23.6, 1.6), (-0.6, 19.0, 1.55), V(-0.6, 19.0, 1.55))
    c.at(F(plan.length), (1.0, 24.0, 1.6), (2.4, 21.5, 1.6), V(2.4, 21.6, 1.6))
    c.shake(F(t), st.n, 0.013)
    return st


# ============================================================================ scene 4: by the lockers

def build_s4(plan):
    st = Stage(plan)
    hall = L.Hall()
    hide_entrance_doors()
    W_ = W
    hood = W_.extra("hoodie", 201, child=0.55)
    hood["outfit"] = [W_.garment("male_casualsuit02", top=(0.5, 0.5, 0.52), top_desat=1.0), W_.shoes("shoes02")]
    hb = H.Human("hoodie", hood["spec"], hood["outfit"])
    hoodie = A.Actor(hb, (-4.15, 7.0, 0), 90.0, seed=201)
    hoodie.stand(1)
    st.actors["hoodie"] = hoodie
    o1 = st.extra("wall1", 211, (-4.2, 7.85, 0), 100, child=0.6)
    o2 = st.extra("wall2", 212, (-4.1, 6.15, 0), 80, child=0.6)
    o3 = st.extra("wall3", 213, (-3.75, 8.6, 0), 120, child=0.6)
    artem = st.main("artem", (-3.25, 7.15, 0), -90)
    karim = st.main("karim", (-3.35, 6.3, 0), -70)
    bob = st.main("bob", (-1.0, 12.5, 0), 180)
    for a, t in ((hoodie, artem), (o1, artem), (o2, karim), (o3, artem), (artem, hoodie), (karim, hoodie)):
        a.yaw = A.yaw_to(a.pos, t.pos)
        a.h.place(1, a.pos, a.yaw)
    hall_crowd(st, [221, 222, 223], [((2.0, 1.0, 0), (2.5, 14.0, 0)), ((3.2, 12.0, 0), (2.8, -4.0, 0)),
                                     ((-0.5, -4.0, 0), (0.5, 16.0, 0))], 0.5, 30.0)
    seat_kids(st, hall, 0, [(-0.45, -1), (0.45, 1)], [111, 113])
    al = ["hoodie", "wall1", "wall2", "wall3", "karim", "artem"]
    st.say("s4_01", to="hoodie", gesture=True, listeners=al)
    st.say("s4_02", to="artem", listeners=al)
    st.say("s4_03", to="bob")
    tb = plan.ev["bob_in"]
    bpos = (-2.9, 7.65, 0)
    bob.walk(F(tb), F(tb + 2.6), bpos)
    bob.turn(F(tb + 2.6), F(tb + 2.9), A.yaw_to(bpos, hoodie.pos))
    karim.look(F(tb), F(tb + 0.4), (-1.0, 11.0, 1.6))
    st.say("s4_04", to="hoodie", listeners=al)
    st.say("s4_05", to="bob")
    st.say("s4_06", to="hoodie", gesture=True, listeners=al)
    st.say("s4_07", to="bob")
    st.say("s4_08", to="hoodie")
    st.say("s4_09", to="bob")
    t0, t1 = st.say("s4_10", to="hoodie", listeners=["hoodie"])
    artem.walk(F(t0), F(t0 + 0.5), (-3.55, 7.1, 0))
    st.say("s4_11", to="artem", listeners=["artem"])
    st.say("s4_12", to="bob", listeners=al)
    hoodie.gesture(F(plan.cues["s4_12"][0]), F(plan.cues["s4_12"][1]), "r", 1.2)
    # onlookers turn around
    hall_kids = [a for n, a in st.actors.items() if n.startswith("walker") or n.startswith("t0k")]
    for i, a in enumerate(hall_kids):
        a.look(F(plan.cues["s4_12"][0] + 0.2 * i), F(plan.cues["s4_12"][0] + 0.2 * i + 0.5), (-3.8, 7.0, 1.4))
    st.say("s4_13", to="karim", listeners=["karim", "artem"])
    # Karim and Artem take him to a locker further down, stuff him in, take the wallet, slam the door
    tk = plan.ev["take"]
    door_i = 5
    door = hall.locker_doors[door_i]
    ly = door.location.y - 0.2
    lx = hall.locker_x
    hoodie.walk(F(tk + 0.3), F(tk + 2.4), (lx + 0.35, ly, 0))
    artem.walk(F(tk), F(tk + 2.4), (lx + 0.75, ly + 0.55, 0))
    karim.walk(F(tk + 0.1), F(tk + 2.4), (lx + 0.85, ly - 0.45, 0))
    A.reach(karim, "l", F(tk + 0.1), 8, 30, fwd=50, down=30, elbow=30)
    door.rotation_euler = (0, 0, 0)
    door.keyframe_insert("rotation_euler", frame=F(tk + 2.4))
    door.rotation_euler = (0, 0, math.radians(100))
    door.keyframe_insert("rotation_euler", frame=F(tk + 2.9))
    door.keyframe_insert("rotation_euler", frame=F(tk + 5.0))
    door.rotation_euler = (0, 0, 0)
    door.keyframe_insert("rotation_euler", frame=F(tk + 5.3))
    # pushed inside, turned around
    hb.arm.keyframe_insert("location", frame=F(tk + 2.6))
    hb.arm.keyframe_insert("rotation_euler", frame=F(tk + 2.6))
    hb.arm.location = (lx - 0.25, ly, 0.1)
    hb.arm.rotation_euler = (0, 0, math.radians(90))
    hb.arm.keyframe_insert("location", frame=F(tk + 3.3))
    hb.arm.keyframe_insert("rotation_euler", frame=F(tk + 3.3))
    A.reach(karim, "r", F(tk + 2.5), 8, 6, fwd=70, down=15, elbow=10)
    A.reach(karim, "l", F(tk + 2.5), 8, 6, fwd=70, down=15, elbow=10)
    A.reach(artem, "r", F(tk + 3.6), 8, 6, fwd=60, down=22, elbow=25)
    hoodie.arm("l", F(tk + 2.7), 40, 20, 60)
    hoodie.arm("r", F(tk + 2.7), 40, 20, 60)
    # Bob waits in the foreground and stares the others down
    for i, a in enumerate((o1, o2, o3)):
        a.look(F(tk + 0.8 + 0.2 * i), F(tk + 1.3 + 0.2 * i), (lx + 0.4, ly, 1.3))
    bob.look(F(tk + 1.0), F(tk + 1.5), st.head("wall2", 1.5))
    bob.look(F(tk + 3.5), F(tk + 4.0), st.head("wall1", 1.5))
    bob.pockets(F(tk + 1.0), "l")
    # they come back
    tb2 = plan.ev["back"]
    artem.walk(F(tb2), F(tb2 + 2.4), (-3.4, 7.0, 0))
    karim.walk(F(tb2 + 0.1), F(tb2 + 2.5), (-3.3, 6.35, 0))
    karim.turn(F(tb2 + 2.5), F(tb2 + 2.8), A.yaw_to((-3.3, 6.35), bpos))
    artem.turn(F(tb2 + 2.4), F(tb2 + 2.7), A.yaw_to((-3.4, 7.0), bpos))
    st.say("s4_14", to="bob", listeners=["bob"])
    st.say("s4_15", to="karim", listeners=["karim"])
    st.say("s4_16", to="bob", listeners=["bob", "artem"])
    st.say("s4_17", to="bob")
    st.finish()
    cu = plan.cues
    H_ = V(-4.15, 7.0, 1.45)
    c = st.cam("4A", 22)
    c.at(1, (-1.4, 5.6, 1.6), (-3.9, 7.0, 1.45), H_)
    c.at(F(cu["s4_02"][0]), (-1.6, 5.8, 1.58), (-4.1, 7.0, 1.42), H_)
    c.at(F(tb + 1.5), (-1.3, 6.1, 1.6), (-3.2, 7.4, 1.55), H_)
    c.at(F(cu["s4_04"][0]), (-1.5, 6.3, 1.6), (-3.1, 7.55, 1.62), V(-2.9, 7.65, 1.7))
    c.at(F(cu["s4_05"][0]), (-1.6, 6.4, 1.58), (-4.1, 7.0, 1.42), H_)
    c.at(F(cu["s4_06"][0]), (-1.6, 6.5, 1.6), (-3.0, 7.6, 1.66), V(-2.9, 7.65, 1.7))
    c.at(F(cu["s4_07"][0]), (-1.7, 6.6, 1.58), (-4.1, 7.0, 1.42), H_)
    c.at(F(cu["s4_08"][0]), (-1.7, 6.7, 1.6), (-3.0, 7.6, 1.66), V(-2.9, 7.65, 1.7))
    c.at(F(cu["s4_09"][0]), (-1.8, 6.7, 1.58), (-4.1, 7.0, 1.42), H_)
    c.shake(1, F(cu["s4_09"][1] + 0.3), 0.012)
    c = st.cam("4B", 28)
    t = cu["s4_09"][1] + 0.2
    c.at(F(t), (-2.55, 8.25, 1.62), (-4.1, 6.95, 1.45), H_)
    c.at(F(cu["s4_11"][0]), (-2.6, 8.3, 1.62), (-3.0, 7.6, 1.66), V(-2.9, 7.65, 1.7))
    c.at(F(cu["s4_12"][0]), (-2.55, 8.25, 1.62), (-4.1, 6.95, 1.45), H_)
    c.at(F(cu["s4_12"][1] + 0.3), (-2.5, 8.35, 1.62), (-4.1, 6.95, 1.45), H_)
    c.shake(F(t), F(cu["s4_12"][1] + 0.4), 0.016)
    c = st.cam("4C", 20)
    t = cu["s4_12"][1] + 0.3
    c.at(F(t), (-0.5, 10.6, 1.58), (-3.4, 6.2, 1.5), V(-2.9, 7.65, 1.7))
    c.at(F(tk + 1.5), (-0.6, 10.4, 1.58), (-4.0, 2.6, 1.3), V(lx + 0.4, ly, 1.3))
    c.at(F(tb2), (-0.65, 10.3, 1.58), (-4.0, 2.4, 1.3), V(lx + 0.4, ly, 1.3))
    c.at(F(tb2 + 2.6), (-0.7, 10.2, 1.58), (-3.3, 6.3, 1.55), V(-3.3, 6.5, 1.6))
    c.shake(F(t), F(tb2 + 2.7), 0.012)
    c = st.cam("4D", 26)
    t = tb2 + 2.6
    c.at(F(t), (-1.5, 5.4, 1.6), (-3.1, 7.2, 1.62), V(-3.1, 7.2, 1.62))
    c.at(F(plan.length), (-1.4, 5.3, 1.6), (-3.0, 7.4, 1.64), V(-3.0, 7.4, 1.64))
    c.shake(F(t), st.n, 0.012)
    return st


# ============================================================================ scene 5: everybody understood

def build_s5(plan):
    st = Stage(plan)
    hall = L.Hall()
    hide_entrance_doors()
    k1 = seat_kids(st, hall, 0, [(-0.45, -1), (0.45, -1), (-0.45, 1)], [111, 112, 113])
    k3 = seat_kids(st, hall, 2, [(-0.5, -1), (0.5, -1), (0.3, 1)], [131, 133, 135])
    k4 = seat_kids(st, hall, 3, [(-0.4, -1), (0.4, -1), (0.0, 1)], [141, 142, 143], ["kid6", "kid7", "t3k2"])
    k5 = seat_kids(st, hall, 4, [(-0.45, -1), (0.45, -1), (-0.45, 1), (0.45, 1)], [151, 152, 153, 154])
    eat(st, k1 + k3 + k5, 1, st.n)
    bob = st.main("bob", (-2.6, 9.0, 0), 0)
    karim = st.main("karim", (-3.1, 8.4, 0), 0)
    artem = st.main("artem", (-2.1, 8.3, 0), 0)
    T = hall.tables
    dest = {"bob": (T[4].x + 1.15, T[4].y - 0.1, 0), "artem": (T[4].x + 1.1, T[4].y + 0.7, 0),
            "karim": (T[4].x + 1.5, T[4].y - 0.8, 0)}
    ta = plan.ev["arrive"]
    for i, (n, a) in enumerate((("bob", bob), ("karim", karim), ("artem", artem))):
        a.walk(F(plan.ev["walk"] + 0.15 * i), F(ta), (dest[n][0] - 1.6, dest[n][1] - 7.0, 0))
        a.walk(F(ta) + 1, F(ta + 3.0), dest[n])
        a.turn(F(ta + 3.0), F(ta + 3.3), A.yaw_to(dest[n], T[4]))
    # whispering kids in the foreground watch Bob pass
    kid6, kid7 = st.actors["kid6"], st.actors["kid7"]
    st.say("s5_01", to="kid7")
    kid6.h.rot("spine_02", F(plan.cues["s5_01"][0] - 0.2), (0, 0, 0))
    kid6.h.rot("spine_02", F(plan.cues["s5_01"][0] + 0.1), (8, 0, 10))
    st.say("s5_02", to="kid6")
    st.say("s5_03", to="kid7")
    kid6.h.rot("spine_02", F(plan.cues["s5_03"][1] + 0.3), (0, 0, 0))
    for a in k4 + k3:
        a.look(F(plan.ev["walk"] + 0.5), F(plan.ev["walk"] + 1.2), (-1.0, 13.0, 1.7))
    # silent payment
    al = [n for n in st.actors if n.startswith("t4")]
    st.say("s5_04", to="t4k0", listeners=al)
    tp = plan.ev["pay"]
    for i, a in enumerate(k5):
        A.reach_seated(a, "r", F(tp + 0.3 * i), 10, 6)
        a.look(F(tp + 0.3 * i - 0.2), F(tp + 0.3 * i + 0.1), st.head("karim"))
    A.reach(karim, "r", F(tp + 0.2), 10, 18)
    st.say("s5_05", to="bob")
    st.say("s5_06", to="bob", gesture=True)
    st.say("s5_07", to="artem")
    # bell: kids get up and leave
    tbl = plan.ev["bell"]
    leavers = k5 + k1[:2] + k3[:2]
    for i, a in enumerate(leavers):
        f = F(tbl + 0.4 + 0.25 * i)
        stand_up(a, f)
        a.walk(f + 16, f + 16 + F(5.0), (a.pos.x + random.Random(i).uniform(-1, 1), -6.0, 0))
    st.say("s5_08", to="artem")
    st.say("s5_09", to="bob")
    st.say("s5_10", to="karim")
    te = plan.ev["exit"]
    for i, a in enumerate((bob, karim, artem)):
        a.walk(F(te + 0.15 * i), F(te + 8.0), (-1.0 + 0.6 * i, 2.0 - 0.5 * i, 0))
    st.finish()
    cu = plan.cues
    c = st.cam("5A", 28)
    c.at(1, (3.35, 18.55, 1.1), (2.2, 19.25, 1.05), V(2.2, 19.2, 1.05))
    c.at(F(plan.cues["s5_03"][1] + 0.4), (3.3, 18.5, 1.1), (1.0, 18.0, 1.3), V(2.2, 19.2, 1.05))
    c.shake(1, F(plan.cues["s5_03"][1] + 0.6), 0.01)
    c = st.cam("5B", 22)
    t = plan.shots[1][1]
    c.at(F(t), (-2.4, 22.0, 1.55), (0.95, 23.4, 1.55), V(0.95, 23.4, 1.6))
    c.at(F(tp), (-2.3, 22.1, 1.5), (0.2, 23.5, 1.1), V(0.2, 23.5, 1.1))
    c.at(F(cu["s5_05"][0]), (-2.3, 22.1, 1.55), (1.0, 23.2, 1.55), V(1.0, 23.2, 1.6))
    c.at(F(cu["s5_07"][1] + 0.6), (-2.2, 22.2, 1.55), (0.95, 23.4, 1.55), V(0.95, 23.4, 1.6))
    c.shake(F(t), F(cu["s5_07"][1] + 0.7), 0.012)
    c = st.cam("5C", 20)
    t = plan.shots[2][1]
    c.at(F(t), (0.6, 25.3, 1.7), (0.4, 18.0, 1.3), V(0.6, 20.0, 1.3))
    c.at(F(te + 3.0), (0.6, 25.2, 1.7), (-0.4, 10.0, 1.3), V(0.0, 14.0, 1.3))
    c.at(F(plan.length), (0.5, 25.0, 1.7), (-0.6, 14.0, 1.0), V(-0.6, 14.0, 1.0))
    c.shake(F(t), st.n, 0.01)
    return st


BUILDERS = {"s1": build_s1, "s2": build_s2, "s3": build_s3, "s4": build_s4, "s5": build_s5}


def build(scene):
    plan = SCENES[scene]()
    return BUILDERS[scene](plan)

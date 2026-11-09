"""3D staging of the episode: builds a scene (location, cast, acting intents, one handheld camera per shot) on the
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


def fwd_of(yaw):
    return Vector((math.sin(math.radians(yaw)), -math.cos(math.radians(yaw)), 0))


class Stage:
    def __init__(self, plan):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        A.Actor.REG.clear()
        sc = bpy.context.scene
        sc.render.fps = 24
        self.plan = plan
        self.n = plan.frames
        sc.frame_start, sc.frame_end = 1, self.n
        self.actors = {}
        self.cams = {}
        self.r = random.Random(hash(plan.name) % 1000)
        self.props = []

    # ---------------------------------------------------------------- cast
    def main(self, name, pos, yaw=0.0, pose="hang", stance="even"):
        a = A.Actor(W.build(name), pos, yaw, seed=sum(map(ord, name)))
        a.pose(1, pose) if pose != "hang" else None
        a.stance(1, stance) if stance != "even" else None
        self.actors[name] = a
        return a

    def extra(self, name, seed, pos, yaw=0.0, child=0.6, outfit=None, pose=None, stance=None):
        e = W.extra(name, seed, child=child)
        if outfit:
            e["outfit"] = outfit
        h = H.Human(name, e["spec"], e["outfit"])
        a = A.Actor(h, pos, yaw, seed=seed)
        r = random.Random(seed)
        a.pose(1, pose or r.choice(["hang", "pockets", "pocket_r", "behind", "hang", "crossed"]))
        a.stance(1, stance or r.choice(["even", "l", "r"]))
        self.actors[name] = a
        return a

    def point(self, target, f):
        if target is None:
            return None
        if isinstance(target, str):
            return self.actors[target].eye_at(f)
        if isinstance(target, tuple) and target and isinstance(target[0], str):
            p = self.actors[target[0]].pos_at(f)
            return Vector((p.x, p.y, p.z + target[1]))
        return Vector(target)

    def face_each_other(self, f, pairs):
        for a, b in pairs:
            A_ = self.actors[a]
            A_.place(f, A_.pos, A.yaw_to(A_.pos, self.actors[b].pos), jump=False)

    # ---------------------------------------------------------------- dialogue
    def say(self, lid, to=None, gesture=0.0, listeners=None, side=None, turn=True):
        t0, t1 = self.plan.cues[lid]
        who = LINES[lid]["who"]
        a = self.actors.get(who)
        if a is not None:
            a.lipsync(LINES[lid]["env"], t0)
            if to:
                a.look(F(t0 - 0.3), F(t0 + 0.1), to)
                if turn:
                    a.face(F(t0 - 0.35), F(t0 + 0.3), to, thr=30)
            if gesture:
                pose = a.pose_at(F(t0))
                sd = side or ("l" if pose in ("pocket_r", "pocket_r_hip_l") else "r")
                a.gesture(F(t0 + 0.2), F(t1 - 0.1), sd, energy=gesture)
        for ln in listeners or []:
            if ln in self.actors and ln != who and a is not None:
                b = self.actors[ln]
                d = 0.08 + 0.25 * self.r.random()
                b.look(F(t0 + d - 0.2), F(t0 + d + 0.25), who)
                b.face(F(t0 + d), F(t0 + d + 0.6), who, thr=70, keep=25)
        return t0, t1

    # ---------------------------------------------------------------- hands
    def bone_world(self, actor, bone, f, tail=False):
        bpy.context.scene.frame_set(f)
        arm = actor.h.arm
        pb = arm.pose.bones[bone]
        return arm.matrix_world @ (pb.tail if tail else pb.head)

    def handoff(self, giver, receiver, t, gside="r", rside="r", prop="notes", keep=0.8, ratio=0.5, gpath=None):
        """Giver's hand goes out with the prop, receiver's hand meets it and takes it (world IK on both)."""
        g, r = self.actors[giver], self.actors[receiver]
        fm = F(t)
        cache = {}

        def meet():
            if "M" not in cache:
                sg = self.bone_world(g, f"upperarm_{gside}", fm)
                sr = self.bone_world(r, f"upperarm_{rside}", fm)
                m = sg.lerp(sr, ratio)
                m.z = min(sg.z, sr.z) - 0.2
                for s, a_ in ((sg, 0.56), (sr, 0.6)):  # keep within reach
                    d = m - s
                    if d.length > a_:
                        m = s + d.normalized() * a_
                cache.update(M=m, sg=sg, sr=sr)
            return cache

        def near_body(a, s, f, down=0.33, fwd=0.18):
            fw = fwd_of(a.yaw_at(f))
            return s + fw * fwd + Vector((0, 0, -down))

        def solve_g(a, side):
            c = meet()
            p0 = gpath or near_body(a, c["sg"], fm - 12)
            return [(fm - 12, p0), (fm, c["M"]), (fm + 6, c["M"]), (fm + 16, near_body(a, c["sg"], fm + 16))]

        fk = fm + int(keep * 24)

        def solve_r(a, side):
            c = meet()
            m = c["M"] + (c["sr"] - c["M"]).normalized() * 0.035
            pre = c["M"] + (c["sr"] - c["M"]).normalized() * 0.12
            chest = near_body(a, c["sr"], fm + 16, down=0.3, fwd=0.22)
            return [(fm - 8, pre), (fm, m), (fm + 6, m), (fm + 16, chest), (max(fk, fm + 17), chest)]

        g.world_ik(gside, fm - 18, fm + 24, solve_g, "grip")
        r.world_ik(rside, fm - 14, fk + 14, solve_r, "grip")
        g.look(fm - 22, fm - 12, receiver)
        r.look(fm - 18, fm - 8, (giver, 1.0))
        ob = A.banknotes(f"note_{giver}_{fm}", n=4 if prop == "stack" else 3) if prop in ("notes", "stack") \
            else wallet(f"wallet_{fm}")
        A.carry(ob, [(1, g, gside), (fm + 3, r, rside)], fm - 14, fk + 8)
        return fm

    def hand_on_shoulder(self, who, whom, t0, t1, side="l", pats=3):
        a, b = self.actors[who], self.actors[whom]
        f0, f1 = F(t0), F(t1)

        def solve(act, sd):
            mid = (f0 + f1) // 2
            me = self.bone_world(a, f"upperarm_{sd}", mid)
            cands = [self.bone_world(b, f"upperarm_{s}", mid) for s in "lr"]
            sh = min(cands, key=lambda p: (p - me).length)
            tgt = sh + Vector((0, 0, 0.05)) + (me - sh).normalized() * 0.05
            pts = [(f0 + 12, tgt)]
            f = f0 + 18
            for _ in range(pats):
                pts += [(f, tgt + Vector((0, 0, 0.05))), (f + 5, tgt)]
                f += 11
            pts.append((f1 - 10, tgt))
            return pts

        a.world_ik(side, f0, f1, solve, "open")

    def fix_hat(self, who, t, dur=1.6):
        a = self.actors[who]
        f0, f1 = F(t), F(t + dur)

        def solve(act, sd):
            mid = f0 + 12
            bpy.context.scene.frame_set(mid)
            arm = a.h.arm
            pb = arm.pose.bones["head"]
            Mw = arm.matrix_world @ pb.matrix
            hpos = Mw.translation
            up = (Mw.to_3x3() @ Vector((0, 1, 0))).normalized()
            lat = (arm.matrix_world.to_3x3() @ Vector((1, 0, 0))).normalized()
            fw = up.cross(lat).normalized() * -1
            s = 1 if sd == "l" else -1
            p = hpos + up * 0.16 + lat * (0.11 * s) + fw * 0.0
            down = -up * 0.018
            twist = fw * (0.02 * s)
            return [(f0 + 10, p + lat * 0.03 * s), (f0 + 14, p), (f0 + 20, p + down), (f0 + 26, p + down + twist),
                    (f1 - 12, p + down + twist)]

        a.world_ik("l", f0, f1, solve, "grip")
        a.world_ik("r", f0, f1, solve, "grip")
        a.nods.append((f0 + 14, -6))

    # ---------------------------------------------------------------- finish
    def finish(self):
        n = self.n
        acts = list(self.actors.values())
        for a in acts:
            a.resolve_positions()
        for a in acts:
            a.resolve_yaw(self)
        for a in acts:
            a.write_root()
        for a in acts:
            a.resolve_head(self, n)
        for a in acts:
            a.resolve_arms(n)
        for a in acts:
            A.fix_quaternions(a.h.arm)
        # world IK needs the posed scene
        for a in acts:
            for side, f0, f1, solver, hand in a.world_actions:
                pts = solver(a, side)
                for f, p in pts:
                    a.ik_world_key(side, f, p)
                a.ik_infl(side, pts[0][0], 1.0, 0.0)
                a.ik_infl(side, pts[-1][0], 1.0, 0.0)
                a.fk_hand(side, pts[0][0], hand)
                a.fk_hand(side, min(f1 - 1, pts[-1][0] + 2), hand)
        for a in acts:
            a.idle(1, n)
            a.blinks(1, n)
            A.fix_quaternions(a.h.arm)
        bpy.context.scene.frame_set(1)

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


def wallet(name):
    me = bpy.data.meshes.new(name)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * 0.085, v.co.y * 0.1 + 0.085, v.co.z * 0.022 - 0.03))
    bm.to_mesh(me)
    bm.free()
    m = bpy.data.materials.get("wallet") or H.plain_material("wallet", (0.09, 0.06, 0.045), rough=0.55)
    me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


# ============================================================================ scene 1: street

def build_s1(plan):
    st = Stage(plan)
    L.Street()
    cu = plan.cues
    john = st.main("john", (-5.5, 7.4, 0), pose="pockets", stance="r")
    bob = st.main("bob", (-4.15, 6.5, 0), pose="pocket_l")
    maxim = st.main("maxim", (-2.9, 7.0, 0), pose="hang", stance="l")
    karim = st.main("karim", (-4.8, 5.0, 0), pose="pockets", stance="l")
    artem = st.main("artem", (-4.1, 4.55, 0), pose="crossed")
    f0 = st.extra("friend0", 71, (-2.35, 7.85, 0), child=0.3, pose="pocket_r", stance="r")
    f1 = st.extra("friend1", 72, (-2.3, 6.15, 0), child=0.3, pose="crossed", stance="even")
    k1 = st.extra("yardkid1", 91, (0.0, 18.4, 0), child=0.55, pose="hang")
    k2 = st.extra("yardkid2", 92, (1.1, 18.9, 0), child=0.55, pose="pockets")
    k3 = st.extra("yardkid3", 93, (5.5, -8.0, 0), child=0.55, pose="hang")
    for a, tgt in ((john, bob), (bob, maxim), (maxim, bob), (karim, bob), (artem, bob), (f0, bob), (f1, bob),
                   (k1, k2), (k2, k1)):
        a.place(1, a.pos, A.yaw_to(a.pos, tgt.pos), jump=False)
    # John leans on the school wall, hands in pockets
    john.lean_body(1, -5)
    k3.walk(F(2.0), F(16.0), (5.6, 14.0, 0))
    k1.gesture(F(4.0), F(7.0), "r", 0.6)
    k2.gesture(F(9.0), F(12.0), "r", 0.5)
    # small life in the group
    artem.pose(F(13.0), "pocket_l")
    karim.stance(F(9.5), "r")
    maxim.pose(F(26.0), "pockets")
    f1.pose(F(15.0), "hang")
    crowd = ["maxim", "friend0", "friend1", "karim", "artem", "john"]
    st.say("s1_01", to="john", listeners=crowd)
    st.say("s1_02", to="bob", listeners=["bob", "maxim"])
    st.say("s1_03", to="john", gesture=0.8, listeners=["maxim", "karim", "artem"])
    st.say("s1_04", to="bob", listeners=["bob"])
    st.say("s1_05", to="john", gesture=0.9, listeners=["maxim", "friend0", "friend1"])
    st.say("s1_06", to="bob", listeners=["bob", "john", "friend0"], gesture=0.5)
    t0, t1 = st.say("s1_07", to="maxim", listeners=["maxim", "bob", "friend0", "friend1"], turn=False)
    # John pushes off the wall towards Maxim on "Я не тебе вопрос задавал"
    john.lean_body(F(t0 - 0.7), -5)
    john.lean_body(F(t0 - 0.2), 0)
    newp = john.pos + (maxim.pos - john.pos).normalized() * 0.55
    john.walk(F(t0 - 0.6), F(t0 + 0.2), newp, face="maxim")
    john.pose(F(t0 - 0.6), "hang")
    maxim.expr(F(t1), eyebrows_left_inner_up=0.0, eyebrows_right_inner_up=0.0)
    maxim.expr(F(t1 + 0.3), eyebrows_left_inner_up=0.5, eyebrows_right_inner_up=0.5)
    # Bob steps to John, turns to him and pats his shoulder while calming him down
    b0, b1 = cu["s1_08"]
    bdest = john.pos + (bob.pos - john.pos).normalized() * 0.5
    bob.walk(F(b0 - 0.9), F(b0 + 0.1), bdest, face="john")
    st.say("s1_08", to="john", listeners=["john", "maxim"])
    st.hand_on_shoulder("bob", "john", b0 + 0.15, b1 + 0.3, side="r", pats=3)
    john.face(F(b0 + 0.3), F(b0 + 0.9), "bob", thr=20)
    john.pose(F(b1 + 0.6), "pockets")
    st.say("s1_09", to="bob", listeners=["bob"])
    st.say("s1_10", to="maxim", gesture=0.7, listeners=["maxim", "john"])
    st.say("s1_11", to="bob", listeners=["bob"])
    # Bob fixes his fur hat with both hands
    th = plan.ev["hat"]
    bob.look(F(th), F(th + 0.4), (bob.pos.x - 0.4, bob.pos.y - 1.6, 1.3))
    st.fix_hat("bob", th + 0.1, 1.7)
    bob.pose(F(th + 2.0), "pockets")
    st.say("s1_12", to="bob", listeners=["bob", "artem"])
    st.say("s1_13", to="karim", listeners=["karim", "artem"])
    # the three leave along the school wall, past the camera
    tl = plan.ev["leave"]
    for i, a in enumerate((bob, karim, artem)):
        dest = (-3.4 - 0.6 * i, -12.0 - 0.8 * i, 0)
        a.walk(F(tl + 0.15 * i), F(tl + 12.0 + 0.2 * i), dest)
    st.say("s1_14", to="bob")
    st.say("s1_15", to="artem")
    john.look(F(tl + 0.5), F(tl + 1.2), "bob")
    maxim.look(F(tl + 0.8), F(tl + 1.5), "bob")
    john.pose(F(tl + 3.0), "crossed")
    st.finish()
    # ---------------------------------------------------------------- cameras
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
    c.at(F(t - 1.0), (-3.0, 9.3, 1.62), (-4.5, 7.0, 1.55), V(-4.6, 7.0, 1.6))
    c.at(F(cu["s1_09"][1] + 0.3), (-2.9, 9.1, 1.6), (-4.6, 6.9, 1.55), V(-4.6, 6.9, 1.6))
    c.shake(F(t - 1.1), F(cu["s1_09"][1] + 0.4), 0.012)
    c = st.cam("1D", 26)
    t = cu["s1_10"][0]
    c.at(F(t - 0.4), (-2.35, 7.75, 1.6), (-4.15, 6.7, 1.66), B)
    c.at(F(plan.ev["hat"] + 2.4), (-2.45, 7.6, 1.6), (-4.3, 6.8, 1.7), V(-4.3, 6.8, 1.7))
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

def seat_kids(st, hall, ti, layout, seeds, names=None):
    """Seat kids at table ti. layout: list of (dx, side) side=-1 south bench (facing north), +1 north bench."""
    tx, ty, _ = hall.tables[ti]
    out = []
    for k, (dx, side) in enumerate(layout):
        name = names[k] if names and k < len(names) and names[k] else f"t{ti}k{k}"
        a = st.extra(name, seeds[k], (tx + dx, ty + side * 0.62, 0), child=0.62, pose="hang", stance="even")
        yaw = 180.0 if side < 0 else 0.0
        a.seat(1, (tx + dx, ty + side * 0.66), 0.46, yaw)
        a.table = (ti, dx, side)
        out.append(a)
    return out


def eat(st, kids, f0, f1, skip=()):
    """Fork to the mouth now and then (local IK from the table to the mouth and back)."""
    for a in kids:
        r = random.Random(a.seed)
        f = f0 + r.randint(0, 50)
        sh = a.shoulder["r"]
        tl = a.pose_defs["table"]["r"][1]
        mouth = (sh.x * 0.25, sh.y - 0.14, a.eye_h - 0.13)
        while f < f1 - 40:
            if not any(s0 - 30 <= f <= s1 + 10 for s0, s1 in skip if True) and not any(
                    s0 - 30 <= f <= s1 + 10 for s0, s1 in getattr(a, "busy", [])):
                def fn(act, sd, fa, fb, tl=tl, mouth=mouth):
                    act.ik_local_key(sd, fa + 8, (tl[0] - 0.02, tl[1] - 0.05, tl[2] + 0.02), absolute=True)
                    act.ik_local_key(sd, fa + 18, mouth, absolute=True)
                    act.ik_local_key(sd, fa + 26, mouth, absolute=True)
                    act.ik_local_key(sd, fa + 36, tl, absolute=True)
                    act.fk_hand(sd, fa + 4, "grip")
                    act.ik_infl(sd, fa + 4, 0.0, 1.0)
                    act.ik_infl(sd, fa + 36, 0.0, 1.0)
                a.act("r", f, f + 40, fn)
            f += r.randint(90, 170)


def busy(a, f0, f1):
    if not hasattr(a, "busy"):
        a.busy = []
    a.busy.append((f0, f1))


def hall_crowd(st, seeds, spots, t0=0.0):
    out = []
    for i, ((p0, p1), sd) in enumerate(zip(spots, seeds)):
        a = st.extra(f"walker{i}", sd, p0, A.yaw_to(p0, p1), child=0.6)
        ta = t0 + 0.6 * i
        a.walk(F(ta), F(ta + (Vector(p1) - Vector(p0)).length / 1.2), p1)
        out.append(a)
    return out


def side_toward(a, p):
    """Which hand of actor a is on the side of point p."""
    y = math.radians(a.yaw)
    left = Vector((math.cos(y), math.sin(y), 0))
    d = Vector((p[0] - a.pos.x, p[1] - a.pos.y, 0))
    return "l" if d.dot(left) > 0 else "r"


def give(st, giver, receiver, t, **kw):
    g, r = st.actors[giver], st.actors[receiver]
    return st.handoff(giver, receiver, t, gside=side_toward(g, r.pos), rside=side_toward(r, g.pos), **kw)


def pass_and_collect(st, plan, near_far, collector, t):
    """Far kid passes his money to the near kid, the near kid hands both to the collector."""
    near, far = near_far
    give(st, far, near, t, keep=0.25)
    busy(st.actors[far], F(t) - 20, F(t) + 26)
    busy(st.actors[near], F(t) - 20, F(t + 1.0) + 30)
    give(st, near, collector, t + 1.0, prop="stack", keep=0.9)


# ============================================================================ scene 2: entering the main school

def build_s2(plan):
    st = Stage(plan)
    hall = L.Hall()
    te = plan.ev["enter"]
    hall.open_doors(F(1.35), F(te + 3.4))
    bob = st.main("bob", (0.0, -10.0, 0), 180.0)
    karim = st.main("karim", (-0.25, -10.7, 0), 180.0)
    artem = st.main("artem", (0.25, -11.3, 0), 180.0)
    bob.walk(F(te - 0.3), F(te + 4.4), (0.0, -3.4, 0), face="karim")
    karim.walk(F(te + 0.15), F(te + 4.9), (-0.8, -3.95, 0), face="bob")
    artem.walk(F(te + 0.55), F(te + 5.2), (0.85, -4.05, 0), face="bob")
    bob.pose(F(te + 4.6), "pockets")
    karim.pose(F(te + 5.0), "pocket_r")
    artem.pose(F(te + 5.4), "hang")
    walkers = hall_crowd(st, [101, 102, 103, 104, 105, 106, 107],
                         [((-3.0, 2.0, 0), (-2.0, 12.0, 0)), ((3.0, -2.0, 0), (3.6, 5.5, 0)),
                          ((-1.0, -5.0, 0), (1.5, 13.0, 0)), ((2.0, 3.0, 0), (-1.5, 16.0, 0)),
                          ((-3.5, -4.0, 0), (-3.2, 9.0, 0)), ((1.0, 0.0, 0), (2.5, 18.0, 0)),
                          ((-2.0, -1.0, 0), (0.5, 20.0, 0))], 0.3)
    seat_kids(st, hall, 0, [(-0.45, -1), (0.45, -1), (-0.45, 1), (0.45, 1)], [111, 112, 113, 114])
    seat_kids(st, hall, 1, [(-0.4, -1), (0.4, -1), (0.4, 1)], [121, 122, 123])
    seat_kids(st, hall, 2, [(-0.5, -1), (0.0, -1), (0.5, -1), (-0.3, 1), (0.3, 1)], [131, 132, 133, 134, 135])
    st.say("s2_01", to=(0.0, 12.0, 1.2), listeners=["bob", "karim"])
    st.say("s2_02", to="bob", listeners=["bob", "artem"], gesture=0.4)
    st.say("s2_03", to="karim", listeners=["karim", "artem"])
    tl = plan.ev["look"]
    for a in (bob, karim, artem):
        a.look(F(tl), F(tl + 0.5), (-1.0, 14.0, 1.0))
    st.say("s2_04", to="artem", listeners=["karim", "artem"], gesture=0.5)
    st.say("s2_05", to="bob")
    tg = plan.ev["go"]
    bob.walk(F(tg), F(tg + 3.5), (-1.4, 0.8, 0))
    karim.walk(F(tg + 0.35), F(tg + 3.9), (-2.0, 0.2, 0))
    artem.walk(F(tg + 0.5), F(tg + 4.0), (-0.7, 0.1, 0))
    st.finish()
    c = st.cam("2A", 20)
    c.at(1, (1.3, 3.5, 1.62), (0.0, -7.5, 1.4), V(0.0, -7.0, 1.4))
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
    k1 = seat_kids(st, hall, 0, [(-0.45, -1), (0.45, -1), (-0.45, 1), (0.45, 1)], [111, 112, 113, 114],
                   ["kid1", "kid2", "t0k2", "t0k3"])
    k2 = seat_kids(st, hall, 1, [(-0.4, -1), (0.4, -1), (0.4, 1)], [121, 122, 123], ["kid3", "t1k1", "t1k2"])
    k3 = seat_kids(st, hall, 2, [(-0.5, -1), (0.0, -1), (0.5, -1), (-0.3, 1), (0.3, 1)], [131, 132, 133, 134, 135],
                   ["t2k0", "t2k2", "kid4", "kid5", "t2k4"])
    k4 = seat_kids(st, hall, 3, [(-0.4, -1), (0.4, 1)], [141, 142])
    T = hall.tables
    bob = st.main("bob", (-1.0, 9.5, 0), 0, pose="pockets")
    artem = st.main("artem", (-1.6, 9.0, 0), 0)
    karim = st.main("karim", (-0.4, 9.0, 0), 0, pose="pocket_l")

    def spots(Tt):
        return {"bob": V(Tt.x + 1.2, Tt.y - 0.05, 0), "artem": V(Tt.x + 1.0, Tt.y + 1.05, 0),
                "karim": V(Tt.x + 1.0, Tt.y - 1.05, 0)}

    # table 1
    p1 = spots(T[0])
    ctr = (T[0].x, T[0].y, 1.0)
    for n, a in (("bob", bob), ("artem", artem), ("karim", karim)):
        a.walk(F(0.1), F(2.0), p1[n], face=ctr)
    ally = ["kid1", "kid2", "t0k2", "t0k3"]
    st.say("s3_01", to="kid2", listeners=ally)
    st.say("s3_02", to="bob", listeners=["bob"])
    st.say("s3_03", to="kid2", listeners=ally, gesture=0.6)
    st.say("s3_04", to="bob")
    for a in k1:
        a.look(F(plan.cues["s3_04"][1]), F(plan.cues["s3_04"][1] + 0.4), "kid1" if a.name != "kid1" else "t0k2")
    st.say("s3_05", to="kid2", listeners=ally)
    tp = plan.ev["pay1"]
    pass_and_collect(st, plan, ("t0k3", "t0k2"), "artem", tp + 0.5)
    pass_and_collect(st, plan, ("kid2", "kid1"), "karim", tp + 0.7)
    # Karim hands his money to Artem across the end of the table, Artem counts
    karim.walk(F(tp + 2.6), F(tp + 3.3), artem.pos + V(0.35, -0.6, 0), face="artem")
    give(st, "karim", "artem", tp + 3.5, prop="stack", keep=1.6)
    artem.look(F(tp + 3.7), F(tp + 4.0), ("artem", 0.95))
    artem.nods.append((F(tp + 4.4), 4))
    st.say("s3_06", to="bob")
    st.say("s3_07", to="kid1", listeners=ally)
    # table 2
    tw = plan.ev["walk2"]
    p2 = spots(T[1])
    ctr = (T[1].x, T[1].y, 1.0)
    for i, (n, a) in enumerate((("bob", bob), ("artem", artem), ("karim", karim))):
        a.walk(F(tw + 0.1 * i), F(tw + 2.5), p2[n], face=ctr)
    al2 = ["kid3", "t1k1", "t1k2"]
    st.say("s3_08", to="t1k1", listeners=al2)
    st.say("s3_09", to="bob")
    st.say("s3_10", to="kid3", listeners=al2)
    tp2 = plan.ev["pay2"]
    pass_and_collect(st, plan, ("t1k1", "kid3"), "karim", tp2 - 0.35)
    give(st, "t1k2", "artem", tp2 + 0.65, keep=0.6)
    busy(st.actors["t1k2"], F(tp2) - 10, F(tp2 + 1.6))
    st.say("s3_11", to="bob")
    st.say("s3_12", to="artem")
    # table 3
    tw = plan.ev["walk3"]
    p3 = spots(T[2])
    ctr = (T[2].x, T[2].y, 1.0)
    for i, (n, a) in enumerate((("bob", bob), ("artem", artem), ("karim", karim))):
        a.walk(F(tw + 0.1 * i), F(tw + 2.5), p3[n], face=ctr)
    kid4 = st.actors["kid4"]
    th = plan.ev["hide"]
    tl4 = kid4.pose_defs["table"]
    sh = kid4.shoulder["r"]
    under = (tl4["r"][1][0] + 0.05, tl4["r"][1][1] + 0.12, tl4["r"][1][2] - 0.2)
    kid4.pose_defs["hide"] = {"l": tl4["l"], "r": ("ikabs", under)}
    kid4.pose(F(th), "hide")
    kid4.look(F(th), F(th + 0.4), (kid4.pos.x, kid4.pos.y + 0.3, 0.7))
    busy(kid4, F(th) - 40, F(plan.ev["pay3"] + 3))
    al3 = ["t2k0", "kid4", "t2k2", "kid5", "t2k4"]
    st.say("s3_13", to="kid4", listeners=al3)
    st.say("s3_14", to="artem")
    kid4.look(F(plan.cues["s3_14"][1] + 0.2), F(plan.cues["s3_14"][1] + 0.6), (kid4.pos.x, kid4.pos.y + 0.4, 0.8))
    st.say("s3_15", to="kid4", listeners=al3)
    tp3 = plan.ev["pay3"]
    kid4.pose(F(tp3 + 1.2), "table")
    give(st, "kid4", "karim", tp3 + 0.75, keep=0.8)
    st.say("s3_16", to="kid4", listeners=al3)
    kid5 = st.actors["kid5"]
    t0, t1 = st.say("s3_17", to="t2k4")
    kid5.lean(F(t0 + 0.1), F(t1), (8, 0, -12))
    st.say("s3_18", to="kid5", listeners=al3)
    st.say("s3_19", to="artem")
    st.say("s3_20", to="kid5", listeners=al3)
    # walking away north-east
    tw = plan.ev["walk4"]
    for i, (a, dest) in enumerate(((bob, (2.6, 21.5, 0)), (artem, (2.0, 22.1, 0)), (karim, (3.2, 21.0, 0)))):
        a.walk(F(tw + 0.1 * i), F(tw + 6.5), dest)
    bob.pose(F(tw + 7.0), "pockets")
    st.say("s3_21", to="bob")
    st.say("s3_22", to="bob", gesture=0.5)
    st.say("s3_23", to="artem")
    eat(st, k1 + k2 + k3 + k4, 1, st.n)
    st.finish()
    # cameras
    cu = plan.cues
    c = st.cam("3A", 20)
    c.at(1, (-0.6, 11.0, 1.62), (-1.3, 14.0, 1.4), V(-1.3, 14.0, 1.4))
    c.at(F(2.2), (-3.9, 12.6, 1.35), (-1.25, 14.0, 1.5), V(-1.25, 13.9, 1.55))
    c.at(F(cu["s3_02"][0]), (-3.95, 12.7, 1.3), (-2.6, 13.4, 1.0), V(-2.85, 13.4, 1.0))
    c.at(F(cu["s3_03"][0] + 0.1), (-3.9, 12.6, 1.35), (-1.25, 14.0, 1.55), V(-1.25, 13.9, 1.6))
    c.at(F(tp + 0.3), (-3.8, 12.7, 1.35), (-1.6, 14.0, 1.15), V(-1.5, 14.0, 1.15))
    c.at(F(tp + 2.4), (-3.75, 12.8, 1.35), (-1.4, 14.2, 1.15), V(-1.4, 14.2, 1.15))
    c.at(F(cu["s3_06"][0]), (-3.7, 12.9, 1.35), (-1.3, 14.8, 1.45), V(-1.3, 14.85, 1.5))
    c.at(F(cu["s3_07"][1] + 0.3), (-3.6, 13.0, 1.4), (-1.25, 13.9, 1.55), V(-1.25, 13.9, 1.6))
    c.shake(1, F(cu["s3_07"][1] + 0.4), 0.012)
    c = st.cam("3B", 22)
    t = cu["s3_07"][1] + 0.3
    c.at(F(t), (-0.6, 12.2, 1.6), (1.0, 13.0, 1.5), V(1.0, 13.0, 1.5))
    c.at(F(plan.ev["walk2"] + 2.6), (0.3, 12.6, 1.55), (2.95, 14.4, 1.55), V(2.95, 14.4, 1.6))
    c.at(F(tp2 - 0.2), (0.4, 12.7, 1.5), (2.4, 14.2, 1.1), V(2.4, 14.2, 1.1))
    c.at(F(tp2 + 1.4), (0.45, 12.75, 1.5), (2.6, 14.6, 1.15), V(2.6, 14.6, 1.15))
    c.at(F(cu["s3_12"][1] + 0.2), (0.5, 12.8, 1.55), (2.95, 14.4, 1.55), V(2.95, 14.4, 1.6))
    c.shake(F(t), F(cu["s3_12"][1] + 0.3), 0.013)
    c = st.cam("3C", 26)
    t = cu["s3_12"][1] + 0.2
    k4 = kid4.pos
    c.at(F(t), (-2.45, 17.75, 1.2), (-1.0, 18.9, 1.5), V(-1.05, 18.9, 1.55))
    c.at(F(plan.ev["hide"] + 0.6), (-2.5, 17.7, 1.15), (k4.x, k4.y + 0.15, 0.85), V(k4.x, k4.y + 0.1, 0.9))
    c.at(F(cu["s3_13"][0] + 0.1), (-2.45, 17.75, 1.2), (-1.0, 18.9, 1.55), V(-1.05, 18.9, 1.6))
    c.at(F(tp3 + 0.3), (-2.4, 17.8, 1.2), (k4.x + 0.4, k4.y - 0.1, 1.05), V(k4.x + 0.4, k4.y - 0.1, 1.05))
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
    hood = W.extra("hoodie", 201, child=0.55)
    hood["outfit"] = [W.garment("male_casualsuit02", top=(0.5, 0.5, 0.52), top_desat=1.0), W.shoes("shoes02")]
    hb = H.Human("hoodie", hood["spec"], hood["outfit"])
    hoodie = A.Actor(hb, (-4.15, 7.0, 0), 90.0, seed=201)
    hoodie.pose(1, "hang")
    st.actors["hoodie"] = hoodie
    o1 = st.extra("wall1", 211, (-4.2, 7.85, 0), 100, child=0.6, pose="behind")
    o2 = st.extra("wall2", 212, (-4.1, 6.15, 0), 80, child=0.6, pose="pockets", stance="l")
    o3 = st.extra("wall3", 213, (-3.75, 8.6, 0), 120, child=0.6, pose="crossed")
    artem = st.main("artem", (-3.25, 7.15, 0), -90, pose="hang", stance="r")
    karim = st.main("karim", (-3.35, 6.3, 0), -70, pose="pocket_r")
    bob = st.main("bob", (-1.0, 12.5, 0), 180, pose="pockets")
    for a, t in ((hoodie, artem), (o1, artem), (o2, karim), (o3, artem), (artem, hoodie), (karim, hoodie)):
        a.place(1, a.pos, A.yaw_to(a.pos, t.pos), jump=False)
    hall_crowd(st, [221, 222, 223], [((2.0, 1.0, 0), (2.5, 14.0, 0)), ((3.2, 12.0, 0), (2.8, -4.0, 0)),
                                     ((-0.5, -4.0, 0), (0.5, 16.0, 0))], 0.5)
    seat_kids(st, hall, 0, [(-0.45, -1), (0.45, 1)], [111, 113])
    al = ["hoodie", "wall1", "wall2", "wall3", "karim", "artem"]
    st.say("s4_01", to="hoodie", gesture=0.7, listeners=al)
    st.say("s4_02", to="artem", listeners=al)
    st.say("s4_03", to="bob")
    tb = plan.ev["bob_in"]
    bpos = V(-2.9, 7.65, 0)
    bob.walk(F(tb), F(tb + 2.6), bpos, face="hoodie")
    karim.look(F(tb), F(tb + 0.4), "bob")
    artem.pose(F(tb + 1.0), "crossed")
    st.say("s4_04", to="hoodie", listeners=al)
    st.say("s4_05", to="bob")
    st.say("s4_06", to="hoodie", gesture=0.7, listeners=al)
    st.say("s4_07", to="bob")
    st.say("s4_08", to="hoodie")
    st.say("s4_09", to="bob")
    t0, t1 = st.say("s4_10", to="hoodie", listeners=["hoodie"])
    artem.pose(F(t0 - 0.3), "hang")
    artem.walk(F(t0), F(t0 + 0.6), (-3.55, 7.1, 0), face="hoodie")
    st.say("s4_11", to="artem", listeners=["artem"])
    artem.walk(F(plan.cues["s4_11"][1]), F(plan.cues["s4_11"][1] + 0.7), (-3.3, 7.15, 0), face="hoodie")
    st.say("s4_12", to="bob", listeners=al, gesture=1.1)
    hall_kids = [a for n, a in st.actors.items() if n.startswith("walker") or n.startswith("t0k")]
    for i, a in enumerate(hall_kids):
        a.look(F(plan.cues["s4_12"][0] + 0.2 * i), F(plan.cues["s4_12"][0] + 0.2 * i + 0.5), (-3.8, 7.0, 1.4))
    st.say("s4_13", to="karim", listeners=["karim", "artem"])
    # Karim and Artem take him to a locker further down, push him in, take the wallet, slam the door
    tk = plan.ev["take"]
    door = hall.locker_doors[5]
    ly = door.location.y - 0.2
    lx = hall.locker_x
    karim.pose(F(tk - 0.3), "hang")
    hoodie.walk(F(tk + 0.3), F(tk + 2.4), (lx + 0.45, ly, 0), face=(lx, ly, 1.4))
    artem.walk(F(tk), F(tk + 2.4), (lx + 0.85, ly + 0.5, 0), face="hoodie")
    karim.walk(F(tk + 0.1), F(tk + 2.4), (lx + 0.9, ly - 0.45, 0), face="hoodie")
    door.rotation_euler = (0, 0, 0)
    door.keyframe_insert("rotation_euler", frame=F(tk + 2.2))
    door.rotation_euler = (0, 0, math.radians(100))
    door.keyframe_insert("rotation_euler", frame=F(tk + 2.6))
    door.keyframe_insert("rotation_euler", frame=F(tk + 5.0))
    door.rotation_euler = (0, 0, 0)
    door.keyframe_insert("rotation_euler", frame=F(tk + 5.3))
    # turned around and pushed in
    hoodie.turn(F(tk + 2.5), F(tk + 2.75), 90.0)
    hoodie.pos_keys.append((F(tk + 2.75), V(lx + 0.45, ly, 0), False))
    hoodie.pos_keys.append((F(tk + 3.2), V(lx - 0.22, ly, 0.08), False))
    hoodie.pos = V(lx - 0.22, ly, 0.08)
    hoodie.pose(F(tk + 2.6), "hands_front")
    hoodie.look(F(tk + 2.7), F(tk + 3.0), "karim")

    def push(who, side, f0, f1):
        def solve(a, sd):
            pts = []
            for f in range(f0 + 6, f1 - 5, 4):
                c = st.bone_world(hoodie, "spine_03", f)
                me = st.bone_world(a, f"upperarm_{sd}", f)
                d = (c - me)
                d.z = 0
                p = c - d.normalized() * 0.12 + Vector((0, 0, -0.05))
                pts.append((f, p))
            return pts
        st.actors[who].world_ik(side, f0, f1, solve, "open")

    push("karim", "r", F(tk + 2.4), F(tk + 3.6))
    push("karim", "l", F(tk + 2.4), F(tk + 3.6))
    push("artem", "l", F(tk + 2.5), F(tk + 3.4))
    give(st, "hoodie", "artem", tk + 4.25, prop="wallet", keep=1.4, ratio=0.15)
    karim.look(F(tk + 4.0), F(tk + 4.3), "hoodie")
    # Bob waits in the foreground and stares the others down
    for i, a in enumerate((o1, o2, o3)):
        a.look(F(tk + 0.8 + 0.2 * i), F(tk + 1.3 + 0.2 * i), (lx + 0.4, ly, 1.3))
        a.face(F(tk + 1.0 + 0.2 * i), F(tk + 1.6 + 0.2 * i), (lx + 0.4, ly, 1.3), thr=40, keep=15)
    bob.look(F(tk + 1.0), F(tk + 1.5), "wall2")
    bob.look(F(tk + 3.5), F(tk + 4.0), "wall1")
    o2.pose(F(tk + 1.5), "hang")
    o1.pose(F(tk + 2.2), "hang")
    # they come back
    tb2 = plan.ev["back"]
    artem.walk(F(tb2), F(tb2 + 2.4), (-3.4, 7.0, 0), face="bob")
    karim.walk(F(tb2 + 0.1), F(tb2 + 2.5), (-3.3, 6.35, 0), face="bob")
    artem.pose(F(tb2 + 2.6), "pocket_r")
    karim.pose(F(tb2 + 2.7), "pockets")
    st.say("s4_14", to="bob", listeners=["bob"])
    st.say("s4_15", to="karim", listeners=["karim"])
    st.say("s4_16", to="bob", listeners=["bob", "artem"])
    st.say("s4_17", to="bob", gesture=0.5)
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
    c = st.cam("4C", 30)
    t = cu["s4_12"][1] + 0.3
    c.at(F(t), (-0.6, 10.2, 1.6), (-3.3, 6.4, 1.5), V(-2.9, 7.65, 1.7))
    c.at(F(tk + 1.2), (-0.3, 9.0, 1.6), (-4.1, 3.4, 1.3), V(lx + 0.5, ly, 1.3))
    c.at(F(tb2), (-0.35, 8.9, 1.6), (-4.1, 3.3, 1.3), V(lx + 0.5, ly, 1.3))
    c.at(F(tb2 + 2.6), (-0.7, 9.6, 1.6), (-3.3, 6.3, 1.55), V(-3.3, 6.5, 1.6))
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
    k1 = seat_kids(st, hall, 0, [(-0.45, -1), (0.45, -1), (-0.45, 1)], [111, 112, 113])
    k3 = seat_kids(st, hall, 2, [(-0.5, -1), (0.5, -1), (0.3, 1)], [131, 133, 135])
    k4 = seat_kids(st, hall, 3, [(-0.4, -1), (0.4, -1), (0.0, 1)], [141, 142, 143], ["kid6", "kid7", "t3k2"])
    k5 = seat_kids(st, hall, 4, [(-0.45, -1), (0.45, -1), (-0.45, 1), (0.45, 1)], [151, 152, 153, 154])
    bob = st.main("bob", (-2.6, 9.0, 0), 0, pose="pockets")
    karim = st.main("karim", (-3.1, 8.4, 0), 0, pose="pocket_l")
    artem = st.main("artem", (-2.1, 8.3, 0), 0)
    T = hall.tables
    dest = {"bob": V(T[4].x + 1.2, T[4].y - 0.05, 0), "artem": V(T[4].x + 1.0, T[4].y + 1.05, 0),
            "karim": V(T[4].x + 1.0, T[4].y - 1.05, 0)}
    ta = plan.ev["arrive"]
    ctr = (T[4].x, T[4].y, 1.0)
    for i, (n, a) in enumerate((("bob", bob), ("karim", karim), ("artem", artem))):
        mid = V(dest[n].x - 1.6, dest[n].y - 7.0, 0)
        a.walk(F(plan.ev["walk"] + 0.15 * i), F(ta), mid)
        a.walk(F(ta) + 1, F(ta + 3.0), dest[n], face=ctr)
    kid6, kid7 = st.actors["kid6"], st.actors["kid7"]
    t0, t1 = st.say("s5_01", to="kid7")
    kid6.lean(F(t0 + 0.1), F(plan.cues["s5_03"][1]), (8, 0, 10))
    st.say("s5_02", to="kid6")
    st.say("s5_03", to="kid7")
    for a in k4 + k3:
        a.look(F(plan.ev["walk"] + 0.5), F(plan.ev["walk"] + 1.2), "bob")
    # silent payment: money is passed to the end of the table and handed over
    al = [n for n in st.actors if n.startswith("t4")]
    st.say("s5_04", to="t4k1", listeners=al)
    tp = plan.ev["pay"]
    pass_and_collect(st, plan, ("t4k1", "t4k0"), "karim", tp - 0.45)
    pass_and_collect(st, plan, ("t4k3", "t4k2"), "artem", tp + 0.25)
    st.say("s5_05", to="bob")
    st.say("s5_06", to="bob", gesture=0.7)
    st.say("s5_07", to="artem")
    # bell: kids get up and leave
    tbl = plan.ev["bell"]
    leavers = k5 + k1[:2] + k3[:2]
    for i, a in enumerate(leavers):
        f = F(tbl + 0.4 + 0.25 * i)
        a.stand_up(f, back=0.35)
        busy(a, f - 20, st.n)
        a.walk(f + 16, f + 16 + F(5.0), (a.pos.x + random.Random(i).uniform(-1, 1), -6.0, 0))
    st.say("s5_08", to="artem")
    st.say("s5_09", to="bob")
    st.say("s5_10", to="karim")
    te = plan.ev["exit"]
    for i, a in enumerate((bob, karim, artem)):
        a.walk(F(te + 0.15 * i), F(te + 8.0), (-1.0 + 0.6 * i, 2.0 - 0.5 * i, 0))
    eat(st, k1 + k3 + k5, 1, st.n)
    st.finish()
    cu = plan.cues
    c = st.cam("5A", 28)
    c.at(1, (3.35, 18.55, 1.1), (2.2, 19.25, 1.05), V(2.2, 19.2, 1.05))
    c.at(F(plan.cues["s5_03"][1] + 0.4), (3.3, 18.5, 1.1), (1.0, 18.0, 1.3), V(2.2, 19.2, 1.05))
    c.shake(1, F(plan.cues["s5_03"][1] + 0.6), 0.01)
    c = st.cam("5B", 22)
    t = plan.shots[1][1]
    c.at(F(t), (-2.4, 22.0, 1.55), (0.95, 23.4, 1.55), V(0.95, 23.4, 1.6))
    c.at(F(tp - 0.6), (-2.3, 22.1, 1.5), (0.5, 23.4, 1.1), V(0.5, 23.4, 1.1))
    c.at(F(tp + 1.6), (-2.3, 22.15, 1.5), (0.6, 23.6, 1.15), V(0.6, 23.6, 1.15))
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

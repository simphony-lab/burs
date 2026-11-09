"""Acting for code-built humans.

Builders record intents on actors (root moves, looks, base poses, arm actions); Stage.finish() resolves them in a
fixed order so channels never fight each other:
  1. root: positions (place / walk / slide / seat), then facing (turn / face) with yaw unwrapped, so a body never
     spins the long way round;
  2. head, neck and spine sampled from look targets (tracking moving targets), nods and leans;
  3. arms: base poses (hanging, pockets, crossed, behind the back, on the table ...) between action windows, FK
     actions (walk swing, gestures) and local-IK actions (eating);
  4. world-IK actions evaluated against the posed scene (hand-offs, a hand on someone's shoulder, fixing a hat);
  5. idle breathing / sway, blinks.
Lip sync writes shape keys directly. Also: a handheld reportage camera.
"""
import math
import random
import subprocess

import bpy
import numpy as np
from mathutils import Vector

import human as H

FPS = 24
REST_BEND = 46.0  # elbow bend of the MakeHuman game-engine rest pose
HANG = 12.0  # natural bend of a hanging arm


def F(t):
    return int(round(t * FPS)) + 1


def yaw_to(src, dst):
    return math.degrees(math.atan2(dst[0] - src[0], -(dst[1] - src[1])))


def wrap(a):
    return (a + 180) % 360 - 180


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def lerp(a, b, t):
    return a + (b - a) * t


def interp(keys, f):
    """keys: sorted [(f, value)], value float or Vector; linear interpolation, held at the ends."""
    if not keys:
        return None
    if f <= keys[0][0]:
        return keys[0][1]
    for (fa, va), (fb, vb) in zip(keys, keys[1:]):
        if fa <= f <= fb:
            if fb == fa:
                return vb
            return va + (vb - va) * ((f - fa) / (fb - fa))
    return keys[-1][1]


def dedupe(keys):
    keys = sorted(keys, key=lambda k: k[0])
    out = []
    for k in keys:
        if out and out[-1][0] == k[0]:
            out[-1] = k
        else:
            out.append(k)
    return out


# ============================================================================ poses

FINGER_CLOSE = {"index": 5, "middle": 0, "ring": -5, "pinky": -10}

# arm base poses. ("fk", name) or ("ik", offset from the shoulder joint in armature space: x = actor's left,
# y = back, z = up; mirrored for the right arm)
POSES = {
    "hang": {"l": ("fk", "hang"), "r": ("fk", "hang")},
    "pockets": {"l": ("fk", "pocket"), "r": ("fk", "pocket")},
    "pocket_l": {"l": ("fk", "pocket"), "r": ("fk", "hang")},
    "pocket_r": {"l": ("fk", "hang"), "r": ("fk", "pocket")},
    "crossed": {"l": ("ik", (-0.34, -0.22, -0.31)), "r": ("ik", (-0.35, -0.27, -0.27))},
    "behind": {"l": ("ik", (-0.13, 0.2, -0.5)), "r": ("ik", (-0.11, 0.21, -0.48))},
    "hip_l": {"l": ("ik", (0.07, 0.0, -0.42)), "r": ("fk", "hang")},
    "pocket_r_hip_l": {"l": ("ik", (0.07, 0.0, -0.42)), "r": ("fk", "pocket")},
    "hands_front": {"l": ("ik", (-0.17, -0.2, -0.5)), "r": ("ik", (-0.19, -0.21, -0.48))},
}


class Actor:
    REG = {}  # name -> actor (builder-time lookups)

    def __init__(self, h, pos, yaw, seed=0):
        Actor.REG[h.name] = self
        self.h = h
        self.r = random.Random(seed)
        self.seed = seed
        self.name = h.name
        self.pos = Vector(pos)  # position at the end of the last recorded move (builder time)
        self.yaw = yaw  # yaw at the end of the last recorded turn/walk (builder time)
        self.pos_keys = [(1, Vector(pos), False)]  # (f, pos, jump)
        self.yaw_ops = [("set", 1, yaw)]
        self.yaw_keys = []
        self.lean_keys = []  # (f, x_deg) whole-body lean (leaning on a wall)
        self.walks = []  # (f0, f1)
        self.seats = []  # [f0, f1] seated intervals
        self.looks = []  # (f0, f1, target, blend)
        self.nods = []  # (f, amount)
        self.spine = []  # (f0, f1, (x, y, z), ramp) leans of spine_02
        self.poses = [(1, "hang")]
        self.pose_defs = {}
        self.stances = [(1, "even")]
        self.actions = {"l": [], "r": [], "legs": []}  # (f0, f1, fn) fn(actor, side, f0, f1)
        self.world_actions = []  # (fn,) resolved after everything else is keyed
        self.idle_amp = 0.6 + 0.6 * self.r.random()
        arm = h.arm
        b = arm.data.bones
        self.shoulder = {s: b[f"upperarm_{s}"].head_local.copy() for s in "lr"}
        self.eye_h = b["head"].head_local.z + 0.09
        self.ik = {}
        h.place(1, pos, yaw)

    # ---------------------------------------------------------------- root intents
    def place(self, f, pos, yaw=None, jump=True):
        self.pos_keys.append((f, Vector(pos), jump))
        self.pos = Vector(pos)
        if yaw is not None:
            self.yaw_ops.append(("set", f, yaw))
            self.yaw = yaw

    def walk(self, f0, f1, dest, stride=0.68, face=None):
        """Walk in a straight line, easing in and out; turns towards the path first, optionally faces a point
        (or actor name) at the end."""
        p0, p1 = self.pos.copy(), Vector(dest)
        dist = (p1 - p0).length
        if dist < 0.05:
            return
        self.walks.append((f0, f1))
        self.yaw_ops.append(("walk", f0, f1, yaw_to(p0, p1), face))
        dur = f1 - f0
        r = min(0.3, 9.0 / max(dur, 1))  # accel fraction
        vmax = 1.0 / (1.0 - r)

        def s_of(t):
            if t < r:
                return vmax * t * t / (2 * r)
            if t > 1 - r:
                return 1 - vmax * (1 - t) ** 2 / (2 * r)
            return vmax * (t - r / 2)

        steps = max(1.0, round(dist / stride))
        prof = []
        for f in range(f0, f1 + 1, 2):
            t = (f - f0) / dur
            s = s_of(t)
            v = (s_of(min(1, t + 0.01)) - s_of(max(0, t - 0.01))) / 0.02 / vmax
            prof.append((f, s, v))
            pos = p0.lerp(p1, s)
            ph = s * steps * math.pi
            pos.z = p0.z + 0.012 * 0.5 * (1 - math.cos(2 * ph)) * min(1.0, v)
            self.pos_keys.append((f, pos, False))
        self.pos_keys.append((f1, p1.copy(), False))
        self.pos = p1
        self.yaw = yaw_to(p0, p1)
        if face is not None:
            fp = Actor.REG[face].pos if isinstance(face, str) else Vector(face)
            self.yaw = yaw_to(p1, fp)

        def legs(a, side, fa, fb, prof=prof, steps=steps):
            h = a.h
            for f, s, v in prof:
                ph = s * steps * math.pi
                k = min(1.0, v * 1.1)
                sw = math.sin(ph) * k
                h.rot("thigh_l", f, (-24 * sw, 0, 0))
                h.rot("thigh_r", f, (24 * sw, 0, 0))
                h.rot("calf_l", f, (38 * max(0, -math.cos(ph)) * k + 4, 0, 0))
                h.rot("calf_r", f, (38 * max(0, math.cos(ph)) * k + 4, 0, 0))
                h.rot("foot_l", f, (-8 * sw, 0, 0))
                h.rot("foot_r", f, (8 * sw, 0, 0))

        def arms(a, side, fa, fb, prof=prof, steps=steps):
            sg = 1 if side == "l" else -1
            a.ik_infl(side, fa + 4, 0.0, 0.0)
            a.ik_infl(side, fb - 4, 0.0, 0.0)
            for f, s, v in prof[1:-1]:
                ph = s * steps * math.pi
                k = min(1.0, v * 1.1)
                a.arm(side, f, 14 * math.sin(ph) * k * sg, 37, HANG + 6)
            a.fk_hand(side, fa + 4, "hang")

        self.actions["legs"].append((f0, f1, legs))
        self.actions["l"].append((f0, f1, arms))
        self.actions["r"].append((f0, f1, arms))

    def turn(self, f0, f1, yaw):
        self.yaw_ops.append(("turn", f0, f1, yaw))
        self.yaw = yaw

    def face(self, f0, f1, target, thr=25.0, keep=8.0):
        """Turn the body towards a point / actor if it is more than thr degrees off (resolved at finish)."""
        self.yaw_ops.append(("face", f0, f1, target, thr, keep))

    def lean_body(self, f, deg):
        self.lean_keys.append((f, deg))

    def seat(self, f, seat_xy, seat_z, yaw, table_z=0.76):
        """Sit on a bench: hips at seat height, thighs forward, hands resting on the table."""
        h = self.h
        hip = h.arm.data.bones["pelvis"].head_local.z
        p = Vector((seat_xy[0], seat_xy[1], seat_z - hip + 0.04))
        self.place(f, p, yaw)
        self.seats.append([f, 10 ** 9])
        lz = table_z - p.z  # table top in armature space
        sh = self.shoulder["l"]
        self.pose_defs["table"] = {"l": ("ikabs", (sh.x - 0.08, sh.y - 0.4, lz + 0.05)),
                                   "r": ("ikabs", (-sh.x + 0.08, sh.y - 0.4, lz + 0.05))}
        self.pose(f, "table")

        def legs(a, side, fa, fb):
            for s in ("l", "r"):
                a.h.rot(f"thigh_{s}", fa, (-86, 0, 0))
                a.h.rot(f"calf_{s}", fa, (84, 0, 0))
                a.h.rot(f"foot_{s}", fa, (-6, 0, 0))

        self.actions["legs"].append((f, 10 ** 9, legs))

    def stand_up(self, f, back=0.35):
        """From the bench to standing next to it (14 frames)."""
        for s in self.seats:
            if s[1] > f:
                s[1] = f + 14
        for side in ("l", "r", "legs"):
            self.actions[side] = [(a, min(b, f) if b >= 10 ** 9 else b, fn) for a, b, fn in self.actions[side]]
        p0 = self.pos.copy()
        fwd = Vector((math.sin(math.radians(self.yaw)), -math.cos(math.radians(self.yaw)), 0))
        p1 = Vector((p0.x, p0.y, 0)) - fwd * back
        self.pos_keys.append((f, p0, False))
        self.pos_keys.append((f + 14, p1, False))
        self.pos = p1
        self.pose(f + 6, "hang")

        def legs(a, side, fa, fb):
            for s in ("l", "r"):
                a.h.rot(f"thigh_{s}", fa, (-86, 0, 0))
                a.h.rot(f"calf_{s}", fa, (84, 0, 0))
                a.h.rot(f"thigh_{s}", fa + 7, (-50, 0, 0))
                a.h.rot(f"calf_{s}", fa + 7, (60, 0, 0))
                a.h.rot(f"thigh_{s}", fb, (0, 0, 0))
                a.h.rot(f"calf_{s}", fb, (0, 0, 0))
                a.h.rot(f"foot_{s}", fb, (0, 0, 0))

        self.actions["legs"].append((f, f + 14, legs))

    def seated_at(self, f):
        return any(a <= f <= b for a, b in self.seats)

    def walking_at(self, f, pad=0):
        return any(a - pad <= f <= b + pad for a, b in self.walks)

    # ---------------------------------------------------------------- head / spine intents
    def look(self, f0, f1, target, blend=1.0):
        """Turn the head toward a world point or an actor (name) between f0 and f1; keeps tracking it."""
        self.looks.append((f0, f1, target, blend))

    def look_ahead(self, f0, f1):
        self.looks.append((f0, f1, None, 1.0))

    def nod(self, f, amt=8):
        self.nods.append((f, amt))

    def lean(self, f0, f1, xyz, ramp=6):
        self.spine.append((f0, f1, xyz, ramp))

    # ---------------------------------------------------------------- arm intents
    def pose(self, f, name):
        self.poses.append((f, name))

    def stance(self, f, name):
        self.stances.append((f, name))

    def act(self, side, f0, f1, fn):
        self.actions[side].append((f0, f1, fn))

    def gesture(self, f0, f1, side="r", energy=1.0):
        """Talking hand: forearm comes up, small accents on the beats, drops back."""
        if f1 - f0 < 14:
            return
        r = random.Random(self.seed * 31 + f0)

        def fn(a, sd, fa, fb):
            a.ik_infl(sd, fa + 6, 0.0, 0.0)
            a.ik_infl(sd, fb - 6, 0.0, 0.0)
            f = fa + 7
            base = (14 * energy, 34, HANG + 55 * energy)
            while f < fb - 10:
                a.arm(sd, f, base[0] + r.uniform(-5, 7) * energy, base[1] + r.uniform(-3, 2), base[2] + r.uniform(-12, 14) * energy,
                      twist=r.uniform(-12, 12), out=r.uniform(-4, 6))
                f += r.randint(9, 16)
            a.arm(sd, fb - 7, base[0] * 0.6, 35, base[2] * 0.7)
            a.fk_hand(sd, fa + 7, "open")

        self.actions[side].append((f0, f1 + 8, fn))

    def reach_local(self, side, f0, f1, points, hold_hand="hang"):
        """Local-IK hand path: points = [(f, offset_from_shoulder)] (mirrored for the right arm)."""
        def fn(a, sd, fa, fb):
            a.ik_infl(sd, points[0][0], 0.0, 1.0)
            for f, off in points:
                a.ik_local_key(sd, f, off)
            a.ik_infl(sd, points[-1][0], 0.0, 1.0)
            a.fk_hand(sd, points[0][0], hold_hand)
        self.actions[side].append((f0, f1, fn))

    def world_ik(self, side, f0, f1, solver, hand="hang"):
        """World-IK action: solver(actor, side) -> [(f, Vector)] evaluated after the scene is posed."""
        self.actions[side].append((f0, f1, None))
        self.world_actions.append((side, f0, f1, solver, hand))

    # ---------------------------------------------------------------- low level
    def arm(self, side, f, fwd=0.0, down=38.0, bend=HANG, twist=0.0, out=0.0):
        """FK arm: fwd/out swing of the upper arm, total elbow bend in degrees."""
        s = 1 if side == "l" else -1
        self.h.rot(f"upperarm_{side}", f, (4 - fwd, down * s, out * s))
        self.h.rot(f"lowerarm_{side}", f, (-(bend - REST_BEND), 0, twist * s))

    def fk_hand(self, side, f, kind="hang"):
        h = self.h
        s = 1 if side == "l" else -1
        if kind == "pocket":
            h.rot(f"hand_{side}", f, (0, 14 * s, 0))
            curl, thumb = (40, 40, 40), 20
        elif kind == "open":
            h.rot(f"hand_{side}", f, (-8, 0, -4 * s))
            curl, thumb = (10, 14, 8), 4
        elif kind == "grip":
            h.rot(f"hand_{side}", f, (0, 0, -6 * s))
            curl, thumb = (38, 48, 30), 22
        else:
            h.rot(f"hand_{side}", f, (0, 0, -6 * s))
            curl, thumb = (22, 30, 20), 6
        for fi, fn in enumerate(H.FINGERS):
            for k in (1, 2, 3):
                c = curl[k - 1] * (1 + 0.15 * fi)
                z = FINGER_CLOSE[fn] * s if k == 1 else 0
                h.rot(f"{fn}_0{k}_{side}", f, (0, c * s, z))
        h.rot(f"thumb_01_{side}", f, (thumb, 0, -thumb * s))
        h.rot(f"thumb_02_{side}", f, (0, 12 * s, 0))

    def ensure_ik(self):
        if self.ik:
            return
        arm = self.h.arm
        coll = bpy.context.scene.collection
        for side in "lr":
            s = 1 if side == "l" else -1
            sh = self.shoulder[side]
            el = bpy.data.objects.new(f"{self.name}_ikl_{side}", None)
            ew = bpy.data.objects.new(f"{self.name}_ikw_{side}", None)
            po = bpy.data.objects.new(f"{self.name}_ikp_{side}", None)
            for o in (el, ew, po):
                coll.objects.link(o)
                o.empty_display_size = 0.03
            el.parent = arm
            po.parent = arm
            po.location = sh + Vector((s * 0.35, 0.6, -0.35))
            el.location = sh + Vector((0, -0.2, -0.4))
            pb = arm.pose.bones[f"lowerarm_{side}"]
            cl = pb.constraints.new("IK")
            cl.name = "ikl"
            cl.target, cl.pole_target, cl.pole_angle, cl.chain_count = el, po, math.radians(-90), 2
            cl.influence = 0.0
            cw = pb.constraints.new("IK")
            cw.name = "ikw"
            cw.target, cw.pole_target, cw.pole_angle, cw.chain_count = ew, po, math.radians(-90), 2
            cw.influence = 0.0
            self.ik[side] = {"el": el, "ew": ew, "cl": cl, "cw": cw}

    def ik_infl(self, side, f, w, l):
        ik = self.ik[side]
        ik["cw"].influence = w
        ik["cw"].keyframe_insert("influence", frame=f)
        ik["cl"].influence = l
        ik["cl"].keyframe_insert("influence", frame=f)

    def ik_local_key(self, side, f, off, absolute=False):
        s = 1 if side == "l" else -1
        if absolute:
            p = Vector(off)
        else:
            p = self.shoulder[side] + Vector((off[0] * s, off[1], off[2]))
        el = self.ik[side]["el"]
        el.location = p
        el.keyframe_insert("location", frame=f)

    def ik_world_key(self, side, f, p):
        ew = self.ik[side]["ew"]
        ew.location = p
        ew.keyframe_insert("location", frame=f)

    # ---------------------------------------------------------------- queries (valid after resolve_positions)
    def pos_at(self, f):
        return interp([(k[0], k[1]) for k in self._pk], f)

    def yaw_at(self, f):
        return interp(self.yaw_keys, f)

    def eye_at(self, f):
        p = self.pos_at(f)
        return Vector((p.x, p.y, p.z + self.eye_h))

    # ================================================================ resolution
    def resolve_positions(self):
        self._pk = dedupe(self.pos_keys)

    def resolve_yaw(self, stage):
        ops = sorted(self.yaw_ops, key=lambda o: o[1])
        cur = None
        keys = []

        def to(v):
            return v if cur is None else cur + wrap(v - cur)

        for op in ops:
            kind = op[0]
            if kind == "set":
                v = to(op[2])
                if cur is not None and op[1] > 1:
                    keys.append((op[1] - 1, cur))
                keys.append((op[1], v))
                cur = v
            elif kind == "turn":
                _, f0, f1, y = op
                keys.append((f0, cur))
                cur = to(y)
                keys.append((f1, cur))
            elif kind == "walk":
                _, f0, f1, ty, face = op
                keys.append((f0, cur))
                ft = f0 + max(4, min(10, (f1 - f0) // 3))
                cur = to(ty)
                keys.append((ft, cur))
                keys.append((max(ft, f1 - 6), cur))
                if face is not None:
                    tp = stage.point(face, f1 + 8)
                    cur = to(yaw_to(self.pos_at(f1), tp))
                    keys.append((f1 + 8, cur))
            elif kind == "face":
                _, f0, f1, target, thr, keep = op
                if self.walking_at(f0, 6) or self.walking_at(f1, 6) or self.seated_at(f0):
                    continue
                tp = stage.point(target, f1)
                me = self.pos_at(f1)
                if (Vector((tp.x, tp.y, 0)) - Vector((me.x, me.y, 0))).length < 0.2:
                    continue
                d = wrap(yaw_to(me, tp) - cur)
                if abs(d) < thr:
                    continue
                keys.append((f0, cur))
                cur = cur + d - math.copysign(min(keep, abs(d) * 0.3), d)
                keys.append((f1, cur))
        keys = dedupe(keys)
        # unwrap in time order (keys from overlapping ops)
        out = []
        for f, v in keys:
            if out:
                v = out[-1][1] + wrap(v - out[-1][1])
            out.append((f, v))
        self.yaw_keys = out

    def write_root(self):
        arm = self.h.arm
        lean = dedupe(self.lean_keys) if self.lean_keys else [(1, 0.0)]
        for f, p, jump in self._pk:
            arm.location = p
            arm.keyframe_insert("location", frame=f)
        frames = sorted({f for f, _ in self.yaw_keys} | {f for f, _ in lean})
        for f in frames:
            arm.rotation_euler = (math.radians(interp(lean, f)), 0, math.radians(self.yaw_at(f)))
            arm.keyframe_insert("rotation_euler", frame=f)
        jumps = {f for f, p, j in self._pk if j and f > 1}
        ad = arm.animation_data
        if ad and ad.action:
            for fc in iter_fcurves(ad.action):
                if fc.data_path != "location":
                    continue
                kps = list(fc.keyframe_points)
                for i, kp in enumerate(kps):
                    if i + 1 < len(kps) and int(round(kps[i + 1].co[0])) in jumps:
                        kp.interpolation = "CONSTANT"

    def resolve_head(self, stage, n):
        """Sample neck/head/spine every 3 frames from the look timeline (targets are tracked as they move)."""
        h = self.h
        looks = sorted(self.looks, key=lambda l: l[0])

        def rel(target, f, blend):
            if target is None:
                return 0.0, 0.0
            tp = stage.point(target, f)
            e = self.eye_at(f)
            yw = wrap(yaw_to(e, tp) - self.yaw_at(f))
            d = math.hypot(tp.x - e.x, tp.y - e.y)
            pt = math.degrees(math.atan2(tp.z - e.z, max(d, 0.05)))
            if abs(yw) > 150:  # behind: don't snap from side to side
                yw = math.copysign(150, yw)
            return yw * blend, pt * blend

        seated_twist = 0.4
        walking_pad = 2
        frames = list(range(1, n + 1, 3)) + [n]
        for f in frames:
            # active look and the one before it (to blend)
            cur, prv = None, None
            for lk in looks:
                if lk[0] <= f:
                    prv, cur = cur, lk
            if cur is None:
                yw, pt = 0.0, 0.0
            else:
                f0, f1, tgt, bl = cur
                yw, pt = rel(tgt, f, bl)
                if f < f1 and f1 > f0:
                    pyw, ppt = rel(prv[2], f, prv[3]) if prv else (0.0, 0.0)
                    k = smooth((f - f0) / (f1 - f0))
                    yw, pt = lerp(pyw, yw, k), lerp(ppt, pt, k)
            if self.walking_at(f, walking_pad):
                yw *= 0.6
                pt *= 0.6
            seated = self.seated_at(f)
            tw = max(-40, min(40, yw * seated_twist)) if seated else max(-20, min(20, yw * 0.2))
            hy = max(-75, min(75, yw - tw))
            pt = max(-35, min(30, pt))
            nod = 0.0
            for fn_, amt in self.nods:
                if fn_ <= f <= fn_ + 10:
                    nod += amt * math.sin(math.pi * (f - fn_) / 10)
            h.rot("neck_01", f, (-pt * 0.35, 0, hy * 0.4))
            h.rot("head", f, (-pt * 0.65 + nod, 0, hy * 0.6))
            lx, ly, lz = 0.0, 0.0, 0.0
            for f0, f1, xyz, ramp in self.spine:
                if f0 - ramp <= f <= f1 + ramp:
                    k = smooth((f - (f0 - ramp)) / ramp) if f < f0 else (smooth(((f1 + ramp) - f) / ramp) if f > f1 else 1.0)
                    lx += xyz[0] * k
                    ly += xyz[1] * k
                    lz += xyz[2] * k
            h.rot("spine_02", f, (lx, ly, lz + tw))

    def pose_at(self, f):
        name = "hang"
        for fp, nm in sorted(self.poses, key=lambda p: p[0]):
            if fp <= f:
                name = nm
        return name

    def write_base(self, side, f, name):
        spec = (self.pose_defs.get(name) or POSES[name])[side]
        kind, val = spec
        if kind == "fk":
            if val == "pocket":
                s = 1 if side == "l" else -1
                self.h.rot(f"upperarm_{side}", f, (10, 41 * s, 0))
                self.h.rot(f"lowerarm_{side}", f, (-(26 - REST_BEND), 0, 0))
                self.fk_hand(side, f, "pocket")
            else:
                self.arm(side, f, 0, 38, HANG)
                self.fk_hand(side, f, "hang")
            self.ik_infl(side, f, 0.0, 0.0)
        else:
            self.arm(side, f, 0, 38, HANG)
            self.fk_hand(side, f, "hang")
            self.ik_local_key(side, f, val, absolute=(kind == "ikabs"))
            self.ik_infl(side, f, 0.0, 1.0)

    def resolve_arms(self, n):
        self.ensure_ik()
        poses = sorted(self.poses, key=lambda p: p[0])
        for side in ("l", "r"):
            wins = sorted(self.actions[side], key=lambda a: a[0])

            def inside(f):
                return any(a < f < b for a, b, _ in wins)

            keys = {1: self.pose_at(1)}
            for fp, nm in poses:
                if fp <= 1:
                    continue
                keys[fp] = self.pose_at(fp - 1)  # old pose held until the change starts
                keys[fp + 10] = nm
            for a, b, _ in wins:
                keys[max(1, a)] = self.pose_at(a)
                if b < n + 50:
                    keys[b] = self.pose_at(b)
            for f in sorted(keys):
                if not inside(f):
                    self.write_base(side, f, keys[f])
            for a, b, fn in wins:
                if fn is not None:
                    fn(self, side, a, b)
        # legs: stances between leg windows
        lw = sorted(self.actions["legs"], key=lambda a: a[0])

        def in_legs(f):
            return any(a <= f <= b for a, b, _ in lw)

        st = sorted(self.stances, key=lambda s: s[0])

        def stance_at(f):
            name = "even"
            for fs, nm in st:
                if fs <= f:
                    name = nm
            return name

        keys = {1: stance_at(1)}
        for fs, nm in st:
            if fs <= 1:
                continue
            keys[fs] = stance_at(fs - 1)
            keys[fs + 12] = nm
        for a, b, _ in lw:
            if a > 2:
                keys[a - 1] = stance_at(a - 1)
            if b < n + 50:
                keys[b + 1] = stance_at(b + 1)
        for f in sorted(keys):
            if not in_legs(f):
                self.write_stance(f, keys[f])
        for a, b, fn in lw:
            fn(self, "legs", a, b)

    def write_stance(self, f, name):
        h = self.h
        for s in ("l", "r"):
            relaxed = (name == "l" and s == "l") or (name == "r" and s == "r")
            if relaxed:
                h.rot(f"thigh_{s}", f, (-5, 0, 0))
                h.rot(f"calf_{s}", f, (11, 0, 0))
                h.rot(f"foot_{s}", f, (-6, 0, 0))
            else:
                h.rot(f"thigh_{s}", f, (0, 0, 0))
                h.rot(f"calf_{s}", f, (0, 0, 0))
                h.rot(f"foot_{s}", f, (0, 0, 0))

    def idle(self, f0, f1):
        h = self.h
        amp = self.idle_amp
        ph = self.r.uniform(0, 6)
        pb = 3.8 + self.r.random() * 1.2
        ps = 6.5 + self.r.random() * 3.0
        for f in range(f0, f1 + 1, 6):
            t = f / FPS
            br = math.sin(t * 2 * math.pi / pb + ph)
            sw = math.sin(t * 2 * math.pi / ps + ph)
            h.rot("spine_03", f, (0.9 * br * amp, 0, 0))
            h.rot("spine_01", f, (0, 0.6 * sw * amp, 0.8 * sw * amp))

    # ---------------------------------------------------------------- face
    def blinks(self, f0, f1):
        f = f0 + self.r.randint(10, 40)
        while f < f1:
            for k in ("eye-left-closure", "eye-right-closure"):
                self.h.key(k, f - 1, 0.0)
                self.h.key(k, f + 1, 1.0)
                self.h.key(k, f + 4, 0.0)
            f += self.r.randint(55, 110)

    def lipsync(self, wav, t0):
        env = envelope(wav) if isinstance(wav, str) else wav
        f0 = F(t0)
        self.h.key("mouth-open", f0 - 2, 0.0)
        prev = 0.0
        for i, v in enumerate(env):
            f = f0 + i
            v = max(0.0, min(1.0, v))
            open_ = 0.55 * v ** 0.8
            if abs(open_ - prev) > 0.03 or i % 3 == 0:
                self.h.key("mouth-open", f, open_)
                self.h.key("mouth-pursing", f, 0.25 * max(0.0, math.sin(i * 0.9)) * v)
                prev = open_
        self.h.key("mouth-open", f0 + len(env) + 1, 0.0)
        self.h.key("mouth-pursing", f0 + len(env) + 1, 0.0)
        return len(env)

    def expr(self, f, **kw):
        for k, v in kw.items():
            self.h.key(k.replace("_", "-"), f, v)


def envelope(wav):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", wav, "-f", "s16le", "-ac", "1", "-ar", "24000", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, "<i2").astype(np.float32) / 32768.0
    hop = 24000 // FPS
    n = len(x) // hop
    rms = np.array([np.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2)) for i in range(n)])
    rms = rms / (rms.max() + 1e-6)
    sm = np.convolve(rms, [0.25, 0.5, 0.25], mode="same")
    return np.clip((sm - 0.08) / 0.7, 0, 1)


# ============================================================================ props

def note_material():
    m = bpy.data.materials.get("banknote")
    if m:
        return m
    m = bpy.data.materials.new("banknote")
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = 60.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.32, 0.36, 0.42, 1)
    ramp.color_ramp.elements[1].color = (0.62, 0.6, 0.55, 1)
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.8
    return m


def banknotes(name, n=3):
    """A small folded stack of notes, built around the palm of a hand bone (bone Y runs along the hand)."""
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    r = random.Random(hash(name) % 1000)
    for i in range(n):
        w, l, t = 0.032, 0.07, 0.0016
        z = -0.025 - i * 0.0022
        ang = r.uniform(-0.25, 0.25)
        ca, sa = math.cos(ang), math.sin(ang)
        vs = []
        for x, y in ((-w, -l), (w, -l), (w, l), (-w, l)):
            xx, yy = x * ca - y * sa, x * sa + y * ca
            vs.append(bm.verts.new((xx, yy + 0.085, z)))
            vs.append(bm.verts.new((xx, yy + 0.085, z - t)))
        top = [vs[0], vs[2], vs[4], vs[6]]
        bot = [vs[1], vs[3], vs[5], vs[7]]
        bm.faces.new(top)
        bm.faces.new(bot[::-1])
        for a in range(4):
            b = (a + 1) % 4
            bm.faces.new((top[a], top[b], bot[b], bot[a]))
    bm.to_mesh(me)
    bm.free()
    me.materials.append(note_material())
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def carry(ob, holders, show, hide):
    """holders: [(f, actor, side)] - the prop follows that hand from frame f on; visible between show and hide."""
    cons = []
    for i, (f, a, side) in enumerate(holders):
        c = ob.constraints.new("COPY_TRANSFORMS")
        c.target = a.h.arm
        c.subtarget = f"hand_{side}"
        cons.append((f, c))
    for i, (f, c) in enumerate(cons):
        nxt = cons[i + 1][0] if i + 1 < len(cons) else None
        for fr, v in ((1, 0.0), (f, 1.0)) + (((nxt, 0.0),) if nxt else ()):
            c.influence = v
            c.keyframe_insert("influence", frame=fr)
    for fr, v in ((1, True), (show, False), (hide, True)):
        ob.hide_render = v
        ob.keyframe_insert("hide_render", frame=fr)
        ob.hide_viewport = v
        ob.keyframe_insert("hide_viewport", frame=fr)
    ad = ob.animation_data
    if ad and ad.action:
        for fc in iter_fcurves(ad.action):
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"


# ============================================================================ camera

class HandheldCam:
    """Reportage camera: keyframed path + target, organic shake, focus pulls, jump cuts."""

    def __init__(self, name="cam", lens=18, fstop=2.8):
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.sensor_width = 36
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = fstop
        cd.clip_start = 0.05
        self.cam = bpy.data.objects.new(name, cd)
        bpy.context.scene.collection.objects.link(self.cam)
        self.tgt = bpy.data.objects.new(name + "_tgt", None)
        bpy.context.scene.collection.objects.link(self.tgt)
        con = self.cam.constraints.new("TRACK_TO")
        con.target = self.tgt
        con.track_axis = "TRACK_NEGATIVE_Z"
        con.up_axis = "UP_Y"
        self.focus = bpy.data.objects.new(name + "_focus", None)
        bpy.context.scene.collection.objects.link(self.focus)
        cd.dof.focus_object = self.focus
        self.keys = []

    def at(self, f, loc, look, focus=None, interp="BEZIER"):
        self.cam.location = loc
        self.cam.keyframe_insert("location", frame=f)
        self.tgt.location = look
        self.tgt.keyframe_insert("location", frame=f)
        self.focus.location = focus if focus is not None else look
        self.focus.keyframe_insert("location", frame=f)
        self.keys.append(f)

    def cut(self, f, loc, look, focus=None):
        """Hard cut / jump cut: constant before, new position from f."""
        for ob in (self.cam, self.tgt, self.focus):
            ob.keyframe_insert("location", frame=f - 1)
        self.at(f, loc, look, focus)
        self._const(f - 1)

    def _const(self, f):
        for ob in (self.cam, self.tgt, self.focus):
            ad = ob.animation_data
            if not ad or not ad.action:
                continue
            for fc in iter_fcurves(ad.action):
                for kp in fc.keyframe_points:
                    if int(round(kp.co[0])) == f:
                        kp.interpolation = "CONSTANT"

    def shake(self, f0, f1, amp=0.018, rot=0.35, seed=3):
        """Adds handheld wobble with delta transforms so the track-to constraint still works."""
        r = random.Random(seed)
        ph = [r.uniform(0, 6.28) for _ in range(9)]
        cam = self.cam
        cam.rotation_mode = "XYZ"
        for f in range(f0, f1 + 1, 2):
            t = f / FPS
            dx = amp * (0.6 * math.sin(t * 1.7 + ph[0]) + 0.3 * math.sin(t * 4.3 + ph[1]) + 0.1 * math.sin(t * 9.1 + ph[2]))
            dy = amp * (0.6 * math.sin(t * 1.3 + ph[3]) + 0.3 * math.sin(t * 3.7 + ph[4]))
            dz = amp * (0.5 * math.sin(t * 2.1 + ph[5]) + 0.3 * math.sin(t * 5.3 + ph[6]))
            cam.delta_location = (dx, dy, dz)
            cam.keyframe_insert("delta_location", frame=f)
            rz = math.radians(rot * (math.sin(t * 1.1 + ph[7]) + 0.4 * math.sin(t * 3.9 + ph[8])))
            cam.delta_rotation_euler = (0, 0, rz)
            cam.keyframe_insert("delta_rotation_euler", frame=f)


def iter_fcurves(action):
    if hasattr(action, "fcurves") and action.fcurves is not None:
        try:
            yield from action.fcurves
            return
        except TypeError:
            pass
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", []):
                yield from bag.fcurves


def fix_quaternions(arm):
    """Make consecutive quaternion keys of every bone lie in the same hemisphere (q and -q are the same rotation,
    mixing them makes bones spin/jitter between keys), and use smooth interpolation."""
    ad = arm.animation_data
    if not ad or not ad.action:
        return
    groups = {}
    for fc in iter_fcurves(ad.action):
        if fc.data_path.endswith("rotation_quaternion"):
            groups.setdefault(fc.data_path, {})[fc.array_index] = fc
    for path, comps in groups.items():
        if len(comps) != 4:
            continue
        frames = sorted({kp.co[0] for kp in comps[0].keyframe_points})
        prev = None
        for fr in frames:
            q = [comps[i].evaluate(fr) for i in range(4)]
            kps = [next((kp for kp in comps[i].keyframe_points if abs(kp.co[0] - fr) < 1e-3), None) for i in range(4)]
            if prev is not None and sum(a * b for a, b in zip(q, prev)) < 0:
                q = [-c for c in q]
                for i in range(4):
                    if kps[i] is not None:
                        kps[i].co[1] = q[i]
            prev = q
        for fc in comps.values():
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"
            fc.update()

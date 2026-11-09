"""Acting for code-built humans: idle/breathing, look-at, lip sync from the line's audio, blinks, gestures,
hands in pockets, walking; plus a handheld reportage camera."""
import math
import random
import subprocess

import bpy
import numpy as np
from mathutils import Vector

import human as H

FPS = 24


def F(t):
    return int(round(t * FPS)) + 1


def yaw_to(src, dst):
    return math.degrees(math.atan2(dst[0] - src[0], -(dst[1] - src[1])))


def wrap(a):
    return (a + 180) % 360 - 180


# ============================================================================ body

class Actor:
    def __init__(self, h, pos, yaw, seed=0, pose="relax"):
        self.h = h
        self.pos = Vector(pos)
        self.yaw = yaw
        self.r = random.Random(seed)
        self.seed = seed
        self.head_keys = []  # (f, yaw, pitch)
        self.arm_pose = {}  # side -> list of (f, (x, y, z), elbow)
        h.place(1, pos, yaw)
        self.pose_name = pose

    # ---------------------------------------------------------------- base pose + idle
    def idle(self, f0, f1, amp=1.0):
        h = self.h
        ph = self.r.uniform(0, 6)
        for f in range(f0, f1 + 1, 6):
            t = f / FPS
            br = math.sin(t * 2 * math.pi / 3.6 + ph)
            sw = math.sin(t * 2 * math.pi / 7.3 + ph)
            h.rot("spine_03", f, (1.2 * br * amp, 0, 0))
            h.rot("spine_01", f, (0, 0.8 * sw * amp, 0.6 * sw * amp))
            h.rot("pelvis", f, (0, 0, 1.2 * sw * amp))

    def stand(self, f):
        H.relax(self.h, f)

    def pockets(self, f, side="both"):
        """Hands in the jacket pockets."""
        sides = (("l", 1), ("r", -1)) if side == "both" else ((side, 1 if side == "l" else -1),)
        for sd, s in sides:
            self.h.rot(f"upperarm_{sd}", f, (10, 41 * s, 0))
            self.h.rot(f"lowerarm_{sd}", f, (-20, 0, 0))
            self.h.rot(f"hand_{sd}", f, (0, 14 * s, 0))
            for fn in H.FINGERS:
                for k in (1, 2, 3):
                    self.h.rot(f"{fn}_0{k}_{sd}", f, (0, 40 * s, 0))

    def arm(self, side, f, fwd=0.0, down=38.0, elbow=0.0, twist=0.0, out=0.0):
        s = 1 if side == "l" else -1
        self.h.rot(f"upperarm_{side}", f, (4 - fwd, down * s, out * s))
        self.h.rot(f"lowerarm_{side}", f, (-elbow, 0, twist * s))

    def gesture(self, f0, f1, side="r", energy=1.0):
        """Talking hand: forearm comes up and moves on stressed beats, then drops back."""
        n = max(1, int((f1 - f0) / 10))
        self.arm(side, f0, 0, 38, 0)
        for i in range(n + 1):
            f = f0 + 4 + i * 10
            if f > f1:
                break
            fw = (18 + 12 * self.r.random()) * energy
            el = (55 + 25 * self.r.random()) * energy
            self.arm(side, f, fw, 36 - 4 * self.r.random(), el, twist=self.r.uniform(-15, 15))
        self.arm(side, f1 + 8, 0, 38, 0)

    def look(self, f0, f1, target, blend=1.0):
        """Turn neck+head toward a world point between f0 and f1 (holds the previous look until f0)."""
        p = self.pos + Vector((0, 0, 1.62))
        yw = wrap(yaw_to(p, target) - self.yaw)
        yw = max(-70, min(70, yw)) * blend
        dist = math.hypot(target[0] - p.x, target[1] - p.y)
        pitch = math.degrees(math.atan2(target[2] - p.z, dist)) * blend
        prev = self.head_keys[-1] if self.head_keys else (1, 0.0, 0.0)
        if f0 > prev[0]:
            self._head(f0, prev[1], prev[2])
        self._head(f1, yw, pitch)

    def _head(self, f, yw, pitch):
        self.head_keys.append((f, yw, pitch))
        self.h.rot("neck_01", f, (-pitch * 0.35, 0, yw * 0.4))
        self.h.rot("head", f, (-pitch * 0.65, 0, yw * 0.6))

    def nod(self, f, amt=8):
        prev = self.head_keys[-1] if self.head_keys else (1, 0.0, 0.0)
        self.h.rot("head", f, (-prev[2] * 0.65, 0, prev[1] * 0.6))
        self.h.rot("head", f + 4, (-prev[2] * 0.65 + amt, 0, prev[1] * 0.6))
        self.h.rot("head", f + 9, (-prev[2] * 0.65, 0, prev[1] * 0.6))

    def turn(self, f0, f1, yaw):
        h = self.h
        h.arm.rotation_euler = (0, 0, math.radians(self.yaw))
        h.arm.keyframe_insert("rotation_euler", frame=f0)
        self.yaw = yaw
        h.arm.rotation_euler = (0, 0, math.radians(yaw))
        h.arm.keyframe_insert("rotation_euler", frame=f1)

    def walk(self, f0, f1, dest, stride=0.68):
        """Procedural walk along a straight line."""
        h = self.h
        p0, p1 = self.pos.copy(), Vector(dest)
        yaw = yaw_to(p0, p1)
        h.arm.location = p0
        h.arm.keyframe_insert("location", frame=f0)
        h.arm.rotation_euler = (0, 0, math.radians(yaw))
        h.arm.keyframe_insert("rotation_euler", frame=f0)
        dist = (p1 - p0).length
        steps = max(1, dist / stride)
        dur = f1 - f0
        for f in range(f0, f1 + 1, 2):
            t = (f - f0) / dur
            ph = t * steps * math.pi
            k = min(1.0, min(t, 1 - t) * 8)  # ease in/out of the cycle
            sw = math.sin(ph) * k
            h.rot("thigh_l", f, (-24 * sw, 0, 0))
            h.rot("thigh_r", f, (24 * sw, 0, 0))
            h.rot("calf_l", f, (38 * max(0, -math.cos(ph)) * k + 4, 0, 0))
            h.rot("calf_r", f, (38 * max(0, math.cos(ph)) * k + 4, 0, 0))
            h.rot("foot_l", f, (-8 * sw, 0, 0))
            h.rot("foot_r", f, (8 * sw, 0, 0))
            self.arm("l", f, 14 * sw, 37, 12)
            self.arm("r", f, -14 * sw, 37, 12)
            h.rot("spine_02", f, (3 * k, 0, 4 * sw))
            pos = p0.lerp(p1, t)
            pos.z += 0.018 * abs(math.cos(ph)) * k
            h.arm.location = pos
            h.arm.keyframe_insert("location", frame=f)
        h.arm.location = p1
        h.arm.keyframe_insert("location", frame=f1)
        self.pos = p1
        self.yaw = yaw

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
    # syllable-ish: emphasise changes
    sm = np.convolve(rms, [0.25, 0.5, 0.25], mode="same")
    return np.clip((sm - 0.08) / 0.7, 0, 1)


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
        """Adds handheld wobble with a child empty to keep the path clean."""
        r = random.Random(seed)
        ph = [r.uniform(0, 6.28) for _ in range(9)]
        cam = self.cam
        cam.rotation_mode = "XYZ"
        # use delta transforms so the track-to constraint still works
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


def seat(actor, f, seat_xy, seat_z, yaw, hands_on_table=True):
    """Sit on a bench: hips at seat height, thighs forward, shins down, hands on the table."""
    h = actor.h
    hip = h.arm.data.bones["pelvis"].head_local.z
    knee = h.arm.data.bones["calf_l"].head_local.z
    actor.pos = Vector((seat_xy[0], seat_xy[1], 0))
    actor.yaw = yaw
    h.arm.location = (seat_xy[0], seat_xy[1], seat_z - hip + 0.04)
    h.arm.rotation_euler = (0, 0, math.radians(yaw))
    h.arm.keyframe_insert("location", frame=f)
    h.arm.keyframe_insert("rotation_euler", frame=f)
    for s in ("l", "r"):
        h.rot(f"thigh_{s}", f, (-86, 0, 0))
        h.rot(f"calf_{s}", f, (84, 0, 0))
        h.rot(f"foot_{s}", f, (-6, 0, 0))
    if hands_on_table:
        actor.arm("l", f, 42, 30, 62, out=-8)
        actor.arm("r", f, 42, 30, 62, out=-8)


def reach(actor, side, f0, dur=10, hold=8, fwd=58, down=26, elbow=22):
    """Hand something over / take something: arm goes forward and back."""
    actor.arm(side, f0, 0, 38, 0)
    actor.arm(side, f0 + dur // 2, fwd, down, elbow)
    actor.arm(side, f0 + dur // 2 + hold, fwd, down, elbow)
    actor.arm(side, f0 + dur + hold, 0, 38, 0)


def reach_seated(actor, side, f0, dur=10, hold=8):
    actor.arm(side, f0, 42, 30, 62, out=-8)
    actor.arm(side, f0 + dur // 2, 75, 22, 25, out=-5)
    actor.arm(side, f0 + dur // 2 + hold, 75, 22, 25, out=-5)
    actor.arm(side, f0 + dur + hold, 42, 30, 62, out=-8)

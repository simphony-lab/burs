"""3D part of every shot of the 6-minute movie. Each function builds a fresh scene, animates it and returns
(frames, cam_for(frame) -> camera object). Durations come from timeline.py."""
import math
import random

from mathutils import Vector

import lib
from lib import FPS, K, OCEAN_X, World, yaw_to
from timeline import DUR, HITS


def F(t):
    """shot-local seconds -> frame number (1-based)"""
    return int(round(t * FPS)) + 1


def frames_of(sid):
    return int(round(DUR[sid] * FPS))


def single(cam):
    return lambda f: cam


def cam_path(cam, tgt, f0, p0, t0, f1, p1, t1):
    K.set(cam, "location", f0, p0)
    K.set(cam, "location", f1, p1)
    K.set(tgt, "location", f0, t0)
    K.set(tgt, "location", f1, t1)


def shake(cam, f0, f1, amp=0.03, step=5, seed=1):
    r = random.Random(seed)
    for f in range(f0, f1 + 1, step):
        base = Vector(K.value_at(cam, "location", f))
        K.set(cam, "location", f, tuple(base + Vector((r.uniform(-amp, amp), r.uniform(-amp, amp), r.uniform(-amp, amp)))))


def aim(tgt, ch, f0, f1, step=2, z=1.45, lag=0):
    for f in range(f0, f1 + 1, step):
        p = ch.p(max(1, f - lag))
        K.set(tgt, "location", f, (p.x, p.y, p.z + z))


SPAWN = {
    "pixel_masha": ((-1.1, -3.7, 0), None),
    "dimon_pro": ((0.5, -4.2, 0), None),
    "snowbunny": ((-3.3, 0.4, 0), math.radians(-90)),
}


def spawn_pair(w, f_end):
    m = w.char("pixel_masha", (-1.1, -3.7, 0))
    d = w.char("dimon_pro", (0.5, -4.2, 0))
    m.place(1, m.p(1), yaw_to(m.p(1), d.p(1)))
    d.place(1, d.p(1), yaw_to(d.p(1), m.p(1)))
    m.idle(1, f_end, 0.3)
    return m, d


def npcs_walking(w, f_end, n=3, seed=3):
    r = random.Random(seed)
    spots = [((8, -8, 0), (3, -6.5, 0)), ((-8, 6, 0), (-8, -5, 0)), ((6, 7, 0), (6.5, 2, 0)),
             ((-6, -8, 0), (-3, -9, 0)), ((7, -2, 0), (8, 5, 0))]
    out = []
    for i in range(n):
        a, b = spots[(i + seed) % len(spots)]
        c = w.npc(a)
        c.walk(1, min(f_end, 1 + int(r.uniform(6, 9) * FPS)), b)
        out.append(c)
    return out


def bro_fp(w, pos, look, items=("sword",)):
    """Invisible cheater body + first-person camera with hand. Returns (bro, cam, tgt, hand, items)."""
    bro = w.char("brohacker", pos)
    bro.root.scale = (0, 0, 0)
    cam, tgt = w.cam("fp", 20)
    eye = Vector(pos) + Vector((0, 0, 1.62))
    K.set(cam, "location", 1, tuple(eye))
    K.set(tgt, "location", 1, tuple(look))
    hand, objs = w.fp_rig(cam, items)
    return bro, cam, tgt, hand, objs


def fp_swing(hand, f):
    K.hold(hand, "rotation_euler", f)
    K.hold(hand, "location", f)
    base_r = K.value_at(hand, "rotation_euler", f)
    base_l = K.value_at(hand, "location", f)
    K.set(hand, "rotation_euler", f + 2, (base_r[0] - 0.9, base_r[1], base_r[2] + 0.6))
    K.set(hand, "location", f + 2, (base_l[0] - 0.12, base_l[1] + 0.06, base_l[2] - 0.05))
    K.set(hand, "rotation_euler", f + 6, base_r)
    K.set(hand, "location", f + 6, base_l)


def fp_switch(objs, f, kind):
    for k, ob in objs.items():
        K.set(ob, "scale", f - 1, K.value_at(ob, "scale", f - 1))
        K.set(ob, "scale", f, (1, 1, 1) if k == kind else (0, 0, 0))


def fp_jump(cam, f, h=0.38):
    p = Vector(K.value_at(cam, "location", f))
    K.set(cam, "location", f, tuple(p))
    K.set(cam, "location", f + 4, tuple(p + Vector((0, 0, h))))
    K.set(cam, "location", f + 8, tuple(p))


# ============================================================================ Act 1

def S1a():
    w = World()
    w.sprout_meshes()
    n = frames_of("S1a")
    spawn_pair(w, n)
    w.chars["dimon_pro"].talk(10, n - 20)
    snow = w.char("snowbunny")
    snow.sit(1, (-6, 9.0, 5.0), 0.0)
    kot = w.char("kotik_777", (-13.0, 12.5, 0))
    kot.place(1, kot.p(1), yaw_to(kot.p(1), (-14, 12.5, 0)))
    for f in range(10, n, 20):
        kot.swing(f)
    lava = w.char("lavaKing", (0, 40.2, 0), math.pi)
    lava.hold("axe")
    lava.hold("shield", "l")
    for f in range(8, n, 22):
        lava.swing(f)
    w.dummy((0, 42.0, 0), 0.0)
    npcs_walking(w, n, 3)
    cam, t = w.cam("c", 20)
    cam_path(cam, t, 1, (16, -24, 16), (0, 2, 0), n, (9, -17, 8.5), (-1, 3, 1.2))
    w.finish(n)
    return w, n, single(cam)


def S1b():
    w = World()
    n = frames_of("S1b")
    m, d = spawn_pair(w, n)
    d.talk(4, n - 10, 1.0)
    for f in range(30, n, 36):
        K.set(m.head, "rotation_euler", f, (0.12, 0, 0))
        K.set(m.head, "rotation_euler", f + 6, (-0.05, 0, 0))
    npcs_walking(w, n, 2, seed=1)
    cam, t = w.cam("c", 26)
    cam_path(cam, t, 1, (2.6, -8.2, 2.0), (-0.3, -3.9, 1.4), n, (2.0, -7.5, 1.9), (-0.3, -3.9, 1.45))
    w.finish(n)
    return w, n, single(cam)


def S1c():
    w = World()
    n = frames_of("S1c")
    lava = w.char("lavaKing", (0, 40.3, 0), math.pi)
    lava.hold("axe")
    lava.hold("shield", "l")
    dummy = w.dummy((0, 42.0, 0), 0.0)
    for i, f in enumerate(range(8, n - 8, 22)):
        if i % 2 == 0:
            lava.swing(f, crit=False)
            K.set(dummy, "rotation_euler", f + 3, (0, 0, 0))
            K.set(dummy, "rotation_euler", f + 5, (0.12, 0, 0.05))
            K.set(dummy, "rotation_euler", f + 10, (0, 0, 0))
        else:
            lava.block(f, f + 12)
    cam, t = w.cam("c", 24)
    cam_path(cam, t, 1, (3.6, 36.6, 1.9), (0, 41.6, 1.3), n, (2.8, 37.3, 1.7), (0, 41.6, 1.25))
    w.finish(n)
    return w, n, single(cam)


def S1d():
    w = World()
    n = frames_of("S1d")
    m, d = spawn_pair(w, n)
    d.talk(4, 40)
    bro = w.char("brohacker", (0.6, -7.2, 0), 0.0)
    bro.appear(F(1.0), flash=False)
    bro.look(F(1.6), F(2.4), (-3, -2, 1.5))
    bro.look(F(3.4), F(4.2), m.head_pos(1))
    m.look(F(2.0), F(2.6), bro.head_pos(1), body_follow=0.8)
    K.tween(m.rarm, "rotation_euler", F(2.6), F(2.9), (-2.7, 0, -0.4))
    for i, f in enumerate(range(F(2.9), F(4.4), 4)):
        K.set(m.rarm, "rotation_euler", f, (-2.7, 0, -0.1 if i % 2 else -0.6))
    K.tween(m.rarm, "rotation_euler", F(4.5), F(4.9), (0, 0, -0.04))
    d.look(F(2.3), F(3.0), bro.head_pos(1), body_follow=0.5)
    npcs_walking(w, n, 2, seed=2)
    cam, t = w.cam("c", 22)
    cam_path(cam, t, 1, (-4.6, -11.2, 2.6), (-0.2, -5.0, 1.3), n, (-4.0, -10.4, 2.5), (-0.2, -5.0, 1.35))
    w.finish(n)
    return w, n, single(cam)


def S1e():
    w = World()
    n = frames_of("S1e")
    bro = w.char("brohacker", (0.6, -7.2, 0), 0.0)
    bro.idle(1, n)
    K.set(bro.head, "rotation_euler", 1, (0.0, 0, 0.0))
    K.set(bro.head, "rotation_euler", F(2.5), (0.12, 0, -0.1))
    K.set(bro.head, "rotation_euler", F(4.0), (0.05, 0, 0.15))
    spawn_pair(w, n)
    cam, t = w.cam("c", 32)
    cam_path(cam, t, 1, (1.3, -9.9, 1.8), (0.6, -7.2, 1.6), n, (0.95, -9.2, 1.72), (0.6, -7.2, 1.62))
    w.finish(n)
    return w, n, single(cam)


# ============================================================================ Act 2

def S2():
    w = World()
    n = frames_of("S2")
    m, d = spawn_pair(w, n)
    m.look(1, 8, (0.6, -7.2, 1.6), body_follow=0.6)
    K.set(m.rarm, "rotation_euler", 10, (-2.7, 0, -0.3))
    K.set(m.rarm, "rotation_euler", 30, (-2.7, 0, -0.3))
    K.set(m.rarm, "rotation_euler", 40, (0, 0, -0.04))
    d.talk(20, 200)
    snow = w.char("snowbunny", (-3.3, 0.4, 0), math.radians(-90))
    snow.walk(F(6), F(14), (-2.5, 4.5, 0))
    snow.walk(F(15), F(24), (3.8, 3.0, 0))
    npcs_walking(w, n, 3, seed=4)
    bro, cam, tgt, hand, objs = bro_fp(w, (0.6, -7.2, 0), (0, 0, 1.0))
    eye = Vector((0.6, -7.2, 1.62))
    for i, f in enumerate(range(1, n + 1, 48)):
        look = Vector((-0.5 + 1.6 * math.sin(i * 0.9), 0.0 + 1.5 * math.cos(i * 0.6), 1.0 + 0.2 * math.sin(i)))
        K.set(tgt, "location", f, tuple(look))
        K.set(cam, "location", f, tuple(eye + Vector((0, 0, 0.02 * math.sin(i)))))
    w.finish(n)
    return w, n, single(cam)


# ============================================================================ Act 3

def S3a():
    w = World()
    n = frames_of("S3a")
    m, d = spawn_pair(w, n)
    bro = w.char("brohacker", (0.6, -6.6, 0), math.pi)
    others = [w.npc((-2.2, -8.0, 0)), w.npc((3.2, -8.8, 0))]
    K.set(bro.root, "location", F(0.6), (0.6, -6.6, 0))
    K.set(bro.root, "location", F(1.4), (0.6, -6.6, 0.8))
    K.set(bro.root, "location", F(3.6), (0.6, -6.6, 6.5))
    bro.hover(F(3.8), n, (0.6, -6.6, 6.5))
    bro.fly_pose(F(1.4), n)
    for i, c in enumerate([m, d] + others):
        c.look(F(1.2 + 0.15 * i), F(2.0 + 0.15 * i), (0.6, -6.6, 6.0), body_follow=0.6)
    d.surprised(F(2.3), "!")
    m.surprised(F(2.8), "?")
    cam, t = w.cam("c", 20)
    cam_path(cam, t, 1, (3.6, -12.4, 1.0), (0.6, -6.6, 2.0), n, (3.2, -12.0, 0.9), (0.6, -6.6, 6.0))
    w.finish(n)
    return w, n, single(cam)


def tpa_wave(w, chars, t0, step=0.12, symbol=True, dur=3.5):
    for i, c in enumerate(chars):
        f = F(t0 + i * step)
        w.fx.swirl(c, f, f + int(dur * FPS))
        if symbol:
            c.surprised(f + 4, "?" if i % 3 else "!")


def spawn_crowd(w, n_npc=5, seed=5):
    m = w.char("pixel_masha", (-1.1, -3.7, 0))
    d = w.char("dimon_pro", (0.5, -4.2, 0))
    s = w.char("snowbunny", (-3.3, 0.4, 0), math.radians(-90))
    r = random.Random(seed)
    spots = [(4.5, 3.5), (-5.5, -5.5), (6.5, -4.0), (-6.0, 5.5), (3.0, 7.0), (-2.5, 7.5), (7.5, 1.0), (-7.5, 0.5)]
    npcs = []
    for i in range(n_npc):
        x, y = spots[i % len(spots)]
        c = w.npc((x, y, 0), r.uniform(-3, 3))
        npcs.append(c)
    m.place(1, m.p(1), yaw_to(m.p(1), d.p(1)))
    d.place(1, d.p(1), yaw_to(d.p(1), m.p(1)))
    return [m, d, s] + npcs


def S3b():
    w = World()
    n = frames_of("S3b")
    crowd = spawn_crowd(w, 5)
    bro, cam, tgt, hand, objs = bro_fp(w, (0.6, -6.6, 6.5), (0.3, -0.5, 0))
    K.set(tgt, "location", 1, (0.3, -1.8, 0))
    K.set(tgt, "location", n, (-0.2, 0.2, 0))
    tpa_wave(w, crowd, 2.2, 0.1)
    for i, c in enumerate(crowd):
        c.look(F(2.8 + 0.1 * i), F(3.4 + 0.1 * i), (0.6, -6.6, 8.0), body_follow=0.4)
    w.finish(n)
    return w, n, single(cam)


def S3c():
    w = World()
    n = frames_of("S3c")
    crowd = spawn_crowd(w, 5)
    for c in crowd:
        f = 1
        w.fx.swirl(c, f, n + 10)
        w.fx.symbol(c, 1, "?")
        K.set(c.mouth, "scale", 1, (1, 1, 1))
    bro = w.char("brohacker", (0.6, -6.6, 6.5), math.pi)
    bro.hover(1, n, (0.6, -6.6, 6.5))
    bro.fly_pose(1, n)
    for i, c in enumerate(crowd):
        c.look(F(0.4 + 0.2 * i), F(1.0 + 0.2 * i), (0.6, -6.6, 8.0), body_follow=0.5)
        if i % 3 == 1:
            c.jump(F(2.0 + 0.3 * i))
    cam, t = w.cam("c", 22)
    cam_path(cam, t, 1, (1.6, -14.5, 3.4), (-0.4, 1.0, 3.6), n, (1.2, -13.0, 3.2), (-0.4, 1.0, 3.9))
    w.finish(n)
    return w, n, single(cam)


KOT = (-9.0, 14.0, 0)
BRO_IN = (-6.0, 12.3, 0)


def S3d():
    w = World()
    n = frames_of("S3d")
    kot = w.char("kotik_777", KOT)
    kot.place(1, KOT, yaw_to(KOT, (-10, 15, 0)))
    for f in range(4, F(1.8), 10):
        kot.swing(f)
    w.fx.swirl(kot, F(0.5), F(3.2))
    kot.look(F(1.6), F(2.0), (-7, 12, 1.0))
    kot.head_rot(F(3.6), F(4.0), 0.1, 0.0)
    for f in range(F(4.2), n, 10):
        kot.swing(f)
    bro = w.char("brohacker", BRO_IN, yaw_to(BRO_IN, KOT))
    bro.hold("sword")
    bro.appear(F(4.6))
    bro.idle(F(4.6), n)
    cam, t = w.cam("c", 16)
    cam_path(cam, t, 1, (-4.4, 11.2, 2.5), (-8.4, 14.0, 1.1), n, (-4.6, 11.3, 2.4), (-8.0, 13.6, 1.1))
    w.finish(n)
    return w, n, single(cam)


def S3e():
    w = World()
    n = frames_of("S3e")
    kot = w.char("kotik_777", KOT)
    kot.place(1, KOT, yaw_to(KOT, (-10, 15, 0)))
    bro = w.char("brohacker", BRO_IN, yaw_to(BRO_IN, KOT))
    bro.hold("sword")
    kot.turn(F(0.3), F(1.1), yaw_to(KOT, BRO_IN))
    kot.surprised(F(1.2), "!")
    K.set(bro.head, "rotation_euler", F(2.4), (0, 0, 0))
    K.set(bro.head, "rotation_euler", F(2.7), (0.1, 0, 0.12))
    cam, t = w.cam("c", 18)
    cam_path(cam, t, 1, (-10.3, 15.3, 2.35), (-6.0, 12.3, 1.5), n, (-10.1, 15.1, 2.3), (-6.0, 12.3, 1.55))
    w.finish(n)
    return w, n, single(cam)


def S3f():
    w = World()
    n = frames_of("S3f")
    kot = w.char("kotik_777", KOT)
    kot.place(1, KOT, yaw_to(KOT, BRO_IN))
    K.set(kot.mouth, "scale", 1, (1, 1, 1))
    K.set(kot.rarm, "rotation_euler", 1, (-0.35, 0, -0.35))
    K.set(kot.larm, "rotation_euler", 1, (-0.35, 0, 0.35))
    bro, cam, tgt, hand, objs = bro_fp(w, BRO_IN, (KOT[0], KOT[1], 1.35))
    K.set(tgt, "location", F(1.8), (KOT[0], KOT[1], 1.35))
    fp_jump(cam, F(2.1))
    fp_swing(hand, F(2.5))
    kot.die(F(2.7), bro)
    w.fx.crit(Vector((KOT[0], KOT[1], 1.3)), F(2.7))
    K.set(tgt, "location", F(3.4), (KOT[0], KOT[1], 0.6))
    K.set(tgt, "location", n, (KOT[0] + 0.5, KOT[1], 0.7))
    w.finish(n)
    return w, n, single(cam)


def S3g():
    w = World()
    n = frames_of("S3g")
    bro = w.char("brohacker", (-7.0, 11.8, 0), 0.0)
    bro.hold("sword")
    w.fx.smoke(Vector((-7.0, 10.6, 1.2)), 3)
    bro.walk(F(0.4), F(1.8), (-7.0, 8.6, 0))
    K.set(bro.root, "location", F(2.4), (-7.0, 8.0, 0.4))
    K.set(bro.root, "location", F(5.4), (-6.0, 6.0, 8.0))
    bro.fly_pose(F(2.4), n)
    cam, t = w.cam("c", 22)
    cam_path(cam, t, 1, (-3.0, 3.4, 1.7), (-7.0, 10.0, 1.5), n, (-3.4, 3.8, 1.9), (-6.4, 7.0, 6.0))
    w.finish(n)
    return w, n, single(cam)


# ============================================================================ Act 4

def fp_above_spawn(sid, pos=(2.0, -6.0, 8.5), look0=(0, 0, 0), look1=(-0.5, 1.0, 0)):
    w = World()
    n = frames_of(sid)
    crowd = spawn_crowd(w, 6, seed=hash(sid) % 7)
    for i, c in enumerate(crowd):
        c.idle(1, n, i)
    crowd[1].talk(10, n - 10)
    bro, cam, tgt, hand, objs = bro_fp(w, pos, look0)
    K.set(tgt, "location", 1, look0)
    K.set(tgt, "location", n, look1)
    return w, n, cam, crowd


def S4a():
    w, n, cam, crowd = fp_above_spawn("S4a")
    w.finish(n)
    return w, n, single(cam)


def S4b():
    w = World()
    n = frames_of("S4b")
    D = (2.6, -3.6, 0)
    d = w.char("dimon_pro", D, 0.4)
    w.fx.swirl(d, F(0.2), F(2.6))
    d.surprised(F(0.5), "?")
    d.head_rot(F(1.0), F(1.4), 0.15, 0.2)
    d.calm(F(2.2))
    B = (3.9, -4.8, 0)
    bro = w.char("brohacker", B, yaw_to(B, D))
    bro.hold("sword")
    bro.appear(F(3.0))
    d.look(F(3.2), F(3.5), bro.head_pos(1), body_follow=0.6)
    bro.swing(F(3.7), sweep=True, crit=True, target=d)
    d.die(F(3.85), bro, drops=True)
    m = w.char("pixel_masha", (-2.6, -1.2, 0))
    m.look(F(3.9), F(4.4), D, body_follow=0.8)
    m.surprised(F(4.4), "!")
    cam, t = w.cam("c", 22)
    cam_path(cam, t, 1, (6.8, -8.8, 2.2), (3.0, -3.8, 1.2), n, (6.4, -8.2, 2.1), (3.1, -4.0, 1.1))
    w.finish(n)
    return w, n, single(cam)


def S4c():
    w, n, cam, crowd = fp_above_spawn("S4c", pos=(-2.0, -5.0, 8.0), look0=(0.5, 0.5, 0), look1=(1.0, 1.5, 0))
    w.finish(n)
    return w, n, single(cam)


MONTAGE = [((14, -12, 0), (6.0, -16.0, 2.2)), ((-14, -5, 0), (-8.0, -10.5, 2.4)), ((0, 29, 0), (4.5, 23.0, 2.0)),
           ((-16, 7.5, 0), (-10.0, 2.5, 2.2)), ((21, -3, 0), (16.0, -9.0, 2.4))]


def S4d():
    w = World()
    n = frames_of("S4d")
    seg = n // 5
    bro = w.char("brohacker", (0, 0, 0))
    bro.hold("sword")
    bro.vanish(1)
    cams = []
    for i, (pos, cpos) in enumerate(MONTAGE):
        f0 = 1 + i * seg
        v = w.npc(pos, yaw_to(pos, cpos))
        v.idle(f0, f0 + seg)
        bp = Vector(pos) + Vector((1.1, 0.9, 0)).normalized() * 1.3
        bro.place(f0 + 4, tuple(bp), yaw_to(bp, pos))
        bro.place(f0 + seg - 1, tuple(bp), yaw_to(bp, pos))
        K.set(bro.root, "scale", f0 + 5, (0, 0, 0))
        K.set(bro.root, "scale", f0 + 6, (1, 1, 1))
        K.set(bro.root, "scale", f0 + seg - 2, (1, 1, 1))
        K.set(bro.root, "scale", f0 + seg - 1, (0, 0, 0))
        w.fx.teleport(bp + Vector((0, 0, 1.0)), f0 + 4)
        v.look(f0 + 8, f0 + 12, (bp.x, bp.y, 1.6), body_follow=0.5)
        bro.swing(f0 + 16, sweep=True, crit=True, target=v)
        v.die(f0 + 18, bro)
        cam, t = w.cam(f"c{i}", 22)
        mid = (Vector(pos) + bp) / 2
        cam_path(cam, t, f0, cpos, (mid.x, mid.y, 1.1), f0 + seg, tuple(Vector(cpos) * 0.97 + mid * 0.03),
                 (mid.x, mid.y, 1.0))
        cams.append(cam)
    w.finish(n)
    return w, n, lambda f: cams[min(4, (f - 1) // seg)]


def S4e():
    w = World()
    n = frames_of("S4e")
    M = (-1.1, -3.7, 0)
    camp = (-0.4, -6.4, 1.75)
    m = w.char("pixel_masha", M, yaw_to(M, camp))
    m.surprised(F(0.2), None)
    K.set(m.rarm, "rotation_euler", F(0.4), (-2.9, 0, -0.3))
    K.set(m.larm, "rotation_euler", F(0.4), (-2.9, 0, 0.3))
    for i, f in enumerate(range(F(0.5), n, 5)):
        K.set(m.rarm, "rotation_euler", f, (-2.9, 0, -0.1 if i % 2 else -0.5))
        K.set(m.larm, "rotation_euler", f, (-2.9, 0, 0.1 if i % 2 else 0.5))
    m.jump(F(0.6), 0.35)
    m.jump(F(1.6), 0.35)
    npcs_walking(w, n, 2, seed=1)
    cam, t = w.cam("c", 30)
    cam_path(cam, t, 1, camp, (-1.1, -3.7, 1.55), n, (-0.55, -6.0, 1.72), (-1.1, -3.7, 1.6))
    shake(cam, 1, n, 0.02, 3)
    w.finish(n)
    return w, n, single(cam)


def S4f():
    w = World()
    n = frames_of("S4f")
    w.fx.drops(Vector((2.6, -3.6, 0.5)), -30)
    for p in ((2.6, -3.6, 0.6), (4.0, 4.0, 0.6), (-5, -5, 0.6)):
        w.fx.smoke(Vector(p), 2)
    bro = w.char("brohacker", (0.0, 0.0, 6.5), math.radians(200))
    bro.hold("sword")
    bro.hover(1, n, (0.0, 0.0, 6.5))
    bro.fly_pose(1, n)
    m = w.char("pixel_masha", (-5.5, -1.0, 0))
    m.run(5, F(4.5), (-9.5, 8.0, 0))
    cam, t = w.cam("c", 20)
    cam_path(cam, t, 1, (-6.5, -12.5, 4.0), (0, 0, 4.0), n, (-5.4, -10.6, 4.3), (0, 0, 4.4))
    w.finish(n)
    return w, n, single(cam)


# ============================================================================ Act 5 (ocean)

SKY = Vector((OCEAN_X, 0, 40))


def S5a():
    w = World(land=False, ocean=True)
    n = frames_of("S5a")
    bro = w.char("brohacker", tuple(SKY + Vector((-40, 0, 0))), math.pi / 2)
    bro.hold("sword")
    cam, t = w.cam("c", 24)
    for f in list(range(1, n + 1, 6)) + [n]:
        k = min(1.0, (f - 1) / (n - 30))
        k = 1 - (1 - k) ** 2
        p = SKY + Vector((-40 + 40 * k, 0, 0.3 * math.sin(f / 7)))
        lean = 0.55 * (1 - max(0.0, (f - (n - 30)) / 30))
        K.set(bro.root, "location", f, tuple(p))
        K.set(bro.root, "rotation_euler", f, (lean, 0, math.pi / 2))
        K.set(cam, "location", f, tuple(p + Vector((-5.5, -3.0, 1.6))))
        K.set(t, "location", f, tuple(p + Vector((1.5, 0, 0.8))))
    bro.fly_pose(1, n)
    w.finish(n)
    return w, n, single(cam)


def S5b():
    w = World(land=False, ocean=True)
    n = frames_of("S5b")
    bro, cam, tgt, hand, objs = bro_fp(w, tuple(SKY), (OCEAN_X + 2, 9, 0))
    K.set(tgt, "location", n, (OCEAN_X + 1, 7, 0))
    w.finish(n)
    return w, n, single(cam)


NINE = [(2.6, 1.0, -0.5), (-2.4, 1.6, 0.6), (1.2, -2.8, 0.2), (-1.6, -2.2, -0.8), (3.4, -1.0, 0.9),
        (-3.3, -0.4, 0.1), (0.4, 3.0, -0.3), (2.0, 2.6, 1.0), (-0.9, 3.4, 0.5)]


def nine(w):
    out = [w.char("lavaKing")]
    for i in range(8):
        out.append(w.npc())
    return out


def S5c():
    w = World(land=False, ocean=True)
    n = frames_of("S5c")
    bro = w.char("brohacker", tuple(SKY), 0.4)
    bro.hold("sword")
    bro.hover(1, n, tuple(SKY))
    bro.fly_pose(1, n)
    people = nine(w)
    for i, (c, off) in enumerate(zip(people, NINE)):
        p = SKY + Vector(off)
        c.place(1, tuple(p), yaw_to(p, SKY) + random.Random(i).uniform(-0.8, 0.8))
        f = F(0.6 + i * 0.32)
        c.appear(f)
        c.surprised(f + 6, "?")
        c.look(f + 8, f + 14, (SKY.x, SKY.y, SKY.z + 1.6))
        fall0 = F(5.3 + 0.05 * i)
        c.fall(fall0, n + 30, tuple(p), tuple(p + Vector((0, 0, -22))))
    K.set(bro.rarm, "rotation_euler", F(4.8), (0, 0, -0.1))
    K.set(bro.rarm, "rotation_euler", F(5.2), (0, 2.45, 0))
    for i, f in enumerate(range(F(5.4), n, 5)):
        K.set(bro.rarm, "rotation_euler", f, (0, 2.2 if i % 2 == 0 else 2.65, 0))
    cam, t = w.cam("c", 20)
    cam_path(cam, t, 1, tuple(SKY + Vector((7, -9, 2.5))), tuple(SKY + Vector((0, 0, 0.6))), n,
             tuple(SKY + Vector((8, -10.5, 4.5))), tuple(SKY + Vector((0, 0, -1.5))))
    w.finish(n)
    return w, n, single(cam)


WATER = [(OCEAN_X + x * 1.3, y * 1.3, 0) for x, y, _ in NINE]


def S5d():
    w = World(land=False, ocean=True)
    n = frames_of("S5d")
    bro = w.char("brohacker", tuple(SKY), 0.4)
    bro.hover(1, n, tuple(SKY))
    people = nine(w)
    r = random.Random(4)
    for i, (c, wp) in enumerate(zip(people, WATER)):
        t0 = 0.2 + i * 0.32 + r.uniform(0, 0.2)
        f0, f1 = F(t0), F(t0 + 1.0)
        c.fall(f0, f1, (wp[0], wp[1], 26), (wp[0], wp[1], -1.45))
        w.fx.splash(Vector((wp[0], wp[1], 0.1)), f1)
        c.swim(f1 + 1, n, wp, i)
    cam, t = w.cam("c", 18)
    cam_path(cam, t, 1, (OCEAN_X + 7, -9, 1.2), (OCEAN_X, 0, 9), n, (OCEAN_X + 6.5, -8.5, 1.0), (OCEAN_X, 0, 4))
    w.finish(n)
    return w, n, single(cam)


def S5e():
    w = World(land=False, ocean=True)
    n = frames_of("S5e")
    people = nine(w)
    for i, (c, wp) in enumerate(zip(people, WATER)):
        c.swim(1, n, wp, i)
        c.place(1, (wp[0], wp[1], -1.45), random.Random(i).uniform(-3, 3))
    lava = people[0]
    lp = WATER[0]
    lava.place(1, (lp[0], lp[1], -1.45), yaw_to(lp, (OCEAN_X + 5, -5, 0)))
    lava.surprised(F(0.4), "!")
    bro = w.char("brohacker", (OCEAN_X + 1.5, 1.0, 9.0), 0.6)
    bro.hold("sword")
    bro.hover(1, n, (OCEAN_X + 1.5, 1.0, 9.0))
    bro.fly_pose(1, n)
    K.set(bro.rarm, "rotation_euler", F(3.3), (0, 0, -0.1))
    K.set(bro.rarm, "rotation_euler", F(3.6), (0, 2.45, 0))
    for i, f in enumerate(range(F(3.8), n, 5)):
        K.set(bro.rarm, "rotation_euler", f, (0, 2.2 if i % 2 == 0 else 2.65, 0))
    cam, t = w.cam("c", 22)
    K.set(cam, "location", 1, (lp[0] + 3.2, lp[1] - 4.2, 0.7))
    K.set(t, "location", 1, (lp[0], lp[1], 0.25))
    K.set(cam, "location", F(2.8), (lp[0] + 3.0, lp[1] - 4.0, 0.7))
    K.set(t, "location", F(2.8), (lp[0], lp[1], 0.3))
    K.set(cam, "location", F(3.6), (lp[0] + 3.0, lp[1] - 4.4, 0.9))
    K.set(t, "location", F(3.6), (OCEAN_X + 1.5, 1.0, 9.6))
    K.set(t, "location", n, (OCEAN_X + 1.5, 1.0, 9.8))
    w.finish(n)
    return w, n, single(cam)


def S5f():
    w = World(land=False, ocean=True)
    n = frames_of("S5f")
    people = nine(w)
    for i, (c, wp) in enumerate(zip(people, WATER)):
        c.swim(1, n, wp, i)
        c.place(1, (wp[0], wp[1], -1.45), random.Random(i).uniform(-3, 3))
        c.walk(F(4), n, (wp[0] - 6, wp[1] - 3, -1.45), swing=0.0)
    bro = w.char("brohacker", tuple(SKY + Vector((0, 0, -20))), 0.0)
    bro.hover(1, n, tuple(SKY + Vector((0, 0, -20))))
    cam, t = w.cam("c", 22)
    cam_path(cam, t, 1, (OCEAN_X + 3, -5, 2.0), (OCEAN_X, 0, 0), n, (OCEAN_X + 12, -26, 28), (OCEAN_X, 0, 0))
    w.finish(n)
    return w, n, single(cam)


# ============================================================================ Act 6 (basement)

BM = {"pixel_masha": (14.0, 4.2, -5), "dimon_pro": (15.3, 2.6, -5), "snowbunny": (16.6, 2.9, -5),
      "lavaKing": (15.4, 5.3, -5)}
CENTER = (15.3, 3.9, -5)
BCAM = (18.5, 6.4, -2.9)


def basement(w):
    out = {}
    for name, p in BM.items():
        c = w.char(name, p)
        c.place(1, p, yaw_to(p, CENTER) if name != "pixel_masha" else yaw_to(p, (16.5, 4.6, -5)))
        out[name] = c
    return out


def S6a():
    w = World()
    n = frames_of("S6a")
    c = basement(w)
    c["pixel_masha"].talk(F(1.0), F(6.4))
    for name in ("dimon_pro", "snowbunny", "lavaKing"):
        c[name].look(5, 14, c["pixel_masha"].head_pos(1))
        c[name].idle(1, n, hash(name) % 5)
    K.set(c["dimon_pro"].head, "rotation_euler", F(7.0), (0.15, 0, 0.3))
    K.set(c["dimon_pro"].head, "rotation_euler", F(7.4), (-0.05, 0, 0.3))
    cam, t = w.cam("c", 16)
    cam_path(cam, t, 1, BCAM, (14.9, 3.6, -4.1), n, (18.3, 6.2, -3.0), (14.9, 3.7, -4.1))
    w.finish(n)
    return w, n, single(cam)


def S6b():
    w = World()
    n = frames_of("S6b")
    c = basement(w)
    s = c["snowbunny"]
    s.look(1, 4, c["pixel_masha"].head_pos(1))
    w.fx.swirl(s, F(0.6), F(3.4))
    K.tween(s.rarm, "rotation_euler", F(1.8), F(2.4), (-2.55, 0, 0.6))
    K.set(s.rarm, "rotation_euler", F(2.6), (-2.45, 0, 0.5))
    K.set(s.rarm, "rotation_euler", F(2.8), (-2.6, 0, 0.6))
    K.tween(s.rarm, "rotation_euler", F(3.4), F(3.8), (0, 0, -0.04))
    s.surprised(F(3.0), "!")
    sp = Vector(BM["snowbunny"])
    dv = (Vector(CENTER) - sp)
    dv.z = 0
    dv.normalize()
    c0 = sp + dv * 1.5
    cam, t = w.cam("c", 30)
    cam_path(cam, t, 1, (c0.x, c0.y, -3.35), (sp.x, sp.y, -3.45), n, (c0.x - dv.x * 0.2, c0.y - dv.y * 0.2, -3.38),
             (sp.x, sp.y, -3.45))
    w.finish(n)
    return w, n, single(cam)


def S6c():
    w = World()
    n = frames_of("S6c")
    c = basement(w)
    bro = w.char("brohacker", (15.4, 3.8, -5), yaw_to((15.4, 3.8), BCAM))
    bro.hold("sword")
    bro.appear(F(0.8))
    for i, ch in enumerate(c.values()):
        ch.look(F(1.0), F(1.3), bro.head_pos(1), body_follow=0.6)
        ch.surprised(F(1.1 + 0.1 * i), "!")
    K.set(bro.head, "rotation_euler", F(1.8), (0, 0, 0.0))
    K.set(bro.head, "rotation_euler", F(2.2), (0.05, 0, 0.5))
    K.set(bro.head, "rotation_euler", F(2.8), (0.05, 0, -0.5))
    cam, t = w.cam("c", 16)
    cam_path(cam, t, 1, BCAM, (15.2, 3.8, -4.0), n, (18.2, 6.1, -3.0), (15.2, 3.8, -4.0))
    w.finish(n)
    return w, n, single(cam)


def S6d():
    w = World()
    n = frames_of("S6d")
    c = basement(w)
    bro = w.char("brohacker", (15.4, 3.8, -5), yaw_to((15.4, 3.8), BCAM))
    bro.hold("sword")
    exits = [(13.0, 6.6, -5), (13.0, 1.8, -5), (18.6, 1.8, -5), (16.0, 6.8, -5)]
    for i, (ch, ex) in enumerate(zip(c.values(), exits)):
        f0 = F(0.2 + 0.25 * i)
        ch.surprised(f0, "!")
        ch.run(f0 + 2, f0 + 34, ex)
        ch.jump(f0 + 10, 0.4)
        ch.vanish(f0 + 34)
    for i, f in enumerate(range(F(0.5), F(3.0), 12)):
        K.set(bro.root, "rotation_euler", f, (0, 0, 0.9 * math.sin(i * 1.4)))
    cam, t = w.cam("c", 16)
    cam_path(cam, t, 1, BCAM, (15.2, 3.8, -4.1), n, (17.9, 5.9, -3.1), (15.2, 3.6, -4.0))
    w.finish(n)
    return w, n, single(cam)


# ============================================================================ Act 7 (arena)

A = Vector((0, 41, 0))
LAVA0 = Vector((0, 37.5, 0))
BRO0 = Vector((0, 44.5, 0))
TRIB_W = [(-10, 37), (-10, 40), (-11, 42), (-10, 45), (-12, 39), (-11, 36), (-12, 44)]
TRIB_E = [(10, 38), (11, 41), (10, 43), (12, 46), (11, 36), (10, 47), (12, 40)]


def tribunes(w, named=True, n_np=10):
    out = []
    names = ["pixel_masha", "dimon_pro", "snowbunny", "kotik_777"] if named else []
    spots = TRIB_W + TRIB_E
    for i, (x, y) in enumerate(spots[: len(names) + n_np]):
        z = abs(x) - 9
        c = w.char(names[i]) if i < len(names) else w.npc()
        c.sit(1, (x, y, z), yaw_to((x, y), (0, 41)))
        c.idle(1, 400, i)
        out.append(c)
    return out


def lava_armed(w, pos=LAVA0, yaw=0.0):
    lava = w.char("lavaKing", tuple(pos), yaw)
    lava.hold("axe")
    lava.hold("shield", "l")
    return lava


def S7a():
    w = World()
    n = frames_of("S7a")
    crowd = tribunes(w)
    lava = lava_armed(w, LAVA0, math.pi)
    lava.idle(1, n)
    lava.block(F(3.0), F(4.2))
    for i, c in enumerate(crowd[:6]):
        c.look(F(1 + 0.3 * i), F(1.6 + 0.3 * i), (0, 37.5, 1.6))
    cam, t = w.cam("c", 22)
    cam_path(cam, t, 1, (7.5, 24.5, 7.5), (0, 41, 1.0), n, (4.5, 27.0, 5.5), (0, 40, 1.4))
    w.finish(n)
    return w, n, single(cam)


def S7b():
    w = World()
    n = frames_of("S7b")
    tribunes(w)
    lava = lava_armed(w, LAVA0, math.pi)
    lava.talk(F(0.2), F(2.2))
    bro = w.char("brohacker", tuple(BRO0 + Vector((0, 0, 9))), 0.0)
    bro.hold("sword")
    K.set(bro.root, "location", 1, tuple(BRO0 + Vector((0, 0, 9))))
    K.set(bro.root, "location", F(2.0), tuple(BRO0 + Vector((0, 0, 7))))
    K.set(bro.root, "location", F(3.2), tuple(BRO0))
    bro.fly_pose(1, F(3.0))
    w.fx.smoke(BRO0 + Vector((0, 0, 0.2)), F(3.2))
    lava.look(F(2.4), F(3.0), (0, 44.5, 3.0))
    cam, t = w.cam("c", 22)
    cam_path(cam, t, 1, (3.4, 35.6, 1.7), (0, 39.0, 1.5), n, (3.6, 35.2, 1.8), (0, 41.0, 1.8))
    w.finish(n)
    return w, n, single(cam)


def S7c():
    w = World()
    n = frames_of("S7c")
    tribunes(w)
    lava = lava_armed(w, LAVA0, math.pi)
    lava.block(F(0.3), n + 10)
    bro = w.char("brohacker", tuple(BRO0), 0.0)
    bro.hold("sword")
    bro.idle(1, n)
    cam, t = w.cam("c", 20)
    cam_path(cam, t, 1, (-6.5, 41, 1.0), (0, 41, 1.4), n, (-6.0, 41.2, 1.1), (0, 41, 1.4))
    w.finish(n)
    return w, n, single(cam)


def S7d():
    w = World()
    n = frames_of("S7d")
    tribunes(w)
    lava = lava_armed(w, LAVA0, math.pi)
    bro, cam, tgt, hand, objs = bro_fp(w, tuple(BRO0), (0, 37.5, 1.5), items=("sword", "axe"))
    # lava strafes around the cheater, gets hit and knocked back
    r = random.Random(9)
    path_t = [0.0, 1.4, 3.0, 4.6, 6.0, 7.4, 9.0, 10.6, 12.0, 14.0]
    ang = [math.pi, math.pi + 0.3, math.pi - 0.4, math.pi + 0.5, math.pi - 0.2, math.pi + 0.6, math.pi - 0.5,
           math.pi + 0.2, math.pi - 0.3, math.pi + 0.1]
    dist = [7.0, 3.2, 3.0, 3.4, 3.1, 3.3, 3.0, 3.6, 4.6, 6.5]
    for t_, a, d in zip(path_t, ang, dist):
        p = BRO0 + Vector((math.sin(a) * d, -math.cos(a) * d * -1, 0))
        p = Vector((BRO0.x + math.sin(a) * d, BRO0.y + math.cos(a) * d, 0))
        lava.place(F(t_), tuple(p), yaw_to(p, BRO0))
    for f in range(1, n, 6):
        a = 0.6 * math.sin(f / 3.0)
        K.set(lava.rleg, "rotation_euler", f, (a, 0, 0))
        K.set(lava.lleg, "rotation_euler", f, (-a, 0, 0))
    lava.block(F(0.6), F(1.9))
    lava.block(F(7.0), F(7.6))
    hits = HITS["S7d"]
    for kind, t_ in hits:
        f = F(t_)
        if kind == "axe":
            fp_switch(objs, f - 6, "axe")
            fp_swing(hand, f)
            K.set(lava.larm, "rotation_euler", f + 2, (0, 0, 0.04))
            fp_switch(objs, f + 8, "sword")
        elif kind == "crit":
            fp_jump(cam, f - 7)
            fp_swing(hand, f)
            lava.hurt(f + 1, None, kb=0)
            w.fx.crit(lava.p(f) + Vector((0, 0, 1.3)), f + 1)
            # knockback away from the cheater
            p = lava.p(f + 1)
            d = (p - BRO0)
            d.z = 0
            d.normalize()
            K.set(lava.root, "location", f + 1, tuple(p))
            K.set(lava.root, "location", f + 5, tuple(p + d * 0.7 + Vector((0, 0, 0.35))))
            K.set(lava.root, "location", f + 10, tuple(p + d * 1.2))
    # aimbot: the camera target snaps to lava's head
    for f in range(1, n + 1, 2):
        p = lava.p(f)
        K.set(tgt, "location", f, (p.x, p.y, p.z + 1.45))
    w.finish(n)
    return w, n, single(cam)


def S7e():
    w = World()
    n = frames_of("S7e")
    tribunes(w, n_np=6)
    lava = lava_armed(w, Vector((0, 42.2, 0)), math.pi)
    bro = w.char("brohacker", tuple(BRO0), math.pi * 0 + math.pi)
    bro.place(1, tuple(BRO0), yaw_to(BRO0, (0, 42.2)))
    sw = bro.hold("sword")
    ax = bro.hold("axe")
    ax.scale = (0, 0, 0)
    lava.block(F(0.3), F(2.4))
    # slow motion: everything takes 4x longer
    for i, t0 in enumerate([1.2, 4.0]):
        f = F(t0)
        K.set(bro.root, "location", f, tuple(BRO0))
        K.set(bro.root, "location", f + 12, tuple(BRO0 + Vector((0, 0, 0.45))))
        K.set(bro.root, "location", f + 24, tuple(BRO0 + Vector((0, 0, 0.1))))
        K.set(bro.root, "location", f + 30, tuple(BRO0))
        for j in range(6):
            K.set(bro.head, "rotation_euler", f + j * 4, (0.25 * ((j * 7) % 3 - 1), 0, 0.5 * ((j * 5) % 3 - 1)))
        if i == 0:
            K.set(ax, "scale", f - 6, (0, 0, 0))
            K.set(ax, "scale", f - 5, (1, 1, 1))
            K.set(sw, "scale", f - 6, (1, 1, 1))
            K.set(sw, "scale", f - 5, (0, 0, 0))
            K.set(ax, "scale", f + 30, (1, 1, 1))
            K.set(ax, "scale", f + 31, (0, 0, 0))
            K.set(sw, "scale", f + 30, (0, 0, 0))
            K.set(sw, "scale", f + 31, (1, 1, 1))
        K.hold(bro.rarm, "rotation_euler", f + 12)
        K.set(bro.rarm, "rotation_euler", f + 18, (-2.5, 0, -0.3))
        K.set(bro.rarm, "rotation_euler", f + 28, (-0.7, 0, 0.35))
        K.set(bro.rarm, "rotation_euler", f + 40, (-0.35, 0, 0))
        w.fx.crit(Vector((0, 42.2, 1.3)), f + 22)
        lava.hurt(f + 22, None, kb=0)
    cam, t = w.cam("c", 26)
    cam_path(cam, t, 1, (4.6, 42.4, 1.4), (0, 43.3, 1.2), n, (4.0, 45.4, 1.6), (0, 43.3, 1.25))
    w.finish(n)
    return w, n, single(cam)


def S7f():
    w = World()
    n = frames_of("S7f")
    tribunes(w, n_np=6)
    BP = Vector((2.4, 43.6, 0))
    LEDGE = Vector((5.5, 45.5, 2.0))
    LAND = Vector((3.3, 44.5, 0))
    lava = lava_armed(w, LEDGE, yaw_to(LEDGE, BP))
    K.set(lava.root, "location", F(0.5), tuple(LEDGE))
    K.set(lava.root, "location", F(0.9), tuple((LEDGE + LAND) / 2 + Vector((0, 0, 1.4))))
    K.set(lava.root, "location", F(1.3), tuple(LAND))
    lava.swing(F(1.15))
    bro = w.char("brohacker", tuple(BP), yaw_to(BP, LEDGE))
    bro.hold("sword")
    w.fx.crit(BP + Vector((0, 0, 1.3)), F(1.35))
    bro.hurt(F(1.35), lava, kb=0.8)
    cam_tp, t1 = w.cam("tp", 22)
    cam_path(cam_tp, t1, 1, (-1.5, 39.0, 1.8), (3.6, 44.4, 1.6), F(3.0), (-1.2, 39.4, 1.9), (3.2, 44.4, 1.4))
    # first person after the totem
    cam_fp, t2 = w.cam("fp", 20)
    eye = BP + Vector((0, -0.8, 1.62))
    K.set(cam_fp, "location", F(3.0), tuple(eye))
    K.set(t2, "location", F(3.0), tuple(LAND + Vector((0, 0, 1.4))))
    K.set(t2, "location", n, tuple(LAND + Vector((0, 0, 1.45))))
    hand, objs = w.fp_rig(cam_fp, ("sword",))
    fwd = (LAND - eye)
    fwd.z = 0
    fwd.normalize()
    w.fx.totem(eye + fwd * 1.2 + Vector((0, 0, -0.2)), F(3.4))
    w.fx.totem(eye + fwd * 2.0 + Vector((0, 0, 0.2)), F(3.6))
    bro.vanish(F(3.0))
    w.finish(n)
    return w, n, lambda f: cam_tp if f < F(3.0) else cam_fp


def S7g():
    w = World()
    n = frames_of("S7g")
    tribunes(w, n_np=6)
    LAND = Vector((3.3, 44.5, 0))
    lava = lava_armed(w, LAND, yaw_to(LAND, (2.4, 43.6)))
    bro, cam, tgt, hand, objs = bro_fp(w, (2.4, 42.8, 0), tuple(LAND + Vector((0, 0, 1.45))))
    for t_ in (1.0, 1.7):
        f = F(t_)
        fp_jump(cam, f - 7)
        fp_swing(hand, f)
        w.fx.crit(LAND + Vector((0, 0, 1.3)), f + 1)
    lava.hurt(F(1.0) + 1, None, kb=0)
    lava.die(F(1.75), bro)
    K.set(tgt, "location", F(2.6), tuple(LAND + Vector((0, 0, 0.6))))
    K.set(tgt, "location", F(4.4), tuple(LAND + Vector((0, 0, 0.6))))
    K.set(tgt, "location", n, (-10, 41, 2.6))
    w.finish(n)
    return w, n, single(cam)


def S7h():
    w = World()
    n = frames_of("S7h")
    crowd = tribunes(w, n_np=10)
    bro, cam, tgt, hand, objs = bro_fp(w, (1.5, 42.0, 0), (-10.5, 41, 2.2))
    K.set(tgt, "location", n, (-10.5, 40.0, 2.4))
    for i, c in enumerate(crowd):
        c.look(F(0.5), F(1.2), (1.5, 42.0, 1.6))
    w.finish(n)
    return w, n, single(cam)


def S7i():
    w = World()
    n = frames_of("S7i")
    tribunes(w, named=False, n_np=0)
    snow = w.char("snowbunny")
    snow.sit(1, (-11, 41, 2), yaw_to((-11, 41), (0, 41)))
    BP = Vector((1.5, 42.0, 0))
    bro = w.char("brohacker", tuple(BP), math.radians(90))
    bro.hold("sword")
    people = [w.char("dimon_pro"), w.char("kotik_777")] + [w.npc() for _ in range(12)]
    r = random.Random(3)
    for i, c in enumerate(people):
        a = 2 * math.pi * i / len(people) + r.uniform(-0.15, 0.15)
        d = r.uniform(1.6, 3.6)
        p = BP + Vector((math.cos(a) * d, math.sin(a) * d, 0))
        c.place(1, tuple(p), yaw_to(p, BP))
        f = F(0.3 + i * 0.12)
        c.appear(f)
        c.surprised(f + 4, "?")
    for k, t_ in enumerate((2.6, 3.3, 4.0)):
        f = F(t_)
        K.set(bro.root, "rotation_euler", f - 2, (0, 0, math.radians(90 + 120 * k)))
        bro.swing(f, sweep=True)
    for i, c in enumerate(people):
        c.die(F(2.7 + (i % 3) * 0.7 + 0.04 * i), bro, drops=(i % 3 == 0))
    cam, t = w.cam("c", 20)
    cam_path(cam, t, 1, (8.5, 32.0, 6.5), tuple(BP + Vector((0, 0, 0.8))), n, (7.0, 33.5, 5.5),
             tuple(BP + Vector((0, 0, 0.9))))
    w.finish(n)
    return w, n, single(cam)


def S7j():
    w = World()
    n = frames_of("S7j")
    snow = w.char("snowbunny")
    sp = (-11, 41, 2)
    snow.sit(1, sp, yaw_to(sp, (0, 41)))
    K.set(snow.head, "rotation_euler", 1, (0.25, 0, 0))
    K.set(snow.head, "rotation_euler", F(0.9), (0.05, 0, 0.1))
    K.set(snow.head, "rotation_euler", F(2.5), (0.3, 0, 0))
    bro = w.char("brohacker", (1.5, 42.0, 0), math.radians(-90))
    bro.hold("sword")
    w.fx.drops(Vector((2.5, 43.0, 0.5)), -40)
    cam, t = w.cam("c", 30)
    cam_path(cam, t, 1, (-8.6, 39.6, 2.9), (-11, 41, 2.75), n, (-8.9, 39.9, 2.85), (-11, 41, 2.72))
    w.finish(n)
    return w, n, single(cam)


# ============================================================================ Act 8 + finale

def S8a():
    w = World()
    n = frames_of("S8a")
    crowd = spawn_crowd(w, 4, seed=8)
    kot = w.char("kotik_777", (2.5, -6.0, 0), 0.6)
    for i, c in enumerate(crowd + [kot]):
        K.set(c.head, "rotation_euler", 1, (0.35, 0, 0))
        c.idle(1, n, i)
    crowd[0].talk(F(1.0), F(4.0))
    cam, t = w.cam("c", 22)
    cam_path(cam, t, 1, (-5.0, -11.5, 2.4), (0, -3, 1.4), n, (-4.4, -10.6, 2.3), (0, -2.6, 1.45))
    w.finish(n)
    return w, n, single(cam)


def S8b():
    w, n, cam, crowd = fp_above_spawn("S8b", pos=(1.0, -7.0, 8.0), look0=(0, -1.0, 0), look1=(0, 0.5, 0))
    w.finish(n)
    return w, n, single(cam)


def S8c():
    w = World()
    n = frames_of("S8c")
    crowd = spawn_crowd(w, 7, seed=6)
    for i, c in enumerate(crowd):
        w.fx.swirl(c, F(0.2 + 0.05 * i), n + 20)
        w.fx.symbol(c, F(0.4 + 0.05 * i), "?" if i % 2 else "!")
        dest = Vector(c.p(1)) + Vector((random.Random(i).uniform(-3, 3), random.Random(i + 9).uniform(-3, 3), 0))
        c.walk(F(1.0), F(9.0), tuple(dest), swing=0.6)
    bro = w.char("brohacker", (0.6, -2.0, 7.5), math.pi)
    bro.hover(1, n, (0.6, -2.0, 7.5))
    bro.fly_pose(1, n)
    cam, t = w.cam("c", 22)
    cam_path(cam, t, 1, (1.6, -14.5, 3.4), (-0.4, 1.0, 3.6), n, (1.0, -12.5, 3.4), (-0.4, 1.0, 4.2))
    w.finish(n)
    return w, n, single(cam)


def S9a():
    w = World()
    n = frames_of("S9a")
    r = random.Random(2)
    m = w.mats
    for i in range(40):
        ob = cube_ = lib.cube_mesh(f"spark{i}", 0.07, m["purple"] if i % 2 else m["pink"])
        x, y = r.uniform(-5, 5), r.uniform(-5, 5)
        z0 = r.uniform(2.0, 6.0)
        f0 = r.randint(1, n // 2)
        K.set(ob, "location", 1, (x, y, z0 + 2.0))
        K.set(ob, "location", n, (x + r.uniform(-1, 1), y + r.uniform(-1, 1), max(0.1, z0 - 4.0)))
        K.set(ob, "scale", 1, (1, 1, 1))
        K.set(ob, "scale", n, (0.3, 0.3, 0.3))
    bro = w.char("brohacker", (0.0, 3.0, 9.0), math.pi)
    bro.hold("sword")
    bro.hover(1, n, (0.0, 3.0, 9.0))
    bro.fly_pose(1, n)
    cam, t = w.cam("c", 22)
    cam_path(cam, t, 1, (6.0, -14.0, 2.5), (0, 1.0, 3.5), n, (4.0, -11.0, 2.6), (0, 2.0, 5.5))
    w.finish(n)
    return w, n, single(cam)


SHOT_FUNCS = {k: v for k, v in globals().items() if k[0] == "S" and k[1].isdigit() and callable(v)}

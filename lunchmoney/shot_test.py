"""20 s style test: scene 1 opening by the gym (Bob, John, Maxim + crew, kids in the background).

    python shot_test.py --out frames --audio audio/audio.json [--frames 1-480] [--res 1280x720] [--samples 12]
"""
import argparse
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import act as A  # noqa: E402
import human as H  # noqa: E402
import school as S  # noqa: E402
import wardrobe as W  # noqa: E402

DUR = 20.0
LINES = {"bob1": 0.3, "john1": 2.62, "bob2": 3.3, "john2": 6.95, "bob3": 8.55, "maxim1": 13.55, "john3": 14.7}
SPEAKER = {"bob1": "bob", "john1": "john", "bob2": "bob", "john2": "john", "bob3": "bob", "maxim1": "maxim",
           "john3": "john"}
SFX = {"locker_slam": 10.45, "footsteps": 4.0}

P = {
    "john": ((-1.62, 3.55, 0), None),
    "bob": ((-0.55, 3.95, 0), None),
    "maxim": ((0.38, 2.5, 0), None),
    "karim": ((-1.35, 6.9, 0), 95),
    "artem": ((-0.72, 7.35, 0), 230),
}


def head(a, h=1.62):
    return (a.pos.x, a.pos.y, a.pos.z + h)


def build(audio):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = 24
    n = int(DUR * 24)
    sc.frame_start, sc.frame_end = 1, n
    cor = S.Corridor()
    actors = {}
    for name in ("bob", "john", "karim", "artem", "maxim"):
        h = W.build(name)
        pos, yaw = P[name]
        actors[name] = A.Actor(h, pos, yaw or 0, seed=hash(name) % 100)
    bob, john, maxim, karim, artem = (actors[k] for k in ("bob", "john", "maxim", "karim", "artem"))
    # facing
    bob.yaw = A.yaw_to(bob.pos, john.pos) + 12
    john.yaw = A.yaw_to(john.pos, bob.pos) - 8
    maxim.yaw = A.yaw_to(maxim.pos, bob.pos) - 10
    for a in actors.values():
        a.h.place(1, a.pos, a.yaw)
        a.stand(1)
        a.idle(1, n)
        a.blinks(1, n)
    # John leans on the wall, hands in pockets
    john.h.arm.rotation_euler = (math.radians(-5), 0, math.radians(john.yaw))
    john.h.arm.keyframe_insert("rotation_euler", frame=1)
    john.pockets(1)
    karim.pockets(1, "l")
    # Maxim's friends
    friends = []
    for i, (p, seed) in enumerate((((0.98, 2.1, 0), 71), ((0.72, 1.5, 0), 72))):
        e = W.extra(f"friend{i}", seed, child=0.3)
        hh = H.Human(f"friend{i}", e["spec"], e["outfit"])
        a = A.Actor(hh, p, A.yaw_to(p, bob.pos), seed=seed)
        a.stand(1)
        a.idle(1, n)
        a.blinks(1, n)
        friends.append(a)
    # kids walking in the background
    walkers = []
    for i, (p0, p1, t0, t1, seed) in enumerate((
            ((0.9, 17.0, 0), (0.5, -6.0, 0), 0.0, 17.0, 81),
            ((-0.3, -7.0, 0), (0.2, 14.0, 0), 3.5, 19.5, 82),
            ((1.3, 13.0, 0), (1.45, 8.2, 0), 1.0, 6.5, 83),
            ((0.2, 20.0, 0), (-0.6, 9.5, 0), 6.0, 15.5, 84))):
        e = W.extra(f"kid{i}", seed, child=0.6)
        hh = H.Human(f"kid{i}", e["spec"], e["outfit"])
        a = A.Actor(hh, p0, A.yaw_to(p0, p1), seed=seed)
        a.stand(1)
        a.walk(A.F(t0), A.F(t1), p1)
        a.blinks(1, n)
        walkers.append(a)
    # kid C stops by the window and looks out
    walkers[2].look(A.F(6.6), A.F(7.4), (2.5, 8.2, 1.4))

    # ---------------------------------------------------------------- dialogue: lip sync + looks + gestures
    lines = audio["lines"]
    for lid, t in LINES.items():
        who = actors[SPEAKER[lid]]
        nfr = who.lipsync(lines[lid]["file"], t)
        tend = t + nfr / 24
        if who is bob:
            bob.look(A.F(t - 0.2), A.F(t + 0.15), head(john))
            if lid in ("bob2", "bob3"):
                bob.gesture(A.F(t + 0.3), A.F(tend - 0.2), "r", energy=0.8 if lid == "bob2" else 1.0)
        elif who is john:
            john.look(A.F(t - 0.15), A.F(t + 0.1), head(bob, 1.72) if lid != "john3" else head(maxim, 1.55))
        elif who is maxim:
            maxim.look(A.F(t - 0.2), A.F(t + 0.1), head(bob, 1.72))
    # listeners
    john.look(A.F(0.2), A.F(0.6), head(bob, 1.72))
    maxim.look(A.F(0.0), A.F(0.5), head(bob, 1.72))
    maxim.look(A.F(2.5), A.F(2.9), head(john))
    maxim.look(A.F(3.4), A.F(3.8), head(bob, 1.72))
    maxim.look(A.F(14.75), A.F(15.0), head(john))
    maxim.look(A.F(16.4), A.F(17.2), (0.2, 1.4, 0.5))  # eyes down
    bob.look(A.F(13.6), A.F(13.9), head(maxim, 1.55))
    bob.look(A.F(14.8), A.F(15.1), head(john))
    for i, fr in enumerate(friends):
        fr.look(A.F(0.3 + i * 0.2), A.F(0.8 + i * 0.2), head(bob, 1.72))
        fr.look(A.F(14.9 + i * 0.15), A.F(15.2 + i * 0.15), head(john))
    # John straightens up and steps toward Maxim on his last line
    john.h.arm.rotation_euler = (math.radians(-5), 0, math.radians(john.yaw))
    john.h.arm.keyframe_insert("rotation_euler", frame=A.F(14.5))
    john.h.arm.location = john.pos
    john.h.arm.keyframe_insert("location", frame=A.F(14.5))
    newp = john.pos + (maxim.pos - john.pos).normalized() * 0.45
    ny = A.yaw_to(newp, maxim.pos)
    john.h.arm.rotation_euler = (0, 0, math.radians(ny))
    john.h.arm.keyframe_insert("rotation_euler", frame=A.F(15.0))
    john.h.arm.location = newp
    john.h.arm.keyframe_insert("location", frame=A.F(15.0))
    john.pos, john.yaw = newp, ny
    # Bob: smirk + adjusts the hat at the end
    bob.expr(A.F(16.6), mouth_corner_puller=0.0)
    bob.expr(A.F(17.2), mouth_corner_puller=0.5)
    bob.arm("r", A.F(17.6), 0, 38, 0)
    bob.arm("r", A.F(18.3), 70, 10, 120, out=10)
    bob.arm("r", A.F(19.2), 70, 10, 120, out=10)
    bob.arm("r", A.F(19.9), 0, 38, 0)
    # background: Artem slams a locker, Karim laughs
    door = cor.locker_doors[5]
    door.rotation_euler = (0, 0, 0)
    door.keyframe_insert("rotation_euler", frame=A.F(8.6))
    door.rotation_euler = (0, 0, math.radians(-95))
    door.keyframe_insert("rotation_euler", frame=A.F(9.3))
    door.keyframe_insert("rotation_euler", frame=A.F(10.25))
    door.rotation_euler = (0, 0, 0)
    door.keyframe_insert("rotation_euler", frame=A.F(10.45))
    artem.look(A.F(8.4), A.F(8.9), (-1.6, 7.4, 1.4))
    artem.arm("l", A.F(9.9), 0, 38, 0)
    artem.arm("l", A.F(10.3), 40, 20, 40, out=25)
    artem.arm("l", A.F(10.5), 30, 25, 20, out=20)
    artem.arm("l", A.F(11.3), 0, 38, 0)
    artem.look(A.F(10.6), A.F(11.0), head(karim))
    karim.look(A.F(10.5), A.F(10.9), head(artem))
    karim.nod(A.F(11.0), 10)
    karim.nod(A.F(11.5), 8)

    # ---------------------------------------------------------------- camera
    cam = A.HandheldCam(lens=18, fstop=2.4)
    J, B, M = head(john, 1.55), head(bob, 1.68), head(maxim, 1.5)
    cam.at(1, (0.5, 5.55, 1.66), (-1.5, 3.4, 1.5), J)
    cam.at(A.F(2.5), (0.42, 5.35, 1.63), (-1.55, 3.45, 1.52), J)
    cam.at(A.F(3.2), (0.55, 4.9, 1.62), (-1.0, 3.6, 1.6), B)
    cam.at(A.F(6.8), (0.28, 1.95, 1.56), (-0.55, 4.2, 1.66), B)
    cam.cut(A.F(6.95), (0.02, 2.4, 1.6), (-1.5, 3.55, 1.5), J)
    cam.at(A.F(8.4), (0.06, 2.45, 1.6), (-1.45, 3.6, 1.52), J)
    cam.at(A.F(8.85), (0.1, 2.5, 1.61), (-0.55, 4.0, 1.66), B)
    cam.at(A.F(13.35), (-0.02, 2.85, 1.63), (-0.55, 4.0, 1.66), B)
    cam.at(A.F(13.65), (-0.2, 3.15, 1.6), (0.38, 2.5, 1.5), M)
    cam.at(A.F(14.6), (-0.25, 3.2, 1.6), (0.38, 2.5, 1.5), M)
    cam.at(A.F(14.85), (-0.3, 3.1, 1.6), (-1.2, 3.35, 1.55), (-1.2, 3.35, 1.55))
    cam.at(A.F(16.4), (-0.32, 3.05, 1.6), (-1.15, 3.3, 1.55), (-1.15, 3.3, 1.55))
    cam.at(A.F(16.9), (-0.25, 3.05, 1.6), (0.38, 2.5, 1.45), M)
    cam.at(A.F(20.0), (-0.05, 2.85, 1.58), (0.38, 2.5, 1.45), M)
    cam.shake(1, n, amp=0.02)
    sc.camera = cam.cam
    return n


def setup_render(res, samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.05
    sc.cycles.max_bounces = 3
    sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 1
    sc.cycles.transmission_bounces = 1
    sc.cycles.transparent_max_bounces = 8
    sc.cycles.sample_clamp_indirect = 4
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.render.use_persistent_data = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Base Contrast"
    except TypeError:
        pass
    if os.environ.get("THREADS"):
        sc.render.threads_mode = "FIXED"
        sc.render.threads = int(os.environ["THREADS"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--frames", default=None, help="a-b or comma list")
    ap.add_argument("--res", default="1280x720")
    ap.add_argument("--samples", type=int, default=12)
    ap.add_argument("--blend")
    args = ap.parse_args()
    audio = json.load(open(args.audio))
    t0 = time.time()
    n = build(audio)
    setup_render(tuple(map(int, args.res.split("x"))), args.samples)
    if args.blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.blend))
    print(f"[build] {time.time() - t0:.0f}s", flush=True)
    os.makedirs(args.out, exist_ok=True)
    if args.frames and "-" in args.frames:
        a, b = map(int, args.frames.split("-"))
        frames = list(range(a, b + 1))
    elif args.frames:
        frames = [int(x) for x in args.frames.split(",")]
    else:
        frames = list(range(1, n + 1))
    sc = bpy.context.scene
    for f in frames:
        path = os.path.join(args.out, f"f{f:04d}.png")
        if os.path.exists(path):
            continue
        t1 = time.time()
        sc.frame_set(f)
        sc.render.filepath = path + ".tmp.png"
        bpy.ops.render.render(write_still=True)
        os.replace(path + ".tmp.png", path)
        print(f"[frame] {f} {time.time() - t1:.1f}s", flush=True)


if __name__ == "__main__":
    main()

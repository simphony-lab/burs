"""Renders frames of shots of one scene of the episode (resumable, splittable across processes).

    python render_episode.py --scene s1 [--shots 1A,1B] [--part 0 --parts 4] --out frames
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402

import episode as E  # noqa: E402


def setup(res, samples, threads):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.05
    sc.cycles.max_bounces = 3
    sc.cycles.diffuse_bounces = 1
    sc.cycles.glossy_bounces = 1
    sc.cycles.transmission_bounces = 1
    sc.cycles.transparent_max_bounces = 6
    sc.cycles.sample_clamp_indirect = 4
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.render.use_persistent_data = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.compression = 15
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Base Contrast"
    except TypeError:
        pass
    if threads:
        sc.render.threads_mode = "FIXED"
        sc.render.threads = threads


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True)
    ap.add_argument("--shots")
    ap.add_argument("--part", type=int, default=0)
    ap.add_argument("--parts", type=int, default=1)
    ap.add_argument("--out", required=True)
    ap.add_argument("--res", default="960x540")
    ap.add_argument("--samples", type=int, default=8)
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--frames", help="explicit frames (preview)")
    args = ap.parse_args()
    t0 = time.time()
    st = E.build(args.scene)
    setup(tuple(map(int, args.res.split("x"))), args.samples, args.threads)
    print(f"[build] {args.scene} {time.time() - t0:.0f}s frames={st.n}", flush=True)
    out = os.path.join(args.out, args.scene)
    os.makedirs(out, exist_ok=True)
    want = set(args.shots.split(",")) if args.shots else None
    ranges = [(s, int(round(a * 24)) + 1, int(round(b * 24))) for s, a, b in st.plan.shots]
    frames = []
    for s, a, b in ranges:
        if want and s not in want:
            continue
        frames += list(range(a, min(b, st.n) + 1))
    if args.frames:
        frames = [int(x) for x in args.frames.split(",")]
    frames = [f for i, f in enumerate(frames) if i % args.parts == args.part]
    sc = bpy.context.scene
    for f in frames:
        path = os.path.join(out, f"f{f:05d}.png")
        if os.path.exists(path):
            continue
        t1 = time.time()
        sc.frame_set(f)
        sc.camera = st.cam_for(f)
        sc.render.filepath = path + ".tmp.png"
        bpy.ops.render.render(write_still=True)
        os.replace(path + ".tmp.png", path)
        print(f"[frame] {args.scene} {f} {time.time() - t1:.1f}s", flush=True)


if __name__ == "__main__":
    main()

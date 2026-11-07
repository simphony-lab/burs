"""Renders the 3D shots of the movie (resumable: finished frames are skipped).

    python render.py --out shots [--only S1a,S2] [--res 720x1280] [--samples 8] [--frames 1,50]
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402,F401  (must come before mathutils)
import shots3d  # noqa: E402
from timeline import KIND, SHOTS  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--only")
    ap.add_argument("--res", default="720x1280")
    ap.add_argument("--samples", type=int, default=8)
    ap.add_argument("--frames", help="comma separated frames (preview)")
    args = ap.parse_args()
    res = tuple(map(int, args.res.split("x")))
    ids = args.only.split(",") if args.only else [s for s, _, k in SHOTS if k == "3d"]
    for sid in ids:
        out = os.path.join(args.out, sid)
        done = os.path.join(out, "DONE")
        if os.path.exists(done) and not args.frames:
            continue
        t0 = time.time()
        w, n, cam_for = shots3d.SHOT_FUNCS[sid]()
        only = [int(x) for x in args.frames.split(",")] if args.frames else None
        w.export_and_render(out, n, cam_for, res=res, samples=args.samples, only=only)
        if not args.frames:
            open(done, "w").write(str(n))
        print(f"[render] {sid}: {n} frames in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()

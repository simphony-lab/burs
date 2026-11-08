"""Exports, for each line / sound, where its source is relative to the camera (pan, distance)."""
import json
import sys

import bpy  # noqa: F401
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

import act as A
import shot_test as ST


def main(audio_path, out):
    audio = json.load(open(audio_path))
    ST.build(audio)
    sc = bpy.context.scene
    cam = sc.camera
    meta = {"lines": {}, "sfx": {}}

    def probe(t, pos):
        sc.frame_set(A.F(t))
        bpy.context.view_layer.update()
        co = world_to_camera_view(sc, cam, Vector(pos))
        dist = (cam.matrix_world.translation - Vector(pos)).length
        pan = (co.x - 0.5) * 2 if co.z > 0 else (1.0 if co.x > 0.5 else -1.0)
        return {"pan": round(pan, 3), "dist": round(dist, 3)}

    for lid, t in ST.LINES.items():
        who = ST.SPEAKER[lid]
        rig = bpy.data.objects[f"{who}_rig"]
        sc.frame_set(A.F(t + 0.3))
        hp = rig.matrix_world @ rig.pose.bones["head"].head
        meta["lines"][lid] = probe(t + 0.3, hp)
    meta["sfx"]["locker_slam"] = probe(ST.SFX["locker_slam"], (-1.55, 7.4, 1.0))
    meta["sfx"]["footsteps"] = probe(ST.SFX["footsteps"], (0.5, 10.0, 0.1))
    json.dump(meta, open(out, "w"), indent=1)
    print(meta)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

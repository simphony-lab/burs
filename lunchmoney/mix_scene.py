"""Dialogue mix for a scene: natural turn-taking with tension pauses, location-specific voice treatment
(street: dry lav/boom sound with a short wall reflection; corridor: short room reverb), loud-ish ambience bed
(~7 dB under speech, like real series), foley, stereo placement, loudness to -16 LUFS.

    python mix_scene.py --audio audio/audio.json --scene street1 --out scene1.wav
"""
import argparse
import json
import math
import subprocess
import wave

import numpy as np

SR = 48000

# timeline: (line id, gap before it in seconds), speaker placement (pan -1..1, distance m)
SCENES = {
    "street1": {
        "location": "street",
        "start": 0.6,
        "lines": [("s1_bob1", 0.0), ("s1_john1", 0.35), ("s1_bob2", 0.35), ("s1_john2", 0.45), ("s1_bob3", 0.4),
                  ("s1_maxim1", 0.5), ("s1_john3", 1.3), ("s1_bob4", 0.9), ("s1_john4", 0.5)],
        "place": {"bob": (0.1, 1.8), "john": (-0.45, 2.4), "maxim": (0.45, 2.1)},
        "tail": 1.4,
        "amb": ["amb_yard1", "amb_yard2"],
        "foley": [("snow_steps", "s1_maxim1", -0.3, 0.4, 0.25), ("snow_steps", "s1_john3", -0.5, -0.45, 0.3)],
    },
}

VOICE_FX = {
    # lav/boom outdoors: low cut, a little warmth, softened top end (real series measured dull above 3-4 kHz)
    "street": "highpass=f=85,equalizer=f=220:t=q:w=1.0:g=2.5,equalizer=f=3200:t=q:w=1.2:g=-1.5,"
              "highshelf=f=4500:g=-6,lowpass=f=10500,acompressor=threshold=-18dB:ratio=2:attack=10:release=150",
    "corridor": "highpass=f=85,equalizer=f=250:t=q:w=1.0:g=1.5,highshelf=f=5000:g=-4,"
                "acompressor=threshold=-18dB:ratio=2:attack=10:release=150",
}


def load(path, fx=None):
    cmd = ["ffmpeg", "-v", "error", "-i", path]
    if fx:
        cmd += ["-af", fx]
    cmd += ["-f", "f32le", "-ac", "1", "-ar", str(SR), "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, "<f4").astype(np.float32)


def pan_gains(p):
    a = (p + 1) * math.pi / 4
    return math.cos(a), math.sin(a)


def rms(x):
    return float(np.sqrt(np.mean(x ** 2) + 1e-12))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--amb_db", type=float, default=-7.0, help="ambience level relative to speech")
    args = ap.parse_args()
    meta = json.load(open(args.audio))
    sc = SCENES[args.scene]
    fx = VOICE_FX[sc["location"]]
    # place lines on the timeline
    t = sc["start"]
    events = []
    for lid, gap in sc["lines"]:
        t += gap
        line = meta["lines"][lid]
        sig = load(line["file"], fx)
        events.append((t, lid, line["who"], sig))
        t += len(sig) / SR
    total = t + sc["tail"]
    n = int(total * SR) + SR
    L = np.zeros(n, np.float32)
    R = np.zeros(n, np.float32)
    speech_rms = []
    starts = {}
    for t0, lid, who, sig in events:
        starts[lid] = t0
        pan, dist = sc["place"].get(who, (0.0, 2.0))
        sig = sig / (np.abs(sig).max() + 1e-6) * 0.5 * min(1.0, 1.8 / dist)
        speech_rms.append(rms(sig[np.abs(sig) > 0.02]))
        gl, gr = pan_gains(pan)
        i = int(t0 * SR)
        L[i:i + len(sig)] += sig * gl
        R[i:i + len(sig)] += sig * gr
        if sc["location"] == "street":
            # ground + school wall: two short, quiet reflections, no reverb tail
            for d, g, p in ((0.006, 0.18, pan), (0.021, 0.1, -0.7)):
                k = int(d * SR)
                g1, g2 = pan_gains(p)
                L[i + k:i + k + len(sig)] += sig * g * g1
                R[i + k:i + k + len(sig)] += sig * g * g2
    sp = float(np.median(speech_rms))
    # ambience bed: two different recordings, one per side for width, crossfaded over time
    a1 = load(meta["sfx"][sc["amb"][0]]["file"])
    a2 = load(meta["sfx"][sc["amb"][1]]["file"])

    def loop(a, length):
        out = np.zeros(length, np.float32)
        pos = 0
        fade = int(1.5 * SR)
        while pos < length:
            seg = a.copy()
            seg[:fade] *= np.linspace(0, 1, fade)
            seg[-fade:] *= np.linspace(1, 0, fade)
            m = min(len(seg), length - pos)
            out[pos:pos + m] += seg[:m]
            pos += len(seg) - fade
        return out

    b1, b2 = loop(a1, n), loop(a2, n)
    target = sp * 10 ** (args.amb_db / 20)
    g = target / (rms(np.concatenate([b1, b2])) + 1e-9)
    L += (b1 * 0.8 + b2 * 0.35) * g
    R += (b2 * 0.8 + b1 * 0.35) * g
    # foley
    for sid, anchor, offset, pan, gain in sc.get("foley", []):
        s = load(meta["sfx"][sid]["file"])
        s = s / (np.abs(s).max() + 1e-6) * gain * sp / 0.1
        i = int((starts[anchor] + offset) * SR)
        gl, gr = pan_gains(pan)
        L[i:i + len(s)] += s[: n - i] * gl
        R[i:i + len(s)] += s[: n - i] * gr
    pcm = np.clip(np.stack([L, R]).T[: int(total * SR)], -1, 1)
    tmp = args.out + ".raw.wav"
    with wave.open(tmp, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((pcm * 32767).astype("<i2").tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af", "loudnorm=I=-16:TP=-1.5:LRA=9", "-ar", str(SR),
                    args.out], check=True)
    print(f"{args.out}: {total:.1f}s, lines at", {k: round(v, 2) for k, v in starts.items()})


if __name__ == "__main__":
    main()

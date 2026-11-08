"""Film finish for the 20 s test: grade + grain + vignette, positional dialogue mix with room reverb,
school ambience bed, foley; final loudness normalisation.

    python compose_test.py --frames frames --audio audio/audio.json --meta meta.json --out test.mp4
"""
import argparse
import json
import math
import os
import subprocess
import tempfile

import numpy as np
from PIL import Image

import shot_test as ST

W, H = 1280, 720
FPS = 24
SR = 48000


# ============================================================================ picture

def grade_frame(img, f, vig):
    a = np.asarray(img.resize((W, H), Image.LANCZOS)).astype(np.float32) / 255.0
    a = a * 0.86  # exposure
    lum = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    a = lum[..., None] + (a - lum[..., None]) * 0.72  # desaturate
    # split tone: teal-green shadows, neutral-warm highlights
    sh = np.clip(1 - lum * 1.6, 0, 1)[..., None]
    hi = np.clip((lum - 0.55) * 2.0, 0, 1)[..., None]
    a = a + sh * np.array([-0.012, 0.01, 0.008], np.float32) + hi * np.array([0.012, 0.006, -0.01], np.float32)
    # filmic s-curve with lifted blacks
    a = np.clip(a, 0, 1)
    a = 0.035 + 0.93 * (a * a * (3 - 2 * a) * 0.55 + a * 0.45)
    a = a * vig
    # grain (luma), changes every frame
    rng = np.random.default_rng(f)
    g = rng.normal(0, 0.022, (H // 2, W // 2)).astype(np.float32)
    g = np.asarray(Image.fromarray(g).resize((W, H), Image.BILINEAR))
    a = a + g[..., None] * (0.6 + 0.4 * (1 - lum[..., None] if lum.shape == g.shape else 1))
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def vignette():
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / math.sqrt(2)
    return (1 - 0.38 * np.clip(r - 0.3, 0, 1) ** 1.6)[..., None].astype(np.float32)


# ============================================================================ sound

def load(path, sr=SR):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, "<f4").astype(np.float32)


def room_ir(rt60=0.65, pre=0.012, seed=1):
    r = np.random.default_rng(seed)
    n = int(SR * rt60 * 1.2)
    t = np.arange(n) / SR
    ir = r.normal(0, 1, n).astype(np.float32) * np.exp(-6.9 * t / rt60)
    # early reflections of a corridor
    for d, g in ((0.009, 0.6), (0.017, 0.45), (0.026, 0.35), (0.041, 0.25)):
        ir[int(d * SR)] += g * 3
    # darker tail
    k = 6
    ir = np.convolve(ir, np.ones(k) / k, mode="same")
    ir = np.concatenate([np.zeros(int(pre * SR), np.float32), ir])
    return ir / np.abs(ir).sum() * 6


def conv(x, ir):
    n = len(x) + len(ir) - 1
    N = 1 << (n - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[:n]
    return y.astype(np.float32)


def highpass(x, fc=90):
    a = math.exp(-2 * math.pi * fc / SR)
    y = np.empty_like(x)
    prev_x = prev_y = 0.0
    # simple one-pole high-pass (vectorised enough for short clips)
    out = []
    for i in range(0, len(x), 4096):
        seg = x[i:i + 4096]
        ys = np.empty_like(seg)
        for j, v in enumerate(seg):
            prev_y = a * (prev_y + v - prev_x)
            prev_x = v
            ys[j] = prev_y
        out.append(ys)
    return np.concatenate(out) if out else y


def lowpass(x, fc):
    a = math.exp(-2 * math.pi * fc / SR)
    from itertools import accumulate  # noqa: F401
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def pan_gains(p):
    """p in [-1, 1] -> constant power L/R"""
    ang = (p + 1) * math.pi / 4
    return math.cos(ang), math.sin(ang)


def mix(audio, meta, out_wav):
    n = int(SR * ST.DUR) + SR
    L = np.zeros(n, np.float32)
    R = np.zeros(n, np.float32)
    ir = room_ir()

    def place(sig, t, pan, gain, wet=0.14, width=0.0):
        i = int(t * SR)
        sig = sig[: n - i]
        gl, gr = pan_gains(pan)
        dry = sig * gain
        L[i:i + len(sig)] += dry * gl
        R[i:i + len(sig)] += dry * gr
        if wet:
            w = conv(sig, ir)[: n - i] * gain * wet
            # reverb a bit wider than the source
            gl2, gr2 = pan_gains(pan * 0.4)
            L[i:i + len(w)] += w * gl2
            R[i:i + len(w)] += w * gr2

    # dialogue
    for lid, t in ST.LINES.items():
        sig = load(audio["lines"][lid]["file"])
        sig = sig / (np.abs(sig).max() + 1e-6) * 0.5
        m = meta["lines"].get(lid, {"pan": 0.0, "dist": 2.0})
        dist = max(0.8, m["dist"])
        gain = min(1.0, 1.6 / dist)
        wet = min(0.35, 0.08 + 0.04 * dist)
        place(sig, t, max(-0.8, min(0.8, m["pan"])), gain, wet=wet)
    # ambience bed (stereo from mono with a small delay), quieter under dialogue
    amb = load(audio["sfx"]["amb_corridor"]["file"])
    amb = np.tile(amb, 2)[:n] * 0.11
    d = int(0.013 * SR)
    L[:len(amb)] += amb
    R[d:len(amb)] += amb[:len(amb) - d] * 0.95
    # foley
    for sid, t in ST.SFX.items():
        sig = load(audio["sfx"][sid]["file"])
        sig = sig / (np.abs(sig).max() + 1e-6)
        m = meta["sfx"].get(sid, {"pan": 0.0, "dist": 4.0})
        g = {"locker_slam": 0.55, "footsteps": 0.18}.get(sid, 0.3) * min(1.0, 3.0 / max(1.0, m["dist"]))
        place(sig, t, max(-0.9, min(0.9, m["pan"])), g, wet=0.3)
    # gentle ducking of the bed under speech (sidechain from dialogue envelope)
    st = np.stack([L, R])
    raw = subprocess.run
    pcm = np.clip(st.T[: int(SR * ST.DUR)], -1, 1)
    tmp = out_wav + ".raw.wav"
    import wave
    with wave.open(tmp, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((pcm * 32767).astype("<i2").tobytes())
    # final: loudness to -16 LUFS (phone/YouTube), true peak -1.5
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af",
                    "highpass=f=50,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120,"
                    "loudnorm=I=-16:TP=-1.5:LRA=9", "-ar", str(SR), out_wav], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    audio = json.load(open(args.audio))
    meta = json.load(open(args.meta))
    work = tempfile.mkdtemp(prefix="lm_")
    vig = vignette()
    n = int(ST.DUR * FPS)
    for f in range(1, n + 1):
        src = os.path.join(args.frames, f"f{f:04d}.png")
        img = Image.open(src).convert("RGB")
        grade_frame(img, f, vig).save(os.path.join(work, f"o{f:04d}.jpg"), quality=94)
    wav = os.path.join(work, "mix.wav")
    mix(audio, meta, wav)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(work, "o%04d.jpg"),
                    "-i", wav, "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", args.out], check=True)
    print("wrote", args.out)


if __name__ == "__main__":
    main()

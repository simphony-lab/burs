"""Final assembly of the episode "Первая смена": rendered shots -> graded picture, per-scene dialogue mix from the
timing plan (episode_plan.py) with location treatment, ambience beds, foley; title card, end card, loudness.

    python compose_episode.py --audio <lm_ep>/audio.json --renders renders --out out/lunchmoney_ep1.mp4
Missing shots are filled with a dark placeholder so a partial cut can be checked early.
"""
import argparse
import json
import math
import os
import subprocess
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import episode_plan as P

W, H = 1280, 720
FPS = P.FPS
SR = 48000
TITLE = 3.0    # seconds of title card before scene 1
ENDCARD = 3.0  # seconds of end card after scene 5
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# where the voices sit in the stereo image (pan -1..1) and how far from the camera (m), per scene
PLACE = {
    "s1": {"bob": (0.1, 1.8), "john": (-0.4, 2.2), "maxim": (0.45, 2.4), "karim": (0.3, 2.4), "artem": (-0.15, 2.6)},
    "s2": {"bob": (0.0, 2.2), "karim": (0.3, 2.3), "artem": (-0.3, 2.4)},
    "s3": {"bob": (0.05, 1.9), "karim": (0.35, 2.3), "artem": (-0.35, 2.3), "kid1": (-0.2, 1.8), "kid2": (0.25, 1.9),
           "kid3": (0.1, 2.0), "kid4": (-0.25, 2.0), "kid5": (0.3, 2.1)},
    "s4": {"bob": (0.05, 1.9), "karim": (0.35, 2.2), "artem": (-0.35, 2.3), "hoodie": (-0.2, 2.0)},
    "s5": {"bob": (0.0, 2.0), "karim": (0.3, 2.3), "artem": (-0.3, 2.3), "kid6": (-0.2, 2.0), "kid7": (0.2, 2.1)},
}

VOICE_FX = {
    "street": "highpass=f=80,equalizer=f=220:t=q:w=1.0:g=1.5,highshelf=f=6000:g=-2.5",
    "hall": "highpass=f=85,equalizer=f=250:t=q:w=1.0:g=1.5,highshelf=f=5000:g=-3.5,"
            "acompressor=threshold=-18dB:ratio=2:attack=10:release=150",
}


# ============================================================================ sound

def load(path, fx=None):
    cmd = ["ffmpeg", "-v", "error", "-i", path]
    if fx:
        cmd += ["-af", fx]
    cmd += ["-f", "f32le", "-ac", "1", "-ar", str(SR), "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, "<f4").astype(np.float32)


def pan_gains(p):
    a = (max(-1, min(1, p)) + 1) * math.pi / 4
    return math.cos(a), math.sin(a)


def rms(x):
    return float(np.sqrt(np.mean(x ** 2) + 1e-12))


def room_ir(rt60=0.7, pre=0.012, seed=1):
    r = np.random.default_rng(seed)
    n = int(SR * rt60 * 1.2)
    t = np.arange(n) / SR
    ir = r.normal(0, 1, n).astype(np.float32) * np.exp(-6.9 * t / rt60)
    for d, g in ((0.009, 0.6), (0.017, 0.45), (0.026, 0.35), (0.041, 0.25)):
        ir[int(d * SR)] += g * 3
    k = 6
    ir = np.convolve(ir, np.ones(k) / k, mode="same")
    ir = np.concatenate([np.zeros(int(pre * SR), np.float32), ir])
    return (ir / np.abs(ir).sum() * 6).astype(np.float32)


def conv(x, ir):
    n = len(x) + len(ir) - 1
    N = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[:n].astype(np.float32)


def loop(a, length, fade_s=1.5):
    out = np.zeros(length, np.float32)
    fade = min(int(fade_s * SR), len(a) // 3)
    pos = 0
    while pos < length:
        seg = a.copy()
        seg[:fade] *= np.linspace(0, 1, fade)
        seg[-fade:] *= np.linspace(1, 0, fade)
        m = min(len(seg), length - pos)
        out[pos:pos + m] += seg[:m]
        pos += len(seg) - fade
    return out


def mix_scene(p, meta, amb_db=-7.0):
    """Stereo float mix of one scene, exactly p.frames / FPS seconds long."""
    loc = "street" if p.loc == "street" else "hall"
    n = int(round(p.frames / FPS * SR))
    pad = 3 * SR
    L = np.zeros(n + pad, np.float32)
    R = np.zeros(n + pad, np.float32)
    ir = room_ir(0.75 if p.name in ("s3", "s5") else 0.65)
    place = PLACE.get(p.name, {})

    def put(sig, t, pan, gain, wet=0.0, refl=False):
        i = max(0, int(t * SR))
        sig = sig[: len(L) - i] * gain
        gl, gr = pan_gains(pan)
        L[i:i + len(sig)] += sig * gl
        R[i:i + len(sig)] += sig * gr
        if refl:  # street: ground + school wall, two quiet reflections, no tail
            for d, g, pp in ((0.006, 0.18, pan), (0.021, 0.1, -0.7)):
                k = i + int(d * SR)
                s2 = sig[: len(L) - k]
                g1, g2 = pan_gains(pp)
                L[k:k + len(s2)] += s2 * g * g1
                R[k:k + len(s2)] += s2 * g * g2
        if wet:
            w = conv(sig, ir)[: len(L) - i] * wet
            g1, g2 = pan_gains(pan * 0.4)
            L[i:i + len(w)] += w * g1
            R[i:i + len(w)] += w * g2

    speech = []
    for lid, (t0, t1) in sorted(p.cues.items(), key=lambda kv: kv[1][0]):
        line = meta["lines"][lid]
        sig = load(line["file"], VOICE_FX[loc])
        sig = sig / (np.abs(sig).max() + 1e-6) * 0.5
        pan, dist = place.get(line["who"], (0.0, 2.2))
        gain = min(1.0, 1.8 / dist)
        speech.append(rms(sig[np.abs(sig) > 0.02]) * gain)
        if loc == "street":
            put(sig, t0, pan, gain, refl=True)
        else:
            put(sig, t0, pan, gain, wet=min(0.3, 0.06 + 0.035 * dist))
    sp = float(np.median(speech)) if speech else 0.08
    # ambience: two recordings crossed left/right for width
    a1 = load(meta["sfx"][p.amb[0]]["file"])
    a2 = load(meta["sfx"][p.amb[1]]["file"])
    b1, b2 = loop(a1, len(L)), loop(a2[int(3.3 * SR):] if len(a2) > 8 * SR else a2, len(L))
    g = sp * 10 ** (amb_db / 20) / (rms(np.concatenate([b1, b2])) + 1e-9)
    L += (b1 * 0.8 + b2 * 0.35) * g
    R += (b2 * 0.8 + b1 * 0.35) * g
    # foley at plan times
    for sid, t, pan, gain in p.sfx:
        if sid not in meta["sfx"]:
            print("  missing sfx", sid)
            continue
        s = load(meta["sfx"][sid]["file"])
        s = s / (np.abs(s).max() + 1e-6) * gain * sp / 0.1
        put(s, t, pan, 1.0, wet=0.25 if loc == "hall" else 0.0)
    out = np.stack([L[:n], R[:n]])
    # click-free scene boundaries
    f = int(0.04 * SR)
    out[:, :f] *= np.linspace(0, 1, f)
    out[:, -f:] *= np.linspace(1, 0, f)
    return out


def write_wav(path, st):
    pcm = np.clip(st.T, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((pcm * 32767).astype("<i2").tobytes())


# ============================================================================ picture

def vignette():
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / math.sqrt(2)
    return (1 - 0.38 * np.clip(r - 0.3, 0, 1) ** 1.6)[..., None].astype(np.float32)


GRAIN = None


def grade(a, f, vig, warm=0.0):
    """a: HxWx3 float 0..1 (already scaled to output size)."""
    global GRAIN
    a = a * 0.88
    lum = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    a = lum[..., None] + (a - lum[..., None]) * 0.74
    sh = np.clip(1 - lum * 1.6, 0, 1)[..., None]
    hi = np.clip((lum - 0.55) * 2.0, 0, 1)[..., None]
    a = a + sh * np.array([-0.012, 0.01, 0.008], np.float32) \
        + hi * np.array([0.012 + warm, 0.006, -0.01 - warm], np.float32)
    a = np.clip(a, 0, 1)
    a = 0.035 + 0.93 * (a * a * (3 - 2 * a) * 0.55 + a * 0.45)
    a = a * vig
    if GRAIN is None:  # pre-baked grain plates, picked pseudo-randomly per frame
        rng = np.random.default_rng(7)
        GRAIN = []
        for _ in range(12):
            g = rng.normal(0, 0.02, (H // 2, W // 2)).astype(np.float32)
            GRAIN.append(np.asarray(Image.fromarray(g).resize((W, H), Image.BILINEAR))[..., None])
    a = a + GRAIN[(f * 7) % 12] * (0.55 + 0.45 * (1 - lum[..., None]))
    return (np.clip(a, 0, 1) * 255).astype(np.uint8)


def card(lines, sizes):
    img = Image.new("RGB", (W, H), (6, 6, 7))
    d = ImageDraw.Draw(img)
    total = sum(s * 1.35 for s in sizes)
    y = H / 2 - total / 2
    for text, s in zip(lines, sizes):
        fnt = ImageFont.truetype(FONT, s)
        w = d.textlength(text, font=fnt)
        d.text(((W - w) / 2, y), text, font=fnt, fill=(232, 228, 220))
        y += s * 1.35
    return np.asarray(img).astype(np.float32) / 255.0


def scene_frames(scene, renders):
    """Yields HxWx3 uint8 frames of one scene from its shot files (placeholder for missing shots)."""
    p = P.SCENES[scene]()
    for sid, a, b in p.shots:
        fa, fb = int(round(a * FPS)) + 1, min(int(round(b * FPS)), p.frames)
        n = fb - fa + 1
        path = os.path.join(renders, f"{scene}_{sid}.mp4")
        got = 0
        if os.path.exists(path):
            proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={W}:{H}:flags=lanczos",
                                     "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
            last = None
            while got < n:
                buf = proc.stdout.read(W * H * 3)
                if len(buf) < W * H * 3:
                    break
                last = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
                got += 1
                yield last
            proc.stdout.close()
            proc.wait()
            if got < n:
                print(f"  {scene}_{sid}: {got}/{n} frames, holding last")
            while got < n and last is not None:
                got += 1
                yield last
        if got < n:
            print(f"  {scene}_{sid}: missing, placeholder")
            ph = (card([f"{scene} {sid}", "(рендер не готов)"], [40, 26]) * 120).astype(np.uint8)
            for _ in range(n - got):
                yield ph


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--renders", default="renders")
    ap.add_argument("--out", required=True)
    ap.add_argument("--scenes", default=",".join(P.ORDER))
    ap.add_argument("--crf", type=int, default=20)
    args = ap.parse_args()
    meta = json.load(open(args.audio))
    scenes = args.scenes.split(",")
    work = tempfile.mkdtemp(prefix="lmep_")
    plans = {k: P.SCENES[k]() for k in scenes}
    full = len(scenes) == len(P.ORDER)
    # ---- sound
    parts = []
    if full:
        t = np.zeros((2, int(TITLE * SR)), np.float32)
        amb = load(meta["sfx"]["amb_yard1"]["file"])[: t.shape[1]]
        ramp = np.linspace(0, 1, len(amb)) ** 2 * 0.05
        t[0, :len(amb)] = amb * ramp
        t[1, :len(amb)] = amb * ramp
        parts.append(t)
    for k in scenes:
        print("mix", k)
        parts.append(mix_scene(plans[k], meta))
    if full:
        e = parts[-1][:, -int(2.0 * SR):]
        e *= np.linspace(1, 0, e.shape[1]) ** 1.5  # sound fades out with the last picture
        parts.append(np.zeros((2, int(ENDCARD * SR)), np.float32))
    raw = os.path.join(work, "mix_raw.wav")
    wav = os.path.join(work, "mix.wav")
    write_wav(raw, np.concatenate(parts, axis=1))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af",
                    "highpass=f=45,acompressor=threshold=-20dB:ratio=2:attack=8:release=140,"
                    "loudnorm=I=-16:TP=-1.5:LRA=9", "-ar", str(SR), wav], check=True)
    # ---- picture
    vig = vignette()
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "slow",
                            "-crf", str(args.crf), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                            "-shortest", "-movflags", "+faststart", args.out], stdin=subprocess.PIPE)
    f = 0

    def emit(a):
        nonlocal f
        f += 1
        enc.stdin.write(a.tobytes())

    if full:
        tc = card(["LUNCH MONEY", "Первая смена"], [64, 32])
        nt = int(TITLE * FPS)
        for i in range(nt):
            k = min(1.0, i / 12, (nt - 1 - i) / 12)
            emit((tc * k * 255).astype(np.uint8))
    total_scene_frames = sum(p.frames for p in plans.values())
    done = 0
    for k in scenes:
        print("picture", k)
        warm = 0.006 if plans[k].loc == "street" else 0.0
        for fr in scene_frames(k, args.renders):
            a = fr.astype(np.float32) / 255.0
            done += 1
            if full and total_scene_frames - done < 36:  # fade to black at the very end
                a = a * ((total_scene_frames - done) / 36.0)
            emit(grade(a, f, vig, warm))
    if full:
        ec = card(["Продолжение следует"], [40])
        ne = int(ENDCARD * FPS)
        for i in range(ne):
            k = min(1.0, i / 12, (ne - 1 - i) / 12)
            emit((ec * k * 255).astype(np.uint8))
    enc.stdin.close()
    enc.wait()
    print("wrote", args.out, f"{f} frames = {f / FPS:.1f}s")


if __name__ == "__main__":
    main()

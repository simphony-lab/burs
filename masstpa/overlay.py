"""Second pass: draws chat, caption and nametags on top of the rendered frames, synthesizes a simple
sound track and encodes the final vertical video.

    python overlay.py --frames frames --out masstpa.mp4
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

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "unifont.otf")

WHITE = (255, 255, 255)
GRAY = (170, 170, 170)
GOLD = (255, 170, 0)
PURPLE = (255, 85, 255)
GREEN = (85, 255, 85)

TPA = [("brohacker", PURPLE), (" хочет телепортироваться к вам.", GOLD)]


def say(name, text, rank=("Игрок", GRAY)):
    return [(f"[{rank[0]}] ", rank[1]), (name, WHITE), (" » ", GRAY), (text, WHITE)]


# (frame, segments); chat is cleared at the start of each listed shot
CHAT = {
    "A": [
        (24, [("[MassTPA] ", PURPLE), ("модуль включён", GREEN)]),
        (31, [("[MassTPA] ", PURPLE), ("отправляю /tpa всем игрокам...", WHITE)]),
        (46, [("[MassTPA] ", PURPLE), ("готово: 47/47 запросов", GREEN)]),
    ],
    "BC": [
        (68, TPA),
        (70, [("Введите ", GRAY), ("/tpaccept", GREEN), (", чтобы принять.", GRAY)]),
        (73, TPA),
        (76, TPA),
        (79, TPA),
        (86, say("pixel_masha", "эээ что??")),
        (104, say("dimon_pro", "мне тоже пришло", ("VIP", GREEN))),
        (118, say("kotik_777", "он ЛЕТАЕТ")),
        (134, say("lavaKing", "кто такой brohacker", ("Премиум", GOLD))),
        (166, say("snowbunny", "админ где??")),
        (192, say("brohacker", "принимайте)")),
    ],
}
CAPTION = [  # (first frame, last frame, lines of (text, color))
    (1, 62, [[("когда читер", WHITE)], [("нашёл ", WHITE), ("MassTPA", PURPLE)]]),
]
QUESTION_POPS = [68 + 9, 71 + 9, 74 + 9, 80 + 9, 84 + 9]


def chat_group(f):
    return "A" if f <= 62 else "BC"


def text_w(draw, s, font):
    return draw.textlength(s, font=font)


def draw_shadowed(draw, xy, s, font, col, alpha=255, shadow=3):
    x, y = xy
    sc = tuple(int(c * 0.25) for c in col)
    draw.text((x + shadow, y + shadow), s, font=font, fill=sc + (alpha,))
    draw.text((x, y), s, font=font, fill=col + (alpha,))


def draw_chat(img, f):
    W, H = img.size
    lines = [(f0, seg) for f0, seg in CHAT[chat_group(f)] if f0 <= f]
    if not lines:
        return
    lines = lines[-5:]
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    fs = 22
    font = ImageFont.truetype(FONT, fs)
    lh = 27
    bottom = int(H * 0.72)
    x0 = int(W * 0.02)
    width = int(W * 0.72)
    for i, (f0, seg) in enumerate(reversed(lines)):
        age = f - f0
        a = min(1.0, (age + 1) / 3.0)
        y = bottom - (i + 1) * lh
        d.rectangle([x0, y, x0 + width, y + lh], fill=(0, 0, 0, int(85 * a)))
        x = x0 + 8
        for s, col in seg:
            draw_shadowed(d, (x, y + (lh - fs) // 2 - 2), s, font, col, int(255 * a), shadow=2)
            x += text_w(d, s, font)
    img.alpha_composite(ov)


def draw_caption(img, f):
    W, H = img.size
    for f0, f1, lines in CAPTION:
        if not (f0 <= f <= f1):
            continue
        d = ImageDraw.Draw(img)
        fs = 52
        font = ImageFont.truetype(FONT, fs)
        pop = min(1.0, (f - f0 + 1) / 4.0)
        a = 255 if f < f1 - 3 else int(255 * (f1 - f) / 3)
        y = int(H * 0.045)
        for line in lines:
            total = sum(text_w(d, s, font) for s, _ in line)
            x = (W - total) / 2
            for s, col in line:
                d.text((x, y), s, font=font, fill=col + (a,), stroke_width=max(3, fs // 12),
                       stroke_fill=(0, 0, 0, a))
                x += text_w(d, s, font)
            y += int(fs * 1.15 * pop)


def draw_tags(img, tags):
    W, H = img.size
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for t in sorted(tags, key=lambda t: -t["depth"]):
        fs = int(max(14, min(26, t["size"] * 0.7)))
        font = ImageFont.truetype(FONT, fs)
        s = t["name"]
        w = text_w(d, s, font)
        x, y = t["x"] - w / 2, t["y"] - fs * 1.5
        if x > W or x + w < 0 or y > H or y + fs < 0:
            continue
        pad = max(3, fs // 5)
        d.rectangle([x - pad, y - pad // 2, x + w + pad, y + fs + pad], fill=(0, 0, 0, 100))
        col = PURPLE if s == "brohacker" else WHITE
        d.text((x, y - 1), s, font=font, fill=col + (235,))
    img.alpha_composite(ov)


def grade(img):
    """Soft bloom on bright areas, gentle warm tint and vignette."""
    a = np.asarray(img.convert("RGB")).astype(np.float32) / 255.0
    lum = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    bright = np.clip((lum - 0.72) / 0.28, 0, 1)[..., None] * a
    from PIL import ImageFilter
    b = Image.fromarray((bright * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(22))
    b = np.asarray(b).astype(np.float32) / 255.0
    a = 1 - (1 - a) * (1 - b * 0.55)
    a = a * np.array([1.03, 1.0, 0.95], np.float32)
    h, w = lum.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / math.sqrt(2)
    a = a * (1 - 0.35 * np.clip(r - 0.35, 0, 1) ** 1.5)[..., None]
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert("RGBA")


def flash(img, f):
    """Short white flash when the requests fire."""
    if 30 <= f <= 34:
        a = int(170 * (1 - (f - 30) / 5))
        img.alpha_composite(Image.new("RGBA", img.size, (255, 255, 255, a)))


# ----------------------------------------------------------------------------- sound

SR = 44100


def env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(attack, 1e-4)) * np.exp(-t / decay)


def load_voice(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-af",
                          "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                          "silenceremove=start_periods=1:start_threshold=-45dB,areverse",
                          "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, "<i2").astype(np.float32) / 32768.0


def synth(fps, frames, voice_lines=()):
    out = np.zeros(int(SR * frames / fps) + SR, np.float32)
    rng = np.random.default_rng(1)

    def add(f, sig, gain=1.0):
        i = int((f - 1) / fps * SR)
        sig = sig[: len(out) - i]
        out[i:i + len(sig)] += sig * gain

    def tone(freq, dur, decay, harm=(1.0,)):
        n = int(SR * dur)
        t = np.arange(n) / SR
        s = sum(a * np.sin(2 * math.pi * freq * (k + 1) * t) for k, a in enumerate(harm))
        return (s * env(n, 0.004, decay)).astype(np.float32)

    # soft wind bed
    n = len(out)
    wind = np.cumsum(rng.normal(0, 1, n)).astype(np.float32)
    wind -= np.convolve(wind, np.ones(4000) / 4000, mode="same")
    wind /= np.abs(wind).max() + 1e-6
    out += wind * 0.05

    # panel pop + click
    add(5, tone(520, 0.12, 0.04) + tone(780, 0.12, 0.03) * 0.5, 0.25)
    click = (rng.normal(0, 1, int(SR * 0.02)) * env(int(SR * 0.02), 0.001, 0.004)).astype(np.float32)
    add(24, click, 0.6)
    add(24, tone(1200, 0.08, 0.02), 0.2)
    # whoosh of the requests
    n = int(SR * 1.0)
    t = np.arange(n) / SR
    sweep = np.sin(2 * math.pi * np.cumsum(220 + 900 * t) / SR)
    noise = rng.normal(0, 1, n)
    noise = np.convolve(noise, np.ones(6) / 6, mode="same")
    e = np.sin(np.pi * np.clip(t / 1.0, 0, 1)) ** 2
    add(30, ((sweep * 0.5 + noise * 0.6) * e).astype(np.float32), 0.35)
    # notification plings for each request in chat
    for f in (68, 73, 76, 79):
        add(f, tone(1318.5, 0.5, 0.12, (1.0, 0.0, 0.25)) + tone(1975.5, 0.5, 0.1) * 0.4, 0.3)
    # "?" pops
    for f in QUESTION_POPS:
        n = int(SR * 0.06)
        t = np.arange(n) / SR
        add(f, (np.sin(2 * math.pi * np.cumsum(500 + 9000 * t) / SR) * env(n, 0.002, 0.02)).astype(np.float32), 0.35)
    # chat blips
    for f0, seg in CHAT["BC"][5:]:
        add(f0, tone(880, 0.08, 0.025), 0.12)
    sfx_peak = np.abs(out).max() + 1e-6
    out *= 0.45 / sfx_peak
    for v in voice_lines:
        sig = load_voice(v["file"])
        sig *= 0.9 / (np.abs(sig).max() + 1e-6)
        add(v["frame"], sig, 1.0)
    out /= max(1.0, np.abs(out).max() / 0.95)
    return out[: int(SR * frames / fps)]


def write_wav(path, data):
    pcm = (np.clip(data, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ----------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--voice", help="lines.json from voice.py")
    ap.add_argument("--only", help="comma separated frames to write as PNG previews instead of a video")
    args = ap.parse_args()

    meta = json.load(open(os.path.join(args.frames, "meta.json")))
    fps, nframes = meta["fps"], meta["frames"]
    tmp = tempfile.mkdtemp(prefix="masstpa_")
    todo = [int(x) for x in args.only.split(",")] if args.only else range(1, nframes + 1)
    for f in todo:
        img = grade(Image.open(os.path.join(args.frames, f"f{f:04d}.png")))
        flash(img, f)
        draw_tags(img, meta["tags"][str(f)])
        draw_chat(img, f)
        draw_caption(img, f)
        dst = os.path.join(tmp if not args.only else os.path.dirname(os.path.abspath(args.out)), f"o{f:04d}.png")
        img.convert("RGB").save(dst)
    if args.only:
        return
    wav = os.path.join(tmp, "audio.wav")
    lines = json.load(open(args.voice)) if args.voice else []
    write_wav(wav, synth(fps, nframes, lines))
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", os.path.join(tmp, "o%04d.png"), "-i", wav,
        "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", args.out,
    ], check=True)
    print("wrote", args.out)


if __name__ == "__main__":
    main()

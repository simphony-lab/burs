"""Second pass for the 6-minute movie: game HUD, cheat overlay, cheat menu, chat, subtitles, nametags,
lag effects, music + sound effects + voices, final encode.

    python compose.py --shots shots --voice voice/lines.json --out out/masstpa_6min.mp4 [--only S7d] [--preview 5]
"""
import argparse
import json
import math
import os
import random
import re
import subprocess
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import timeline as T
from sprites import ICONS

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "unifont.otf")
W, H = 720, 1280
FPS = T.FPS
_fonts = {}


def font(size):
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(FONT, size)
    return _fonts[size]


def tw(d, s, f):
    return d.textlength(s, font=f)


def shadow_text(d, xy, s, f, col, a=255, sh=2):
    x, y = xy
    d.text((x + sh, y + sh), s, font=f, fill=tuple(int(c * 0.25) for c in col) + (a,))
    d.text((x, y), s, font=f, fill=tuple(col) + (a,))


def outline_text(d, xy, s, f, col, a=255, stroke=3, anchor=None):
    d.text(xy, s, font=f, fill=tuple(col) + (a,), stroke_width=stroke, stroke_fill=(0, 0, 0, a), anchor=anchor)


def rainbow(i, t):
    h = (i * 0.07 + t * 0.25) % 1.0
    r, g, b = [int(255 * (0.5 + 0.5 * math.cos(2 * math.pi * (h + k)))) for k in (0, 1 / 3, 2 / 3)]
    return (max(r, 60), max(g, 60), max(b, 60))


_icon_cache = {}


def icon(kind, size):
    key = (kind, size)
    if key not in _icon_cache:
        spr, pal = ICONS[kind]()
        im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        for (x, y), k in spr.items():
            im.putpixel((x, y), pal[k] + (255,))
        _icon_cache[key] = im.resize((size, size), Image.NEAREST)
    return _icon_cache[key]


# ============================================================================ game HUD

HOTBAR = ["sword", "axe", "apple", "totem", "pearl", "cobble", "bread", None, None]
COUNTS = {2: "12", 3: "3", 4: "16", 5: "64", 6: "32"}


def heart(d, x, y, s, kind):
    """kind: full, half, empty, gold"""
    col = {"full": (220, 30, 30), "half": (220, 30, 30), "empty": (40, 10, 10), "gold": (250, 200, 40)}[kind]
    pts = [(1, 0), (2, 0), (4, 0), (5, 0), (0, 1), (6, 1), (0, 2), (6, 2), (1, 3), (5, 3), (2, 4), (4, 4), (3, 5)]
    px = s / 7
    d.rectangle([x, y + px, x + 7 * px, y + 3 * px], fill=(0, 0, 0, 255))
    for yy in range(6):
        for xx in range(7):
            inside = (yy == 0 and xx in (1, 2, 4, 5)) or (yy in (1, 2) and 0 <= xx <= 6) or \
                     (yy == 3 and 1 <= xx <= 5) or (yy == 4 and 2 <= xx <= 4) or (yy == 5 and xx == 3)
            if not inside:
                continue
            c = col
            if kind == "half" and xx > 3:
                c = (40, 10, 10)
            d.rectangle([x + xx * px, y + yy * px, x + (xx + 1) * px - 1, y + (yy + 1) * px - 1], fill=c + (255,))
    d.rectangle([x + 1 * px, y + 1 * px, x + 2 * px - 1, y + 2 * px - 1], fill=(255, 200, 200, 255))


def draw_hud(img, d, st):
    """st: dict(slot, hp(0..20), gold(absorption), cooldown 0..1)"""
    s = 44
    x0 = (W - 9 * s) // 2
    y0 = H - 150
    d.rectangle([x0 - 4, y0 - 4, x0 + 9 * s + 4, y0 + s + 4], fill=(0, 0, 0, 150))
    for i in range(9):
        x = x0 + i * s
        d.rectangle([x, y0, x + s - 2, y0 + s - 2], outline=(140, 140, 140, 230), width=2,
                    fill=(60, 60, 60, 140))
        if HOTBAR[i]:
            img.alpha_composite(icon(HOTBAR[i], 32), (x + 5, y0 + 5))
            if i in COUNTS:
                shadow_text(d, (x + s - 22, y0 + s - 20), COUNTS[i], font(16), (255, 255, 255))
    sx = x0 + st.get("slot", 0) * s
    d.rectangle([sx - 3, y0 - 3, sx + s + 1, y0 + s + 1], outline=(250, 250, 250, 255), width=3)
    # offhand shield
    d.rectangle([x0 - 60, y0, x0 - 16, y0 + s - 2], outline=(140, 140, 140, 230), width=2, fill=(60, 60, 60, 140))
    img.alpha_composite(icon("shield", 32), (x0 - 54, y0 + 5))
    # xp bar
    d.rectangle([x0, y0 - 14, x0 + 9 * s, y0 - 8], fill=(20, 20, 20, 220))
    d.rectangle([x0, y0 - 14, x0 + int(9 * s * 0.62), y0 - 8], fill=(120, 230, 60, 255))
    shadow_text(d, (W // 2 - 8, y0 - 34), "37", font(16), (130, 255, 80))
    hp = st.get("hp", 20)
    for i in range(10):
        v = hp - i * 2
        kind = "full" if v >= 2 else ("half" if v >= 1 else "empty")
        heart(d, x0 + i * 19, y0 - 42, 18, kind)
    for i in range(int(st.get("gold", 0)) // 2):
        heart(d, x0 + i * 19, y0 - 62, 18, "gold")
    for i in range(10):
        d.rectangle([x0 + 9 * s - (i + 1) * 19 + 3, y0 - 38, x0 + 9 * s - i * 19 - 3, y0 - 28],
                    fill=(170, 110, 50, 255), outline=(60, 30, 10, 255))
    # crosshair + attack cooldown
    cx, cy = W // 2, H // 2
    d.rectangle([cx - 1, cy - 10, cx + 1, cy + 10], fill=(255, 255, 255, 220))
    d.rectangle([cx - 10, cy - 1, cx + 10, cy + 1], fill=(255, 255, 255, 220))
    cd = st.get("cooldown", 1.0)
    if cd < 1.0:
        d.rectangle([cx - 16, cy + 18, cx + 16, cy + 24], fill=(40, 40, 40, 200))
        d.rectangle([cx - 16, cy + 18, cx - 16 + int(32 * cd), cy + 24], fill=(230, 230, 230, 255))


# ============================================================================ cheat overlay

MODULES = ["Полёт", "ESP", "KillAura", "Аимбот", "Криты", "АвтоОружие", "АвтоТотем", "MassTPA"]


def modules_on(gt):
    """Which modules are enabled at global time gt (enabled one by one during S2)."""
    t0 = T.START["S2"]
    if gt < t0 + 3.0:
        return []
    clicks = [3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.5]
    return [m for m, c in zip(MODULES, clicks) if gt >= t0 + c]


def draw_cheat(img, d, gt, t, sid, boxes, extra):
    mods = modules_on(gt)
    if not mods:
        return
    # watermark
    d.rectangle([10, 10, 250, 44], fill=(0, 0, 0, 150))
    d.rectangle([10, 10, 14, 44], fill=rainbow(0, t) + (255,))
    shadow_text(d, (22, 12), "БРО-КЛИЕНТ", font(32), rainbow(2, t))
    shadow_text(d, (22, 48), "v6.6 | FPS 144 | пинг 12", font(16), (200, 200, 200))
    # array list (longest first)
    f = font(32)
    items = sorted(mods, key=lambda m: -tw(d, m, f))
    for i, m in enumerate(items):
        wdt = tw(d, m, f)
        y = 10 + i * 34
        d.rectangle([W - wdt - 22, y, W - 10, y + 34], fill=(0, 0, 0, 140))
        d.rectangle([W - 14, y, W - 10, y + 34], fill=rainbow(i, t) + (255,))
        shadow_text(d, (W - wdt - 16, y + 1), m, f, rainbow(i, t))
    # ESP + tracers
    if "ESP" in mods:
        for b in boxes:
            if b["name"] == "brohacker":
                continue
            x0, y0, x1, y1 = b["x0"], b["y0"], b["x1"], b["y1"]
            if x1 < 0 or x0 > W or y1 < 0 or y0 > H or (x1 - x0) > W * 1.5:
                continue
            col = (255, 60, 60) if b["depth"] < 6 else ((255, 200, 40) if b["depth"] < 14 else (60, 255, 120))
            d.rectangle([x0, y0, x1, y1], outline=(0, 0, 0, 200), width=4)
            d.rectangle([x0, y0, x1, y1], outline=col + (255,), width=2)
            hp = extra.get("hp_of", {}).get(b["name"], 20)
            d.rectangle([x0 - 7, y0, x0 - 4, y1], fill=(0, 0, 0, 200))
            hh = (y1 - y0) * hp / 20
            d.rectangle([x0 - 7, y1 - hh, x0 - 4, y1], fill=(60, 255, 60, 255))
            lbl = f"{b['name']} {b['depth']:.0f}м"
            fs = font(16)
            lw = tw(d, lbl, fs)
            d.rectangle([(x0 + x1) / 2 - lw / 2 - 3, y1 + 2, (x0 + x1) / 2 + lw / 2 + 3, y1 + 20], fill=(0, 0, 0, 160))
            d.text(((x0 + x1) / 2 - lw / 2, y1 + 3), lbl, font=fs, fill=col + (255,))
            if extra.get("tracers", True):
                d.line([(W / 2, H / 2), ((x0 + x1) / 2, (y0 + y1) / 2)], fill=col + (150,), width=2)
    # target hud (duel)
    tg = extra.get("target")
    if tg:
        x, y = W // 2 + 40, H // 2 + 40
        d.rectangle([x, y, x + 250, y + 86], fill=(0, 0, 0, 170), outline=rainbow(1, t) + (255,), width=2)
        shadow_text(d, (x + 10, y + 6), tg["name"], font(32), (255, 255, 255))
        hp = max(0.0, tg["hp"])
        d.rectangle([x + 10, y + 44, x + 240, y + 54], fill=(60, 0, 0, 255))
        d.rectangle([x + 10, y + 44, x + 10 + int(230 * hp / 20), y + 54], fill=(240, 60, 60, 255))
        shadow_text(d, (x + 10, y + 60), f"{hp / 2:.1f} ❤  броня 20  {tg.get('dist', 3.1):.1f} бл  " +
                    ("щит ↑" if tg.get("shield") else ""), font(16), (230, 230, 230))
    if extra.get("combo"):
        c = extra["combo"]
        pop = extra.get("combo_pop", 0.0)
        f = font(64 if pop > 0.5 else 48)
        outline_text(d, (W // 2, int(H * 0.36)), f"КОМБО ×{c}", f, rainbow(3, t), stroke=4, anchor="mm")
        if extra.get("cps"):
            outline_text(d, (W // 2, int(H * 0.36) + 44), "CPS 20 · крит 100%", font(32), (255, 255, 255), stroke=3,
                         anchor="mm")
    if extra.get("coords"):
        shadow_text(d, (10, 70), extra["coords"], font(16), (255, 255, 255))


def draw_masstpa_progress(img, d, t, sent, total, accepted=None, t_acc=None):
    x, y, w_, h_ = 60, int(H * 0.40), W - 120, 92
    d.rectangle([x, y, x + w_, y + h_], fill=(10, 0, 20, 200), outline=(255, 85, 255, 255), width=3)
    outline_text(d, (x + 16, y + 10), "MassTPA", font(32), (255, 85, 255), stroke=2)
    lbl = f"Отправка {sent}/{total}"
    shadow_text(d, (x + w_ - tw(d, lbl, font(32)) - 16, y + 10), lbl, font(32), (255, 255, 255))
    d.rectangle([x + 16, y + 56, x + w_ - 16, y + 74], fill=(40, 0, 60, 255))
    d.rectangle([x + 16, y + 56, x + 16 + int((w_ - 32) * sent / total), y + 74], fill=(200, 80, 255, 255))
    if accepted is not None:
        a = min(1.0, (t - t_acc) / 0.25)
        f = font(64)
        outline_text(d, (W // 2, y + h_ + 60), f"Принято: {accepted}", f, (85, 255, 85), a=int(255 * a), stroke=4,
                     anchor="mm")


# ============================================================================ cheat menu (click GUI)

GUI = {
    # shot: list of (t, action, value)
    "S2": [(2.0, "open", "list"), (3.0, "click", 0), (4.0, "click", 1), (5.0, "click", 2), (6.0, "click", 3),
           (7.0, "click", 4), (8.0, "click", 5), (9.0, "click", 6), (10.5, "click", 7), (11.6, "open", "tpa"),
           (16.0, "hover", "cooldown"), (19.5, "hover", "delay"), (22.5, "hover", "targets"), (28.6, "close", None)],
    "S4a": [(0.3, "open", "tpa"), (1.0, "type", "Раздаю алмазы! Примите тп)"), (5.2, "send", 47),
            (7.4, "close", None)],
    "S4c": [(0.2, "open", "tpa"), (0.4, "settext", ""), (0.6, "type", "Розыгрыш элитр! Первые пять, кто примет тп"),
            (3.8, "send", 47), (4.6, "accepted", 5), (5.6, "close", None)],
    "S5b": [(0.5, "open", "tpa"), (2.0, "mode", "here"), (2.6, "settext", ""),
            (2.7, "type", "Админ: срочный сбор, примите"), (5.4, "send", 47), (7.0, "accepted", 9)],
    "S7h": [(0.6, "open", "tpa"), (0.8, "mode", "here"), (0.9, "settext", ""), (1.0, "type", "Победителю — приз"),
            (2.8, "send", 47), (3.4, "accepted", 14)],
    "S8b": [(0.3, "open", "tpa"), (1.5, "slide", 10), (4.4, "send", 470)],
}
TYPE_CPS = 14


def gui_state(sid, t):
    st = {"panel": None, "on": set(), "mode": "them", "text": "", "repeat": 1, "hover": None, "cursor": None,
          "send": None, "accepted": None, "t_acc": None, "clicks": []}
    prev_text = {"S4c": "Раздаю алмазы! Примите тп)", "S5b": "Розыгрыш элитр! Первые пять, кто примет тп",
                 "S7h": "Админ: срочный сбор, примите", "S8b": "Победителю — приз"}.get(sid, "")
    st["text"] = prev_text
    if sid != "S2":
        st["on"] = set(range(8))
    if sid in ("S7h", "S8b"):
        st["mode"] = "here"
    for (tt, act, val) in GUI.get(sid, []):
        if t < tt:
            break
        if act == "open":
            st["panel"] = val
        elif act == "close":
            st["panel"] = None
        elif act == "click":
            st["on"].add(val)
            st["cursor"] = ("mod", val)
        elif act == "hover":
            st["hover"] = val
        elif act == "mode":
            st["mode"] = val
        elif act == "settext":
            st["text"] = val
        elif act == "type":
            n = int((t - tt) * TYPE_CPS)
            st["text"] = val[:n]
            st["typing"] = n < len(val)
        elif act == "slide":
            st["repeat"] = max(1, min(val, 1 + int((t - tt) / 0.2)))
        elif act == "send":
            st["send"] = (tt, val)
        elif act == "accepted":
            st["accepted"] = val
            st["t_acc"] = tt
    if st["panel"] == "list" and sid == "S2":
        nxt = [(tt, v) for tt, a, v in GUI["S2"] if a == "click" and tt > t]
        if nxt:
            st["cursor"] = ("mod", nxt[0][1])
    return st


def draw_gui(img, d, sid, t, st):
    if st["panel"] is None:
        return
    # dim the world
    d.rectangle([0, 0, W, H], fill=(0, 0, 0, 90))
    f32, f16 = font(32), font(16)
    if st["panel"] == "list":
        x, y, w_ = 150, 260, 420
        d.rectangle([x, y, x + w_, y + 44], fill=(70, 230, 100, 255))
        shadow_text(d, (x + 12, y + 6), "БРО-КЛИЕНТ · Модули", f32, (10, 20, 10), sh=0)
        for i, m in enumerate(MODULES):
            yy = y + 44 + i * 48
            on = i in st["on"]
            d.rectangle([x, yy, x + w_, yy + 48], fill=(20, 60, 30, 235) if on else (16, 18, 20, 230))
            d.text((x + 16, yy + 8), m, font=f32, fill=(120, 255, 150, 255) if on else (220, 220, 220, 255))
            d.text((x + w_ - 100, yy + 8), "ВКЛ" if on else "ВЫКЛ", font=f32,
                   fill=(85, 255, 85, 255) if on else (255, 85, 85, 255))
        cur = st.get("cursor")
        if cur:
            i = cur[1]
            cx, cy = x + w_ - 140, y + 44 + i * 48 + 26
            draw_cursor(d, cx, cy)
        return
    # MassTPA settings
    x, y, w_ = 60, 300, W - 120
    rows = 7
    d.rectangle([x, y, x + w_, y + 56 + rows * 62 + 20], fill=(12, 6, 20, 240), outline=(255, 85, 255, 255), width=3)
    d.rectangle([x, y, x + w_, y + 56], fill=(200, 70, 255, 255))
    shadow_text(d, (x + 14, y + 12), "MassTPA · настройки", f32, (20, 0, 30), sh=0)
    yy = y + 70

    def row(label, value, hl=False, col=(255, 255, 255)):
        nonlocal yy
        if hl:
            d.rectangle([x + 6, yy - 6, x + w_ - 6, yy + 50], fill=(80, 30, 110, 255))
        d.text((x + 18, yy), label, font=f32, fill=(200, 190, 220, 255))
        d.text((x + 18, yy + 30), value, font=f16 if len(value) > 34 else f32, fill=col + (255,)) if False else None
        yy_val = yy
        vw = tw(d, value, f32)
        d.text((x + w_ - vw - 18, yy_val), value, font=f32, fill=col + (255,))
        yy += 62

    mode_here = st["mode"] == "here"
    row("Режим", "КО МНЕ (/tpahere)" if mode_here else "К НИМ (/tpa)", hl=(sid in ("S5b",) and 2.0 <= t < 2.6),
        col=(255, 200, 80) if mode_here else (120, 230, 255))
    row("Цели", "все онлайн (47)", hl=st["hover"] == "targets")
    row("Обход кулдауна", "ВКЛ", hl=st["hover"] == "cooldown", col=(85, 255, 85))
    row("Задержка", "0 мс", hl=st["hover"] == "delay", col=(85, 255, 85))
    # repeat slider
    d.text((x + 18, yy), "Повторы", font=f32, fill=(200, 190, 220, 255))
    sx0, sx1 = x + 250, x + w_ - 110
    d.rectangle([sx0, yy + 14, sx1, yy + 22], fill=(60, 40, 80, 255))
    kx = sx0 + (sx1 - sx0) * (st["repeat"] - 1) / 9
    d.rectangle([sx0, yy + 14, kx, yy + 22], fill=(255, 85, 255, 255))
    d.rectangle([kx - 8, yy + 4, kx + 8, yy + 32], fill=(255, 255, 255, 255))
    d.text((x + w_ - 90, yy), f"×{st['repeat']}", font=f32, fill=(255, 255, 255, 255))
    if sid == "S8b" and 1.2 < t < 4.0:
        draw_cursor(d, kx + 4, yy + 20)
    yy += 62
    # bait text field
    d.text((x + 18, yy), "Приманка", font=f32, fill=(200, 190, 220, 255))
    yy += 36
    d.rectangle([x + 18, yy, x + w_ - 18, yy + 44], fill=(0, 0, 0, 255), outline=(160, 120, 200, 255), width=2)
    txt = st["text"]
    fnt = f32 if tw(d, txt, f32) < w_ - 70 else f16
    d.text((x + 28, yy + (6 if fnt is f32 else 14)), txt, font=fnt, fill=(255, 255, 255, 255))
    if int(t * 3) % 2 == 0 or st.get("typing"):
        cx = x + 30 + tw(d, txt, fnt)
        d.rectangle([cx, yy + 8, cx + 3, yy + 36], fill=(255, 255, 255, 255))
    yy += 64
    # send button
    bx0, bx1 = x + w_ // 2 - 130, x + w_ // 2 + 130
    pressed = st["send"] and 0 <= t - st["send"][0] < 0.25
    d.rectangle([bx0, yy, bx1, yy + 50], fill=(140, 40, 200, 255) if pressed else (200, 70, 255, 255))
    lbl = "ОТПРАВИТЬ"
    d.text(((bx0 + bx1) / 2 - tw(d, lbl, f32) / 2, yy + 9), lbl, font=f32, fill=(255, 255, 255, 255))
    if st["send"] and -0.6 < t - st["send"][0] < 0.4:
        draw_cursor(d, (bx0 + bx1) / 2 + 40, yy + 30)
    if sid == "S5b" and 1.5 < t < 2.3:
        draw_cursor(d, x + w_ - 120, y + 95)


def draw_cursor(d, x, y):
    pts = [(x, y), (x, y + 26), (x + 7, y + 20), (x + 12, y + 31), (x + 17, y + 29), (x + 12, y + 18), (x + 21, y + 18)]
    d.polygon(pts, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))


# ============================================================================ chat + subtitles + nametags

CHAT_G = sorted(((T.g(s, t), seg) for s, t, seg in T.CHAT), key=lambda x: x[0])
RESETS = sorted(T.START[s] for s in T.CHAT_RESET)


def draw_chat(img, gt, n_lines=6):
    last_reset = max([r for r in RESETS if r <= gt + 1e-6], default=0.0)
    lines = [(t0, seg) for t0, seg in CHAT_G if last_reset - 1e-6 <= t0 <= gt]
    if not lines:
        return
    lines = lines[-n_lines:]
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    fs = font(16)
    f = ImageFont.truetype(FONT, 22)
    lh = 27
    bottom = int(H * 0.86) - 120
    for i, (t0, seg) in enumerate(reversed(lines)):
        a = min(1.0, (gt - t0) * 8 + 0.2)
        y = bottom - (i + 1) * lh
        d.rectangle([12, y, int(W * 0.80), y + lh], fill=(0, 0, 0, int(95 * a)))
        x = 18
        for s, col in seg:
            shadow_text(d, (x, y + 2), s, f, col, int(255 * a))
            x += tw(d, s, f)
    img.alpha_composite(ov)


def clean(text):
    return re.sub(r"\[[^\]]*\]\s*", "", text).strip()


def subtitles(voice):
    out = []
    for vid, shot, t in T.VOICE:
        if vid not in voice:
            continue
        v = voice[vid]
        out.append((T.g(shot, t), T.g(shot, t) + v["duration"] + 0.3, v["who"], clean(v["text"])))
    return out


SUB_COL = {"narrator": (255, 255, 255), "brohacker": (255, 85, 255), "pixel_masha": (255, 160, 200),
           "dimon_pro": (120, 190, 255), "lavaKing": (255, 170, 60), "kotik_777": (140, 230, 120),
           "snowbunny": (170, 230, 255)}


def wrap_text(d, text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if tw(d, trial, f) > maxw and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def draw_subs(img, d, gt, subs):
    act = [s for s in subs if s[0] <= gt <= s[1]]
    y = int(H * 0.585)
    for t0, t1, who, text in act[-2:]:
        f = font(32)
        prefix = "" if who == "narrator" else f"{who}: "
        lines = wrap_text(d, prefix + text, f, W - 70)
        a = int(255 * min(1.0, (gt - t0) * 6, (t1 - gt) * 6))
        for ln in lines:
            outline_text(d, (W // 2, y), ln, f, SUB_COL.get(who, (255, 255, 255)), a=a, stroke=3, anchor="mm")
            y += 36
        y += 8


def draw_tags(img, d, tags, skip=("brohacker",), fp=False):
    for tg in sorted(tags, key=lambda q: -q["depth"]):
        if fp and tg["name"] in skip:
            continue
        fs = int(max(14, min(26, tg["size"] * 0.7)))
        f = ImageFont.truetype(FONT, fs)
        s = tg["name"]
        wdt = tw(d, s, f)
        x, y = tg["x"] - wdt / 2, tg["y"] - fs * 1.5
        if x > W or x + wdt < 0 or y > H or y + fs < 0:
            continue
        pad = max(3, fs // 5)
        d.rectangle([x - pad, y - pad // 2, x + wdt + pad, y + fs + pad], fill=(0, 0, 0, 100))
        d.text((x, y - 1), s, font=f, fill=((255, 85, 255) if s == "brohacker" else (255, 255, 255)) + (235,))


# ============================================================================ per-shot extras

def duel_state(sid, t):
    """target hp, combo, slot, cooldown, shield for the duel shots"""
    ex = {}
    hp = 20.0
    combo = 0
    slot = 0
    cooldown = 1.0
    shield = False
    last_swing = -9
    pop = 0.0
    if sid == "S7d":
        shield = (0.6 <= t < 1.9) or (7.0 <= t < 7.6)
        for kind, tt in T.HITS["S7d"]:
            if kind == "axe" and tt - 0.25 <= t < tt + 0.35:
                slot = 1
            if t >= tt:
                last_swing = tt
                if kind == "crit":
                    hp -= 1.5
                    combo += 1
                    pop = max(0.0, 1 - (t - tt) / 0.3)
        ex["target"] = {"name": "lavaKing", "hp": hp, "shield": shield, "dist": 3.0 + 0.4 * math.sin(t)}
        ex["combo"] = combo
        ex["combo_pop"] = pop
        ex["cps"] = combo > 0
    elif sid == "S7g":
        hp = 5.0
        combo = 10
        for tt in (1.0, 1.7):
            if t >= tt:
                last_swing = tt
                hp -= 2.5
                combo += 1
                pop = max(0.0, 1 - (t - tt) / 0.3)
        if t < 2.8:
            ex["target"] = {"name": "lavaKing", "hp": hp, "dist": 1.8}
        ex["combo"] = combo
        ex["combo_pop"] = pop
    cooldown = min(1.0, (t - last_swing) / 0.625)
    return ex, {"slot": slot, "cooldown": cooldown}


def shot_extras(sid, t, gt):
    ex, hud = {}, {"slot": 0, "hp": 20, "cooldown": 1.0}
    if sid in ("S7d", "S7g"):
        e2, h2 = duel_state(sid, t)
        ex.update(e2)
        hud.update(h2)
    if sid in ("S3f",):
        hud["cooldown"] = min(1.0, max(0.0, (t - 2.5) / 0.625)) if t >= 2.5 else 1.0
    if sid == "S7f":
        hud["hp"] = 1 if t < 3.35 else 2
        hud["gold"] = 0 if t < 3.35 else 8
    if sid in ("S5b",):
        ex["coords"] = "XYZ: 3000 / 200 / 0   ·   3000 блоков от спавна"
    ex["tracers"] = sid not in ("S2",)
    return ex, hud


# ============================================================================ frame assembly

def vignette_mask():
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / math.sqrt(2)
    return (1 - 0.32 * np.clip(r - 0.35, 0, 1) ** 1.5)[..., None].astype(np.float32)


VIG = None


def base_frame(shots_dir, sid, f, n):
    kind = T.KIND[sid]
    if kind == "2d":
        return Image.new("RGBA", (W, H), (0, 0, 0, 255)), None
    src_sid, src_f = sid, f
    if sid == "S8d":
        src_sid, src_f = "S8c", int(T.DUR["S8c"] * FPS)
    if sid == "S8c":
        # lag: from 7.5 s the image stutters, then freezes
        t = (f - 1) / FPS
        if t > 7.5:
            hold = 3 if t < 9 else (6 if t < 10.5 else 12)
            src_f = int((7.5 * FPS) + ((f - int(7.5 * FPS)) // hold) * hold * 0.4)
    path = os.path.join(shots_dir, src_sid, f"f{src_f:04d}.png")
    if not os.path.exists(path):
        img = Image.new("RGBA", (W, H), (30, 30, 40, 255))
        ImageDraw.Draw(img).text((40, H // 2), f"{sid} f{f} (нет кадра)", font=font(32), fill=(255, 80, 80, 255))
        return img, None
    img = Image.open(path).convert("RGB")
    if img.size != (W, H):
        img = img.resize((W, H), Image.BILINEAR)
    a = np.asarray(img).astype(np.float32)
    global VIG
    if VIG is None:
        VIG = vignette_mask()
    a = np.clip(a * VIG * np.array([1.02, 1.0, 0.97], np.float32), 0, 255).astype(np.uint8)
    meta = load_meta(shots_dir, src_sid)
    m = meta["f"].get(str(src_f)) if meta else None
    return Image.fromarray(a).convert("RGBA"), m


_meta = {}


def load_meta(shots_dir, sid):
    if sid not in _meta:
        p = os.path.join(shots_dir, sid, "meta.json")
        _meta[sid] = json.load(open(p)) if os.path.exists(p) else None
    return _meta[sid]


def glitch(img, strength, seed):
    r = random.Random(seed)
    a = np.asarray(img).copy()
    for _ in range(int(6 * strength)):
        y0 = r.randint(0, H - 40)
        hgt = r.randint(8, 60)
        dx = r.randint(-40, 40)
        a[y0:y0 + hgt] = np.roll(a[y0:y0 + hgt], dx, axis=1)
    if strength > 0.5:
        a[..., 0] = np.roll(a[..., 0], int(6 * strength), axis=1)
    return Image.fromarray(a)


def prolog(img, d, t):
    n = 0 if t < 1.0 else (1 if t < 2.2 else (2 if t < 3.0 else min(60, int(3 + (t - 3.0) ** 2 * 6))))
    f = ImageFont.truetype(FONT, 22)
    for i in range(n):
        y = H - 200 - (n - 1 - i) * 27
        if y < -30:
            continue
        x = 18
        for s, col in T.TPA:
            shadow_text(d, (x, y), s, f, col)
            x += tw(d, s, f)
    if t > 6.5:
        a = min(200, int((t - 6.5) * 120))
        d.rectangle([0, 0, W, H], fill=(120, 30, 180, a))
    if t > 12.0:
        outline_text(d, (W // 2, int(H * 0.45)), "СЕРВЕР БЕЗ", font(64), (255, 255, 255), stroke=4, anchor="mm")
        outline_text(d, (W // 2, int(H * 0.45) + 70), "АНТИЧИТА", font(64), (255, 85, 255), stroke=4, anchor="mm")


def finale(img, d, t):
    if t < 1.0:
        return
    f = ImageFont.truetype(FONT, 26)
    lines = [T.TPA, T.ACCEPT_HINT]
    for i, seg in enumerate(lines):
        if t < 1.0 + i * 1.2:
            continue
        x = 20
        y = H - 300 + i * 32
        for s, col in seg:
            shadow_text(d, (x, y), s, f, col)
            x += tw(d, s, f)
    if t > 3.5:
        d.rectangle([12, H - 220, W - 12, H - 180], fill=(0, 0, 0, 180), outline=(120, 120, 120, 255))
        txt = "/tpaccept"[:max(0, int((t - 4.2) * 4))] if t > 4.2 else ""
        d.text((22, H - 214), txt, font=font(32), fill=(255, 255, 255, 255))
        if int(t * 2.5) % 2 == 0:
            cx = 24 + tw(d, txt, font(32))
            d.rectangle([cx, H - 212, cx + 14, H - 188], fill=(255, 255, 255, 255))


def compose_frame(shots_dir, sid, f, n, subs):
    t = (f - 1) / FPS
    gt = T.START[sid] + t
    img, m = base_frame(shots_dir, sid, f, n)
    d = ImageDraw.Draw(img)
    fp = sid in T.FP_SHOTS or (sid in T.FP_LATE and t >= T.FP_LATE[sid])
    if m:
        draw_tags(img, d, m["tags"], fp=fp)
    ex, hud = shot_extras(sid, t, gt)
    if fp:
        draw_cheat(img, d, gt, t, sid, m["boxes"] if m else [], ex)
        draw_hud(img, d, hud)
    if sid == "S7f" and 3.35 <= t < 5.0:
        k = (t - 3.35) / 1.65
        size = int(200 + 260 * min(1.0, k * 3))
        ic = icon("totem", 16).resize((size, size), Image.NEAREST)
        a = int(255 * (1 - max(0.0, k - 0.5) * 2))
        ic.putalpha(ic.getchannel("A").point(lambda v: min(v, a)))
        img.alpha_composite(ic, (W // 2 - size // 2, int(H * 0.45) - size // 2))
        outline_text(d, (W // 2, int(H * 0.27)), "Тотем бессмертия использован", font(32), (250, 214, 70), stroke=3,
                     anchor="mm")
    if sid == "S3b" and t >= 2.2:
        sent = min(47, int((t - 2.2) / 1.4 * 47))
        draw_masstpa_progress(img, d, t, sent, 47)
    st = gui_state(sid, t) if sid in GUI else None
    if st:
        draw_gui(img, d, sid, t, st)
        if st["send"] and t >= st["send"][0]:
            tt, total = st["send"]
            sent = min(total, int((t - tt) / 1.3 * total) + 1)
            if t - tt < 2.6 or st["accepted"]:
                draw_masstpa_progress(img, d, t, sent, total, st["accepted"], st["t_acc"])
    if sid == "S7c":
        k = int(t / 0.9)
        txt = ["3", "2", "1", "БОЙ!"][min(3, k)]
        sc = 1 + max(0.0, 0.3 - (t - k * 0.9)) * 2
        outline_text(d, (W // 2, int(H * 0.42)), txt, font(int(64 * min(sc, 1.6) // 16 * 16) or 64),
                     (255, 85, 85) if txt == "БОЙ!" else (255, 255, 255), stroke=5, anchor="mm")
    if sid == "S7e":
        outline_text(d, (24, 24), "▶ ПОВТОР ×0.25", font(32), (255, 80, 80), stroke=3)
        if int(t * 2) % 2 == 0:
            d.ellipse([W - 50, 30, W - 26, 54], fill=(255, 40, 40, 255))
    if sid in ("S8c", "S8d"):
        tps = 20.0 if t < 6.0 else max(0.4, 20 - (t - 6.0) * 6) if sid == "S8c" else 0.4
        col = (85, 255, 85) if tps > 15 else ((255, 200, 60) if tps > 5 else (255, 60, 60))
        outline_text(d, (W - 20, 30), f"TPS {tps:.1f}", font(32), col, stroke=3, anchor="ra")
    if T.KIND[sid] == "2d" and sid == "P1":
        prolog(img, d, t)
    if sid == "S9b":
        finale(img, d, t)
    if sid in T.CHAT_SHOWN:
        draw_chat(img, gt)
    if sid == "S8c" and t > 7.5:
        img = glitch(img, min(1.0, (t - 7.5) / 3), f).convert("RGBA")
        d = ImageDraw.Draw(img)
    if sid == "S8d":
        img = glitch(img, 1.0 if t < 3 else 0.6, f // 3).convert("RGBA")
        d = ImageDraw.Draw(img)
        if t > 5.0:
            d.rectangle([0, 0, W, H], fill=(0, 0, 0, min(255, int((t - 5.0) * 120))))
    draw_subs(img, d, gt, subs)
    # fades
    if sid == "S1a" and t < 0.6:
        d.rectangle([0, 0, W, H], fill=(0, 0, 0, int(255 * (1 - t / 0.6))))
    if sid == "S9b" and t > 8.5:
        d.rectangle([0, 0, W, H], fill=(0, 0, 0, min(255, int((t - 8.5) * 200))))
    return img.convert("RGB")


# ============================================================================ audio

SR = 44100


def env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(attack, 1e-4)) * np.exp(-t / decay)


def tone(freq, dur, decay, harm=(1.0,), attack=0.004):
    n = int(SR * dur)
    t = np.arange(n) / SR
    s = sum(a * np.sin(2 * math.pi * freq * (k + 1) * t) for k, a in enumerate(harm))
    return (s * env(n, attack, decay)).astype(np.float32)


def noise(n, smooth=1, seed=0):
    x = np.random.default_rng(seed).normal(0, 1, n)
    if smooth > 1:
        x = np.convolve(x, np.ones(smooth) / smooth, mode="same")
    return x.astype(np.float32)


def sweep_tone(f0, f1, dur, decay):
    n = int(SR * dur)
    t = np.arange(n) / SR
    fr = f0 + (f1 - f0) * t / dur
    return (np.sin(2 * math.pi * np.cumsum(fr) / SR) * env(n, 0.003, decay)).astype(np.float32)


def sfx(name, seed=0):
    if name == "pling":
        return 0.5 * (tone(1318.5, 0.45, 0.12, (1, 0, 0.25)) + 0.4 * tone(1975.5, 0.45, 0.1))
    if name == "chat":
        return 0.3 * tone(880, 0.08, 0.025)
    if name == "teleport":
        n = int(SR * 0.5)
        s = sweep_tone(300, 1400, 0.5, 0.2) * 0.5 + noise(n, 4, seed) * env(n, 0.01, 0.12) * 0.4
        return s + 0.25 * tone(1760, 0.5, 0.15)
    if name == "crit":
        n = int(SR * 0.25)
        thump = sweep_tone(180, 60, 0.25, 0.06)
        crack = noise(n, 1, seed) * env(n, 0.001, 0.02)
        return 0.9 * thump + 0.5 * crack + 0.2 * tone(2400, 0.2, 0.05)
    if name == "hurt":
        return 0.8 * sweep_tone(220, 110, 0.3, 0.08)
    if name == "sweep":
        n = int(SR * 0.35)
        nz = noise(n, 3, seed)
        e = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
        return (nz * e * 0.6 + sweep_tone(900, 300, 0.35, 0.15) * 0.3).astype(np.float32)
    if name == "death":
        return 0.7 * sweep_tone(330, 90, 0.45, 0.15) + 0.4 * sweep_tone(160, 50, 0.4, 0.12)
    if name == "poof":
        n = int(SR * 0.35)
        return noise(n, 8, seed) * env(n, 0.005, 0.08) * 0.6
    if name == "splash":
        n = int(SR * 0.6)
        return noise(n, 2, seed) * env(n, 0.003, 0.18) * 0.7 + noise(n, 30, seed + 1) * env(n, 0.01, 0.3) * 0.6
    if name == "totem":
        out = np.zeros(int(SR * 1.4), np.float32)
        for i, fr in enumerate([523.25, 659.25, 783.99, 1046.5, 1318.5, 1568.0]):
            s = tone(fr, 0.8, 0.3, (1, 0.3))
            j = int(i * 0.09 * SR)
            out[j:j + len(s)] += s * 0.4
        return out
    if name == "shield":
        out = np.zeros(int(SR * 0.6), np.float32)
        for fr, a in ((420, 0.6), (1130, 0.4), (2310, 0.3), (3570, 0.2)):
            out += tone(fr, 0.6, 0.12) * a
        n = int(SR * 0.05)
        out[:n] += noise(n, 1, seed) * 0.8
        return out
    if name == "jump":
        return 0.3 * sweep_tone(140, 90, 0.12, 0.04)
    if name == "swoosh":
        n = int(SR * 0.9)
        nz = noise(n, 5, seed)
        e = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
        return nz * e * 0.5
    if name == "beep":
        return 0.5 * tone(880, 0.25, 0.1, (1, 0.2))
    if name == "go":
        return 0.6 * tone(1320, 0.6, 0.25, (1, 0.3, 0.1))
    if name == "glitch":
        n = int(SR * 0.7)
        sq = np.sign(np.sin(2 * math.pi * 55 * np.arange(n) / SR)) * 0.4
        nz = noise(n, 1, seed)
        hold = (np.arange(n) // 900) % 2
        return ((sq + nz * 0.5) * hold * 0.5).astype(np.float32)
    if name == "click":
        n = int(SR * 0.03)
        return noise(n, 1, seed) * env(n, 0.0005, 0.006) * 0.6 + tone(2000, 0.03, 0.01) * 0.3
    if name == "type":
        n = int(SR * 0.025)
        return noise(n, 2, seed) * env(n, 0.0005, 0.005) * 0.35
    raise ValueError(name)


def music(total):
    """Simple generated score: calm pad -> tense pulse -> duel drive -> breakdown -> quiet."""
    n = int(SR * total) + SR
    out = np.zeros(n, np.float32)
    bpm = 100
    beat = 60 / bpm
    t_all = np.arange(n) / SR

    def chord_pad(t0, t1, freqs, amp):
        i0, i1 = int(t0 * SR), min(n, int(t1 * SR))
        t = t_all[i0:i1] - t0
        e = np.minimum(1, t / 1.5) * np.minimum(1, (t1 - t0 - t) / 1.5)
        s = sum(np.sin(2 * math.pi * f * t) + 0.3 * np.sin(2 * math.pi * f * 2.001 * t) for f in freqs)
        out[i0:i1] += (s * e * amp / len(freqs)).astype(np.float32)

    A, F_, C, G, E = 110.0, 87.31, 130.81, 98.0, 82.41
    prog_calm = [(A, A * 1.189, A * 1.498), (F_, F_ * 1.26, F_ * 1.498), (C, C * 1.26, C * 1.498),
                 (G, G * 1.26, G * 1.498)]
    prog_tense = [(A, A * 1.189, A * 1.498), (A, A * 1.189, A * 1.414), (F_, F_ * 1.26, F_ * 1.498),
                  (E, E * 1.26, E * 1.414)]
    sec_calm = (T.START["S1a"], T.START["S2"])
    sec_tense = (T.START["S2"], T.START["S7c"])
    sec_duel = (T.START["S7c"] + 2.9, T.START["S7j"])
    sec_after = (T.START["S7j"], T.START["S8c"] + 7.5)
    sec_end = (T.START["S9a"], T.START["S9b"] + 5.0)
    bar = 4 * beat
    for sec, prog, amp in ((sec_calm, prog_calm, 0.10), (sec_tense, prog_tense, 0.08), (sec_duel, prog_tense, 0.07),
                           (sec_after, prog_tense, 0.07), (sec_end, prog_tense, 0.06)):
        t = sec[0]
        i = 0
        while t < sec[1]:
            t1 = min(sec[1], t + 2 * bar)
            chord_pad(t, t1 + 1.0, prog[i % 4], amp)
            t += 2 * bar
            i += 1
    # pulse: bass 8ths + kick (tense and duel), hats in the duel
    kick = sweep_tone(120, 40, 0.25, 0.08)
    hat = (noise(int(SR * 0.04), 1, 3) * env(int(SR * 0.04), 0.001, 0.01)).astype(np.float32)
    snare = (noise(int(SR * 0.15), 2, 4) * env(int(SR * 0.15), 0.001, 0.05) * 0.8).astype(np.float32)

    def place(sig, t, gain):
        i = int(t * SR)
        if i >= n:
            return
        s = sig[: n - i]
        out[i:i + len(s)] += s * gain

    for (t0, t1), intensity in ((sec_tense, 1), (sec_duel, 2), (sec_after, 1)):
        k = 0
        t = t0
        while t < t1:
            root = prog_tense[(int((t - t0) / (2 * bar))) % 4][0] / 2
            place(tone(root, beat / 2 * 0.9, 0.12, (1, 0.5, 0.25)), t, 0.16)
            if k % 2 == 0 and (intensity == 2 or k % 4 == 0):
                place(kick, t, 0.32 if intensity == 2 else 0.22)
            if intensity == 2:
                place(hat, t + beat / 4, 0.12)
                if k % 4 == 2:
                    place(snare, t, 0.18)
            t += beat / 2
            k += 1
    return out


def load_voice(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-af",
                          "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                          "silenceremove=start_periods=1:start_threshold=-45dB,areverse",
                          "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, "<i2").astype(np.float32) / 32768.0


def build_audio(voice, path):
    total = T.TOTAL
    n = int(SR * total) + SR
    fx = np.zeros(n, np.float32)
    vo = np.zeros(n, np.float32)

    def add(buf, t, sig, gain):
        i = int(t * SR)
        if i >= n:
            return
        s = sig[: n - i]
        buf[i:i + len(s)] += s * gain

    for k, (name, shot, t) in enumerate(T.SFX):
        add(fx, T.g(shot, t), sfx(name, k), 0.5)
    # GUI clicks and typing
    for sid, events in GUI.items():
        for tt, act, val in events:
            if act in ("click", "open", "close", "mode", "send", "slide"):
                add(fx, T.g(sid, tt), sfx("click", int(tt * 10)), 0.6)
            if act == "type":
                for i in range(len(val)):
                    add(fx, T.g(sid, tt + i / TYPE_CPS), sfx("type", i), 0.6)
    for vid, shot, t in T.VOICE:
        if vid not in voice:
            continue
        sig = load_voice(voice[vid]["file"])
        sig *= 0.9 / (np.abs(sig).max() + 1e-6)
        add(vo, T.g(shot, t), sig, 1.0 if voice[vid]["who"] == "narrator" else 0.85)
    mu = music(total)[:n]
    # duck music under voices
    envv = np.abs(vo)
    k = int(SR * 0.25)
    envv = np.convolve(envv, np.ones(k) / k, mode="same")
    duck = 1 - 0.65 * np.clip(envv * 6, 0, 1)
    mix = vo + fx * 0.7 + mu * duck
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    pcm = (np.clip(mix[: int(SR * total)], -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ============================================================================ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", required=True)
    ap.add_argument("--voice", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", help="comma separated shots -> writes preview PNGs instead of the video")
    ap.add_argument("--at", default="0.5", help="with --only: comma separated shot-local seconds to preview")
    ap.add_argument("--work", help="frame cache directory")
    args = ap.parse_args()
    voice = json.load(open(args.voice))
    subs = subtitles(voice)
    if args.only:
        os.makedirs(args.out, exist_ok=True)
        for sid in args.only.split(","):
            n = int(T.DUR[sid] * FPS)
            for s in args.at.split(","):
                f = min(n, int(float(s) * FPS) + 1)
                compose_frame(args.shots, sid, f, n, subs).save(os.path.join(args.out, f"{sid}_{f:04d}.jpg"), quality=90)
        return
    work = args.work or tempfile.mkdtemp(prefix="compose_")
    os.makedirs(work, exist_ok=True)
    idx = 0
    for sid, dur, kind in T.SHOTS:
        n = int(round(dur * FPS))
        for f in range(1, n + 1):
            idx += 1
            dst = os.path.join(work, f"o{idx:05d}.jpg")
            if not os.path.exists(dst):
                compose_frame(args.shots, sid, f, n, subs).save(dst, quality=92)
        print(f"[compose] {sid} done ({idx} frames)", flush=True)
    wav = os.path.join(work, "audio.wav")
    build_audio(voice, wav)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(work, "o%05d.jpg"),
                    "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", args.out], check=True)
    print("wrote", args.out)


if __name__ == "__main__":
    main()

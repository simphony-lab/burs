"""Generates narration (Stanislav) and character voice lines with ElevenLabs.

    ELEVENLABS_API_KEY=... python voice.py --out voice [--only N1,N2]

Writes <id>.mp3 per line plus lines.json {id: {file, duration, text, who}} for compose.py.
Files are cached by a hash of voice+text+model, so only changed lines are regenerated.
"""
import argparse
import hashlib
import json
import os
import subprocess
import urllib.request

VOICES = {
    "narrator": "ogi2DyUAKJb7CEdqqvlU",   # Stanislav
    "brohacker": "lsAmGFzUYusakA482527",  # Andrey
    "pixel_masha": "cgSgspJ2msm6clMCkdW9",
    "dimon_pro": "kwajW3Xh5svCeKU5ky2S",
    "lavaKing": "bg9LrEYQkRYwqkxA8VOy",
    "kotik_777": "6A9D8WSMm4rFsg2DWFeE",
    "snowbunny": "FGY2WhTYpPnrIDTdsKH5",
}

NARR = "[serious, deep documentary narration] "

LINES = {
    # narrator
    "N0": ("narrator", NARR + "Одна команда. Сорок семь запросов. Ноль защиты. Это история о том, как один модуль сломал целый сервер."),
    "N1": ("narrator", NARR + "БлокМир. Маленький русский сервер. Сорок семь игроков онлайн. Один админ — и тот третью неделю в отпуске. Античит? А зачем. Здесь все друг друга знают."),
    "N2": ("narrator", NARR + "Знали. До сегодняшнего дня."),
    "N3": ("narrator", NARR + "Обычный тэ-пэ-а — это один запрос, одному игроку, раз в минуту. Масс-тэ-пэ-а — это сорок семь запросов за одну секунду. И каждый, кто нажмёт «принять», — его."),
    "N4": ("narrator", NARR + "Первое правило масс-тэ-пэ-а: из сорока семи кто-нибудь да нажмёт."),
    "N5": ("narrator", NARR + "Второе правило: если люди не нажимают — дай им повод."),
    "N6": ("narrator", NARR + "Третье правило: телепорт работает в обе стороны."),
    "N7": ("narrator", NARR + "Четвёртое правило: рано или поздно нажимают все."),
    "N8": ("narrator", NARR + "Лава Кинг. Лучший пэвэпэшер сервера. Двести побед — ни одного поражения."),
    "N9": ("narrator", NARR + "Идеальный тайминг. Каждый удар — крит. Человек так не может."),
    "N10": ("narrator", NARR + "Даже смерть у него — по подписке."),
    "N11": ("narrator", NARR + "Сервер пережил три вайпа и два переезда. А от одной кнопки — лёг."),
    "N12": ("narrator", NARR + "Античит на БлокМире так и не поставили. Говорят, он до сих пор там. И модуль у него всё ещё включён."),
    # characters
    "masha_hi": ("pixel_masha", "[cheerful] О, новенький! Привет!"),
    "bro_play": ("brohacker", "[mischievously] Ну что, БлокМир… поиграем."),
    "dimon_fly": ("dimon_pro", "[shocked] Он что, летает?!"),
    "kotik_tp": ("kotik_777", "[happy] О, бесплатный тэпэ."),
    "kotik_oi": ("kotik_777", "[scared, quietly] …ой."),
    "bro_hi": ("brohacker", "[calm, creepy] Привет."),
    "dimon_ok": ("dimon_pro", "[hesitant] Ну ладно…"),
    "masha_no": ("pixel_masha", "[shouting] Не принимайте его тэпэ!!"),
    "lava_where": ("lavaKing", "[angry, out of breath] Где мы вообще?!"),
    "bro_swim": ("brohacker", "[laughing] Удачно доплыть."),
    "masha_council": ("pixel_masha", "[whispering, serious] Никто ничего не принимает. Вообще ничего. Поняли?"),
    "snow_oi": ("snowbunny", "[quietly, embarrassed] …ой."),
    "bro_council": ("brohacker", "[smug] Я тоже на совет."),
    "lava_duel": ("lavaKing", "[determined] Без телепортов. Один на один."),
    "snow_unfair": ("snowbunny", "[sad] …это нечестно."),
    "bro_accept": ("brohacker", "[whispers] Принимай."),
}


def tts(key, voice, text, model, path):
    body = json.dumps({
        "text": text,
        "model_id": model,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "style": 0.4, "speed": 1.0},
    }).encode()
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128",
        data=body, headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
    )
    with urllib.request.urlopen(req, timeout=180) as r, open(path, "wb") as fh:
        fh.write(r.read())


def trimmed_duration(path):
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-af",
         "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
         "silenceremove=start_periods=1:start_threshold=-45dB,areverse", "-f", "s16le", "-ac", "1", "-ar", "8000", "-"],
        capture_output=True, check=True).stdout
    return len(out) / 2 / 8000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="eleven_v3")
    ap.add_argument("--only")
    args = ap.parse_args()
    key = os.environ["ELEVENLABS_API_KEY"]
    os.makedirs(args.out, exist_ok=True)
    meta_path = os.path.join(args.out, "lines.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    only = set(args.only.split(",")) if args.only else None
    for lid, (who, text) in LINES.items():
        if only and lid not in only:
            continue
        voice = VOICES[who]
        tag = hashlib.sha1(f"{voice}|{text}|{args.model}".encode()).hexdigest()[:10]
        path = os.path.join(args.out, f"{lid}_{tag}.mp3")
        if not os.path.exists(path):
            tts(key, voice, text, args.model, path)
        d = trimmed_duration(path)
        meta[lid] = {"who": who, "file": os.path.abspath(path), "duration": d, "text": text}
        print(f"{lid:14s} {who:12s} {d:5.2f}s", flush=True)
    with open(meta_path, "w") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

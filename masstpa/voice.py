"""Generates the character voice lines with ElevenLabs (Russian).

    ELEVENLABS_API_KEY=... python voice.py --out voice

Writes one mp3 per line plus lines.json (start frame, file) for overlay.py to mix in.
"""
import argparse
import hashlib
import json
import os
import subprocess
import urllib.request

# frame where the line starts, speaker, ElevenLabs voice id, text (eleven_v3 audio tags in brackets)
LINES = [
    (3, "brohacker", "lsAmGFzUYusakA482527", "[excited] Жмём масс-тэ-пэ-а!"),
    (78, "pixel_masha", "cgSgspJ2msm6clMCkdW9", "[surprised] Э-э... что?!"),
    (128, "lavaKing", "bg9LrEYQkRYwqkxA8VOy", "[confused] Кто такой брохакер?!"),
    (182, "brohacker", "lsAmGFzUYusakA482527", "[laughing] Принимайте!"),
]


def tts(key, voice, text, model, path):
    body = json.dumps({
        "text": text,
        "model_id": model,
        "voice_settings": {"stability": 0.4, "similarity_boost": 0.8, "style": 0.5, "speed": 1.1},
    }).encode()
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128",
        data=body, headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
    )
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as fh:
        fh.write(r.read())


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="eleven_v3")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    key = os.environ["ELEVENLABS_API_KEY"]
    os.makedirs(args.out, exist_ok=True)
    meta = []
    for i, (frame, who, voice, text) in enumerate(LINES):
        tag = hashlib.sha1(f"{voice}|{text}|{args.model}".encode()).hexdigest()[:10]
        path = os.path.join(args.out, f"{who}_{tag}.mp3")
        if args.force or not os.path.exists(path):
            tts(key, voice, text, args.model, path)
        d = duration(path)
        meta.append({"frame": frame, "who": who, "file": os.path.abspath(path), "duration": d, "text": text})
        print(f"{frame:4d} {who:12s} {d:5.2f}s  {text}")
    with open(os.path.join(args.out, "lines.json"), "w") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

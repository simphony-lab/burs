"""Voice casting for LUNCH MONEY: for each character builds candidate voices (existing Russian voices +
newly designed voices from a description) reading the character's own lines, and glues them into one
audition file per character (candidates separated by 1, 2, 3... beeps).

    ELEVENLABS_API_KEY=... python cast.py --out cast
"""
import argparse
import base64
import json
import os
import subprocess
import urllib.request

API = "https://api.elevenlabs.io/v1"

CAST = {
    "bob": {
        "name": "Большой Боб",
        "design": "Young Russian man, about 18, deep low voice, calm, slow and confident, slightly husky, "
                  "leader of a street gang, speaks Russian naturally",
        "voices": [("Nester", "pM78bgjPVk0JXtaEnFoj"), ("Ivan", "JKtNvDNrWu33P1xzttP2")],
        "text": "Значит, договорились. Джон, останешься здесь. Мы с пацанами вернёмся в свою школу. "
                "Здорово, пацаны. Как lunch money сегодня? С собой взяли?",
    },
    "john": {
        "name": "Опасный Джон",
        "design": "Young Russian man, about 18, cold sharp unfriendly tone, slightly raspy, short phrases, "
                  "speaks Russian naturally",
        "voices": [("Denis", "0BcDz9UPwL3MpsnTeUlO")],
        "text": "А ты куда? И что мне здесь делать? Я не тебе вопрос задавал. Ладно. Буду на связи. "
                "Присмотрю тут за всеми.",
    },
    "karim": {
        "name": "Карим",
        "design": "Young Russian man, about 20, laid-back and calm, slightly nasal, casual street manner, "
                  "speaks Russian naturally",
        "voices": [("Dmitry", "kwajW3Xh5svCeKU5ky2S")],
        "text": "Ну что, домой? Давайте без задержек. Боб, тут проблема. "
                "Три стола, и ни одного серьёзного разговора.",
    },
    "artem": {
        "name": "Неожиданный Артём",
        "design": "Young Russian man, about 20, fast, cocky and mocking, slightly higher voice, grins while "
                  "talking, speaks Russian naturally",
        "voices": [("Andrey", "lsAmGFzUYusakA482527")],
        "text": "Надеюсь, сегодня без приключений. Эй, ты чего там прячешь? Ты чего упёрся? "
                "Видишь, Боб? Теперь даже объяснять ничего не надо.",
    },
    "maxim": {
        "name": "Максим",
        "design": "Young Russian man, about 20, polite, slightly unsure, soft voice, speaks Russian naturally",
        "voices": [("Leonid", "bg9LrEYQkRYwqkxA8VOy")],
        "text": "Да всё нормально будет. Понял. Если что, сразу к нему обратимся, без проблем. "
                "Мы тут сами разберёмся, не переживайте.",
    },
    "hoodie": {
        "name": "Мальчик в серой толстовке",
        "design": "Young Russian man with a light, high, boyish voice, stubborn and defiant but nervous, "
                  "speaks Russian naturally",
        "voices": [("Leonid", "bg9LrEYQkRYwqkxA8VOy"), ("Dmitry", "kwajW3Xh5svCeKU5ky2S")],
        "pitch": 3,
        "text": "Неважно. Понимаю. Вы деньги забираете. А если я не хочу? "
                "Я не буду вам ничего отдавать. Это мои деньги.",
    },
    "kids": {
        "name": "Младшеклассники",
        "design": "Young Russian man with a light, high, soft boyish voice, shy and quiet, "
                  "speaks Russian naturally",
        "voices": [("Leonid", "bg9LrEYQkRYwqkxA8VOy"), ("Dmitry", "kwajW3Xh5svCeKU5ky2S"),
                   ("Andrey", "lsAmGFzUYusakA482527")],
        "pitch": 3,
        "text": "Здравствуйте… Да… Да, сейчас. Ничего… Это Большой Боб. Я знаю. "
                "Сегодня лучше вообще не спорить. Они сегодня быстро…",
    },
}


def post(path, body, key, accept="application/json"):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(),
                                 headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": accept})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def tts(key, voice, text, path):
    audio = post(f"/text-to-speech/{voice}?output_format=mp3_44100_128",
                 {"text": text, "model_id": "eleven_v3",
                  "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "style": 0.3}}, key, "audio/mpeg")
    open(path, "wb").write(audio)


def design(key, desc, text):
    d = json.loads(post("/text-to-voice/design", {"voice_description": desc, "model_id": "eleven_multilingual_ttv_v2",
                                                   "text": text, "auto_generate_text": False}, key))
    return d.get("previews", [])


def to_wav(src, dst, pitch=0):
    af = "loudnorm=I=-18:TP=-1.5"
    if pitch:
        r = 2 ** (pitch / 12)
        af = f"asetrate={int(44100 * r)},aresample=44100,atempo={1 / r:.4f}," + af
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", af, "-ac", "1", "-ar", "44100", dst], check=True)


def beeps(n, path):
    parts = []
    for i in range(n):
        parts.append("sine=frequency=1200:duration=0.12")
    inputs = []
    for p in parts:
        inputs += ["-f", "lavfi", "-i", p]
    flt = "".join(f"[{i}]apad=pad_dur=0.12[a{i}];" for i in range(n)) + "".join(f"[a{i}]" for i in range(n)) + \
        f"concat=n={n}:v=0:a=1,volume=0.4,apad=pad_dur=0.5"
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", flt, "-ac", "1", "-ar", "44100", path],
                   check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--only")
    args = ap.parse_args()
    key = os.environ["ELEVENLABS_API_KEY"]
    os.makedirs(args.out, exist_ok=True)
    index_path = os.path.join(args.out, "cast.json")
    index = json.load(open(index_path)) if os.path.exists(index_path) else {}
    for cid, c in CAST.items():
        if args.only and cid not in args.only.split(","):
            continue
        d = os.path.join(args.out, cid)
        os.makedirs(d, exist_ok=True)
        cands = []
        for label, vid in c["voices"]:
            p = os.path.join(d, f"{label}.mp3")
            if not os.path.exists(p):
                tts(key, vid, c["text"], p)
            cands.append({"label": label, "voice_id": vid, "file": p, "kind": "library"})
        try:
            prevs = design(key, c["design"], c["text"])
        except Exception as e:  # noqa: BLE001
            print(cid, "design failed:", e)
            prevs = []
        for i, pv in enumerate(prevs):
            p = os.path.join(d, f"new{i + 1}.mp3")
            open(p, "wb").write(base64.b64decode(pv["audio_base_64"]))
            cands.append({"label": f"новый {i + 1}", "generated_voice_id": pv["generated_voice_id"], "file": p,
                          "kind": "designed"})
        # audition file: N beeps, then candidate N
        seq = []
        for i, cand in enumerate(cands):
            b = os.path.join(d, f"_beep{i}.wav")
            beeps(i + 1, b)
            w = os.path.join(d, f"_c{i}.wav")
            to_wav(cand["file"], w, c.get("pitch", 0))
            seq += [b, w]
        lst = os.path.join(d, "_list.txt")
        open(lst, "w").write("".join(f"file '{p}'\n" for p in seq))
        out = os.path.join(args.out, f"{cid}.mp3")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-ac", "1",
                        "-c:a", "libmp3lame", "-b:a", "128k", out], check=True)
        index[cid] = {"name": c["name"], "pitch": c.get("pitch", 0), "candidates": cands, "audition": out}
        print(cid, [x["label"] for x in cands], flush=True)
        json.dump(index, open(index_path, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

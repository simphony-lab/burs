"""Dialogue + sound effects for LUNCH MONEY via ElevenLabs.

    ELEVENLABS_API_KEY=... python audio_gen.py --out audio --scene test

Lines are generated one by one (eleven_v3, short audio tags for acting), cleaned with the voice isolator
where needed (removes echo of designed voices), trimmed of silence. Ambience / foley come from the
sound-effects endpoint. Everything is cached by content hash.
"""
import argparse
import hashlib
import json
import os
import subprocess
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://api.elevenlabs.io/v1"
VOICES = json.load(open(os.path.join(HERE, "voices.json")))

SCENES = {
    "test": {
        "lines": [
            ("bob1", "bob", "[calm, low] Значит, договорились. Джон, останешься здесь."),
            ("john1", "john", "А ты куда?"),
            ("bob2", "bob", "[casually] Мы с пацанами вернёмся в свою школу. У нас там как раз перемена скоро."),
            ("john2", "john", "[annoyed] И что мне здесь делать?"),
            ("bob3", "bob", "Посмотри, как у них идут дела. Познакомься поближе с местными. Если что — сообщишь мне."),
            ("maxim1", "maxim", "[a bit nervous] Да всё нормально будет."),
            ("john3", "john", "[coldly] Я не тебе вопрос задавал."),
        ],
        "sfx": [
            ("amb_corridor", "Indoor school hallway during a break, many distant teenagers chatting, footsteps on wooden "
                             "floor, echoey long corridor, no music", 22.0),
            ("locker_slam", "A metal school locker door slammed shut in a hallway, single hit", 1.5),
            ("footsteps", "Several teenagers walking past on a wooden parquet floor in a corridor, sneakers", 6.0),
        ],
        "isolate": ["maxim"],
    },
}


def req(path, body, key, accept="audio/mpeg"):
    r = urllib.request.Request(API + path, data=json.dumps(body).encode(),
                               headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": accept})
    with urllib.request.urlopen(r, timeout=300) as resp:
        return resp.read()


def isolate(key, src, dst):
    padded = dst + ".pad.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", "apad=whole_dur=6", "-ac", "1", "-ar", "44100",
                    padded], check=True)
    out = subprocess.run(["curl", "-sS", "-f", "-m", "300", "-X", "POST", API + "/audio-isolation",
                          "-H", f"xi-api-key: {key}", "-F", f"audio=@{padded}", "-o", dst], capture_output=True,
                         text=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr)


def trim(src, dst, pitch=0):
    af = ["silenceremove=start_periods=1:start_threshold=-45dB", "areverse",
          "silenceremove=start_periods=1:start_threshold=-45dB", "areverse"]
    if pitch:
        r = 2 ** (pitch / 12)
        af = [f"asetrate={int(44100 * r)}", "aresample=44100", f"atempo={1 / r:.4f}"] + af
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", ",".join(af), "-ac", "1", "-ar", "44100", dst],
                   check=True)


def duration(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True, check=True).stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--scene", default="test")
    args = ap.parse_args()
    key = os.environ["ELEVENLABS_API_KEY"]
    sc = SCENES[args.scene]
    os.makedirs(args.out, exist_ok=True)
    meta = {"lines": {}, "sfx": {}}
    for lid, who, text in sc["lines"]:
        vid = VOICES["voices"][who]
        tag = hashlib.sha1(f"{vid}|{text}".encode()).hexdigest()[:10]
        raw = os.path.join(args.out, f"{lid}_{tag}.mp3")
        if not os.path.exists(raw):
            open(raw, "wb").write(req(f"/text-to-speech/{vid}?output_format=mp3_44100_128",
                                      {"text": text, "model_id": "eleven_v3",
                                       "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "style": 0.25}},
                                      key))
        src = raw
        if who in sc.get("isolate", []):
            iso = raw.replace(".mp3", "_iso.mp3")
            if not os.path.exists(iso):
                isolate(key, raw, iso)
            src = iso
        wav = os.path.join(args.out, f"{lid}.wav")
        trim(src, wav, VOICES.get("pitch", {}).get(who, 0))
        meta["lines"][lid] = {"who": who, "text": text, "file": wav, "duration": duration(wav)}
        print(lid, who, round(meta["lines"][lid]["duration"], 2), flush=True)
    for sid, prompt, dur in sc["sfx"]:
        tag = hashlib.sha1(f"{prompt}|{dur}".encode()).hexdigest()[:10]
        p = os.path.join(args.out, f"{sid}_{tag}.mp3")
        if not os.path.exists(p):
            open(p, "wb").write(req("/sound-generation", {"text": prompt, "duration_seconds": dur,
                                                          "prompt_influence": 0.5}, key))
        meta["sfx"][sid] = {"file": p, "duration": duration(p)}
        print(sid, round(meta["sfx"][sid]["duration"], 2), flush=True)
    json.dump(meta, open(os.path.join(args.out, "audio.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

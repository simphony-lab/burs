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

# delivery after generation: younger pitch without chipmunk timbre (formants preserved) + a bit faster tempo,
# measured against a real series (teen voices 130-150 Hz, 6.6-8.2 syllables/s)
# Post pitch/tempo processing made voices sound robotic, so it is off: voices are used as generated.
# (Younger / faster delivery must come from the voice itself and the text, not from DSP.)
DELIVERY = {}

KIDS = {"kid1": "bg9LrEYQkRYwqkxA8VOy", "kid2": "gJEfHTTiifXEDmO687lC", "kid3": "6A9D8WSMm4rFsg2DWFeE",
        "kid4": "bg9LrEYQkRYwqkxA8VOy", "kid5": "gJEfHTTiifXEDmO687lC", "kid6": "6A9D8WSMm4rFsg2DWFeE",
        "kid7": "bg9LrEYQkRYwqkxA8VOy"}

# Whole episode "Первая смена". '+' goes right before the stressed vowel (пацан+ами = пацанАми).
EPISODE_LINES = [
    # scene 1, street by the school
    ("s1_01", "bob", "Зн+ачит, договор+ились. Джон, ост+анешься здесь."),
    ("s1_02", "john", "А ты куд+а?"),
    ("s1_03", "bob", "Мы с пацан+ами вернёмся в сво+ю шк+олу. У нас там как раз перем+ена ск+оро."),
    ("s1_04", "john", "[annoyed] И что мне здесь д+елать?"),
    ("s1_05", "bob", "Посмотр+и, как у них ид+ут дел+а. Познак+омься побл+иже с м+естными. "
                     "+Если что-то изм+енится или появ+ятся вопр+осы — сообщ+ишь мне."),
    ("s1_06", "maxim", "Да всё норм+ально б+удет."),
    ("s1_07", "john", "[coldly, quietly] Я не теб+е вопр+ос задав+ал."),
    ("s1_08", "bob", "[calmly] Джон, спок+ойно, спок+ойно, не кипиш+уй. Пр+осто послед+и за обстан+овкой, хорош+о?"),
    ("s1_09", "john", "[reluctantly] Л+адно. Б+уду на св+язи."),
    ("s1_10", "bob", "Макс+им, +если что, обращ+айтесь к нем+у. Он от н+ашей комп+ании."),
    ("s1_11", "maxim", "Пон+ял."),
    ("s1_12", "karim", "Ну что, дом+ой?"),
    ("s1_13", "bob", "Нет. В шк+олу. У нас там т+оже дел+а."),
    ("s1_14", "artem", "Над+еюсь, сег+одня без приключ+ений."),
    ("s1_15", "bob", "Посм+отрим."),
    # scene 2, main school, break
    ("s2_01", "artem", "О, смотр+и, уж+е все в+ышли."),
    ("s2_02", "karim", "Сег+одня нар+оду м+ного."),
    ("s2_03", "bob", "Зн+ачит, д+олго ход+ить не придётся."),
    ("s2_04", "bob", "Д+авайте без л+ишней сует+ы."),
    ("s2_05", "artem", "Пон+ял."),
    # scene 3, three tables
    ("s3_01", "bob", "Здор+ово, пацан+ы."),
    ("s3_02", "kid1", "[shyly] Здр+авствуйте…"),
    ("s3_03", "bob", "Как lunch money сег+одня? С соб+ой вз+яли?"),
    ("s3_04", "kid2", "[unsure] Да…"),
    ("s3_05", "bob", "Ну, тогд+а вы зн+аете, что д+елать."),
    ("s3_06", "artem", "Ч+етверо. Норм+ально."),
    ("s3_07", "bob", "Хор+ошего об+еда, пацан+ы."),
    ("s3_08", "bob", "Здор+ово. Lunch money есть?"),
    ("s3_09", "kid3", "Да, сейч+ас."),
    ("s3_10", "karim", "Д+авайте без зад+ержек."),
    ("s3_11", "artem", "Б+ыстро сег+одня."),
    ("s3_12", "bob", "Пошл+и д+альше."),
    ("s3_13", "artem", "Эй, ты чег+о там пр+ячешь?"),
    ("s3_14", "kid4", "[scared] Ничег+о…"),
    ("s3_15", "bob", "Не н+адо д+елать вид, что не поним+аешь, зач+ем мы подошл+и."),
    ("s3_16", "karim", "Всё, своб+одны."),
    ("s3_17", "kid5", "[whispering] Он+и сег+одня б+ыстро…"),
    ("s3_18", "artem", "Что сказ+ал?"),
    ("s3_19", "kid5", "[scared] Ничег+о."),
    ("s3_20", "bob", "Вот и хорош+о."),
    ("s3_21", "karim", "Три стол+а, и ни одног+о серьёзного разгов+ора."),
    ("s3_22", "artem", "Я же говор+ил, сег+одня б+ыстро б+удет."),
    ("s3_23", "bob", "Не р+адуйся р+аньше вр+емени. Ещё не зак+ончили."),
    # scene 4, corridor by the canteen
    ("s4_01", "artem", "Ты чег+о упёрся?"),
    ("s4_02", "hoodie", "Я не б+уду вам ничег+о отдав+ать."),
    ("s4_03", "karim", "Боб, тут пробл+ема."),
    ("s4_04", "bob", "Как теб+я зов+ут?"),
    ("s4_05", "hoodie", "Нев+ажно."),
    ("s4_06", "bob", "Хорош+о. Тогд+а д+авай без представл+ений. Ты поним+аешь, что сейч+ас происх+одит?"),
    ("s4_07", "hoodie", "Поним+аю. Вы д+еньги забир+аете."),
    ("s4_08", "bob", "Тогд+а не н+адо усложн+ять."),
    ("s4_09", "hoodie", "А +если я не хоч+у?"),
    ("s4_10", "artem", "Сл+ушай, ты д+олго ещё—"),
    ("s4_11", "bob", "Артём, подожд+и."),
    ("s4_12", "hoodie", "[louder] Это мо+и д+еньги! Я ником+у ничег+о не д+олжен!"),
    ("s4_13", "bob", "Разбер+итесь с ситу+ацией."),
    ("s4_14", "karim", "Всё."),
    ("s4_15", "bob", "Д+еньги?"),
    ("s4_16", "karim", "Забр+али."),
    ("s4_17", "artem", "Вот теп+ерь м+ожно идт+и."),
    # scene 5, end of the break
    ("s5_01", "kid6", "[whispering] Это Больш+ой Боб."),
    ("s5_02", "kid7", "[whispering] Я зн+аю."),
    ("s5_03", "kid6", "[whispering] Сег+одня л+учше в+ообще не сп+орить."),
    ("s5_04", "bob", "Ну что, пацан+ы, как об+ед?"),
    ("s5_05", "karim", "Вот так."),
    ("s5_06", "artem", "В+идишь, Боб? Теп+ерь д+аже объясн+ять ничег+о не н+адо."),
    ("s5_07", "bob", "Пох+оже, все уж+е пон+яли, как тут всё устр+оено."),
    ("s5_08", "bob", "Л+адно, пошл+и. На сег+одня дост+аточно."),
    ("s5_09", "karim", "А з+автра?"),
    ("s5_10", "bob", "З+автра б+удет з+автра."),
]

EPISODE_SFX = [
    ("amb_yard1", "Outdoor winter schoolyard during a break, light cold wind, distant kids shouting and playing, "
                  "distant city traffic, a crow, no music", 22.0),
    ("amb_yard2", "Quiet winter street next to a school, wind, far away voices of teenagers, a car passing "
                  "in the distance, snow, no music", 22.0),
    ("snow_steps", "A teenager shifting his weight and stepping on packed snow, crunching footsteps, close", 4.0),
    ("snow_walk", "Three people walking away on packed snow, crunching footsteps fading", 6.0),
    ("zipper", "A leather coat zipper being zipped up, close", 2.0),
    ("amb_hall1", "Busy school corridor during a break, many kids talking and laughing, footsteps, echo, no music", 22.0),
    ("amb_hall2", "School hallway crowd during recess, children chatter, sneakers squeaking, distant shouts, no music",
     22.0),
    ("bell", "Old electric school bell ringing loudly in a corridor", 5.0),
    ("door", "Heavy school entrance door opening and closing", 3.0),
    ("amb_canteen1", "School canteen during lunch, kids talking at tables, cutlery and plates clinking, trays, echo, "
                     "no music", 22.0),
    ("amb_canteen2", "Cafeteria murmur, children eating and chatting quietly, spoons on plates, no music", 22.0),
    ("money", "Paper banknotes and coins being taken out of a pocket and handed over, rustle", 3.0),
    ("count", "Someone quickly counting paper banknotes", 3.0),
    ("wallet", "A cheap wallet with velcro being opened", 2.0),
    ("locker_slam", "A metal school locker door slammed shut hard, bang, rattling", 2.0),
    ("scuffle", "Short scuffle in a corridor, clothes rustling, sneakers squeaking, a muffled bump against metal", 4.0),
    ("steps_indoor", "Group of teenagers walking in a school corridor, footsteps on linoleum", 6.0),
]

SCENES = {
    "episode": {"lines": EPISODE_LINES, "sfx": EPISODE_SFX, "isolate": []},
    "street1": {
        # scene 1 opening, outdoors by the school. '+' marks the stressed vowel.
        "lines": [
            ("s1_bob1", "bob", "Зн+ачит, договор+ились. Джон, ост+анешься здесь."),
            ("s1_john1", "john", "А ты куд+а?"),
            ("s1_bob2", "bob", "Мы с пац+анами вернёмся в сво+ю шк+олу. У нас там как раз перем+ена ск+оро."),
            ("s1_john2", "john", "[annoyed] И что мне здесь д+елать?"),
            ("s1_bob3", "bob", "Посмотр+и, как у них ид+ут дел+а. Познак+омься побл+иже с м+естными. "
                               "+Если что-то изм+енится или появ+ятся вопр+осы — сообщ+ишь мне."),
            ("s1_maxim1", "maxim", "Да всё норм+ально б+удет."),
            ("s1_john3", "john", "[coldly, quietly] Я не теб+е вопр+ос задав+ал."),
            ("s1_bob4", "bob", "[calmly] Джон, спок+ойно, спок+ойно, не кип+ишуй. Пр+осто послед+и за обстан+овкой, хорош+о?"),
            ("s1_john4", "john", "[reluctantly] Л+адно. Б+уду на св+язи."),
        ],
        "sfx": [
            ("amb_yard1", "Outdoor winter schoolyard during a break, light cold wind, distant kids shouting and playing, "
                          "distant city traffic, a crow, no music", 22.0),
            ("amb_yard2", "Quiet winter street next to a school, wind, far away voices of teenagers, a car passing "
                          "in the distance, snow, no music", 22.0),
            ("snow_steps", "A teenager shifting his weight and stepping on packed snow, crunching footsteps, close", 4.0),
        ],
        "isolate": [],
    },
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


VOWELS = "аеёиоуыэюяАЕЁИОУЫЭЮЯ"


def stress(text):
    """'+' before a stressed vowel -> vowel + combining acute accent (U+0301), which ElevenLabs reads as stress.
    Example: "Знач+ит, догов+орились" -> "Знач́ит"... (the mark goes after the vowel)."""
    out = []
    i = 0
    while i < len(text):
        c = text[i]
        if c == "+" and i + 1 < len(text) and text[i + 1] in VOWELS:
            out.append(text[i + 1] + "\u0301")
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


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


def trim(src, dst, pitch=0.0, tempo=1.0):
    af = ["silenceremove=start_periods=1:start_threshold=-45dB", "areverse",
          "silenceremove=start_periods=1:start_threshold=-45dB", "areverse"]
    if pitch or tempo != 1.0:
        af.append(f"rubberband=pitch={2 ** (pitch / 12):.5f}:tempo={tempo:.4f}:formant=preserved:transients=smooth")
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
        vid = KIDS.get(who) or VOICES["voices"][who]
        tag = hashlib.sha1(f"{vid}|{text}".encode()).hexdigest()[:10]
        raw = os.path.join(args.out, f"{lid}_{tag}.mp3")
        if not os.path.exists(raw):
            open(raw, "wb").write(req(f"/text-to-speech/{vid}?output_format=mp3_44100_128",
                                      {"text": stress(text), "model_id": "eleven_v3",
                                       "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "style": 0.25}},
                                      key))
        src = raw
        if who in sc.get("isolate", []):
            iso = raw.replace(".mp3", "_iso.mp3")
            if not os.path.exists(iso):
                isolate(key, raw, iso)
            src = iso
        wav = os.path.join(args.out, f"{lid}.wav")
        dl = DELIVERY.get(who, {})
        trim(src, wav, dl.get("pitch", 0.0), dl.get("tempo", 1.0))
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

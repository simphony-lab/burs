"""Single source of truth for the 6-minute edit: shot order/durations, voice cues, chat, sound effects.
Pure python (no bpy) so both the renderer and the compositor can import it."""

FPS = 24

# (shot id, seconds, kind) kind: "3d" rendered, "2d" drawn only, "hold" = reuses frames of another shot
SHOTS = [
    ("P1", 15, "2d"),
    ("S1a", 10, "3d"), ("S1b", 6, "3d"), ("S1c", 5, "3d"), ("S1d", 8, "3d"), ("S1e", 6, "3d"),
    ("S2", 30, "3d"),
    ("S3a", 5, "3d"), ("S3b", 5, "3d"), ("S3c", 6, "3d"), ("S3d", 7, "3d"), ("S3e", 5, "3d"), ("S3f", 6, "3d"),
    ("S3g", 6, "3d"),
    ("S4a", 8, "3d"), ("S4b", 7, "3d"), ("S4c", 6, "3d"), ("S4d", 10, "3d"), ("S4e", 4, "3d"), ("S4f", 5, "3d"),
    ("S5a", 6, "3d"), ("S5b", 8, "3d"), ("S5c", 8, "3d"), ("S5d", 6, "3d"), ("S5e", 7, "3d"), ("S5f", 10, "3d"),
    ("S6a", 10, "3d"), ("S6b", 6, "3d"), ("S6c", 6, "3d"), ("S6d", 8, "3d"),
    ("S7a", 8, "3d"), ("S7b", 5, "3d"), ("S7c", 4, "3d"), ("S7d", 14, "3d"), ("S7e", 7, "3d"), ("S7f", 7, "3d"),
    ("S7g", 6, "3d"), ("S7h", 6, "3d"), ("S7i", 7, "3d"), ("S7j", 6, "3d"),
    ("S8a", 6, "3d"), ("S8b", 7, "3d"), ("S8c", 12, "3d"), ("S8d", 10, "hold"),
    ("S9a", 10, "3d"), ("S9b", 10, "2d"),
]
DUR = {s: d for s, d, _ in SHOTS}
KIND = {s: k for s, _, k in SHOTS}
START = {}
_t = 0.0
for _s, _d, _k in SHOTS:
    START[_s] = _t
    _t += _d
TOTAL = _t

# first person shots (draw the game HUD) and which ones show the cheat overlay
FP_SHOTS = {"S2", "S3b", "S3f", "S4a", "S4c", "S5b", "S7d", "S7g", "S7h", "S8b"}
FP_LATE = {"S7f": 3.0}  # shot switches to first person at this local time

# duel hits: (kind, local seconds). "axe" breaks the shield, "crit" is a jump crit with the sword
HITS = {
    "S7d": [("axe", 1.8), ("crit", 2.9), ("crit", 3.6), ("crit", 4.3), ("crit", 5.0), ("crit", 5.7),
            ("crit", 6.4), ("axe", 7.5), ("crit", 8.3), ("crit", 9.0), ("crit", 9.7), ("crit", 10.4)],
}


def g(shot, t):
    """shot-local seconds -> global seconds"""
    return START[shot] + t


# ---------------------------------------------------------------------------- voice cues (id, shot, t)
VOICE = [
    ("N0", "P1", 4.5),
    ("N1", "S1a", 1.0),
    ("masha_hi", "S1d", 2.5),
    ("N2", "S1e", 1.5),
    ("bro_play", "S2", 27.0),
    ("N3", "S2", 13.0),
    ("dimon_fly", "S3a", 2.3),
    ("kotik_tp", "S3d", 1.9),
    ("kotik_oi", "S3e", 1.3),
    ("bro_hi", "S3e", 2.6),
    ("N4", "S3g", 0.8),
    ("dimon_ok", "S4b", 1.1),
    ("masha_no", "S4e", 0.3),
    ("N5", "S4f", 0.4),
    ("lava_where", "S5e", 0.6),
    ("bro_swim", "S5e", 3.8),
    ("N6", "S5f", 1.0),
    ("masha_council", "S6a", 1.0),
    ("snow_oi", "S6b", 3.0),
    ("bro_council", "S6c", 1.8),
    ("N7", "S6d", 3.2),
    ("N8", "S7a", 0.8),
    ("lava_duel", "S7b", 0.3),
    ("N9", "S7e", 0.8),
    ("N10", "S7f", 4.4),
    ("snow_unfair", "S7j", 1.0),
    ("N11", "S8d", 1.5),
    ("N12", "S9a", 1.0),
    ("bro_accept", "S9b", 6.2),
]

# ---------------------------------------------------------------------------- chat
WHITE, GRAY, GOLD, PURPLE, GREEN, RED, YELLOW, AQUA = (
    (255, 255, 255), (170, 170, 170), (255, 170, 0), (255, 85, 255), (85, 255, 85), (255, 85, 85),
    (255, 255, 85), (85, 255, 255))
RANK = {"pixel_masha": ("Игрок", GRAY), "dimon_pro": ("VIP", GREEN), "lavaKing": ("Премиум", GOLD),
        "snowbunny": ("Игрок", GRAY), "kotik_777": ("Игрок", GRAY), "brohacker": ("Игрок", GRAY)}


def say(name, text):
    rk, col = RANK.get(name, ("Игрок", GRAY))
    return [(f"[{rk}] ", col), (name, WHITE), (" » ", GRAY), (text, WHITE)]


def sysmsg(text, col=YELLOW):
    return [("[Сервер] ", AQUA), (text, col)]


TPA = [("brohacker", PURPLE), (" хочет телепортироваться к вам.", GOLD)]
TPAHERE = [("brohacker", PURPLE), (" просит вас телепортироваться к нему.", GOLD)]
ACCEPT_HINT = [("Введите ", GRAY), ("/tpaccept", GREEN), (", чтобы принять.", GRAY)]


def killed(victim, killer="brohacker"):
    return [(victim, WHITE), (" был убит игроком ", GRAY), (killer, PURPLE)]


# chat is cleared at the start of these shots (new point of view)
CHAT_RESET = {"S1a", "S2", "S3c", "S3d", "S4b", "S5c", "S6a", "S7a", "S8a", "S9a"}
# shots where the chat box is visible
CHAT_SHOWN = {"S1d", "S1e", "S2", "S3b", "S3c", "S3d", "S3e", "S3f", "S4a", "S4b", "S4c", "S4d", "S4e", "S4f",
              "S5b", "S5c", "S5e", "S6b", "S7a", "S7b", "S7d", "S7g", "S7h", "S7i", "S7j", "S8a", "S8b", "S8c"}

CHAT = [
    ("S1a", 2.0, say("pixel_masha", "кто-нибудь меняет алмазы на железо?")),
    ("S1a", 5.5, say("dimon_pro", "я! у колодца")),
    ("S1d", 1.0, [("brohacker", YELLOW), (" зашёл на сервер", YELLOW)]),
    ("S1d", 3.2, say("pixel_masha", "привет новенький)")),
    ("S2", 2.0, say("pixel_masha", "если что спрашивай")),
    ("S2", 9.0, say("dimon_pro", "у нас тут спокойно, античита нет, он не нужен))")),
    ("S3b", 2.4, [("[MassTPA] ", PURPLE), ("отправка запросов...", WHITE)]),
    ("S3b", 4.0, [("[MassTPA] ", PURPLE), ("отправлено 47/47", GREEN)]),
    ("S3c", 0.0, TPA), ("S3c", 0.3, ACCEPT_HINT), ("S3c", 0.7, TPA), ("S3c", 1.1, TPA),
    ("S3c", 2.2, say("pixel_masha", "эээ что??")),
    ("S3c", 3.4, say("dimon_pro", "он ЛЕТАЕТ")),
    ("S3c", 4.4, say("snowbunny", "мне 3 запроса пришло")),
    ("S3d", 0.6, TPA), ("S3d", 0.8, ACCEPT_HINT),
    ("S3d", 3.6, [("Вы приняли запрос от ", GRAY), ("brohacker", PURPLE)]),
    ("S3f", 3.4, killed("kotik_777")),
    ("S4a", 6.8, [("[MassTPA] ", PURPLE), ("отправлено 47/47", GREEN)]),
    ("S4b", 0.2, TPA), ("S4b", 0.3, [("brohacker", PURPLE), (": Раздаю алмазы! Примите тп)", WHITE)]),
    ("S4b", 2.4, [("Вы приняли запрос от ", GRAY), ("brohacker", PURPLE)]),
    ("S4b", 4.6, killed("dimon_pro")),
    ("S4c", 4.6, [("[MassTPA] ", PURPLE), ("Принято: 5", GREEN)]),
    ("S4d", 1.2, killed("Vanya_2012")), ("S4d", 3.2, killed("pro100_gamer")), ("S4d", 5.2, killed("Kisa_Murka")),
    ("S4d", 7.2, killed("NoobMaster")), ("S4d", 9.2, killed("tolik_pvp")),
    ("S4e", 0.4, say("pixel_masha", "НЕ ПРИНИМАЙТЕ ЕГО ТП!!")),
    ("S4f", 1.2, say("snowbunny", "он всех убивает")),
    ("S4f", 2.6, say("kotik_777", "я принял потому что алмазы(((")),
    ("S5b", 5.6, [("[MassTPA] ", PURPLE), ("режим: КО МНЕ · отправлено 47/47", WHITE)]),
    ("S5b", 7.2, [("[MassTPA] ", PURPLE), ("Принято: 9", GREEN)]),
    ("S5c", 0.2, TPAHERE), ("S5c", 0.4, [("brohacker", PURPLE), (": Админ: срочный сбор, примите", WHITE)]),
    ("S5e", 1.0, say("lavaKing", "ГДЕ МЫ")),
    ("S5e", 2.0, say("Lena_cat", "тут океан везде")),
    ("S5e", 5.4, say("brohacker", "удачно доплыть)")),
    ("S6b", 0.6, TPA), ("S6b", 0.8, ACCEPT_HINT),
    ("S6b", 3.0, [("Вы приняли запрос от ", GRAY), ("brohacker", PURPLE)]),
    ("S7a", 0.5, sysmsg("Дуэль: lavaKing vs brohacker", WHITE)),
    ("S7a", 2.5, say("pixel_masha", "лава, порви его")),
    ("S7a", 4.5, say("kotik_777", "ВПЕРЁД ЛАВА")),
    ("S7b", 0.4, say("lavaKing", "без телепортов. 1 на 1")),
    ("S7b", 3.5, say("brohacker", "ок)")),
    ("S7d", 1.9, [("Щит сломан", RED)]),
    ("S7d", 7.6, [("Щит сломан", RED)]),
    ("S7g", 2.6, killed("lavaKing")),
    ("S7h", 1.0, say("snowbunny", "не может быть")),
    ("S7h", 3.4, [("[MassTPA] ", PURPLE), ("Принято: 14", GREEN)]),
    ("S7i", 2.9, killed("dimon_pro")), ("S7i", 3.0, killed("kotik_777")), ("S7i", 3.2, killed("Lena_cat")),
    ("S7i", 3.4, killed("Sanya_K")), ("S7i", 3.6, killed("minecrafter07")), ("S7i", 3.8, killed("Dasha_bee")),
    ("S7i", 4.0, killed("kirill_top")), ("S7i", 4.2, killed("Zhenya42")),
    ("S7i", 4.6, say("brohacker", "gg ez")),
    ("S8a", 0.4, say("pixel_masha", "РЕПОРТ")), ("S8a", 0.9, say("dimon_pro", "РЕПОРТ")),
    ("S8a", 1.4, say("kotik_777", "админ где??")), ("S8a", 2.0, say("lavaKing", "/report brohacker")),
    ("S8a", 2.8, sysmsg("Администрация сейчас не в сети.", RED)),
    ("S8a", 4.0, say("snowbunny", "мы обречены")),
    ("S8b", 5.8, [("[MassTPA] ", PURPLE), ("отправлено 470/470", GREEN)]),
]
# MassTPA x10 chat flood in S8c (wall of requests)
for _i in range(60):
    CHAT.append(("S8c", 0.1 + _i * 0.13, TPA if _i % 5 else ACCEPT_HINT))
CHAT.append(("S8c", 8.6, sysmsg("Сервер перегружен.", RED)))

# ---------------------------------------------------------------------------- sound effects (name, shot, t)
SFX = [
    ("pling", "S3c", 0.0), ("pling", "S3c", 0.7), ("pling", "S3c", 1.1),
    ("pling", "S3d", 0.6), ("teleport", "S3d", 4.5), ("chat", "S3c", 2.2), ("chat", "S3c", 3.4),
    ("jump", "S3f", 2.1), ("crit", "S3f", 2.6), ("death", "S3f", 2.7), ("poof", "S3f", 3.5),
    ("swoosh", "S3a", 1.3), ("swoosh", "S3g", 2.4),
    ("pling", "S4b", 0.2), ("teleport", "S4b", 2.9), ("sweep", "S4b", 3.7), ("death", "S4b", 3.85),
    ("poof", "S4b", 4.6),
    ("pling", "S6b", 0.6), ("teleport", "S6c", 0.7),
    ("splash", "S5d", 1.4), ("splash", "S5d", 1.9), ("splash", "S5d", 2.3), ("splash", "S5d", 2.6),
    ("splash", "S5d", 3.0), ("splash", "S5d", 3.3), ("splash", "S5d", 3.7), ("splash", "S5d", 4.0),
    ("swoosh", "S5a", 0.2), ("swoosh", "S7b", 2.0),
    ("totem", "S7f", 3.35), ("crit", "S7f", 1.35), ("hurt", "S7f", 1.4),
    ("crit", "S7g", 1.0), ("crit", "S7g", 1.7), ("death", "S7g", 1.75), ("poof", "S7g", 2.6),
    ("glitch", "S8c", 8.0), ("glitch", "S8c", 9.5), ("glitch", "S8c", 10.6),
]
for _i in range(5):
    SFX += [("teleport", "S4d", _i * 2 + 0.17), ("sweep", "S4d", _i * 2 + 0.67), ("death", "S4d", _i * 2 + 0.75),
            ("poof", "S4d", _i * 2 + 1.5)]
for _i in range(9):
    SFX.append(("teleport", "S5c", 0.55 + _i * 0.32))
for _i in range(14):
    SFX.append(("teleport", "S7i", 0.25 + _i * 0.12))
SFX += [("sweep", "S7i", 2.6), ("sweep", "S7i", 3.3), ("sweep", "S7i", 4.0), ("death", "S7i", 2.75),
        ("death", "S7i", 3.45), ("death", "S7i", 4.15)]
for _k, _t in HITS["S7d"]:
    SFX.append(("shield" if _k == "axe" else "crit", "S7d", _t))
    if _k == "crit":
        SFX.append(("jump", "S7d", _t - 0.3))
for _i in range(30):
    SFX.append(("pling", "S8c", 0.1 + _i * 0.26))
# countdown beeps
SFX += [("beep", "S7c", 0.2), ("beep", "S7c", 1.1), ("beep", "S7c", 2.0), ("go", "S7c", 2.9)]

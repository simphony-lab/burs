"""Pixel-art item sprites (16x16), shared by the 3D items and the 2D hotbar icons."""


def sprite_sword():
    s = {}
    for i in range(10):
        x, y = 5 + i, 10 - i
        s[(x, y)] = "b"
        s[(x + 1, y)] = "e"
        s[(x, y - 1)] = "e"
    for d in range(-2, 3):
        s[(4 + d, 11 + d)] = "g"
    for i in range(3):
        s[(3 - i, 12 + i)] = "h"
    s[(0, 15)] = "g"
    return s, {"b": (150, 236, 230), "e": (210, 255, 250), "g": (60, 60, 70), "h": (110, 76, 40)}


def sprite_axe():
    s = {}
    for i in range(11):
        s[(2 + i, 14 - i)] = "h"
    for (x, y) in [(9, 1), (10, 1), (11, 1), (8, 2), (9, 2), (10, 2), (11, 2), (12, 2), (8, 3), (9, 3), (10, 3),
                   (11, 3), (12, 3), (13, 3), (9, 4), (10, 4), (11, 4), (12, 4), (13, 4), (10, 5), (11, 5), (12, 5),
                   (13, 6), (13, 5), (14, 5)]:
        s[(x, y)] = "m"
    for (x, y) in [(8, 2), (8, 3), (9, 4), (10, 5)]:
        s[(x, y)] = "e"
    return s, {"h": (110, 76, 40), "m": (70, 62, 74), "e": (130, 120, 140)}


def sprite_shield():
    s = {}
    for y in range(1, 15):
        w = 5 if y < 11 else 5 - (y - 10)
        for x in range(8 - w, 8 + w):
            s[(x, y)] = "r" if (x in (8 - w, 7 + w) or y in (1, 14)) else "f"
    for y in range(4, 11):
        s[(7, y)] = "c"
        s[(8, y)] = "c"
    return s, {"r": (170, 170, 176), "f": (222, 82, 30), "c": (252, 202, 46)}


def sprite_apple():
    s = {}
    for y in range(4, 15):
        for x in range(3, 13):
            if (x - 7.5) ** 2 / 25 + (y - 9.5) ** 2 / 30 <= 1:
                s[(x, y)] = "a"
    for (x, y) in [(5, 6), (5, 7), (6, 6)]:
        s[(x, y)] = "h"
    s[(8, 2)] = s[(8, 3)] = "s"
    s[(9, 2)] = s[(10, 1)] = "l"
    return s, {"a": (250, 200, 40), "h": (255, 250, 200), "s": (110, 76, 40), "l": (90, 200, 70)}


def sprite_totem():
    s = {}
    for y in range(2, 8):
        for x in range(5, 11):
            s[(x, y)] = "y"
    for (x, y) in [(6, 4), (9, 4)]:
        s[(x, y)] = "g"
    for y in range(8, 14):
        for x in range(4, 12):
            s[(x, y)] = "y" if 5 <= x <= 10 else "w"
    for (x, y) in [(2, 9), (3, 9), (12, 9), (13, 9), (2, 10), (13, 10)]:
        s[(x, y)] = "w"
    for y in range(9, 13):
        s[(7, y)] = s[(8, y)] = "g"
    return s, {"y": (250, 214, 70), "g": (90, 200, 80), "w": (230, 190, 60)}


def sprite_pearl():
    s = {}
    for y in range(4, 13):
        for x in range(4, 13):
            if (x - 8) ** 2 + (y - 8) ** 2 <= 16:
                s[(x, y)] = "p" if (x - 7) ** 2 + (y - 7) ** 2 > 3 else "l"
    return s, {"p": (30, 110, 100), "l": (120, 220, 200)}


def sprite_cobble():
    s = {}
    for y in range(2, 15):
        for x in range(2, 15):
            s[(x, y)] = "c" if (x * 7 + y * 3) % 5 else "d"
    return s, {"c": (130, 130, 130), "d": (90, 90, 90)}


def sprite_bread():
    s = {}
    for y in range(6, 12):
        for x in range(2, 15):
            if not (y in (6, 11) and x in (2, 14)):
                s[(x, y)] = "b" if y > 7 else "t"
    for x in (5, 8, 11):
        s[(x, 7)] = "c"
    return s, {"b": (190, 130, 60), "t": (220, 160, 80), "c": (240, 210, 140)}


SPRITES = {"sword": sprite_sword, "axe": sprite_axe}
ICONS = {"sword": sprite_sword, "axe": sprite_axe, "shield": sprite_shield, "apple": sprite_apple,
         "totem": sprite_totem, "pearl": sprite_pearl, "cobble": sprite_cobble, "bread": sprite_bread}

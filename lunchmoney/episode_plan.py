"""Timing plan of the episode "Первая смена" (no Blender needed): when each line is said, where sound effects go,
which shots cover which part of each scene. Used by both the renderer and the sound mixer."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LINES = json.load(open(os.path.join(HERE, "data", "lines.json")))
FPS = 24


def D(lid):
    return LINES[lid]["duration"]


class Plan:
    def __init__(self, name, loc, start=0.8):
        self.name, self.loc = name, loc
        self.t = start
        self.cues = {}
        self.ev = {}
        self.sfx = []
        self.shots = []
        self.amb = []

    def line(self, lid, gap=0.35):
        t0 = self.t + gap
        t1 = t0 + D(lid)
        self.cues[lid] = (t0, t1)
        self.t = t1
        return t0, t1

    def wait(self, dt):
        self.t += dt
        return self.t

    def mark(self, name, dt=0.0):
        self.ev[name] = self.t + dt
        return self.ev[name]

    def fx(self, sid, t, pan=0.0, gain=0.3):
        self.sfx.append((sid, t, pan, gain))

    def shot(self, sid, t0, t1):
        self.shots.append((sid, t0, t1))

    @property
    def frames(self):
        return int(round(self.length * FPS))


def scene1():
    p = Plan("s1", "street")
    p.amb = ["amb_yard1", "amb_yard2"]
    p.line("s1_01", 0.0)
    p.line("s1_02", 0.35)
    p.line("s1_03", 0.35)
    p.line("s1_04", 0.45)
    a_end = p.line("s1_05", 0.4)[1]
    m0 = p.line("s1_06", 0.5)[0]
    p.fx("snow_steps", m0 + 0.3, 0.4, 0.2)
    j0, j1 = p.line("s1_07", 1.3)
    p.fx("snow_steps", j0 - 0.5, -0.5, 0.25)
    p.line("s1_08", 0.9)
    c_end = p.line("s1_09", 0.5)[1]
    p.line("s1_10", 0.6)
    p.line("s1_11", 0.3)
    p.mark("hat", 0.3)
    p.wait(2.4)
    d_end = p.t
    p.line("s1_12", 0.2)
    p.line("s1_13", 0.3)
    p.mark("leave", 0.1)
    p.line("s1_14", 0.4)
    p.line("s1_15", 0.3)
    p.fx("snow_walk", p.ev["leave"] + 0.2, -0.2, 0.3)
    p.length = p.t + 4.0
    p.shot("1A", 0.0, a_end + 0.25)
    p.shot("1B", a_end + 0.25, j1 + 0.6)
    p.shot("1C", j1 + 0.6, c_end + 0.3)
    p.shot("1D", c_end + 0.3, d_end)
    p.shot("1E", d_end, p.length)
    return p


def scene2():
    p = Plan("s2", "hall", start=0.0)
    p.amb = ["amb_hall1", "amb_hall2"]
    p.fx("bell", 0.0, 0.3, 0.45)
    p.mark("enter", 1.6)
    p.fx("door", 1.4, 0.0, 0.3)
    p.fx("steps_indoor", 2.0, 0.0, 0.25)
    p.t = 3.4
    p.line("s2_01", 0.0)
    p.line("s2_02", 0.3)
    p.line("s2_03", 0.3)
    p.mark("look", 0.2)
    p.line("s2_04", 0.7)
    p.line("s2_05", 0.25)
    p.mark("go", 0.3)
    p.length = p.t + 2.2
    p.shot("2A", 0.0, p.ev["enter"] + 1.6)
    p.shot("2B", p.ev["enter"] + 1.6, p.length)
    return p


def scene3():
    p = Plan("s3", "hall", start=0.0)
    p.amb = ["amb_canteen1", "amb_canteen2"]
    p.mark("walk1")
    p.t = 2.2
    t1_start = p.t
    p.line("s3_01", 0.0)
    p.line("s3_02", 0.35)
    p.line("s3_03", 0.35)
    p.line("s3_04", 0.6)
    p.line("s3_05", 0.4)
    p.mark("pay1", 0.2)
    for dt, pan in ((0.75, 0.1), (1.75, 0.15), (3.35, 0.1)):
        p.fx("money", p.ev["pay1"] + dt, pan, 0.28)
    p.wait(4.2)
    p.fx("count", p.t + 0.2, 0.2, 0.35)
    p.line("s3_06", 0.3)
    p.line("s3_07", 0.4)
    a_end = p.t
    p.mark("walk2", 0.3)
    p.t += 2.6
    p.line("s3_08", 0.0)
    p.line("s3_09", 0.35)
    p.line("s3_10", 0.25)
    p.mark("pay2", 0.1)
    for dt in (0.65, 1.55):
        p.fx("money", p.ev["pay2"] + dt, 0.0, 0.28)
    p.wait(2.4)
    p.line("s3_11", 0.2)
    p.line("s3_12", 0.3)
    b_end = p.t
    p.mark("walk3", 0.2)
    p.t += 2.6
    p.mark("hide", -1.0)
    p.line("s3_13", 0.0)
    p.line("s3_14", 0.35)
    p.line("s3_15", 0.45)
    p.mark("pay3", 0.3)
    p.fx("money", p.ev["pay3"] + 0.75, 0.0, 0.3)
    p.wait(1.6)
    p.line("s3_16", 0.1)
    w0 = p.line("s3_17", 0.5)[0]
    p.line("s3_18", 0.3)
    p.line("s3_19", 0.3)
    p.line("s3_20", 0.3)
    c_end = p.t
    p.mark("walk4", 0.3)
    p.line("s3_21", 0.6)
    p.line("s3_22", 0.3)
    p.line("s3_23", 0.3)
    p.length = p.t + 1.2
    p.shot("3A", 0.0, a_end + 0.3)
    p.shot("3B", a_end + 0.3, b_end + 0.2)
    p.shot("3C", b_end + 0.2, w0 - 0.15)
    p.shot("3D", w0 - 0.15, c_end + 0.3)
    p.shot("3E", c_end + 0.3, p.length)
    return p


def scene4():
    p = Plan("s4", "hall", start=0.6)
    p.amb = ["amb_hall2", "amb_hall1"]
    p.line("s4_01", 0.0)
    p.line("s4_02", 0.35)
    p.line("s4_03", 0.4)
    p.mark("bob_in", -1.2)
    p.line("s4_04", 0.6)
    p.line("s4_05", 0.4)
    p.line("s4_06", 0.5)
    p.line("s4_07", 0.4)
    p.line("s4_08", 0.45)
    a_end = p.line("s4_09", 0.6)[1]
    p.line("s4_10", 0.3)
    p.line("s4_11", 0.05)
    p.line("s4_12", 0.35)
    b_end = p.t
    p.line("s4_13", 0.9)
    p.mark("take", 0.3)
    t = p.ev["take"]
    p.fx("scuffle", t + 2.6, -0.4, 0.35)
    p.fx("locker_slam", t + 5.3, -0.4, 0.55)
    p.fx("wallet", t + 4.3, -0.4, 0.3)
    p.wait(6.0)
    p.mark("back")
    p.wait(2.6)
    c_end = p.t
    p.line("s4_14", 0.0)
    p.line("s4_15", 0.3)
    p.line("s4_16", 0.3)
    p.line("s4_17", 0.35)
    p.length = p.t + 1.2
    p.shot("4A", 0.0, a_end + 0.2)
    p.shot("4B", a_end + 0.2, b_end + 0.3)
    p.shot("4C", b_end + 0.3, c_end)
    p.shot("4D", c_end, p.length)
    return p


def scene5():
    p = Plan("s5", "hall", start=0.6)
    p.amb = ["amb_canteen2", "amb_canteen1"]
    p.mark("walk")
    p.line("s5_01", 0.6)
    p.line("s5_02", 0.25)
    p.line("s5_03", 0.3)
    a_end = p.t + 0.5
    p.t = max(p.t + 1.8, 9.0)
    p.mark("arrive", -0.2)
    p.line("s5_04", 0.0)
    p.mark("pay", 0.3)
    for dt in (0.55, 1.25):
        p.fx("money", p.ev["pay"] + dt, 0.0, 0.28)
    p.wait(2.0)
    p.line("s5_05", 0.2)
    p.line("s5_06", 0.4)
    p.line("s5_07", 0.4)
    b_end = p.t
    p.mark("bell", 0.4)
    p.fx("bell", p.ev["bell"], 0.0, 0.45)
    p.line("s5_08", 1.4)
    p.line("s5_09", 0.3)
    p.line("s5_10", 0.3)
    p.mark("exit", 0.2)
    p.length = p.t + 6.5
    p.shot("5A", 0.0, a_end)
    p.shot("5B", a_end, b_end + 0.6)
    p.shot("5C", b_end + 0.6, p.length)
    return p


SCENES = {"s1": scene1, "s2": scene2, "s3": scene3, "s4": scene4, "s5": scene5}
ORDER = ["s1", "s2", "s3", "s4", "s5"]


def all_plans():
    return {k: SCENES[k]() for k in ORDER}


if __name__ == "__main__":
    tot = 0
    for k, p in all_plans().items():
        tot += p.length
        print(k, f"{p.length:6.1f}s", [(s, round(a, 1), round(b, 1)) for s, a, b in p.shots])
    print(f"total {tot:.1f}s = {tot / 60:.1f} min, {int(tot * FPS)} frames")

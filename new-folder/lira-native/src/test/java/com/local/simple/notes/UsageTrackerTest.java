package com.local.simple.notes;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

import org.junit.Before;
import org.junit.Test;

/** Plain JVM tests of the event state machine (no Android runtime needed). */
public class UsageTrackerTest {
    static final int R = UsageTracker.RESUMED, P = UsageTracker.PAUSED, S = UsageTracker.STOPPED;
    static final long DAY = UsageTracker.startOfDay(System.currentTimeMillis());
    static final long T = DAY + 10 * 3600_000L; // 10:00 today

    UsageTracker t;

    @Before public void setUp() {
        t = new UsageTracker(null);
        t.reset(DAY);
    }

    @Test public void singleSession() {
        t.event(R, T, "yt", "Main");
        t.event(P, T + 60_000, "yt", "Main");
        assertEquals(60_000, t.usage("yt", T + 100_000));
        assertNull(t.foreground());
    }

    @Test public void liveSessionCountsUntilNow() {
        t.event(R, T, "yt", "Main");
        assertEquals(42_000, t.usage("yt", T + 42_000));
        assertEquals("yt", t.foreground());
    }

    @Test public void activityChangeInsideOneAppKeepsCounting() {
        // Android 10+: A paused, B resumed, then A stopped.
        t.event(R, T, "tg", "A");
        t.event(P, T + 10_000, "tg", "A");
        t.event(R, T + 10_200, "tg", "B");
        t.event(S, T + 10_500, "tg", "A");
        assertEquals("tg", t.foreground());
        assertEquals(29_800, t.usage("tg", T + 30_000));
        t.event(P, T + 30_000, "tg", "B");
        t.event(S, T + 30_400, "tg", "B");
        assertEquals(29_800, t.usage("tg", T + 90_000));
    }

    @Test public void nextAppEndsPreviousEvenWithoutPause() {
        t.event(R, T, "a", "X");
        t.event(R, T + 5_000, "b", "Y");
        assertEquals(5_000, t.usage("a", T + 20_000));
        assertEquals(15_000, t.usage("b", T + 20_000));
        assertEquals("b", t.foreground());
        t.event(P, T + 21_000, "a", "X"); // late pause of a: ignored
        assertEquals(5_000, t.usage("a", T + 30_000));
    }

    @Test public void screenOffAndLockStopCounting() {
        t.event(R, T, "yt", "Main");
        t.event(UsageTracker.SCREEN_OFF, T + 30_000, null, null);
        t.event(P, T + 31_000, "yt", "Main");
        assertEquals(30_000, t.usage("yt", T + 600_000));
        assertNull(t.foreground());
        t.event(R, T + 600_000, "yt", "Main");
        t.event(UsageTracker.KEYGUARD_SHOWN, T + 610_000, null, null);
        assertEquals(40_000, t.usage("yt", T + 700_000));
    }

    @Test public void sessionStartedBeforeMidnightCountsFromMidnight() {
        t.event(R, DAY - 600_000, "yt", "Main");
        assertEquals(300_000, t.usage("yt", DAY + 300_000));
        t.event(P, DAY + 400_000, "yt", "Main");
        assertEquals(400_000, t.usage("yt", DAY + 900_000));
    }

    @Test public void sameEventTwiceIsCountedOnce() {
        t.event(R, T, "yt", "Main");
        t.event(P, T + 10_000, "yt", "Main");
        t.event(R, T, "yt", "Main");          // re-read by the overlap window
        t.event(P, T + 10_000, "yt", "Main");
        assertEquals(10_000, t.usage("yt", T + 50_000));
        assertNull(t.foreground());
    }

    @Test public void pruneForgetsOnlyOldKeys() {
        t.event(R, T, "yt", "Main");
        t.prune(T + 1);
        t.event(R, T, "yt", "Main"); // forgotten key, still no double count: session already open
        assertEquals(5_000, t.usage("yt", T + 5_000));
    }

    @Test public void snapshotHasAllApps() {
        t.event(R, T, "a", "X");
        t.event(R, T + 1_000, "b", "Y");
        assertEquals(2, t.snapshot(T + 2_000).size());
        assertEquals(1_000L, (long) t.snapshot(T + 2_000).get("a"));
        assertEquals(1_000L, (long) t.snapshot(T + 2_000).get("b"));
    }
}

package com.local.simple.notes;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.util.HashMap;

/** Plain JVM tests for what the island decides to show. */
public class IslandSnapshotTest {
    static final long T = 1_800_000_000_000L, M = 60_000L;

    static ScreenTime.Config cfg() {
        ScreenTime.Config c = new ScreenTime.Config();
        c.island = true;
        return c;
    }

    @Test public void nothingMeansNone() {
        IslandSnapshot s = IslandSnapshot.compute(cfg(), null, T, null, null, null, 0);
        assertEquals(IslandSnapshot.NONE, s.kind);
        assertTrue(s.tasks.isEmpty());
    }

    @Test public void currentTasksSortedAndCounted() {
        ScreenTime.Config c = cfg();
        c.tasks.add(new ScreenTime.Task("b", "Бег", T - 10 * M, T + 20 * M, false));
        c.tasks.add(new ScreenTime.Task("a", "Почта", T - 30 * M, T + 5 * M, false));
        c.tasks.add(new ScreenTime.Task("c", "Обед", T - 5 * M, T + 40 * M, true));
        c.tasks.add(new ScreenTime.Task("d", "Позже", T + 10 * M, T + 40 * M, false));
        c.tasks.add(new ScreenTime.Task("e", "Раньше", T - 90 * M, T - 30 * M, false));
        IslandSnapshot s = IslandSnapshot.compute(c, null, T, null, null, null, 0);
        assertEquals(IslandSnapshot.TASK, s.kind);
        assertEquals(3, s.tasks.size());
        assertEquals("a", s.tasks.get(0).key);
        assertEquals(2, s.openTasks);
        assertEquals("Почта", s.firstOpen().title);
    }

    @Test public void islandTickOverridesConfig() {
        ScreenTime.Config c = cfg();
        c.tasks.add(new ScreenTime.Task("a", "Почта", T - M, T + M, false));
        HashMap<String, Boolean> p = new HashMap<String, Boolean>();
        p.put("a", true);
        IslandSnapshot s = IslandSnapshot.compute(c, p, T, null, null, null, 0);
        assertTrue(s.tasks.get(0).done);
        assertEquals(0, s.openTasks);
        assertEquals(IslandSnapshot.NONE, s.kind);
        assertNull(s.firstOpen());
        assertFalse(s.structure().equals(IslandSnapshot.compute(c, null, T, null, null, null, 0).structure()));
    }

    @Test public void curfewCountdownStartsThirtyMinutesBefore() {
        ScreenTime.Config c = cfg();
        c.curfew.add(new long[]{T + 31 * M, T + 9 * 60 * M});
        assertEquals(IslandSnapshot.NONE, IslandSnapshot.compute(c, null, T, null, null, null, 0).kind);
        IslandSnapshot s = IslandSnapshot.compute(c, null, T + 2 * M, null, null, null, 0);
        assertEquals(IslandSnapshot.CURFEW_SOON, s.kind);
        assertEquals("29:00", IslandSnapshot.countdown(s.curfewStart - s.now));
        assertEquals(IslandSnapshot.CURFEW_ON, IslandSnapshot.compute(c, null, T + 40 * M, null, null, null, 0).kind);
        assertEquals(IslandSnapshot.NONE, IslandSnapshot.compute(c, null, T + 10 * 60 * M, null, null, null, 0).kind);
    }

    @Test public void priorityCurfewThenLimitThenTask() {
        ScreenTime.Config c = cfg();
        c.limits.put("yt", 30);
        c.tasks.add(new ScreenTime.Task("a", "Почта", T - M, T + M, false));
        assertEquals(IslandSnapshot.TASK, IslandSnapshot.compute(c, null, T, null, null, null, 0).kind);
        IslandSnapshot s = IslandSnapshot.compute(c, null, T, "yt", "YouTube", null, 12 * M);
        assertEquals(IslandSnapshot.LIMIT, s.kind);
        assertEquals(30 * M, s.limit);
        assertEquals(1, s.tasks.size());
        c.curfew.add(new long[]{T + 10 * M, T + 600 * M});
        assertEquals(IslandSnapshot.CURFEW_SOON, IslandSnapshot.compute(c, null, T, "yt", "YouTube", null, 12 * M).kind);
        c.enabled = false; // limits switched off: no limit content
        assertNull(IslandSnapshot.compute(c, null, T, "yt", "YouTube", null, 12 * M).limitPkg);
    }

    @Test public void countdownFormat() {
        assertEquals("30:00", IslandSnapshot.countdown(30 * M));
        assertEquals("0:01", IslandSnapshot.countdown(1));
        assertEquals("0:00", IslandSnapshot.countdown(0));
        assertEquals("1:00:00", IslandSnapshot.countdown(60 * M));
        assertEquals("9:59", IslandSnapshot.countdown(10 * M - 1000));
    }

}

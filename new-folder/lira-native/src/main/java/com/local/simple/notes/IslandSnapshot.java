package com.local.simple.notes;

import android.graphics.Bitmap;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

/** What the dynamic island should show at one moment. Built once a second by the service. */
final class IslandSnapshot {
    static final int NONE = 0, TASK = 1, LIMIT = 2, CURFEW_SOON = 3, CURFEW_ON = 4;
    /** The countdown starts this long before the curfew. */
    static final long CURFEW_LEAD = 30L * 60_000L;

    int kind = NONE;
    long now;
    // app limit (when an app with a limit is in front)
    String limitPkg, limitLabel;
    Bitmap limitIcon;
    long used, limit;
    // curfew
    long curfewStart, curfewEnd;
    // tasks whose time window contains now; done flags already include ticks made on the island
    final ArrayList<ScreenTime.Task> tasks = new ArrayList<ScreenTime.Task>();
    int openTasks;

    boolean hasCurfew() { return kind == CURFEW_SOON || kind == CURFEW_ON || curfewStart > 0; }
    boolean hasLimit() { return limitPkg != null; }

    /** First task that is not done yet (the one the compact island shows). */
    ScreenTime.Task firstOpen() {
        for (ScreenTime.Task t : tasks) if (!t.done) return t;
        return null;
    }

    /** Changes only when the island needs a different layout, not when a number ticks. */
    String structure() {
        StringBuilder b = new StringBuilder().append(kind).append('|').append(limitPkg).append('|')
                .append(curfewStart > 0 ? (now >= curfewStart ? "on" : "soon") : "-").append('|');
        for (ScreenTime.Task t : tasks) b.append(t.key).append(t.done ? '+' : '-').append(',');
        return b.toString();
    }

    static IslandSnapshot compute(ScreenTime.Config cfg, Map<String, Boolean> pending, long now,
                                  String fgPkg, String fgLabel, Bitmap fgIcon, long fgUsed) {
        IslandSnapshot s = new IslandSnapshot();
        s.now = now;
        for (ScreenTime.Task t : cfg.tasks) {
            if (t.start <= now && now < t.end) {
                Boolean p = pending == null ? null : pending.get(t.key);
                s.tasks.add(p == null || p == t.done ? t : new ScreenTime.Task(t.key, t.title, t.start, t.end, p));
            }
        }
        Collections.sort(s.tasks, new Comparator<ScreenTime.Task>() {
            @Override public int compare(ScreenTime.Task a, ScreenTime.Task b) {
                if (a.start != b.start) return a.start < b.start ? -1 : 1;
                if (a.end != b.end) return a.end < b.end ? -1 : 1;
                return a.title.compareTo(b.title);
            }
        });
        for (ScreenTime.Task t : s.tasks) if (!t.done) s.openTasks++;

        for (long[] w : cfg.curfew) {
            if (w[1] <= now) continue;
            if (now >= w[0] || w[0] - now <= CURFEW_LEAD) {
                s.curfewStart = w[0];
                s.curfewEnd = w[1];
            }
            break;
        }

        Integer lim = fgPkg == null ? null : cfg.limits.get(fgPkg);
        if (cfg.enabled && lim != null && lim > 0) {
            s.limitPkg = fgPkg;
            s.limitLabel = fgLabel == null ? fgPkg : fgLabel;
            s.limitIcon = fgIcon;
            s.used = Math.max(0L, fgUsed);
            s.limit = lim * 60_000L;
        }

        if (s.curfewStart > 0) s.kind = now >= s.curfewStart ? CURFEW_ON : CURFEW_SOON;
        else if (s.limitPkg != null) s.kind = LIMIT;
        else if (s.openTasks > 0) s.kind = TASK;
        return s;
    }

    /** "29:41" (or "1:02:03"), rounded up so that the last second shows 0:01. */
    static String countdown(long ms) {
        long sec = Math.max(0L, (ms + 999L) / 1000L);
        long h = sec / 3600, m = (sec % 3600) / 60, ss = sec % 60;
        return h > 0 ? String.format(java.util.Locale.ROOT, "%d:%02d:%02d", h, m, ss)
                : String.format(java.util.Locale.ROOT, "%d:%02d", m, ss);
    }

    static List<ScreenTime.Task> firstN(List<ScreenTime.Task> list, int n) {
        return list.size() <= n ? list : list.subList(0, n);
    }
}

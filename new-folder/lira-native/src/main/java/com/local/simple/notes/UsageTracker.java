package com.local.simple.notes;

import android.app.usage.UsageEvents;
import android.app.usage.UsageStatsManager;

import java.util.Calendar;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Map;

/**
 * Today's foreground time per app, computed from the system usage events the same way
 * Android's own screen-time screen does: from an activity being resumed until it is
 * paused, the screen goes off or the lock screen appears. Counting starts at local midnight.
 *
 * update() is cheap after the first call: it only reads the events of the last few seconds.
 * Not thread-safe; the service uses it from one thread.
 */
final class UsageTracker {
    static final int RESUMED = 1;          // UsageEvents.Event.ACTIVITY_RESUMED
    static final int PAUSED = 2;           // UsageEvents.Event.ACTIVITY_PAUSED
    static final int SCREEN_OFF = 16;      // UsageEvents.Event.SCREEN_NON_INTERACTIVE
    static final int KEYGUARD_SHOWN = 17;  // UsageEvents.Event.KEYGUARD_SHOWN
    static final int STOPPED = 23;         // UsageEvents.Event.ACTIVITY_STOPPED
    static final int SHUTDOWN = 26;        // UsageEvents.Event.DEVICE_SHUTDOWN

    /** How far before midnight the first scan looks, to find an app that was already open. */
    static final long LOOKBACK = 12L * 3600_000L;
    /** Each update re-reads this much of the previous window, in case an event is written late. */
    static final long OVERLAP = 4000L;

    private final UsageStatsManager usm;
    private long dayStart = Long.MIN_VALUE;
    private long lastEnd;
    private final HashMap<String, Long> total = new HashMap<String, Long>();
    private final HashMap<String, Long> since = new HashMap<String, Long>();
    private final HashMap<String, HashSet<String>> open = new HashMap<String, HashSet<String>>();
    private final HashMap<String, Long> seen = new HashMap<String, Long>();
    private String fg;

    UsageTracker(UsageStatsManager usm) { this.usm = usm; }

    static long startOfDay(long now) {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(now);
        c.set(Calendar.HOUR_OF_DAY, 0);
        c.set(Calendar.MINUTE, 0);
        c.set(Calendar.SECOND, 0);
        c.set(Calendar.MILLISECOND, 0);
        return c.getTimeInMillis();
    }

    long dayStart() { return dayStart; }

    /** The app whose activity is in front right now, or null (home screen counts as an app). */
    String foreground() { return fg; }

    void update(long now) {
        long ds = startOfDay(now);
        if (ds != dayStart || now < lastEnd - 60_000L) {
            reset(ds);
            feed(ds - LOOKBACK, now);
        } else {
            feed(Math.max(ds - LOOKBACK, lastEnd - OVERLAP), now);
        }
        lastEnd = now;
    }

    void reset(long ds) {
        dayStart = ds;
        total.clear();
        since.clear();
        open.clear();
        seen.clear();
        fg = null;
    }

    private void feed(long from, long to) {
        if (usm != null && to > from) {
            UsageEvents ev = usm.queryEvents(from, to);
            if (ev != null) {
                UsageEvents.Event e = new UsageEvents.Event();
                while (ev.hasNextEvent()) {
                    if (!ev.getNextEvent(e)) break;
                    event(e.getEventType(), e.getTimeStamp(), e.getPackageName(), e.getClassName());
                }
            }
        }
        prune(to - OVERLAP);
    }

    /** Drops remembered event keys that the next update can no longer return. */
    void prune(long before) {
        Iterator<Map.Entry<String, Long>> it = seen.entrySet().iterator();
        while (it.hasNext()) if (it.next().getValue() < before) it.remove();
    }

    void event(int type, long ts, String pkg, String cls) {
        if (type != RESUMED && type != PAUSED && type != STOPPED
                && type != SCREEN_OFF && type != KEYGUARD_SHOWN && type != SHUTDOWN) return;
        if (cls == null) cls = "";
        String key = ts + "|" + type + "|" + pkg + "|" + cls;
        if (seen.containsKey(key)) return;
        seen.put(key, ts);
        if (type == SCREEN_OFF || type == KEYGUARD_SHOWN || type == SHUTDOWN) {
            closeAll(ts);
            return;
        }
        if (pkg == null) return;
        if (type == RESUMED) {
            // One app in front at a time: a newly resumed app ends the previous one even if its
            // pause event was lost or arrives later.
            if (fg != null && !fg.equals(pkg)) close(fg, ts);
            HashSet<String> s = open.get(pkg);
            if (s == null) {
                s = new HashSet<String>();
                open.put(pkg, s);
            }
            if (!since.containsKey(pkg)) since.put(pkg, ts);
            s.add(cls);
            fg = pkg;
        } else {
            // Paused or stopped: the app leaves the front once none of its activities are resumed.
            // Inside one app, B is resumed before A is stopped, so A's stop must not end the session.
            HashSet<String> s = open.get(pkg);
            if (s != null && s.remove(cls) && s.isEmpty()) close(pkg, ts);
        }
    }

    private void close(String pkg, long ts) {
        Long st = since.remove(pkg);
        open.remove(pkg);
        if (st != null) add(pkg, st, ts);
        if (pkg.equals(fg)) fg = null;
    }

    private void closeAll(long ts) {
        for (Map.Entry<String, Long> e : since.entrySet()) add(e.getKey(), e.getValue(), ts);
        since.clear();
        open.clear();
        fg = null;
    }

    private void add(String pkg, long start, long end) {
        long a = Math.max(start, dayStart);
        if (end <= a) return;
        Long t = total.get(pkg);
        total.put(pkg, (t == null ? 0L : t) + (end - a));
    }

    /** Milliseconds in front today, including the session that is still going on. */
    long usage(String pkg, long now) {
        Long t = total.get(pkg);
        long r = t == null ? 0L : t;
        Long st = since.get(pkg);
        if (st != null) r += Math.max(0L, now - Math.max(st, dayStart));
        return r;
    }

    Map<String, Long> snapshot(long now) {
        HashMap<String, Long> out = new HashMap<String, Long>();
        for (String p : total.keySet()) out.put(p, usage(p, now));
        for (String p : since.keySet()) out.put(p, usage(p, now));
        return out;
    }
}

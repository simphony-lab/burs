package com.local.simple.notes;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.app.usage.UsageStatsManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.os.Build;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.IBinder;
import android.os.Looper;
import android.os.PowerManager;
import android.util.Log;

import java.util.HashMap;
import java.util.Map;

/**
 * Runs in its own ":screen" process, so nothing here can take Lira's main screen down.
 * Once a second while the screen is on it checks which app is in front; for an app with a
 * daily limit it shows the pill with today's minutes.
 */
public class ScreenTimeService extends Service {
    static final String CHANNEL = "lira_screen_time";
    static final int NOTE_ID = 0x5717;
    static final long TICK_MS = 1000L;

    private Handler main;
    private Handler work;
    private HandlerThread thread;
    private UsageTracker tracker;
    private ScreenTimeOverlay overlay;   // the 7.4 pill (when the island is off)
    private IslandOverlay island;        // main thread only
    private volatile boolean usageOk;
    /** Ticks made on the island that Lira has not taken over yet: task key -> done. */
    private final java.util.concurrent.ConcurrentHashMap<String, Boolean> pending = new java.util.concurrent.ConcurrentHashMap<String, Boolean>();
    static final String PENDING = "island_pending.json";
    private volatile ScreenTime.Config cfg = new ScreenTime.Config();
    private volatile boolean alive;
    private volatile boolean screenOn = true;
    private BroadcastReceiver screenRx;
    private int ticks;

    // Work thread only.
    private final HashMap<String, String> labels = new HashMap<String, String>();
    private final HashMap<String, Bitmap> icons = new HashMap<String, Bitmap>();

    @Override public IBinder onBind(Intent intent) { return null; }

    private static volatile ScreenTimeService self;

    /** The accessibility service came or went: move the island to the right window type. */
    static void hostChanged() {
        final ScreenTimeService s = self;
        if (s == null || s.main == null) return;
        s.main.post(new Runnable() { @Override public void run() { s.rebuildIsland(); } });
    }

    private IslandOverlay newIsland() {
        IslandAccessibility a = IslandAccessibility.instance;
        return a != null ? new IslandOverlay(a, islandListener, true) : new IslandOverlay(this, islandListener, false);
    }

    private void rebuildIsland() {
        if (!alive || !cfg.island) return;
        boolean wantA11y = IslandAccessibility.instance != null;
        if (island != null && !island.isDead() && island.isA11y() == wantA11y) return;
        if (island != null) island.destroy();
        island = newIsland();
        island.setConfig(cfg);
        kick();
    }

    @Override public void onCreate() {
        super.onCreate();
        main = new Handler(Looper.getMainLooper());
        self = this;
        thread = new HandlerThread("lira-screen-time");
        thread.start();
        work = new Handler(thread.getLooper());
        tracker = new UsageTracker((UsageStatsManager) getSystemService(Context.USAGE_STATS_SERVICE));
        try {
            PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
            screenOn = pm == null || pm.isInteractive();
        } catch (Throwable ignored) {}
        screenRx = new BroadcastReceiver() {
            @Override public void onReceive(Context c, Intent i) {
                if (Intent.ACTION_SCREEN_OFF.equals(i.getAction())) {
                    screenOn = false;
                    if (overlay != null) overlay.hide();
                    if (island != null) island.collapse();
                } else {
                    screenOn = true;
                    kick();
                }
            }
        };
        IntentFilter f = new IntentFilter();
        f.addAction(Intent.ACTION_SCREEN_ON);
        f.addAction(Intent.ACTION_SCREEN_OFF);
        f.addAction(Intent.ACTION_USER_PRESENT);
        try {
            registerReceiver(screenRx, f);
        } catch (Throwable t) {
            Log.w(ScreenTime.TAG, "receiver", t);
            screenRx = null;
        }
        loadPending();
    }

    @Override public void onConfigurationChanged(android.content.res.Configuration c) {
        super.onConfigurationChanged(c);
        if (island != null) island.onConfigurationChanged();
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        ScreenTime.Config c = ScreenTime.parse(ScreenTime.read(this));
        cfg = c;
        // Always go foreground first: that is what startForegroundService() requires.
        foreground();
        if (!ScreenTime.wanted(this, c)) {
            shutdown();
            return START_NOT_STICKY;
        }
        alive = true;
        usageOk = ScreenTime.hasUsageAccess(this);
        prunePending(c);
        if (c.island) {
            if (overlay != null) { overlay.destroy(); overlay = null; }
            if (island != null && !island.isDead() && island.isA11y() != (IslandAccessibility.instance != null)) island.destroy();
            if (island == null || island.isDead()) island = newIsland();
            island.setConfig(c);
        } else {
            if (island != null) { island.destroy(); island = null; }
            if (overlay == null || overlay.isDead()) overlay = new ScreenTimeOverlay(this);
            overlay.setConfig(c);
        }
        kick();
        return START_STICKY;
    }

    @Override public void onDestroy() {
        alive = false;
        if (self == this) self = null;
        if (screenRx != null) {
            try { unregisterReceiver(screenRx); } catch (Throwable ignored) {}
            screenRx = null;
        }
        if (work != null) work.removeCallbacksAndMessages(null);
        if (thread != null) thread.quitSafely();
        if (overlay != null) overlay.destroy();
        if (island != null) island.destroy();
        super.onDestroy();
    }

    private void shutdown() {
        alive = false;
        if (work != null) work.removeCallbacksAndMessages(null);
        if (overlay != null) overlay.destroy();
        if (island != null) island.destroy();
        try { stopForeground(true); } catch (Throwable ignored) {}
        stopSelf();
    }

    private void kick() {
        if (!alive || work == null) return;
        work.removeCallbacks(tick);
        work.post(tick);
    }

    private final Runnable tick = new Runnable() {
        @Override public void run() {
            if (!alive) return;
            if (!screenOn) {
                if (!cfg.island) post(null, null, null, 0, 0, 0);
                return; // ACTION_SCREEN_ON starts the loop again
            }
            try {
                Context c = ScreenTimeService.this;
                if (++ticks % 30 == 0) {
                    usageOk = ScreenTime.hasUsageAccess(c);
                    if (!ScreenTime.wanted(c, cfg)) {
                        main.post(new Runnable() { @Override public void run() { shutdown(); } });
                        return;
                    }
                }
                long now = System.currentTimeMillis();
                String fg = null;
                long used = 0;
                if (cfg.limitsOn() && usageOk) {
                    tracker.update(now);
                    fg = tracker.foreground();
                    if (fg != null && (fg.equals(getPackageName()) || !cfg.limits.containsKey(fg))) fg = null;
                    if (fg != null) used = tracker.usage(fg, now);
                }
                if (cfg.island) {
                    final IslandSnapshot snap = IslandSnapshot.compute(cfg, pending, now, fg,
                            fg == null ? null : label(fg), fg == null ? null : icon(fg), used);
                    main.post(new Runnable() {
                        @Override public void run() {
                            IslandOverlay o = island;
                            if (o == null || !alive) return;
                            try { o.update(snap); } catch (Throwable t) { Log.w(ScreenTime.TAG, "island", t); }
                        }
                    });
                } else if (fg != null) {
                    post(fg, label(fg), icon(fg), used, cfg.limits.get(fg) * 60_000L, tracker.dayStart());
                } else {
                    post(null, null, null, 0, 0, 0);
                }
            } catch (Throwable t) {
                Log.w(ScreenTime.TAG, "tick", t);
            }
            if (alive) work.postDelayed(this, TICK_MS);
        }
    };

    private final IslandOverlay.Listener islandListener = new IslandOverlay.Listener() {
        @Override public void onToggle(final String key, final boolean done) {
            pending.put(key, done);
            if (work != null) {
                work.post(new Runnable() {
                    @Override public void run() {
                        ScreenTime.inboxWrite(ScreenTimeService.this, key, done);
                        savePending();
                    }
                });
            }
            kick();
        }

        @Override public void onOpenApp() {
            try {
                Intent i = getPackageManager().getLaunchIntentForPackage(getPackageName());
                if (i == null) return;
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED);
                startActivity(i);
            } catch (Throwable t) {
                Log.w(ScreenTime.TAG, "open", t);
            }
        }
    };

    private void loadPending() {
        try {
            java.io.File f = new java.io.File(getFilesDir(), PENDING);
            if (!f.isFile()) return;
            java.io.FileInputStream in = new java.io.FileInputStream(f);
            java.io.ByteArrayOutputStream b = new java.io.ByteArrayOutputStream();
            try {
                byte[] buf = new byte[2048];
                int n;
                while ((n = in.read(buf)) > 0) b.write(buf, 0, n);
            } finally {
                in.close();
            }
            org.json.JSONObject o = new org.json.JSONObject(new String(b.toByteArray(), "UTF-8"));
            java.util.Iterator<String> it = o.keys();
            while (it.hasNext()) {
                String k = it.next();
                pending.put(k, o.optBoolean(k));
            }
        } catch (Throwable t) {
            Log.w(ScreenTime.TAG, "pending", t);
        }
    }

    private synchronized void savePending() {
        try {
            org.json.JSONObject o = new org.json.JSONObject();
            for (java.util.Map.Entry<String, Boolean> e : pending.entrySet()) o.put(e.getKey(), (boolean) e.getValue());
            java.io.File dir = getFilesDir(), tmp = new java.io.File(dir, PENDING + ".tmp");
            java.io.FileOutputStream out = new java.io.FileOutputStream(tmp);
            try {
                out.write(o.toString().getBytes("UTF-8"));
            } finally {
                out.close();
            }
            tmp.renameTo(new java.io.File(dir, PENDING));
        } catch (Throwable t) {
            Log.w(ScreenTime.TAG, "pending save", t);
        }
    }

    /** Forgets island ticks that Lira already took over (or tasks that are gone). */
    private void prunePending(ScreenTime.Config c) {
        if (pending.isEmpty()) return;
        java.util.HashMap<String, Boolean> state = new java.util.HashMap<String, Boolean>();
        for (ScreenTime.Task t : c.tasks) state.put(t.key, t.done);
        boolean changed = false;
        for (String k : new java.util.ArrayList<String>(pending.keySet())) {
            Boolean d = state.get(k);
            if (d == null || d.equals(pending.get(k))) { pending.remove(k); changed = true; }
        }
        if (changed && work != null) {
            work.post(new Runnable() { @Override public void run() { savePending(); } });
        }
    }

    Map<String, Boolean> pendingForTest() { return pending; }

    private void post(final String pkg, final String label, final Bitmap icon, final long used, final long limit, final long day) {
        main.post(new Runnable() {
            @Override public void run() {
                ScreenTimeOverlay o = overlay;
                if (o == null || !alive) return;
                try {
                    if (pkg == null) o.hide();
                    else o.show(pkg, label, icon, used, limit, day);
                } catch (Throwable t) {
                    Log.w(ScreenTime.TAG, "overlay", t);
                }
            }
        });
    }

    private String label(String pkg) {
        String l = labels.get(pkg);
        if (l != null) return l;
        try {
            PackageManager pm = getPackageManager();
            l = pm.getApplicationLabel(pm.getApplicationInfo(pkg, 0)).toString();
        } catch (Throwable t) {
            l = pkg;
        }
        labels.put(pkg, l);
        return l;
    }

    private Bitmap icon(String pkg) {
        if (icons.containsKey(pkg)) return icons.get(pkg);
        Bitmap b = null;
        try {
            int size = Math.round(32 * getResources().getDisplayMetrics().density);
            b = ScreenTime.bitmap(getPackageManager().getApplicationIcon(pkg), Math.max(32, size));
        } catch (Throwable ignored) {}
        icons.put(pkg, b);
        return b;
    }

    private void foreground() {
        try {
            Notification.Builder b;
            if (Build.VERSION.SDK_INT >= 26) {
                NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
                NotificationChannel ch = new NotificationChannel(CHANNEL, "Экранное время", NotificationManager.IMPORTANCE_MIN);
                ch.setDescription("Подсчёт минут в приложениях с дневным лимитом");
                ch.setShowBadge(false);
                nm.createNotificationChannel(ch);
                b = new Notification.Builder(this, CHANNEL);
            } else {
                b = new Notification.Builder(this);
                b.setPriority(Notification.PRIORITY_MIN);
            }
            int n = cfg.limits.size();
            Intent open = getPackageManager().getLaunchIntentForPackage(getPackageName());
            if (open == null) open = new Intent(Intent.ACTION_MAIN).setPackage(getPackageName());
            b.setSmallIcon(android.R.drawable.ic_menu_recent_history)
                    .setContentTitle(cfg.island ? "Динамический остров" : "Экранное время")
                    .setContentText(n > 0 && cfg.enabled ? "Лимиты для " + n + " " + ScreenTime.appsGenitive(n)
                            : cfg.island ? "Задачи, лимиты и комендантский час" : "Подсчёт времени в приложениях")
                    .setOngoing(true)
                    .setShowWhen(false)
                    .setCategory(Notification.CATEGORY_SERVICE)
                    .setContentIntent(PendingIntent.getActivity(this, 0x5717, open,
                            PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT));
            startForeground(NOTE_ID, b.build());
        } catch (Throwable t) {
            Log.w(ScreenTime.TAG, "foreground", t);
        }
    }
}

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
    private ScreenTimeOverlay overlay;
    private volatile ScreenTime.Config cfg = new ScreenTime.Config();
    private volatile boolean alive;
    private volatile boolean screenOn = true;
    private BroadcastReceiver screenRx;
    private int ticks;

    // Work thread only.
    private final HashMap<String, String> labels = new HashMap<String, String>();
    private final HashMap<String, Bitmap> icons = new HashMap<String, Bitmap>();

    @Override public IBinder onBind(Intent intent) { return null; }

    @Override public void onCreate() {
        super.onCreate();
        main = new Handler(Looper.getMainLooper());
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
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        ScreenTime.Config c = ScreenTime.parse(ScreenTime.read(this));
        cfg = c;
        // Always go foreground first: that is what startForegroundService() requires.
        foreground();
        if (!c.active() || !ScreenTime.hasUsageAccess(this) || !ScreenTime.canOverlay(this)) {
            shutdown();
            return START_NOT_STICKY;
        }
        alive = true;
        if (overlay == null || overlay.isDead()) overlay = new ScreenTimeOverlay(this);
        overlay.setConfig(c);
        kick();
        return START_STICKY;
    }

    @Override public void onDestroy() {
        alive = false;
        if (screenRx != null) {
            try { unregisterReceiver(screenRx); } catch (Throwable ignored) {}
            screenRx = null;
        }
        if (work != null) work.removeCallbacksAndMessages(null);
        if (thread != null) thread.quitSafely();
        if (overlay != null) overlay.destroy();
        super.onDestroy();
    }

    private void shutdown() {
        alive = false;
        if (work != null) work.removeCallbacksAndMessages(null);
        if (overlay != null) overlay.destroy();
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
                post(null, null, null, 0, 0, 0);
                return; // ACTION_SCREEN_ON starts the loop again
            }
            try {
                if (++ticks % 30 == 0) {
                    Context c = ScreenTimeService.this;
                    if (!ScreenTime.hasUsageAccess(c) || !ScreenTime.canOverlay(c)) {
                        main.post(new Runnable() { @Override public void run() { shutdown(); } });
                        return;
                    }
                }
                long now = System.currentTimeMillis();
                tracker.update(now);
                String fg = tracker.foreground();
                Integer lim = fg == null || fg.equals(getPackageName()) ? null : cfg.limits.get(fg);
                if (lim != null && lim > 0) {
                    post(fg, label(fg), icon(fg), tracker.usage(fg, now), lim * 60_000L, tracker.dayStart());
                } else {
                    post(null, null, null, 0, 0, 0);
                }
            } catch (Throwable t) {
                Log.w(ScreenTime.TAG, "tick", t);
            }
            if (alive) work.postDelayed(this, TICK_MS);
        }
    };

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
            int size = Math.round(16 * getResources().getDisplayMetrics().density);
            b = ScreenTime.bitmap(getPackageManager().getApplicationIcon(pkg), Math.max(16, size));
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
                    .setContentTitle("Экранное время")
                    .setContentText(n > 0 ? "Лимиты для " + n + " " + ScreenTime.appsGenitive(n) : "Подсчёт времени в приложениях")
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

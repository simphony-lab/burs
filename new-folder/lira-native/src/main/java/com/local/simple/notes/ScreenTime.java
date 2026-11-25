package com.local.simple.notes;

import android.app.Activity;
import android.app.AppOpsManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.drawable.Drawable;
import android.os.Build;
import android.os.Process;
import android.provider.Settings;
import android.util.Base64;
import android.util.Log;
import android.webkit.WebView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Iterator;
import java.util.LinkedHashMap;

/**
 * Screen-time limits: settings file and small helpers shared by the app process
 * (WebView bridge) and the ":screen" process (tracker service and overlay).
 *
 * The settings live in files/screentime.json. Lira's own data (localStorage of the
 * WebView) is never read or written here.
 */
public final class ScreenTime {
    static final String TAG = "LiraScreenTime";
    static final String FILE = "screentime.json";
    static final String ACTION_RELOAD = "com.local.simple.notes.SCREEN_TIME_RELOAD";
    static final int DEFAULT_ACCENT = 0xFFA3DFCB;

    private ScreenTime() {}

    /** Called from MainActivity.onCreate before the page loads. Never throws. */
    public static void attach(Activity activity, WebView web) {
        try {
            web.addJavascriptInterface(new ScreenTimeBridge(activity), "LiraST");
        } catch (Throwable t) {
            Log.w(TAG, "bridge", t);
        }
        try {
            final Context app = activity.getApplicationContext();
            new Thread(new Runnable() {
                @Override public void run() { sync(app); }
            }, "lira-st-sync").start();
        } catch (Throwable t) {
            Log.w(TAG, "sync", t);
        }
    }

    /** A dated to-do from Lira's day plan with its time window (epoch ms). */
    static final class Task {
        final String key, title;
        final long start, end;
        final boolean done;

        Task(String key, String title, long start, long end, boolean done) {
            this.key = key; this.title = title; this.start = start; this.end = end; this.done = done;
        }
    }

    static final class Config {
        boolean enabled = true;
        boolean compact = true;
        boolean hideFull = true;
        int pos = 0; // 0 centre, 1 left, 2 right
        int accent = DEFAULT_ACCENT;
        final LinkedHashMap<String, Integer> limits = new LinkedHashMap<String, Integer>();
        /** Dynamic island instead of the pill; idle = keep the black island visible when it has nothing to show. */
        boolean island = false;
        boolean islandIdle = true;
        /** Curfew windows [start, end] in epoch ms, sorted. */
        final ArrayList<long[]> curfew = new ArrayList<long[]>();
        final ArrayList<Task> tasks = new ArrayList<Task>();

        boolean limitsOn() { return enabled && !limits.isEmpty(); }

        /** Kept for the 7.4 pill logic and tests. */
        boolean active() { return limitsOn(); }
    }

    static Config parse(String json) {
        Config c = new Config();
        if (json == null || json.trim().isEmpty()) return c;
        try {
            JSONObject o = new JSONObject(json);
            c.enabled = o.optBoolean("enabled", true);
            c.compact = o.optBoolean("compact", true);
            c.hideFull = o.optBoolean("hideFull", true);
            c.pos = Math.max(0, Math.min(2, o.optInt("pos", 0)));
            String a = o.optString("accent", "");
            if (a.matches("#[0-9a-fA-F]{6}")) c.accent = 0xFF000000 | Integer.parseInt(a.substring(1), 16);
            JSONObject l = o.optJSONObject("limits");
            if (l != null) {
                Iterator<String> it = l.keys();
                while (it.hasNext()) {
                    String k = it.next();
                    int m = l.optInt(k, 0);
                    if (k.length() > 0 && m > 0 && m <= 1440) c.limits.put(k, m);
                }
            }
            JSONObject is = o.optJSONObject("island");
            if (is != null) {
                c.island = is.optBoolean("on", true);
                c.islandIdle = is.optBoolean("idle", true);
            }
            JSONArray cf = o.optJSONArray("curfew");
            if (cf != null) {
                for (int i = 0; i < cf.length() && i < 64; i++) {
                    JSONArray w = cf.optJSONArray(i);
                    if (w == null || w.length() < 2) continue;
                    long st = w.optLong(0, 0), en = w.optLong(1, 0);
                    if (st > 0 && en > st && en - st <= 24L * 3600_000L) c.curfew.add(new long[]{st, en});
                }
                Collections.sort(c.curfew, new Comparator<long[]>() {
                    @Override public int compare(long[] x, long[] y) { return x[0] < y[0] ? -1 : x[0] > y[0] ? 1 : 0; }
                });
            }
            JSONArray ts = o.optJSONArray("tasks");
            if (ts != null) {
                for (int i = 0; i < ts.length() && i < 500; i++) {
                    JSONObject t = ts.optJSONObject(i);
                    if (t == null) continue;
                    String k = t.optString("k", ""), title = t.optString("t", "").trim();
                    long st = t.optLong("s", 0), en = t.optLong("e", 0);
                    if (k.isEmpty() || title.isEmpty() || st <= 0 || en <= st) continue;
                    if (title.length() > 140) title = title.substring(0, 140);
                    c.tasks.add(new Task(k, title, st, en, t.optBoolean("d", false)));
                }
            }
        } catch (Exception e) {
            Log.w(TAG, "config", e);
        }
        return c;
    }

    static String read(Context c) {
        File f = new File(c.getFilesDir(), FILE);
        if (!f.isFile()) return "";
        FileInputStream in = null;
        try {
            in = new FileInputStream(f);
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buf = new byte[4096];
            int n;
            while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
            return new String(out.toByteArray(), "UTF-8");
        } catch (IOException e) {
            return "";
        } finally {
            if (in != null) try { in.close(); } catch (IOException ignored) {}
        }
    }

    static synchronized void write(Context c, String json) throws IOException {
        File dir = c.getFilesDir();
        File tmp = new File(dir, FILE + ".tmp");
        FileOutputStream out = new FileOutputStream(tmp);
        try {
            out.write(json.getBytes("UTF-8"));
            out.getFD().sync();
        } finally {
            out.close();
        }
        if (!tmp.renameTo(new File(dir, FILE))) throw new IOException("rename failed");
    }

    static boolean hasUsageAccess(Context c) {
        try {
            AppOpsManager ops = (AppOpsManager) c.getSystemService(Context.APP_OPS_SERVICE);
            if (ops == null) return false;
            int mode = Build.VERSION.SDK_INT >= 29
                    ? ops.unsafeCheckOpNoThrow(AppOpsManager.OPSTR_GET_USAGE_STATS, Process.myUid(), c.getPackageName())
                    : ops.checkOpNoThrow(AppOpsManager.OPSTR_GET_USAGE_STATS, Process.myUid(), c.getPackageName());
            if (mode == AppOpsManager.MODE_DEFAULT) {
                return c.checkCallingOrSelfPermission("android.permission.PACKAGE_USAGE_STATS") == PackageManager.PERMISSION_GRANTED;
            }
            return mode == AppOpsManager.MODE_ALLOWED;
        } catch (Throwable t) {
            return false;
        }
    }

    static boolean canOverlay(Context c) {
        try {
            return Settings.canDrawOverlays(c);
        } catch (Throwable t) {
            return false;
        }
    }

    /** Starts the tracker when it has limits and both permissions, stops it otherwise. Never throws. */
    static void sync(Context c) {
        try {
            Context app = c.getApplicationContext() != null ? c.getApplicationContext() : c;
            Config cfg = parse(read(app));
            Intent i = new Intent(app, ScreenTimeService.class).setAction(ACTION_RELOAD);
            if (wanted(app, cfg)) {
                if (Build.VERSION.SDK_INT >= 26) app.startForegroundService(i);
                else app.startService(i);
            } else {
                app.stopService(i);
            }
        } catch (Throwable t) {
            Log.w(TAG, "sync", t);
        }
    }

    /** Whether the tracker service has something to do with these settings and permissions. */
    static boolean wanted(Context c, Config cfg) {
        if (cfg.island) return canOverlay(c) || islandA11y(c);
        return canOverlay(c) && cfg.limitsOn() && hasUsageAccess(c);
    }

    /** Whether Lira's accessibility service (the "over everything" island) is switched on. */
    static boolean islandA11y(Context c) {
        try {
            if (Settings.Secure.getInt(c.getContentResolver(), Settings.Secure.ACCESSIBILITY_ENABLED, 0) != 1) return false;
            String list = Settings.Secure.getString(c.getContentResolver(), Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES);
            if (list == null) return false;
            ComponentName me = new ComponentName(c.getPackageName(), IslandAccessibility.class.getName());
            for (String part : list.split(":")) {
                ComponentName cn = ComponentName.unflattenFromString(part.trim());
                if (me.equals(cn)) return true;
            }
        } catch (Throwable ignored) {}
        return false;
    }

    // ---- island inbox: ticks made on the island, picked up by Lira when it opens ----------------
    static final String INBOX = "island_inbox";

    /** Records "task key is now done / not done" for Lira. One file per event, written atomically. */
    static void inboxWrite(Context c, String key, boolean done) {
        try {
            File dir = new File(c.getFilesDir(), INBOX);
            if (!dir.isDirectory() && !dir.mkdirs()) return;
            long now = System.currentTimeMillis();
            String name = String.format(java.util.Locale.ROOT, "e%015d_%04d", now, (int) (Math.random() * 10000));
            File tmp = new File(dir, name + ".tmp");
            FileOutputStream out = new FileOutputStream(tmp);
            try {
                out.write(new JSONObject().put("k", key).put("d", done).put("ts", now).toString().getBytes("UTF-8"));
                out.getFD().sync();
            } finally {
                out.close();
            }
            if (!tmp.renameTo(new File(dir, name + ".json"))) tmp.delete();
        } catch (Throwable t) {
            Log.w(TAG, "inbox", t);
        }
    }

    /** All events in order, removing them. */
    static JSONArray inboxTake(Context c) {
        JSONArray out = new JSONArray();
        File dir = new File(c.getFilesDir(), INBOX);
        File[] files = dir.listFiles();
        if (files == null) return out;
        java.util.Arrays.sort(files);
        for (File f : files) {
            if (!f.getName().endsWith(".json")) continue;
            try {
                FileInputStream in = new FileInputStream(f);
                try {
                    ByteArrayOutputStream b = new ByteArrayOutputStream();
                    byte[] buf = new byte[1024];
                    int n;
                    while ((n = in.read(buf)) > 0) b.write(buf, 0, n);
                    out.put(new JSONObject(new String(b.toByteArray(), "UTF-8")));
                } finally {
                    in.close();
                }
            } catch (Throwable t) {
                Log.w(TAG, "inbox read", t);
            }
            f.delete();
        }
        return out;
    }

    static Bitmap bitmap(Drawable d, int size) {
        Bitmap b = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(b);
        d.setBounds(0, 0, size, size);
        d.draw(canvas);
        return b;
    }

    static String pngDataUrl(Drawable d, int size) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        bitmap(d, size).compress(Bitmap.CompressFormat.PNG, 100, out);
        return "data:image/png;base64," + Base64.encodeToString(out.toByteArray(), Base64.NO_WRAP);
    }

    /** "приложения" / "приложений" after "для N". */
    static String appsGenitive(int n) {
        return (n % 10 == 1 && n % 100 != 11) ? "приложения" : "приложений";
    }
}

package com.local.simple.notes;

import android.app.Activity;
import android.app.AppOpsManager;
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

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
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

    static final class Config {
        boolean enabled = true;
        boolean compact = true;
        boolean hideFull = true;
        int pos = 0; // 0 centre, 1 left, 2 right
        int accent = DEFAULT_ACCENT;
        final LinkedHashMap<String, Integer> limits = new LinkedHashMap<String, Integer>();

        boolean active() { return enabled && !limits.isEmpty(); }
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
            if (cfg.active() && hasUsageAccess(app) && canOverlay(app)) {
                if (Build.VERSION.SDK_INT >= 26) app.startForegroundService(i);
                else app.startService(i);
            } else {
                app.stopService(i);
            }
        } catch (Throwable t) {
            Log.w(TAG, "sync", t);
        }
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

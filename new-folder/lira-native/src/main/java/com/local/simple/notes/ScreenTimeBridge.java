package com.local.simple.notes;

import android.app.Activity;
import android.app.usage.UsageStatsManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.net.Uri;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.provider.Settings;
import android.util.Log;
import android.webkit.JavascriptInterface;

import org.json.JSONArray;
import org.json.JSONObject;

import java.lang.ref.WeakReference;
import java.text.Collator;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** window.LiraST in the WebView. Every method returns plain strings/booleans and never throws. */
public class ScreenTimeBridge {
    private final Context app;
    private final WeakReference<Activity> activity;
    private final Handler main = new Handler(Looper.getMainLooper());

    ScreenTimeBridge(Activity a) {
        app = a.getApplicationContext();
        activity = new WeakReference<Activity>(a);
    }

    @JavascriptInterface
    public String status() {
        try {
            JSONObject o = new JSONObject();
            o.put("v", 1);
            o.put("usage", ScreenTime.hasUsageAccess(app));
            o.put("overlay", ScreenTime.canOverlay(app));
            boolean battery = false;
            try {
                PowerManager pm = (PowerManager) app.getSystemService(Context.POWER_SERVICE);
                battery = pm != null && pm.isIgnoringBatteryOptimizations(app.getPackageName());
            } catch (Throwable ignored) {}
            o.put("battery", battery);
            o.put("sdk", Build.VERSION.SDK_INT);
            return o.toString();
        } catch (Throwable t) {
            return "{}";
        }
    }

    @JavascriptInterface
    public void openUsage() {
        open(new Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS, Uri.fromParts("package", app.getPackageName(), null)),
                new Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS));
    }

    @JavascriptInterface
    public void openOverlay() {
        open(new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:" + app.getPackageName())),
                new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION));
    }

    @JavascriptInterface
    public void openBattery() {
        open(new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, Uri.parse("package:" + app.getPackageName())),
                new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS));
    }

    private void open(final Intent first, final Intent fallback) {
        main.post(new Runnable() {
            @Override public void run() {
                Activity a = activity.get();
                Context c = a != null && !a.isFinishing() ? a : app;
                for (Intent i : new Intent[]{first, fallback}) {
                    try {
                        if (c == app) i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                        c.startActivity(i);
                        return;
                    } catch (Throwable t) {
                        Log.w(ScreenTime.TAG, "open " + i.getAction(), t);
                    }
                }
            }
        });
    }

    /** Launchable apps except Lira: [{"p":package,"n":label}], sorted by label. */
    @JavascriptInterface
    public String apps() {
        try {
            PackageManager pm = app.getPackageManager();
            Intent launcher = new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER);
            List<ResolveInfo> list = pm.queryIntentActivities(launcher, 0);
            HashSet<String> seen = new HashSet<String>();
            final ArrayList<String[]> rows = new ArrayList<String[]>();
            for (ResolveInfo r : list) {
                if (r.activityInfo == null) continue;
                String p = r.activityInfo.packageName;
                if (p == null || p.equals(app.getPackageName()) || !seen.add(p)) continue;
                ApplicationInfo ai = r.activityInfo.applicationInfo;
                CharSequence label = ai != null ? ai.loadLabel(pm) : null;
                rows.add(new String[]{p, label == null ? p : label.toString()});
            }
            final Collator col = Collator.getInstance(new Locale("ru"));
            Collections.sort(rows, new Comparator<String[]>() {
                @Override public int compare(String[] a, String[] b) { return col.compare(a[1], b[1]); }
            });
            JSONArray out = new JSONArray();
            for (String[] r : rows) out.put(new JSONObject().put("p", r[0]).put("n", r[1]));
            return out.toString();
        } catch (Throwable t) {
            Log.w(ScreenTime.TAG, "apps", t);
            return "[]";
        }
    }

    /** The app's icon as a PNG data URL, or "" when it is not installed. */
    @JavascriptInterface
    public String icon(String pkg) {
        try {
            return ScreenTime.pngDataUrl(app.getPackageManager().getApplicationIcon(pkg), 96);
        } catch (Throwable t) {
            return "";
        }
    }

    /** Milliseconds in front today per app: {"package":ms}. "{}" without usage access. */
    @JavascriptInterface
    public String usage() {
        try {
            if (!ScreenTime.hasUsageAccess(app)) return "{}";
            UsageTracker t = new UsageTracker((UsageStatsManager) app.getSystemService(Context.USAGE_STATS_SERVICE));
            long now = System.currentTimeMillis();
            t.update(now);
            JSONObject o = new JSONObject();
            for (Map.Entry<String, Long> e : t.snapshot(now).entrySet()) {
                if (e.getValue() >= 1000L) o.put(e.getKey(), (long) e.getValue());
            }
            return o.toString();
        } catch (Throwable t) {
            Log.w(ScreenTime.TAG, "usage", t);
            return "{}";
        }
    }

    /** Ticks made on the island since the last call: [{"k":taskKey,"d":done,"ts":ms}], oldest first. */
    @JavascriptInterface
    public String takeInbox() {
        try {
            return ScreenTime.inboxTake(app).toString();
        } catch (Throwable t) {
            return "[]";
        }
    }

    @JavascriptInterface
    public String getConfig() {
        try {
            return ScreenTime.read(app);
        } catch (Throwable t) {
            return "";
        }
    }

    /** Saves the settings for the tracker and starts or stops it. */
    @JavascriptInterface
    public boolean setConfig(String json) {
        try {
            new JSONObject(json);
            ScreenTime.write(app, json);
            ScreenTime.sync(app);
            return true;
        } catch (Throwable t) {
            Log.w(ScreenTime.TAG, "setConfig", t);
            return false;
        }
    }
}

package com.local.simple.notes;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;
import static org.robolectric.Shadows.shadowOf;

import android.app.Activity;
import android.app.AppOpsManager;
import android.app.Application;
import android.app.Notification;
import android.app.usage.UsageEvents;
import android.app.usage.UsageStatsManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageInfo;
import android.content.pm.ResolveInfo;
import android.os.Build;
import android.os.HandlerThread;
import android.os.Looper;
import android.os.Process;
import android.view.View;
import android.view.WindowManager;
import android.webkit.WebView;

import org.robolectric.RuntimeEnvironment;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.android.controller.ServiceController;
import org.robolectric.annotation.Config;
import org.robolectric.shadows.ShadowLooper;
import org.robolectric.shadows.ShadowSettings;
import org.robolectric.shadows.ShadowUsageStatsManager;

import java.io.File;
import java.lang.reflect.Field;
import java.time.Duration;
import java.util.List;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = {23, 26, 29, 31, 35})
public class ScreenTimeAndroidTest {
    static final int OP_GET_USAGE_STATS = 43;
    Application app;
    String me;

    @Before public void setUp() {
        app = RuntimeEnvironment.getApplication();
        me = app.getPackageName();
        install("com.google.android.youtube", "YouTube");
        install("org.telegram.messenger", "Telegram");
        install("com.zhiliaoapp.musically", "TikTok");
    }

    void install(String pkg, String label) {
        ApplicationInfo ai = new ApplicationInfo();
        ai.packageName = pkg;
        ai.name = label;
        ai.nonLocalizedLabel = label;
        PackageInfo pi = new PackageInfo();
        pi.packageName = pkg;
        pi.applicationInfo = ai;
        shadowOf(app.getPackageManager()).installPackage(pi);
        ActivityInfo act = new ActivityInfo();
        act.packageName = pkg;
        act.name = pkg + ".Main";
        act.applicationInfo = ai;
        act.nonLocalizedLabel = label;
        ResolveInfo ri = new ResolveInfo();
        ri.activityInfo = act;
        ri.nonLocalizedLabel = label;
        shadowOf(app.getPackageManager()).addResolveInfoForIntent(
                new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER), ri);
        shadowOf(app.getPackageManager()).setApplicationIcon(pkg, new android.graphics.drawable.ColorDrawable(0xFFFF0033));
    }

    void grant(boolean usage, boolean overlay) {
        AppOpsManager ops = (AppOpsManager) app.getSystemService(Context.APP_OPS_SERVICE);
        shadowOf(ops).setMode(OP_GET_USAGE_STATS, Process.myUid(), me,
                usage ? AppOpsManager.MODE_ALLOWED : AppOpsManager.MODE_IGNORED);
        ShadowSettings.setCanDrawOverlays(overlay);
    }

    void event(String pkg, String cls, int type, long ts) {
        UsageStatsManager usm = (UsageStatsManager) app.getSystemService(Context.USAGE_STATS_SERVICE);
        shadowOf(usm).addEvent(ShadowUsageStatsManager.EventBuilder.buildEvent()
                .setPackage(pkg).setClass(cls).setEventType(type).setTimeStamp(ts).build());
    }

    ScreenTimeBridge bridge() {
        Activity a = Robolectric.buildActivity(Activity.class).setup().get();
        return new ScreenTimeBridge(a);
    }

    void writeConfig(String json) throws Exception {
        ScreenTime.write(app, json);
    }

    @Test public void configParsing() {
        ScreenTime.Config c = ScreenTime.parse("{\"enabled\":true,\"compact\":false,\"hideFull\":false,\"pos\":7,\"accent\":\"#62d9ff\","
                + "\"limits\":{\"a\":30,\"b\":0,\"c\":5000,\"d\":\"x\",\"e\":90}}");
        assertFalse(c.compact);
        assertFalse(c.hideFull);
        assertEquals(2, c.pos);
        assertEquals(0xFF62D9FF, c.accent);
        assertEquals(2, c.limits.size());
        assertEquals(30, (int) c.limits.get("a"));
        assertEquals(90, (int) c.limits.get("e"));
        assertTrue(c.active());
        ScreenTime.Config d = ScreenTime.parse("not json");
        assertTrue(d.enabled);
        assertFalse(d.active());
        assertFalse(ScreenTime.parse("").active());
        assertEquals("приложения", ScreenTime.appsGenitive(1));
        assertEquals("приложений", ScreenTime.appsGenitive(2));
        assertEquals("приложений", ScreenTime.appsGenitive(11));
        assertEquals("приложения", ScreenTime.appsGenitive(21));
    }

    @Test public void attachNeverThrowsAndAddsBridge() {
        Activity a = Robolectric.buildActivity(Activity.class).setup().get();
        WebView w = new WebView(a);
        ScreenTime.attach(a, w);
        ScreenTime.attach(null, null); // must swallow everything
    }

    @Test public void bridgeStatusAndPermissions() throws Exception {
        ScreenTimeBridge b = bridge();
        grant(false, false);
        JSONObject s = new JSONObject(b.status());
        assertFalse(s.getBoolean("usage"));
        assertFalse(s.getBoolean("overlay"));
        assertEquals(Build.VERSION.SDK_INT, s.getInt("sdk"));
        grant(true, true);
        s = new JSONObject(b.status());
        assertTrue(s.getBoolean("usage"));
        assertTrue(s.getBoolean("overlay"));
        b.openUsage();
        b.openOverlay();
        b.openBattery();
        ShadowLooper.idleMainLooper();
        Intent started = shadowOf(app).getNextStartedActivity();
        assertNotNull(started);
    }

    @Test public void bridgeAppsIconsUsage() throws Exception {
        ScreenTimeBridge b = bridge();
        JSONArray apps = new JSONArray(b.apps());
        assertEquals(3, apps.length());
        assertEquals("Telegram", apps.getJSONObject(0).getString("n"));
        assertEquals("TikTok", apps.getJSONObject(1).getString("n"));
        assertEquals("YouTube", apps.getJSONObject(2).getString("n"));
        assertTrue(b.icon("com.google.android.youtube").startsWith("data:image/png;base64,"));
        assertEquals("", b.icon("no.such.app"));

        grant(false, false);
        assertEquals("{}", b.usage());
        grant(true, true);
        long now = System.currentTimeMillis();
        event("com.google.android.youtube", "Main", UsageEvents.Event.MOVE_TO_FOREGROUND, now - 120_000);
        event("com.google.android.youtube", "Main", UsageEvents.Event.MOVE_TO_BACKGROUND, now - 60_000);
        event("org.telegram.messenger", "Chat", UsageEvents.Event.MOVE_TO_FOREGROUND, now - 30_000);
        JSONObject u = new JSONObject(b.usage());
        assertEquals(60_000, u.getLong("com.google.android.youtube"));
        long tg = u.getLong("org.telegram.messenger");
        assertTrue("telegram " + tg, tg >= 30_000 && tg < 40_000);
    }

    @Test public void setConfigWritesFileAndStartsOrStopsService() throws Exception {
        ScreenTimeBridge b = bridge();
        grant(true, true);
        assertTrue(b.setConfig("{\"limits\":{\"com.google.android.youtube\":30}}"));
        assertTrue(new File(app.getFilesDir(), ScreenTime.FILE).isFile());
        assertEquals("{\"limits\":{\"com.google.android.youtube\":30}}", b.getConfig());
        Intent i = shadowOf(app).getNextStartedService();
        assertNotNull(i);
        assertEquals(new ComponentName(app, ScreenTimeService.class), i.getComponent());
        assertFalse(b.setConfig("{broken"));
        // Without limits the service is stopped, not started.
        assertTrue(b.setConfig("{\"limits\":{}}"));
        assertNull(shadowOf(app).getNextStartedService());
        Intent stopped = shadowOf(app).getNextStoppedService();
        assertNotNull(stopped);
        // Without permissions it is not started either.
        grant(false, true);
        assertTrue(b.setConfig("{\"limits\":{\"com.google.android.youtube\":30}}"));
        assertNull(shadowOf(app).getNextStartedService());
    }

    @Test public void bootReceiverStartsTracker() throws Exception {
        grant(true, true);
        writeConfig("{\"limits\":{\"com.google.android.youtube\":30}}");
        new ScreenTimeBoot().onReceive(app, new Intent(Intent.ACTION_BOOT_COMPLETED));
        assertNotNull(shadowOf(app).getNextStartedService());
        new ScreenTimeBoot().onReceive(app, new Intent("something.else"));
        assertNull(shadowOf(app).getNextStartedService());
        new ScreenTimeBoot().onReceive(app, null);
    }

    static Object field(Object o, String name) throws Exception {
        Field f = o.getClass().getDeclaredField(name);
        f.setAccessible(true);
        return f.get(o);
    }

    void runTicks(ScreenTimeService s, int n) throws Exception {
        HandlerThread th = (HandlerThread) field(s, "thread");
        for (int i = 0; i < n; i++) {
            shadowOf(th.getLooper()).idle();
            ShadowLooper.idleMainLooper();
            shadowOf(th.getLooper()).idleFor(Duration.ofMillis(1000));
            ShadowLooper.idleMainLooper(1000, java.util.concurrent.TimeUnit.MILLISECONDS);
        }
    }

    @Test public void serviceShowsPillForLimitedAppOnly() throws Exception {
        grant(true, true);
        writeConfig("{\"limits\":{\"com.google.android.youtube\":30,\"org.telegram.messenger\":10}}");
        long now = System.currentTimeMillis();
        event("org.telegram.messenger", "Chat", UsageEvents.Event.MOVE_TO_FOREGROUND, now - 40 * 60_000L);
        event("org.telegram.messenger", "Chat", UsageEvents.Event.MOVE_TO_BACKGROUND, now - 29 * 60_000L);
        event("com.google.android.youtube", "Main", UsageEvents.Event.MOVE_TO_FOREGROUND, now - 12 * 60_000L);

        ServiceController<ScreenTimeService> sc = Robolectric.buildService(ScreenTimeService.class,
                new Intent(ScreenTime.ACTION_RELOAD)).create().startCommand(0, 1);
        ScreenTimeService s = sc.get();
        Notification n = shadowOf(s).getLastForegroundNotification();
        assertNotNull(n);
        assertTrue(shadowOf(n).getContentText().toString().contains("2 приложений"));
        HandlerThread th = (HandlerThread) field(s, "thread");
        shadowOf(th.getLooper()).idle();
        ShadowLooper.idleMainLooper();

        ScreenTimeOverlay o = (ScreenTimeOverlay) field(s, "overlay");
        assertTrue(o.isAttached());
        assertTrue(o.isShown());
        assertEquals("YouTube", o.nameText().toString());
        assertEquals("12 / 30 мин", o.valueText().toString());
        WindowManager.LayoutParams lp = (WindowManager.LayoutParams) o.view().getLayoutParams();
        assertTrue((lp.flags & WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE) != 0);
        assertTrue((lp.flags & WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE) != 0);
        if (Build.VERSION.SDK_INT >= 31) assertTrue(lp.alpha <= 0.8f + 1e-6);
        assertEquals(Build.VERSION.SDK_INT >= 26 ? WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
                : WindowManager.LayoutParams.TYPE_PHONE, lp.type);

        // Collapses to the counter after a few seconds.
        ShadowLooper.idleMainLooper(5, java.util.concurrent.TimeUnit.SECONDS);
        runTicks(s, 1);
        assertFalse(o.isExpanded());
        assertEquals("12/30", o.valueText().toString());

        // Home screen (no limit): pill goes away and the window is removed.
        event("com.android.launcher", "Home", UsageEvents.Event.MOVE_TO_FOREGROUND, System.currentTimeMillis());
        runTicks(s, 2);
        assertFalse(o.isShown());
        assertFalse(o.isAttached());

        // Lira itself is never tracked.
        event(me, "MainActivity", UsageEvents.Event.MOVE_TO_FOREGROUND, System.currentTimeMillis());
        runTicks(s, 1);
        assertFalse(o.isShown());

        // Over the limit: expands, red, "Лимит исчерпан".
        event("org.telegram.messenger", "Chat", UsageEvents.Event.MOVE_TO_FOREGROUND, System.currentTimeMillis());
        runTicks(s, 1);
        assertTrue(o.isShown());
        assertTrue(o.isExpanded());
        assertEquals("Лимит исчерпан", o.nameText().toString());
        assertEquals("11 / 10 мин", o.valueText().toString());

        // Screen off hides it.
        app.sendBroadcast(new Intent(Intent.ACTION_SCREEN_OFF));
        ShadowLooper.idleMainLooper();
        runTicks(s, 1);
        assertFalse(o.isShown());

        sc.destroy();
        assertTrue(o.isDead());
        assertFalse(o.isAttached());
    }

    @Test public void serviceStopsItselfWithoutPermission() throws Exception {
        grant(false, false);
        writeConfig("{\"limits\":{\"com.google.android.youtube\":30}}");
        ServiceController<ScreenTimeService> sc = Robolectric.buildService(ScreenTimeService.class).create().startCommand(0, 1);
        assertTrue(shadowOf(sc.get()).isStoppedBySelf());
    }

    @Test public void serviceStopsItselfWithoutLimits() throws Exception {
        grant(true, true);
        ServiceController<ScreenTimeService> sc = Robolectric.buildService(ScreenTimeService.class).create().startCommand(0, 1);
        assertTrue(shadowOf(sc.get()).isStoppedBySelf());
        // and survives a null intent restart
        ServiceController<ScreenTimeService> sc2 = Robolectric.buildService(ScreenTimeService.class, (Intent) null).create();
        sc2.get().onStartCommand(null, 0, 2);
        sc2.destroy();
    }

    @Test public void overlayThresholdsAndConfig() {
        ScreenTimeOverlay o = new ScreenTimeOverlay(app);
        long day = UsageTracker.startOfDay(System.currentTimeMillis());
        ScreenTime.Config c = new ScreenTime.Config();
        o.setConfig(c);
        o.show("p", "Игра", null, 5 * 60_000L, 30 * 60_000L, day);
        assertTrue(o.isExpanded());
        assertEquals("5 / 30 мин", o.valueText().toString());
        ShadowLooper.idleMainLooper(5, java.util.concurrent.TimeUnit.SECONDS);
        assertFalse(o.isExpanded());
        // Crossing 80% expands again once.
        o.show("p", "Игра", null, 24 * 60_000L, 30 * 60_000L, day);
        assertTrue(o.isExpanded());
        ShadowLooper.idleMainLooper(7, java.util.concurrent.TimeUnit.SECONDS);
        assertFalse(o.isExpanded());
        o.show("p", "Игра", null, 25 * 60_000L, 30 * 60_000L, day);
        assertFalse(o.isExpanded());
        // Not compact: always expanded.
        ScreenTime.Config full = ScreenTime.parse("{\"compact\":false,\"pos\":2}");
        o.setConfig(full);
        assertTrue(o.isExpanded());
        ShadowLooper.idleMainLooper(10, java.util.concurrent.TimeUnit.SECONDS);
        assertTrue(o.isExpanded());
        WindowManager.LayoutParams lp = (WindowManager.LayoutParams) o.view().getLayoutParams();
        assertEquals(android.view.Gravity.RIGHT, lp.gravity & android.view.Gravity.HORIZONTAL_GRAVITY_MASK);
        o.hide();
        ShadowLooper.idleMainLooper(1, java.util.concurrent.TimeUnit.SECONDS);
        assertFalse(o.isAttached());
        o.destroy();
        o.show("p", "Игра", null, 1, 1, day); // after destroy: ignored
        assertFalse(o.isAttached());
    }
}

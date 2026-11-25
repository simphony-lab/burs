package com.local.simple.notes;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;
import static org.robolectric.Shadows.shadowOf;

import android.app.Activity;
import android.app.Application;
import android.content.Intent;
import android.os.HandlerThread;
import android.os.SystemClock;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;

import org.json.JSONArray;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.android.controller.ServiceController;
import org.robolectric.annotation.Config;
import org.robolectric.shadows.ShadowLooper;
import org.robolectric.shadows.ShadowSettings;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = {23, 26, 29, 31, 35})
public class IslandAndroidTest {
    static final long M = 60_000L;
    Application app;
    final List<String> toggles = new ArrayList<String>();
    int opens;

    final IslandOverlay.Listener listener = new IslandOverlay.Listener() {
        @Override public void onToggle(String key, boolean done) { toggles.add(key + "=" + done); }
        @Override public void onOpenApp() { opens++; }
    };

    @Before public void setUp() {
        app = RuntimeEnvironment.getApplication();
        ShadowSettings.setCanDrawOverlays(true);
    }

    static void settle() { ShadowLooper.idleMainLooper(1500, TimeUnit.MILLISECONDS); }

    static MotionEvent ev(int action, float x, float y) {
        long t = SystemClock.uptimeMillis();
        return MotionEvent.obtain(t, t, action, x, y, 0);
    }

    static void tap(View v, float x, float y) {
        v.dispatchTouchEvent(ev(MotionEvent.ACTION_DOWN, x, y));
        v.dispatchTouchEvent(ev(MotionEvent.ACTION_UP, x, y));
    }

    static void layout(View v) {
        WindowManager.LayoutParams lp = (WindowManager.LayoutParams) v.getLayoutParams();
        v.measure(View.MeasureSpec.makeMeasureSpec(lp.width, View.MeasureSpec.EXACTLY),
                View.MeasureSpec.makeMeasureSpec(lp.height, View.MeasureSpec.EXACTLY));
        v.layout(0, 0, lp.width, lp.height);
    }

    ScreenTime.Config cfg(String json) {
        return ScreenTime.parse(json);
    }

    IslandSnapshot tasksSnap(long now, int n, int done) {
        ScreenTime.Config c = cfg("{\"island\":{\"on\":true}}");
        for (int i = 0; i < n; i++) c.tasks.add(new ScreenTime.Task("k" + i, "Задача " + i, now - (10 - i) * M, now + 30 * M, i < done));
        return IslandSnapshot.compute(c, null, now, null, null, null, 0);
    }

    @Test public void idleCompactExpandedAndBack() {
        IslandOverlay o = new IslandOverlay(app, listener);
        o.setConfig(cfg("{\"island\":{\"on\":true,\"idle\":true}}"));
        long now = System.currentTimeMillis();
        o.update(IslandSnapshot.compute(o == null ? null : cfg("{\"island\":{\"on\":true}}"), null, now, null, null, null, 0));
        settle();
        assertTrue(o.isAttached());
        assertEquals(IslandOverlay.M_IDLE, o.mode());
        WindowManager.LayoutParams lp = (WindowManager.LayoutParams) o.view().getLayoutParams();
        assertTrue("idle must not take touches", (lp.flags & WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE) != 0);
        int idleH = lp.height;

        o.update(tasksSnap(now, 3, 0));
        settle();
        assertEquals(IslandOverlay.M_COMPACT, o.mode());
        assertEquals("Задача 0", o.compactTitle().toString());
        lp = (WindowManager.LayoutParams) o.view().getLayoutParams();
        assertTrue((lp.flags & WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE) == 0);
        assertTrue(lp.height > idleH);
        assertEquals(1f, o.shape()[3], 0.001f);
        // the capsule around the camera never takes touches; the body starts below the status bar
        WindowManager.LayoutParams cl = (WindowManager.LayoutParams) o.capsuleView().getLayoutParams();
        assertTrue((cl.flags & WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE) != 0);
        int sb = app.getResources().getDimensionPixelSize(app.getResources().getIdentifier("status_bar_height", "dimen", "android"));
        assertTrue("body below the status bar: " + lp.y + " vs " + sb, lp.y >= sb);
        assertTrue(cl.y + cl.height <= lp.y);
        assertTrue("capsule is narrow", cl.width < lp.width / 2);
        assertEquals(1f, o.capsule()[0], 0.001f);

        layout(o.view());
        tap(o.view(), lp.width / 2f, lp.height - 10);
        settle();
        assertEquals(IslandOverlay.M_EXPANDED, o.mode());
        assertEquals(3, o.panelRows());
        lp = (WindowManager.LayoutParams) o.view().getLayoutParams();
        assertTrue((lp.flags & WindowManager.LayoutParams.FLAG_WATCH_OUTSIDE_TOUCH) != 0);

        // tick the second task right on the island
        layout(o.view());
        IslandOverlay.ExpandedPanel panel = (IslandOverlay.ExpandedPanel) ((android.view.ViewGroup) o.view()).getChildAt(1);
        panel.rows.get(1).performClick();
        assertEquals("[k1=true]", toggles.toString());

        // outside tap closes it
        o.view().dispatchTouchEvent(ev(MotionEvent.ACTION_OUTSIDE, -10, -10));
        settle();
        assertEquals(IslandOverlay.M_COMPACT, o.mode());

        // nothing left: back to the black idle island, then switched off entirely
        o.update(IslandSnapshot.compute(cfg("{\"island\":{\"on\":true}}"), null, now, null, null, null, 0));
        settle();
        assertEquals(IslandOverlay.M_IDLE, o.mode());
        o.setConfig(cfg("{\"island\":{\"on\":true,\"idle\":false}}"));
        settle();
        assertEquals(IslandOverlay.M_HIDDEN, o.mode());
        assertFalse(o.isAttached());
        o.destroy();
        o.update(tasksSnap(now, 1, 0));
        assertFalse(o.isAttached());
    }

    @Test public void compactShowsPlusN_countdown_andLimit() {
        IslandOverlay o = new IslandOverlay(app, listener);
        ScreenTime.Config c = cfg("{\"island\":{\"on\":true},\"limits\":{\"yt\":30}}");
        o.setConfig(c);
        long now = System.currentTimeMillis();
        o.update(tasksSnap(now, 4, 1));
        settle();
        IslandOverlay.CompactRow row = (IslandOverlay.CompactRow) ((android.view.ViewGroup) o.view()).getChildAt(0);
        assertEquals("Задача 1", o.compactTitle().toString());
        assertEquals(View.VISIBLE, row.badge.getVisibility());
        assertEquals("+2", row.badge.getText().toString());

        ScreenTime.Config cf = cfg("{\"island\":{\"on\":true}}");
        cf.curfew.add(new long[]{now + 25 * M, now + 500 * M});
        o.update(IslandSnapshot.compute(cf, null, now, null, null, null, 0));
        settle();
        assertEquals("Комендантский час", o.compactTitle().toString());
        assertEquals("25:00", o.compactValue());
        o.update(IslandSnapshot.compute(cf, null, now + 1000, null, null, null, 0));
        assertEquals("24:59", o.compactValue());

        o.update(IslandSnapshot.compute(c, null, now, "yt", "YouTube", null, 12 * M));
        settle();
        assertEquals("YouTube", o.compactTitle().toString());
        assertEquals("12/30", o.compactValue());
        o.update(IslandSnapshot.compute(c, null, now, "yt", "YouTube", null, 31 * M));
        settle();
        assertEquals("Лимит исчерпан", o.compactTitle().toString());

        // more than three tasks: "open Lira" link in the opened island
        o.update(tasksSnap(now, 5, 0));
        settle();
        layout(o.view());
        WindowManager.LayoutParams lp = (WindowManager.LayoutParams) o.view().getLayoutParams();
        tap(o.view(), lp.width / 2f, lp.height - 8);
        settle();
        assertEquals(IslandOverlay.M_EXPANDED, o.mode());
        IslandOverlay.ExpandedPanel panel = (IslandOverlay.ExpandedPanel) ((android.view.ViewGroup) o.view()).getChildAt(1);
        View more = panel.getChildAt(panel.getChildCount() - 1);
        assertTrue(((android.widget.TextView) more).getText().toString().startsWith("Ещё 2"));
        more.performClick();
        assertEquals(1, opens);
        o.destroy();
    }

    @Test public void fullscreenHidesWhenAsked() throws Exception {
        IslandOverlay o = new IslandOverlay(app, listener);
        o.setConfig(cfg("{\"island\":{\"on\":true},\"hideFull\":true}"));
        long now = System.currentTimeMillis();
        o.update(tasksSnap(now, 1, 0));
        settle();
        Field f = IslandOverlay.class.getDeclaredField("fullscreen");
        f.setAccessible(true);
        java.lang.reflect.Method m = IslandOverlay.class.getDeclaredMethod("setFullscreen", boolean.class);
        m.setAccessible(true);
        m.invoke(o, true);
        settle();
        assertEquals(IslandOverlay.M_HIDDEN, o.mode());
        m.invoke(o, false);
        settle();
        assertEquals(IslandOverlay.M_COMPACT, o.mode());
        o.destroy();
    }

    static Object field(Object o, String name) throws Exception {
        Field f = o.getClass().getDeclaredField(name);
        f.setAccessible(true);
        return f.get(o);
    }

    @Test public void serviceRunsIslandAndRecordsTicksForLira() throws Exception {
        long now = System.currentTimeMillis();
        String task = "{\"k\":\"2026-11-25|t1\",\"t\":\"Отчёт\",\"s\":" + (now - 5 * M) + ",\"e\":" + (now + 40 * M);
        ScreenTime.write(app, "{\"island\":{\"on\":true,\"idle\":true},\"tasks\":[" + task + ",\"d\":false}]}");
        // island alone needs only the overlay permission
        ServiceController<ScreenTimeService> sc = Robolectric.buildService(ScreenTimeService.class).create().startCommand(0, 1);
        ScreenTimeService s = sc.get();
        assertFalse(shadowOf(s).isStoppedBySelf());
        HandlerThread th = (HandlerThread) field(s, "thread");
        shadowOf(th.getLooper()).idle();
        settle();
        IslandOverlay o = (IslandOverlay) field(s, "island");
        assertNotNull(o);
        assertEquals(IslandOverlay.M_COMPACT, o.mode());
        assertEquals("Отчёт", o.compactTitle().toString());

        // tick it on the island
        IslandOverlay.Listener l = (IslandOverlay.Listener) field(s, "islandListener");
        l.onToggle("2026-11-25|t1", true);
        shadowOf(th.getLooper()).idle();
        settle();
        assertEquals(IslandOverlay.M_IDLE, o.mode());
        JSONArray inbox = new JSONArray(new ScreenTimeBridge(Robolectric.buildActivity(Activity.class).setup().get()).takeInbox());
        assertEquals(1, inbox.length());
        assertEquals("2026-11-25|t1", inbox.getJSONObject(0).getString("k"));
        assertTrue(inbox.getJSONObject(0).getBoolean("d"));
        assertEquals("[]", new ScreenTimeBridge(Robolectric.buildActivity(Activity.class).setup().get()).takeInbox());
        assertTrue(s.pendingForTest().get("2026-11-25|t1"));

        // Lira took it over and pushes the task as done: the pending tick is forgotten
        ScreenTime.write(app, "{\"island\":{\"on\":true,\"idle\":true},\"tasks\":[" + task + ",\"d\":true}]}");
        sc.startCommand(0, 2);
        assertTrue(s.pendingForTest().isEmpty());
        shadowOf(th.getLooper()).idle();
        settle();
        assertEquals(IslandOverlay.M_IDLE, o.mode());

        // island off and no limits: the service stops
        ScreenTime.write(app, "{\"island\":{\"on\":false}}");
        sc.startCommand(0, 3);
        assertTrue(shadowOf(s).isStoppedBySelf());
        sc.destroy();
        assertTrue(o.isDead());
    }

    @Test public void syncStartsServiceForIslandWithoutUsageAccess() throws Exception {
        ScreenTime.write(app, "{\"island\":{\"on\":true}}");
        ScreenTime.sync(app);
        Intent i = shadowOf(app).getNextStartedService();
        assertNotNull(i);
        ShadowSettings.setCanDrawOverlays(false);
        ScreenTime.sync(app);
        assertEquals(null, shadowOf(app).getNextStartedService());
    }
    @Test public void configParsesIslandCurfewTasks() {
        long T = System.currentTimeMillis();
        String json = "{\"island\":{\"on\":true,\"idle\":false},\"curfew\":[[" + (T + 5000) + "," + (T + 1000) + "],[" + T + "," + (T + 600 * M) + "]],"
                + "\"tasks\":[{\"k\":\"2026-11-25|x\",\"t\":\"  Спорт \",\"s\":" + T + ",\"e\":" + (T + M) + ",\"d\":true},{\"k\":\"\",\"t\":\"bad\",\"s\":1,\"e\":2},{\"k\":\"y\",\"t\":\"neg\",\"s\":5,\"e\":3}]}";
        ScreenTime.Config c = ScreenTime.parse(json);
        assertTrue(c.island);
        assertFalse(c.islandIdle);
        assertEquals(1, c.curfew.size()); // end before start dropped
        assertEquals(1, c.tasks.size());
        assertEquals("Спорт", c.tasks.get(0).title);
        assertTrue(c.tasks.get(0).done);
        assertFalse(ScreenTime.parse("{}").island);
    }

    @Test public void accessibilityHostedIslandSurvivesSettingsScreens() throws Exception {
        // window type: the accessibility overlay is the one Android does not hide in Settings
        IslandOverlay a = new IslandOverlay(app, listener, true);
        a.setConfig(cfg("{\"island\":{\"on\":true}}"));
        a.update(tasksSnap(System.currentTimeMillis(), 1, 0));
        settle();
        assertTrue(a.isA11y());
        assertEquals(WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY, ((WindowManager.LayoutParams) a.view().getLayoutParams()).type);
        a.destroy();

        // detection of the switched-on service
        assertFalse(ScreenTime.islandA11y(app));
        android.provider.Settings.Secure.putInt(app.getContentResolver(), android.provider.Settings.Secure.ACCESSIBILITY_ENABLED, 1);
        android.provider.Settings.Secure.putString(app.getContentResolver(), android.provider.Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES,
                "com.other/.X:" + app.getPackageName() + "/" + IslandAccessibility.class.getName());
        assertTrue(ScreenTime.islandA11y(app));
        // island may run on the accessibility window alone, without the overlay permission
        ShadowSettings.setCanDrawOverlays(false);
        assertTrue(ScreenTime.wanted(app, cfg("{\"island\":{\"on\":true}}")));
        assertFalse(ScreenTime.wanted(app, cfg("{\"limits\":{\"yt\":30}}")));
        ShadowSettings.setCanDrawOverlays(true);

        // the running island moves to the accessibility window and back
        long now = System.currentTimeMillis();
        String task = "{\"k\":\"d|t\",\"t\":\"Звонок\",\"s\":" + (now - M) + ",\"e\":" + (now + 30 * M) + "}";
        ScreenTime.write(app, "{\"island\":{\"on\":true},\"tasks\":[" + task + "]}");
        ServiceController<ScreenTimeService> sc = Robolectric.buildService(ScreenTimeService.class).create().startCommand(0, 1);
        ScreenTimeService s = sc.get();
        HandlerThread th = (HandlerThread) field(s, "thread");
        shadowOf(th.getLooper()).idle();
        settle();
        IslandOverlay before = (IslandOverlay) field(s, "island");
        assertFalse(before.isA11y());
        ServiceController<IslandAccessibility> ac = Robolectric.buildService(IslandAccessibility.class).create();
        java.lang.reflect.Method connected = IslandAccessibility.class.getDeclaredMethod("onServiceConnected");
        connected.setAccessible(true);
        connected.invoke(ac.get());
        settle();
        shadowOf(th.getLooper()).idle();
        settle();
        IslandOverlay now1 = (IslandOverlay) field(s, "island");
        assertTrue(now1.isA11y());
        assertTrue(before.isDead());
        assertEquals(IslandOverlay.M_COMPACT, now1.mode());
        assertEquals(WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY, ((WindowManager.LayoutParams) now1.view().getLayoutParams()).type);
        ac.destroy();
        settle();
        shadowOf(th.getLooper()).idle();
        settle();
        IslandOverlay back = (IslandOverlay) field(s, "island");
        assertFalse(back.isA11y());
        assertTrue(now1.isDead());
        assertEquals(IslandOverlay.M_COMPACT, back.mode());
        sc.destroy();
    }
}

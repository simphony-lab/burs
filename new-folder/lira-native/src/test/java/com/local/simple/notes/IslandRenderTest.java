package com.local.simple.notes;

import android.app.Application;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.view.View;
import android.view.WindowManager;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;
import org.robolectric.annotation.GraphicsMode;
import org.robolectric.shadows.ShadowLooper;

import java.io.File;
import java.io.FileOutputStream;
import java.util.concurrent.TimeUnit;

/** Renders the real island views over a fake phone top, for review. */
@RunWith(RobolectricTestRunner.class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = 35, qualifiers = "w393dp-h852dp-xxhdpi")
public class IslandRenderTest {
    static final File OUT = new File(System.getProperty("render.dir", "target/render"));
    static final long M = 60_000L;
    final IslandOverlay.Listener noop = new IslandOverlay.Listener() {
        @Override public void onToggle(String key, boolean done) {}
        @Override public void onOpenApp() {}
    };

    float d;

    Bitmap phone(IslandOverlay o, boolean dark, int height) {
        Application app = RuntimeEnvironment.getApplication();
        d = app.getResources().getDisplayMetrics().density;
        int w = Math.round(393 * d), h = Math.round(height * d);
        Bitmap b = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
        Canvas c = new Canvas(b);
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        c.drawColor(dark ? 0xFF0E0E10 : 0xFFF3F4F7);
        // app content
        p.setColor(dark ? 0xFF1B1B1F : 0xFFFFFFFF);
        c.drawRect(0, 0, w, 96 * d, p);
        p.setColor(dark ? 0xFFEDEDED : 0xFF101114);
        p.setTypeface(Typeface.DEFAULT_BOLD);
        p.setTextSize(22 * d);
        c.drawText("Сообщения", 18 * d, 80 * d, p);
        p.setColor(dark ? 0xFF222226 : 0xFFE9EBEF);
        for (int i = 0; i < 4; i++) c.drawRoundRect(new RectF(16 * d, (112 + i * 64) * d, w - 16 * d, (164 + i * 64) * d), 14 * d, 14 * d, p);
        // the island window
        View v = o.view();
        if (o.isAttached() && v != null) {
            WindowManager.LayoutParams lp = (WindowManager.LayoutParams) v.getLayoutParams();
            v.measure(View.MeasureSpec.makeMeasureSpec(lp.width, View.MeasureSpec.EXACTLY), View.MeasureSpec.makeMeasureSpec(lp.height, View.MeasureSpec.EXACTLY));
            v.layout(0, 0, lp.width, lp.height);
            c.save();
            c.translate(lp.x, lp.y);
            v.draw(c);
            c.restore();
        }
        // front camera and status bar (drawn above, like the system does)
        float sb = 32 * d;
        p.setColor(0xFF050505);
        c.drawCircle(w / 2f, sb / 2f + 1 * d, 5.5f * d, p);
        p.setColor(0xFF1D2433);
        c.drawCircle(w / 2f - 1.5f * d, sb / 2f - 0.5f * d, 1.6f * d, p);
        int ic = dark ? Color.WHITE : 0xFF111111;
        p.setColor(ic);
        p.setTextSize(14 * d);
        p.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        c.drawText("9:41", 24 * d, sb / 2f + 5 * d, p);
        // wifi-ish, signal, battery
        float x = w - 30 * d, y = sb / 2f;
        p.setStyle(Paint.Style.STROKE);
        p.setStrokeWidth(1.3f * d);
        c.drawRoundRect(new RectF(x - 8 * d, y - 5 * d, x + 12 * d, y + 5 * d), 2.5f * d, 2.5f * d, p);
        p.setStyle(Paint.Style.FILL);
        c.drawRoundRect(new RectF(x - 6.5f * d, y - 3.5f * d, x + 8 * d, y + 3.5f * d), 1.5f * d, 1.5f * d, p);
        for (int i = 0; i < 4; i++) c.drawRect(x - (36 - i * 4.5f) * d, y + (4 - i * 2.4f) * d, x - (33 - i * 4.5f) * d, y + 5 * d, p);
        Path wifi = new Path();
        wifi.moveTo(x - 52 * d, y - 2 * d);
        wifi.lineTo(x - 44 * d, y + 5 * d);
        wifi.lineTo(x - 36 * d - 0 * d, y - 2 * d);
        wifi.close();
        c.drawPath(wifi, p);
        return b;
    }

    static Bitmap stack(Bitmap... parts) {
        int w = parts[0].getWidth(), h = 0;
        for (Bitmap p : parts) h += p.getHeight() + 8;
        Bitmap out = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
        Canvas c = new Canvas(out);
        c.drawColor(0xFF6E6E73);
        int y = 0;
        for (Bitmap p : parts) { c.drawBitmap(p, 0, y, null); y += p.getHeight() + 8; }
        return out;
    }

    static void save(Bitmap b, String name) throws Exception {
        OUT.mkdirs();
        FileOutputStream out = new FileOutputStream(new File(OUT, name));
        b.compress(Bitmap.CompressFormat.PNG, 100, out);
        out.close();
    }

    static Bitmap appIcon(int color, int size) {
        Bitmap b = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888);
        Canvas c = new Canvas(b);
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        p.setColor(color);
        c.drawRoundRect(new RectF(0, 0, size, size), size * 0.28f, size * 0.28f, p);
        p.setColor(Color.WHITE);
        Path t = new Path();
        t.moveTo(size * 0.38f, size * 0.3f);
        t.lineTo(size * 0.72f, size * 0.5f);
        t.lineTo(size * 0.38f, size * 0.7f);
        t.close();
        c.drawPath(t, p);
        return b;
    }

    static void settle(long ms) { ShadowLooper.idleMainLooper(ms, TimeUnit.MILLISECONDS); }

    @Test public void renderIsland() throws Exception {
        Application app = RuntimeEnvironment.getApplication();
        long now = System.currentTimeMillis();
        ScreenTime.Config c = ScreenTime.parse("{\"island\":{\"on\":true,\"idle\":true},\"accent\":\"#62d9ff\",\"limits\":{\"yt\":30}}");
        for (int i = 0; i < 5; i++) {
            String[] titles = {"Подготовить отчёт", "Позвонить маме", "Тренировка", "Разобрать почту", "Прогулка"};
            c.tasks.add(new ScreenTime.Task("k" + i, titles[i], now - (40 - i * 5) * M, now + (20 + i * 10) * M, i == 1));
        }

        IslandOverlay idle = new IslandOverlay(app, noop);
        idle.setConfig(c);
        idle.update(IslandSnapshot.compute(ScreenTime.parse("{\"island\":{\"on\":true}}"), null, now, null, null, null, 0));
        settle(1500);
        Bitmap f1 = phone(idle, false, 120), f1d = phone(idle, true, 120);

        IslandOverlay task = new IslandOverlay(app, noop);
        task.setConfig(c);
        task.update(IslandSnapshot.compute(ScreenTime.parse("{\"island\":{\"on\":true}}"), null, now, null, null, null, 0));
        settle(1500);
        task.update(IslandSnapshot.compute(c, null, now, null, null, null, 0));
        settle(120);
        Bitmap m1 = phone(task, true, 120);
        settle(140);
        Bitmap m2 = phone(task, true, 120);
        settle(1500);
        Bitmap f2 = phone(task, false, 120), f2d = phone(task, true, 120);

        ScreenTime.Config cf = ScreenTime.parse("{\"island\":{\"on\":true},\"accent\":\"#62d9ff\"}");
        cf.curfew.add(new long[]{now + 24 * M + 37_000, now + 9 * 60 * M});
        IslandOverlay cur = new IslandOverlay(app, noop);
        cur.setConfig(cf);
        cur.update(IslandSnapshot.compute(cf, null, now, null, null, null, 0));
        settle(1500);
        Bitmap f3 = phone(cur, true, 120), f3l = phone(cur, false, 120);
        cur.update(IslandSnapshot.compute(cf, null, now + 1000, null, null, null, 0));
        settle(120);
        Bitmap f3roll = phone(cur, true, 120);

        IslandOverlay lim = new IslandOverlay(app, noop);
        lim.setConfig(c);
        Bitmap yt = appIcon(0xFFFF0033, Math.round(32 * d));
        lim.update(IslandSnapshot.compute(c, null, now, "yt", "YouTube", yt, 24 * M));
        settle(1500);
        Bitmap f4 = phone(lim, false, 120);

        // opened island: curfew + limit + tasks
        ScreenTime.Config all = ScreenTime.parse("{\"island\":{\"on\":true},\"accent\":\"#62d9ff\",\"limits\":{\"yt\":30}}");
        all.tasks.addAll(c.tasks);
        all.curfew.add(new long[]{now + 12 * M, now + 9 * 60 * M});
        IslandOverlay ex = new IslandOverlay(app, noop);
        ex.setConfig(all);
        ex.update(IslandSnapshot.compute(all, null, now, "yt", "YouTube", yt, 24 * M));
        settle(1500);
        ex.expand();
        settle(1500);
        Bitmap f5 = phone(ex, false, 420), f5d = phone(ex, true, 420);

        IslandOverlay ex2 = new IslandOverlay(app, noop);
        ex2.setConfig(c);
        ex2.update(IslandSnapshot.compute(c, null, now, null, null, null, 0));
        settle(1500);
        ex2.expand();
        settle(260);
        Bitmap mid = phone(ex2, true, 330);
        settle(1500);
        Bitmap f6 = phone(ex2, true, 330);

        // morph frames: drive the running animation by hand
        IslandOverlay mo = new IslandOverlay(app, noop);
        mo.setConfig(c);
        mo.update(IslandSnapshot.compute(ScreenTime.parse("{\"island\":{\"on\":true}}"), null, now, null, null, null, 0));
        settle(1500);
        java.lang.reflect.Field fa = IslandOverlay.class.getDeclaredField("shapeAnim");
        fa.setAccessible(true);
        java.util.ArrayList<Bitmap> morph = new java.util.ArrayList<Bitmap>();
        mo.update(IslandSnapshot.compute(c, null, now, null, null, null, 0));
        for (float fr : new float[]{0.12f, 0.3f, 0.55f}) {
            android.animation.ValueAnimator va = (android.animation.ValueAnimator) fa.get(mo);
            va.setCurrentFraction(fr);
            morph.add(phone(mo, true, 120));
        }
        settle(1500);
        mo.expand();
        for (float fr : new float[]{0.15f, 0.35f, 0.6f}) {
            android.animation.ValueAnimator va = (android.animation.ValueAnimator) fa.get(mo);
            va.setCurrentFraction(fr);
            morph.add(phone(mo, true, 330));
        }
        save(stack(morph.toArray(new Bitmap[0])), "island_morph.png");

        save(stack(f1, f1d, m1, m2, f2, f2d, f3, f3l, f3roll, f4), "island_compact.png");
        save(stack(f5, f5d), "island_expanded_all.png");
        save(stack(mid, f6), "island_expanded_tasks.png");
    }
}

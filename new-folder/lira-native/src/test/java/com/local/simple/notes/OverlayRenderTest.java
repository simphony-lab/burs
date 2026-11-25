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

/** Draws the real pill in several states over a light and a dark app and saves PNGs (for review). */
@RunWith(RobolectricTestRunner.class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = 35, qualifiers = "w393dp-h852dp-xxhdpi")
public class OverlayRenderTest {
    static final File OUT = new File(System.getProperty("render.dir", "target/render"));

    static Bitmap appIcon(int color, String glyph, int size) {
        Bitmap b = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888);
        Canvas c = new Canvas(b);
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        p.setColor(color);
        c.drawRoundRect(new RectF(0, 0, size, size), size * 0.28f, size * 0.28f, p);
        p.setColor(Color.WHITE);
        if (glyph.equals("play")) {
            Path t = new Path();
            t.moveTo(size * 0.38f, size * 0.3f);
            t.lineTo(size * 0.72f, size * 0.5f);
            t.lineTo(size * 0.38f, size * 0.7f);
            t.close();
            c.drawPath(t, p);
        } else {
            p.setTextSize(size * 0.6f);
            p.setTypeface(Typeface.DEFAULT_BOLD);
            p.setTextAlign(Paint.Align.CENTER);
            c.drawText(glyph, size / 2f, size * 0.72f, p);
        }
        return b;
    }

    /** A fake app screen top: status-bar-free toolbar with a title, then content. */
    static void fakeApp(Canvas c, int w, int h, boolean dark, float d) {
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        c.drawColor(dark ? 0xFF0F0F0F : 0xFFFFFFFF);
        p.setColor(dark ? 0xFF1F1F1F : 0xFFF2F2F2);
        for (int i = 0; i < 3; i++) c.drawRoundRect(new RectF(16 * d, (64 + i * 70) * d, w - 16 * d, (120 + i * 70) * d), 12 * d, 12 * d, p);
        p.setColor(dark ? 0xFFEDEDED : 0xFF111111);
        p.setTextSize(19 * d);
        p.setTypeface(Typeface.DEFAULT_BOLD);
        c.drawText("Главная", 18 * d, 36 * d, p);
        p.setColor(dark ? 0xFF9A9A9A : 0xFF666666);
        c.drawCircle(w - 32 * d, 30 * d, 11 * d, p);
    }

    static void save(Bitmap b, String name) throws Exception {
        OUT.mkdirs();
        FileOutputStream out = new FileOutputStream(new File(OUT, name));
        b.compress(Bitmap.CompressFormat.PNG, 100, out);
        out.close();
    }

    Bitmap frame(ScreenTimeOverlay o, boolean dark, float alpha) {
        Application app = RuntimeEnvironment.getApplication();
        float d = app.getResources().getDisplayMetrics().density;
        int w = Math.round(393 * d), h = Math.round(150 * d);
        Bitmap b = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
        Canvas c = new Canvas(b);
        fakeApp(c, w, h, dark, d);
        View v = o.view();
        int ww = v.getLayoutParams() != null && v.getLayoutParams().width > 0 ? v.getLayoutParams().width : w;
        v.measure(View.MeasureSpec.makeMeasureSpec(ww, View.MeasureSpec.EXACTLY), View.MeasureSpec.makeMeasureSpec(h, View.MeasureSpec.AT_MOST));
        v.layout(0, 0, v.getMeasuredWidth(), v.getMeasuredHeight());
        int x = (w - v.getMeasuredWidth()) / 2;
        c.save();
        c.translate(x, 0);
        c.saveLayerAlpha(new RectF(0, 0, v.getMeasuredWidth(), v.getMeasuredHeight()), Math.round(alpha * 255));
        v.draw(c);
        c.restore();
        c.restore();
        return b;
    }

    Bitmap stack(Bitmap... parts) {
        int w = parts[0].getWidth(), h = 0;
        for (Bitmap p : parts) h += p.getHeight() + 6;
        Bitmap out = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
        Canvas c = new Canvas(out);
        c.drawColor(0xFF7A7A7A);
        int y = 0;
        for (Bitmap p : parts) { c.drawBitmap(p, 0, y, null); y += p.getHeight() + 6; }
        return out;
    }

    @Test public void renderStates() throws Exception {
        Application app = RuntimeEnvironment.getApplication();
        long day = UsageTracker.startOfDay(System.currentTimeMillis());
        int px = Math.round(16 * app.getResources().getDisplayMetrics().density);
        Bitmap yt = appIcon(0xFFFF0033, "play", px), tt = appIcon(0xFF111111, "♪", px), tg = appIcon(0xFF2AABEE, "✈", px);
        ScreenTime.Config cfg = ScreenTime.parse("{\"accent\":\"#bddfd6\"}");

        ScreenTimeOverlay o = new ScreenTimeOverlay(app);
        o.setConfig(cfg);
        o.show("yt", "YouTube", yt, 12 * 60_000L, 30 * 60_000L, day);
        ShadowLooper.idleMainLooper(1, TimeUnit.SECONDS);
        org.junit.Assert.assertTrue(o.isVisibleNow());
        Bitmap a1 = frame(o, false, 0.8f), a2 = frame(o, true, 0.8f);
        ShadowLooper.idleMainLooper(5, TimeUnit.SECONDS);
        Bitmap b1 = frame(o, false, 0.8f), b2 = frame(o, true, 0.8f);

        ScreenTimeOverlay w = new ScreenTimeOverlay(app);
        w.setConfig(cfg);
        w.show("tt", "TikTok", tt, 25 * 60_000L, 30 * 60_000L, day);
        ShadowLooper.idleMainLooper(1, TimeUnit.SECONDS);
        Bitmap c1 = frame(w, false, 0.8f);

        ScreenTimeOverlay x = new ScreenTimeOverlay(app);
        x.setConfig(cfg);
        x.show("tg", "Telegram", tg, 47 * 60_000L, 45 * 60_000L, day);
        ShadowLooper.idleMainLooper(1, TimeUnit.SECONDS);
        Bitmap d1 = frame(x, false, 0.8f), d2 = frame(x, true, 0.8f);
        ShadowLooper.idleMainLooper(7, TimeUnit.SECONDS);
        Bitmap e1 = frame(x, true, 0.8f);

        save(stack(a1, a2, b1, b2, c1, d1, d2, e1), "pill_states.png");
        save(a1, "pill_expanded_light.png");
        save(b2, "pill_compact_dark.png");
        save(d1, "pill_over_light.png");
    }
}

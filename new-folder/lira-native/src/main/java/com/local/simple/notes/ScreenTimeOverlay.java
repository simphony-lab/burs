package com.local.simple.notes;

import android.animation.LayoutTransition;
import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.hardware.input.InputManager;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.text.SpannableStringBuilder;
import android.text.Spanned;
import android.text.TextUtils;
import android.text.style.ForegroundColorSpan;
import android.util.Log;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.WindowInsets;
import android.view.WindowManager;
import android.view.animation.AccelerateInterpolator;
import android.view.animation.DecelerateInterpolator;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.HashSet;

/**
 * The small pill at the top of the screen: app icon, name, "12 / 30 мин" and a bar that fills
 * up. It never takes focus or touches (taps go to the app below), collapses to just the
 * counter after a few seconds, expands again at 80% and 100%, and can hide itself while
 * another app is full screen. Main thread only.
 */
final class ScreenTimeOverlay {
    static final int BG = 0xFA0F1724;
    static final int STROKE = 0x29FFFFFF;
    static final int TEXT = 0xFFF3F8FF;
    static final int SUB = 0xFFA7BAD0;
    static final int TRACK = 0x2EFFFFFF;
    static final int WARN = 0xFFFFD27A;
    static final int OVER = 0xFFFF8FA3;
    static final long SHOW_MS = 4000L;
    static final long ALERT_MS = 6000L;

    private final Context ctx;
    private final WindowManager wm;
    private final float density;
    private final Handler h = new Handler(Looper.getMainLooper());

    private FrameLayout root;
    private LinearLayout pill;
    private ImageView iconView;
    private TextView nameView;
    private TextView valueView;
    private Bar bar;
    private WindowManager.LayoutParams lp;

    private ScreenTime.Config cfg = new ScreenTime.Config();
    private boolean attached, shown, expanded, fullscreen, visible, dead;
    private String pkg;
    private String label = "";
    private long used, limit, day = Long.MIN_VALUE;
    private int level;
    private final HashSet<String> alerted = new HashSet<String>();

    private final Runnable collapse = new Runnable() {
        @Override public void run() { if (shown) setExpanded(false); }
    };
    private final Runnable detach = new Runnable() {
        @Override public void run() { if (!shown) detachNow(); }
    };

    ScreenTimeOverlay(Context c) {
        ctx = c;
        wm = (WindowManager) c.getSystemService(Context.WINDOW_SERVICE);
        density = c.getResources().getDisplayMetrics().density;
    }

    int dp(float v) { return Math.round(v * density); }

    boolean isDead() { return dead; }
    boolean isAttached() { return attached; }
    boolean isShown() { return shown; }
    boolean isExpanded() { return expanded; }
    boolean isVisibleNow() { return visible; }
    boolean isFullscreen() { return fullscreen; }
    View view() { return root; }
    CharSequence valueText() { return valueView == null ? "" : valueView.getText(); }
    CharSequence nameText() { return nameView == null ? "" : nameView.getText(); }

    void setConfig(ScreenTime.Config c) {
        if (dead) return;
        boolean moved = c.pos != cfg.pos;
        cfg = c;
        if (root == null) return;
        if (moved) place();
        if (!cfg.compact) setExpanded(true);
        else if (shown && expanded) { h.removeCallbacks(collapse); h.postDelayed(collapse, SHOW_MS); }
        updateVisibility();
        render();
    }

    void show(String p, String lbl, Bitmap icon, long usedMs, long limitMs, long dayStart) {
        if (dead || p == null) return;
        if (dayStart != day) { day = dayStart; alerted.clear(); }
        boolean fresh = !shown || !p.equals(pkg);
        if (!attached && !attach()) return;
        h.removeCallbacks(detach);
        pkg = p;
        label = lbl == null ? "" : lbl;
        used = Math.max(0L, usedMs);
        limit = Math.max(60_000L, limitMs);
        float f = (float) used / limit;
        int lvl = f >= 1f ? 2 : f >= 0.8f ? 1 : 0;
        boolean alert = lvl > 0 && alerted.add(p + ":" + lvl) && !fresh;
        level = lvl;
        if (fresh) {
            iconView.setImageBitmap(icon);
            iconView.setVisibility(icon == null ? View.GONE : View.VISIBLE);
            shown = true;
            setExpanded(true);
            scheduleCollapse(SHOW_MS);
            render();
            bar.grow(f, color());
            pill.setAlpha(0f);
            pill.setTranslationY(-dp(10));
            pill.setScaleX(0.94f);
            pill.setScaleY(0.94f);
            visible = false;
        } else {
            if (alert) {
                setExpanded(true);
                scheduleCollapse(ALERT_MS);
            }
            render();
            bar.set(f, color());
        }
        updateVisibility();
    }

    void hide() {
        if (!shown) return;
        shown = false;
        pkg = null;
        h.removeCallbacks(collapse);
        updateVisibility();
        h.removeCallbacks(detach);
        h.postDelayed(detach, 600);
    }

    void destroy() {
        dead = true;
        shown = false;
        h.removeCallbacksAndMessages(null);
        detachNow();
    }

    // ----------------------------------------------------------------------------------------

    private int color() { return level == 2 ? OVER : level == 1 ? WARN : cfg.accent; }

    private void scheduleCollapse(long ms) {
        h.removeCallbacks(collapse);
        if (cfg.compact) h.postDelayed(collapse, ms);
    }

    private void setExpanded(boolean e) {
        boolean want = e || !cfg.compact;
        if (want == expanded && nameView.getVisibility() == (want ? View.VISIBLE : View.GONE)) return;
        expanded = want;
        nameView.setVisibility(want ? View.VISIBLE : View.GONE);
        render();
    }

    private void render() {
        if (root == null) return;
        long u = used / 60_000L, l = limit / 60_000L;
        boolean over = level == 2;
        String name = over ? "Лимит исчерпан" : label;
        if (!TextUtils.equals(nameView.getText(), name)) nameView.setText(name);
        nameView.setTextColor(over ? OVER : TEXT);
        SpannableStringBuilder s = new SpannableStringBuilder(String.valueOf(u));
        s.setSpan(new ForegroundColorSpan(over ? OVER : TEXT), 0, s.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        int a = s.length();
        s.append(expanded ? " / " + l + " мин" : "/" + l);
        s.setSpan(new ForegroundColorSpan(SUB), a, s.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        if (!TextUtils.equals(valueView.getText().toString(), s.toString())) valueView.setText(s);
        bar.set((float) used / limit, color());
        pill.setContentDescription(label + ": " + u + " из " + l + " минут");
    }

    private void updateVisibility() {
        boolean want = shown && !(cfg.hideFull && fullscreen);
        if (want == visible) return;
        visible = want;
        pill.animate().cancel();
        if (want) {
            pill.animate().alpha(1f).translationY(0f).scaleX(1f).scaleY(1f)
                    .setDuration(260).setInterpolator(new DecelerateInterpolator(1.6f)).start();
        } else {
            pill.animate().alpha(0f).translationY(-dp(8)).scaleX(0.96f).scaleY(0.96f)
                    .setDuration(170).setInterpolator(new AccelerateInterpolator()).start();
        }
    }

    private void setFullscreen(boolean f) {
        if (f == fullscreen) return;
        fullscreen = f;
        updateVisibility();
    }

    private boolean attach() {
        if (root == null) build();
        int type = Build.VERSION.SDK_INT >= 26
                ? WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
                : WindowManager.LayoutParams.TYPE_PHONE;
        int width = Math.min(dp(288), ctx.getResources().getDisplayMetrics().widthPixels);
        lp = new WindowManager.LayoutParams(width, WindowManager.LayoutParams.WRAP_CONTENT, type,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
                        | WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED,
                PixelFormat.TRANSLUCENT);
        lp.setTitle("LiraScreenTime");
        if (Build.VERSION.SDK_INT >= 30) {
            // Lay the window out from the very top so its insets tell whether this phone has a
            // status bar that is hidden right now (full-screen video or game). The pill itself is
            // kept below the status bar with top padding.
            lp.setFitInsetsTypes(0);
            lp.layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
            topInset(statusBarHeight());
        }
        if (Build.VERSION.SDK_INT >= 31) {
            // Since Android 12 taps pass through another app's overlay only if it is at most this opaque.
            float max = 0.8f;
            try {
                InputManager im = (InputManager) ctx.getSystemService(Context.INPUT_SERVICE);
                if (im != null) max = im.getMaximumObscuringOpacityForTouch();
            } catch (Throwable ignored) {}
            lp.alpha = Math.max(0f, Math.min(0.9f, max));
        }
        place();
        try {
            wm.addView(root, lp);
            attached = true;
            visible = false;
            fullscreen = false;
            return true;
        } catch (Throwable t) {
            Log.w(ScreenTime.TAG, "overlay", t);
            attached = false;
            return false;
        }
    }

    private int statusBarHeight() {
        try {
            int id = ctx.getResources().getIdentifier("status_bar_height", "dimen", "android");
            if (id != 0) return ctx.getResources().getDimensionPixelSize(id);
        } catch (Throwable ignored) {}
        return dp(24);
    }

    private void topInset(int px) {
        int top = px + dp(6);
        if (root != null && root.getPaddingTop() != top) {
            root.setPadding(root.getPaddingLeft(), top, root.getPaddingRight(), root.getPaddingBottom());
        }
    }

    private void place() {
        int g = cfg.pos == 1 ? Gravity.LEFT : cfg.pos == 2 ? Gravity.RIGHT : Gravity.CENTER_HORIZONTAL;
        if (pill != null) {
            FrameLayout.LayoutParams p = (FrameLayout.LayoutParams) pill.getLayoutParams();
            p.gravity = Gravity.TOP | g;
            pill.setLayoutParams(p);
        }
        if (lp != null) {
            lp.gravity = Gravity.TOP | g;
            lp.x = 0;
            lp.y = 0;
            if (attached) {
                try { wm.updateViewLayout(root, lp); } catch (Throwable t) { Log.w(ScreenTime.TAG, "place", t); }
            }
        }
    }

    private void detachNow() {
        if (!attached) return;
        try {
            wm.removeView(root);
        } catch (Throwable t) {
            Log.w(ScreenTime.TAG, "detach", t);
        }
        attached = false;
        visible = false;
    }

    private void build() {
        root = new FrameLayout(ctx);
        root.setClipChildren(false);
        root.setClipToPadding(false);
        root.setPadding(dp(12), dp(6), dp(12), dp(12));
        root.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO_HIDE_DESCENDANTS);

        pill = new LinearLayout(ctx);
        pill.setOrientation(LinearLayout.VERTICAL);
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(BG);
        bg.setCornerRadius(dp(19));
        bg.setStroke(Math.max(1, dp(1)), STROKE);
        pill.setBackground(bg);
        pill.setElevation(dp(6));
        pill.setPadding(dp(12), dp(7), dp(12), dp(8));
        pill.setMinimumWidth(dp(64));

        LinearLayout row = new LinearLayout(ctx);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);

        iconView = new ImageView(ctx);
        iconView.setScaleType(ImageView.ScaleType.FIT_CENTER);
        LinearLayout.LayoutParams ip = new LinearLayout.LayoutParams(dp(16), dp(16));
        ip.rightMargin = dp(7);
        row.addView(iconView, ip);

        nameView = new TextView(ctx);
        nameView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12.5f);
        nameView.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        nameView.setTextColor(TEXT);
        nameView.setSingleLine(true);
        nameView.setEllipsize(TextUtils.TruncateAt.END);
        nameView.setMaxWidth(dp(124));
        nameView.setIncludeFontPadding(false);
        LinearLayout.LayoutParams np = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        np.rightMargin = dp(10);
        row.addView(nameView, np);

        valueView = new TextView(ctx);
        valueView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12.5f);
        valueView.setTypeface(Typeface.create("sans-serif", Typeface.BOLD));
        valueView.setTextColor(TEXT);
        valueView.setSingleLine(true);
        valueView.setIncludeFontPadding(false);
        valueView.setFontFeatureSettings("tnum");
        row.addView(valueView, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        bar = new Bar(ctx);
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(3));
        bp.topMargin = dp(6);

        pill.addView(row, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT));
        pill.addView(bar, bp);
        root.addView(pill, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT, Gravity.TOP | Gravity.CENTER_HORIZONTAL));

        // Smooth width change when the name hides or shows again.
        row.setLayoutTransition(transition());
        pill.setLayoutTransition(transition());
        root.setLayoutTransition(transition());

        root.setOnApplyWindowInsetsListener(new View.OnApplyWindowInsetsListener() {
            @Override public WindowInsets onApplyWindowInsets(View v, WindowInsets in) {
                if (Build.VERSION.SDK_INT >= 30) {
                    int bar = in.getInsetsIgnoringVisibility(WindowInsets.Type.statusBars()).top;
                    int cut = in.getInsetsIgnoringVisibility(WindowInsets.Type.displayCutout()).top;
                    int top = Math.max(bar, cut);
                    topInset(top > 0 ? top : statusBarHeight());
                    // Only "full screen" when there is a status bar and it is hidden: if this window
                    // cannot see the status bar at all, the pill simply stays visible.
                    setFullscreen(bar > 0 && !in.isVisible(WindowInsets.Type.statusBars()));
                }
                return in;
            }
        });
        if (Build.VERSION.SDK_INT < 30) {
            root.setOnSystemUiVisibilityChangeListener(new View.OnSystemUiVisibilityChangeListener() {
                @Override public void onSystemUiVisibilityChange(int vis) {
                    setFullscreen((vis & View.SYSTEM_UI_FLAG_FULLSCREEN) != 0);
                }
            });
        }
        nameView.setVisibility(View.VISIBLE);
        expanded = true;
    }

    private static LayoutTransition transition() {
        LayoutTransition t = new LayoutTransition();
        t.enableTransitionType(LayoutTransition.CHANGING);
        t.setDuration(220);
        return t;
    }

    /** Thin rounded progress bar. */
    static final class Bar extends View {
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final RectF rect = new RectF();
        private float frac, target;
        private int color = ScreenTime.DEFAULT_ACCENT;
        private ValueAnimator anim;

        Bar(Context c) { super(c); }

        float fraction() { return target; }
        int color() { return color; }

        void set(float f, int c) {
            f = Math.max(0f, Math.min(1f, f));
            boolean dirty = c != color;
            color = c;
            target = f;
            if ((anim == null || !anim.isRunning()) && frac != f) {
                frac = f;
                dirty = true;
            }
            if (dirty) invalidate();
        }

        /** Fills from empty to f, for the moment the pill appears. */
        void grow(float f, int c) {
            if (anim != null) anim.cancel();
            color = c;
            target = Math.max(0f, Math.min(1f, f));
            frac = 0f;
            anim = ValueAnimator.ofFloat(0f, 1f);
            anim.setDuration(700);
            anim.setInterpolator(new DecelerateInterpolator(1.8f));
            anim.addUpdateListener(new ValueAnimator.AnimatorUpdateListener() {
                @Override public void onAnimationUpdate(ValueAnimator a) {
                    frac = target * (Float) a.getAnimatedValue();
                    invalidate();
                }
            });
            anim.start();
            invalidate();
        }

        @Override protected void onDraw(Canvas canvas) {
            float w = getWidth(), hh = getHeight(), r = hh / 2f;
            paint.setColor(TRACK);
            rect.set(0, 0, w, hh);
            canvas.drawRoundRect(rect, r, r, paint);
            if (frac > 0f) {
                paint.setColor(color);
                rect.set(0, 0, Math.max(hh, w * frac), hh);
                canvas.drawRoundRect(rect, r, r, paint);
            }
        }
    }
}

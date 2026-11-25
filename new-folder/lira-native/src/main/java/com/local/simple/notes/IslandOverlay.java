package com.local.simple.notes;

import android.animation.Animator;
import android.animation.AnimatorListenerAdapter;
import android.animation.TimeInterpolator;
import android.animation.ValueAnimator;
import android.content.Context;
import android.content.res.Configuration;
import android.graphics.Bitmap;
import android.graphics.BitmapShader;
import android.graphics.Canvas;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.PathMeasure;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.RenderEffect;
import android.graphics.Shader;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.text.TextUtils;
import android.util.Log;
import android.util.TypedValue;
import android.view.DisplayCutout;
import android.view.Gravity;
import android.view.HapticFeedbackConstants;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowInsets;
import android.view.WindowManager;
import android.view.animation.DecelerateInterpolator;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.ArrayList;
import java.util.Calendar;
import java.util.List;
import java.util.Locale;

/**
 * Lira's dynamic island: a black shape around the front camera. Idle it is a small black
 * capsule; with something to show (a task that is on now, an app with a limit, the curfew
 * countdown) it grows below the status bar with the content; a tap opens a small panel where
 * current tasks can be ticked without opening Lira. Main thread only.
 *
 * Android does not deliver taps inside the status bar to other apps, so everything you can tap
 * sits below it; the part inside the status bar only hugs the camera.
 */
final class IslandOverlay {
    interface Listener {
        void onToggle(String key, boolean done);
        void onOpenApp();
    }

    static final int M_HIDDEN = 0, M_IDLE = 1, M_COMPACT = 2, M_EXPANDED = 3;
    static final int BLACK = 0xFF000000, WHITE = 0xFFFFFFFF, GREY = 0xFF8E8E93, DIM = 0xFF2C2C2E, LINE = 0xFF1C1C1E;
    static final int MOON = 0xFFB9A8FF, AMBER = 0xFFFFB340, RED = 0xFFFF6B6B, WARN = 0xFFFFD27A;
    static final long EXPANDED_IDLE_MS = 12_000L;
    static final int MAX_ROWS = 3;

    private final Context ctx;
    private final WindowManager wm;
    private final float density;
    private final Handler h = new Handler(Looper.getMainLooper());
    private final Listener listener;

    private ScreenTime.Config cfg = new ScreenTime.Config();
    private IslandSnapshot snap = new IslandSnapshot();
    private String structure = "";

    private IslandView root;            // the body under the status bar (touchable)
    private CapsuleView cap;            // the black capsule around the camera (never takes touches)
    private CompactRow compact;
    private ExpandedPanel panel;
    private WindowManager.LayoutParams lp, capLp;
    private boolean attached, dead, fullscreen;
    private int mode = M_HIDDEN;

    // geometry, px
    // top = capsule top; bodyY = where the body starts (just below the status bar, so the status
    // bar icons on both sides of the camera always stay visible and the shade can be pulled anywhere)
    private int screenW, sbH, top, centerX, idleW, idleH, bodyY, rowH, compactW, compactH, expandedW, expandedH;
    private boolean landscape;

    // shape being drawn
    private float curW, curH, curR, curA;   // body
    private float capA, capS = 1f;          // capsule alpha and scale
    private ValueAnimator shapeAnim;
    private float press = 1f;
    private ValueAnimator pressAnim;

    private final Runnable autoCollapse = new Runnable() {
        @Override public void run() { if (mode == M_EXPANDED) collapse(); }
    };

    /** true when the window belongs to Lira's accessibility service (shown even over system Settings). */
    private final boolean a11y;

    IslandOverlay(Context c, Listener l) { this(c, l, false); }

    /**
     * @param c context whose WindowManager owns the window; for {@code a11y} it must be the
     *          running accessibility service, which supplies the window token.
     */
    IslandOverlay(Context c, Listener l, boolean a11y) {
        ctx = c;
        listener = l;
        this.a11y = a11y;
        wm = (WindowManager) c.getSystemService(Context.WINDOW_SERVICE);
        density = c.getResources().getDisplayMetrics().density;
    }

    boolean isA11y() { return a11y; }

    int dp(float v) { return Math.round(v * density); }

    // ---- state for tests -------------------------------------------------------------------
    int mode() { return mode; }
    boolean isAttached() { return attached; }
    boolean isDead() { return dead; }
    View view() { return root; }
    View capsuleView() { return cap; }
    float[] capsule() { return new float[]{capA, capS}; }
    CharSequence compactTitle() { return compact == null ? "" : compact.title.getText(); }
    String compactValue() { return compact == null ? "" : compact.valueText(); }
    int panelRows() { return panel == null ? 0 : panel.rows.size(); }
    float[] shape() { return new float[]{curW, curH, curR, curA}; }
    int[] window() { return lp == null ? new int[]{0, 0, 0, 0} : new int[]{lp.x, lp.y, lp.width, lp.height}; }

    // ---- public API ------------------------------------------------------------------------
    void setConfig(ScreenTime.Config c) {
        if (dead) return;
        cfg = c;
        update(snap);
    }

    void update(IslandSnapshot s) {
        if (dead || s == null) return;
        snap = s;
        String st = s.structure();
        boolean structural = !st.equals(structure);
        structure = st;
        int want = targetMode(s);
        if (want != mode) {
            go(want);
        } else if (structural && mode == M_COMPACT) {
            compact.swap(s);
        } else if (structural && mode == M_EXPANDED) {
            panel.bind(s);
            resizeExpanded();
        } else {
            if (compact != null && mode == M_COMPACT) compact.values(s, true);
            if (panel != null && mode == M_EXPANDED) panel.values(s);
        }
    }

    void expand() {
        if (dead || mode != M_COMPACT) return;
        haptic(HapticFeedbackConstants.VIRTUAL_KEY);
        go(M_EXPANDED);
    }

    void collapse() {
        if (dead || mode != M_EXPANDED) return;
        h.removeCallbacks(autoCollapse);
        mode = M_COMPACT; // so targetMode() does not keep it open
        int want = targetMode(snap);
        mode = M_EXPANDED;
        go(want);
    }

    void onConfigurationChanged() {
        if (dead) return;
        geometry();
        if (attached) {
            float[] target = targetShape(mode);
            if (shapeAnim != null) shapeAnim.cancel();
            curW = target[0]; curH = target[1]; curR = target[2]; curA = target[3];
            capA = capTarget(mode);
            setWindow(mode, Math.round(curW), Math.round(curH));
            placeCapsule();
            root.invalidate();
            cap.invalidate();
        }
    }

    void destroy() {
        dead = true;
        h.removeCallbacksAndMessages(null);
        if (shapeAnim != null) shapeAnim.cancel();
        detach();
    }

    // ---- modes -----------------------------------------------------------------------------
    private int targetMode(IslandSnapshot s) {
        boolean content = s.kind != IslandSnapshot.NONE;
        if (fullscreen && (cfg.hideFull || !content)) return M_HIDDEN;
        if (mode == M_EXPANDED && (content || !s.tasks.isEmpty())) return M_EXPANDED;
        if (content) return M_COMPACT;
        if (landscape) return M_HIDDEN;
        return cfg.islandIdle ? M_IDLE : M_HIDDEN;
    }

    /** Body shape {width, height, radius, alpha}; idle and hidden have no body. */
    private float[] targetShape(int m) {
        switch (m) {
            case M_COMPACT: return new float[]{compactW, compactH, compactH / 2f, 1f};
            case M_EXPANDED: return new float[]{expandedW, expandedH, dp(30), 1f};
            default: return new float[]{idleW * 0.36f, 0f, 0f, 1f};
        }
    }

    private float capTarget(int m) { return m == M_HIDDEN || (landscape && m == M_IDLE) ? 0f : landscape ? 0f : 1f; }

    private void go(int to) {
        if (to != M_HIDDEN && !attached && !attach()) return;
        if (!attached) { mode = to; return; }
        int from = mode;
        mode = to;
        h.removeCallbacks(autoCollapse);
        if (to == M_COMPACT) compact.bind(snap);
        if (to == M_EXPANDED) {
            panel.bind(snap);
            measurePanel();
            h.postDelayed(autoCollapse, EXPANDED_IDLE_MS);
        }
        animateShape(from, to);
    }

    private void measurePanel() {
        panel.measure(View.MeasureSpec.makeMeasureSpec(expandedW, View.MeasureSpec.EXACTLY),
                View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED));
        expandedH = Math.max(compactH + dp(20), panel.getMeasuredHeight());
    }

    private void resizeExpanded() {
        int before = expandedH;
        measurePanel();
        if (before != expandedH) animateShape(M_EXPANDED, M_EXPANDED);
    }

    /** Springs the black shape from where it is now to the target of mode {@code to}. */
    private void animateShape(final int from, final int to) {
        if (shapeAnim != null) shapeAnim.cancel();
        final float a0 = curA;
        float[] t = targetShape(to);
        final float w1 = t[0], h1 = t[1], r1 = t[2], a1 = t[3];
        if (curH <= 0.5f) { curW = idleW * 0.36f; curR = 0f; } // the body drops out from under the camera, neck-wide
        final float sw = curW, sh = curH, sr = curR;
        final float ca0 = capA, ca1 = capTarget(to), cs0 = ca0 == 0f ? 0.6f : capS;
        final float c0 = compact.getAlpha(), p0 = panel.getAlpha();
        final float cTarget = to == M_COMPACT ? 1f : 0f, pTarget = to == M_EXPANDED ? 1f : 0f;
        if (cTarget > 0) compact.setVisibility(View.VISIBLE);
        if (pTarget > 0) panel.setVisibility(View.VISIBLE);
        int ww = (int) Math.ceil(Math.max(sw, w1) + 0.12f * Math.abs(w1 - sw)) + 2;
        int wh = (int) Math.ceil(Math.max(sh, h1) + 0.12f * Math.abs(h1 - sh)) + 2;
        setWindow(to, ww, wh);
        shapeAnim = ValueAnimator.ofFloat(0f, 1f);
        boolean big = to == M_EXPANDED || from == M_EXPANDED;
        shapeAnim.setDuration(big ? 620 : 540);
        final TimeInterpolator spring = new Spring(big ? 0.74f : 0.7f, big ? 10.5f : 11.5f);
        shapeAnim.addUpdateListener(new ValueAnimator.AnimatorUpdateListener() {
            @Override public void onAnimationUpdate(ValueAnimator a) {
                float p = a.getAnimatedFraction(), v = spring.getInterpolation(p);
                curW = sw + (w1 - sw) * v;
                curH = sh + (h1 - sh) * v;
                curR = Math.max(1f, sr + (r1 - sr) * v);
                curH = Math.max(0f, curH);
                curA = a0 + (a1 - a0) * clamp(p / 0.35f);
                capA = ca0 + (ca1 - ca0) * clamp(p / 0.4f);
                capS = cs0 + (1f - cs0) * v;
                fade(compact, c0, cTarget, p, 0.12f, 0.42f);
                fade(panel, p0, pTarget, p, 0.18f, 0.45f);
                root.invalidate();
                cap.invalidate();
            }
        });
        shapeAnim.addListener(new AnimatorListenerAdapter() {
            boolean cancelled;
            @Override public void onAnimationCancel(Animator a) { cancelled = true; }
            @Override public void onAnimationEnd(Animator a) {
                if (cancelled || dead) return;
                curW = w1; curH = h1; curR = r1; curA = a1;
                capA = ca1; capS = 1f;
                cap.invalidate();
                fade(compact, c0, cTarget, 1f, 0f, 1f);
                fade(panel, p0, pTarget, 1f, 0f, 1f);
                if (cTarget == 0f) compact.setVisibility(View.INVISIBLE);
                if (pTarget == 0f) panel.setVisibility(View.INVISIBLE);
                if (mode == M_HIDDEN) detach();
                else setWindow(mode, (int) Math.ceil(w1), (int) Math.ceil(h1));
                root.invalidate();
            }
        });
        shapeAnim.start();
    }

    /** Fades a content layer in (after the shape has grown a bit) or out (quickly), with a light blur. */
    private void fade(View v, float from, float target, float p, float delay, float span) {
        float a;
        if (target > from) a = from + (target - from) * clamp((p - delay) / span);
        else a = from + (target - from) * clamp(p / Math.max(0.01f, span * 0.55f));
        v.setAlpha(a);
        float s = 0.92f + 0.08f * a;
        v.setScaleX(s);
        v.setScaleY(s);
        v.setTranslationY((1f - a) * -dp(6));
        if (Build.VERSION.SDK_INT >= 31) {
            try {
                float r = (1f - a) * dp(6);
                v.setRenderEffect(r < 0.5f ? null : RenderEffect.createBlurEffect(r, r, Shader.TileMode.DECAL));
            } catch (Throwable ignored) {}
        }
    }

    static float clamp(float x) { return x < 0f ? 0f : x > 1f ? 1f : x; }

    // ---- window ----------------------------------------------------------------------------
    private int flags(int m) {
        int f = WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
                | WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS
                | WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED;
        if (m == M_IDLE || m == M_HIDDEN) f |= WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE;
        if (m == M_EXPANDED) f |= WindowManager.LayoutParams.FLAG_WATCH_OUTSIDE_TOUCH;
        return f;
    }

    private void setWindow(int m, int w, int hgt) {
        if (lp == null) return;
        lp.width = Math.max(1, w);
        lp.height = Math.max(1, hgt);
        lp.x = centerX - lp.width / 2;
        lp.y = bodyY;
        lp.flags = flags(m);
        if (attached) {
            try { wm.updateViewLayout(root, lp); } catch (Throwable t) { Log.w(ScreenTime.TAG, "island layout", t); }
        }
    }

    /** The capsule window: around the camera down to the body, never touchable. */
    private void placeCapsule() {
        if (capLp == null) return;
        capLp.width = idleW;
        capLp.height = Math.max(idleH, bodyY - top);
        capLp.x = centerX - idleW / 2;
        capLp.y = top;
        if (attached) {
            try { wm.updateViewLayout(cap, capLp); } catch (Throwable t) { Log.w(ScreenTime.TAG, "capsule layout", t); }
        }
    }

    private WindowManager.LayoutParams params(int type, int flags) {
        WindowManager.LayoutParams p = new WindowManager.LayoutParams(1, 1, type, flags, PixelFormat.TRANSLUCENT);
        p.gravity = Gravity.TOP | Gravity.LEFT;
        p.windowAnimations = 0;
        if (Build.VERSION.SDK_INT >= 28) p.layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
        if (Build.VERSION.SDK_INT >= 30) p.setFitInsetsTypes(0);
        return p;
    }

    private boolean attach() {
        if (dead) return false;
        if (root == null) build();
        geometry();
        // An accessibility overlay is not hidden by system Settings and sits above the status bar,
        // so the whole island can be tapped. Otherwise an ordinary app overlay.
        int type = a11y ? WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY
                : Build.VERSION.SDK_INT >= 26 ? WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
                : WindowManager.LayoutParams.TYPE_PHONE;
        lp = params(type, flags(M_HIDDEN));
        lp.setTitle("LiraIsland");
        capLp = params(type, flags(M_HIDDEN));
        capLp.setTitle("LiraIslandCamera");
        curW = idleW * 0.36f; curH = 0f; curR = 0f; curA = 1f;
        capA = 0f; capS = 0.6f;
        compact.setAlpha(0f); compact.setVisibility(View.INVISIBLE);
        panel.setAlpha(0f); panel.setVisibility(View.INVISIBLE);
        setWindow(M_HIDDEN, 1, 1);
        placeCapsule();
        try {
            wm.addView(cap, capLp);
            try {
                wm.addView(root, lp);
            } catch (Throwable t) {
                try { wm.removeView(cap); } catch (Throwable ignored) {}
                throw t;
            }
            attached = true;
            fullscreen = false;
            mode = M_HIDDEN;
            return true;
        } catch (Throwable t) {
            Log.w(ScreenTime.TAG, "island", t);
            return false;
        }
    }

    private void detach() {
        if (!attached) return;
        try { wm.removeView(root); } catch (Throwable t) { Log.w(ScreenTime.TAG, "island detach", t); }
        try { wm.removeView(cap); } catch (Throwable t) { Log.w(ScreenTime.TAG, "capsule detach", t); }
        attached = false;
        mode = M_HIDDEN;
    }

    private void geometry() {
        android.util.DisplayMetrics dm = ctx.getResources().getDisplayMetrics();
        screenW = dm.widthPixels;
        landscape = ctx.getResources().getConfiguration().orientation == Configuration.ORIENTATION_LANDSCAPE;
        sbH = statusBarHeight();
        Rect cut = null;
        if (Build.VERSION.SDK_INT >= 29) {
            try {
                DisplayCutout c = wm.getDefaultDisplay().getCutout();
                if (c != null) {
                    for (Rect r : c.getBoundingRects()) {
                        if (r.top <= dp(4) && r.height() > 0 && r.bottom <= sbH * 2 && r.width() < screenW / 2
                                && Math.abs(r.centerX() - screenW / 2f) < screenW * 0.22f) { cut = r; break; }
                    }
                }
            } catch (Throwable ignored) {}
        }
        idleH = Math.max(dp(20), Math.min(dp(34), sbH - dp(7)));
        if (cut != null) {
            centerX = cut.centerX();
            idleH = Math.min(Math.max(idleH, cut.height() + dp(6)), Math.max(idleH, sbH));
            top = Math.max(0, cut.centerY() - idleH / 2);
            idleW = Math.max(Math.round(idleH * 3.3f), cut.width() + dp(48));
        } else {
            centerX = screenW / 2;
            top = Math.max(0, (sbH - idleH) / 2);
            idleW = Math.round(idleH * 3.3f);
        }
        bodyY = Math.max(sbH + dp(1), top + idleH + dp(2));
        rowH = dp(30);
        compactH = rowH + dp(10);
        compactW = Math.min(screenW - dp(24), dp(258));
        expandedW = Math.min(screenW - dp(16), dp(420));
        if (expandedH < compactH) expandedH = compactH;
        if (compact != null) {
            FrameLayout.LayoutParams cl = (FrameLayout.LayoutParams) compact.getLayoutParams();
            cl.width = compactW - dp(36);
            cl.height = rowH;
            cl.topMargin = (compactH - rowH) / 2;
            compact.setLayoutParams(cl);
            FrameLayout.LayoutParams pl = (FrameLayout.LayoutParams) panel.getLayoutParams();
            pl.width = expandedW;
            panel.setLayoutParams(pl);
            panel.setPadding(dp(18), dp(14), dp(18), dp(14));
        }
    }

    private int statusBarHeight() {
        try {
            int id = ctx.getResources().getIdentifier("status_bar_height", "dimen", "android");
            if (id != 0) {
                int v = ctx.getResources().getDimensionPixelSize(id);
                if (v > 0) return v;
            }
        } catch (Throwable ignored) {}
        return dp(28);
    }

    private void haptic(int type) {
        try { if (root != null) root.performHapticFeedback(type); } catch (Throwable ignored) {}
    }

    private void setFullscreen(boolean f) {
        if (f == fullscreen) return;
        fullscreen = f;
        update(snap);
    }

    private void build() {
        root = new IslandView(ctx);
        cap = new CapsuleView(ctx);
        cap.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
        root.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_YES);
        compact = new CompactRow(ctx);
        panel = new ExpandedPanel(ctx);
        root.addView(compact, new FrameLayout.LayoutParams(dp(200), dp(30), Gravity.TOP | Gravity.CENTER_HORIZONTAL));
        root.addView(panel, new FrameLayout.LayoutParams(dp(360), ViewGroup.LayoutParams.WRAP_CONTENT, Gravity.TOP | Gravity.CENTER_HORIZONTAL));
        root.setOnApplyWindowInsetsListener(new View.OnApplyWindowInsetsListener() {
            @Override public WindowInsets onApplyWindowInsets(View v, WindowInsets in) {
                if (Build.VERSION.SDK_INT >= 30) {
                    int bar = in.getInsetsIgnoringVisibility(WindowInsets.Type.statusBars()).top;
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
    }

    static TextView text(Context c, float sp, int color, boolean bold) {
        TextView t = new TextView(c);
        t.setTextSize(TypedValue.COMPLEX_UNIT_SP, sp);
        t.setTextColor(color);
        t.setTypeface(Typeface.create(bold ? "sans-serif-medium" : "sans-serif", Typeface.NORMAL));
        t.setSingleLine(true);
        t.setEllipsize(TextUtils.TruncateAt.END);
        t.setIncludeFontPadding(false);
        return t;
    }

    static String clock(long ms) {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(ms);
        return String.format(Locale.ROOT, "%02d:%02d", c.get(Calendar.HOUR_OF_DAY), c.get(Calendar.MINUTE));
    }

    private int limitColor(IslandSnapshot s) {
        float f = s.limit > 0 ? (float) s.used / s.limit : 0f;
        return f >= 1f ? RED : f >= 0.8f ? WARN : cfg.accent;
    }

    private int curfewColor(IslandSnapshot s) {
        return s.curfewStart - s.now <= 5 * 60_000L ? RED : AMBER;
    }

    // ---- views -----------------------------------------------------------------------------

    /** Draws the black shape and clips the content to it. */
    final class IslandView extends FrameLayout {
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Path path = new Path();
        private final RectF rect = new RectF();

        IslandView(Context c) {
            super(c);
            setWillNotDraw(false);
            setClipChildren(true);
            paint.setColor(BLACK);
        }

        RectF shapeRect() {
            float w = curW * press, hh = curH * press;
            float l = (getWidth() - w) / 2f;
            rect.set(l, 0, l + w, hh);
            return rect;
        }

        @Override protected void dispatchDraw(Canvas canvas) {
            if (curA <= 0.001f || curH < 0.5f) return;
            RectF r = shapeRect();
            float rad = Math.min(curR * press, Math.min(r.width(), r.height()) / 2f);
            paint.setAlpha(Math.round(255 * curA));
            canvas.drawRoundRect(r, rad, rad, paint);
            path.reset();
            path.addRoundRect(r, rad, rad, Path.Direction.CW);
            int save = canvas.save();
            canvas.clipPath(path);
            if (press != 1f) canvas.scale(press, press, getWidth() / 2f, 0);
            super.dispatchDraw(canvas);
            canvas.restoreToCount(save);
        }

        @Override public boolean onTouchEvent(MotionEvent e) {
            int a = e.getActionMasked();
            if (a == MotionEvent.ACTION_OUTSIDE) {
                if (mode == M_EXPANDED) collapse();
                return false;
            }
            boolean inside = shapeRect().contains(e.getX(), e.getY());
            if (mode == M_COMPACT) {
                if (a == MotionEvent.ACTION_DOWN && inside) { pressTo(0.95f); return true; }
                if (a == MotionEvent.ACTION_UP) { pressTo(1f); if (inside) expand(); return true; }
                if (a == MotionEvent.ACTION_CANCEL) { pressTo(1f); return true; }
                return true;
            }
            if (mode == M_EXPANDED) {
                if (a == MotionEvent.ACTION_UP) collapse();
                return true;
            }
            return false;
        }

        private void pressTo(float target) {
            if (pressAnim != null) pressAnim.cancel();
            pressAnim = ValueAnimator.ofFloat(press, target);
            pressAnim.setDuration(target < 1f ? 120 : 380);
            pressAnim.setInterpolator(target < 1f ? new DecelerateInterpolator() : new Spring(0.55f, 12f));
            pressAnim.addUpdateListener(new ValueAnimator.AnimatorUpdateListener() {
                @Override public void onAnimationUpdate(ValueAnimator v) {
                    press = (Float) v.getAnimatedValue();
                    invalidate();
                }
            });
            pressAnim.start();
        }
    }

    /**
     * The capsule around the front camera and, while the body is out, a short neck with soft
     * inner corners joining it to the body, like a drop hanging from the camera. It is narrow,
     * so the clock and icons of the status bar on both sides stay visible.
     */
    final class CapsuleView extends View {
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Path neck = new Path(), corner = new Path();
        private final RectF r = new RectF();

        CapsuleView(Context c) {
            super(c);
            paint.setColor(BLACK);
        }

        @Override protected void onDraw(Canvas canvas) {
            if (capA <= 0.001f) return;
            float w = getWidth(), hh = getHeight(), cx = w / 2f;
            paint.setAlpha(Math.round(255 * capA));
            float cw = idleW * capS, ch = idleH * capS;
            r.set(cx - cw / 2f, (idleH - ch) / 2f, cx + cw / 2f, (idleH + ch) / 2f);
            canvas.drawRoundRect(r, ch / 2f, ch / 2f, paint);
            // neck grows with the body
            float n = clamp(curH / dp(12)) * curA;
            float gapTop = idleH * 0.5f;
            if (n <= 0.01f || hh <= idleH) return;
            float nw = idleW * 0.36f * n, f = Math.min(dp(6), hh - idleH) * n;
            neck.reset();
            neck.addRect(cx - nw / 2f, gapTop, cx + nw / 2f, hh, Path.Direction.CW);
            for (int side = -1; side <= 1; side += 2) {
                float x0 = cx + side * nw / 2f;
                corner.reset();
                corner.addRect(Math.min(x0, x0 + side * f), hh - f, Math.max(x0, x0 + side * f), hh, Path.Direction.CW);
                Path hole = new Path();
                hole.addCircle(x0 + side * f, hh - f, f, Path.Direction.CW);
                corner.op(hole, Path.Op.DIFFERENCE);
                neck.op(corner, Path.Op.UNION);
            }
            canvas.drawPath(neck, paint);
        }
    }

    /** One line under the camera: icon, title, value or "+N". */
    final class CompactRow extends LinearLayout {
        final IconView icon;
        final TextView title;
        final RollingText value;
        final TextView badge;
        private ValueAnimator swapAnim;

        CompactRow(Context c) {
            super(c);
            setOrientation(HORIZONTAL);
            setGravity(Gravity.CENTER_VERTICAL);
            icon = new IconView(c);
            addView(icon, new LayoutParams(dp(22), dp(22)));
            title = text(c, 13.5f, WHITE, true);
            LayoutParams tl = new LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
            tl.leftMargin = dp(9);
            tl.rightMargin = dp(8);
            addView(title, tl);
            value = new RollingText(c, 14f, true);
            addView(value, new LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(22)));
            badge = text(c, 12f, WHITE, true);
            GradientDrawable bg = new GradientDrawable();
            bg.setColor(DIM);
            bg.setCornerRadius(dp(10));
            badge.setBackground(bg);
            badge.setPadding(dp(7), dp(3), dp(7), dp(3));
            LayoutParams bl = new LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            bl.leftMargin = dp(6);
            addView(badge, bl);
        }

        String valueText() { return value.text; }

        void bind(IslandSnapshot s) {
            switch (s.kind) {
                case IslandSnapshot.CURFEW_SOON:
                    icon.moon(MOON);
                    title.setText("Комендантский час");
                    break;
                case IslandSnapshot.CURFEW_ON:
                    icon.moon(MOON);
                    title.setText("Пора отдыхать");
                    break;
                case IslandSnapshot.LIMIT:
                    icon.app(s.limitIcon);
                    title.setText(s.used >= s.limit ? "Лимит исчерпан" : s.limitLabel);
                    break;
                case IslandSnapshot.TASK:
                    icon.task(cfg.accent);
                    ScreenTime.Task t = s.firstOpen();
                    title.setText(t == null ? "" : t.title);
                    break;
                default:
                    title.setText("");
            }
            values(s, false);
        }

        void values(IslandSnapshot s, boolean animate) {
            badge.setVisibility(GONE);
            value.setVisibility(VISIBLE);
            switch (s.kind) {
                case IslandSnapshot.CURFEW_SOON: {
                    long left = s.curfewStart - s.now;
                    icon.ring(1f - clamp((float) left / IslandSnapshot.CURFEW_LEAD), curfewColor(s));
                    value.set(IslandSnapshot.countdown(left), curfewColor(s), animate);
                    break;
                }
                case IslandSnapshot.CURFEW_ON:
                    icon.ring(-1f, 0);
                    value.set("до " + clock(s.curfewEnd), GREY, animate);
                    break;
                case IslandSnapshot.LIMIT: {
                    int col = limitColor(s);
                    icon.ring(clamp((float) s.used / s.limit), col);
                    String name = s.used >= s.limit ? "Лимит исчерпан" : s.limitLabel;
                    if (!TextUtils.equals(title.getText(), name)) title.setText(name);
                    title.setTextColor(s.used >= s.limit ? RED : WHITE);
                    value.set((s.used / 60_000L) + "/" + (s.limit / 60_000L), col, animate);
                    break;
                }
                case IslandSnapshot.TASK: {
                    ScreenTime.Task t = s.firstOpen();
                    if (t != null) icon.ring(clamp((float) (s.now - t.start) / (t.end - t.start)), cfg.accent);
                    if (s.openTasks > 1) {
                        value.setVisibility(GONE);
                        badge.setVisibility(VISIBLE);
                        badge.setText("+" + (s.openTasks - 1));
                    } else if (t != null) {
                        value.set("до " + clock(t.end), GREY, animate);
                    }
                    break;
                }
                default:
                    value.set("", GREY, false);
            }
            if (s.kind != IslandSnapshot.LIMIT) title.setTextColor(WHITE);
        }

        /** Content of a different kind: quick blur-fade out, swap, back in. */
        void swap(final IslandSnapshot s) {
            if (swapAnim != null) swapAnim.cancel();
            swapAnim = ValueAnimator.ofFloat(0f, 1f);
            swapAnim.setDuration(380);
            final boolean[] swapped = {false};
            swapAnim.addUpdateListener(new ValueAnimator.AnimatorUpdateListener() {
                @Override public void onAnimationUpdate(ValueAnimator a) {
                    float p = a.getAnimatedFraction();
                    if (p >= 0.4f && !swapped[0]) { swapped[0] = true; bind(snap); }
                    float alpha = p < 0.4f ? 1f - p / 0.4f : (p - 0.4f) / 0.6f;
                    setAlpha(alpha);
                    // old content leaves upwards, new content arrives from below
                    setTranslationY(p < 0.4f ? -dp(5) * (p / 0.4f) : dp(5) * (1f - (p - 0.4f) / 0.6f));
                    float sc = 0.94f + 0.06f * alpha;
                    setScaleX(sc);
                    setScaleY(sc);
                    if (Build.VERSION.SDK_INT >= 31) {
                        try {
                            float r = (1f - alpha) * dp(5);
                            setRenderEffect(r < 0.5f ? null : RenderEffect.createBlurEffect(r, r, Shader.TileMode.DECAL));
                        } catch (Throwable ignored) {}
                    }
                }
            });
            swapAnim.addListener(new AnimatorListenerAdapter() {
                @Override public void onAnimationEnd(Animator a) {
                    if (!swapped[0]) bind(snap);
                    setAlpha(1f);
                    setTranslationY(0f);
                    setScaleX(1f);
                    setScaleY(1f);
                    if (Build.VERSION.SDK_INT >= 31) try { setRenderEffect(null); } catch (Throwable ignored) {}
                }
            });
            swapAnim.start();
        }
    }

    /** The opened island: curfew, limit and up to three tasks you can tick. */
    final class ExpandedPanel extends LinearLayout {
        final ArrayList<TaskRow> rows = new ArrayList<TaskRow>();
        private String keys = "";
        private RollingText curfewValue;
        private TextView limitText;
        private Bar limitBar;

        ExpandedPanel(Context c) {
            super(c);
            setOrientation(VERTICAL);
        }

        void bind(IslandSnapshot s) {
            StringBuilder k = new StringBuilder().append(s.curfewStart > 0 ? (s.now >= s.curfewStart ? "on" : "soon") : "-")
                    .append('|').append(s.limitPkg).append('|');
            List<ScreenTime.Task> shown = IslandSnapshot.firstN(s.tasks, MAX_ROWS);
            for (ScreenTime.Task t : shown) k.append(t.key).append(',');
            k.append('|').append(s.tasks.size());
            if (k.toString().equals(keys)) {
                for (int i = 0; i < rows.size() && i < shown.size(); i++) rows.get(i).sync(shown.get(i));
                values(s);
                return;
            }
            keys = k.toString();
            removeAllViews();
            rows.clear();
            curfewValue = null;
            limitText = null;
            limitBar = null;
            boolean first = true;
            if (s.curfewStart > 0) {
                LinearLayout r = row();
                IconView ic = new IconView(getContext());
                ic.moon(MOON);
                r.addView(ic, new LayoutParams(dp(34), dp(34)));
                LinearLayout col = column();
                boolean on = s.now >= s.curfewStart;
                col.addView(text(getContext(), 15f, WHITE, true));
                ((TextView) col.getChildAt(0)).setText(on ? "Комендантский час" : "Скоро комендантский час");
                TextView sub = text(getContext(), 12.5f, GREY, false);
                sub.setText(on ? "Отложите телефон · до " + clock(s.curfewEnd) : "С " + clock(s.curfewStart) + " до " + clock(s.curfewEnd));
                col.addView(sub);
                r.addView(col, new LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
                curfewValue = new RollingText(getContext(), on ? 15f : 24f, true);
                r.addView(curfewValue, new LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(on ? 22 : 32)));
                addView(r);
                first = false;
            }
            if (s.limitPkg != null) {
                if (!first) addView(divider());
                LinearLayout r = row();
                IconView ic = new IconView(getContext());
                ic.app(s.limitIcon);
                r.addView(ic, new LayoutParams(dp(34), dp(34)));
                LinearLayout col = column();
                TextView name = text(getContext(), 15f, WHITE, true);
                name.setText(s.limitLabel);
                col.addView(name);
                limitText = text(getContext(), 12.5f, GREY, false);
                col.addView(limitText);
                limitBar = new Bar(getContext());
                LayoutParams bl = new LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(4));
                bl.topMargin = dp(7);
                col.addView(limitBar, bl);
                r.addView(col, new LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
                addView(r);
                first = false;
            }
            if (!s.tasks.isEmpty()) {
                if (!first) addView(divider());
                TextView head = text(getContext(), 11.5f, GREY, true);
                head.setText("СЕЙЧАС" + (s.tasks.size() > 1 ? " · " + s.tasks.size() : ""));
                head.setLetterSpacing(0.08f);
                LayoutParams hl = new LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
                hl.topMargin = dp(first ? 2 : 10);
                hl.bottomMargin = dp(2);
                addView(head, hl);
                for (ScreenTime.Task t : shown) {
                    TaskRow tr = new TaskRow(getContext(), t);
                    rows.add(tr);
                    addView(tr);
                }
                if (s.tasks.size() > MAX_ROWS) {
                    TextView more = text(getContext(), 13f, cfg.accent, true);
                    int n = s.tasks.size() - MAX_ROWS;
                    more.setText("Ещё " + n + " — открыть Лиру");
                    more.setPadding(0, dp(10), 0, dp(2));
                    more.setOnClickListener(new OnClickListener() {
                        @Override public void onClick(View v) {
                            haptic(HapticFeedbackConstants.VIRTUAL_KEY);
                            collapse();
                            listener.onOpenApp();
                        }
                    });
                    addView(more);
                }
            }
            values(s);
        }

        private LinearLayout row() {
            LinearLayout r = new LinearLayout(getContext());
            r.setOrientation(HORIZONTAL);
            r.setGravity(Gravity.CENTER_VERTICAL);
            r.setPadding(0, dp(8), 0, dp(8));
            return r;
        }

        private LinearLayout column() {
            LinearLayout col = new LinearLayout(getContext());
            col.setOrientation(VERTICAL);
            col.setPadding(dp(12), 0, dp(10), 0);
            return col;
        }

        private View divider() {
            View v = new View(getContext());
            v.setBackgroundColor(LINE);
            LayoutParams l = new LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, Math.max(1, dp(1)));
            l.topMargin = dp(4);
            l.bottomMargin = dp(4);
            v.setLayoutParams(l);
            return v;
        }

        void values(IslandSnapshot s) {
            if (curfewValue != null) {
                if (s.now >= s.curfewStart) curfewValue.set("до " + clock(s.curfewEnd), GREY, true);
                else curfewValue.set(IslandSnapshot.countdown(s.curfewStart - s.now), curfewColor(s), true);
            }
            if (limitText != null && s.limit > 0) {
                long u = s.used / 60_000L, l = s.limit / 60_000L;
                long left = (s.limit - s.used) / 60_000L;
                String t = u + " из " + l + " мин · " + (s.used >= s.limit ? "превышен на " + Math.max(1, -left) + " мин" : "осталось " + left + " мин");
                if (!TextUtils.equals(limitText.getText(), t)) limitText.setText(t);
                limitBar.set(clamp((float) s.used / s.limit), limitColor(s));
            }
        }
    }

    /** A task in the opened island: tap anywhere on it to tick it. */
    final class TaskRow extends LinearLayout {
        ScreenTime.Task task;
        boolean done;
        final CheckView check;
        final TextView title, time;

        TaskRow(Context c, ScreenTime.Task t) {
            super(c);
            task = t;
            done = t.done;
            setOrientation(HORIZONTAL);
            setGravity(Gravity.CENTER_VERTICAL);
            setPadding(0, dp(9), 0, dp(9));
            check = new CheckView(c, cfg.accent);
            addView(check, new LayoutParams(dp(26), dp(26)));
            LinearLayout col = new LinearLayout(c);
            col.setOrientation(VERTICAL);
            col.setPadding(dp(12), 0, 0, 0);
            title = text(c, 14.5f, WHITE, true);
            title.setText(t.title);
            time = text(c, 12f, GREY, false);
            time.setText(clock(t.start) + " – " + clock(t.end));
            col.addView(title);
            LayoutParams tl = new LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            tl.topMargin = dp(3);
            col.addView(time, tl);
            addView(col, new LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
            check.set(done, false);
            title.setAlpha(done ? 0.5f : 1f);
            setClickable(true);
            setContentDescription(t.title);
            setOnClickListener(new OnClickListener() {
                @Override public void onClick(View v) { toggle(); }
            });
        }

        void toggle() {
            done = !done;
            check.set(done, true);
            title.animate().alpha(done ? 0.5f : 1f).setDuration(220).start();
            haptic(Build.VERSION.SDK_INT >= 30 ? HapticFeedbackConstants.CONFIRM : HapticFeedbackConstants.VIRTUAL_KEY);
            h.removeCallbacks(autoCollapse);
            h.postDelayed(autoCollapse, EXPANDED_IDLE_MS);
            listener.onToggle(task.key, done);
        }

        void sync(ScreenTime.Task t) {
            task = t;
            if (t.done != done) {
                done = t.done;
                check.set(done, true);
                title.setAlpha(done ? 0.5f : 1f);
            }
        }

        @Override public boolean onTouchEvent(MotionEvent e) {
            if (e.getActionMasked() == MotionEvent.ACTION_DOWN) animate().scaleX(0.98f).scaleY(0.98f).setDuration(90).start();
            else if (e.getActionMasked() == MotionEvent.ACTION_UP || e.getActionMasked() == MotionEvent.ACTION_CANCEL)
                animate().scaleX(1f).scaleY(1f).setDuration(220).start();
            return super.onTouchEvent(e);
        }
    }

    // ---- small drawing views ---------------------------------------------------------------

    /** Underdamped spring step response: settles at 1 with a small overshoot, like iOS. */
    static final class Spring implements TimeInterpolator {
        private final double zeta, omega, wd, k;

        Spring(float dampingRatio, float frequency) {
            zeta = dampingRatio;
            omega = frequency;
            wd = omega * Math.sqrt(1 - zeta * zeta);
            k = zeta / Math.sqrt(1 - zeta * zeta);
        }

        @Override public float getInterpolation(float t) {
            if (t >= 1f) return 1f;
            double e = Math.exp(-zeta * omega * t);
            return (float) (1 - e * (Math.cos(wd * t) + k * Math.sin(wd * t)));
        }
    }

    /** Text whose changed characters roll in from below (for the countdown and counters). */
    final class RollingText extends View {
        final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        String text = "", old = "";
        float progress = 1f;
        private ValueAnimator anim;

        RollingText(Context c, float sp, boolean bold) {
            super(c);
            paint.setTextSize(TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP, sp, c.getResources().getDisplayMetrics()));
            paint.setTypeface(Typeface.create(bold ? "sans-serif-medium" : "sans-serif", Typeface.NORMAL));
            paint.setFontFeatureSettings("tnum");
            paint.setColor(WHITE);
        }

        void set(String t, int color, boolean animate) {
            if (t == null) t = "";
            boolean colorChanged = paint.getColor() != color;
            paint.setColor(color);
            if (t.equals(text)) { if (colorChanged) invalidate(); return; }
            boolean widthChange = paint.measureText(t) != paint.measureText(text);
            old = text;
            text = t;
            if (anim != null) anim.cancel();
            if (animate && !old.isEmpty() && getVisibility() == VISIBLE && isAttachedToWindow()) {
                progress = 0f;
                anim = ValueAnimator.ofFloat(0f, 1f);
                anim.setDuration(360);
                anim.setInterpolator(new DecelerateInterpolator(1.6f));
                anim.addUpdateListener(new ValueAnimator.AnimatorUpdateListener() {
                    @Override public void onAnimationUpdate(ValueAnimator a) {
                        progress = (Float) a.getAnimatedValue();
                        invalidate();
                    }
                });
                anim.start();
            } else {
                progress = 1f;
            }
            if (widthChange) requestLayout();
            invalidate();
        }

        @Override protected void onMeasure(int wSpec, int hSpec) {
            int w = (int) Math.ceil(Math.max(paint.measureText(text), progress < 1f ? paint.measureText(old) : 0f)) + dp(1);
            Paint.FontMetrics fm = paint.getFontMetrics();
            int hh = (int) Math.ceil(fm.descent - fm.ascent);
            setMeasuredDimension(resolveSize(w, wSpec), resolveSize(hh, hSpec));
        }

        @Override protected void onDraw(Canvas canvas) {
            Paint.FontMetrics fm = paint.getFontMetrics();
            float hh = getHeight();
            float base = (hh - (fm.descent - fm.ascent)) / 2f - fm.ascent;
            int save = canvas.save();
            canvas.clipRect(0, 0, getWidth(), hh);
            int n = Math.max(text.length(), old.length());
            float xNew = getWidth(), xOld = getWidth();
            int alpha = paint.getAlpha();
            for (int i = 1; i <= n; i++) {
                String c = i <= text.length() ? text.substring(text.length() - i, text.length() - i + 1) : null;
                String o = i <= old.length() ? old.substring(old.length() - i, old.length() - i + 1) : null;
                if (c != null) xNew -= paint.measureText(c);
                if (o != null) xOld -= paint.measureText(o);
                boolean same = c != null && c.equals(o) && xNew == xOld;
                if (progress >= 1f || same) {
                    if (c != null) { paint.setAlpha(alpha); canvas.drawText(c, xNew, base, paint); }
                    continue;
                }
                if (o != null) {
                    paint.setAlpha(Math.round(alpha * (1f - progress)));
                    canvas.drawText(o, xOld, base - hh * 0.7f * progress, paint);
                }
                if (c != null) {
                    paint.setAlpha(Math.round(alpha * progress));
                    canvas.drawText(c, xNew, base + hh * 0.7f * (1f - progress), paint);
                }
            }
            paint.setAlpha(alpha);
            canvas.restoreToCount(save);
        }
    }

    /** Small round icon: crescent moon, task dot or app icon, with an optional progress ring. */
    final class IconView extends View {
        static final int MOON_T = 1, TASK_T = 2, APP_T = 3;
        private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG), stroke = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Path tmp = new Path(), tmp2 = new Path();
        private final RectF oval = new RectF();
        int type;
        int color = WHITE, ringColor = WHITE;
        float ring = -1f;
        Bitmap bmp;

        IconView(Context c) {
            super(c);
            stroke.setStyle(Paint.Style.STROKE);
            stroke.setStrokeCap(Paint.Cap.ROUND);
        }

        void moon(int c) { type = MOON_T; color = c; invalidate(); }
        void task(int c) { type = TASK_T; color = c; invalidate(); }
        void app(Bitmap b) { type = APP_T; bmp = b; invalidate(); }
        void ring(float f, int c) {
            if (f == ring && c == ringColor) return;
            ring = f;
            ringColor = c;
            invalidate();
        }

        @Override protected void onDraw(Canvas canvas) {
            float size = Math.min(getWidth(), getHeight()), cx = getWidth() / 2f, cy = getHeight() / 2f;
            float sw = Math.max(1.5f, size * 0.09f);
            float r = size / 2f;
            if (ring >= 0f) {
                stroke.setStrokeWidth(sw);
                oval.set(cx - r + sw / 2, cy - r + sw / 2, cx + r - sw / 2, cy + r - sw / 2);
                stroke.setColor(DIM);
                canvas.drawOval(oval, stroke);
                if (ring > 0f) {
                    stroke.setColor(ringColor);
                    canvas.drawArc(oval, -90f, 360f * ring, false, stroke);
                }
                r -= sw * 2.1f;
            }
            if (type == MOON_T) {
                fill.setColor(color);
                tmp.reset();
                tmp.addCircle(cx, cy, r * 0.92f, Path.Direction.CW);
                tmp2.reset();
                tmp2.addCircle(cx + r * 0.48f, cy - r * 0.36f, r * 0.78f, Path.Direction.CW);
                tmp.op(tmp2, Path.Op.DIFFERENCE);
                canvas.drawPath(tmp, fill);
            } else if (type == TASK_T) {
                fill.setColor(color);
                canvas.drawCircle(cx, cy, r * (ring >= 0f ? 0.5f : 0.42f), fill);
            } else if (type == APP_T) {
                if (bmp != null) {
                    BitmapShader sh = new BitmapShader(bmp, Shader.TileMode.CLAMP, Shader.TileMode.CLAMP);
                    Matrix m = new Matrix();
                    float s = (2 * r) / Math.max(1, Math.max(bmp.getWidth(), bmp.getHeight()));
                    m.setScale(s, s);
                    m.postTranslate(cx - r, cy - r);
                    sh.setLocalMatrix(m);
                    fill.setShader(sh);
                    oval.set(cx - r, cy - r, cx + r, cy + r);
                    canvas.drawRoundRect(oval, r * 0.45f, r * 0.45f, fill);
                    fill.setShader(null);
                } else {
                    fill.setColor(DIM);
                    canvas.drawCircle(cx, cy, r, fill);
                }
            }
        }
    }

    /** Round tick box that fills and draws its check mark. */
    final class CheckView extends View {
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Path check = new Path(), seg = new Path();
        private final int accent;
        private float p;
        private ValueAnimator anim;

        CheckView(Context c, int accent) {
            super(c);
            this.accent = accent;
            paint.setStrokeCap(Paint.Cap.ROUND);
            paint.setStrokeJoin(Paint.Join.ROUND);
        }

        boolean checked() { return p > 0.5f; }

        void set(boolean on, boolean animate) {
            float target = on ? 1f : 0f;
            if (anim != null) anim.cancel();
            if (!animate) { p = target; invalidate(); return; }
            anim = ValueAnimator.ofFloat(p, target);
            anim.setDuration(on ? 520 : 260);
            anim.setInterpolator(on ? new DecelerateInterpolator(1.4f) : new DecelerateInterpolator());
            anim.addUpdateListener(new ValueAnimator.AnimatorUpdateListener() {
                @Override public void onAnimationUpdate(ValueAnimator a) {
                    p = (Float) a.getAnimatedValue();
                    invalidate();
                }
            });
            anim.start();
        }

        @Override protected void onDraw(Canvas canvas) {
            float s = Math.min(getWidth(), getHeight()), cx = getWidth() / 2f, cy = getHeight() / 2f;
            float r = s / 2f - dp(1.5f);
            float fillP = clamp(p / 0.45f);
            // pop: grows past full size and settles
            float pop = fillP < 1f ? 0.55f + 0.6f * fillP : 1.15f - 0.15f * clamp((p - 0.45f) / 0.25f);
            paint.setStyle(Paint.Style.STROKE);
            paint.setStrokeWidth(dp(2));
            paint.setColor(GREY);
            paint.setAlpha(Math.round(255 * (1f - fillP)));
            canvas.drawCircle(cx, cy, r, paint);
            if (fillP > 0f) {
                paint.setStyle(Paint.Style.FILL);
                paint.setColor(accent);
                paint.setAlpha(Math.round(255 * fillP));
                canvas.drawCircle(cx, cy, r * Math.min(1.08f, pop), paint);
            }
            float cp = clamp((p - 0.3f) / 0.7f);
            if (cp > 0f) {
                check.reset();
                check.moveTo(cx - r * 0.42f, cy + r * 0.02f);
                check.lineTo(cx - r * 0.1f, cy + r * 0.34f);
                check.lineTo(cx + r * 0.46f, cy - r * 0.3f);
                PathMeasure pm = new PathMeasure(check, false);
                seg.reset();
                pm.getSegment(0, pm.getLength() * cp, seg, true);
                paint.setStyle(Paint.Style.STROKE);
                paint.setStrokeWidth(dp(2.4f));
                paint.setColor(BLACK);
                paint.setAlpha(255);
                canvas.drawPath(seg, paint);
            }
        }
    }

    /** Thin rounded bar. */
    final class Bar extends View {
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final RectF r = new RectF();
        private float f;
        private int color = WHITE;

        Bar(Context c) { super(c); }

        void set(float frac, int c) {
            if (frac == f && c == color) return;
            f = frac;
            color = c;
            invalidate();
        }

        @Override protected void onDraw(Canvas canvas) {
            float hh = getHeight(), w = getWidth();
            paint.setColor(DIM);
            r.set(0, 0, w, hh);
            canvas.drawRoundRect(r, hh / 2, hh / 2, paint);
            if (f > 0) {
                paint.setColor(color);
                r.set(0, 0, Math.max(hh, w * f), hh);
                canvas.drawRoundRect(r, hh / 2, hh / 2, paint);
            }
        }
    }
}

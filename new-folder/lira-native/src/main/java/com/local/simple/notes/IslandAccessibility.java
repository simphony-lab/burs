package com.local.simple.notes;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.content.Intent;
import android.util.Log;
import android.view.accessibility.AccessibilityEvent;

/**
 * Optional "island over everything" mode. Android hides ordinary app overlays inside system
 * Settings and below the status bar; a window that belongs to an accessibility service is not
 * hidden. This service asks for no events and cannot read the screen: it only lends its window
 * token to the island, which keeps living in ScreenTimeService (same ":screen" process).
 */
public class IslandAccessibility extends AccessibilityService {
    static volatile IslandAccessibility instance;

    @Override protected void onServiceConnected() {
        try {
            AccessibilityServiceInfo info = new AccessibilityServiceInfo();
            info.eventTypes = 0;
            info.feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC;
            info.notificationTimeout = 1000;
            info.flags = AccessibilityServiceInfo.DEFAULT;
            setServiceInfo(info);
        } catch (Throwable t) {
            Log.w(ScreenTime.TAG, "a11y info", t);
        }
        instance = this;
        ScreenTime.sync(this);
        ScreenTimeService.hostChanged();
    }

    @Override public void onAccessibilityEvent(AccessibilityEvent event) {}

    @Override public void onInterrupt() {}

    @Override public boolean onUnbind(Intent intent) {
        gone();
        return super.onUnbind(intent);
    }

    @Override public void onDestroy() {
        gone();
        super.onDestroy();
    }

    private void gone() {
        if (instance == this) {
            instance = null;
            ScreenTimeService.hostChanged();
        }
    }
}

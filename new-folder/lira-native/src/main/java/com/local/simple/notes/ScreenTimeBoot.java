package com.local.simple.notes;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** Restarts the screen-time tracker after a reboot or an app update. */
public class ScreenTimeBoot extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        String a = intent == null ? null : intent.getAction();
        if (Intent.ACTION_BOOT_COMPLETED.equals(a)
                || Intent.ACTION_MY_PACKAGE_REPLACED.equals(a)
                || "android.intent.action.QUICKBOOT_POWERON".equals(a)) {
            ScreenTime.sync(context);
        }
    }
}

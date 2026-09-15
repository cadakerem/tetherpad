package com.ps5bridge.screenguard;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.view.accessibility.AccessibilityEvent;
import android.util.Log;

/**
 * PS5Bridge ScreenGuard — AccessibilityService
 *
 * HID input Android'in kernel HID driver'i uzerinden ekrani uyandirinca
 * bu servis ACTION_SCREEN_ON yakalayip performGlobalAction(GLOBAL_ACTION_LOCK_SCREEN)
 * cagiriyor. Bu public Android API — OEM bagimsiz, Android 5+'te calisir.
 *
 * Avantaj vs service call power hacks:
 *  - Kernel seviyesindeki wakeUp() yarisiyla ugrasmaz
 *  - Ekran acilinca LOCK_SCREEN hemen cagrilir, kullanici sadece kara goruyor
 *  - Root gerektirmez
 *
 * Kullanim: Telefon Ayarlar > Erisilebilirlik > PS5 ScreenGuard > AC
 * Otomatik: ps5_bridge.py baslayinca intent gonderir (etkinleştirme hariç — 
 *           etkinlestirme tek seferlik manueldir, Android politikasi geregi)
 */
public class ScreenGuardService extends AccessibilityService {

    private static final String TAG = "PS5ScreenGuard";
    private static boolean sActive = false;
    private BroadcastReceiver mScreenReceiver;

    /** Dışarıdan etkin/pasif toggle için static flag */
    public static boolean isActive() { return sActive; }
    public static void setActive(boolean v) {
        sActive = v;
        Log.i(TAG, "Active = " + v);
    }

    @Override
    public void onServiceConnected() {
        Log.i(TAG, "ScreenGuardService connected");
        sActive = true;

        // SCREEN_ON broadcast dinle
        mScreenReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context ctx, Intent intent) {
                if (Intent.ACTION_SCREEN_ON.equals(intent.getAction()) && sActive) {
                    Log.d(TAG, "SCREEN_ON detected — locking");
                    // Kucuk gecikme: lock_screen intent'i isle
                    performGlobalAction(GLOBAL_ACTION_LOCK_SCREEN);
                }
            }
        };
        IntentFilter f = new IntentFilter(Intent.ACTION_SCREEN_ON);
        registerReceiver(mScreenReceiver, f);
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        // Kullanilmiyor — ekran eventleri SCREEN_ON broadcast ile geliyor
    }

    @Override
    public void onInterrupt() {
        Log.w(TAG, "Service interrupted");
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        sActive = false;
        if (mScreenReceiver != null) {
            try { unregisterReceiver(mScreenReceiver); } catch (Exception e) {}
        }
    }
}

package com.ps5bridge.screenguard;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** Telefon yeniden basladiginda servisi otomatik olarak baslat */
public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context ctx, Intent intent) {
        // Servis AccessibilityService oldugu icin direkt start edilemiyor —
        // kullanici erisilebilirlik'ten etkinlestirdikten sonra Android otomatik baslatir.
        // Bu receiver gelecekte ek baslangic islemi icin rezerve edildi.
    }
}

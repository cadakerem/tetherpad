package com.ps5bridge.screenguard;

import android.app.Activity;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.WindowManager;
import android.graphics.Color;
import android.widget.LinearLayout;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.bluetooth.BluetoothDevice;

/**
 * Kara Delik (Black Hole) Ekrani
 * 
 * Bu ekran ciktiginda:
 * 1) Arka plan simsiyah olur, ekran parlakligi sifira duser.
 * 2) Kilit ekraninin UZERINDE gosterilir.
 * 3) Gelen butun HID / Gamepad / Klavye tuslarini YUTAR.
 * 4) YENI: USB kablosu cekilirse veya kol koparsa kendi kendini otomatik kapatir!
 */
public class MainActivity extends Activity {

    // USB veya Bluetooth koptugunda intihar eden tetikleyici
    private BroadcastReceiver disconnectReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            String action = intent.getAction();
            if (Intent.ACTION_POWER_DISCONNECTED.equals(action) || 
                BluetoothDevice.ACTION_ACL_DISCONNECTED.equals(action)) {
                // Kablo cekildi veya Kol kapandi -> Siyah ekrani yik!
                if (android.os.Build.VERSION.SDK_INT >= 21) {
                    finishAndRemoveTask();
                } else {
                    finish();
                }
                System.exit(0);
            }
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Kapanma durumlarini (Kablo cekilmesi, BT kopmasi) dinlemeye basla
        IntentFilter filter = new IntentFilter();
        filter.addAction(Intent.ACTION_POWER_DISCONNECTED);
        filter.addAction(BluetoothDevice.ACTION_ACL_DISCONNECTED);
        registerReceiver(disconnectReceiver, filter);

        // Kilit ekrani uzerinde goster & Tam ekran yap
        getWindow().addFlags(
            WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED |
            WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD |
            WindowManager.LayoutParams.FLAG_FULLSCREEN |
            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
        );

        // Ekran parlakligini donanimsal olarak minimuma (0) cek
        WindowManager.LayoutParams params = getWindow().getAttributes();
        params.screenBrightness = 0.0f;
        getWindow().setAttributes(params);

        // Ekranin tamamini siyah bir boslukla kapla
        LinearLayout layout = new LinearLayout(this);
        layout.setBackgroundColor(Color.BLACK);
        setContentView(layout);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        try {
            unregisterReceiver(disconnectReceiver);
        } catch (Exception e) {}
    }

    /** Bütün tus basimlarini yutar (PS5 kolunun Android'i kontrol etmesini onler) */
    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        int kc = event.getKeyCode();
        // Ses acma/kisma ve guc tuslarina dokunma, kalani kara delige gitsin
        if (kc == KeyEvent.KEYCODE_VOLUME_UP || 
            kc == KeyEvent.KEYCODE_VOLUME_DOWN || 
            kc == KeyEvent.KEYCODE_POWER) {
            return super.dispatchKeyEvent(event);
        }
        return true; // True = Tusu yuttuk, Android islemeyecek!
    }

    /** Analog cubuk (joystick) hareketlerini yutar */
    @Override
    public boolean dispatchGenericMotionEvent(MotionEvent event) {
        return true; 
    }

    /** Dokunmatigi yutar (yanlislikla cebe girerse vb.) */
    @Override
    public boolean dispatchTouchEvent(MotionEvent event) {
        return true; 
    }
}

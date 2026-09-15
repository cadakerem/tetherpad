# TetherPad

A lightweight, zero-install, and zero-latency bridge that allows you to use your PlayStation 4/5 (DualShock 4 / DualSense) controller on a Windows PC by routing inputs through an Android device via a USB cable.

## 🚀 Why This Project Exists
When connecting a PS4/PS5 controller directly to a PC via Bluetooth, you often experience severe input lag or connection drops unless you buy a dedicated Bluetooth adapter. Connecting the PS4/PS5 controller to your Android phone via Bluetooth, however, is incredibly stable. 

This project bridges that flawless Bluetooth connection from your Android phone directly to your Windows PC over a USB cable using ADB (Android Debug Bridge), effectively creating a lag-free gaming experience.

## ✨ Features
* **Zero Input Lag:** Routes raw kernel-level inputs via USB using ADB, bypassing Android's UI layer entirely.
* **Plug & Play (Invisible App):** Automatically installs an invisible, 11KB background app ("BlackHole") to your phone when you start the program.
* **Battery Saver (BlackHole Mode):** The invisible app creates a pure black overlay on your phone, reduces hardware brightness to 0%, and swallows all controller inputs so your phone doesn't accidentally navigate menus or call emergency numbers while you're playing.
* **Auto-Destruct:** The moment you unplug the USB cable or turn off your controller, the black screen closes instantly and your phone returns to normal.
* **Universal Compatibility:** Tested and working on Android versions as old as Android 4.4.4 (KitKat) up to Android 14+.

## 🗺️ Roadmap
* **Native Xbox Controller Emulation:** Currently, TetherPad bridges all connected gamepads to Windows as a **Virtual PlayStation 4 (DualShock 4)** controller. While this works flawlessly on Steam and most modern games, native Virtual Xbox 360 Controller emulation (dynamic analog conversion and layout mapping) is planned for a future update.
* **Broader OEM Testing:** Gathering more community feedback on highly restricted custom Android ROMs.

## ⚠️ Prerequisites (Crucial Step!)
Since this system relies on ADB, **you MUST enable USB Debugging on your Android phone** for this to work. This is a one-time setup:
1. Go to your phone's **Settings** > **About Phone**.
2. Tap on **Build Number** 7 times until you see "You are now a developer!".
3. Go back to Settings, find **Developer Options**.
4. Enable **USB Debugging**.
5. Connect your phone to your PC via USB. A prompt will appear on your phone asking *"Allow USB debugging?"*. Check **"Always allow from this computer"** and tap **OK**.

## 🛠️ How to Use
1. Connect your PS4/PS5 Controller to your Android phone via Bluetooth.
2. Connect your Android phone to your PC via a USB cable.
3. Run `TetherPad.exe` on your PC.
4. **Important Note on Google Play Protect:** When the program installs the invisible 11KB background app, Google Play Protect might flag it as an "Unsafe App" simply because it was installed via ADB and has no launcher icon. **This is completely normal.** Tap *"Install anyway"* if prompted.
5. Your phone screen will turn completely black (BlackHole mode active). 
6. Start playing your game on Steam/Windows!
7. When you're done, simply **unplug the USB cable** or press **Ctrl+C** on the console. The black screen will disappear instantly.

## 📊 Compatibility & Tested Devices
This software uses core Linux kernel commands (`getevent`) to read inputs, making it highly universal. However, strict OEM policies might affect behavior.

| Device | Android Version | Status |
|--------|-----------------|--------|
| Sony Xperia E4g (E2003) | Android 4.4.4 (KitKat) | ✅ Working flawlessly |
| LG Aristo (MS210) | Android 7.0 (Nougat) | ✅ Working flawlessly |
| Samsung (Knox) Devices | Android 10+ | ⏳ Needs testing (PRs welcome) |
| Xiaomi (MIUI/HyperOS) | Android 10+ | ⏳ Needs testing (PRs welcome) |
| Google Pixel (Stock) | Android 13+ | ⏳ Needs testing (PRs welcome) |

*Note: On devices with strict SELinux policies, reading `/dev/input` via ADB shell might be restricted. Community testing and Pull Requests are highly appreciated!*

## 🧑‍💻 Technical Architecture
Instead of relying on root permissions or losing the kernel race-condition against Android's wake-up triggers, this bridge utilizes a companion APK strategy:
1. The Python script spawns an `adb shell getevent` listener to stream raw hex inputs.
2. It translates these inputs and emulates them on Windows using `vgamepad` (ViGEmBus).
3. To prevent the phone from reacting to the gamepad, it installs `ScreenGuard.apk`—a faceless Android Activity with `FLAG_SHOW_WHEN_LOCKED` and `FLAG_FULLSCREEN`. This activity consumes all `dispatchKeyEvent` and `dispatchGenericMotionEvent` events, effectively sandboxing the controller inputs while maintaining a 0.0f screen brightness.

## License
MIT License

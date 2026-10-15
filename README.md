# TetherPad

A lightweight, zero-install, and zero-latency bridge that allows you to use your PlayStation 4/5 (DualShock 4 / DualSense) or Xbox (Wireless / 360 / One) controller on a Windows PC by routing inputs through an Android device via a USB cable.

## 🚀 Why This Project Exists
When connecting gamepads like a PS4/PS5 or Xbox controller directly to a PC via Bluetooth, you often experience severe input lag or connection drops unless you buy a dedicated Bluetooth adapter. Connecting these controllers to your Android phone via Bluetooth, however, is incredibly stable. 

This project bridges that flawless Bluetooth connection from your Android phone directly to your Windows PC over a USB cable using ADB (Android Debug Bridge), effectively creating a lag-free gaming experience.

## ✨ Features
* **Zero Input Lag:** Routes raw kernel-level inputs via USB using ADB, bypassing Android's UI layer entirely.
* **Silent Background Service:** Runs completely windowless as a System Tray icon. No annoying black command prompts or taskbar clutter.
* **System Tray Integration:** Access real-time connection logs directly via Notepad, toggle "Start with Windows", or safely quit the application with a simple right-click on the 'T' icon.
* **Fully Portable (No ADB Setup):** You don't need to download the Android SDK or mess with environment variables. Custom `platform-tools` are bundled in the release zip and ready to go out of the box.
* **Plug & Play (Invisible App):** Automatically installs an invisible ~21KB background app (`ScreenGuard`) to your phone on first use. On subsequent connections, it detects the app is already installed and launches it instantly — no reinstall delay.
* **Battery Saver (ScreenGuard Mode):** The invisible app creates a pure black overlay on your phone, reduces hardware brightness to 0%, and swallows all controller inputs so your phone doesn't accidentally navigate menus while you're playing.
* **Auto-Destruct:** When you quit TetherPad from the tray icon, the black screen closes and the companion app is automatically uninstalled from your phone. If you simply unplug the USB cable, the black screen closes but the app remains on your phone (ready for instant launch next session).
* **Multi-Profile Auto-Detection:** Automatically identifies whether a connected gamepad is a Sony (PlayStation 4 / DualSense / Clone) or Microsoft (Xbox Wireless / 360 / One) controller via hardware vendor IDs and device descriptors.
* **Concurrent Virtual Touchpad Streaming & Physical Click (v1.4.2):** Parallel background thread streaming real-time single-finger touchpad pointer coordinates (`ABS_MT_POSITION_X/Y`, `ABS_MT_TRACKING_ID`) while precisely disambiguating mechanical clicks (`BTN_LEFT` / `0110`) from capacitive touch (`BTN_TOOL_FINGER` / `0145`) directly to the Windows virtual DualShock 4 touchpad.
* **Asynchronous Sustained Force Feedback Engine (v1.4.2):** Non-blocking background worker thread with motor inertia power scaling (200ms–500ms pulses) and 200ms periodic pulse refresh for sustained, interruption-free in-game rumble.
* **Instant Hardware Vibration Test:** System tray menu action ("Test Vibration (1s)") allowing direct verification of physical rumble motors at any time without launching a game.
* **Dual-Topology Axis Resolution:** Automatically switches between modern Linux evdev axes (`sony_modern`: RX=0003, RY=0004, L2=0002, R2=0005) on Android 12+ `hid-playstation` / `hid-sony` kernels and legacy MTK BT HID axes on older devices (Android 4.4/7.0).
* **Thread-Safe Input Architecture:** Internal mutex synchronization guarding virtual controller reports against concurrent multi-thread updates.
* **Native Virtual Controller Emulation:** 
  - Sony controllers spawn as native **Virtual DualShock 4 (DS4)** gamepads on Windows.
  - Xbox controllers spawn as native **Virtual Xbox 360 (X360)** gamepads with normalized analog axes (-32768..32767) and native XInput D-Pad buttons.
* **Auto-Calibration & Custom Mapping Wizard:** Interactive dark-mode Calibration Wizard in the system tray menu (`mapping.json`), letting you rebind buttons and axes per controller profile on the fly.
* **Automated ViGEmBus Deployment:** Gracefully detects if the required virtual gamepad driver is missing and seamlessly downloads/launches the installer for you.
* **Broad Compatibility:** Tested and verified on legacy devices (KitKat, Nougat) and modern Android 12+ flagships.

## ⚠️ Prerequisites & Warnings
1. **ViGEmBus Driver (Virtual Controller Emulation):** TetherPad creates a virtual DualShock 4 or Xbox 360 controller on Windows via the industry-standard ViGEmBus driver (depending on your physical controller).
   - **Automated Setup:** If ViGEmBus is not installed, TetherPad will detect it upon launch and display a 1-click prompt to download and run the official installer automatically.
   - **Manual Installation:** You can also install it manually via Windows Terminal: `winget install ViGEm.ViGEmBus` or download the installer directly from [ViGEmBus Releases](https://github.com/nefarius/ViGEmBus/releases).
2. **USB Debugging:** Since this system relies on ADB, **you MUST enable USB Debugging on your Android phone** for this to work. 
   - Go to **Settings** > **About Phone**. Tap **Build Number** 7 times.
   - Go to **Developer Options** and enable **USB Debugging**.
   - Connect to PC, check **"Always allow from this computer"** when the prompt appears on your phone.
   - **Crucial Note for Samsung Devices (One UI 6+ / Android 14–16):** Samsung includes a security feature called **Auto Blocker (Otomatik Engelleyici)** that disables USB debugging commands and ADB by default. Before connecting, go to **Settings > Security and privacy > Auto Blocker** and turn it **OFF**. Once Auto Blocker is disabled, you can successfully enable and authorize **USB Debugging**.
3. **Windows SmartScreen:** Since `TetherPad.exe` is a standalone executable compiled with cx_Freeze and isn't digitally signed, Windows Defender or SmartScreen may flag it. If you see a blue *"Windows protected your PC"* warning, simply click **More info** > **Run anyway**.
4. **Google Play Protect:** When the program installs the invisible ~21KB background app, Google Play Protect might flag it as an "Unsafe App" simply because it was installed via ADB and has no launcher icon. **This is completely normal.** Tap *"Install anyway"* if prompted.

## 📊 Compatibility & Tested Devices
This software uses core Linux kernel commands (`getevent`) to read inputs, making it highly universal. However, strict OEM policies might affect behavior.

| Device | Android Version | Status |
|--------|-----------------|--------|
| Samsung Galaxy S25 / S25 FE (SM-S731B) | Android 16 | ✅ Tested & Working flawlessly (Multi-node evdev + Touchpad click + Rumble) |
| Sony Xperia E4g (E2003) | Android 4.4.4 (KitKat) | ✅ Working flawlessly (Single-node legacy BT HID) |
| LG Aristo (MS210) | Android 7.0 (Nougat) | ✅ Working flawlessly (Single-node legacy BT HID) |
| Xiaomi (MIUI/HyperOS) | Android 10+ | ⏳ Needs testing |

> **Testing & Verification Transparency:** The v1.4.2 multi-node architecture was designed from official Linux kernel `hid-sony` / `hid-playstation` device tree specifications and fully verified on physical hardware (Samsung Galaxy S25 running Android 16) alongside automated unit test suites (`tests/test_multinode_dual_sense.py`). Hardware multi-node separation, touchpad click translation, and haptic rumble workers are thoroughly tested and proven.

> **Note on Legacy Devices & Next-Gen Controllers:** If you are repurposing an older Android device as your bridge (especially Android 4.x - 7.x), you may experience pairing issues or connection instability with **next-gen controllers (Xbox Series X/S or PS5 DualSense)**. These modern gamepads are optimized for newer Bluetooth protocols natively supported by Android 10+. Conversely, last-gen Bluetooth controllers (like the PS4 DualShock 4) use classic profiles and pair flawlessly even on devices as old as Android 4.

> **Note on Replica / Clone Controllers:** TetherPad fully supports reading touchpad coordinates and forwarding Force Feedback (Rumble/Vibration). However, Android's Bluetooth HID driver does **not** transmit these specific hardware signals for replica/third-party clone controllers. To utilize the Touchpad and Rumble features wirelessly via TetherPad, a genuine original Sony DualSense or DualShock 4 controller is required.

## 🧑‍💻 Technical Architecture
Instead of relying on root permissions or losing the kernel race-condition against Android's wake-up triggers, this bridge utilizes a companion APK strategy:
1. The Python script spawns an `adb shell getevent` listener to stream raw hex inputs.
2. In modern multi-node topologies (Android 12+), it spawns a concurrent companion worker to capture single-finger touchpad coordinates without stalling or clobbering main stick/button states.
3. It translates these inputs and emulates them on Windows using `vgamepad` (ViGEmBus).
4. To prevent the phone from reacting to the gamepad, it installs `ScreenGuard.apk`—a faceless Android Activity with `FLAG_SHOW_WHEN_LOCKED` and `FLAG_FULLSCREEN`. This activity consumes all `dispatchKeyEvent` and `dispatchGenericMotionEvent` events, effectively sandboxing the controller inputs while maintaining a 0.0f screen brightness.

## 🛠️ How to Use
1. Download TetherPad from the **[Releases](../../releases)** page (run the setup installer or extract the portable ZIP).
2. Connect your PS4/PS5 or Xbox Controller to your Android phone via Bluetooth (or via OTG cable if your controller lacks Bluetooth).
3. Connect your Android phone to your PC via a USB cable.
4. Run `TetherPad.exe` on your PC. 
   *(Note: The app runs in "Windowless" mode. It will instantly hide in your System Tray next to the clock as a 'T' icon.)*
5. Your phone screen will turn completely black (`ScreenGuard` mode active). 
6. Start playing your game on Steam/Windows!
7. **To view logs:** Right-click the 'T' icon in your system tray and select **Show Logs (Notepad)**.
8. **To stop playing:** Simply unplug the USB cable or right-click the tray icon and click **Quit**.

## 🧑‍💻 Developer & Contributions
Developed by Kerem Barbaros Karnabat ([@cadakerem](https://github.com/cadakerem)).

> **Repository & Build Architecture:** 
> - Core Windows bridging logic: `tetherpad.py` compiled via `cx_Freeze` (`setup.py`).
> - Android companion app source: `ScreenGuard/` directory.
> - Automated test suite: `tests/test_multinode_dual_sense.py` covers device node topology detection, backwards compatibility, and thread synchronization.
> - Binary distributions: Compiled binaries and platform tools are strictly excluded from git tracking via `.gitignore` and distributed cleanly via GitHub Releases.

Contributions, issues, and feature requests are welcome! Feel free to check the [Issues page](../../issues).

## 📜 License & Contributions

TetherPad is source-available under the **[PolyForm Noncommercial License 1.0.0](LICENSE)**.
- **Personal & Noncommercial Use:** Free for personal, educational, research, and hobby gaming use.
- **Commercial Inquiries:** Commercial distribution, resale, or repackaging for profit is strictly prohibited. For commercial licensing, OEM integration, or business inquiries, contact: **[cadakerem.me](https://cadakerem.me/)** or via GitHub [@cadakerem](https://github.com/cadakerem).
- **Third-Party Components:** External libraries, drivers, and tools are licensed under their respective open-source licenses, detailed in [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
- **Contributions:** Pull requests are welcome under the Contributor License Agreement specified in [CONTRIBUTING.md](CONTRIBUTING.md).

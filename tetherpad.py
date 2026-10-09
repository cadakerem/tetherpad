import os
import subprocess

if os.name == "nt":
    CREATE_NO_WINDOW = 0x08000000
    _orig_run = subprocess.run
    _orig_popen = subprocess.Popen

    def _run_no_window(*args, **kwargs):
        kwargs['creationflags'] = kwargs.get('creationflags', 0) | CREATE_NO_WINDOW
        return _orig_run(*args, **kwargs)

    def _popen_no_window(*args, **kwargs):
        kwargs['creationflags'] = kwargs.get('creationflags', 0) | CREATE_NO_WINDOW
        return _orig_popen(*args, **kwargs)

    subprocess.run = _run_no_window
    subprocess.Popen = _popen_no_window
else:
    CREATE_NO_WINDOW = 0



import time
import sys
import os
import winreg
import ctypes
import threading
import json
import urllib.request
import tempfile
import webbrowser

# Win32 MessageBox constants
MB_OK = 0x00000000
MB_YESNO = 0x00000004
MB_ICONERROR = 0x00000010
MB_ICONQUESTION = 0x00000020
MB_ICONWARNING = 0x00000030
MB_ICONINFORMATION = 0x00000040
MB_TOPMOST = 0x00040000
IDYES = 6

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_path()
adb_cmd = os.path.join(BASE_DIR, "platform-tools", "adb.exe")
mapping_file = os.path.join(BASE_DIR, "mapping.json")

DEFAULT_MAPPING = {
    "buttons": {
        "CROSS": "0131",
        "CIRCLE": "0132",
        "SQUARE": "0130",
        "TRIANGLE": "0133",
        "L1": "0134",
        "R1": "0135",
        "L2_BTN": "0136",
        "R2_BTN": "0137",
        "SHARE": "0138",
        "OPTIONS": "0139",
        "L3": "013a",
        "R3": "013b",
        "PS": "013c",
        "TOUCHPAD": "013d"
    },
    "axes": {
        "LX": {"type": "0003", "code": "0000"},
        "LY": {"type": "0003", "code": "0001"},
        "RX": {"type": "0003", "code": "0002"},
        "RY": {"type": "0003", "code": "0005"},
        "L2": {"type": "0003", "code": "0003"},
        "R2": {"type": "0003", "code": "0004"},
        "DPAD_X": {"type": "0003", "code": "0010"},
        "DPAD_Y": {"type": "0003", "code": "0011"}
    }
}

def ensure_mapping_config():
    """Checks if mapping.json exists; if not, automatically generates the default mapping."""
    if not os.path.exists(mapping_file):
        try:
            with open(mapping_file, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_MAPPING, f, indent=4)
            print("[+] Generated default mapping configuration: mapping.json")
        except Exception as e:
            print(f"[!] Warning: Could not write default mapping.json: {e}")

_wizard_running = False

def open_calibration_wizard(icon=None, item=None):
    """Launches the controller button calibration wizard GUI in a background thread."""
    global _wizard_running
    if _wizard_running:
        return
    threading.Thread(target=_run_calibration_wizard_gui, daemon=True).start()

def _run_calibration_wizard_gui():
    global _wizard_running
    _wizard_running = True
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox

        root = tk.Tk()
        root.title("TetherPad - Controller Calibration")
        root.geometry("480x430")
        root.resizable(False, False)
        root.attributes("-topmost", True)

        bg_color = "#1e1e2e"
        fg_color = "#cdd6f4"
        accent_color = "#89b4fa"
        btn_bg = "#313244"

        root.configure(bg=bg_color)

        buttons_to_map = [
            ("CROSS", "Cross / A (X)"),
            ("CIRCLE", "Circle / B (O)"),
            ("SQUARE", "Square / X (□)"),
            ("TRIANGLE", "Triangle / Y (△)"),
            ("L1", "L1 (Left Bumper)"),
            ("R1", "R1 (Right Bumper)"),
            ("L2_BTN", "L2 (Left Trigger Button)"),
            ("R2_BTN", "R2 (Right Trigger Button)"),
            ("SHARE", "Share / Select / Create"),
            ("OPTIONS", "Options / Start"),
            ("L3", "L3 (Left Stick Click)"),
            ("R3", "R3 (Right Stick Click)"),
            ("PS", "PS / Home Button"),
            ("TOUCHPAD", "Touchpad Click"),
        ]

        current_idx = [0]
        recorded = dict(DEFAULT_MAPPING["buttons"])
        if os.path.exists(mapping_file):
            try:
                with open(mapping_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    recorded.update(saved.get("buttons", {}))
            except Exception:
                pass

        stop_listener = threading.Event()

        title_lbl = tk.Label(root, text="Controller Calibration Wizard", font=("Segoe UI", 14, "bold"), bg=bg_color, fg=accent_color)
        title_lbl.pack(pady=(15, 5))

        desc_lbl = tk.Label(root, text="Press each button on your controller when prompted.", font=("Segoe UI", 10), bg=bg_color, fg="#a6adc8")
        desc_lbl.pack(pady=(0, 15))

        card_frame = tk.Frame(root, bg="#252538", bd=2, relief="groove")
        card_frame.pack(fill="x", padx=30, pady=10)

        step_lbl = tk.Label(card_frame, text="Step 1 of 14", font=("Segoe UI", 10, "italic"), bg="#252538", fg="#9399b2")
        step_lbl.pack(pady=(10, 2))

        target_btn_lbl = tk.Label(card_frame, text="", font=("Segoe UI", 16, "bold"), bg="#252538", fg="#f38ba8")
        target_btn_lbl.pack(pady=(2, 10))

        status_lbl = tk.Label(root, text="Listening for input from phone...", font=("Segoe UI", 10), bg=bg_color, fg="#a6e3a1")
        status_lbl.pack(pady=5)

        progress = ttk.Progressbar(root, orient="horizontal", length=420, mode="determinate")
        progress.pack(pady=10)

        def update_ui():
            idx = current_idx[0]
            if idx < len(buttons_to_map):
                key, label = buttons_to_map[idx]
                step_lbl.config(text=f"Step {idx + 1} of {len(buttons_to_map)}")
                target_btn_lbl.config(text=f"Press: {label}")
                progress["value"] = (idx / len(buttons_to_map)) * 100
            else:
                finish_calibration()

        def save_and_close():
            nonlocal stop_listener
            stop_listener.set()
            try:
                current_cfg = dict(DEFAULT_MAPPING)
                if os.path.exists(mapping_file):
                    try:
                        with open(mapping_file, "r", encoding="utf-8") as f:
                            current_cfg = json.load(f)
                    except Exception:
                        pass
                current_cfg["buttons"] = recorded
                with open(mapping_file, "w", encoding="utf-8") as f:
                    json.dump(current_cfg, f, indent=4)
                load_mapping()
                messagebox.showinfo("TetherPad", "Controller mapping saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save mapping: {e}")
            finally:
                root.destroy()

        def finish_calibration():
            step_lbl.config(text="Calibration Complete!")
            target_btn_lbl.config(text="All buttons mapped!", fg="#a6e3a1")
            progress["value"] = 100
            status_lbl.config(text="Saving configuration...", fg="#a6e3a1")
            root.after(600, save_and_close)

        def on_skip():
            current_idx[0] += 1
            update_ui()

        def on_reset_defaults():
            nonlocal recorded
            recorded = dict(DEFAULT_MAPPING["buttons"])
            try:
                with open(mapping_file, "w", encoding="utf-8") as f:
                    json.dump(DEFAULT_MAPPING, f, indent=4)
                load_mapping()
                messagebox.showinfo("TetherPad", "Reset to default PS4/PS5 layout complete.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to reset mapping: {e}")
            finally:
                stop_listener.set()
                root.destroy()

        btn_frame = tk.Frame(root, bg=bg_color)
        btn_frame.pack(side="bottom", fill="x", pady=15, padx=30)

        skip_btn = tk.Button(btn_frame, text="Skip Button", command=on_skip, bg=btn_bg, fg=fg_color, relief="flat", padx=10, pady=5)
        skip_btn.pack(side="left")

        reset_btn = tk.Button(btn_frame, text="Reset to Defaults", command=on_reset_defaults, bg="#45475a", fg=fg_color, relief="flat", padx=10, pady=5)
        reset_btn.pack(side="left", padx=10)

        cancel_btn = tk.Button(btn_frame, text="Cancel", command=lambda: (stop_listener.set(), root.destroy()), bg=btn_bg, fg=fg_color, relief="flat", padx=10, pady=5)
        cancel_btn.pack(side="right")

        def listen_events():
            target_node = device_node or find_device_node()
            if not target_node:
                root.after(0, lambda: status_lbl.config(text="Waiting for phone & controller connection...", fg="#f9e2af"))
                while not stop_listener.is_set() and not target_node:
                    time.sleep(1)
                    target_node = device_node or find_device_node()
                if stop_listener.is_set():
                    return
                root.after(0, lambda: status_lbl.config(text=f"Listening on {target_node}", fg="#a6e3a1"))

            try:
                proc = _orig_popen(
                    [adb_cmd, "shell", "-tt", f"getevent {target_node}"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
                )
                for line in iter(proc.stdout.readline, ''):
                    if stop_listener.is_set():
                        break
                    parts = line.strip().split()
                    if len(parts) == 3 and parts[0] == '0001':
                        code = parts[1]
                        try:
                            val = int(parts[2], 16)
                        except ValueError:
                            continue
                        if val == 1:
                            idx = current_idx[0]
                            if idx < len(buttons_to_map):
                                key, _ = buttons_to_map[idx]
                                recorded[key] = code
                                current_idx[0] += 1
                                root.after(0, update_ui)
                try:
                    proc.terminate()
                except Exception:
                    pass
            except Exception as e:
                print(f"[Wizard Error] {e}")

        listener_thread = threading.Thread(target=listen_events, daemon=True)
        listener_thread.start()

        update_ui()
        root.mainloop()
        stop_listener.set()
    finally:
        _wizard_running = False

def is_vigembus_installed():
    """Checks if ViGEmBus kernel driver or service is installed on the system."""
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\ViGEmBus")
        winreg.CloseKey(key)
        return True
    except OSError:
        pass

    sys_root = os.environ.get("SystemRoot", r"C:\Windows")
    sys_driver = os.path.join(sys_root, "System32", "drivers", "ViGEmBus.sys")
    return os.path.exists(sys_driver)

def ensure_vigembus():
    """
    Ensures the ViGEmBus driver is installed before importing or using vgamepad.
    If missing, prompts the user with a native dialog to automatically download and run the installer.
    """
    if is_vigembus_installed():
        return True

    title = "TetherPad - ViGEmBus Driver Required"
    msg = (
        "TetherPad requires the ViGEmBus driver to emulate a virtual gamepad on Windows.\n\n"
        "The ViGEmBus driver was not found on your system.\n\n"
        "Would you like TetherPad to automatically download and launch the installer now?\n\n"
        "• Click 'Yes' to download and install ViGEmBus.\n"
        "• Click 'No' to open the manual download page in your browser."
    )

    resp = ctypes.windll.user32.MessageBoxW(0, msg, title, MB_YESNO | MB_ICONQUESTION | MB_TOPMOST)
    if resp == IDYES:
        installer_name = "ViGEmBus_Setup.exe"
        installer_path = os.path.join(BASE_DIR, installer_name)

        if not os.path.exists(installer_path):
            installer_url = "https://github.com/nefarius/ViGEmBus/releases/download/v1.22.0/ViGEmBus_1.22.0_x64_x86_arm64.exe"
            installer_path = os.path.join(tempfile.gettempdir(), installer_name)
            try:
                urllib.request.urlretrieve(installer_url, installer_path)
            except Exception as e:
                ctypes.windll.user32.MessageBoxW(
                    0,
                    f"Failed to download ViGEmBus installer:\n{e}\n\nPlease install it manually from GitHub.",
                    "TetherPad - Download Error",
                    MB_ICONERROR | MB_TOPMOST
                )
                webbrowser.open("https://github.com/nefarius/ViGEmBus/releases/latest")
                sys.exit(1)

        # Launch the installer with normal visible window and elevation
        try:
            ret = ctypes.windll.shell32.ShellExecuteW(None, "open", installer_path, None, None, 1)
            if ret <= 32:
                # SE_ERR_ACCESSDENIED = 5 (User cancelled UAC prompt)
                if ret == 5:
                    ctypes.windll.user32.MessageBoxW(
                        0,
                        "Installation was cancelled (Administrator permission denied).\n"
                        "TetherPad cannot start without ViGEmBus.",
                        "TetherPad - Setup Cancelled",
                        MB_ICONWARNING | MB_TOPMOST
                    )
                else:
                    ctypes.windll.user32.MessageBoxW(
                        0,
                        f"Failed to start installer (Error code: {ret}).\nPlease run the installer manually.",
                        "TetherPad - Launch Error",
                        MB_ICONERROR | MB_TOPMOST
                    )
                sys.exit(1)
        except Exception as e:
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Failed to start installer:\n{e}",
                "TetherPad - Launch Error",
                MB_ICONERROR | MB_TOPMOST
            )
            sys.exit(1)

        ctypes.windll.user32.MessageBoxW(
            0,
            "The ViGEmBus installer has been launched.\n\n"
            "Please complete the installation wizard on your screen, then start TetherPad again.",
            "TetherPad - Driver Setup",
            MB_ICONINFORMATION | MB_TOPMOST
        )
        sys.exit(0)
    else:
        webbrowser.open("https://github.com/nefarius/ViGEmBus/releases/latest")
        sys.exit(0)

# Check and ensure ViGEmBus driver is present before importing vgamepad
ensure_vigembus()

try:
    import vgamepad as vg
except Exception as e:
    ctypes.windll.user32.MessageBoxW(
        0,
        f"Failed to initialize virtual gamepad:\n{e}",
        "TetherPad - Initialization Error",
        MB_ICONERROR | MB_TOPMOST
    )
    sys.exit(1)

import pystray
from PIL import Image, ImageDraw

ensure_mapping_config()

def load_mapping():
    """Loads controller mapping configuration from mapping.json or falls back to DEFAULT_MAPPING."""
    global BTN_MAP, SPECIAL_BTN_MAP, AXIS_LX, AXIS_LY, AXIS_RX, AXIS_RY, AXIS_L2, AXIS_R2, DPAD_X, DPAD_Y
    ensure_mapping_config()
    config = DEFAULT_MAPPING
    if os.path.exists(mapping_file):
        try:
            with open(mapping_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            print(f"[!] Error loading mapping.json: {e}")
            config = DEFAULT_MAPPING

    b = config.get("buttons", {})
    a = config.get("axes", {})

    BTN_MAP = {
        b.get("CROSS"): vg.DS4_BUTTONS.DS4_BUTTON_CROSS,
        b.get("CIRCLE"): vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE,
        b.get("SQUARE"): vg.DS4_BUTTONS.DS4_BUTTON_SQUARE,
        b.get("TRIANGLE"): vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE,
        b.get("L1"): vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT,
        b.get("R1"): vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT,
        b.get("L2_BTN"): vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_LEFT,
        b.get("R2_BTN"): vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_RIGHT,
        b.get("SHARE"): vg.DS4_BUTTONS.DS4_BUTTON_SHARE,
        b.get("OPTIONS"): vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS,
        b.get("L3"): vg.DS4_BUTTONS.DS4_BUTTON_THUMB_LEFT,
        b.get("R3"): vg.DS4_BUTTONS.DS4_BUTTON_THUMB_RIGHT,
    }
    BTN_MAP = {k: v for k, v in BTN_MAP.items() if k}

    SPECIAL_BTN_MAP = {
        b.get("PS"): vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_PS,
        b.get("TOUCHPAD"): vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_TOUCHPAD,
    }
    SPECIAL_BTN_MAP = {k: v for k, v in SPECIAL_BTN_MAP.items() if k}

    AXIS_LX = a.get("LX", {}).get("code")
    AXIS_LY = a.get("LY", {}).get("code")
    AXIS_RX = a.get("RX", {}).get("code")
    AXIS_RY = a.get("RY", {}).get("code")
    AXIS_L2 = a.get("L2", {}).get("code")
    AXIS_R2 = a.get("R2", {}).get("code")
    DPAD_X = a.get("DPAD_X", {}).get("code")
    DPAD_Y = a.get("DPAD_Y", {}).get("code")

def find_device_node():
    try:
        proc = subprocess.run([adb_cmd, "shell", "getevent -i"], capture_output=True, text=True)
        current_device = None
        for line in proc.stdout.split('\n'):
            if line.startswith("add device"):
                current_device = line.split(":")[-1].strip()
            if any(x in line.upper() for x in ["WIRELESS CONTROLLER", "SONY", "DUALSENSE", "MTK BT HID", "GAMEPAD", "JOYSTICK"]):
                return current_device
    except Exception:
        pass
    return None

# --- Global state ---
_cleanup_done = False
_cleanup_lock = threading.Lock()
stop_event   = threading.Event()
gamepad      = None
input_process = None
usb_t = None
bt_t = None
device_node = None
_device_info = {}  # {'android_ver': int, 'manufacturer': str}

# ============================================================
# CIHAZ BILGISI TESPITI
# ============================================================
def detect_device_info():
    """Bagli telefona ait Android surumu ve uretici bilgisini okur."""
    global _device_info
    try:
        ver = subprocess.run(
            [adb_cmd, "shell", "getprop ro.build.version.release"],
            capture_output=True, text=True
        ).stdout.strip()
        mfr = subprocess.run(
            [adb_cmd, "shell", "getprop ro.product.manufacturer"],
            capture_output=True, text=True
        ).stdout.strip().upper()
        
        major = int(ver.split(".")[0]) if ver else 0
        _device_info = {"android_ver": major, "manufacturer": mfr, "ver_str": ver}
        print(f"[Device] Android {ver} | Mfr: {mfr.capitalize()}")
    except Exception:
        _device_info = {"android_ver": 0, "manufacturer": "", "ver_str": "?"}

def _is_stubborn_device():
    """HID input eventlerini kullanici aktivitesi sayip ekrani uyandiran
    cihazlar icin True doner. (Android 7 ve alti LG / dusuk RAM cihazlar)"""
    return _device_info.get("android_ver", 99) <= 7

# ============================================================
# SCREEN GUARD (KARA DELIK) OTOMATIK KURULUM
# ============================================================
def setup_screenguard():
    """
    Kullaniciya hissettirmeden ScreenGuard APK'sini kurar ve Kara Delik ekranini baslatir.
    USB band genisligini yormamak icin agressif power loop'lari yerine bu modern yontem kullanilir.
    """
    apk_path = os.path.join(get_base_path(), "ScreenGuard.apk")
    if os.path.exists(apk_path):
        print("[+] ScreenGuard (BlackHole) is being prepared...")
        # Önceki bozuk/disabled statüleri temizlemek için eski sürümü tamamen sil
        subprocess.run(
            [adb_cmd, "uninstall", "com.ps5bridge.screenguard"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        # Temiz kurulum
        subprocess.run(
            [adb_cmd, "install", "-r", apk_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        # Siyah ekrani (MainActivity) kilit ekraninin uzerinde baslat
        subprocess.run(
            [adb_cmd, "shell", "am", "start", "-n", "com.ps5bridge.screenguard/.MainActivity"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        print("[+] Screen secured (Press Home on the phone to exit).")
    else:
        print("[-] ScreenGuard.apk not found. Screen protection skipped.")

def teardown_screenguard():
    """Program kapandiginda siyah ekrani kapatir ve APK'yi telefondan tamamen siler."""
    print("  [4] ScreenGuard is being uninstalled from the device...")
    # 1. Önce uygulamayı durdur (siyah ekranı kapat)
    subprocess.run(
        [adb_cmd, "shell", "am", "force-stop", "com.ps5bridge.screenguard"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    # 2. Uygulamayı telefondan kökten sil (uninstall)
    subprocess.run(
        [adb_cmd, "uninstall", "com.ps5bridge.screenguard"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

# ============================================================
# USB WATCHDOG
# ============================================================
def usb_watchdog():
    global input_process
    time.sleep(2.0)
    subprocess.run([adb_cmd, "wait-for-disconnect"])
    if not stop_event.is_set():
        print("\n[!] USB/ADB connection lost!")
        if input_process and input_process.poll() is None:
            try:
                input_process.terminate()
            except Exception:
                pass
        cleanup(reason="USB baglantisi kesildi")

# ============================================================
# BT WATCHDOG
# ============================================================
def bt_watchdog():
    global input_process, device_node
    time.sleep(3.0)
    cmd = f"while [ -e {device_node} ]; do sleep 1.5; done; echo GONE"
    try:
        proc = subprocess.run([adb_cmd, "shell", cmd], capture_output=True, text=True)
        if not stop_event.is_set() and "GONE" in proc.stdout:
            print("\n[!] Bluetooth connection lost! Controller disconnected.")
            if input_process and input_process.poll() is None:
                try:
                    input_process.terminate()
                except Exception:
                    pass
            cleanup(reason="Bluetooth baglantisi koptu")
    except Exception:
        pass

# ============================================================
# TEMIZLIK
# ============================================================
def cleanup(reason=""):
    global _cleanup_done, gamepad, input_process

    with _cleanup_lock:
        if _cleanup_done:
            return
        _cleanup_done = True

    print(f"\n[Shutting down] {reason}")

    stop_event.set()

    if input_process and input_process.poll() is None:
        try:
            input_process.terminate()
        except Exception:
            pass

    print("  [3] Removing virtual gamepad...")
    try:
        if gamepad is not None:
            del gamepad
            gamepad = None
            print("      Virtual gamepad removed from Windows!")
    except Exception as e:
        print(f"      [!] Error removing virtual gamepad: {e}")
        
    teardown_screenguard()

    print("\nClean shutdown complete.")

# ============================================================
# ANA AKIS
# ============================================================
def run():
    global input_process, gamepad, _cleanup_done, sticks, stop_event, BTN_MAP, SPECIAL_BTN_MAP, AXIS_LX, AXIS_LY, AXIS_RX, AXIS_RY, AXIS_L2, AXIS_R2, DPAD_X, DPAD_Y, usb_t, bt_t, device_node
    
    while True:
        try:
            _cleanup_done = False
            stop_event.clear()
            
            print("=" * 55)
            print("  TetherPad - Starting up")
            print("=" * 55)
            
            print(f"\n[Waiting] Connect your PS5 controller to your phone via Bluetooth...")
            print(f"           (Ensure the USB cable is connected)\n")
            
            # USB'yi bekle
            subprocess.run([adb_cmd, "wait-for-device"], creationflags=CREATE_NO_WINDOW)
            
            # BT kolu bekle ve otomatik bul
            device_node = None
            while True:
                device_node = find_device_node()
                if device_node:
                    break
                
                # USB kopup kopmadigini kontrol et
                proc = subprocess.run([adb_cmd, "shell", "echo PING"], capture_output=True, text=True)
                if "PING" not in proc.stdout:
                    break # USB koptu
                
                time.sleep(2)
                
            if not device_node:
                print("\n[!] USB disconnected. Waiting for connection...")
                time.sleep(2)
                continue
            
            print(f"\n[OK] Controller found: {device_node}")
            
            # ADIM 1.5: Cihaz bilgisi tespiti (ekran stratejisi icin)
            detect_device_info()
            
            # ADIM 2: Sanal gamepad olustur
            print("\n[OK] Creating virtual PlayStation controller...")
            gamepad = vg.VDS4Gamepad()
            print("[OK] Virtual controller active on Windows/Steam!")
            
            # ADIM 3: Ekran kapatici THREAD'i baslat
            print("[OK] Starting screen protector...")
            setup_screenguard()
            print("[OK] Screen protector active!")
            
            # ADIM 4: getevent dinleyicisi
            print(f"\\n[OK] {device_node} dinleniyor...\\n")
            input_process = subprocess.Popen(
                [adb_cmd, "shell", "-tt", f"getevent {device_node}"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
            )
            
            print("Listening for PS5 Controller input... (Ctrl+C to stop completely)")
            print("=> NOTE: Undefined inputs will be ignored.\n")
            
            load_mapping()
            
            def map_axis(val):
                return max(0, min(255, val))
            
            sticks = {'lx': 128, 'ly': 128, 'rx': 128, 'ry': 128}
            
            if usb_t is None or not usb_t.is_alive():
                usb_t = threading.Thread(target=usb_watchdog, daemon=True)
                usb_t.start()
            
            if bt_t is None or not bt_t.is_alive():
                bt_t  = threading.Thread(target=bt_watchdog, daemon=True)
                bt_t.start()
            
            for line in iter(input_process.stdout.readline, ''):
                if stop_event.is_set():
                    break
                parts = line.strip().split()
                if len(parts) != 3:
                    continue
                event_type = parts[0]
                event_code = parts[1]
                try:
                    event_value = int(parts[2], 16)
                except ValueError:
                    continue
        
                if event_type == '0001':
                    if event_code in BTN_MAP:
                        btn = BTN_MAP[event_code]
                        if event_value == 1:
                            gamepad.press_button(button=btn)
                        elif event_value == 0:
                            gamepad.release_button(button=btn)
                    elif event_code in SPECIAL_BTN_MAP:
                        btn = SPECIAL_BTN_MAP[event_code]
                        if event_value == 1:
                            gamepad.press_special_button(special_button=btn)
                        elif event_value == 0:
                            gamepad.release_special_button(special_button=btn)
        
                elif event_type == '0003':
                    if event_code == AXIS_LX:
                        sticks['lx'] = event_value
                        gamepad.left_joystick(x_value=map_axis(sticks['lx']), y_value=map_axis(sticks['ly']))
                    elif event_code == AXIS_LY:
                        sticks['ly'] = event_value
                        gamepad.left_joystick(x_value=map_axis(sticks['lx']), y_value=map_axis(sticks['ly']))
                    elif event_code == AXIS_RX:
                        sticks['rx'] = event_value
                        gamepad.right_joystick(x_value=map_axis(sticks['rx']), y_value=map_axis(sticks['ry']))
                    elif event_code == AXIS_RY:
                        sticks['ry'] = event_value
                        gamepad.right_joystick(x_value=map_axis(sticks['rx']), y_value=map_axis(sticks['ry']))
                    elif event_code == AXIS_L2:
                        gamepad.left_trigger(value=map_axis(event_value))
                    elif event_code == AXIS_R2:
                        gamepad.right_trigger(value=map_axis(event_value))
                    elif event_code == DPAD_X:
                        if event_value == 0xffffffff or event_value == 0xffff or (event_value & 0x80000000):
                            gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST)
                        elif event_value == 1:
                            gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST)
                        else:
                            gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE)
                    elif event_code == DPAD_Y:
                        if event_value == 0xffffffff or event_value == 0xffff or (event_value & 0x80000000):
                            gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH)
                        elif event_value == 1:
                            gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH)
                        else:
                            gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE)
        
                elif event_type == '0000' and event_code == '0000':
                    gamepad.update()
            
            if not stop_event.is_set():
                print("\n[!] Bluetooth disconnected or controller turned off!")
                
        except KeyboardInterrupt:
            print("\nUser interrupted via Ctrl+C.")
            cleanup(reason="User Request (Ctrl+C)")
            sys.exit(0)
            
        except (OSError, BrokenPipeError, ValueError):
            pass
            
        finally:
            cleanup(reason="Connection lost")
            
        print("\n[*] Switching back to search mode in 3 seconds...")
        time.sleep(3)


# ============================================================
# SYSTEM TRAY & AUTO-START
# ============================================================
APP_NAME = "TetherPad"

def get_exe_path():
    if getattr(sys, 'frozen', False):
        return sys.executable
    else:
        return os.path.abspath(__file__)

def is_startup_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except WindowsError:
        return False

def toggle_startup(icon, item):
    enabled = is_startup_enabled()
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
        if enabled:
            winreg.DeleteValue(key, APP_NAME)
        else:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{get_exe_path()}" --hidden')
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Startup toggle error: {e}")

log_path = os.path.join(os.path.dirname(get_exe_path()), "tetherpad.log")
sys.stdout = open(log_path, "w", encoding="utf-8", buffering=1)
sys.stderr = sys.stdout

def open_logs(icon, item):
    try:
        os.startfile(log_path)
    except:
        pass

def quit_app(icon, item):
    icon.stop()
    stop_event.set()
    cleanup(reason="User Request (Tray Quit)")
    os._exit(0)

def create_image():
    # Mavi zemin uzerine beyaz T harfi (dikdortgenlerle cizildi - font sorunu yasamamak icin)
    image = Image.new('RGB', (64, 64), color=(0, 120, 215))
    draw = ImageDraw.Draw(image)
    # T'nin ust yatay cizgisi
    draw.rectangle((16, 16, 48, 24), fill=(255, 255, 255))
    # T'nin alt dikey cizgisi
    draw.rectangle((28, 24, 36, 52), fill=(255, 255, 255))
    return image

if __name__ == '__main__':
    # Run the main loop in a background thread
    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    
    # Create the tray menu
    menu = pystray.Menu(
        pystray.MenuItem("Show Logs (Notepad)", open_logs),
        pystray.MenuItem("Calibrate Controller", open_calibration_wizard),
        pystray.MenuItem("Start with Windows", toggle_startup, checked=lambda item: is_startup_enabled()),
        pystray.MenuItem("Quit", quit_app)
    )
    
    icon = pystray.Icon("TetherPad", create_image(), "TetherPad Bridge", menu)
    icon.run()

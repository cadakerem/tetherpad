import subprocess
import vgamepad as vg
import time
import sys
import os
import winreg
import ctypes
import pystray
from PIL import Image, ImageDraw
import sys
import threading
import json
import os

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_path()
adb_cmd = os.path.join(BASE_DIR, "platform-tools", "adb.exe")
mapping_file = os.path.join(BASE_DIR, "mapping.json")

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
            subprocess.run([adb_cmd, "wait-for-device"])
            
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
            
            if not os.path.exists(mapping_file):
                print("\n[!] ERROR: mapping.json not found!")
                print("[!] Please run 'TetherPad_Calibration.exe' first.\n")
                sys.exit(1)
            
            with open(mapping_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            
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

kernel32 = ctypes.WinDLL('kernel32')
user32 = ctypes.WinDLL('user32')
hWnd = kernel32.GetConsoleWindow()
console_visible = True

# Disable the X (Close) button on the console window so users don't accidentally kill the background process
if hWnd:
    hMenu = user32.GetSystemMenu(hWnd, False)
    if hMenu:
        user32.DeleteMenu(hMenu, 0xF060, 0) # SC_CLOSE

def hide_console():
    if hWnd: user32.ShowWindow(hWnd, 0)

def show_console():
    if hWnd: user32.ShowWindow(hWnd, 5)

def toggle_console(icon, item):
    global console_visible
    if console_visible:
        hide_console()
    else:
        show_console()
    console_visible = not console_visible

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
    if "--hidden" in sys.argv:
        hide_console()
        console_visible = False
    
    # Run the main loop in a background thread
    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    
    # Create the tray menu
    menu = pystray.Menu(
        pystray.MenuItem("Show Console Log", toggle_console, checked=lambda item: console_visible),
        pystray.MenuItem("Start with Windows", toggle_startup, checked=lambda item: is_startup_enabled()),
        pystray.MenuItem("Quit", quit_app)
    )
    
    icon = pystray.Icon("TetherPad", create_image(), "TetherPad Bridge", menu)
    icon.run()

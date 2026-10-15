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



import atexit
import ctypes
import json
import os
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser
try:
    import winreg
except ImportError:
    winreg = None

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
    if getattr(sys, 'frozen', False) or hasattr(sys, 'nuitka') or "__compiled__" in globals():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_path()

def get_data_dir():
    appdata = os.getenv('LOCALAPPDATA')
    if appdata:
        data_dir = os.path.join(appdata, "TetherPad")
    else:
        data_dir = BASE_DIR
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

DATA_DIR = get_data_dir()
adb_cmd = os.path.join(BASE_DIR, "platform-tools", "adb.exe")
mapping_file = os.path.join(DATA_DIR, "mapping.json")

DEFAULT_MAPPINGS = {
    "sony": {
        "name": "Sony DualShock 4 / DualSense",
        "emulation": "ds4",
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
    },
    "sony_modern": {
        "name": "Sony DualShock 4 / DualSense (Modern evdev)",
        "emulation": "ds4",
        "buttons": {
            "CROSS": "0130",
            "CIRCLE": "0131",
            "SQUARE": "0134",
            "TRIANGLE": "0133",
            "L1": "0136",
            "R1": "0137",
            "L2_BTN": "0138",
            "R2_BTN": "0139",
            "SHARE": "013a",
            "OPTIONS": "013b",
            "L3": "013d",
            "R3": "013e",
            "PS": "013c",
            "TOUCHPAD": "0110"
        },
        "axes": {
            "LX": {"type": "0003", "code": "0000"},
            "LY": {"type": "0003", "code": "0001"},
            "RX": {"type": "0003", "code": "0003"},
            "RY": {"type": "0003", "code": "0004"},
            "L2": {"type": "0003", "code": "0002"},
            "R2": {"type": "0003", "code": "0005"},
            "DPAD_X": {"type": "0003", "code": "0010"},
            "DPAD_Y": {"type": "0003", "code": "0011"}
        }
    },
    "xbox": {
        "name": "Xbox Wireless Controller",
        "emulation": "xbox360",
        "buttons": {
            "A": "0130",
            "B": "0131",
            "X": "0133",
            "Y": "0134",
            "LB": "0136",
            "RB": "0137",
            "BACK": "013a",
            "START": "013b",
            "L3": "013d",
            "R3": "013e",
            "GUIDE": "013c"
        },
        "axes": {
            "LX": {"type": "0003", "code": "0000"},
            "LY": {"type": "0003", "code": "0001"},
            "RX": {"type": "0003", "code": "0003"},
            "RY": {"type": "0003", "code": "0004"},
            "LT": {"type": "0003", "code": "0002"},
            "RT": {"type": "0003", "code": "0005"},
            "DPAD_X": {"type": "0003", "code": "0010"},
            "DPAD_Y": {"type": "0003", "code": "0011"}
        }
    }
}

DEFAULT_MAPPING = DEFAULT_MAPPINGS["sony"]

def ensure_mapping_config():
    """Checks if mapping.json exists; if not or if profiles are outdated, updates mapping."""
    if not os.path.exists(mapping_file):
        try:
            with open(mapping_file, "w", encoding="utf-8") as f:
                json.dump({"profiles": DEFAULT_MAPPINGS}, f, indent=4)
            print("[+] Generated multi-profile mapping configuration: mapping.json")
        except Exception as e:
            print(f"[!] Warning: Could not write default mapping.json: {e}")
    else:
        try:
            with open(mapping_file, "r", encoding="utf-8") as f:
                raw_cfg = json.load(f)
            updated = False
            if "profiles" not in raw_cfg:
                raw_cfg = {"profiles": dict(DEFAULT_MAPPINGS)}
                updated = True
            else:
                for k, v in DEFAULT_MAPPINGS.items():
                    if k not in raw_cfg["profiles"]:
                        raw_cfg["profiles"][k] = v
                        updated = True
                    elif k == "sony_modern" and raw_cfg["profiles"][k].get("buttons", {}).get("CROSS") != "0130":
                        raw_cfg["profiles"][k] = v
                        updated = True
            if updated:
                with open(mapping_file, "w", encoding="utf-8") as f:
                    json.dump(raw_cfg, f, indent=4)
                print("[+] Synchronized mapping.json with modern profiles.")
        except Exception as e:
            print(f"[!] Warning: Could not update mapping.json: {e}")

_wizard_running = False
current_profile_type = "sony"

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
        root.geometry("490x440")
        root.resizable(False, False)
        root.attributes("-topmost", True)

        bg_color = "#1e1e2e"
        fg_color = "#cdd6f4"
        accent_color = "#89b4fa"
        btn_bg = "#313244"
        root.configure(bg=bg_color)

        active_profile = current_profile_type or "sony"
        profile_title = "Xbox" if active_profile == "xbox" else "PlayStation"
        root.title(f"TetherPad - Controller Calibration ({profile_title})")

        if active_profile == "xbox":
            buttons_to_map = [
                ("A", "A Button"),
                ("B", "B Button"),
                ("X", "X Button"),
                ("Y", "Y Button"),
                ("LB", "LB (Left Bumper)"),
                ("RB", "RB (Right Bumper)"),
                ("BACK", "Back / View Button"),
                ("START", "Start / Menu Button"),
                ("L3", "L3 (Left Stick Click)"),
                ("R3", "R3 (Right Stick Click)"),
                ("GUIDE", "Xbox Guide Button"),
            ]
        elif active_profile == "sony_modern":
            buttons_to_map = [
                ("CROSS", "Cross / A (X)"),
                ("CIRCLE", "Circle / B (O)"),
                ("SQUARE", "Square / X (□)"),
                ("TRIANGLE", "Triangle / Y (△)"),
                ("L1", "L1 (Left Bumper)"),
                ("R1", "R1 (Right Bumper)"),
                ("L2_BTN", "L2 (Left Trigger Button)"),
                ("R2_BTN", "R2 (Right Trigger Button)"),
                ("SHARE", "Share / Create"),
                ("OPTIONS", "Options / Start"),
                ("L3", "L3 (Left Stick Click)"),
                ("R3", "R3 (Right Stick Click)"),
                ("PS", "PS Button"),
            ]
        else:
            buttons_to_map = [
                ("CROSS", "Cross / A (X)"),
                ("CIRCLE", "Circle / B (O)"),
                ("SQUARE", "Square / X (□)"),
                ("TRIANGLE", "Triangle / Y (△)"),
                ("L1", "L1 (Left Bumper)"),
                ("R1", "R1 (Right Bumper)"),
                ("L2_BTN", "L2 (Left Trigger Button)"),
                ("R2_BTN", "R2 (Right Trigger Button)"),
                ("SHARE", "Share / Create"),
                ("OPTIONS", "Options / Start"),
                ("L3", "L3 (Left Stick Click)"),
                ("R3", "R3 (Right Stick Click)"),
                ("PS", "PS Button"),
                ("TOUCHPAD", "Touchpad Click"),
            ]

        current_idx = [0]
        recorded = dict(DEFAULT_MAPPINGS.get(active_profile, DEFAULT_MAPPINGS["sony"])["buttons"])
        if os.path.exists(mapping_file):
            try:
                with open(mapping_file, "r", encoding="utf-8") as f:
                    raw_cfg = json.load(f)
                    if "profiles" in raw_cfg and active_profile in raw_cfg["profiles"]:
                        recorded.update(raw_cfg["profiles"][active_profile].get("buttons", {}))
                    elif "buttons" in raw_cfg and active_profile == "sony":
                        recorded.update(raw_cfg["buttons"])
            except Exception:
                pass

        stop_listener = threading.Event()

        title_lbl = tk.Label(root, text=f"{profile_title} Calibration Wizard", font=("Segoe UI", 14, "bold"), bg=bg_color, fg=accent_color)
        title_lbl.pack(pady=(15, 5))

        desc_lbl = tk.Label(root, text="Press each button on your controller when prompted.", font=("Segoe UI", 10), bg=bg_color, fg="#a6adc8")
        desc_lbl.pack(pady=(0, 15))

        card_frame = tk.Frame(root, bg="#252538", bd=2, relief="groove")
        card_frame.pack(fill="x", padx=30, pady=10)

        step_lbl = tk.Label(card_frame, text=f"Step 1 of {len(buttons_to_map)}", font=("Segoe UI", 10, "italic"), bg="#252538", fg="#9399b2")
        step_lbl.pack(pady=(10, 2))

        target_btn_lbl = tk.Label(card_frame, text="", font=("Segoe UI", 16, "bold"), bg="#252538", fg="#f38ba8")
        target_btn_lbl.pack(pady=(2, 10))

        status_lbl = tk.Label(root, text="Listening for input from phone...", font=("Segoe UI", 10), bg=bg_color, fg="#a6e3a1")
        status_lbl.pack(pady=5)

        progress = ttk.Progressbar(root, orient="horizontal", length=430, mode="determinate")
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
                out_cfg = {"profiles": dict(DEFAULT_MAPPINGS)}
                if os.path.exists(mapping_file):
                    try:
                        with open(mapping_file, "r", encoding="utf-8") as f:
                            saved = json.load(f)
                            if "profiles" in saved:
                                out_cfg["profiles"] = saved["profiles"]
                    except Exception:
                        pass
                if active_profile not in out_cfg["profiles"]:
                    out_cfg["profiles"][active_profile] = dict(DEFAULT_MAPPINGS.get(active_profile, DEFAULT_MAPPINGS["sony"]))
                out_cfg["profiles"][active_profile]["buttons"] = recorded
                with open(mapping_file, "w", encoding="utf-8") as f:
                    json.dump(out_cfg, f, indent=4)
                load_mapping(active_profile)
                messagebox.showinfo("TetherPad", f"{profile_title} mapping saved successfully!")
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
            recorded = dict(DEFAULT_MAPPINGS.get(active_profile, DEFAULT_MAPPINGS["sony"])["buttons"])
            try:
                out_cfg = {"profiles": dict(DEFAULT_MAPPINGS)}
                if os.path.exists(mapping_file):
                    try:
                        with open(mapping_file, "r", encoding="utf-8") as f:
                            saved = json.load(f)
                            if "profiles" in saved:
                                out_cfg["profiles"] = saved["profiles"]
                    except Exception:
                        pass
                out_cfg["profiles"][active_profile] = dict(DEFAULT_MAPPINGS.get(active_profile, DEFAULT_MAPPINGS["sony"]))
                with open(mapping_file, "w", encoding="utf-8") as f:
                    json.dump(out_cfg, f, indent=4)
                load_mapping(active_profile)
                messagebox.showinfo("TetherPad", f"Reset to default {profile_title} layout complete.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to reset mapping: {e}")
            finally:
                stop_listener.set()
                root.destroy()

        btn_frame = tk.Frame(root, bg=bg_color)
        btn_frame.pack(side="bottom", fill="x", pady=15, padx=30)

        skip_btn = tk.Button(btn_frame, text="Skip Button", command=on_skip, bg=btn_bg, fg=fg_color, relief="flat", padx=10, pady=5)
        skip_btn.pack(side="left")

        reset_btn = tk.Button(btn_frame, text="Reset Defaults", command=on_reset_defaults, bg="#45475a", fg=fg_color, relief="flat", padx=10, pady=5)
        reset_btn.pack(side="left", padx=10)

        cancel_btn = tk.Button(btn_frame, text="Cancel", command=lambda: (stop_listener.set(), root.destroy()), bg=btn_bg, fg=fg_color, relief="flat", padx=10, pady=5)
        cancel_btn.pack(side="right")

        def listen_events():
            target_node = device_node
            if not target_node:
                node, *rest = find_device_node()
                target_node = node
            if not target_node:
                root.after(0, lambda: status_lbl.config(text="Waiting for phone & controller connection...", fg="#f9e2af"))
                while not stop_listener.is_set() and not target_node:
                    time.sleep(1)
                    node, *rest = find_device_node()
                    target_node = node
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

def send_vibrate_broadcast(left, right, timeout=2):
    """Sends an ADB broadcast to ScreenGuard to vibrate the controller motors."""
    return _orig_run(
        [adb_cmd, "shell", "am", "broadcast", "-a", "com.ps5bridge.VIBRATE", "--ei", "l", str(left), "--ei", "r", str(right)],
        creationflags=CREATE_NO_WINDOW,
        timeout=timeout
    )

class GamepadBridge:
    """Wrapper that unifies Virtual DualShock 4 and Virtual Xbox 360 gamepads."""
    def __init__(self, c_type="sony", emulation="ds4"):
        self.lock = threading.Lock()
        self.c_type = "xbox" if c_type == "xbox" else "sony"
        self.emulation = (emulation or ("xbox" if self.c_type == "xbox" else "ds4")).lower()
        if self.emulation in ("xbox", "xbox360"):
            self.pad = vg.VX360Gamepad()
            print("[OK] Virtual Xbox 360 controller active on Windows/Steam!")
        else:
            self.pad = vg.VDS4Gamepad()
            self.ext_report = MY_DS4_REPORT_EX()
            self.ext_report.Report.bTouchPacketsN = 1
            self.ext_report.Report.sCurrentTouch.bIsUpTrackingNum1 = 0x80 # UP by default
            self.ext_report.Report.sCurrentTouch.bIsUpTrackingNum2 = 0x80
            self.ext_report.Report.sPreviousTouch[0].bIsUpTrackingNum1 = 0x80
            self.ext_report.Report.sPreviousTouch[0].bIsUpTrackingNum2 = 0x80
            self.ext_report.Report.sPreviousTouch[1].bIsUpTrackingNum1 = 0x80
            self.ext_report.Report.sPreviousTouch[1].bIsUpTrackingNum2 = 0x80
            self.touch_packet_counter = 0
            print("[OK] Virtual DualShock 4 controller active on Windows/Steam!")

        # Asynchronous rumble worker to prevent process spawning storms
        self._rumble_lock = threading.Lock()
        self._rumble_state = (0, 0)
        self._rumble_event = threading.Event()
        self._stop_rumble = threading.Event()
        self._rumble_thread = threading.Thread(target=self._rumble_worker, daemon=True)
        self._rumble_thread.start()

        # Register for rumble events
        self.pad.register_notification(self._rumble_cb)

    def _rumble_cb(self, client, target, large_motor, small_motor, led_number, user_data):
        with self._rumble_lock:
            self._rumble_state = (large_motor, small_motor)
        self._rumble_event.set()

    def _rumble_worker(self):
        last_sent = (0, 0)
        while not self._stop_rumble.is_set():
            # Wait up to 0.2s for incoming rumble event or refresh cycle
            self._rumble_event.wait(timeout=0.2)
            self._rumble_event.clear()

            if self._stop_rumble.is_set():
                break

            with self._rumble_lock:
                large, small = self._rumble_state

            if (large, small) == (0, 0):
                if last_sent != (0, 0):
                    last_sent = (0, 0)
                    try:
                        send_vibrate_broadcast(0, 0, timeout=1)
                    except Exception as e:
                        print(f"[Rumble Warning] {e}")
                continue

            last_sent = (large, small)
            power = max(large, small)
            # ScreenGuard calculates duration = power * 0.5 ms.
            # Scale power so duration is between 200ms - 500ms (overcomes ERM motor inertia).
            # Refreshing every 0.2s maintains continuous, uninterrupted sustained rumble.
            scaled = int(400 + (power / 255.0) * 600)
            send_l = scaled if large >= small else int(scaled * (large / max(small, 1)))
            send_r = scaled if small >= large else int(scaled * (small / max(large, 1)))

            try:
                print(f"[Rumble] ViGEm feedback -> L={large}, R={small} (Phone pulse: L={send_l}, R={send_r})")
                send_vibrate_broadcast(send_l, send_r, timeout=1)
            except Exception as e:
                print(f"[Rumble Warning] {e}")

    def press_button(self, btn):
        if not getattr(self, 'pad', None): return
        with self.lock:
            self.pad.press_button(button=btn)

    def release_button(self, btn):
        if not getattr(self, 'pad', None): return
        with self.lock:
            self.pad.release_button(button=btn)

    def press_special(self, btn):
        if not getattr(self, 'pad', None): return
        with self.lock:
            if self.emulation == "ds4":
                self.pad.press_special_button(special_button=btn)
            else:
                self.pad.press_button(button=btn)

    def release_special(self, btn):
        if not getattr(self, 'pad', None): return
        with self.lock:
            if self.emulation == "ds4":
                self.pad.release_special_button(special_button=btn)
            else:
                self.pad.release_button(button=btn)

    @staticmethod
    def _to_xinput_axis(val, invert=False):
        """Maps 0..255 Android HID axis to full -32768..32767 XInput range."""
        if val >= 128:
            res = int(((val - 128) / 127.0) * 32767)
        else:
            res = int(((val - 128) / 128.0) * 32768)
        if invert:
            res = -res
        return max(-32768, min(32767, res))

    def set_left_stick(self, x_val, y_val):
        if not getattr(self, 'pad', None): return
        with self.lock:
            if self.emulation == "ds4":
                self.pad.left_joystick(x_value=x_val, y_value=y_val)
            else:
                x_16 = self._to_xinput_axis(x_val, invert=False)
                y_16 = self._to_xinput_axis(y_val, invert=True)
                self.pad.left_joystick(x_value=x_16, y_value=y_16)

    def set_right_stick(self, x_val, y_val):
        if not getattr(self, 'pad', None): return
        with self.lock:
            if self.emulation == "ds4":
                self.pad.right_joystick(x_value=x_val, y_value=y_val)
            else:
                x_16 = self._to_xinput_axis(x_val, invert=False)
                y_16 = self._to_xinput_axis(y_val, invert=True)
                self.pad.right_joystick(x_value=x_16, y_value=y_16)

    def set_triggers(self, l2_val=None, r2_val=None):
        if not getattr(self, 'pad', None): return
        with self.lock:
            if l2_val is not None:
                self.pad.left_trigger(value=l2_val)
            if r2_val is not None:
                self.pad.right_trigger(value=r2_val)

    def set_dpad(self, dpad_x, dpad_y):
        if not getattr(self, 'pad', None): return
        with self.lock:
            if self.emulation == "ds4":
                if dpad_x == -1 and dpad_y == -1: d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHWEST
                elif dpad_x == 1 and dpad_y == -1: d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHEAST
                elif dpad_x == -1 and dpad_y == 1: d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHWEST
                elif dpad_x == 1 and dpad_y == 1: d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHEAST
                elif dpad_y == -1: d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH
                elif dpad_y == 1: d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH
                elif dpad_x == -1: d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST
                elif dpad_x == 1: d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST
                else: d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE
                self.pad.directional_pad(direction=d)
            else:
                self.pad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
                self.pad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
                self.pad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
                self.pad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)
                if dpad_y == -1: self.pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
                elif dpad_y == 1: self.pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
                if dpad_x == -1: self.pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
                elif dpad_x == 1: self.pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)

    def set_touchpad(self, is_down, x, y):
        if self.emulation != "ds4" or not getattr(self, 'pad', None): return
        with self.lock:
            # Move current to previous
            self.ext_report.Report.sPreviousTouch[1] = self.ext_report.Report.sPreviousTouch[0]
            self.ext_report.Report.sPreviousTouch[0] = self.ext_report.Report.sCurrentTouch
            
            # Generate new touch
            self.touch_packet_counter = (self.touch_packet_counter + 1) & 0xFF
            self.ext_report.Report.sCurrentTouch.bPacketCounter = self.touch_packet_counter
            
            if is_down:
                # Down (active low, bit 7 is 0)
                self.ext_report.Report.sCurrentTouch.bIsUpTrackingNum1 = 0x00
                self.ext_report.Report.sCurrentTouch.bTouchData1[0] = x & 0xFF
                self.ext_report.Report.sCurrentTouch.bTouchData1[1] = ((x >> 8) & 0x0F) | ((y & 0x0F) << 4)
                self.ext_report.Report.sCurrentTouch.bTouchData1[2] = (y >> 4) & 0xFF
            else:
                # Up (bit 7 is 1)
                self.ext_report.Report.sCurrentTouch.bIsUpTrackingNum1 = 0x80
            
    def update(self):
        if not getattr(self, 'pad', None): return
        with self.lock:
            if self.emulation == "ds4":
                import vgamepad.win.vigem_client as vcli
                import vgamepad.win.vigem_commons as vcom
                self.ext_report.Report.bThumbLX = self.pad.report.bThumbLX
                self.ext_report.Report.bThumbLY = self.pad.report.bThumbLY
                self.ext_report.Report.bThumbRX = self.pad.report.bThumbRX
                self.ext_report.Report.bThumbRY = self.pad.report.bThumbRY
                self.ext_report.Report.wButtons = self.pad.report.wButtons
                self.ext_report.Report.bSpecial = self.pad.report.bSpecial
                self.ext_report.Report.bTriggerL = self.pad.report.bTriggerL
                self.ext_report.Report.bTriggerR = self.pad.report.bTriggerR
                vcli.vigem_target_ds4_update_ex_ptr(self.pad._busp, self.pad._devicep, ctypes.cast(ctypes.pointer(self.ext_report), ctypes.POINTER(vcom.DS4_REPORT_EX)))
            else:
                self.pad.update()

    def close(self):
        try:
            if hasattr(self, '_stop_rumble'):
                self._stop_rumble.set()
                self._rumble_event.set()
            with self.lock:
                if hasattr(self, 'pad') and self.pad is not None:
                    del self.pad
                    self.pad = None
        except Exception:
            pass

def is_vigembus_installed():
    """Checks if ViGEmBus kernel driver or service is installed on the system."""
    if not winreg:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\ViGEmBus")
        winreg.CloseKey(key)
        return True
    except (OSError, AttributeError):
        pass

    sys_root = os.environ.get("SystemRoot", r"C:\Windows")
    sys_driver = os.path.join(sys_root, "System32", "drivers", "ViGEmBus.sys")
    return os.path.exists(sys_driver)

def ensure_vigembus(force=False):
    """
    Ensures the ViGEmBus driver is installed before importing or using vgamepad.
    If missing, prompts the user with a native dialog to automatically download and run the installer.
    """
    if not force and is_vigembus_installed():
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
if os.name == "nt":
    ensure_vigembus()

    try:
        import vgamepad as vg
    except Exception as e:
        if "VIGEM_ERROR_BUS_NOT_FOUND" in str(e):
            # Driver registry key was found, but bus could not be initialized (likely incomplete removal/install)
            ensure_vigembus(force=True)
        else:
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Failed to initialize virtual gamepad:\n{e}",
                "TetherPad - Initialization Error",
                MB_ICONERROR | MB_TOPMOST
            )
            sys.exit(1)
else:
    try:
        import vgamepad as vg
    except Exception:
        vg = None

import ctypes
from ctypes import c_ubyte, c_ushort, c_short, Structure, Union

class MY_DS4_TOUCH(Structure):
    _pack_ = 1
    _fields_ = [
        ('bPacketCounter', c_ubyte),
        ('bIsUpTrackingNum1', c_ubyte),
        ('bTouchData1', c_ubyte * 3),
        ('bIsUpTrackingNum2', c_ubyte),
        ('bTouchData2', c_ubyte * 3)
    ]

class MY_DS4_SUB_REPORT_EX(Structure):
    _pack_ = 1
    _fields_ = [
        ('bThumbLX', c_ubyte), ('bThumbLY', c_ubyte), ('bThumbRX', c_ubyte), ('bThumbRY', c_ubyte),
        ('wButtons', c_ushort), ('bSpecial', c_ubyte), ('bTriggerL', c_ubyte), ('bTriggerR', c_ubyte),
        ('wTimestamp', c_ushort), ('bBatteryLvl', c_ubyte),
        ('wGyroX', c_short), ('wGyroY', c_short), ('wGyroZ', c_short),
        ('wAccelX', c_short), ('wAccelY', c_short), ('wAccelZ', c_short),
        ('_bUnknown1', c_ubyte * 5), ('bBatteryLvlSpecial', c_ubyte),
        ('_bUnknown2', c_ubyte * 2), ('bTouchPacketsN', c_ubyte),
        ('sCurrentTouch', MY_DS4_TOUCH),
        ('sPreviousTouch', MY_DS4_TOUCH * 2)
    ]

class MY_DS4_REPORT_EX(Union):
    _pack_ = 1
    _fields_ = [
        ('Report', MY_DS4_SUB_REPORT_EX),
        ('ReportBuffer', c_ubyte * 63)
    ]

if os.name == "nt":
    import pystray
    from PIL import Image, ImageDraw
else:
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception:
        pystray = None
        Image = None
        ImageDraw = None

ensure_mapping_config()

def load_mapping(profile_type="sony"):
    """
    Loads controller mapping configuration for 'sony' or 'xbox' profile.
    Supports both multi-profile and legacy single-profile mapping.json.
    """
    global BTN_MAP, SPECIAL_BTN_MAP, AXIS_LX, AXIS_LY, AXIS_RX, AXIS_RY, AXIS_L2, AXIS_R2, DPAD_X, DPAD_Y, current_profile_type
    current_profile_type = profile_type
    ensure_mapping_config()

    config = {}
    if os.path.exists(mapping_file):
        try:
            with open(mapping_file, "r", encoding="utf-8") as f:
                raw_cfg = json.load(f)
                if "profiles" in raw_cfg:
                    config = raw_cfg["profiles"].get(profile_type, DEFAULT_MAPPINGS.get(profile_type, DEFAULT_MAPPINGS["sony"]))
                elif "buttons" in raw_cfg and profile_type == "sony":
                    config = raw_cfg
                else:
                    config = DEFAULT_MAPPINGS.get(profile_type, DEFAULT_MAPPINGS["sony"])
        except Exception as e:
            print(f"[!] Error loading mapping.json: {e}")
            config = DEFAULT_MAPPINGS.get(profile_type, DEFAULT_MAPPINGS["sony"])
    else:
        config = DEFAULT_MAPPINGS.get(profile_type, DEFAULT_MAPPINGS["sony"])

    if profile_type == "xbox":
        def_btns = DEFAULT_MAPPINGS["xbox"]["buttons"]
        def_axes = DEFAULT_MAPPINGS["xbox"]["axes"]
    elif profile_type == "sony_modern":
        def_btns = DEFAULT_MAPPINGS["sony_modern"]["buttons"]
        def_axes = DEFAULT_MAPPINGS["sony_modern"]["axes"]
    else:
        def_btns = DEFAULT_MAPPINGS["sony"]["buttons"]
        def_axes = DEFAULT_MAPPINGS["sony"]["axes"]

    b = {**def_btns, **config.get("buttons", {})}
    a = {**def_axes, **config.get("axes", {})}

    if profile_type == "xbox":
        BTN_MAP = {
            b.get("A"): vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
            b.get("B"): vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
            b.get("X"): vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
            b.get("Y"): vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
            b.get("LB"): vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
            b.get("RB"): vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
            b.get("BACK"): vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
            b.get("START"): vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
            b.get("L3"): vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
            b.get("R3"): vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
        }
        BTN_MAP = {k: v for k, v in BTN_MAP.items() if k}
        SPECIAL_BTN_MAP = {
            b.get("GUIDE"): vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE
        }
        SPECIAL_BTN_MAP = {k: v for k, v in SPECIAL_BTN_MAP.items() if k}

        AXIS_LX = a.get("LX", {}).get("code")
        AXIS_LY = a.get("LY", {}).get("code")
        AXIS_RX = a.get("RX", {}).get("code")
        AXIS_RY = a.get("RY", {}).get("code")
        AXIS_L2 = a.get("LT", a.get("L2", {})).get("code")
        AXIS_R2 = a.get("RT", a.get("R2", {})).get("code")
        DPAD_X = a.get("DPAD_X", {}).get("code")
        DPAD_Y = a.get("DPAD_Y", {}).get("code")

    else:
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

    return config

def resolve_profile(detected_profile, device_name="", touchpad_node=None, product_id="", android_ver=0):
    """
    Resolves the exact controller profile.
    For Sony controllers:
    - If a companion touchpad node is present (Linux hid-sony >=4.10 / hid-playstation multi-node),
      or running on Android 10+ (modern evdev layout), resolve to 'sony_modern'.
    - Otherwise (single-node legacy MTK HID on Android 4.4/7.0), retain 'sony' legacy profile.
    """
    if detected_profile == "sony":
        if touchpad_node or android_ver >= 10:
            return "sony_modern"
    return detected_profile

def find_device_node(android_ver=0):
    """
    Scans adb getevent -i and automatically identifies the controller.
    Returns (main_node, profile_type, display_name, touchpad_node).
    """
    try:
        proc = subprocess.run([adb_cmd, "shell", "getevent -i"], capture_output=True, text=True)
        device_entries = []
        current_entry = {}
        for line in proc.stdout.split('\n'):
            line_str = line.strip()
            if line.startswith("add device"):
                if current_entry and "node" in current_entry:
                    device_entries.append(current_entry)
                current_node = line.split(":")[-1].strip()
                current_entry = {"node": current_node, "name": "", "vendor": "", "product": ""}
            elif line_str.startswith("name:"):
                current_entry["name"] = line_str.split(":", 1)[-1].strip().strip('"')
            elif line_str.startswith("vendor"):
                current_entry["vendor"] = line_str.split()[-1].strip().lower()
            elif line_str.startswith("product"):
                current_entry["product"] = line_str.split()[-1].strip().lower()

        if current_entry and "node" in current_entry:
            device_entries.append(current_entry)

        # 1. Identify companion Touchpad sub-node (Android 12+ hid-playstation split)
        touchpad_node = None
        for dev in device_entries:
            name_u = dev["name"].upper()
            vendor = dev.get("vendor", "").lower()
            if "TOUCHPAD" in name_u and (any(k in name_u for k in ["DUALSENSE", "WIRELESS CONTROLLER", "SONY", "PLAYSTATION"]) or vendor == "054c"):
                touchpad_node = dev["node"]
                break

        # 2. Identify main controller node, strictly ignoring companion nodes (TOUCHPAD, MOTION, SENSOR)
        target_ver = android_ver or _device_info.get("android_ver", 0)
        for dev in device_entries:
            name_u = dev["name"].upper()
            vendor = dev.get("vendor", "").lower()

            # Skip companion nodes for main button/axis controller selection
            if any(comp in name_u for comp in ["TOUCHPAD", "MOTION", "SENSOR"]):
                continue

            if "XBOX" in name_u or vendor == "045e":
                return dev["node"], "xbox", dev["name"] or "Xbox Controller", None
            if any(k in name_u for k in ["WIRELESS CONTROLLER", "SONY", "DUALSENSE", "PLAYSTATION"]) or vendor == "054c":
                prof = resolve_profile("sony", dev.get("name", ""), touchpad_node, dev.get("product", ""), target_ver)
                return dev["node"], prof, dev["name"] or "PlayStation Controller", touchpad_node
            if any(k in name_u for k in ["GAMEPAD", "JOYSTICK", "MTK BT HID"]):
                return dev["node"], "sony", dev["name"] or "Generic Controller", None
    except Exception:
        pass
    return None, None, None, None

# --- Global state ---
_cleanup_done = False
_cleanup_lock = threading.Lock()
stop_event   = threading.Event()
gamepad      = None
input_process = None
touchpad_process = None
touchpad_t = None
usb_t = None
bt_t = None
device_node = None
touchpad_node = None
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
    apk_path = os.path.join(get_base_path(), "ScreenGuard.apk")
    if os.path.exists(apk_path):
        print("[+] ScreenGuard (BlackHole) is being prepared...")
        
        # Kurulu olup olmadigini kontrol et
        check = subprocess.run([adb_cmd, "shell", "pm", "list", "packages", "com.ps5bridge.screenguard"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        if "com.ps5bridge.screenguard" not in check.stdout:
            print("  [+] Installing TetherPad APK to phone...")
            res = subprocess.run(
                [adb_cmd, "install", "-r", "-d", "-g", apk_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            if res.returncode != 0:
                subprocess.run(
                    [adb_cmd, "install", "-r", "-d", apk_path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
        else:
            print("  [+] APK is already installed, skipping install.")
            
        subprocess.run(
            [adb_cmd, "shell", "am", "start", "-n", "com.ps5bridge.screenguard/.MainActivity"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        print("[+] Screen secured (Press Home on the phone to exit).")
    else:
        print("[-] ScreenGuard.apk not found. Screen protection skipped.")

def teardown_screenguard():
    """Program kapandiginda siyah ekrani kapatir ve APK'yi kaldirir."""
    print("  [4] ScreenGuard stopping and uninstalling...")
    subprocess.run(
        [adb_cmd, "shell", "am", "force-stop", "com.ps5bridge.screenguard"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    subprocess.run(
        [adb_cmd, "uninstall", "com.ps5bridge.screenguard"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def _terminate_proc(proc):
    """Safely terminates a subprocess if still running."""
    if proc and proc.poll() is None:
        try:
            proc.terminate()
        except Exception:
            pass

# ============================================================
# COMPANION TOUCHPAD WORKER (Modern Android 12+ / DualSense)
# ============================================================
def touchpad_worker(tp_node, bridge, stop_evt):
    global touchpad_process
    print(f"[OK] Companion Touchpad listener started for {tp_node}...")
    local_proc = None
    try:
        local_proc = subprocess.Popen(
            [adb_cmd, "shell", "-tt", f"getevent {tp_node}"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
        )
        touchpad_process = local_proc
        tp_state = {'x': 0, 'y': 0, 'is_down': False}
        for line in iter(local_proc.stdout.readline, ''):
            if stop_evt.is_set():
                break
            parts = line.strip().split()
            if len(parts) != 3:
                continue
            ev_type, ev_code = parts[0], parts[1]
            try:
                ev_val = int(parts[2], 16)
            except ValueError:
                continue

            if ev_type == '0003':
                if ev_code == '0035':
                    tp_state['x'] = ev_val
                elif ev_code == '0036':
                    tp_state['y'] = ev_val
                elif ev_code == '0039':
                    if ev_val in (0xffffffff, -1):
                        tp_state['is_down'] = False
                    else:
                        tp_state['is_down'] = True
            elif ev_type == '0001':
                if ev_code == '0110':
                    if ev_val == 1:
                        bridge.press_special(vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_TOUCHPAD)
                    elif ev_val == 0:
                        bridge.release_special(vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_TOUCHPAD)
                    bridge.update()
            elif ev_type == '0000' and ev_code == '0000':
                bridge.set_touchpad(tp_state['is_down'], tp_state['x'], tp_state['y'])
                bridge.update()
    except Exception as e:
        print(f"[Touchpad Worker Warning] {e}")
    finally:
        _terminate_proc(local_proc)
        if touchpad_process == local_proc:
            touchpad_process = None

# ============================================================
# USB WATCHDOG
# ============================================================
def usb_watchdog():
    global input_process, touchpad_process
    time.sleep(2.0)
    subprocess.run([adb_cmd, "wait-for-disconnect"])
    if not stop_event.is_set():
        print("\n[!] USB/ADB connection lost!")
        _terminate_proc(input_process)
        _terminate_proc(touchpad_process)
        cleanup(reason="USB baglantisi kesildi")

# ============================================================
# BT WATCHDOG
# ============================================================
def bt_watchdog():
    global input_process, touchpad_process, device_node
    time.sleep(3.0)
    cmd = f"while [ -e {device_node} ]; do sleep 1.5; done; echo GONE"
    try:
        proc = subprocess.run([adb_cmd, "shell", cmd], capture_output=True, text=True)
        if not stop_event.is_set() and "GONE" in proc.stdout:
            print("\n[!] Bluetooth connection lost! Controller disconnected.")
            _terminate_proc(input_process)
            _terminate_proc(touchpad_process)
            cleanup(reason="Bluetooth baglantisi koptu")
    except Exception:
        pass

# ============================================================
# TEMIZLIK & ADB SUNUCU YONETIMI
# ============================================================
def stop_adb_server():
    """Gracefully terminates the background adb daemon to avoid file locking on Windows."""
    try:
        if os.path.exists(adb_cmd):
            subprocess.run([adb_cmd, "kill-server"], creationflags=CREATE_NO_WINDOW, timeout=3)
    except Exception as e:
        print(f"[!] Warning during adb shutdown: {e}")


atexit.register(stop_adb_server)


def cleanup(reason=""):
    global _cleanup_done, gamepad, input_process, touchpad_process

    with _cleanup_lock:
        if _cleanup_done:
            return
        _cleanup_done = True

    print(f"\n[Shutting down] {reason}")

    stop_event.set()

    _terminate_proc(input_process)
    _terminate_proc(touchpad_process)

    print("  [3] Removing virtual gamepad...")
    try:
        if gamepad is not None:
            gamepad.close()
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
    global input_process, touchpad_process, touchpad_t, gamepad, _cleanup_done, sticks, stop_event, BTN_MAP, SPECIAL_BTN_MAP, AXIS_LX, AXIS_LY, AXIS_RX, AXIS_RY, AXIS_L2, AXIS_R2, DPAD_X, DPAD_Y, usb_t, bt_t, device_node, touchpad_node
    
    while True:
        try:
            _cleanup_done = False
            stop_event.clear()
            
            print("=" * 55)
            print("  TetherPad - Starting up")
            print("=" * 55)
            
            print(f"\n[Waiting] Connect your controller to your phone via Bluetooth...")
            print(f"           (Ensure the USB cable is connected)\n")
            
            # USB'yi bekle
            subprocess.run([adb_cmd, "wait-for-device"], creationflags=CREATE_NO_WINDOW)
            detect_device_info()
            
            # BT kolu bekle ve otomatik bul
            device_node = None
            detected_profile = "sony"
            detected_name = "Controller"
            touchpad_node = None
            while True:
                node, p_type, d_name, tp_node = find_device_node()
                if node:
                    device_node = node
                    detected_profile = p_type or "sony"
                    detected_name = d_name or "Controller"
                    touchpad_node = tp_node
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
            
            print(f"\n[OK] Controller found: {device_node} ({detected_name})")
            print(f"[Profile] Active Controller Profile: {detected_profile.upper()}")
            
            # ADIM 1.5: Mapping ve emulasyon konfigürasyonunu hazırla
            prof_cfg = load_mapping(detected_profile)
            emul = (prof_cfg.get("emulation") if prof_cfg else None) or ("xbox" if detected_profile == "xbox" else "ds4")
            
            # ADIM 2: Sanal gamepad olustur (Xbox ise VX360, Sony ise VDS4)
            print(f"\n[OK] Creating virtual {emul.upper()} controller (Profile: {detected_profile.upper()})...")
            gamepad = GamepadBridge(detected_profile, emulation=emul)
            
            # ADIM 3: Ekran kapatici THREAD'i baslat
            print("[OK] Starting screen protector in background...")
            threading.Thread(target=setup_screenguard, daemon=True).start()
            print("[OK] Screen protector installation started!")
            
            # ADIM 4: getevent dinleyicisi
            print(f"\n[OK] {device_node} dinleniyor...\n")
            input_process = subprocess.Popen(
                [adb_cmd, "shell", "-tt", f"getevent {device_node}"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
            )
            
            # ADIM 4.5: Companion Touchpad dinleyicisi (Modern Android 12+ / DualSense)
            if touchpad_node and detected_profile in ("sony", "sony_modern"):
                touchpad_t = threading.Thread(
                    target=touchpad_worker,
                    args=(touchpad_node, gamepad, stop_event),
                    daemon=True
                )
                touchpad_t.start()
            
            print(f"Listening for {detected_profile.upper()} input... (Ctrl+C to stop completely)")
            print("=> NOTE: Undefined inputs will be ignored.\n")
            
            def map_axis(val):
                return max(0, min(255, val))
            
            sticks = {'lx': 128, 'ly': 128, 'rx': 128, 'ry': 128}
            dpad_state = {'x': 0, 'y': 0}
            touch_state = {'x': 0, 'y': 0, 'is_down': False}
            
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
                            gamepad.press_button(btn)
                        elif event_value == 0:
                            gamepad.release_button(btn)
                    elif event_code in SPECIAL_BTN_MAP:
                        btn = SPECIAL_BTN_MAP[event_code]
                        if event_value == 1:
                            gamepad.press_special(btn)
                        elif event_value == 0:
                            gamepad.release_special(btn)
        
                elif event_type == '0003':
                    if event_code == AXIS_LX:
                        sticks['lx'] = map_axis(event_value)
                        gamepad.set_left_stick(sticks['lx'], sticks['ly'])
                    elif event_code == AXIS_LY:
                        sticks['ly'] = map_axis(event_value)
                        gamepad.set_left_stick(sticks['lx'], sticks['ly'])
                    elif event_code == AXIS_RX:
                        sticks['rx'] = map_axis(event_value)
                        gamepad.set_right_stick(sticks['rx'], sticks['ry'])
                    elif event_code == AXIS_RY:
                        sticks['ry'] = map_axis(event_value)
                        gamepad.set_right_stick(sticks['rx'], sticks['ry'])
                    elif event_code == AXIS_L2:
                        gamepad.set_triggers(l2_val=map_axis(event_value))
                    elif event_code == AXIS_R2:
                        gamepad.set_triggers(r2_val=map_axis(event_value))
                    elif event_code == DPAD_X:
                        if event_value in (0xffffffff, 0xffff) or (event_value & 0x80000000):
                            dpad_state['x'] = -1
                        elif event_value == 1:
                            dpad_state['x'] = 1
                        else:
                            dpad_state['x'] = 0
                        gamepad.set_dpad(dpad_state['x'], dpad_state['y'])
                    elif event_code == DPAD_Y:
                        if event_value in (0xffffffff, 0xffff) or (event_value & 0x80000000):
                            dpad_state['y'] = -1
                        elif event_value == 1:
                            dpad_state['y'] = 1
                        else:
                            dpad_state['y'] = 0
                        gamepad.set_dpad(dpad_state['x'], dpad_state['y'])
                    elif event_code == '0035':
                        touch_state['x'] = event_value
                    elif event_code == '0036':
                        touch_state['y'] = event_value
                    elif event_code == '0039':
                        if event_value == 0xffffffff:
                            touch_state['is_down'] = False
                        else:
                            touch_state['is_down'] = True
        
                elif event_type == '0000' and event_code == '0000':
                    if not touchpad_node:
                        gamepad.set_touchpad(touch_state['is_down'], touch_state['x'], touch_state['y'])
                    gamepad.update()
            
            if not stop_event.is_set():
                print("\n[!] Bluetooth disconnected or controller turned off!")
                
        except KeyboardInterrupt:
            print("\nUser interrupted via Ctrl+C.")
            cleanup(reason="User Request (Ctrl+C)")
            stop_adb_server()
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
    if getattr(sys, 'frozen', False) or hasattr(sys, 'nuitka') or "__compiled__" in globals():
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

log_path = os.path.join(DATA_DIR, "tetherpad.log")
sys.stdout = open(log_path, "w", encoding="utf-8", buffering=1)
sys.stderr = sys.stdout

def open_logs(icon, item):
    try:
        os.startfile(log_path)
    except:
        pass

def test_vibration(icon=None, item=None):
    """Sends a 1-second test vibration broadcast to phone/controller."""
    def _do_vib():
        print("[Rumble Test] Triggering 1-second test vibration on controller...")
        try:
            send_vibrate_broadcast(2000, 2000, timeout=3)
            print("[Rumble Test] Vibration signal sent successfully.")
        except Exception as e:
            print(f"[Rumble Test Error] {e}")
    threading.Thread(target=_do_vib, daemon=True).start()

def quit_app(icon, item):
    icon.stop()
    stop_event.set()
    cleanup(reason="User Request (Tray Quit)")
    stop_adb_server()
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
    
    # Create the tray menu if pystray is available
    if pystray:
        menu = pystray.Menu(
            pystray.MenuItem("Show Logs (Notepad)", open_logs),
            pystray.MenuItem("Calibrate Controller", open_calibration_wizard),
            pystray.MenuItem("Test Vibration (1s)", test_vibration),
            pystray.MenuItem("Start with Windows", toggle_startup, checked=lambda item: is_startup_enabled()),
            pystray.MenuItem("Quit", quit_app)
        )
        icon = pystray.Icon("TetherPad", create_image(), "TetherPad Bridge", menu)
        icon.run()
    else:
        worker.join()

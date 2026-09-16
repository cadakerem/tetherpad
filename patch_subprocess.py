import os

with open('tetherpad.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Add the CREATE_NO_WINDOW constant definition right after imports
if 'CREATE_NO_WINDOW' not in code:
    code = code.replace('import subprocess', 'import subprocess\n\nif os.name == "nt":\n    CREATE_NO_WINDOW = 0x08000000\nelse:\n    CREATE_NO_WINDOW = 0\n')

# Replace exact subprocess calls
reps = [
    ('subprocess.run([adb_cmd, "wait-for-device"])', 'subprocess.run([adb_cmd, "wait-for-device"], creationflags=CREATE_NO_WINDOW)'),
    ('subprocess.run([adb_cmd, "shell", "getevent", "-p"], capture_output=True, text=True)', 'subprocess.run([adb_cmd, "shell", "getevent", "-p"], capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)'),
    ('subprocess.run([adb_cmd, "shell", "dumpsys", "input"], capture_output=True, text=True)', 'subprocess.run([adb_cmd, "shell", "dumpsys", "input"], capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)'),
    ('subprocess.run([adb_cmd, "uninstall", "com.ps5bridge.screenguard"], capture_output=True)', 'subprocess.run([adb_cmd, "uninstall", "com.ps5bridge.screenguard"], capture_output=True, creationflags=CREATE_NO_WINDOW)'),
    ('subprocess.run([adb_cmd, "install", "-r", "ScreenGuard.apk"], capture_output=True)', 'subprocess.run([adb_cmd, "install", "-r", "ScreenGuard.apk"], capture_output=True, creationflags=CREATE_NO_WINDOW)'),
    ('subprocess.run([adb_cmd, "shell", "am", "start", "-n", "com.ps5bridge.screenguard/.MainActivity"], capture_output=True)', 'subprocess.run([adb_cmd, "shell", "am", "start", "-n", "com.ps5bridge.screenguard/.MainActivity"], capture_output=True, creationflags=CREATE_NO_WINDOW)'),
    ('subprocess.run([adb_cmd, "shell", "am", "force-stop", "com.ps5bridge.screenguard"], capture_output=True)', 'subprocess.run([adb_cmd, "shell", "am", "force-stop", "com.ps5bridge.screenguard"], capture_output=True, creationflags=CREATE_NO_WINDOW)'),
    ('subprocess.Popen([adb_cmd, "shell", "getevent"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)', 'subprocess.Popen([adb_cmd, "shell", "getevent"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, creationflags=CREATE_NO_WINDOW)')
]

for old, new in reps:
    code = code.replace(old, new)

with open('tetherpad.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Subprocess calls patched.")

import sys
from cx_Freeze import setup, Executable

build_exe_options = {
    "packages": ["os", "sys", "json", "threading", "subprocess", "time", "winreg", "tkinter", "pystray", "PIL", "vgamepad", "urllib", "http", "ssl", "socket"],
    "excludes": ["unittest", "email", "pydoc"],
    "include_files": ["ViGEmBus_Setup.exe"]
}

base = "Win32GUI" if sys.platform == "win32" else None

setup(
    name="TetherPad",
    version="1.3.0",
    description="TetherPad Bridge",
    options={"build_exe": build_exe_options},
    executables=[Executable("tetherpad.py", base=base, icon="icon.ico", target_name="tetherpad.exe")],
)

import sys
from cx_Freeze import setup, Executable

build_exe_options = {
    "packages": ["os", "sys", "json", "threading", "subprocess", "time", "winreg", "tkinter", "pystray", "PIL", "vgamepad"],
    "excludes": ["unittest", "email", "http", "xml", "pydoc"],
}

base = "Win32GUI" if sys.platform == "win32" else None

setup(
    name="TetherPad",
    version="1.2.0",
    description="TetherPad Bridge",
    options={"build_exe": build_exe_options},
    executables=[Executable("tetherpad.py", base=base, target_name="tetherpad.exe")],
)

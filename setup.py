import sys
from cx_Freeze import setup, Executable

build_exe_options = {
    "packages": [
        "os", "sys", "json", "threading", "subprocess", "time", "winreg",
        "tkinter", "pystray", "PIL", "vgamepad", "urllib", "http", "ssl",
        "socket", "ctypes",
        # six and queue are dynamically referenced by pystray._win32 via six.moves.queue
        "queue", "six",
    ],
    "excludes": [
        "unittest", "email", "pydoc", "test",
        "numpy", "matplotlib", "IPython", "ipykernel", "jedi", "lxml", "trio",
        "debugpy", "zmq", "tornado", "jupyter_client", "jupyter_core", "_pytest",
        "pytest", "wheel", "setuptools", "parso", "pygments", "prompt_toolkit",
        "fontTools", "kiwisolver", "contourpy", "cycler", "dill", "yaml",
        "sqlite3", "_sqlite3", "curses", "dbm", "multiprocessing"
    ],
    "include_files": ["ViGEmBus_Setup.exe", "platform-tools/", ("ScreenGuard/ScreenGuard.apk", "ScreenGuard.apk"), "icon.ico", "LICENSE", "THIRD_PARTY_LICENSES.md"]
}

base = "Win32GUI" if sys.platform == "win32" else None

setup(
    name="TetherPad",
    version="1.4.2",
    description="TetherPad Bridge",
    options={"build_exe": build_exe_options},
    executables=[Executable("tetherpad.py", base=base, icon="icon.ico", target_name="tetherpad.exe")],
)

"""
Minimal Android SDK setup:
- Sadece aapt, dx, apksigner ve android.jar indirir (~80MB)
- Android Studio gerektirmez
- Tek calistir: python setup_sdk.py
"""
import os, sys, urllib.request, zipfile, shutil

SDK_DIR = r"C:\Android\MiniSdk"
BT_VER  = "33.0.2"  # build-tools versiyonu
PLAT    = "android-28"

URLS = {
    "build-tools": f"https://dl.google.com/android/repository/build-tools_r{BT_VER}-windows.zip",
    "platform":    f"https://dl.google.com/android/repository/platform-28_r06.zip",
}

def dl(url, dest):
    if os.path.exists(dest):
        print(f"  Zaten var: {dest}")
        return
    print(f"  Indiriliyor: {os.path.basename(dest)} ...")
    urllib.request.urlretrieve(url, dest, 
        lambda b, bs, ts: print(f"\r  {b*bs/1024/1024:.1f}/{ts/1024/1024:.1f} MB", end=""))
    print()

def setup():
    os.makedirs(SDK_DIR, exist_ok=True)
    tmp = os.path.join(SDK_DIR, "tmp")
    os.makedirs(tmp, exist_ok=True)

    for name, url in URLS.items():
        z = os.path.join(tmp, f"{name}.zip")
        dl(url, z)
        out = os.path.join(SDK_DIR, name)
        if not os.path.exists(out):
            print(f"  Cikartiliyor: {name}...")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(out)
    
    # PATH hint yaz
    bt_dir = os.path.join(SDK_DIR, "build-tools")
    print(f"\n✅ SDK hazir: {SDK_DIR}")
    print(f"\nBuild-tools: {bt_dir}")
    print("\nSimdi: python build_apk.py")
    
    # ANDROID_HOME ayarla (bu session icin)
    os.environ["ANDROID_HOME"] = SDK_DIR

if __name__ == "__main__":
    setup()

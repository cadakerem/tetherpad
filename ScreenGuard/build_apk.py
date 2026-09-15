"""
ScreenGuard APK build script.
Android SDK build-tools olmadan derler — sadece aapt, dx, apksigner gerektirir.
Bunlar build-tools ZIP'inden standalone alınabilir.

Kullanim: python build_apk.py
"""
import os, sys, subprocess, shutil, zipfile, struct, urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR  = os.path.join(SCRIPT_DIR, "build")
OUT_APK    = os.path.join(SCRIPT_DIR, "ScreenGuard.apk")

# Build-tools yollarini bul (SDK kuruluysa)
def find_tool(name):
    # 1) PATH'te ara
    p = shutil.which(name)
    if p: return p
    # 2) Yaygın SDK konumları
    sdk_roots = [
        os.path.join(os.environ.get("LOCALAPPDATA",""), "Android", "Sdk"),
        os.path.join(os.environ.get("ANDROID_HOME",""), ""),
        r"C:\Android\Sdk",
        r"C:\Users\kbarb\AppData\Local\Android\Sdk",
    ]
    for sdk in sdk_roots:
        bt = os.path.join(sdk, "build-tools")
        if os.path.isdir(bt):
            versions = sorted(os.listdir(bt), reverse=True)
            for v in versions:
                t = os.path.join(bt, v, name + (".exe" if sys.platform=="win32" else ""))
                if os.path.isfile(t):
                    return t
    return None

def find_android_jar():
    sdk_roots = [
        os.path.join(os.environ.get("LOCALAPPDATA",""), "Android", "Sdk"),
        r"C:\Android\Sdk",
        r"C:\Users\kbarb\AppData\Local\Android\Sdk",
    ]
    for sdk in sdk_roots:
        pf = os.path.join(sdk, "platforms")
        if os.path.isdir(pf):
            for plat in sorted(os.listdir(pf), reverse=True):
                jar = os.path.join(pf, plat, "android.jar")
                if os.path.isfile(jar):
                    return jar
    return None

def run(cmd, **kw):
    print(f"$ {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        print(f"  ERROR (code {r.returncode})")
        sys.exit(1)
    return r

def build():
    aapt = find_tool("aapt")
    dx   = find_tool("dx")
    apksigner = find_tool("apksigner")
    android_jar = find_android_jar()

    if not aapt:
        print("[HATA] aapt bulunamadi. Android SDK build-tools kurun.")
        print("  Kurulum: https://developer.android.com/studio#command-line-tools-only")
        sys.exit(1)
    if not dx:
        print("[HATA] dx bulunamadi.")
        sys.exit(1)
    if not android_jar:
        print("[HATA] android.jar bulunamadi. SDK platforms klasorunu kontrol edin.")
        sys.exit(1)

    print(f"aapt: {aapt}")
    print(f"dx:   {dx}")
    print(f"jar:  {android_jar}")

    src_dir  = os.path.join(SCRIPT_DIR, "src")
    res_dir  = os.path.join(SCRIPT_DIR, "res")
    manifest = os.path.join(SCRIPT_DIR, "AndroidManifest.xml")
    gen_dir  = os.path.join(BUILD_DIR, "gen")
    cls_dir  = os.path.join(BUILD_DIR, "classes")
    dex_dir  = os.path.join(BUILD_DIR, "dex")
    tmp_apk  = os.path.join(BUILD_DIR, "unsigned.apk")

    for d in [BUILD_DIR, gen_dir, cls_dir, dex_dir]:
        os.makedirs(d, exist_ok=True)

    # 1) R.java uret
    print("\n[1] R.java olusturuluyor...")
    run([aapt, "package", "-f", "-m", "-S", res_dir, "-J", gen_dir,
         "-M", manifest, "-I", android_jar])

    # 2) Java derle
    print("\n[2] Java derleniyor...")
    java_files = []
    for root, _, files in os.walk(src_dir):
        for f in files:
            if f.endswith(".java"):
                java_files.append(os.path.join(root, f))
    for root, _, files in os.walk(gen_dir):
        for f in files:
            if f.endswith(".java"):
                java_files.append(os.path.join(root, f))

    run(["javac", "-source", "7", "-target", "7",
         "-classpath", android_jar,
         "-d", cls_dir] + java_files)

    # 3) DEX olustur
    print("\n[3] DEX olusturuluyor...")
    run([dx, "--dex", f"--output={os.path.join(dex_dir,'classes.dex')}", cls_dir])

    # 4) APK paketleme (resources + manifest)
    print("\n[4] APK paketleniyor...")
    run([aapt, "package", "-f", "-M", manifest, "-S", res_dir,
         "-I", android_jar, "-F", tmp_apk])

    # 5) DEX ekle
    print("\n[5] DEX ekleniyor...")
    with zipfile.ZipFile(tmp_apk, "a") as zf:
        zf.write(os.path.join(dex_dir, "classes.dex"), "classes.dex")

    # 6) Imzalama (debug keystore ile)
    print("\n[6] APK imzalaniyor (debug key)...")
    keystore = os.path.join(os.path.expanduser("~"), ".android", "debug.keystore")
    if not os.path.exists(keystore):
        # Debug keystore olustur
        run(["keytool", "-genkey", "-v", "-keystore", keystore,
             "-alias", "androiddebugkey", "-storepass", "android",
             "-keypass", "android", "-keyalg", "RSA", "-keysize", "2048",
             "-validity", "10000", "-dname",
             "CN=Android Debug,O=Android,C=US"])

    if apksigner:
        signed_apk = OUT_APK
        run([apksigner, "sign", "--ks", keystore,
             "--ks-pass", "pass:android",
             "--key-pass", "pass:android",
             "--ks-key-alias", "androiddebugkey",
             "--out", signed_apk, tmp_apk])
    else:
        # jarsigner fallback
        run(["jarsigner", "-verbose", "-sigalg", "SHA1withRSA",
             "-digestalg", "SHA1", "-keystore", keystore,
             "-storepass", "android", "-keypass", "android",
             tmp_apk, "androiddebugkey"])
        shutil.copy(tmp_apk, OUT_APK)

    print(f"\n✅ APK hazır: {OUT_APK}")
    print(f"   Boyut: {os.path.getsize(OUT_APK):,} bytes")
    print(f"\nYükle: adb install -r ScreenGuard.apk")
    print(f"Aç:    adb shell am start -n com.ps5bridge.screenguard/.MainActivity")

if __name__ == "__main__":
    build()

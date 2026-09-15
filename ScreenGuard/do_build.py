import os, subprocess, zipfile, shutil, sys

SCRIPT_DIR = r'C:\Users\kbarb\Documents\adb_project\ScreenGuard'
BUILD_DIR  = os.path.join(SCRIPT_DIR, 'build')
OUT_APK    = os.path.join(SCRIPT_DIR, '..', 'ScreenGuard.apk')

aapt = r'C:\Android\MiniSdk\build-tools28\android-9\aapt.exe'
dx   = r'C:\Android\MiniSdk\build-tools28\android-9\dx.bat'
ajar = r'C:\Android\MiniSdk\platform\android-9\android.jar'

src_dir  = os.path.join(SCRIPT_DIR, 'src')
res_dir  = os.path.join(SCRIPT_DIR, 'res')
manifest = os.path.join(SCRIPT_DIR, 'AndroidManifest.xml')
gen_dir  = os.path.join(BUILD_DIR, 'gen')
cls_dir  = os.path.join(BUILD_DIR, 'classes')
dex_dir  = os.path.join(BUILD_DIR, 'dex')
dex_file = os.path.join(dex_dir, 'classes.dex')
tmp_apk  = os.path.join(BUILD_DIR, 'unsigned.apk')

for d in [BUILD_DIR, gen_dir, cls_dir, dex_dir]:
    os.makedirs(d, exist_ok=True)

# Find Portable JDK
jdk_dir = r"C:\Android\jdk"
javac_exe = "javac"
jarsigner_exe = "jarsigner"
keytool_exe = "keytool"

if os.path.exists(jdk_dir):
    for root, dirs, files in os.walk(jdk_dir):
        if "javac.exe" in files:
            javac_exe = os.path.join(root, "javac.exe")
        if "jarsigner.exe" in files:
            jarsigner_exe = os.path.join(root, "jarsigner.exe")
        if "keytool.exe" in files:
            keytool_exe = os.path.join(root, "keytool.exe")

def run(cmd, label=''):
    print(f'[{label}]', ' '.join(str(c) for c in cmd[:4]))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print('STDOUT:', r.stdout[:800])
        print('STDERR:', r.stderr[:800])
        sys.exit(1)
    return r

# 1) R.java
print('Step 1: R.java...')
run([aapt, 'package', '-f', '-m', '-S', res_dir, '-J', gen_dir, '-M', manifest, '-I', ajar], 'aapt')

# 2) javac
print('Step 2: javac...')
java_files = []
for root, _, files in os.walk(src_dir):
    for f in files:
        if f.endswith('.java'):
            java_files.append(os.path.join(root, f))
for root, _, files in os.walk(gen_dir):
    for f in files:
        if f.endswith('.java'):
            java_files.append(os.path.join(root, f))
print(f'  {len(java_files)} java files')
run([javac_exe, '-encoding', 'UTF-8', '-source', '7', '-target', '7', '-classpath', ajar, '-d', cls_dir] + java_files, 'javac')

dx_jar = r'C:\Android\MiniSdk\build-tools28\android-9\lib\dx.jar'

# 3) dx
print('Step 3: dx...')
run([os.path.join(jdk_dir, 'jdk-11.0.23+9', 'bin', 'java.exe'), '-jar', dx_jar, '--dex', '--output=' + dex_file, cls_dir], 'dx')

# 4) aapt package
print('Step 4: package resources...')
run([aapt, 'package', '-f', '-M', manifest, '-S', res_dir, '-I', ajar, '-F', tmp_apk], 'aapt-pkg')

# 5) add dex to apk
print('Step 5: add dex...')
with zipfile.ZipFile(tmp_apk, 'a') as zf:
    zf.write(dex_file, 'classes.dex')

# 6) sign with debug keystore
print('Step 6: sign...')
keystore = os.path.join(os.path.expanduser('~'), '.android', 'debug.keystore')
if not os.path.exists(keystore):
    os.makedirs(os.path.dirname(keystore), exist_ok=True)
    subprocess.run([
        keytool_exe, '-genkey', '-v', '-keystore', keystore,
        '-alias', 'androiddebugkey', '-storepass', 'android',
        '-keypass', 'android', '-keyalg', 'RSA', '-keysize', '2048',
        '-validity', '10000', '-dname', 'CN=Android Debug,O=Android,C=US'
    ], check=True)

out = os.path.abspath(OUT_APK)
subprocess.run([
    jarsigner_exe, '-verbose', '-sigalg', 'SHA1withRSA', '-digestalg', 'SHA1',
    '-keystore', keystore, '-storepass', 'android', '-keypass', 'android',
    '-signedjar', out, tmp_apk, 'androiddebugkey'
], check=True, capture_output=True)

print(f'APK hazir: {out}')
print(f'Boyut: {os.path.getsize(out):,} bytes')
print()
print('Yukle:')
print(f'  adb install -r ScreenGuard.apk')
print('Ac:')
print(f'  adb shell am start -n com.ps5bridge.screenguard/.MainActivity')

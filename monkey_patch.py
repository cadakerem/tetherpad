import os

with open('tetherpad.py', 'r', encoding='utf-8') as f:
    code = f.read()

old_patch = '''if os.name == "nt":
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0'''
code = code.replace(old_patch, '')

new_patch = '''if os.name == "nt":
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
    CREATE_NO_WINDOW = 0'''

code = code.replace('import subprocess', 'import subprocess\n\n' + new_patch)

with open('tetherpad.py', 'w', encoding='utf-8') as f:
    f.write(code)

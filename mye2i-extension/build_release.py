# Builds the release files for the MyE2i extension:
#   mye2iv3-latest.zip   unpacked folder (mye2iv3/) for "Load unpacked"; this is
#                        what UPDATE_URL in scripts/mye2iserver.py points to
#   mye2iv3-latest.crx   signed package, only if a browser and --pem are given
#                        (Chrome/Edge do not install it outside policies or
#                        developer mode, kept for policy-based installs)
# Usage: python build_release.py [--pem path/to/mye2i-extension.pem] [--out dir]
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = {'build_release.py', '__pycache__'}
BROWSERS = (
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    '/usr/bin/microsoft-edge',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
)


def copy_tree(dst):
    for name in os.listdir(HERE):
        if name in SKIP or name.endswith(('.zip', '.crx')):
            continue
        src = os.path.join(HERE, name)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(dst, name), ignore=shutil.ignore_patterns('__pycache__'))
        else:
            shutil.copy2(src, os.path.join(dst, name))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pem')
    ap.add_argument('--out', default=os.path.join(HERE, 'dist'))
    args = ap.parse_args()

    with open(os.path.join(HERE, 'manifest.json'), encoding='utf-8') as f:
        version = json.load(f)['version']
    os.makedirs(args.out, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        build = os.path.join(tmp, 'mye2iv3')
        os.makedirs(build)
        copy_tree(build)

        zip_path = os.path.join(args.out, 'mye2iv3-latest.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for root, _dirs, files in os.walk(build):
                for name in sorted(files):
                    full = os.path.join(root, name)
                    z.write(full, os.path.join('mye2iv3', os.path.relpath(full, build)))
        print('zip: %s (v%s)' % (zip_path, version))

        if args.pem:
            browser = next((b for b in BROWSERS if os.path.exists(b)), None)
            if not browser:
                sys.exit('no Chrome/Edge found for the .crx step')
            subprocess.run([browser, '--pack-extension=' + build, '--pack-extension-key=' + os.path.abspath(args.pem)], check=True)
            crx = build + '.crx'
            if not os.path.exists(crx):
                sys.exit('browser did not produce a .crx')
            crx_path = os.path.join(args.out, 'mye2iv3-latest.crx')
            shutil.copy2(crx, crx_path)
            print('crx: %s' % crx_path)


if __name__ == '__main__':
    main()

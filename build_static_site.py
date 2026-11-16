"""
Assemble a folder that can be dropped on any static host: no Python, no API.

    python3 build_static_site.py          -> writes ./site/

Layout:

    site/
    ├── index.html            SANS monitor (reads sans-static.js, demo mode)
    ├── app.js  style.css  sans-static.js  learn.html
    └── anatomy-explorer/     Unity build, untouched
        ├── index.html
        ├── immune.html       blood and immune monitor
        ├── immune-data.js
        ├── Build/  TemplateData/  StreamingAssets/

`sans-static.js` and `immune-data.js` are regenerated first, so the folder is
never assembled from stale data.

What the static copy cannot do
    Anything that writes: recording a measurement, editing the baseline,
    deleting a row, saving settings, adding a countermeasure. Those exist only
    when sans_web.py is running locally.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = ROOT / 'site'
WEB = ROOT / 'web'
ANATOMY = ROOT / 'anatomy-explorer'

WEB_FILES = ['index.html', 'learn.html', 'app.js', 'style.css', 'sans-static.js']


def run(script: str) -> None:
    print(f'  running {script}')
    result = subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT,
                            capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f'{script} failed')


def main() -> None:
    print('Regenerating data bundles')
    run('export_sans_static.py')
    run('export_demo_data.py')
    run('export_cardio_data.py')

    missing = [f for f in WEB_FILES if not (WEB / f).is_file()]
    if missing:
        raise SystemExit(f'missing from web/: {missing}')

    print(f'Assembling {SITE}')
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()

    for name in WEB_FILES:
        shutil.copy2(WEB / name, SITE / name)

    # The Unity page and the monitor it opens.
    shutil.copytree(ANATOMY, SITE / 'anatomy-explorer')

    total = sum(p.stat().st_size for p in SITE.rglob('*') if p.is_file())
    count = sum(1 for p in SITE.rglob('*') if p.is_file())
    print(f'Done: {count} files, {total / 1024 / 1024:.1f} MB')
    print('Test it with:  python3 -m http.server 8080 --directory site')
    print('Deploy: upload the contents of site/ to the web root.')


if __name__ == '__main__':
    main()

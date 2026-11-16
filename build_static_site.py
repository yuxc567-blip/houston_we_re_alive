"""
Assemble a folder that can be dropped on any static host: no Python, no API.

    python3 build_static_site.py          -> writes ./site/

Layout:

    site/index.html         opens the anatomy explorer
    site/anatomy/           Unity browser export
    site/eye/web/           SANS monitor, countermeasure guide and static data
    site/immune/web/        blood/immune monitor and existing demo bundle
    site/cardio/web/        heart and circulation monitor

SANS data is regenerated. The committed immune demo bundle is reused unless
--refresh-immune is passed (requires the optional NASA CBC dataset).

What the static copy cannot do
    Anything that writes: recording a measurement, editing the baseline,
    deleting a row, saving settings, adding a countermeasure. Those exist only
    when sans_web.py is running locally.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = ROOT / 'site'
WEB = ROOT / 'eye' / 'web'
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh-immune', action='store_true', help='Regenerate immune data; requires the optional NASA CBC dataset.')
    args = parser.parse_args()
    print('Preparing data bundles')
    run('export_sans_static.py')
    if args.refresh_immune:
        run('export_demo_data.py')
    else:
        print('  keeping the committed immune demo bundle (use --refresh-immune to regenerate)')

    missing = [f for f in WEB_FILES if not (WEB / f).is_file()]
    if missing:
        raise SystemExit(f'missing from eye/web/: {missing}')

    print(f'Assembling {SITE}')
    if SITE.exists():
        if SITE.resolve() != ROOT.resolve() / 'site':
            raise RuntimeError('Unexpected build destination')
        shutil.rmtree(SITE)
    SITE.mkdir()

    eye = SITE / 'eye' / 'web'
    eye.mkdir(parents=True)
    for name in WEB_FILES:
        shutil.copy2(WEB / name, eye / name)
    shutil.copytree(ROOT / 'immune' / 'web', SITE / 'immune' / 'web')
    shutil.copytree(ROOT / 'cardio' / 'web', SITE / 'cardio' / 'web')
    (SITE / 'index.html').write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=anatomy/"><title>Mission health explorer</title><a href="anatomy/">Open anatomy explorer</a>', encoding='utf-8')

    # The Unity page and the monitor it opens.
    shutil.copytree(ANATOMY, SITE / 'anatomy')

    total = sum(p.stat().st_size for p in SITE.rglob('*') if p.is_file())
    count = sum(1 for p in SITE.rglob('*') if p.is_file())
    print(f'Done: {count} files, {total / 1024 / 1024:.1f} MB')
    print('Test it with:  python3 -m http.server 8080 --directory site')
    print('Deploy: upload the contents of site/ to the web root.')


if __name__ == '__main__':
    main()

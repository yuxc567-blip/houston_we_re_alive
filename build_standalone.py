"""
Build one self-contained HTML file for the site root.

Porkbun keeps serving its placeholder until an index.html exists at the web
root. Everything else is already uploaded under /web/ and
/anatomy-explorer/, so the fastest way to replace the placeholder is to
upload a single file.

This inlines the stylesheet and both scripts into one document, and rewrites
the links so they point at the folders that are already on the server.

    python3 build_standalone.py     -> writes site-swap/index.html
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB = ROOT / 'web'
OUT = ROOT / 'site-swap'


def main() -> None:
    html = (WEB / 'index.html').read_text(encoding='utf-8')
    css = (WEB / 'style.css').read_text(encoding='utf-8')
    data = (WEB / 'sans-static.js').read_text(encoding='utf-8')
    app = (WEB / 'app.js').read_text(encoding='utf-8')

    html = html.replace('<link rel="stylesheet" href="style.css">',
                        f'<style>\n{css}\n</style>', 1)
    html = html.replace('<script src="sans-static.js"></script>',
                        f'<script>\n{data}\n</script>', 1)
    html = html.replace('<script src="app.js"></script>',
                        f'<script>\n{app}\n</script>', 1)

    # The guide and the anatomy build already live in their own folders.
    html = html.replace('href="learn.html', 'href="/web/learn.html')
    html = html.replace('href="../anatomy-explorer/"', 'href="/anatomy-explorer/"')
    html = html.replace('<script src="/sans-static.js"></script>', '')
    html = html.replace('<script src="/app.js"></script>', '')

    if re.search(r'src="(app|sans-static)\.js"|href="style\.css"', html):
        raise SystemExit('an external reference survived inlining')

    OUT.mkdir(exist_ok=True)
    target = OUT / 'index.html'
    target.write_text(html, encoding='utf-8')
    print(f'wrote {target}  ({target.stat().st_size / 1024:.1f} KB)')
    print('Upload this single file to the web root, replacing nothing.')


if __name__ == '__main__':
    main()

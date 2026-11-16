import json
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import urlopen

from eye.server import make_handler

ROOT = Path(__file__).resolve().parents[1]

class FeatureRoutesTests(unittest.TestCase):
    def serve(self, handler):
        server = HTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return "http://127.0.0.1:" + str(server.server_port)

    def read(self, url):
        with urlopen(url, timeout=5) as response:
            return response.read().decode("utf-8")

    def test_live_feature_routes_and_legacy_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            handler = make_handler(Path(temp) / "mission.json")
            handler.log_message = lambda *args: None
            base = self.serve(handler)
            self.assertIn("SANS", self.read(base + "/eye/web/index.html"))
            self.assertIn("Countermeasures", self.read(base + "/eye/web/learn.html"))
            self.assertEqual(self.read(base + "/eye/web/sans-static.js"), "window.SANS_STATIC = null;")
            self.assertIn("ENGINE_DATA", self.read(base + "/immune/web/immune-data.js"))
            self.assertIn("SANS", self.read(base + "/"))
            self.assertIn("eyes", json.loads(self.read(base + "/api/data")))
            with self.assertRaises(HTTPError) as error:
                self.read(base + "/eye/web/../../sans.py")
            self.assertEqual(error.exception.code, 403)
            error.exception.close()

    def test_relative_links_on_live_server_and_hosted_subdirectory(self):
        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self, *args): pass
        base = self.serve(partial(Quiet, directory=str(ROOT)))
        for prefix in ("/anatomy-explorer/", "/site/anatomy/"):
            anatomy = base + prefix + "index.html"
            page = self.read(anatomy)
            for target in ("../eye/web/index.html", "../immune/web/index.html"):
                self.assertIn(target, page)
                self.assertIn("<!doctype html", self.read(urljoin(anatomy, target)).lower())
            eye = urljoin(anatomy, "../eye/web/index.html")
            for asset in ("app.js", "style.css", "sans-static.js", "learn.html"):
                self.assertTrue(self.read(urljoin(eye, asset)))
            self.assertIn("window.SANS_STATIC", self.read(urljoin(eye, "sans-static.js")))

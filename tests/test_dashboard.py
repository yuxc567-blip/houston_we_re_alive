from http.server import HTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from sleep.dashboard import load_data, make_handler


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "journal.json"
        handler = make_handler(self.path)
        handler.log_message = lambda *args: None
        self.server = HTTPServer(("127.0.0.1", 0), handler)
        self.addCleanup(self.server.server_close)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def request(self, route, body=None, origin=None):
        request = Request(self.base + route, data=None if body is None else json.dumps(body).encode(), headers={"Content-Type": "application/json", **({"Origin":origin} if origin else {})})
        try:
            with urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            with error:
                return error.code, json.loads(error.read())

    def test_sleep_persistence_historical_entry_and_duplicate_rejection(self):
        self.assertEqual(self.request("/api/state")[1]["data"]["sleep"], [])
        for day, hours in [(3,7),(1,8),(2,6)]:
            status, result = self.request("/api/sleep", {"day":day,"hours":hours,"baseline_hours":8})
            self.assertEqual(status,200)
        rows = result["sleep_analysis"]["records"]
        self.assertEqual([r["mission_day"] for r in rows],[1,2,3])
        self.assertAlmostEqual(rows[-1]["accumulated_relative_error_days"],.3125)
        original = self.path.read_bytes()
        for body in [{"day":2,"hours":8},{"day":4,"hours":25},{"day":4,"hours":7,"baseline_hours":9},{"day":True,"hours":7},{"day":4,"hours":float("nan")}]:
            self.assertEqual(self.request("/api/sleep",body)[0],400)
            self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(load_data(self.path),result["data"])

    def test_measured_trials_baseline_and_time_based_reaction_analysis(self):
        body={"mode":"session","day":1,"trials_ms":[300]*5}
        self.assertEqual(self.request("/api/reaction",body)[0],400)
        status,result=self.request("/api/reaction",{"mode":"baseline","trials_ms":[240,250,260,250,250]})
        self.assertEqual(status,200)
        self.assertEqual(result["data"]["reaction_baseline"]["mean_ms"],250)
        for day, value in [(1,250),(3,300)]:
            status,result=self.request("/api/reaction",{"mode":"session","day":day,"trials_ms":[value]*5,"early_clicks":1,"timeouts":0})
            self.assertEqual(status,200)
        self.assertAlmostEqual(result["reaction_analysis"][-1]["error_rate"],.1)
        self.assertEqual(self.request("/api/reaction",{"mode":"baseline","trials_ms":[200]*5})[0],400)
        for values in [[200]*4,[0]*5,[6000]*5,[float("inf")]*5]:
            self.assertEqual(self.request("/api/reaction",{"mode":"session","day":4,"trials_ms":values})[0],400)
        self.assertEqual(self.request("/api/export")[1],result)
        self.assertEqual(load_data(self.path),result["data"])

    def test_local_assets_and_cross_origin_rejection(self):
        for path, mime in [("/","text/html"),("/app.js","application/javascript"),("/style.css","text/css")]:
            with urlopen(self.base+path,timeout=5) as response:
                self.assertEqual(response.status,200)
                self.assertIn(mime,response.headers["Content-Type"])
                self.assertTrue(response.read())
        self.assertEqual(self.request("/api/sleep",{"day":1,"hours":8},origin="https://example.com")[0],403)
        self.assertFalse(self.path.exists())
        self.assertEqual(self.request("/../reactiontime.py")[0],404)

    def test_invalid_saved_file_is_not_overwritten(self):
        self.path.write_text('not json')
        with self.assertRaises(ValueError): make_handler(self.path)
        self.assertEqual(self.path.read_text(),'not json')

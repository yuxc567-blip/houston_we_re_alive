import io
import json
from pathlib import Path
import tempfile
import unittest

import interventions
import sans
import sans_web


class CountermeasureTests(unittest.TestCase):
    def test_pairing_and_other_sessions(self):
        data = sans.demo_data()
        data['interventions'] = interventions.demo_records()
        result = sans_web.payload(data, {})['interventions']
        lbnp = next(r for r in result if r['kind'] == 'LBNP')
        r = lbnp['responses']['R']
        self.assertEqual((r['before']['flight_day'], r['after']['flight_day']), (70, 80))
        self.assertEqual(r['change_um'], -2)
        self.assertEqual(r['other_intervention_ids'], ['demo-vtc'])
        self.assertEqual(r['after']['threshold_status'], sans.Status.EXCEEDED.value)

    def test_missing_baseline_and_same_day(self):
        data = sans.new_data()
        for day, value in [(5, 400), (10, 420), (15, 410)]:
            sans.add_record(data, 'R', day, value)
        data['interventions'] = [interventions.normalize(dict(kind='VTC', status='Completed', start_day=10, end_day=10))]
        r = sans_web.payload(data, {})['interventions'][0]['responses']
        self.assertEqual(r['R']['change_um'], 10)
        self.assertIsNone(r['R']['after']['delta_trt_um'])
        self.assertIsNone(r['L']['change_um'])
        data['interventions'][0]['status'] = 'Skipped'
        self.assertIsNone(sans_web.payload(data, {})['interventions'][0]['responses']['R']['change_um'])

    def test_validation(self):
        good = dict(kind='Medication', name='Recorded medicine', status='Completed', start_day=10, end_day=11)
        for changes in [dict(start_day=float('nan')), dict(end_day=9), dict(name=''), dict(duration_minutes=-1), dict(kind='invalid')]:
            with self.assertRaises(ValueError):
                interventions.normalize(dict(good, **changes))

    def test_api_roundtrip_edit_delete_and_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'data.json'
            def caller():
                Handler = sans_web.make_handler(path)
                def call(route, body=None):
                    h = object.__new__(Handler)
                    h.path = route
                    encoded = json.dumps(body).encode()
                    h.headers = {'Content-Length': str(len(encoded)), 'Host': 'localhost:8000'}
                    h.rfile = io.BytesIO(encoded)
                    result = []
                    h.send = lambda status, data, content_type=None: result.append((status, data))
                    (h.do_GET if body is None else h.do_POST)()
                    return result[0]
                return call
            call = caller()
            self.assertEqual(call('/api/data')[1]['interventions'], [])
            self.assertEqual(call('/api/baseline', dict(R=400, quality=True))[0], 200)
            self.assertEqual(call('/api/baseline', dict(R=405, quality=True))[0], 400)
            good = dict(kind='LBNP', status='Completed', start_day=75, end_day=75, details='Recorded parameter')
            status, data = call('/api/intervention', good)
            self.assertEqual(status, 200)
            saved_id = data['interventions'][0]['id']
            self.assertEqual(caller()('/api/data')[1]['interventions'][0]['id'], saved_id)
            self.assertEqual(call('/api/intervention', dict(good, id=saved_id, notes='Updated'))[0], 200)
            before = path.read_bytes()
            self.assertEqual(call('/api/intervention', dict(good, end_day=1))[0], 400)
            self.assertEqual(path.read_bytes(), before)
            call('/api/demo')
            self.assertEqual(path.read_bytes(), before)
            export = call('/api/export-linked')[1]
            self.assertEqual(export['raw_records']['interventions'][0]['notes'], 'Updated')
            self.assertTrue(path.with_suffix('.json.bak').exists())
            self.assertEqual(call('/api/intervention-delete', {'id':saved_id})[0], 200)
            self.assertEqual(caller()('/api/data')[1]['interventions'], [])


if __name__ == '__main__':
    unittest.main()

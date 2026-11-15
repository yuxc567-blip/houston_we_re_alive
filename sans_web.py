"""Local English web interface for sans.py. Run: python3 sans_web.py."""
import argparse
import copy
import csv
import io
import json
import math
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

import sans
import interventions

ROOT = Path(__file__).resolve().parent


def positive(value, label, zero=False):
    if isinstance(value, bool):
        raise ValueError(f'{label} must be a finite number.')
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise ValueError(f'{label} must be a number.') from None
    if not math.isfinite(result) or (result < 0 if zero else result <= 0):
        raise ValueError(f'{label} must be finite and {"zero or greater" if zero else "greater than zero"}.')
    return result


def payload(data, settings):
    eyes = {eye: {'baseline': data['eyes'][eye]['baseline'],
                  'results': sans.analyze(data, eye, **settings)} for eye in sans.EYES}
    return {'eyes': eyes, 'settings': settings,
            'interventions': interventions.comparisons(data.get('interventions', []), eyes)}


def make_handler(path):
    data = sans.load_data(path)
    interventions.validate(data)
    settings = {'rate_review_threshold': None, 'prediction_days': None}

    class Handler(BaseHTTPRequestHandler):
        def send(self, status, body, content_type='application/json; charset=utf-8'):
            if not isinstance(body, bytes):
                body = json.dumps(body, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            route = urlparse(self.path).path
            if route == '/api/data':
                return self.send(200, payload(data, settings))
            if route == '/api/demo':
                demo = sans.demo_data()
                demo['interventions'] = interventions.demo_records()
                return self.send(200, payload(demo, settings))
            if route == '/api/export-linked':
                return self.send(200, {'raw_records': data, 'analysis': payload(data, settings),
                                       'pairing': 'Latest scan strictly before start day; first scan strictly after end day. Same-day scans excluded.'})
            if route == '/api/export':
                rows = [dict(eye=eye, **r) for eye in sans.EYES for r in sans.analyze(data, eye, **settings)]
                stream = io.StringIO()
                if rows:
                    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
                return self.send(200, stream.getvalue().encode('utf-8-sig'), 'text/csv; charset=utf-8')
            files = {'/': ('index.html', 'text/html'), '/learn': ('learn.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'),
                     '/style.css': ('style.css', 'text/css')}
            if route in files:
                name, mime = files[route]
                return self.send(200, (ROOT / 'web' / name).read_bytes(), mime + '; charset=utf-8')
            self.send(404, {'error': 'Not found.'})

        def do_POST(self):
            nonlocal data, settings
            # Only same-origin browser requests may mutate local records.
            if self.headers.get('Origin') not in (None, 'http://' + self.headers.get('Host', '')):
                return self.send(403, {'error': 'Cross-origin requests are not allowed.'})
            try:
                length = int(self.headers.get('Content-Length', 0))
                if not 0 < length <= 16384:
                    raise ValueError('Invalid request size.')
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError('Request must be a JSON object.')
                route = urlparse(self.path).path
                if route == '/api/settings':
                    settings = {key: None if body.get(key) in (None, '') else positive(body[key], key.replace('_', ' '))
                                for key in settings}
                elif route in ('/api/baseline', '/api/record', '/api/delete', '/api/intervention', '/api/intervention-delete'):
                    candidate = copy.deepcopy(data)
                    if route == '/api/intervention':
                        records = candidate.setdefault('interventions', [])
                        existing_id = body.get('id')
                        if existing_id:
                            match = next((i for i, r in enumerate(records) if r['id'] == existing_id), None)
                            if match is None:
                                raise ValueError('Countermeasure record not found.')
                            records[match] = interventions.normalize(body, existing_id)
                        else:
                            records.append(interventions.normalize(body))
                    elif route == '/api/intervention-delete':
                        records = candidate.get('interventions', [])
                        if not any(r['id'] == body.get('id') for r in records):
                            raise ValueError('Countermeasure record not found.')
                        candidate['interventions'] = [r for r in records if r['id'] != body.get('id')]
                    elif route == '/api/baseline':
                        if body.get('quality') is not True:
                            raise ValueError('Please confirm measurement quality.')
                        if all(body.get(e) in (None, '') for e in sans.EYES):
                            raise ValueError('Enter a baseline for at least one eye.')
                        for eye in sans.EYES:
                            if body.get(eye) not in (None, ''):
                                if candidate['eyes'][eye]['baseline'] is not None:
                                    raise ValueError('An established baseline cannot be changed.')
                                candidate['eyes'][eye]['baseline'] = positive(body[eye], f'{eye} baseline')
                    elif route == '/api/record':
                        day = positive(body.get('day'), 'Flight day', zero=True)
                        if body.get('quality') is not True:
                            raise ValueError('Please confirm measurement quality.')
                        if all(body.get(e) in (None, '') for e in sans.EYES):
                            raise ValueError('Enter a TRT measurement for at least one eye.')
                        for eye in sans.EYES:
                            if body.get(eye) not in (None, ''):
                                value = positive(body[eye], f'{eye} TRT')
                                if any(r['flight_day'] == day for r in candidate['eyes'][eye]['records']):
                                    raise ValueError(f'{eye} eye already has a measurement on flight day {day:g}. Delete it before correcting it.')
                                sans.add_record(candidate, eye, day, value)
                    else:
                        eye = body.get('eye')
                        if eye not in sans.EYES:
                            raise ValueError('Select a valid eye.')
                        day = positive(body.get('day'), 'Flight day', zero=True)
                        candidate['eyes'][eye]['records'] = [r for r in candidate['eyes'][eye]['records'] if r['flight_day'] != day]
                    interventions.validate(candidate)
                    sans.save_data(path, candidate)
                    data = candidate
                else:
                    return self.send(404, {'error': 'Not found.'})
                self.send(200, payload(data, settings))
            except (ValueError, TypeError, KeyError) as exc:
                message = str(exc)
                self.send(400, {'error': message if message.isascii() else 'Invalid measurement data. Check your values.'})
            except OSError:
                self.send(500, {'error': 'Could not save the data file. Please check file permissions.'})

    return Handler


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--data', type=Path, default=ROOT / 'sans_data.json')
    args = parser.parse_args()
    server = HTTPServer(('127.0.0.1', args.port), make_handler(args.data))
    print(f'SANS Monitor is ready at http://localhost:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

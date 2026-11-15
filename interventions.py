"""Recorded countermeasures and observed, per-eye before/after comparisons."""
import math
from uuid import uuid4

KINDS = ('LBNP', 'VTC', 'ITD', 'Medication', 'Supplement', 'Other')
STATUSES = ('Completed', 'Stopped early', 'Skipped')


def numeric(value, label, optional=False):
    if optional and value in (None, ''):
        return None
    if isinstance(value, bool):
        raise ValueError(f'{label} must be a number.')
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'{label} must be a number.') from None
    if not math.isfinite(value) or value < 0:
        raise ValueError(f'{label} must be finite and zero or greater.')
    return value


def short_text(value, label, limit=500):
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError(f'{label} must be text, at most {limit} characters.')
    return value.strip()


def normalize(body, record_id=None):
    kind, status = body.get('kind'), body.get('status')
    if kind not in KINDS or status not in STATUSES:
        raise ValueError('Select a countermeasure and completion status.')
    start = numeric(body.get('start_day'), 'Start flight day')
    end = numeric(body.get('end_day', start), 'End flight day')
    if end < start:
        raise ValueError('End flight day cannot be before start flight day.')
    name = short_text(body.get('name', ''), 'Name', 100)
    if kind in ('Medication', 'Supplement', 'Other') and not name:
        raise ValueError('Enter the name of the countermeasure.')
    duration = numeric(body.get('duration_minutes'), 'Duration', optional=True)
    if duration is not None and duration <= 0:
        raise ValueError('Duration must be greater than zero, or left blank.')
    return {'id': record_id or uuid4().hex, 'kind': kind, 'name': name,
            'start_day': start, 'end_day': end, 'duration_minutes': duration,
            'details': short_text(body.get('details', ''), 'Parameters / dose', 200),
            'status': status, 'notes': short_text(body.get('notes', ''), 'Notes')}


def validate(data):
    records = data.get('interventions', [])
    if not isinstance(records, list):
        raise ValueError('Invalid countermeasure records.')
    ids = set()
    for i, r in enumerate(records):
        if not isinstance(r, dict) or not isinstance(r.get('id'), str) or not r['id'] or r['id'] in ids:
            raise ValueError('Invalid or duplicate countermeasure ID.')
        records[i] = normalize(r, r['id'])
        ids.add(r['id'])


def comparisons(records, eyes):
    results = []
    for record in sorted(records, key=lambda r: r['start_day'], reverse=True):
        entry = dict(record, responses={})
        for eye, item in eyes.items():
            rows = item['results']
            before = [r for r in rows if r['flight_day'] < record['start_day']]
            after = [r for r in rows if r['flight_day'] > record['end_day']]
            pre, post = (before[-1] if before else None), (after[0] if after else None)
            if record['status'] == 'Skipped':
                pre = post = None
            change = post['current_trt_um'] - pre['current_trt_um'] if pre and post else None
            others = [r['id'] for r in records if r['id'] != record['id'] and r['status'] != 'Skipped'
                      and pre and post and r['start_day'] < post['flight_day'] and r['end_day'] > pre['flight_day']]
            entry['responses'][eye] = {'before': pre, 'after': post, 'change_um': change,
                                      'other_intervention_ids': others}
        results.append(entry)
    return results


def demo_records():
    return [normalize({'kind':'LBNP', 'status':'Completed', 'start_day':75, 'end_day':75,
                       'notes':'Fictional demo session.'}, 'demo-lbnp'),
            normalize({'kind':'VTC', 'status':'Completed', 'start_day':76, 'end_day':76,
                       'notes':'Fictional demo session in the same scan interval.'}, 'demo-vtc'),
            normalize({'kind':'ITD', 'status':'Stopped early', 'start_day':95, 'end_day':95,
                       'notes':'Fictional demo: discomfort recorded.'}, 'demo-itd')]

"""
Run the cardiovascular monitor over four fictional missions and export the
results for the web page.

All readings are invented. The reference trajectory is real: Balali et al.
(2025), 17 ISS cosmonauts, DOI 10.1038/s41526-025-00522-8, interpolated over
flight days 6-159. The engine refuses days outside that window.

    python -m cardio.export_cardio_data   -> cardio/web/cardio-data.js
"""
from __future__ import annotations

import json
import math
import random
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from . import cardiovascular as cv
except ImportError:      # run directly
    import cardiovascular as cv

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'web' / 'cardio-data.js'

LAUNCH = datetime(2026, 1, 1, tzinfo=timezone.utc)
BASELINE = {'heart_rate': 70.0, 'systolic_bp': 120.0, 'diastolic_bp': 80.0}
FIRST_DAY, LAST_DAY = 6, 159

ACTION_ORDER = ['CONTINUE_SCHEDULED_MONITORING', 'REPEAT_AND_CHECK_CONTEXT',
                'REPEAT_MEASUREMENT', 'MEDICAL_REVIEW', 'URGENT_ASSESSMENT']

LABELS = {
    'heart_rate': 'Heart rate',
    'systolic_bp': 'Systolic pressure',
    'diastolic_bp': 'Diastolic pressure',
}
UNITS = {'heart_rate': 'bpm', 'systolic_bp': 'mmHg', 'diastolic_bp': 'mmHg'}


def reference_value(indicator, day):
    return BASELINE[indicator] * cv.experimental_reference(indicator, day)['ratio_to_preflight']


def jitter(rng, pct):
    return 1.0 + rng.gauss(0, pct)


def case_specs():
    return [
        {
            'id': 'cv_normal',
            'label': 'Steady mission',
            'note': 'Readings track the modelled reference. Nothing should fire.',
            'readings': lambda day: {},
            'symptoms': lambda day: [],
        },
        {
            'id': 'cv_tachycardia',
            'label': 'Tachycardia episode around day 40',
            'note': 'Heart rate climbs well above the modelled reference, then settles.',
            'readings': lambda day: {
                'heart_rate': 1.0 + 0.42 * bump(day, 34, 42, 52)},
            'symptoms': lambda day: ['palpitations'] if bump(day, 34, 42, 52) > 0.35 else [],
        },
        {
            'id': 'cv_hypotension',
            'label': 'Blood pressure drop around day 60',
            'note': 'Both pressures fall together while heart rate rises a little.',
            'readings': lambda day: {
                'systolic_bp': 1.0 - 0.24 * bump(day, 54, 62, 74),
                'diastolic_bp': 1.0 - 0.22 * bump(day, 54, 62, 74),
                'heart_rate': 1.0 + 0.10 * bump(day, 54, 62, 74),
            },
            'symptoms': lambda day: ['dizziness'] if bump(day, 54, 62, 74) > 0.5 else [],
        },
        {
            'id': 'cv_emergency',
            'label': 'Chest pain reported on day 95',
            'note': 'A symptom that overrides every numeric comparison.',
            'readings': lambda day: {},
            'symptoms': lambda day: ['chest_pain'] if 95 <= day <= 96 else [],
        },
    ]


def bump(day, start, peak, end):
    if day <= start or day >= end:
        return 0.0
    if day <= peak:
        return (day - start) / max(1, peak - start)
    return (end - day) / max(1, end - peak)


def build_case(spec):
    rng = random.Random(zlib.crc32(spec['id'].encode()) & 0xFFFF)
    monitor = cv.CardiovascularMonitor(dict(BASELINE), LAUNCH)
    samples = []

    for day in range(FIRST_DAY, LAST_DAY + 1):
        ts = LAUNCH + timedelta(days=day)
        modifiers = spec['readings'](day)
        symptoms = spec['symptoms'](day)

        rows = []
        for indicator in cv.EXPERIMENTS:
            value = reference_value(indicator, day) * modifiers.get(indicator, 1.0) * jitter(rng, 0.012)
            out = monitor.process(indicator, ts, value, symptoms=symptoms)
            rows.append({
                'indicator': indicator,
                'label': LABELS[indicator],
                'unit': UNITS[indicator],
                'value': round(out['current_value'], 1),
                'baseline': round(out['personal_preflight_baseline'], 1),
                'reference': round(out['modeled_personal_reference'], 1),
                'personal_pct': round(out['personal_change_pct'], 1),
                'study_pct': round(out['experimental_change_pct'], 1),
                'difference_pp': round(out['difference_percentage_points'], 1),
                'status': out['demo_comparison_status'],
                'urgency': out['demo_urgency_level'],
                'action': out['guidance']['action'],
                'direction': out['guidance']['direction_from_reference'],
                'concerns': out['guidance']['possible_concerns'],
                'advice': out['guidance']['advice'],
            })

        worst = max(rows, key=lambda r: ACTION_ORDER.index(r['action']))
        samples.append({
            'day': day,
            'timestamp': ts.strftime('%Y-%m-%d'),
            'rows': rows,
            'action': worst['action'],
            'status': 'URGENT' if worst['action'] == 'URGENT_ASSESSMENT' else worst['status'],
            'symptoms': symptoms,
            'lead': worst['indicator'],
        })

    return {
        'id': spec['id'],
        'label': spec['label'],
        'note': spec['note'],
        'source': 'synthetic readings, published reference',
        'cadence_label': 'Daily checks (reference limited to days 6-159)',
        'baseline': dict(BASELINE),
        'samples': samples,
    }


def main():
    cases = [build_case(spec) for spec in case_specs()]
    payload = {
        'generated_from': 'cardiovascular.py',
        'reference': 'Balali et al. 2025, doi:10.1038/s41526-025-00522-8',
        'indicators': {k: {'label': LABELS[k], 'unit': UNITS[k]} for k in cv.EXPERIMENTS},
        'cases': cases,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text('window.CARDIO_DATA = '
                   + json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
                   + ';\n', encoding='utf-8')
    print(f'wrote {OUT}  ({OUT.stat().st_size / 1024:.1f} KB)')
    for c in cases:
        counts = {}
        for s in c['samples']:
            counts[s['action']] = counts.get(s['action'], 0) + 1
        print(f"  {c['label'][:44]:<46}{counts}")


if __name__ == '__main__':
    main()

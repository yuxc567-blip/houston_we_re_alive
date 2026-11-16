"""
Precompute the brain module's page data from the two analysis modules that
already exist in sleep/, so the page runs on a static host with no Python.

    sleep/sleep_duration.py  analyze_sleep()
    sleep/reactiontime.py    process_reaction_times()

Both are called once over a whole mission, so the cumulative columns in the
export are exactly the ones those functions produce; the page simply walks
the resulting records. Readings are invented; the models are not.

    python3 sleep/export_brain_data.py   -> sleep/web/brain-data.js
"""
from __future__ import annotations

import json
import random
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import reactiontime as rt          # noqa: E402
import sleep_duration as sd        # noqa: E402

OUT = HERE / 'web' / 'brain-data.js'

SLEEP_REFERENCE_HOURS = 8.0        # AASM adult consensus, stated in the page
RT_BASELINE_MS = 250.0             # fictional personal baseline
DAYS = 30

# Presentation bands only. Neither module defines a clinical threshold, and
# the page says so; these exist to colour the display.
BANDS = [(5.0, 'steady'), (15.0, 'notable'), (10 ** 9, 'marked')]
BAND_LABEL = {'steady': 'Steady', 'notable': 'Notable', 'marked': 'Marked'}
BAND_ORDER = ['steady', 'notable', 'marked']


def band(deviation_percent):
    magnitude = abs(deviation_percent)
    for limit, name in BANDS:
        if magnitude < limit:
            return name
    return 'marked'


def case_specs():
    return [
        {
            'id': 'brain_steady',
            'label': 'Steady rest and response',
            'note': 'Sleep holds near eight hours and reaction time stays flat.',
            'sleep': lambda d: 8.0 + 0.18 * ((d % 3) - 1),
            'rt': lambda d: RT_BASELINE_MS + 2.0 * ((d % 5) - 2),
        },
        {
            'id': 'brain_drift',
            'label': 'Sleep slipping, responses slowing',
            'note': 'Sleep falls about six minutes a night and reaction time follows.',
            'sleep': lambda d: 8.0 - 0.085 * d + 0.15 * ((d % 3) - 1),
            'rt': lambda d: RT_BASELINE_MS + 2.2 * d + 3.0 * ((d % 4) - 1.5),
        },
        {
            'id': 'brain_acuteloss',
            'label': 'Three rough nights around day 12',
            'note': 'Acute sleep loss, then recovery. Watch the cumulative line keep climbing.',
            'sleep': lambda d: (8.0 - 4.6 * bump(d, 10, 12, 15)) + 0.15 * ((d % 3) - 1),
            'rt': lambda d: RT_BASELINE_MS + 120.0 * bump(d, 10, 12.5, 17)
                            + 2.0 * ((d % 5) - 2),
        },
    ]


def bump(day, start, peak, end):
    if day <= start or day >= end:
        return 0.0
    if day <= peak:
        return (day - start) / max(1e-9, peak - start)
    return (end - day) / max(1e-9, end - peak)


def build_case(spec):
    rng = random.Random(zlib.crc32(spec['id'].encode()) & 0xFFFF)
    days = list(range(1, DAYS + 1))
    sleep_hours = [round(max(2.0, min(12.0, spec['sleep'](d) + rng.gauss(0, 0.12))), 1)
                   for d in days]
    reaction_ms = [round(max(120.0, spec['rt'](d) + rng.gauss(0, 6.0)), 0)
                   for d in days]

    sleep_analysis = sd.analyze_sleep(sleep_hours, days,
                                      baseline_hours=SLEEP_REFERENCE_HOURS)
    rt_rows = rt.process_reaction_times(days, reaction_ms, RT_BASELINE_MS)

    samples = []
    for sleep_row, rt_row in zip(sleep_analysis['records'], rt_rows):
        rows = [
            {
                'indicator': 'sleep',
                'label': 'Sleep per 24 h',
                'unit': 'h',
                'value': round(sleep_row['sleep_hours'], 1),
                'reference': SLEEP_REFERENCE_HOURS,
                'deviation': round(sleep_row['deviation_hours'], 2),
                'deviation_pct': round(sleep_row['deviation_percent'], 1),
                'cumulative': round(sleep_row['accumulated_relative_error_days'], 3),
                'rate': None if sleep_row['error_rate_per_day'] is None
                        else round(sleep_row['error_rate_per_day'] * 100, 2),
                'change': None if sleep_row['change_from_previous_hours'] is None
                          else round(sleep_row['change_from_previous_hours'], 1),
                'band': band(sleep_row['deviation_percent']),
            },
            {
                'indicator': 'reaction',
                'label': 'Reaction time',
                'unit': 'ms',
                'value': round(rt_row['reaction_time_ms'], 0),
                'reference': RT_BASELINE_MS,
                'deviation': round(rt_row['deviation'], 1),
                'deviation_pct': round(rt_row['deviation_percent'], 1),
                'cumulative': round(rt_row['accumulated_error'], 3),
                'rate': None if rt_row['error_rate'] is None
                        else round(rt_row['error_rate'] * 100, 2),
                'change': None if rt_row['change_from_previous_ms'] is None
                          else round(rt_row['change_from_previous_ms'], 0),
                'band': band(rt_row['deviation_percent']),
            },
        ]
        worst = max(rows, key=lambda r: BAND_ORDER.index(r['band']))
        samples.append({
            'day': sleep_row['mission_day'],
            'rows': rows,
            'band': worst['band'],
            'lead': worst['indicator'],
        })

    return {
        'id': spec['id'],
        'label': spec['label'],
        'note': spec['note'],
        'source': 'synthetic readings, published reference values',
        'cadence_label': 'Daily log, thirty days',
        'references': {'sleep_hours': SLEEP_REFERENCE_HOURS,
                       'reaction_ms': RT_BASELINE_MS},
        'samples': samples,
    }


def main():
    cases = [build_case(spec) for spec in case_specs()]
    payload = {
        'generated_from': ['sleep/sleep_duration.py', 'sleep/reactiontime.py'],
        'indicators': {
            'sleep': {'label': 'Sleep per 24 h', 'unit': 'h',
                      'reference': SLEEP_REFERENCE_HOURS},
            'reaction': {'label': 'Reaction time', 'unit': 'ms',
                         'reference': RT_BASELINE_MS},
        },
        'bands': {k: v for k, v in BAND_LABEL.items()},
        'cases': cases,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text('window.BRAIN_DATA = '
                   + json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
                   + ';\n', encoding='utf-8')
    print(f'wrote {OUT}  ({OUT.stat().st_size / 1024:.1f} KB)')
    for case in cases:
        counts = {}
        for s in case['samples']:
            counts[s['band']] = counts.get(s['band'], 0) + 1
        last = case['samples'][-1]['rows']
        print(f"  {case['label'][:42]:<44}{counts}")
        print(f"      day 30: sleep {last[0]['value']} h ({last[0]['deviation_pct']:+.1f}%), "
              f"reaction {last[1]['value']:.0f} ms ({last[1]['deviation_pct']:+.1f}%)")


if __name__ == '__main__':
    main()

"""Run the real OrbitCare controller and export its six outputs for the web demo.

The HTML page holds no analytics of its own: it renders `demo/data.js`, which is
produced here by `orbitcare_pid.py`. Regenerate after any change to the engine:

    python3 export_demo_data.py
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import orbitcare_pid as oc

BASE = datetime(2026, 1, 1, 12, 0)

# id, label, note, series of (baseline_value, total_delta), event days
SYNTHETIC = [
    {
        "id": "syn_hemolysis",
        "label": "Haemolysis over 30 days",
        "note": "Full panel present, so the haemolytic pattern can actually be tested.",
        "n": 30,
        "onset": 8,
        "series": {
            "hemoglobin": (14.2, -3.6), "hematocrit": (44.0, -9.0),
            "reticulocytes": (1.1, 2.8), "haptoglobin": (62.0, -46.0),
            "serum_iron": (92.0, 80.0), "wbc": (6.4, 0.3),
            "neutrophil_lymphocyte": (2.4, 0.2), "platelets": (240.0, -10.0),
            "crp": (1.2, 2.0), "total_protein": (7.1, 0.1),
            "mch": (30.0, -0.4), "rdw": (12.6, 0.6),
        },
        "events": [(6, "sleep debt onset"), (12, "EVA exercise load")],
        "symptoms": [(26, "coldSore")],
    },
    {
        "id": "syn_infection",
        "label": "Infection at day 12",
        "note": "Neutrophilia with a C-reactive protein rise. Tests infection against stress demargination.",
        "n": 30,
        "onset": 12,
        "bump": (12, 16, 26),   # rise, peak, resolve
        "series": {
            "hemoglobin": (14.0, -0.4), "hematocrit": (43.0, -1.0),
            "reticulocytes": (1.2, 0.1), "haptoglobin": (70.0, -6.0),
            "serum_iron": (95.0, -22.0), "wbc": (6.0, 5.5),
            "neutrophil_lymphocyte": (2.2, 2.8), "platelets": (245.0, -30.0),
            "crp": (1.0, 38.0), "total_protein": (7.0, -0.2),
            "mch": (30.0, 0.0), "rdw": (12.5, 0.1),
        },
        "events": [(10, "cabin humidity excursion")],
        "symptoms": [(14, "fever"), (15, "soreThroat")],
    },
    {
        "id": "syn_marrow",
        "label": "Marrow suppression",
        "note": "All lineages fall with no reticulocyte response. Tests production failure.",
        "n": 28,
        "onset": 10,
        "series": {
            "hemoglobin": (14.4, -3.0), "hematocrit": (44.0, -8.0),
            "reticulocytes": (1.3, -0.9), "haptoglobin": (65.0, 2.0),
            "serum_iron": (90.0, 10.0), "wbc": (6.2, -3.4),
            "neutrophil_lymphocyte": (2.3, -0.4), "platelets": (250.0, -140.0),
            "crp": (1.1, 1.5), "total_protein": (7.1, 0.0),
            "mch": (30.0, 0.2), "rdw": (12.4, 0.3),
        },
        "events": [(8, "solar particle event")],
        "symptoms": [],
    },
    {
        "id": "syn_concentration",
        "label": "Haemoconcentration (dehydration)",
        "note": "Haematocrit and total protein rise together while haemoglobin falls.",
        "n": 30,
        "onset": 6,
        "bump": (6, 12, 24),
        "series": {
            "hemoglobin": (14.6, -1.2), "hematocrit": (44.0, 7.0),
            "reticulocytes": (1.2, -0.1), "haptoglobin": (66.0, 1.0),
            "serum_iron": (94.0, 6.0), "wbc": (6.3, 0.4),
            "neutrophil_lymphocyte": (2.4, 0.1), "platelets": (245.0, 8.0),
            "crp": (1.1, 0.3), "total_protein": (7.0, 1.3),
            "mch": (30.0, 0.0), "rdw": (12.5, 0.0),
        },
        "events": [(4, "cabin humidity drop"), (5, "reduced fluid intake")],
        "symptoms": [],
    },
]


def jsonable(obj):
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%d")
    if isinstance(obj, dict):
        return {k: jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, float):
        return round(obj, 4)
    return obj


KEEP_FIELDS = ("analyte", "label", "value", "unit", "std", "rcv", "deviation_pct",
               "error_rcv", "rail", "implausible", "drift", "drift_run", "escalate")


def slim(results):
    return [{k: r[k] for k in KEEP_FIELDS if k in r} for r in results]


def phase_of(day: int) -> str:
    return "pre" if day < 0 else "mission"


def render_sample(panel, ts, readings, crew, six=True, day=None):
    results = panel.process(ts, readings)
    summary = panel.summarise(results)
    sample = {
        "timestamp": ts.strftime("%Y-%m-%d"),
        "day": day,
        "phase": phase_of(day) if day is not None else "mission",
        "status": summary["status"],
        "summary": jsonable(summary),
        "results": slim(results),
        "outputs": None,
    }
    # a normal sample carries no handover package: it would be 40 lines of
    # "maintain cadence" repeated 100 times
    if six and results and summary["status"] != "NORMAL":
        sample["outputs"] = jsonable(
            panel.outputs(results, summary, crew=crew)
        )
    return sample


def build_real(rows):
    by_crew = {}
    for r in rows:
        by_crew.setdefault(r["crew"], []).append(r)

    cases = []
    for crew, crew_rows in sorted(by_crew.items()):
        crew_rows.sort(key=lambda r: oc.DEMO_DAYS[r["timepoint"]])
        pre = [r for r in crew_rows if r["timepoint"] in ("L-92", "L-44")]
        if not pre:
            continue
        baseline = {}
        for key in ("hemoglobin", "hematocrit", "wbc", "platelets", "rdw", "mch"):
            vals = sorted(
                r[key] for r in pre
                if r[key] == r[key] and r[key] > 0
                and oc.implausible_reason(key, r[key]) is None
            )
            if vals:
                import statistics
                baseline[key] = statistics.median(vals)

        panel = oc.Panel(baseline, horizon="long")
        samples = []
        for r in crew_rows:
            ts = oc.demo_timestamp(r["timepoint"])
            readings = {k: r[k] for k in baseline}
            samples.append(render_sample(panel, ts, readings, crew,
                                         day=oc.DEMO_DAYS[r["timepoint"]]))

        # keep every sample: the page steps through them one click at a time
        cases.append({
            "id": "real_" + crew,
            "label": f"{crew} — real Inspiration4 complete blood count",
            "crew": crew,
            "source": "real",
            "cadence": "research",
            "cadence_label": "research sampling · irregular",
            "note": "NASA OSDR OSD-569. Complete blood count only, so patterns that "
                    "need reticulocytes, haptoglobin, iron or C-reactive protein are "
                    "reported as blocked.",
            "baseline": {k: round(v, 3) for k, v in baseline.items()},
            "samples": samples,
            "series": [
                {"timestamp": s["timestamp"], "status": s["status"],
                 "max_error_rcv": s["summary"]["max_error_rcv"]}
                for s in samples
            ],
        })
    return cases


PRE_FLIGHT_DAYS = 7


def profile(day: int, onset: int, bump=None) -> float:
    """0 -> 1 ramp from onset, or a rise/peak/resolve triangle when bump is set."""
    if bump is None:
        return max(0.0, (day - onset) / 1.0) if day >= onset else 0.0
    start, peak, end = bump
    if day <= start or day >= end:
        return 0.0
    if day <= peak:
        return (day - start) / max(1, peak - start)
    return (end - day) / max(1, end - peak)


def build_synthetic(spec):
    days = spec["n"]
    onset = spec["onset"]
    baseline = {}
    samples = []
    import random
    import statistics
    # str.__hash__ is salted per process, so hash() made every export a
    # different dataset. Use a stable checksum instead.
    import zlib
    rng = random.Random(zlib.crc32(spec["id"].encode()) & 0xFFFF)

    # generate: a pre-flight block (negative days), then the mission
    series = {}
    for analyte, (base, delta) in spec["series"].items():
        pts = []
        for d in range(-PRE_FLIGHT_DAYS, 0):
            pts.append((d, round(max(base * (1 + rng.gauss(0, 0.012)), 0.01), 3)))
        bump = spec.get("bump")
        for d in range(1, days + 1):
            if bump is None:
                t = max(0.0, (d - onset) / max(1, days - onset))
            else:
                t = profile(d, onset, bump)
            pts.append((d, round(max(base + delta * t, 0.01), 3)))
        series[analyte] = pts

    # baseline = median of the pre-flight block
    for analyte, pts in series.items():
        vals = sorted(v for d, v in pts if d < 0 and v > 0)
        if vals:
            baseline[analyte] = statistics.median(vals)

    panel = oc.Panel(baseline, horizon="short")
    events = [(BASE + timedelta(days=d), label) for d, label in spec["events"]]
    symptoms = [(BASE + timedelta(days=d), s) for d, s in spec["symptoms"]]

    for d in range(-PRE_FLIGHT_DAYS, days + 1):
        if d == 0:
            continue
        ts = BASE + timedelta(days=d)
        readings = {a: dict(pts)[d] for a, pts in series.items()}
        results = panel.process(ts, readings)
        summary = panel.summarise(results)
        outputs = panel.outputs(results, summary, events=events, symptoms=symptoms,
                                crew="SYN") if results else None
        samples.append({
            "timestamp": ts.strftime("%Y-%m-%d"),
            "day": d,
            "phase": phase_of(d),
            "status": summary["status"],
            "summary": jsonable(summary),
            "results": slim(results),
            "outputs": jsonable(outputs) if summary["status"] != "NORMAL" else None,
        })

    # keep every sample: the page steps through them one click at a time
    return {
        "id": spec["id"],
        "label": spec["label"],
        "crew": "SYN",
        "source": "synthetic",
        "cadence": "daily",
        "cadence_label": "acute phase · daily",
        "note": spec["note"],
        "baseline": {k: round(v, 3) for k, v in baseline.items()},
        "samples": samples,
        "series": [
            {"timestamp": s["timestamp"], "status": s["status"],
             "max_error_rcv": s["summary"]["max_error_rcv"]}
            for s in samples
        ],
    }


# ── weekly mission simulation ──────────────────────────────────────────────
MISSION_CSV = Path(__file__).parent / "data" / "mission_sim_cbc.csv"
MISSION_LABEL = {
    "N001": "Healthy control, weekly sampling",
    "N002": "Slow iron-deficiency-like drift, weekly sampling",
    "N003": "Acute infection at week 20, weekly sampling",
    "N004": "Corrupt record at week 30, then loss of signal",
    "N005": "Solar particle event at week 20, weekly sampling",
    "N006": "Chronic iron deficiency, weekly sampling",
    "N007": "Dehydration episode, weekly sampling",
    "N008": "One bad record, then two bad records, weekly sampling",
}
MISSION_ANALYTES = {
    "hemoglobin": "hemoglobin_value_percent",
    "hematocrit": "hematocrit_value_percent",
    "wbc": "white_blood_cell_count_value_thousand_per_microliter",
    "platelets": "platelet_count_value_thousand_per_microliter",
    "rdw": "rdw_value_percent",
    "mch": "mch_value_picogram",
    "total_protein": "total_protein_value_gram_per_deciliter",
}


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _week_of(tp):
    if tp == "L-92":
        return -92
    if tp == "L-44":
        return -44
    if tp.startswith("W") and tp[1:].isdigit():
        return int(tp[1:]) * 7
    return None


def build_mission():
    """Weekly cadence: the routine monitoring rate the design settled on."""
    import csv as _csv
    import statistics
    rows = {}
    with MISSION_CSV.open(encoding="utf-8-sig") as fh:
        for r in _csv.DictReader(fh):
            name = r["Sample Name"]
            crew = name[:4]
            tp = name.split("_")[-2]
            rec = {"tp": tp, "day": _week_of(tp)}
            for a, col in MISSION_ANALYTES.items():
                rec[a] = _num(r[col])
            rec["neutrophil_lymphocyte"] = (
                rec["wbc"] and _num(r["absolute_neutrophils_value_cells_per_microliter"])
                and _num(r["absolute_lymphocytes_value_cells_per_microliter"]) or None)
            nl = _num(r["absolute_neutrophils_value_cells_per_microliter"])
            ly = _num(r["absolute_lymphocytes_value_cells_per_microliter"])
            rec["neutrophil_lymphocyte"] = round(nl / ly, 2) if nl and ly else None
            if rec["day"] is not None:
                rows.setdefault(crew, []).append(rec)

    cases = []
    for crew, recs in sorted(rows.items()):
        recs.sort(key=lambda r: r["day"])
        pre = [r for r in recs if r["day"] < 0]
        baseline = {}
        for a in MISSION_ANALYTES:
            vals = sorted(r[a] for r in pre if r[a] is not None)
            if vals:
                baseline[a] = statistics.median(vals)
        panel = oc.Panel(baseline, horizon="long")
        samples = []
        for r in recs:
            ts = BASE + timedelta(days=r["day"])
            readings = {a: r[a] for a in baseline}
            results = panel.process(ts, readings)
            summary = panel.summarise(results)
            outputs = panel.outputs(results, summary, crew=crew) if results else None
            samples.append({
                "timestamp": ts.strftime("%Y-%m-%d"),
                "day": r["day"],
                "label": "pre-flight" if r["day"] < 0 else f"week {r['day']//7}",
                "phase": phase_of(r["day"]),
                "status": summary["status"],
                "summary": jsonable(summary),
                "results": slim(results),
                "outputs": jsonable(outputs) if summary["status"] != "NORMAL" else None,
            })
        cases.append({
            "id": "weekly_" + crew,
            "label": MISSION_LABEL.get(crew, crew),
            "crew": crew,
            "source": "synthetic",
            "cadence": "weekly",
            "cadence_label": "routine · every 7 days",
            "note": "52-week mission simulation at the routine monitoring cadence, used to exercise the drift rule.",
            "baseline": {k: round(v, 3) for k, v in baseline.items()},
            "samples": samples,
            "series": [{"timestamp": s["timestamp"], "status": s["status"],
                        "max_error_rcv": s["summary"]["max_error_rcv"]} for s in samples],
        })
    return cases

def main():
    rows = oc.load_cbc(next(p for p in oc.CBC_PATHS if p.exists()))
    cases = (build_real(rows)
             + build_mission()
             + [build_synthetic(spec) for spec in SYNTHETIC])

    payload = {
        "generated_from": "orbitcare_pid.py",
        "analytes": {
            k: {"label": v["label"], "unit": v["unit"], "class": v.get("class", "A")}
            for k, v in oc.ANALYTES.items()
        },
        "cases": cases,
    }

    out = Path(__file__).parent / "anatomy-explorer" / "immune-data.js"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "window.ENGINE_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    print(f"wrote {out}  ({out.stat().st_size/1024:.1f} KB)")
    for c in cases:
        statuses = [s["status"] for s in c["samples"]]
        print(f"  {c['label'][:44]:<46} samples_kept={len(c['samples'])} {statuses}")


if __name__ == "__main__":
    main()

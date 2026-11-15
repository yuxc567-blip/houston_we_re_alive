# SANS Monitor

An English, local web interface for the TRT monitoring model in `sans.py`.

## Start

Requires Python 3.9 or later; no packages need to be installed.

```sh
python3 sans_web.py
```

Open **http://localhost:8000**. Keep the terminal process running while using the site. Stop it with Ctrl+C.

To choose a different mission file or port:

```sh
python3 sans_web.py --data mission_02.json --port 8001
```

## Workflow

1. On first entry, set preflight values in the baseline dialog. It closes after saving; established baselines stay fixed. Use Baseline to view the reference or complete a missing eye. You can defer setup when the reference is unavailable.
2. Enter the flight day and TRT for one or both eyes, then confirm measurement quality.
3. Review both eyes together on Overview: latest scan day, baseline change, research-threshold status and a short next-step checklist. Open Additional analysis for rate, integral and forecast.
4. Open Measurement history for the per-eye trend chart, full measurement table, deletion of incorrect records, or CSV export.
5. Optionally enable experimental rate review and linear extrapolation in Analysis settings. These settings last for the server session.

Explore demo uses fictional measurements without modifying saved records. Return to my data to resume entry. Print report includes the overview and both eyes' history.

## Data and calculations

The server binds to loopback only. Records are saved to `sans_data.json` beside the scripts by default, compatible with the original terminal application. The previous saved version is retained as `.bak`. Use one server process per data file; do not edit the same file simultaneously with the terminal program.

All calculations use `sans.HealthController` through `sans.analyze`: fixed baseline deviation, relative change, interval-average rate, signed trapezoidal integral from the first recorded observation, and the model's strict +19.4 μm threshold comparison. Missing baselines and first measurements retain their original unavailable-value behavior. The interface is a research prototype, not a diagnostic or treatment system.

The interface uses system fonts and has no external font dependency. No measurement data is sent to a cloud backend.

The original CLI remains available: `python3 sans.py`.

## Crew interface

Overview prioritizes both eyes, input and next steps. Warm red with a triangle denotes research-threshold exceedance, green with explicit text denotes non-exceedance (not a healthy diagnosis), grey denotes unavailable assessment, and amber denotes an experimental measurement-review flag. Colors always have text labels. The OCT quick guide at `/learn` provides a scan-to-entry checklist, OCT research context, and concise explanations of logged countermeasures with their evidence limits. Additional Analysis links to the countermeasure guide only when the selected eye exceeds the research threshold. These are research summaries, not mission-approved operating or treatment instructions.

## Countermeasure records

Use Countermeasures to log actual LBNP, VTC, ITD, medication, supplement or other use. Record start/end flight day, actual duration or dose/settings, completion and optional notes. Entries can be edited or deleted. Demo mode includes fictional sessions and does not write real records.

Responses pair the last scan strictly before the session's start day with the first scan strictly after its end day, independently for each eye. Same-day scans are excluded because measurement/session ordering is unknown. Each card shows actual TRT, baseline deviation, measured change, scan interval and the post-session threshold state. Other interventions overlapping the scan interval are listed. Skipped sessions have no response comparison. Missing scans remain unavailable. New, edited or deleted scans automatically update the comparisons.

Interventions are stored as an optional `interventions` list in the existing mission JSON; old files continue to work. The CLI preserves this list. Export records downloads a JSON bundle containing raw quality-confirmed measurements, interventions, calculated metrics, comparisons and the pairing rule. Existing CSV export remains available for OCT metrics.

Run backend checks with `python3 -m unittest discover -s tests -v`.

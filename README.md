# SANS Monitor

Anatomy explorer with separate eye/SANS and blood/immune modules. The existing Python launch commands remain available at the repository root.

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

Overview prioritizes both eyes, input and next steps. Warm red with a triangle denotes research-threshold exceedance, green with explicit text denotes non-exceedance (not a healthy diagnosis), grey denotes unavailable assessment, and amber denotes an experimental measurement-review flag. Colors always have text labels. The OCT quick guide at `/eye/web/learn.html` provides a scan-to-entry checklist, OCT research context, and concise explanations of logged countermeasures with their evidence limits. Additional Analysis links to the countermeasure guide only when the selected eye exceeds the research threshold. These are research summaries, not mission-approved operating or treatment instructions.

## Countermeasure records

Use Countermeasures to log actual LBNP, VTC, ITD, medication, supplement or other use. Record start/end flight day, actual duration or dose/settings, completion and optional notes. Entries can be edited or deleted. Demo mode includes fictional sessions and does not write real records.

Responses pair the last scan strictly before the session's start day with the first scan strictly after its end day, independently for each eye. Same-day scans are excluded because measurement/session ordering is unknown. Each card shows actual TRT, baseline deviation, measured change, scan interval and the post-session threshold state. Other interventions overlapping the scan interval are listed. Skipped sessions have no response comparison. Missing scans remain unavailable. New, edited or deleted scans automatically update the comparisons.

Interventions are stored as an optional `interventions` list in the existing mission JSON; old files continue to work. The CLI preserves this list. Export records downloads a JSON bundle containing raw quality-confirmed measurements, interventions, calculated metrics, comparisons and the pairing rule. Existing CSV export remains available for OCT metrics.

Run backend checks with `python3 -m unittest discover -s tests -v`.


## Feature folders and local preview

- `eye/sans.py`: TRT calculations; `eye/interventions.py`: countermeasure records and response comparisons.
- `eye/server.py`: local API server. `eye/export_static.py`: static SANS bundle generator.
- `eye/web/`: eye monitor and countermeasure/education guide (`learn.html`), styling, scripts and static demo data.
- `eye/docs/`: SANS education source notes. Read `SANS_RESEARCH_HANDOFF.md` at the root before SANS changes.
- `immune/orbitcare_pid.py`: blood/immune engine; `immune/export_demo_data.py`: bundle exporter.
- `immune/web/`: immune monitor and its existing demo bundle. `immune/data/`: mission-simulation CSV.
- `control_loop.py`: shared controller; `sleep/`: existing sleep feature; `AnatomyExplorer-Source/`: editable Unity source.

Root `sans.py`, `sans_web.py`, `interventions.py`, `orbitcare_pid.py` and exporter files are compatibility entry points. Edit the implementations in `eye/` and `immune/`.

### VS Code Live Server

Open `anatomy-explorer/index.html` with Live Server. The eye and immune topic selections open their feature pages inside the viewer. Eye results use the bundled **read-only showcase**; Live Server cannot execute Python or save measurements. The countermeasure guide is at `eye/web/learn.html`.

### Full local Python app

Run `python sans_web.py`, then open `http://localhost:8000/anatomy/`. The eye monitor opens the live API-backed interface, where measurement entry and countermeasure records work. Existing `http://localhost:8000/` and `/learn` routes are retained. Saved mission data stays at the repository root unless `--data` specifies another location.

### Static hosting

Run `python build_static_site.py` and upload the **contents of `site/`**. Its root opens the anatomy viewer; `eye/web/` and `immune/web/` contain the monitor pages. Relative paths also work under a hosted subdirectory.

The builder regenerates the SANS bundle and reuses the committed immune demo bundle by default. To regenerate immune results, supply the optional `immune/data/OSD-569_CBC.csv` dataset and run `python build_static_site.py --refresh-immune`. Existing calculation rules are unchanged.


## Sleep and reaction interface

## Combined sleep and reaction-time dashboard

Run `python sleep/dashboard.py` and open **http://127.0.0.1:8010**. Keep the Python process running. The local webpage combines sleep entry, a measured five-trial reaction-time test, separate charts, history, and JSON export using the existing Python analysis functions.

See [the dashboard guide](sleep/DASHBOARD.md). No external assets or additional packages are required. VS Code Live Server alone cannot execute the Python APIs. Personal records stay local and are excluded from Git.


The dashboard also shows exploratory linear trends and user-approved **unvalidated prototype** status/urgency labels. See [the model and evidence audit](sleep/EVIDENCE_AND_MODEL_AUDIT.md) for formulas, thresholds, source pages and limitations. These labels are not diagnoses or a trained clinical urgency model.


### Brain sleep and reaction popup

Run `python sleep/dashboard.py`, then open http://127.0.0.1:8010/anatomy/ and click the brain. The large popup uses the live Python sleep/reaction dashboard. See [dashboard instructions](sleep/DASHBOARD.md). Unity source is in `AnatomyExplorer-Source`.

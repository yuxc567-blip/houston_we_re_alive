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

1. Set the preflight baseline for each eye. Established baselines are fixed.
2. Enter the flight day and TRT for one or both eyes, then confirm measurement quality.
3. Review the latest observation, baseline deviation, interval rate, signed integral, and trend chart. Switch eyes independently.
4. Open Measurement history to inspect, delete incorrect records, or export CSV.
5. Optionally enable experimental rate review and linear extrapolation in Analysis settings. These settings last for the server session.

Explore demo uses fictional measurements without modifying saved records. Return to my data to resume entry. Print report includes the overview and both eyes' history.

## Data and calculations

The server binds to loopback only. Records are saved to `sans_data.json` beside the scripts by default, compatible with the original terminal application. The previous saved version is retained as `.bak`. Use one server process per data file; do not edit the same file simultaneously with the terminal program.

All calculations use `sans.HealthController` through `sans.analyze`: fixed baseline deviation, relative change, interval-average rate, signed trapezoidal integral from the first recorded observation, and the model's strict +19.4 μm threshold comparison. Missing baselines and first measurements retain their original unavailable-value behavior. The interface is a research prototype, not a diagnostic or treatment system.

The page uses system fonts if optional Google Fonts cannot load. No measurement data is sent to a cloud backend.

The original CLI remains available: `python3 sans.py`.

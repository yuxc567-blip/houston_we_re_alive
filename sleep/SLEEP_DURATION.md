# Sleep duration analysis

Run from the repository root:

```sh
python sleep/sleep_duration.py
python sleep/sleep_duration.py --hours 8 6 7 --no-plot
python sleep/sleep_duration.py --hours 6 7 --days 2 4 --json
```

`--baseline` changes the comparison reference (default: the original script's 8 hours). `--days` supplies actual positive, increasing mission days when measurements have gaps. Duration is hours slept within each 24-hour period, between 0 and 24.

The script uses `Deviation`, `Error`, `AccumulatedError`, and `DeteriorationRate` from the unchanged root `control_loop.py`. Positive deviation is reference minus recorded sleep. Relative error is deviation/reference; printed percentage is 100 times relative error. A positive rate means sleep decreased; a negative rate means sleep increased. The table prints rate in percentage points per day. The first change and rate are unavailable because there is no previous reading.

Accumulated error is the shared trapezoidal integral of relative error over actual mission days, in fraction-days. It starts at the first recorded observation and assumes linear interpolation between observations. Negative deviations offset positive ones; it is not cumulative sleep debt or a validated damage metric. The mean summarizes recorded values, not unmeasured days.

`analyze_sleep(hours, mission_days=None, baseline_hours=8)` returns a JSON-compatible dictionary for future website/popup integration. `--json` writes that dictionary to stdout. No Unity/browser integration has been added here.

The existing shared status/urgency classes require warning, critical and rate thresholds. They are not applied because this script has no established sleep-specific thresholds. Results describe comparisons, not health classifications.

Plotting needs Matplotlib (`python -m pip install matplotlib`); analysis, JSON and `--no-plot` use only the Python standard library. Run checks with `python -B -m unittest discover -s tests -v`.


The combined browser dashboard adds a separate, user-approved **unvalidated prototype** review layer with fitted OLS trends and status/urgency rules. The raw analysis function described here remains descriptive. See [the model/evidence audit](EVIDENCE_AND_MODEL_AUDIT.md) for the distinction and source limits.

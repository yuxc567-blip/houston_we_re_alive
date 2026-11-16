# Combined sleep and reaction-time webpage

Run from the `houston-interface` repository folder:

```sh
python sleep/dashboard.py
```

Open **http://127.0.0.1:8010**. Keep the Python process running. This page needs the Python server; VS Code Live Server alone cannot run its calculation APIs.

- **Sleep journal:** record hours slept in each 24-hour period on actual mission days. Choose the reference before the first entry; it remains fixed afterward. Historical entries are sorted and the analysis is recomputed. Duplicate days are rejected.
- **Reaction test:** measure a five-trial browser baseline, then five-trial daily sessions. Wait for green, then click/tap the button or press Space/Enter with the button focused. Early responses and five-second timeouts do not become valid trial scores. Switching away cancels unfinished trials. Completed trials are only recorded after a successful local save; failed saves can be retried.
- **History:** view separate sleep and reaction series, deviations, rates, signed integrals, and reaction early/timeout counts. The first observation has no rate. Each chart has its own units and actual mission-day spacing.
- **Export journal:** download raw observations and calculated outputs as JSON.

The server calls the existing `analyze_sleep` in `sleep_duration.py` and `process_reaction_times` in `reactiontime.py`. The clinical interpretation and sign conventions are documented in their respective guides. No urgency classifications or correlation/causation claims are added.

Personal records are stored in `sleep/wellness_results.json`, excluded from Git. The original Tkinter test's result file is separate; browser and native timing should not share a baseline. To start a separate person/mission without overwriting existing records:

```sh
python sleep/dashboard.py --port 8012 --data sleep/mission2_results.json
```

The server binds only to loopback. Fonts, styles, scripts, timing, analysis and persistence are local; using the running webpage requires no LTE traffic. It is not a public hosting setup. No additional Python packages are needed.

Web files: `sleep/web/index.html`, `style.css`, and `app.js`. Server: `sleep/dashboard.py`. The existing blink-camera page at `sleep/index.html` is preserved. Run checks with `python -B -m unittest discover -s tests -v`.

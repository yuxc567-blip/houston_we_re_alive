# Houston — interface workspace

## Combined sleep and reaction-time dashboard

Run `python sleep/dashboard.py` and open **http://127.0.0.1:8010**. Keep the Python process running. The local webpage combines sleep entry, a measured five-trial reaction-time test, separate charts, history, and JSON export using the existing Python analysis functions.

See [the dashboard guide](sleep/DASHBOARD.md). No external assets or additional packages are required. VS Code Live Server alone cannot execute the Python APIs. Personal records stay local and are excluded from Git.


The dashboard also shows exploratory linear trends and user-approved **unvalidated prototype** status/urgency labels. See [the model and evidence audit](sleep/EVIDENCE_AND_MODEL_AUDIT.md) for formulas, thresholds, source pages and limitations. These labels are not diagnoses or a trained clinical urgency model.


### Brain sleep and reaction popup

Run `python sleep/dashboard.py`, then open http://127.0.0.1:8010/anatomy/ and click the brain. The large popup uses the live Python sleep/reaction dashboard. See [dashboard instructions](sleep/DASHBOARD.md). Unity source is in `AnatomyExplorer-Source`.

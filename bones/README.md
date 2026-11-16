# Bone module

- `export_bone_data.py`: runs the project controller over four mission profiles
  and writes `web/bone-data.js`.
- `prevention.py`: carried over unchanged from its author; supplies the
  prevention line for `bone_density`.
- `web/index.html`: monitor interface.

The engine is not reimplemented here. Every status, urgency band, error and
prevention line on the page is produced by `../control_loop.py`:
`HealthController(std=100, warning=0.05, critical=0.10, warning_rate=0.01,
critical_rate=0.02, prediction_days=7)` — the same configuration `test.py`
uses to export the Unity bone report.

Only the readings are simulated: bone density as a percentage of the crew
member's pre-flight baseline, over invented mission profiles.

Run from the repository root: `python -m bones.export_bone_data`.

# Heart / circulation module

- `cardiovascular.py`: the engine, carried over unchanged from its author.
  Reference trajectory is Balali et al. (2025), 17 ISS cosmonauts,
  doi:10.1038/s41526-025-00522-8, interpolated over flight days 6-159.
- `export_cardio_data.py`: generates `web/cardio-data.js`.
- `web/index.html`: monitor interface.

Where this differs from the blood module: the blood panel compares a reading
with the crew member's own pre-flight baseline, while this one compares it with
a *modelled expected value* — the published group trajectory scaled to that
baseline. Both the personal change and the study change are shown.

Run from the repository root: `python -m cardio.export_cardio_data`.

The thresholds the engine uses are fictional, and no individual clinical range
is established; the module reports a comparison, never a diagnosis.

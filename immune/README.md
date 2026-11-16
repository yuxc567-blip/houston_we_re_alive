# Blood / immune module

- `orbitcare_pid.py`: existing engine using the shared `../control_loop.py`.
- `export_demo_data.py`: generates `web/immune-data.js`.
- `web/index.html`: monitor interface.
- `data/mission_sim_cbc.csv`: existing mission simulation.

Run from the repository root: `python export_demo_data.py`, or `python -m immune.export_demo_data`. Regeneration also requires the optional NASA `data/OSD-569_CBC.csv` input. The committed demo bundle remains available without that dataset.

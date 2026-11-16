"""Run the bone-density example and optionally export it for Unity."""

import argparse
import json
from datetime import datetime
from pathlib import Path

from control_loop import HealthController


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unity-report", action="store_true")
    args = parser.parse_args()

    controller = HealthController(
        std=100.0,
        warning=0.05,
        critical=0.10,
        warning_rate=0.01,
        critical_rate=0.02,
        prediction_days=7,
    )
    timestamp = datetime(2026, 6, 6, 12, 0, 0)
    current_value = 92.5
    result = controller.process(timestamp, current_value)
    print(result)

    if args.unity_report:
        from prevention import PREVENTION_PLANS, Prevention, PreventionDatabase

        root = Path(__file__).resolve().parent
        history = root / "prevention.db"
        database = PreventionDatabase(history if history.is_file() else ":memory:")
        try:
            recommendation = Prevention(database, PREVENTION_PLANS).recommend(
                "bone_density", result["error"], result["urgency_level"]
            )
        finally:
            database.close()

        report = dict(
            result,
            baseline=controller.std,
            current=current_value,
            date=timestamp.date().isoformat(),
            prevention=recommendation,
        )
        destination = (
            root / "AnatomyExplorer-Source" / "Assets" / "Anatomy"
            / "Resources" / "BoneDensityReport.json"
        )
        destination.parent.mkdir(exist_ok=True)
        destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

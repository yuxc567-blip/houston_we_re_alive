"""Astronaut health indicator module.

The repository's existing convention is a very small script that prints a
mission status message when executed directly, while still exposing the health
calculator for import use.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Union


@dataclass(frozen=True)
class AstronautVitals:
    heart_rate: float
    oxygen: float
    temperature: float
    hydration: float
    stress: float


def astronaut_health_indicator(
    heart_rate: float,
    oxygen: float,
    temperature: float,
    hydration: float,
    stress: float,
) -> Dict[str, Union[str, int]]:
    """Return a health score and status for a given astronaut vital-sign set."""

    score = 100

    if heart_rate < 50 or heart_rate > 90:
        score -= 25
    elif heart_rate < 55 or heart_rate > 80:
        score -= 10

    if oxygen < 92:
        score -= 30
    elif oxygen < 95:
        score -= 15

    if temperature < 36.5 or temperature > 37.5:
        score -= 20
    elif temperature < 37.0 or temperature > 37.2:
        score -= 8

    if hydration < 60 or hydration > 120:
        score -= 20
    elif hydration < 70 or hydration > 100:
        score -= 8

    if stress > 70:
        score -= 25
    elif stress > 45:
        score -= 12

    score = max(0, min(100, int(score)))
    status = "stable" if score >= 80 else "monitor" if score >= 60 else "critical"
    return {"score": score, "status": status}


def main() -> None:
    """Print the mission status line expected by the project."""

    print("houston we are alive")


if __name__ == "__main__":
    main()

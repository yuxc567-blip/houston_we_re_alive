"""Analyze recorded sleep using the shared control-loop calculation classes.

Positive error means less sleep than the reference; negative means more.
The reference is a comparison value, not a diagnostic threshold.
"""
import argparse
from datetime import datetime, timedelta
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from control_loop import AccumulatedError, Deviation, DeteriorationRate, Error


def _number(value, label):
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number.")
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"{label} must be a finite number.") from None
    if not math.isfinite(number):
        raise ValueError(f"{label} must be a finite number.")
    return number


def analyze_sleep(sleep_durations, mission_days=None, baseline_hours=8):
    """Return JSON-compatible metrics without plotting or reading input.

    Each duration represents sleep hours in a 24-hour period. Explicit days
    support gaps: rates and integration use actual elapsed mission days.
    Integration covers only the first through last recorded observations,
    with linear interpolation between readings; it is not total sleep debt.
    """
    baseline = _number(baseline_hours, "Sleep reference")
    if not 0 < baseline <= 24:
        raise ValueError("Sleep reference must be greater than 0 and at most 24 hours.")
    hours = [_number(value, "Sleep duration") for value in sleep_durations]
    if not hours:
        raise ValueError("Enter at least one sleep duration.")
    if any(not 0 <= value <= 24 for value in hours):
        raise ValueError("Sleep duration must be between 0 and 24 hours.")
    days = list(range(1, len(hours) + 1)) if mission_days is None else list(mission_days)
    if len(days) != len(hours):
        raise ValueError("Provide one mission day for every sleep duration.")
    days = [_number(day, "Mission day") for day in days]
    if any(day < 1 or not day.is_integer() for day in days):
        raise ValueError("Mission days must be positive whole numbers.")
    days = [int(day) for day in days]
    if any(right <= left for left, right in zip(days, days[1:])):
        raise ValueError("Mission days must increase; duplicates are not allowed.")
    accumulated, deterioration = AccumulatedError(), DeteriorationRate()
    origin = datetime(2000, 1, 1)
    records = []
    for index, (day, duration) in enumerate(zip(days, hours)):
        try:
            timestamp = origin + timedelta(days=day - days[0])
        except OverflowError:
            raise ValueError("Mission day range is too large.") from None
        deviation = Deviation(baseline, duration).calculate()
        error = Error(baseline, duration).calculate()
        integral = accumulated.calculate(timestamp, error)
        rate = deterioration.calculate(timestamp, error)
        records.append({
            "mission_day": day,
            "sleep_hours": duration,
            "deviation_hours": deviation,
            "relative_error": error,
            "deviation_percent": error * 100,
            "change_from_previous_hours": None if index == 0 else duration - hours[index - 1],
            "error_rate_per_day": None if index == 0 else rate,
            "accumulated_relative_error_days": integral,
        })
    return {
        "baseline_hours": baseline,
        "mean_recorded_sleep_hours": sum(hours) / len(hours),
        "observed_start_day": days[0],
        "observed_end_day": days[-1],
        "records": records,
    }


def print_analysis(analysis):
    print(f"\nSleep reference: {analysis['baseline_hours']:g} hours per 24-hour period")
    print("Positive deviation = below reference; negative = above reference.")
    print(f"{'Day':>5} {'Sleep (h)':>10} {'Deviation (h)':>14} {'Deviation (%)':>14} {'Change (h)':>12} {'Rate (pp/day)':>15} {'Integral (fraction-days)':>25}")
    for row in analysis["records"]:
        change = row["change_from_previous_hours"]
        rate = row["error_rate_per_day"]
        change_text = "N/A" if change is None else f"{change:+.2f}"
        rate_text = "N/A" if rate is None else f"{rate * 100:+.2f}"
        print(f"{row['mission_day']:5d} {row['sleep_hours']:10.2f} {row['deviation_hours']:+14.2f} {row['deviation_percent']:+14.2f} {change_text:>12} {rate_text:>15} {row['accumulated_relative_error_days']:+25.3f}")
    print(f"Mean of recorded sleep values: {analysis['mean_recorded_sleep_hours']:.2f} hours.")
    last = analysis["records"][-1]
    deviation = last["deviation_hours"]
    position = "below" if deviation > 0 else "above" if deviation < 0 else "equal to"
    print(f"Latest sleep: {last['sleep_hours']:g} hours, {position} the reference" +
          (f" by {abs(deviation):g} h." if deviation != 0 else "."))
    print("Rate is change in deviation, in percentage points/day; positive means sleep decreased.")
    print("Integral covers recorded days only; above-reference values offset below-reference values.")
    print("These are descriptive comparisons, not a sleep-health or urgency classification.")


def plot_analysis(analysis):
    import matplotlib.pyplot as plt
    records = analysis["records"]
    days = [row["mission_day"] for row in records]
    figure, axes = plt.subplots(2, 1, sharex=True, figsize=(10, 7))
    axes[0].plot(days, [row["sleep_hours"] for row in records], marker="o", label="Hours slept")
    axes[0].axhline(analysis["baseline_hours"], color="gray", linestyle="--", label="Sleep reference")
    axes[0].set_ylabel("Sleep hours per 24-hour period")
    axes[0].set_title("Daily Sleep Duration and Reference Deviation")
    axes[0].legend()
    axes[1].plot(days, [row["deviation_percent"] for row in records], marker="o", label="Relative deviation")
    axes[1].axhline(0, color="gray", linestyle="--")
    axes[1].set_ylabel("Deviation (%) — positive = less sleep")
    axes[1].set_xlabel("Mission day")
    axes[1].legend()
    if len(days) <= 20:
        axes[1].set_xticks(days)
    for axis in axes:
        axis.grid(True, alpha=0.3)
    figure.tight_layout()
    plt.show()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=float, nargs="+", help="Recorded sleep hours (otherwise prompt interactively).")
    parser.add_argument("--days", type=int, nargs="+", help="Actual mission days, matching --hours.")
    parser.add_argument("--baseline", type=float, default=8, help="Comparison reference in hours; default 8.")
    parser.add_argument("--no-plot", action="store_true", help="Print results without opening a plot.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable results without a plot.")
    args = parser.parse_args()
    try:
        if args.days is not None and args.hours is None:
            raise ValueError("Use --days with --hours.")
        hours = args.hours
        if hours is None:
            total_days = int(input("Enter the total number of mission days: "))
            if total_days < 1:
                raise ValueError("The mission must last at least one day.")
            hours = [float(input(f"Enter sleep duration for mission day {day} (hours): ")) for day in range(1, total_days + 1)]
        analysis = analyze_sleep(hours, args.days, args.baseline)
    except (ValueError, EOFError) as error:
        parser.error(str(error))
    if args.json:
        print(json.dumps(analysis, allow_nan=False, indent=2))
    else:
        print_analysis(analysis)
        if not args.no_plot:
            plot_analysis(analysis)


if __name__ == "__main__":
    main()

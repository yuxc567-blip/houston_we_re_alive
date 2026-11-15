from datetime import datetime, timedelta, timezone
from enum import Enum
from math import isfinite


# ============================================================
# REFERENCE DATA
# ============================================================

# Balali et al. (2025), Tables 1–2:
# https://doi.org/10.1038/s41526-025-00522-8
#
# Separate study—not the NASA 2022 evidence report.
# Seated preflight group medians, 17 ISS cosmonauts.
# Nominal measurement days: 6, 37, 159.
# Actual timing: 6 ± 2, 37 ± 4, 159 ± 4 days.
#
# Daily interpolation is an estimate, not daily measured data.
# These references do NOT establish individual normal ranges.

EXPERIMENTS = {
    "heart_rate": {
        "unit": "bpm",
        "preflight": 66.0,
        "points": [(6, 61.0), (37, 62.0), (159, 61.0)],
    },
    "systolic_bp": {
        "unit": "mmHg",
        "preflight": 127.0,
        "points": [(6, 121.0), (37, 116.0), (159, 117.0)],
    },
    "diastolic_bp": {
        "unit": "mmHg",
        "preflight": 87.0,
        "points": [(6, 78.0), (37, 72.0), (159, 72.0)],
    },
}


def validate_positive(value, name):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"{name} must be positive and finite.")


# ============================================================
# 1. DEVIATION
# ============================================================

class Deviation:

    def __init__(self, std, current):
        validate_positive(std, "Reference")
        validate_positive(current, "Reading")

        self.std = std
        self.current = current

    def calculate(self):
        return self.std - self.current


# ============================================================
# 2. ERROR
# ============================================================

class Error(Deviation):

    def calculate(self):
        deviation = super().calculate()

        # Measure distance above OR below the reference.
        return abs(deviation / self.std)


# ============================================================
# 3. ACCUMULATED ERROR
# ============================================================

class AccumulatedError:

    def __init__(self, max_gap_days=2):
        validate_positive(max_gap_days, "Maximum gap")

        self.previous_error = None
        self.previous_time = None
        self.total = 0.0
        self.max_gap_days = max_gap_days

    def calculate(self, timestamp, error):

        if self.previous_error is None:
            self.previous_error = error
            self.previous_time = timestamp
            return self.total

        dt = (
            timestamp - self.previous_time
        ).total_seconds() / 86400

        if dt <= 0:
            raise ValueError("Timestamp must increase.")

        # Do not assume continuous observations across long gaps.
        if dt <= self.max_gap_days:
            self.total += (
                (self.previous_error + error) / 2
            ) * dt

        self.previous_error = error
        self.previous_time = timestamp

        return self.total


# ============================================================
# 4. DETERIORATION RATE
# ============================================================

class DeteriorationRate:

    def __init__(self, max_gap_days=2):
        self.previous_error = None
        self.previous_time = None
        self.max_gap_days = max_gap_days

    def calculate(self, timestamp, error):

        if self.previous_error is None:
            self.previous_error = error
            self.previous_time = timestamp

            # No trend can be calculated from one observation.
            return None

        dt = (
            timestamp - self.previous_time
        ).total_seconds() / 86400

        if dt <= 0:
            raise ValueError("Timestamp must increase.")

        rate = None

        if dt <= self.max_gap_days:
            rate = (
                error - self.previous_error
            ) / dt

        self.previous_error = error
        self.previous_time = timestamp

        return rate


# ============================================================
# 5. INTERVENTION STATUS — SIMULATION ONLY
# ============================================================

class Status(Enum):
    # NORMAL means below demo tolerance, not medically healthy.
    NORMAL = "NORMAL"
    WATCH = "WATCH"
    ACTION_REVIEW = "ACTION_REVIEW"


class InterventionStatus:

    def __init__(self, warning, critical):
        validate_positive(warning, "Warning threshold")
        validate_positive(critical, "Critical threshold")

        if warning >= critical:
            raise ValueError("Warning must be below critical.")

        self.warning = warning
        self.critical = critical

    def evaluate(self, error):

        if error >= self.critical:
            return Status.ACTION_REVIEW

        elif error >= self.warning:
            return Status.WATCH

        return Status.NORMAL


# ============================================================
# 6. URGENCY — SIMULATION ONLY
# ============================================================

class UrgencyLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Urgency:

    def __init__(
        self,
        warning,
        critical,
        warning_rate,
        critical_rate,
        prediction_days=7
    ):
        InterventionStatus(warning, critical)
        validate_positive(warning_rate, "Warning rate")
        validate_positive(critical_rate, "Critical rate")
        validate_positive(prediction_days, "Prediction days")

        if warning_rate >= critical_rate:
            raise ValueError(
                "Warning rate must be below critical rate."
            )

        self.warning = warning
        self.critical = critical
        self.warning_rate = warning_rate
        self.critical_rate = critical_rate
        self.prediction_days = prediction_days

    def evaluate(self, error, rate):

        if rate is None:
            return {
                "level": "INSUFFICIENT_TREND_DATA",
                "rate": None,
                "predicted_error": None,
            }

        # Experimental extrapolation—not a medical forecast.
        predicted_error = max(
            0.0,
            error + rate * self.prediction_days
        )

        # Preserves your original rule:
        # rapid changes in either direction trigger attention.
        rate_magnitude = abs(rate)

        if (
            error >= self.critical
            or predicted_error >= self.critical
            or rate_magnitude >= self.critical_rate
        ):
            level = UrgencyLevel.HIGH

        elif (
            error >= self.warning
            or predicted_error >= self.warning
            or rate_magnitude >= self.warning_rate
        ):
            level = UrgencyLevel.MEDIUM

        else:
            level = UrgencyLevel.LOW

        return {
            "level": level.value,
            "rate": rate,
            "predicted_error": predicted_error,
        }


# ============================================================
# 7. GENERAL HEALTH CONTROLLER
# ============================================================

class HealthController:

    def __init__(
        self,
        std,
        warning,
        critical,
        warning_rate,
        critical_rate,
        prediction_days=7
    ):
        validate_positive(std, "Reference")
        self.std = std

        self.accumulated = AccumulatedError()
        self.deterioration = DeteriorationRate()

        self.status = InterventionStatus(
            warning,
            critical
        )

        self.urgency = Urgency(
            warning,
            critical,
            warning_rate,
            critical_rate,
            prediction_days
        )

    def process(
        self,
        timestamp,
        current_value,
        reference_value=None
    ):
        if (
            not isinstance(timestamp, datetime)
            or timestamp.utcoffset() is None
        ):
            raise ValueError(
                "Use a timezone-aware datetime."
            )

        validate_positive(current_value, "Reading")

        reference = (
            self.std
            if reference_value is None
            else reference_value
        )

        validate_positive(reference, "Reference")

        # Validate before modifying either history.
        previous_time = self.deterioration.previous_time

        if (
            previous_time is not None
            and timestamp <= previous_time
        ):
            raise ValueError("Timestamp must increase.")

        self.std = reference

        # 1. Calculate deviation.
        deviation = Deviation(
            self.std, current_value
        ).calculate()

        # 2. Calculate relative error.
        error = Error(
            self.std, current_value
        ).calculate()

        # 3. Integrate error over observed time.
        accumulated_error = self.accumulated.calculate(
            timestamp, error
        )

        # 4. Calculate rate of error.
        rate = self.deterioration.calculate(
            timestamp, error
        )

        # 5. Evaluate demo status.
        status = self.status.evaluate(error)

        # 6. Evaluate demo urgency.
        urgency = self.urgency.evaluate(error, rate)

        # 7. Return results.
        return {
            "deviation": deviation,
            "error": error,
            "accumulated_error": accumulated_error,
            "error_rate": urgency["rate"],
            "intervention_status": status.value,
            "urgency_level": urgency["level"],
            "predicted_error": urgency["predicted_error"],
        }


# ============================================================
# 8. DAILY EXPERIMENTAL REFERENCE
# ============================================================

def experimental_reference(indicator, flight_day):

    if indicator not in EXPERIMENTS:
        raise ValueError(f"Unknown indicator: {indicator}")

    if (
        not isinstance(flight_day, (int, float))
        or not isfinite(flight_day)
        or not 6 <= flight_day <= 159
    ):
        raise ValueError(
            "Reference available only for flight days 6–159."
        )

    experiment = EXPERIMENTS[indicator]
    points = experiment["points"]

    for (day1, value1), (day2, value2) in zip(
        points, points[1:]
    ):
        if day1 <= flight_day <= day2:

            daily_rate = (
                value2 - value1
            ) / (day2 - day1)

            estimated_value = (
                value1
                + daily_rate * (flight_day - day1)
            )

            ratio = (
                estimated_value / experiment["preflight"]
            )

            return {
                "study_value": estimated_value,
                "ratio": ratio,
                "change_pct": 100 * (ratio - 1),
                "daily_rate": daily_rate,
            }

    raise ValueError("Unable to interpolate reference.")


# ============================================================
# 9. CARDIOVASCULAR MONITOR
# ============================================================

class CardiovascularMonitor:

    def __init__(self, personal_baselines, launch_time):

        if (
            not isinstance(launch_time, datetime)
            or launch_time.utcoffset() is None
        ):
            raise ValueError(
                "Launch time must include a timezone."
            )

        self.launch_time = launch_time
        self.baselines = {}
        self.controllers = {}

        for indicator in EXPERIMENTS:

            baseline = personal_baselines[indicator]
            validate_positive(baseline, "Personal baseline")
            self.baselines[indicator] = baseline

            # FICTIONAL thresholds for demonstrating the code.
            # They are NOT derived from experimental ranges.
            self.controllers[indicator] = HealthController(
                std=baseline,
                warning=0.15,
                critical=0.30,
                warning_rate=0.02,
                critical_rate=0.05,
                prediction_days=7
            )

    def process(self, indicator, timestamp, current_value):

        if (
            not isinstance(timestamp, datetime)
            or timestamp.utcoffset() is None
        ):
            raise ValueError(
                "Timestamp must include a timezone."
            )

        validate_positive(current_value, "Reading")

        flight_day = (
            timestamp - self.launch_time
        ).total_seconds() / 86400

        experiment = experimental_reference(
            indicator, flight_day
        )

        baseline = self.baselines[indicator]

        # Apply the study's relative change to the astronaut.
        # This scaling is a prototype assumption.
        personal_reference = (
            baseline * experiment["ratio"]
        )

        result = self.controllers[indicator].process(
            timestamp,
            current_value,
            reference_value=personal_reference
        )

        personal_change_pct = 100 * (
            current_value / baseline - 1
        )

        return {
            "indicator": indicator,
            "unit": EXPERIMENTS[indicator]["unit"],
            "flight_day": flight_day,
            "current_value": current_value,
            "personal_baseline": baseline,
            "modeled_reference": personal_reference,
            "personal_change_pct": personal_change_pct,
            "experimental_change_pct": experiment["change_pct"],
            "difference_percentage_points": (
                personal_change_pct - experiment["change_pct"]
            ),
            **result,
            "medical_intervention_status": "NOT_ASSESSED",
            "within_experimental_individual_range": (
                "NOT_ESTABLISHED"
            ),
        }


# ============================================================
# 10. FICTIONAL DATA AND DISPLAY
# ============================================================

def main():

    launch = datetime(2026, 1, 1, tzinfo=timezone.utc)

    monitor = CardiovascularMonitor(
        personal_baselines={
            "heart_rate": 70.0,
            "systolic_bp": 120.0,
            "diastolic_bp": 80.0,
        },
        launch_time=launch
    )

    # FICTIONAL astronaut measurements.
    samples = [
        (20, {
            "heart_rate": 65.0,
            "systolic_bp": 112.0,
            "diastolic_bp": 70.0,
        }),
        (21, {
            "heart_rate": 66.0,
            "systolic_bp": 113.0,
            "diastolic_bp": 71.0,
        }),
        (22, {
            "heart_rate": 80.0,
            "systolic_bp": 140.0,
            "diastolic_bp": 95.0,
        }),
    ]

    print("CARDIOVASCULAR RESEARCH COMPARISON")
    print("Fictional readings and alert thresholds.")
    print("Experimental daily references are interpolated.")
    print("Statuses are demonstration labels, not diagnoses.")

    for day, readings in samples:

        timestamp = launch + timedelta(days=day)

        print(f"\n{'=' * 55}")
        print(f"FLIGHT DAY {day}")
        print("=" * 55)

        for indicator, reading in readings.items():

            result = monitor.process(
                indicator,
                timestamp,
                reading
            )

            print(f"\n{indicator.upper()}")
            print(
                f"  Current: {reading:.2f} "
                f"{result['unit']}"
            )
            print(
                "  Modeled reference: "
                f"{result['modeled_reference']:.2f} "
                f"{result['unit']}"
            )
            print(
                "  Personal change: "
                f"{result['personal_change_pct']:+.2f}%"
            )
            print(
                "  Experimental change: "
                f"{result['experimental_change_pct']:+.2f}%"
            )
            print(
                "  Difference: "
                f"{result['difference_percentage_points']:+.2f}"
                " percentage points"
            )
            print(
                f"  Relative error: {result['error']:.4f}"
            )
            print(
                "  Accumulated error: "
                f"{result['accumulated_error']:.4f}"
                " fraction-days"
            )

            rate = result["error_rate"]

            print(
                "  Error rate: "
                + (
                    "Not available yet"
                    if rate is None
                    else f"{rate:+.4f} per day"
                )
            )
            print(
                "  Demo status: "
                f"{result['intervention_status']}"
            )
            print(
                "  Demo urgency: "
                f"{result['urgency_level']}"
            )


if __name__ == "__main__":
    main()
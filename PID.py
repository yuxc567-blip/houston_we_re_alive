
from datetime import timedelta
from enum import Enum


# ============================================================
# 1. REFERENCE STANDARDS
# Define these outside the classes.
# Replace placeholders with actual reference values.
# ============================================================

std_bone = 1.00
std_eye = None       # Define your reference value
std_cardiac = None   # Define your reference value
std_muscle = None         # Define your fourth indicator


# Thresholds represent relative deviation from the reference.
# These are examples, not universal medical thresholds.

warning_bone = 0.03
critical_bone = 0.05

# Define corresponding thresholds for other indicators
# once their reference standards are established.


# ============================================================
# 2. DEVIATION
# ============================================================

class Deviation:

    def __init__(self, std, current):
        self.std = std
        self.current = current

    def calculate(self):
        return self.std - self.current


# ============================================================
# 3. ERROR
# Inherits the absolute deviation calculation.
# ============================================================

class Error(Deviation):

    def calculate(self):
        deviation = super().calculate()

        return deviation / self.std


# ============================================================
# 4. ACCUMULATED ERROR
# Integrates positive error over time.
# ============================================================

class AccumulatedError:

    def __init__(self, window_days=30):
        self.window_days = window_days
        self.history = []

    def update(self, timestamp, error):

        self.history.append((timestamp, error))

    def calculate(self):

        if len(self.history) < 2:
            return 0.0

        latest = self.history[-1][0]

        cutoff = latest - timedelta(
            days=self.window_days
        )

        samples = [
            (t, e) for t, e in self.history
            if t >= cutoff
        ]

        total = 0.0

        for i in range(1, len(samples)):

            t1, e1 = samples[i - 1]
            t2, e2 = samples[i]

            dt = (t2 - t1).total_seconds() / 86400

            # Only accumulate positive deviation.
            # Improvement does not cancel past deterioration.
            e1 = max(e1, 0)
            e2 = max(e2, 0)

            total += ((e1 + e2) / 2) * dt

        return total


# ============================================================
# 5. DETERIORATION RATE
# Positive = deterioration.
# Negative = improvement.
# ============================================================

class DeteriorationRate:

    def __init__(self):
        self.previous_error = None
        self.previous_time = None

    def elapsed_days(self, timestamp):
        if self.previous_time is None:
            return None

        days = (timestamp - self.previous_time).total_seconds() / 86400
        if days <= 0:
            raise ValueError(
                "Timestamp must be later than previous measurement."
            )
        return days

    def calculate(self, timestamp, error):
        days = self.elapsed_days(timestamp)
        rate = 0.0 if days is None else (error - self.previous_error) / days
        self.previous_error = error
        self.previous_time = timestamp
        return rate


# ============================================================
# 6. INTERVENTION STATUS
# ============================================================

class Status(Enum):
    NORMAL = "NORMAL"
    WATCH = "WATCH"
    ACTION_REVIEW = "ACTION_REVIEW"


class InterventionStatus:

    def __init__(self, warning, critical):
        self.warning = warning
        self.critical = critical

    def evaluate(self, error):

        if error >= self.critical:
            return Status.ACTION_REVIEW

        elif error >= self.warning:
            return Status.WATCH

        return Status.NORMAL


# ============================================================
# 7. URGENCY
# Combines severity, deterioration rate and persistence.
# ============================================================

class UrgencyLevel(Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Urgency:

    def __init__(
        self,
        critical,
        rate_scale,
        accumulated_scale,
        weights=(0.50, 0.25, 0.25)
    ):

        self.critical = critical
        self.rate_scale = rate_scale
        self.accumulated_scale = accumulated_scale

        self.w_severity = weights[0]
        self.w_rate = weights[1]
        self.w_persistence = weights[2]

    def evaluate(self, error, rate, accumulated):

        severity = min(
            max(error, 0) / self.critical, 1
        )

        trend = min(
            max(rate, 0) / self.rate_scale, 1
        )

        persistence = min(
            max(accumulated, 0) / self.accumulated_scale, 1
        )

        score = 100 * (
            self.w_severity * severity
            + self.w_rate * trend
            + self.w_persistence * persistence
        )

        if error >= self.critical:
            level = UrgencyLevel.CRITICAL

        elif score >= 70:
            level = UrgencyLevel.HIGH

        elif score >= 40:
            level = UrgencyLevel.MODERATE

        else:
            level = UrgencyLevel.LOW

        return {
            "score": round(score, 2),
            "level": level.value
        }


# ============================================================
# 8. GENERAL HEALTH CONTROLLER
# All health indicators can use this same class.
# ============================================================

class HealthController:

    def __init__(
        self,
        std,
        warning,
        critical,
        window_days=30,
        rate_scale=0.001,
        accumulated_scale=1.0
    ):

        self.std = std

        self.deviation = Deviation(std, std)
        self.error = Error(std, std)

        self.accumulated = AccumulatedError(window_days)

        self.deterioration = DeteriorationRate()

        self.status = InterventionStatus(
            warning,
            critical
        )

        self.urgency = Urgency(
            critical,
            rate_scale,
            accumulated_scale
        )

    def process(self, timestamp, current_value):

        # 1. Calculate deviation.
        next_deviation = Deviation(self.std, current_value)
        next_error = Error(self.std, current_value)
        deviation = next_deviation.calculate()
        error = next_error.calculate()

        # Validate the timestamp before storing the new measurement.
        rate = self.deterioration.calculate(timestamp, error)
        self.deviation = next_deviation
        self.error = next_error

        # 4. Add the accepted reading to the accumulated error.
        self.accumulated.update(timestamp, error)
        accumulated = self.accumulated.calculate()

        # 5. Determine intervention status.
        status = self.status.evaluate(error)

        # 6. Determine urgency.
        urgency = self.urgency.evaluate(
            error, rate, accumulated
        )

        # 7. Return controller outputs.
        return {
            "current_value": current_value,
            "deviation": deviation,
            "error": error,
            "accumulated_error": accumulated,
            "deterioration_rate": rate,
            "intervention_status": status.value,
            "urgency_score": urgency["score"],
            "urgency_level": urgency["level"]
        }


# ============================================================
# 9. CREATE INDIVIDUAL CONTROLLERS
# ============================================================

bone_controller = HealthController(
    std=std_bone,
    warning=warning_bone,
    critical=critical_bone
)

# Create other controllers after defining their standards
# and thresholds.

# eye_controller = HealthController(
#     std=std_eye,
#     warning=warning_eye,
#     critical=critical_eye
# )
#
# cardiac_controller = HealthController(
#     std=std_cardiac,
#     warning=warning_cardiac,
#     critical=critical_cardiac
# )

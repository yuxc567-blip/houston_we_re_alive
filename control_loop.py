
from enum import Enum


# ============================================================
# 1. DEVIATION
# ============================================================

class Deviation:

    def __init__(self, std, current):
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
        return deviation / self.std


# ============================================================
# 3. ACCUMULATED ERROR
# ============================================================

class AccumulatedError:

    def __init__(self):
        self.previous_error = None
        self.previous_time = None
        self.total = 0.0

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

        # Trapezoidal integration.
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

    def __init__(self):
        self.previous_error = None
        self.previous_time = None

    def calculate(self, timestamp, error):

        if self.previous_error is None:
            self.previous_error = error
            self.previous_time = timestamp
            return 0.0

        dt = (
            timestamp - self.previous_time
        ).total_seconds() / 86400

        if dt <= 0:
            raise ValueError("Timestamp must increase.")

        rate = (
            error - self.previous_error
        ) / dt

        self.previous_error = error
        self.previous_time = timestamp

        return rate


# ============================================================
# 5. INTERVENTION STATUS
# ============================================================

class Status(Enum):
    NORMAL = "NORMAL"
    WATCH = "WATCH OUT"
    ACTION_REVIEW = "ACTION NEEDED"


class InterventionStatus:
    def __init__(self, warning, critical):
        self.warning = warning   # e.g., 0.05 (5% deviation)
        self.critical = critical # e.g., 0.10 (10% deviation)

    def evaluate(self, error):
        abs_error = abs(error)

        if abs_error >= self.critical:
            return Status.ACTION_REVIEW
        elif abs_error >= self.warning:
            return Status.WATCH

        return Status.NORMAL


# ============================================================
# 6. URGENCY
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
        prediction_days=7 # Number of days to predict into the future
    ):

        self.warning = warning
        self.critical = critical

        self.warning_rate = warning_rate
        self.critical_rate = critical_rate

        self.prediction_days = prediction_days

    def evaluate(self, error, rate):

        # Predict future error using the current rate.
        predicted_error = (
            error + rate * self.prediction_days
        )

        # Detect rapid changes in either direction.
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
            "rate": rate
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

    def process(self, timestamp, current_value):

        # 1. Calculate deviation.
        deviation = Deviation(
            self.std, current_value
        ).calculate()

        # 2. Calculate relative error.
        error = Error(
            self.std, current_value
        ).calculate()

        # 3. Integrate error over time.
        accumulated_error = self.accumulated.calculate(
            timestamp, error
        )

        # 4. Calculate rate of error.
        rate = self.deterioration.calculate(
            timestamp, error
        )

        # 5. Evaluate intervention status.
        status = self.status.evaluate(error)

        # 6. Evaluate urgency.
        urgency = self.urgency.evaluate(error, rate)

        # 7. Return results.
        return {
            "deviation": deviation,
            "error": error,
            "accumulated_error": accumulated_error,
            "error_rate": urgency["rate"],
            "intervention_status": status.value,
            "urgency_level": urgency["level"]
        }

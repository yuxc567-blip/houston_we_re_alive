"""Exploratory trends and user-approved prototype review rules.

The thresholds are project examples, NOT NASA or clinical limits. Regression
fits measured deviations; urgency is an explicit rule, not a trained outcome model.
"""
import math
import statistics

from control_loop import InterventionStatus, Urgency

SETTINGS = {
    "warning_error": 0.05,
    "critical_error": 0.10,
    "warning_rate_per_day": 0.02,
    "critical_rate_per_day": 0.05,
    "forecast_days": 7,
    "minimum_regression_points": 3,
    "classification_basis": "User-approved unvalidated prototype thresholds; not NASA or clinical criteria.",
}
NASA_URL = "https://humanresearchroadmap.nasa.gov/Evidence/reports/Sleep.pdf"
AASM_URL = "https://aasm.org/resources/pdf/adultsleepdurationconsensus.pdf"
EVIDENCE = [
    {"id": "schedule", "title": "Protect sleep opportunity and review workload",
     "guidance": "Protect planned sleep time; identify work or schedule changes that displace it. For continuing difficulties, review the schedule with the appropriate clinician or mission team.",
     "basis": "NASA 2016, pp. 24 and 50–52: operational scheduling, recovery sleep and fatigue-management research; effects and individual needs vary.", "url": NASA_URL + "#page=24"},
    {"id": "light", "title": "Review sleep timing and the lighting plan",
     "guidance": "Aim for a consistent sleep/wake schedule where operations allow. Discuss major schedule shifts and any targeted light intervention with trained personnel; light timing matters.",
     "basis": "NASA 2016, pp. 24 and 48–49: lighting can alter circadian timing and alertness. Ground findings do not establish a personalized treatment from this dashboard.", "url": NASA_URL + "#page=48"},
    {"id": "naps", "title": "Plan naps rather than treating them as a replacement for sleep",
     "guidance": "When sleep opportunity is constrained, discuss strategically scheduled naps. Account for sleep inertia after waking and the effect of naps on the main sleep schedule.",
     "basis": "NASA 2016, pp. 30–31 and 50: studies support possible benefits, with timing, circadian and sleep-inertia limitations. No universal nap duration is prescribed here.", "url": NASA_URL + "#page=50"},
    {"id": "recovery", "title": "Allow recovery and verify the pattern",
     "guidance": "Review persistent short sleep and plan recovery opportunities. Repeat response tests under comparable conditions; do not use a better five-click score as proof of full recovery or fitness for duty.",
     "basis": "NASA 2016, pp. 25 and 50–51: recovery can require more than one opportunity, and validated PVT protocols differ from this short practice task.", "url": NASA_URL + "#page=50"},
    {"id": "medication", "title": "Medication and stimulant strategies require an individual plan",
     "guidance": "The report reviews caffeine, melatonin and sleep medicines. This app does not recommend their dose or timing, or substitute them for a personalized clinical or mission plan.",
     "basis": "NASA 2016, pp. 23–24 and 45–48: benefits, adverse effects and individual variability are discussed; reported use is not a treatment recommendation.", "url": NASA_URL + "#page=45"},
]


def linear_regression(x_values, y_values):
    """OLS with intercept, centered for numerical stability; no external packages."""
    xs, ys = list(x_values), list(y_values)
    if len(xs) != len(ys):
        raise ValueError("Regression inputs must have the same length.")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in xs + ys):
        raise ValueError("Regression inputs must be finite numbers.")
    result = {"n": len(xs), "minimum_points": SETTINGS["minimum_regression_points"],
              "status": "insufficient_data", "slope": None, "intercept": None,
              "r_squared": None, "rmse": None}
    if len(xs) < SETTINGS["minimum_regression_points"]:
        return result
    mean_x, mean_y = statistics.mean(xs), statistics.mean(ys)
    xx = math.fsum((x - mean_x) ** 2 for x in xs)
    if xx == 0:
        result["status"] = "no_predictor_variation"
        return result
    slope = math.fsum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / xx
    intercept = mean_y - slope * mean_x
    residual = math.fsum((y - (mean_y + slope * (x - mean_x))) ** 2 for x, y in zip(xs, ys))
    total = math.fsum((y - mean_y) ** 2 for y in ys)
    return {**result, "status": "fitted", "slope": slope, "intercept": intercept,
            "r_squared": max(0.0, min(1.0, 1 - residual / total)) if total > 0 else None,
            "rmse": math.sqrt(residual / len(xs)), "mean_x": mean_x, "mean_y": mean_y}


def _status(error):
    # Sleep deficit / response slowdown are the adverse directions here. Do not
    # flag above-reference sleep or faster responding just because magnitude is large.
    return InterventionStatus(SETTINGS["warning_error"], SETTINGS["critical_error"]).evaluate(max(0.0, round(error, 12))).value


def assess_series(records, error_key, rate_key, integral_key):
    trend = linear_regression([r["mission_day"] for r in records], [r[error_key] for r in records])
    if not records:
        return {"status": "NOT ASSESSED", "urgency": "NOT ASSESSED", "trend": trend,
                "reason": "Add observations; missing data is not a normal result.", "recommendation_ids": [], "reasons": []}
    latest = records[-1]
    current, derivative = latest[error_key], latest[rate_key]
    slope = trend["slope"]
    # Generic Urgency uses abs(rate). Passing only worsening components prevents
    # a rapid improvement from being classified as high urgency by its magnitude.
    worsening = round(max(0.0, derivative or 0.0, slope or 0.0), 12)
    base = Urgency(SETTINGS["warning_error"], SETTINGS["critical_error"],
                   SETTINGS["warning_rate_per_day"], SETTINGS["critical_rate_per_day"],
                   prediction_days=0).evaluate(max(0.0, round(current, 12)), worsening)["level"]
    forecast = None
    if trend["status"] == "fitted":
        future_day = latest["mission_day"] + SETTINGS["forecast_days"]
        forecast = trend["mean_y"] + trend["slope"] * (future_day - trend["mean_x"])
        trend["forecast_day"] = future_day
        trend["forecast_error"] = forecast
        trend["observed_start_day"] = records[0]["mission_day"]
        trend["observed_end_day"] = latest["mission_day"]
        # Forecast is used only when the fitted error trend is worsening. It is a
        # mathematical extrapolation, not a clinically calibrated prediction.
        if slope > 0:
            if round(forecast, 12) >= SETTINGS["critical_error"]:
                base = "HIGH"
            elif round(forecast, 12) >= SETTINGS["warning_error"] and base == "LOW":
                base = "MEDIUM"
    status = _status(current)
    reasons = [f"Current adverse-direction deviation: {max(0.0, current) * 100:.2f}%."]
    if derivative is None:
        reasons.append("Interval derivative unavailable: there is no previous reading.")
    else:
        reasons.append(f"Latest interval derivative: {derivative * 100:+.2f} percentage points/day.")
    if slope is not None:
        reasons.append(f"Fitted error slope: {slope * 100:+.2f} percentage points/day across {len(records)} observations.")
        reasons.append(f"Unvalidated {SETTINGS['forecast_days']}-day linear extrapolation: {forecast * 100:+.2f}% deviation.")
    else:
        reasons.append("Linear regression needs at least three observations with varying mission days.")
    reasons.append("Only positive worsening rates can raise urgency; improvement alone does not.")
    reasons.append("Signed integral is descriptive; it has no validated escalation cutoff.")
    ids = ["schedule", "light"] if base == "LOW" else ["schedule", "recovery", "naps", "light"]
    action = {"LOW": "Maintain planned sleep opportunities and keep observing. A NORMAL prototype result is not a health or fitness-for-duty clearance.",
              "MEDIUM": "Review the entries, test conditions and sleep/work schedule. Consider the evidence-linked scheduling options below; this demo flag is a prompt for review.",
              "HIGH": "Prioritize review of the repeated observations and the sleep/work schedule with the appropriate clinician or mission team. This HIGH label is a prototype rule, not a medical emergency grade."}[base]
    return {"status": status, "urgency": base, "current_error": current,
            "latest_derivative_per_day": derivative, "worsening_rate_used_per_day": worsening,
            "signed_integral_fraction_days": latest[integral_key], "trend": trend,
            "reasons": reasons, "recommendation": action, "recommendation_ids": ids}


def monitoring_summary(sleep_records, reaction_records):
    sleep = assess_series(sleep_records, "relative_error", "error_rate_per_day", "accumulated_relative_error_days")
    reaction = assess_series(reaction_records, "error", "error_rate", "accumulated_error")
    paired = {r["mission_day"]: r["relative_error"] for r in sleep_records}
    pairs = [(paired[r["mission_day"]], r["error"]) for r in reaction_records if r["mission_day"] in paired]
    association = linear_regression([p[0] for p in pairs], [p[1] for p in pairs])
    association["description"] = "Same-day sleep-deviation versus response-slowdown association. Exploratory only; not causation and not used to assign urgency."
    return {"settings": dict(SETTINGS), "sleep": sleep, "reaction": reaction,
            "association": association, "evidence": EVIDENCE,
            "reference_context": "The sleep reference is user-chosen; 8 hours is not a universal healthy/clinical cutoff. Adult (18–60) consensus recommends at least 7 hours regularly; individual sleep needs vary. The reaction baseline is a personal practice reference, not proof of healthy performance.",
            "reference_source": AASM_URL,
            "model_limit": "Linear regression plus explicit prototype rules is not a trained or validated clinical urgency model. The 2016 report is historical evidence, not current mission operating guidance."}

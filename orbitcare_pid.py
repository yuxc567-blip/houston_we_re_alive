"""
OrbitCare — adapter layer for the team PID controller (PID.py).

Does not modify PID.py. Wraps HealthController so that the evidence-based
configuration from the research work can drive it unchanged.

Three things the adapter fixes:

1. PID.py's Error is unilateral: error = (std - current) / std. That is correct
   only for markers where LOW is bad. For a high-bad marker such as CRP or RDW
   the error becomes negative and never reaches a threshold. Solved here by
   transforming the input value per direction, so PID.py needs no change.

2. PID.py's thresholds are fixed relative deviations (0.03 / 0.05). Thresholds
   must instead be the analyte's own reference change value: a 5% fall in
   haemoglobin is inside normal noise, while a 5% rise in sodium is not.

3. PID.py has no physiological rail. A value can be "only 8% from baseline" and
   still be a clinical emergency.

Run:  python3 orbitcare_pid.py --demo
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta
from math import isfinite
from pathlib import Path
from statistics import median

from control_loop import HealthController

# ============================================================================
# ANALYTE CONFIGURATION
#
# direction : "low_bad" | "high_bad" | "both_bad"
# rcv_short : one reference change value; used for short-interval comparisons
# rcv_long  : wider value for comparisons across weeks/months (mission drift)
# rail      : physiological hard limits; crossing overrides every other rule
# evidence  : "cited" | "derived" | "inferred"  (see the research notes)
#
# RCV values are indicative: published within-subject biological variation plus
# an assumed analytical CV of 1-3%. Rails are terrestrial clinical critical
# values, not flight standards.
# ============================================================================

ANALYTES: dict[str, dict] = {
    # RCV derivation, applied identically to every analyte below:
    #
    #     RCV = 1.96 * sqrt(2) * sqrt(CVi^2 + CVa^2)
    #
    # CVa (analytical) is assumed 1.5% for counting methods, 2% per count for
    # ratios where two counts propagate. CVi (within-subject biological
    # variation) is taken from the haematology biological-variation literature
    # -- Coskun et al. 2019 (Clin Chem Lab Med 58:25-32, PMID 31503541) reports
    # erythrocyte-related parameters below 3% and leukocyte/platelet parameters
    # between 5% and 15%. Each entry records the CVi used, so the number can be
    # recomputed rather than trusted.
    #
    # rcv_short applies to comparisons over days to weeks.
    # rcv_long applies to comparisons over months; it is only widened where the
    # observed data showed larger spread (haemoglobin, haematocrit).
    "hemoglobin": {
        "label": "Haemoglobin",
        "unit": "g/dL",
        "direction": "low_bad",
        "cvi": 2.8,
        "rcv_short": 0.09,   # CVi 2.8%, CVa 1.5% -> 8.8%
        "rcv_long": 0.12,    # widened: observed within-person CV 4.2% in OSD-569
        "rail_low": 7.0,
        "rail_high": 20.0,
                "ref_low": 13.2,
        "ref_high": 17.1,
        "evidence": "derived",
    },
    "hematocrit": {
        "label": "Haematocrit",
        "unit": "%",
        "direction": "both_bad",
        "cvi": 2.7,
        "rcv_short": 0.08,   # CVi 2.7% -> 8.6%
        "rcv_long": 0.11,    # widened for long-interval comparison
        "rail_low": 18.0,
        "rail_high": 60.0,
                "ref_low": 38.5,
        "ref_high": 50.0,
        "evidence": "derived",
    },
    "wbc": {
        "label": "White cell count",
        "unit": "10^3/uL",
        "direction": "both_bad",
        "cvi": 12.0,
        "rcv_short": 0.34,   # CVi 12% -> 33.5%
        "rcv_long": 0.34,
        "rail_low": 1.0,
        "rail_high": 30.0,
                "ref_low": 3.8,
        "ref_high": 10.8,
        "evidence": "derived",
    },
    "neutrophil_lymphocyte": {
        "label": "Neutrophil:lymphocyte ratio",
        "unit": "ratio",
        "direction": "high_bad",
        # NLR is a ratio and has no entry in any biological-variation database.
        # Derived by error propagation, assuming neutrophil and lymphocyte CVi
        # are both 10% (midpoint of the 5-15% leukocyte band):
        #     CVi(NLR) = sqrt(10^2 + 10^2) = 14.1%
        #     CVa(NLR) = sqrt(2^2 + 2^2)   = 2.8%
        #     RCV      = 1.96 * sqrt(2) * sqrt(14.1^2 + 2.8^2) = 40.0%
        # The 10% assumption is not verified; treat as derived-with-assumption.
        "cvi": 14.1,
        "rcv_short": 0.40,
        "rcv_long": 0.40,
        "ref_low": 1.0,
        "ref_high": 5.0,
        "rail_low": 0.5,
        "rail_high": 20.0,
        "evidence": "derived (assumed CVi)",
    },
    "platelets": {
        "label": "Platelets",
        "unit": "10^3/uL",
        "direction": "low_bad",
        "cvi": 7.0,
        "rcv_short": 0.20,   # CVi 7% -> 19.8%
        "rcv_long": 0.20,
        "rail_low": 20.0,
        "rail_high": 1000.0,
                "ref_low": 140.0,
        "ref_high": 400.0,
        "evidence": "derived",
    },
    "rdw": {
        "label": "RDW",
        "unit": "%",
        "direction": "high_bad",
        "cvi": 3.0,
        "rcv_short": 0.09,   # CVi 3.0% -> 9.3%  (was 0.15, 61% too wide)
        "rcv_long": 0.09,
        "rail_low": 11.5,
        "rail_high": 20.0,
                "ref_low": 11.0,
        "ref_high": 15.0,
        "evidence": "derived",
    },
    "mch": {
        "label": "MCH",
        "unit": "pg",
        "direction": "low_bad",
        "cvi": 2.5,
        "rcv_short": 0.08,   # CVi 2.5% -> 8.1%  (was 0.10, 23% too wide)
        "rcv_long": 0.08,
        "rail_low": 20.0,
        "rail_high": 36.0,
                "ref_low": 27.0,
        "ref_high": 33.0,
        "evidence": "derived",
    },
    "total_protein": {
        "label": "Total protein",
        "unit": "g/dL",
        "direction": "both_bad",
        "cvi": 2.7,
        "rcv_short": 0.09,   # CVi 2.7% -> 8.6%  (was 0.06, 30% too narrow)
        "rcv_long": 0.09,
        "ref_low": 6.1,
        "ref_high": 8.1,
        "rail_low": 4.0,
        "rail_high": 10.0,
        "evidence": "derived",
    },
}


# ============================================================================
# MECHANISM PATTERNS
#
# Each pattern lists the analytes it needs and the direction each must take.
# Directions are classified from the RCV-normalised error, not the raw
# percentage, so a 6% fall in haemoglobin (0.50 RCV) and a 17% fall in white
# cells (0.50 RCV) both count as "low".
#
# Reconstructed from the six-output export after the original method was lost
# to a file collision; thresholds were read back out of 715 stored detail
# records, then re-validated against the 100 exported samples.
# ============================================================================

PATTERNS: list[dict] = [
    {
        "id": "hemolysis",
        "title": "Haemolytic pattern",
        "mechanism": "Red cells are destroyed faster than they are made.",
        "want": {"hemoglobin": "low", "reticulocytes": "high",
                 "haptoglobin": "low", "serum_iron": "high"},
        "avoid": ["High-intensity aerobic training this week",
                  "Iron supplementation",
                  "Reading falling haemoglobin as nutritional"],
        "next": ["Haptoglobin", "Indirect bilirubin", "LDH", "Reticulocyte count"],
    },
    {
        "id": "marrowsupp",
        "title": "Marrow suppression pattern",
        "mechanism": "The marrow is producing fewer cells across more than one line.",
        "want": {"hemoglobin": "low", "wbc": "low",
                 "platelets": "low", "reticulocytes": "low"},
        "avoid": ["Exercise of any intensity until reviewed",
                  "Iron or B12 supplementation without a level"],
        "next": ["CBC repeat in 24 h", "EPO", "Reticulocyte count"],
    },
    {
        "id": "microcytic",
        "title": "Microcytic pattern",
        "mechanism": "Small, pale red cells with low haemoglobin: iron deficiency or "
                     "thalassaemia territory.",
        "want": {"hemoglobin": "low", "mch": "low"},
        "avoid": ["Assuming thalassaemia is iron deficiency",
                  "Iron without a ferritin level"],
        "next": ["Ferritin", "Serum iron", "Transferrin saturation"],
    },
    {
        "id": "dilution",
        "title": "Dilution pattern",
        "mechanism": "All concentration markers fall together: plasma volume is up.",
        "want": {"hemoglobin": "low", "hematocrit": "low", "total_protein": "low"},
        "avoid": ["Fluid restriction without medical direction",
                  "Iron supplementation"],
        "next": ["Albumin", "Total protein"],
    },
    {
        "id": "concentration",
        "title": "Haemoconcentration pattern",
        "mechanism": "Protein and cells concentrate together: plasma volume is down.",
        "want": {"hematocrit": "high", "total_protein": "high"},
        "avoid": ["Diuretics", "Reading high haemoglobin as good"],
        "next": ["Daily fluid intake log", "Total protein"],
    },
    {
        "id": "infection",
        "title": "Infection pattern",
        "mechanism": "Neutrophilia with an inflammatory marker rise.",
        "want": {"wbc": "high", "neutrophil_lymphocyte": "high", "crp": "high"},
        "avoid": ["Self-starting antibiotics", "Strenuous exercise"],
        "next": ["Blood culture if available", "CRP", "Symptom review 12-hourly"],
    },
    {
        "id": "stress",
        "title": "Stress demargination pattern",
        "mechanism": "White cells rise without an inflammatory marker: stress axis, "
                     "not infection.",
        "want": {"wbc": "high", "neutrophil_lymphocyte": "high"},
        "avoid": ["Caffeine to compensate for fatigue", "Treating as infection"],
        "next": ["CRP to exclude infection", "Salivary cortisol (diurnal)"],
    },
]

# An analyte counts as low/high once it is half a normal wobble from baseline.
DIRECTION_FLOOR_RCV = 0.5
PATTERN_MIN_HITS = 2
PATTERN_MIN_CONFIDENCE = 0.66
FORECAST_HORIZON_DAYS = 90
EVENT_WINDOW_DAYS = 14


def classify_direction(result: dict) -> str:
    """low / high / flat, measured in RCV rather than in percent."""
    if result["error_rcv"] < DIRECTION_FLOOR_RCV:
        return "flat"
    return "low" if result["deviation_pct"] < 0 else "high"


def evaluate_pattern(pattern: dict, by_analyte: dict) -> dict:
    detail, present, missing, hits = [], [], [], 0
    for analyte, want in pattern["want"].items():
        r = by_analyte.get(analyte)
        if r is None:
            missing.append(analyte)
            detail.append({"analyte": analyte, "want": want, "got": None, "ok": False})
        else:
            got = classify_direction(r)
            ok = got == want
            hits += int(ok)
            present.append(analyte)
            detail.append({"analyte": analyte, "want": want, "got": got, "ok": ok})
    confidence = hits / len(present) if present else 0.0
    return {
        "id": pattern["id"],
        "title": pattern["title"],
        "mechanism": pattern["mechanism"],
        "avoid": list(pattern["avoid"]),
        "next": list(pattern["next"]),
        "hits": hits,
        "present": present,
        "missing": missing,
        "detail": detail,
        "confidence": round(confidence, 4),
        "qualifies": hits >= PATTERN_MIN_HITS and confidence >= PATTERN_MIN_CONFIDENCE,
    }


# ============================================================================
# DIRECTION
# ============================================================================

def implausible_reason(analyte: str, value: float) -> str | None:
    """
    A value so far outside the laboratory interval that it is more likely a
    data-entry or assay fault than a physiological state.

    OSD-569 contains exactly this case: C003's L-92 record reads platelets
    12.9 x10^3/uL (all other samples 185-396) and RDW 32.4% (all others
    11.8-13.2) in the same row, while haematocrit still equals RBC x MCV.
    Two implausible fields, one otherwise consistent row.
    """
    cfg = ANALYTES.get(analyte, {})
    lo, hi = cfg.get("ref_low"), cfg.get("ref_high")
    if lo is None or hi is None or not isfinite(value):
        return None
    if value < lo * 0.5:
        return f"{value:g} is below half the laboratory lower limit ({lo:g})"
    if value > hi * 2:
        return f"{value:g} is above twice the laboratory upper limit ({hi:g})"
    return None


def directed_value(direction: str, std: float, current: float) -> float:
    """
    Map any direction onto PID.py's built-in assumption that a value below std
    is deterioration.

    low_bad   value falls  -> pass through
    high_bad  value rises  -> mirror about std
    both_bad  either way   -> collapse to |deviation|

    After this, PID.py's error = (std - x) / std is always >= 0 when the
    deviation is in the harmful direction, and < 0 when it is in the safe one.
    """
    if direction == "low_bad":
        return current
    if direction == "high_bad":
        return 2 * std - current
    if direction == "both_bad":
        return std - abs(current - std)
    raise ValueError(f"unknown direction: {direction!r}")


# ============================================================================
# CONTROLLER
# ============================================================================

class AnalyteController:
    """One analyte, configured for the PID.py engine."""

    def __init__(self, analyte: str, std: float, horizon: str = "short"):
        cfg = ANALYTES[analyte]
        self.analyte = analyte
        self.cfg = cfg
        self.std = float(std)
        if not isfinite(self.std) or self.std <= 0:
            raise ValueError("Baseline must be finite and positive.")
        self.direction = cfg["direction"]

        rcv = cfg["rcv_long"] if horizon == "long" else cfg["rcv_short"]
        self.rcv = rcv

        # control_loop.py thresholds are relative deviations, so RCV is passed
        # directly. warning = 1 RCV, critical = 2 RCV. The *_rate arguments are
        # changes per checking interval (one day), so a rate of one RCV means
        # one RCV per day, and two RCV per day is critical.
        self.engine = HealthController(
            std=self.std,
            warning=rcv,
            critical=2 * rcv,
            warning_rate=rcv,
            critical_rate=2 * rcv,
            prediction_days=7,       # urgency projects one week ahead
        )

        # SPC rule 4: a run of consecutive readings on the same side of the
        # baseline. Individual points can each sit inside one RCV while the
        # series slides, which is the characteristic shape of slow deterioration
        # on a long mission.
        self.drift_threshold = 8
        # A run of same-side readings alone is not evidence of anything. With
        # 156 weekly samples over three years the bare rule fires on about 60%
        # of missions by chance. Requiring the current reading to sit at least
        # half an RCV from baseline cuts that to ~4% and costs about three weeks
        # of detection latency for a 1.5%-per-month drift (simulated, CVi 2.8%,
        # rho 0.3). Raising the floor to 0.75 buys almost nothing and delays
        # detection by eight weeks.
        self.drift_floor_rcv = 0.5
        self.drift_run = 0
        self._last_side = 0

    # -- rails -------------------------------------------------------------

    def rail_status(self, value: float) -> str | None:
        low = self.cfg.get("rail_low")
        high = self.cfg.get("rail_high")
        if low is not None and value < low:
            return f"below rail {low:g} {self.cfg['unit']}"
        if high is not None and value > high:
            return f"above rail {high:g} {self.cfg['unit']}"
        return None

    def plausibility(self, value: float) -> str | None:
        return implausible_reason(self.analyte, value)

    # -- drift -------------------------------------------------------------

    def _side(self, deviation_pct: float) -> int:
        """-1 below baseline, +1 above, 0 exactly on it."""
        if deviation_pct > 0:
            return 1
        if deviation_pct < 0:
            return -1
        return 0

    def _harmful(self, side: int) -> bool:
        if side == 0:
            return False
        if self.direction == "low_bad":
            return side < 0
        if self.direction == "high_bad":
            return side > 0
        return True          # both_bad: either side counts

    # -- processing --------------------------------------------------------

    def process(self, timestamp: datetime, value: float) -> dict:
        if not isfinite(value):
            raise ValueError("Reading must be finite.")
        transformed = directed_value(self.direction, self.std, value)
        out = self.engine.process(timestamp, transformed)

        # PID.py reports the deviation of the transformed value, which is not
        # meaningful to a clinician. Recompute the human-facing numbers.
        deviation = value - self.std
        deviation_pct = deviation / self.std
        error_rcv = max(out["error"], 0.0) / self.rcv

        side = self._side(deviation_pct)
        if side == 0:
            self.drift_run = 0
        elif side == self._last_side:
            self.drift_run += 1
        else:
            self.drift_run = 1
        self._last_side = side
        drift = (self._harmful(side)
                 and self.drift_run >= self.drift_threshold
                 # Tolerance only absorbs float error at the boundary: a
                 # reading computed to 0.4999999 must behave like 0.5.
                 and error_rcv >= self.drift_floor_rcv - 1e-9)

        rail = self.rail_status(value)
        implausible = self.plausibility(value)
        # A single implausible value is treated as real until repeated: a
        # platelet count of 25 x10^3/uL is a genuine emergency, not a typo.
        # Only the panel can decide whether the *sample* is suspect, because
        # that judgement needs the other analytes. See Panel.summarise.
        escalate = bool(rail) or error_rcv >= 3.0

        return {
            "analyte": self.analyte,
            "label": self.cfg["label"],
            "value": value,
            "std": self.std,
            "unit": self.cfg["unit"],
            "direction": self.direction,
            "deviation": round(deviation, 3),
            "deviation_pct": round(deviation_pct * 100, 1),
            "error_rcv": error_rcv,
            "intervention_status": out["intervention_status"],
            "urgency_score": None,   # control_loop reports a level, not a score
            "urgency_level": out["urgency_level"],
            "accumulated_error": round(out["accumulated_error"], 3),
            "deterioration_rate": round(out["error_rate"], 4),
            "rail": rail,
            "implausible": implausible,
            "escalate": escalate,
            "rcv": self.rcv,
            "drift_run": self.drift_run,
            "drift": drift,
        }


# ============================================================================
# PANEL
# ============================================================================

class Panel:
    """A set of analyte controllers sharing one baseline sample."""

    def __init__(self, baseline: dict[str, float | None], horizon: str = "short"):
        self.last_timestamp: datetime | None = None
        self.history: dict[str, list[tuple[datetime, float]]] = {}
        self.controllers: dict[str, AnalyteController] = {}
        for name, value in baseline.items():
            if name in ANALYTES and value is not None and isfinite(value) and value > 0:
                self.controllers[name] = AnalyteController(name, value, horizon)

    def process(self, timestamp: datetime, readings: dict[str, float | None]) -> list[dict]:
        valid = [
            (self.controllers[name], value)
            for name, value in readings.items()
            if name in self.controllers and value is not None and isfinite(value)
        ]
        # Check the entire sample before advancing any controller.
        # control_loop.py has no elapsed_days(), so the ordering check is done
        # here against the rate tracker's own previous timestamp.
        for ctrl, _ in valid:
            prev = ctrl.engine.deterioration.previous_time
            if prev is not None and (timestamp - prev).total_seconds() <= 0:
                raise ValueError(
                    "Timestamp must be later than previous measurement."
                )
        out = [ctrl.process(timestamp, value) for ctrl, value in valid]
        if valid:
            self.last_timestamp = timestamp
            for ctrl, value in valid:
                self.history.setdefault(ctrl.analyte, []).append((timestamp, value))
        return out

    def staleness(self, now: datetime) -> float | None:
        """Days since the last reading was ingested, or None if never."""
        if self.last_timestamp is None:
            return None
        days = (now - self.last_timestamp).total_seconds() / 86400
        return days if days >= 0 else None

    @staticmethod
    def summarise(results: list[dict], stale_days: float | None = None,
                  stale_after_days: float = 30.0) -> dict:
        # Pathway aggregation: max error within the panel, plus a count of
        # aligned deviations. Deliberately not a sum: summing lets one extreme
        # analyte dominate everything, and hides how many signals agree.
        stale = stale_days is not None and stale_days > stale_after_days
        if not results:
            return {"status": "NO_DATA", "max_error_rcv": 0.0, "aligned": 0,
                    "escalate": False, "implausible": [], "sample_suspect": False,
                    "rails": [], "drift": [], "stale_days": stale_days, "stale": stale}

        max_err = max(r["error_rcv"] for r in results)
        aligned = sum(1 for r in results if r["error_rcv"] >= 1.0)
        rails = [f"{r['label']}: {r['rail']}" for r in results if r["rail"]]
        implausible = [f"{r['label']}: {r['implausible']}" for r in results if r["implausible"]]

        # Corroboration: two or more implausible analytes in the same sample
        # point at a bad record. One implausible analyte points at a sick
        # patient until a repeat says otherwise.
        sample_suspect = len(implausible) >= 2

        # A suspect sample can still contain a reading that independently
        # qualifies for escalation and passes its own plausibility check.
        escalate = any(
            r["escalate"] and (not sample_suspect or not r["implausible"])
            for r in results
        )
        drift = [f"{r['label']}: {r['drift_run']} consecutive readings on the same "
                 f"side, now {r['error_rcv']:.2f} RCV from baseline"
                 for r in results if r.get("drift")]

        if escalate:
            status = "ESCALATE"
        elif stale:
            status = "STALE"
        elif sample_suspect:
            status = "RECHECK_SAMPLE"
        elif max_err >= 2.0 or aligned >= 3:
            status = "ACTION_REVIEW"
        elif max_err >= 1.0 or drift:
            status = "WATCH"
        else:
            status = "NORMAL"

        if implausible and status in ("NORMAL", "WATCH"):
            status = "RECHECK_SAMPLE"

        return {
            "status": status,
            "implausible": implausible,
            "max_error_rcv": round(max_err, 2),
            "aligned": aligned,
            "escalate": escalate,
            "sample_suspect": sample_suspect,
            "rails": rails,
            "drift": drift,
            "stale_days": stale_days,
            "stale": stale,
        }



    # -- six outputs -------------------------------------------------------

    def _slope(self, analyte: str) -> float | None:
        """Least-squares slope of the stored values, in units per day."""
        series = self.history.get(analyte, [])
        if len(series) < 3:
            return None
        t0 = series[0][0]
        xs = [(t - t0).total_seconds() / 86400 for t, _ in series]
        ys = [v for _, v in series]
        n = len(xs)
        mx = sum(xs) / n
        my = sum(ys) / n
        denom = sum((x - mx) ** 2 for x in xs)
        if denom == 0:
            return None
        return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom

    def _forecast(self, results: list[dict]) -> dict | None:
        if not results:
            return None
        # Watch the analyte that is furthest from its own baseline.
        worst = max(results, key=lambda r: r["error_rcv"])
        slope = self._slope(worst["analyte"])
        if slope is None:
            return None
        ctrl = self.controllers[worst["analyte"]]
        rail = ctrl.cfg.get("rail_low") if ctrl.direction == "low_bad" else ctrl.cfg.get("rail_high")
        current = worst["value"]
        toward = rail is not None and ((slope < 0 and rail < current) or (slope > 0 and rail > current))
        days = None
        if toward and slope != 0:
            days = (rail - current) / slope
        beyond = days is not None and days > FORECAST_HORIZON_DAYS
        return {
            "analyte": worst["analyte"],
            "label": worst["label"],
            "slope_per_day": round(slope, 4),
            "current": current,
            "rail": rail,
            "days_to_rail": None if (days is None or beyond) else round(days, 1),
            "beyond_horizon": bool(beyond),
            "toward_rail": bool(toward),
        }

    def _attribution(self, results: list[dict], events, summary: dict) -> dict:
        out = {"onset": None, "event": None, "gap_days": None, "age_days": None}
        flagged = [r for r in results if r["error_rcv"] >= 1.0]
        if not flagged:
            return out
        worst = max(flagged, key=lambda r: r["error_rcv"])
        ctrl = self.controllers.get(worst["analyte"])
        series = self.history.get(worst["analyte"], [])
        if ctrl is None or not series:
            return out
        onset = None
        for ts, value in series:
            err = abs(value - ctrl.std) / ctrl.std / ctrl.rcv
            if err >= 1.0:
                onset = ts
                break
        if onset is None:
            return out
        out["onset"] = onset.strftime("%Y-%m-%d")
        out["age_days"] = (series[-1][0] - onset).days
        if events:
            prior = [(d, lab) for d, lab in events if d <= onset]
            if prior:
                d, lab = max(prior, key=lambda x: x[0])
                gap = (onset - d).days
                if gap <= EVENT_WINDOW_DAYS:
                    out["event"] = lab
                    out["gap_days"] = gap
        return out

    def _next_tests(self, decisive, undetermined, results) -> list[str]:
        out: list[str] = []
        for p in decisive:
            for t in p["next"]:
                if t not in out:
                    out.append(t)
        return out

    @staticmethod
    def _package(crew, summary, results, chosen, forecast, attribution, next_test) -> str:
        lines = ["CREW MEDICAL HANDOVER", "=====================",
                 f"Crew: {crew}",
                 f"Status: {summary['status']}",
                 f"Max error: {summary['max_error_rcv']:.2f} RCV, "
                 f"aligned inputs {summary['aligned']}"]
        if chosen:
            lines.append(f"Pattern: {chosen['title']} "
                         f"(confidence {chosen['confidence'] * 100:.0f}%, "
                         f"{chosen['hits']}/{len(chosen['present'])} present criteria)")
        else:
            lines.append("Pattern: none")
        if attribution.get("onset"):
            tail = attribution.get("event") or "unattributed"
            lines.append(f"Onset: {attribution['onset']} - {tail}")
        else:
            lines.append("Onset: not attributable to a single analyte")

        if chosen:
            lines += ["", "Pattern evidence", "----------------"]
            for d in chosen["detail"]:
                r = next((x for x in results if x["analyte"] == d["analyte"]), None)
                if r is None or d["got"] is None:
                    lines.append(f"{d['analyte']}: not measured")
                else:
                    lines.append(f"{r['label']}: {r['value']} {r['unit']} "
                                 f"({r['deviation_pct']:+.1f}%) - {d['got']} as expected"
                                 if d["ok"] else
                                 f"{r['label']}: {r['value']} {r['unit']} "
                                 f"({r['deviation_pct']:+.1f}%) - {d['got']}, wanted {d['want']}")

        flagged = [r for r in results if r["error_rcv"] >= 1.0]
        lines += ["", "Flagged values", "--------------"]
        if flagged:
            for r in sorted(flagged, key=lambda x: -x["error_rcv"]):
                lines.append(f"{r['label']}: {r['value']} {r['unit']} "
                             f"(baseline {r['std']}, {r['deviation_pct']:+.1f}%, "
                             f"{r['error_rcv']:.2f} RCV)")
        else:
            lines.append("none")

        missing = [a for a in (chosen["missing"] if chosen else [])]
        lines += ["", "Not available", "-------------",
                  ", ".join(missing) if missing else "none"]
        lines += ["", "Requested action", "----------------"]
        lines += next_test if next_test else ["Continue monitoring; repeat in 24 h."]
        return "\n".join(lines)

    def outputs(self, results: list[dict], summary: dict, crew: str = "CREW",
                events=None, symptoms=None) -> dict:
        """The six decision outputs: mechanism, forecast, contraindication,
        attribution, next tests, handover package."""
        by_analyte = {r["analyte"]: r for r in results}
        evaluated = [evaluate_pattern(p, by_analyte) for p in PATTERNS]
        # Tie-break on how much of the pattern is actually verifiable: a pattern
        # that needs three analytes we cannot measure is weaker evidence than one
        # that matched every analyte it asked for.
        decisive = sorted([e for e in evaluated if e["qualifies"]],
                          key=lambda e: (-e["hits"], -e["confidence"],
                                         len(e["missing"]), e["id"]))
        undetermined = sorted(
            [e for e in evaluated if not e["qualifies"] and e["missing"] and e["hits"] >= 1],
            key=lambda e: (-e["hits"], -e["confidence"], len(e["missing"]), e["id"]))[:2]
        chosen = decisive[0] if decisive else None
        forecast = self._forecast(results)
        attribution = self._attribution(results, events, summary)
        next_test = self._next_tests(decisive, undetermined, results)
        avoid: list[str] = []
        for p in decisive:
            for a in p["avoid"]:
                if a not in avoid:
                    avoid.append(a)
        return {
            "status": summary["status"],
            "mechanism": {"pattern": chosen, "decisive": decisive,
                          "undetermined": undetermined},
            "forecast": forecast,
            "contraindication": {"avoid": avoid},
            "attribution": attribution,
            "next_test": next_test,
            "package": self._package(crew, summary, results, chosen,
                                     forecast, attribution, next_test),
        }


# ============================================================================
# DEMO — real NASA data (OSDR OSD-569 CBC, Inspiration4)
# ============================================================================

CBC_PATHS = [
    Path(__file__).parent / "data" / "OSD-569_CBC.csv",
    Path("/Users/guozitao/Documents/deepseek-harness/default-workspace/nasa-space-app/research/osdr_cbc/OSD-569_CBC.csv"),
]

# OSD-569 reports nominal days before launch (L) and after return (R).
# Use the documented three-day mission to put both on one launch-relative clock.
DEMO_DAYS = {"L-92": -92, "L-44": -44, "L-3": -3, "R+1": 4, "R+45": 48,
             "R+82": 85, "R+194": 197}
TIMEPOINT_ORDER = list(DEMO_DAYS)


def demo_timestamp(timepoint: str) -> datetime:
    return datetime(2026, 1, 1, 12, 0) + timedelta(days=DEMO_DAYS[timepoint])


def load_cbc(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            sample = row["Sample Name"]
            parts = sample.split("_")
            tp = parts[-2] if parts[-1] == "cbc" else parts[-1]
            if tp not in DEMO_DAYS:
                continue
            rows.append({
                "crew": sample[:4],
                "timepoint": tp,
                "hemoglobin": float(row["hemoglobin_value_percent"] or "nan"),
                "hematocrit": float(row["hematocrit_value_percent"] or "nan"),
                "wbc": float(row["white_blood_cell_count_value_thousand_per_microliter"] or "nan"),
                "platelets": float(row["platelet_count_value_thousand_per_microliter"] or "nan"),
                "rdw": float(row["rdw_value_percent"] or "nan"),
                "mch": float(row["mch_value_picogram"] or "nan"),
            })
    return rows


def demo() -> None:
    path = next((p for p in CBC_PATHS if p.exists()), None)
    if path is None:
        raise SystemExit("CBC dataset not found; place OSD-569_CBC.csv in ./data/")

    rows = load_cbc(path)
    by_crew: dict[str, list[dict]] = {}
    for r in rows:
        by_crew.setdefault(r["crew"], []).append(r)

    print(f"source: {path}")
    print(f"crew: {len(by_crew)}  samples: {len(rows)}\n")

    for crew, crew_rows in sorted(by_crew.items()):
        crew_rows.sort(key=lambda r: DEMO_DAYS[r["timepoint"]])

        # Baseline = median of the pre-flight window excluding L-3.
        pre = [r for r in crew_rows if r["timepoint"] in ("L-92", "L-44")]
        if not pre:
            continue
        baseline = {}
        for key in ("hemoglobin", "hematocrit", "wbc", "platelets", "rdw", "mch"):
            vals = sorted(
                r[key] for r in pre
                if isfinite(r[key]) and r[key] > 0 and implausible_reason(key, r[key]) is None
            )
            if vals:
                baseline[key] = median(vals)

        panel = Panel(baseline, horizon="long")
        print(f"=== {crew} ===")
        print("  baseline (L-92/L-44 median): "
              + ", ".join(f"{k}={v:.2f}" for k, v in baseline.items()))

        for r in crew_rows:
            ts = demo_timestamp(r["timepoint"])
            results = panel.process(ts, {k: r[k] for k in baseline})
            summary = Panel.summarise(results)
            worst = max(results, key=lambda x: x["error_rcv"], default=None)
            worst_text = f"{worst['label']} ({worst['deviation_pct']:+.1f}%)" if worst else "—"
            note = ""
            if summary["sample_suspect"]:
                note = "  <- sample suspect: " + "; ".join(summary["implausible"][:2])
            elif summary["implausible"]:
                note = "  <- flagged reading: " + summary["implausible"][0]
            print(f"  {r['timepoint']:<6} {summary['status']:<15} "
                  f"max={summary['max_error_rcv']:>5.2f} RCV  "
                  f"aligned={summary['aligned']}  worst={worst_text}{note}")
        print()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="run on real OSD-569 data")
    args = ap.parse_args()
    if args.demo:
        demo()
    else:
        print(__doc__)

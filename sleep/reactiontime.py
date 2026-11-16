"""Offline reaction-time button test and descriptive control-loop analysis."""
import argparse
from datetime import datetime, timedelta
import json
import math
from pathlib import Path
import random
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from control_loop import AccumulatedError, Deviation, DeteriorationRate, Error


def positive(value, label):
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a positive finite number.")
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a positive finite number.") from None
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"{label} must be a positive finite number.")
    return result


def process_reaction_times(days, reaction_times, baseline_rt):
    """Analyze daily session means; positive error means slower than baseline.

    Sign is reversed from the shared reference-minus-current convention because
    higher latency means slower responding. No status thresholds are assumed.
    """
    baseline = positive(baseline_rt, "Baseline")
    days, values = list(days), list(reaction_times)
    if not days or len(days) != len(values):
        raise ValueError("Provide matching, nonempty days and reaction times.")
    days = [positive(day, "Mission day") for day in days]
    if any(not day.is_integer() for day in days):
        raise ValueError("Mission days must be whole numbers.")
    if any(b <= a for a, b in zip(days, days[1:])):
        raise ValueError("Mission days must increase without duplicates.")
    values = [positive(value, "Reaction time") for value in values]
    integral, rate = AccumulatedError(), DeteriorationRate()
    rows = []
    for index, (day, value) in enumerate(zip(days, values)):
        try:
            timestamp = datetime(2000, 1, 1) + timedelta(days=day - days[0])
        except OverflowError:
            raise ValueError("Mission day range is too large.") from None
        deviation = -Deviation(baseline, value).calculate()
        error = -Error(baseline, value).calculate()
        accumulated = integral.calculate(timestamp, error)
        derivative = rate.calculate(timestamp, error)
        rows.append({"mission_day": int(day), "reaction_time_ms": value,
                     "deviation": deviation, "error": error,
                     "deviation_percent": error * 100,
                     "accumulated_error": accumulated,
                     "error_rate": None if index == 0 else derivative,
                     "change_from_previous_ms": None if index == 0 else value - values[index - 1]})
    return rows


class ReactionTrial:
    """Measurement gate: clicks before the signal never become valid scores."""
    def __init__(self):
        self.state = "idle"
        self.started = None

    def wait(self):
        self.state, self.started = "waiting", None

    def signal(self, now):
        if self.state == "waiting":
            self.state, self.started = "ready", now

    def press(self, now):
        if self.state == "waiting":
            self.cancel()
            return "early", None
        if self.state == "ready":
            milliseconds = (now - self.started) * 1000
            self.cancel()
            if milliseconds > 0:
                return "valid", milliseconds
        return "ignored", None

    def cancel(self):
        self.state, self.started = "idle", None


def load_results(path):
    if not path.exists():
        return {"baseline": None, "sessions": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    baseline = data["baseline"]
    if baseline is not None:
        positive(baseline["mean_ms"], "Saved baseline")
    sessions = data["sessions"]
    if not isinstance(sessions, list) or (sessions and baseline is None):
        raise ValueError("Invalid saved sessions.")
    if sessions:
        process_reaction_times([s["day"] for s in sessions], [s["mean_ms"] for s in sessions], baseline["mean_ms"])
    return data


def save_results(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, allow_nan=False, indent=2), encoding="utf-8")
    temporary.replace(path)


class ReactionTimeApp:
    TRIALS = 5

    def __init__(self, root, path):
        import tkinter as tk
        from tkinter import messagebox
        self.tk, self.messagebox, self.root, self.path = tk, messagebox, root, path
        self.data = load_results(path)
        self.trial, self.pending, self.samples, self.mode = ReactionTrial(), None, [], None
        self.early, self.timeouts = 0, 0
        root.title("Reaction Time — Offline Test")
        root.geometry("780x660")
        root.minsize(640, 560)
        panel = tk.Frame(root, padx=24, pady=18)
        panel.pack(fill="both", expand=True)
        tk.Label(panel, text="Reaction-time test", font=("Segoe UI", 23, "bold")).pack(anchor="w")
        tk.Label(panel, text="Wait for GREEN, then click the large button. Five valid trials per session.\nUse the same device and input method for comparisons. No network is used.", justify="left").pack(anchor="w", pady=8)
        self.reference = tk.StringVar()
        tk.Label(panel, textvariable=self.reference).pack(anchor="w")
        toolbar = tk.Frame(panel)
        toolbar.pack(fill="x", pady=12)
        self.baseline_button = tk.Button(toolbar, text="1. Measure baseline", command=lambda: self.begin("baseline"))
        self.baseline_button.pack(side="left")
        tk.Label(toolbar, text="Mission day:").pack(side="left", padx=(18, 4))
        self.day = tk.StringVar(value=str(self.data["sessions"][-1]["day"] + 1 if self.data["sessions"] else 1))
        tk.Entry(toolbar, textvariable=self.day, width=7).pack(side="left")
        self.test_button = tk.Button(toolbar, text="2. Test this day", command=lambda: self.begin("session"))
        self.test_button.pack(side="left", padx=10)
        self.target = tk.Button(panel, text="Choose baseline or daily test above", font=("Segoe UI", 20, "bold"), height=5, bg="#dce2e8", command=self.respond)
        self.target.bind("<ButtonPress-1>", lambda event: self.respond())
        self.target.pack(fill="x", pady=8)
        self.status = tk.StringVar(value="The baseline will be measured from your own clicks.")
        tk.Label(panel, textvariable=self.status, wraplength=700, justify="left").pack(anchor="w", pady=6)
        actions = tk.Frame(panel)
        actions.pack(fill="x")
        self.next_button = tk.Button(actions, text="Next trial", command=self.next_trial, state="disabled")
        self.next_button.pack(side="left")
        tk.Button(actions, text="Cancel test", command=self.cancel).pack(side="left", padx=10)
        self.output = tk.Text(panel, height=10, wrap="word", font=("Consolas", 10))
        self.output.pack(fill="both", expand=True, pady=12)
        tk.Label(panel, text="Descriptive practice tool, not a validated vigilance or medical test. Device latency affects scores.", wraplength=700).pack(anchor="w")
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.bind("<FocusOut>", lambda event: root.after_idle(self.check_focus))
        self.refresh()

    def refresh(self):
        baseline = self.data["baseline"]
        self.reference.set(f"Measured baseline mean: {baseline['mean_ms']:.1f} ms" if baseline else "No baseline recorded yet.")
        self.test_button.configure(state="normal" if baseline and self.mode is None else "disabled")
        self.baseline_button.configure(state="normal" if self.mode is None else "disabled")
        lines = [f"Local results: {self.path}"]
        if baseline and self.data["sessions"]:
            sessions = self.data["sessions"]
            rows = process_reaction_times([s["day"] for s in sessions], [s["mean_ms"] for s in sessions], baseline["mean_ms"])
            lines.append("Day | Mean ms | Difference ms | Difference % | Rate pp/day | Integral fraction-days")
            for row in rows:
                derivative = "N/A" if row["error_rate"] is None else f"{row['error_rate'] * 100:+.2f}"
                lines.append(f"{row['mission_day']:3} | {row['reaction_time_ms']:7.1f} | {row['deviation']:+13.1f} | {row['deviation_percent']:+12.2f} | {derivative:>11} | {row['accumulated_error']:+.3f}")
            lines.append("Positive difference = slower than baseline; negative = faster.\nIntegral starts at the first recorded day; signed deviations can cancel. It is not a damage score.")
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", "\n".join(lines))
        self.output.configure(state="disabled")

    def begin(self, mode):
        if self.mode is not None:
            return
        if mode == "baseline" and self.data["baseline"] is not None:
            self.messagebox.showinfo("Baseline preserved", "The baseline is fixed for this result file. Use --data with a new filename to start a new baseline.")
            return
        if mode == "session":
            try:
                day = positive(self.day.get(), "Mission day")
                if not day.is_integer() or (self.data["sessions"] and day <= self.data["sessions"][-1]["day"]):
                    raise ValueError("Use a whole-number mission day later than the last saved day.")
                self.session_day = int(day)
            except ValueError as error:
                self.messagebox.showerror("Check mission day", str(error))
                return
        self.mode, self.samples, self.early, self.timeouts = mode, [], 0, 0
        self.refresh()
        self.next_trial()

    def stop_timer(self):
        if self.pending is not None:
            self.root.after_cancel(self.pending)
            self.pending = None

    def next_trial(self):
        if self.mode is None:
            return
        self.stop_timer()
        self.trial.wait()
        self.next_button.configure(state="disabled")
        self.target.configure(text="WAIT… do not click yet", bg="#f5cf86")
        self.status.set(f"Trial {len(self.samples)+1}/{self.TRIALS}. Early clicks: {self.early}; timeouts: {self.timeouts}.")
        self.pending = self.root.after(random.randint(1500, 3500), self.signal)

    def signal(self):
        self.pending = None
        self.target.configure(text="CLICK NOW", bg="#70d5ad")
        self.root.update_idletasks()
        self.trial.signal(time.perf_counter())
        self.pending = self.root.after(5000, self.timeout)

    def respond(self):
        outcome, milliseconds = self.trial.press(time.perf_counter())
        if outcome == "ignored":
            return
        self.stop_timer()
        if outcome == "early":
            self.early += 1
            self.target.configure(text="Too early — not counted", bg="#f5cf86")
        else:
            self.samples.append(milliseconds)
            self.target.configure(text=f"{milliseconds:.1f} ms", bg="#dce2e8")
        if len(self.samples) == self.TRIALS:
            self.finish()
        else:
            self.status.set(f"{len(self.samples)}/{self.TRIALS} valid trials. Click Next trial when ready.")
            self.next_button.configure(state="normal")

    def timeout(self):
        self.pending = None
        self.trial.cancel()
        self.timeouts += 1
        self.target.configure(text="No response — not counted", bg="#f5cf86")
        self.status.set("The 5-second input window expired. This is a test timeout, not a clinical lapse threshold.")
        self.next_button.configure(state="normal")

    def finish(self):
        record = {"trials_ms": list(self.samples), "mean_ms": statistics.mean(self.samples), "median_ms": statistics.median(self.samples), "early_clicks": self.early, "timeouts": self.timeouts, "recorded_at": datetime.now().isoformat(timespec="seconds")}
        candidate = json.loads(json.dumps(self.data))
        if self.mode == "baseline":
            candidate["baseline"] = record
        else:
            record["day"] = self.session_day
            candidate["sessions"].append(record)
        try:
            save_results(self.path, candidate)
        except OSError as error:
            self.status.set(f"Could not save: {error}. Results have not been recorded. Start again after fixing the file location.")
        else:
            self.data = candidate
            self.status.set(f"Saved {self.TRIALS} valid trials. Mean {record['mean_ms']:.1f} ms; median {record['median_ms']:.1f} ms. Early clicks {self.early}; timeouts {self.timeouts}.")
            if "day" in record:
                self.day.set(str(record["day"] + 1))
        self.mode = None
        self.refresh()

    def cancel(self):
        self.stop_timer()
        self.trial.cancel()
        self.mode, self.samples = None, []
        self.next_button.configure(state="disabled")
        self.target.configure(text="Choose baseline or daily test above", bg="#dce2e8")
        self.status.set("Test cancelled. Partial trials were not saved.")
        self.refresh()

    def check_focus(self):
        if self.mode is not None and self.root.focus_get() is None:
            self.cancel()
            self.status.set("Test cancelled because the window lost focus. Restart when ready.")

    def close(self):
        self.stop_timer()
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path(__file__).with_name("reactiontime_results.json"))
    args = parser.parse_args()
    import tkinter as tk
    root = tk.Tk()
    try:
        ReactionTimeApp(root, args.data.resolve())
    except (ValueError, KeyError, TypeError, OSError) as error:
        from tkinter import messagebox
        messagebox.showerror("Cannot load results", f"Existing data was not overwritten.\n{error}")
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()

# Offline reaction-time test

Run from the repository root:

```sh
python sleep/reactiontime.py
```

1. Choose **Measure baseline**. Wait for the large button to turn green, then click it. Choose **Next trial** between attempts. Five valid clicks establish your personal baseline mean.
2. Enter an actual mission day and choose **Test this day**. Complete five more valid trials. The session mean is compared with your fixed baseline.
3. Repeat on a later mission day to see rate and accumulated deviation. Saved days must increase. Raw trials, mean, median, early-click count, timeouts and daily results stay in `sleep/reactiontime_results.json`.

Early clicks are discarded. A response window expires after five seconds; this is an input timeout, not a validated vigilance-lapse threshold. Losing window focus cancels the partial session; partial results are not saved. Keep device, input method and conditions consistent. Timing uses a monotonic high-resolution clock, but display/input latency remains part of the measurement. This is a practice prototype, not a standardized PVT or a diagnostic instrument.

`process_reaction_times(days, reaction_times, baseline_rt)` accepts session means in milliseconds. It uses the unchanged shared `Deviation`, `Error`, `AccumulatedError`, and `DeteriorationRate` classes. The shared sign is reversed so **positive deviation means slower than baseline**. Error is `(current_ms - baseline_ms) / baseline_ms`. Table rates are percentage points per day; negative rate means responding became faster. The first rate is unavailable. Signed integration covers only observed days and uses actual intervals; it is neither cumulative sleep debt nor a damage measure. No unvalidated status/urgency thresholds are applied.

To start a separate baseline/person without replacing existing data:

```sh
python sleep/reactiontime.py --data sleep/my_other_test.json
```

The test uses Python's installed Tkinter and no external assets, server or network calls. No packages need downloading on this computer. It does not update Unity or the website. Do not commit personal test JSON files; share only source code.

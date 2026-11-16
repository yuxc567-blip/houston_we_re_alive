# Sleep model audit and evidence mapping

Reviewed 2026-11-15 against the user-supplied NASA **Risk of Performance Decrements and Adverse Health Outcomes Resulting from Sleep Loss, Circadian Desynchronization, and Work Overload**, approved for public release April 11, 2016. This is a historical evidence report, not proof of current mission clinical policy.

Source PDF SHA-256: `71e146207753408e5b7e3734760f13811429b3516635d0166b322598c03b1b6f`.

Official report: https://humanresearchroadmap.nasa.gov/Evidence/reports/Sleep.pdf
Adult reference consensus: https://aasm.org/resources/pdf/adultsleepdurationconsensus.pdf

## What the audit found and changed

Before this change, `sleep_duration.py` and `reactiontime.py` used the shared deviation, relative-error, finite-difference derivative and trapezoidal-integral classes. The dashboard did not fit linear regression or produce status, urgency, or preventive guidance. The generic `Urgency` class's linear extrapolation was not a fitted regression.

The user explicitly selected the existing controller's example thresholds as **unvalidated prototype settings**. `sleep/monitoring.py` now implements the fitted models and review rules; `dashboard.py` includes them in `/api/state` and `/api/export`; the web interface displays them. The original raw calculation functions and shared `control_loop.py` are preserved.

## Calculations and model definitions

- Sleep signed error: `(reference_hours - recorded_hours) / reference_hours`.
- Reaction signed error: `(session_mean_ms - personal_baseline_ms) / personal_baseline_ms`.
- Interval derivative: `(e_i - e_previous) / actual_elapsed_days`, fractions/day. UI multiplies by 100 to display percentage points/day. First derivative is unavailable.
- Signed integral: trapezoidal integration of observed errors over actual mission days. It starts at the first recorded point; positive and negative areas can cancel. It is not total sleep debt, cumulative tissue damage, or an independently validated risk score.
- Trend: ordinary least-squares regression with intercept, `error = intercept + slope * mission_day`, using all available observations. At least three points with predictor variation are required. Report n, slope, intercept, in-sample R² and RMSE. Flat responses have undefined R². The fitted slope estimates error change per day; it is distinct from the latest interval derivative.
- Extrapolation: evaluate the fitted line seven days after the latest observation. This is an unconstrained mathematical extrapolation, not a validated prognosis. It can become physiologically implausible. No probability/confidence in an individual's diagnosis is inferred from R².
- Optional association: OLS of reaction error against sleep error on matching mission days, with at least three paired observations and varying sleep error. This is descriptive and confounded; it is not causation and is not an input to urgency. A statistical model of urgency itself would need defined outcomes and independent validation; that is not claimed here.

## Explicit prototype rules

These numbers come from existing project examples and user approval, **not from the NASA report**:

- Current adverse-direction error below 5%: NORMAL; at least 5%: WATCH OUT; at least 10%: ACTION NEEDED.
- Only sleep deficit and reaction slowdown are adverse directions here. Above-reference sleep or faster responses are not automatically adverse simply because their absolute deviation is large. NORMAL means below demo cutoffs, not medically healthy.
- Urgency: LOW/MEDIUM/HIGH from current status plus the largest positive rate among the interval derivative and fitted trend. At least 2 percentage points/day raises MEDIUM; at least 5 raises HIGH. The shared `Urgency` class is used with its built-in forecast disabled.
- With at least three points and a positive fitted slope, the seven-day fitted extrapolation can also raise MEDIUM at 5% or HIGH at 10%. This forecast escalation is a prototype design choice.
- A negative derivative/slope is not escalated just for its magnitude. Current adverse deviation can remain elevated even when improving.
- Signed integral is displayed but does not escalate labels: no cutoff was established in the attachment.
- Missing measurements are NOT ASSESSED. A current-point-only label is possible, but derivative and regression limitations are explicit.

## Healthy-reference context

NASA p. 7 discusses large individual differences in sleep need. The AASM/SRS consensus supports at least seven hours regularly for adults aged 18–60, not a universal eight-hour disease threshold. That adult guidance is not automatically applicable to children/adolescents or a personalized prescription. The dashboard's user-selected sleep reference remains eight hours by default. Its 5%/10% labels are separate from the adult duration recommendation. A self-measured five-click baseline is a personal practice reference, not independently verified healthy performance.

NASA pp. 24–26 discusses validated PVT protocols lasting minutes, including PVT-B and PVT-A; our five-click test is not interchangeable with those protocols. Do not import their lapse/decision thresholds into this test or infer fitness for critical duty.

## Research-informed options and their limits

| Option | Evidence location | Application and limitation |
| --- | --- | --- |
| Protect sleep opportunity; review workload/schedule | NASA pp. 24, 50–52 | Review factors displacing planned sleep. Operational/clinical planning is individualized. |
| Review circadian schedule and lighting | NASA pp. 24, 48–49 | Light timing influences phase/alertness. Ground and field findings do not define a personalized light regimen from these data. |
| Consider planned naps when sleep is constrained | NASA pp. 30–31, 50 | Potential benefits depend on timing, total sleep opportunity and sleep inertia. No universal nap duration is generated. |
| Plan recovery and recheck comparable measurements | NASA pp. 25, 50–51 | A single recovery opportunity may be insufficient in restriction studies. A faster brief practice test is not proof of full recovery. |
| Medication/stimulant strategies require individual review | NASA pp. 23–24, 45–48 | Research on caffeine, melatonin and hypnotics is not a prescription. No dose, timing or medication selection is automated. |

The page links directly to the report's relevant pages and distinguishes educational research options from current clinical or mission procedures. Recommendations are prompts to review the pattern, not proof that a countermeasure will prevent a condition.

## Validation

Automated checks cover known OLS coefficients on actual irregular days, insufficient/constant/invalid predictors, threshold equality, derivative direction, improvement without false escalation, exploratory forecast escalation, separate same-day association, missing data, HTTP integration and persistence. These checks validate implementation against the specified prototype rules; they are not clinical validation.

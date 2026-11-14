# FICTIONAL DATA — software demonstration only
personal_baselines = {
    "heart_rate": 70.0,       # bpm
    "systolic_bp": 120.0,    # mmHg
    "diastolic_bp": 80.0,    # mmHg
    "filtered_qrs": 85.0,    # ms
}

demo_thresholds = {
    "warning": 0.15,
    "critical": 0.30,
    "warning_rate": 0.02,
    "critical_rate": 0.05,
    "prediction_days": 7,
}

daily_readings = [
    # Day 1
    {
        "heart_rate": 65.0,
        "systolic_bp": 115.0,
        "diastolic_bp": 75.0,
        "filtered_qrs": 90.0,
    },
    # Day 2
    {
        "heart_rate": 66.0,
        "systolic_bp": 116.0,
        "diastolic_bp": 76.0,
        "filtered_qrs": 91.0,
    },
    # Day 3
    {
        "heart_rate": 80.0,
        "systolic_bp": 140.0,
        "diastolic_bp": 95.0,
        "filtered_qrs": 100.0,
    },
]
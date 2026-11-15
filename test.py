from control_loop import *
from datetime import datetime

# 1. Instantiate the controller once with your desired thresholds and standard value
controller = HealthController(
    std=100.0,
    warning=0.05,        # 5% warning limit
    critical=0.10,       # 10% critical limit
    warning_rate=0.01,
    critical_rate=0.02,
    prediction_days=7
)

# 2. Whenever a new data point comes in with a timestamp, call process()
timestamp = datetime(2026, 6, 6, 12, 0, 0)
current_value = 92.5

result = controller.process(timestamp, current_value)

# 3. Access everything you need right from the returned dictionary
print(result)

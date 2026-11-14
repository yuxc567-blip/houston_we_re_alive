from control_loop import *
std_eye_thickness = 19.4

bone_controller = HealthController(
    std=...,
    warning=...,
    critical=...,
    warning_rate=...,
    critical_rate=...
)

eye_controller = HealthController(
    std=...,
    warning=...,
    critical=...,
    warning_rate=...,
    critical_rate=...
)

x = pd.read("data.csv")
import sys
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from control_loop import HealthController


WARNING_DEVIATION = 0.05
CRITICAL_DEVIATION = 0.10
WARNING_RATE = 0.02
CRITICAL_RATE = 0.05

def plot_reaction_time(days, reaction_times, baseline_rt, lapses):
	"""Plot reaction-time data and refresh as values are appended to the lists."""
	if not (len(days) == len(reaction_times) == len(lapses)):
		raise ValueError("days, reaction_times, and lapses must have the same length")

	fig, rt_ax = plt.subplots()
	lapse_ax = rt_ax.twinx()

	rt_line, = rt_ax.plot(days, reaction_times, "b-", label="Average reaction time")
	baseline_line = rt_ax.axhline(
		baseline_rt, color="green", linestyle="--", label="Baseline reaction time"
	)
	lapse_line, = lapse_ax.plot(days, lapses, "r-", label="Attention lapses")

	rt_ax.set_title("Astronaut Reaction Time Monitoring")
	rt_ax.set_xlabel("Mission days")
	rt_ax.set_ylabel("Average reaction time (ms)")
	lapse_ax.set_ylabel("Attention lapses (count)")
	rt_ax.legend(
		[rt_line, baseline_line, lapse_line],
		[rt_line.get_label(), baseline_line.get_label(), lapse_line.get_label()],
		loc="best",
	)

	def refresh(_frame):
		if not (len(days) == len(reaction_times) == len(lapses)):
			return rt_line, lapse_line
		rt_line.set_data(days, reaction_times)
		lapse_line.set_data(days, lapses)
		rt_ax.relim()
		rt_ax.autoscale_view()
		lapse_ax.relim()
		lapse_ax.autoscale_view()
		return rt_line, lapse_line

	# Periodically reread the input lists so newly appended daily data appears.
	animation = FuncAnimation(fig, refresh, interval=1000, blit=False, cache_frame_data=False)
	fig.tight_layout()
	return fig, rt_ax, lapse_ax, animation


def process_reaction_times(days, reaction_times, baseline_rt):
	"""Process daily reaction times through the health controller."""
	if len(days) != len(reaction_times):
		raise ValueError("days and reaction_times must have the same length")
	if baseline_rt <= 0 or any(reaction_time <= 0 for reaction_time in reaction_times):
		raise ValueError("Reaction times and the baseline must be greater than zero.")

	controller = HealthController(
		std=1.0,
		warning=WARNING_DEVIATION,
		critical=CRITICAL_DEVIATION,
		warning_rate=WARNING_RATE,
		critical_rate=CRITICAL_RATE,
	)
	start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
	results = []

	for day, reaction_time in zip(days, reaction_times):
		relative_speed = baseline_rt / reaction_time
		timestamp = start_time + timedelta(days=day - days[0])
		results.append(controller.process(timestamp, relative_speed))

	return results


def main():
	# Replace these sample values with measured data.
	days = [1, 2, 3, 4, 5]
	reaction_times = [250, 260, 275, 265, 290]
	lapses = [1, 2, 3, 2, 5]
	baseline_rt = 250

	processed_results = process_reaction_times(days, reaction_times, baseline_rt)
	for day, reaction_time, result in zip(days, reaction_times, processed_results):
		print(
			f"Day {day}: {reaction_time} ms, "
			f"deviation {result['deviation']:.1%}, "
			f"status {result['intervention_status']}, "
			f"urgency {result['urgency_level']}"
		)

	_, _, _, _animation = plot_reaction_time(
	    days, reaction_times, baseline_rt, lapses
	)
	plt.show()


if __name__ == "__main__":
	main()

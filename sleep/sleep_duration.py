import matplotlib.pyplot as plt


def main():
	total_days = int(input("Enter the total number of mission days: "))
	if total_days < 1:
		raise ValueError("The mission must last at least one day.")

	mission_days = list(range(1, total_days + 1))
	sleep_durations = []
	for day in mission_days:
		duration = float(input(f"Enter sleep duration for mission day {day} (hours): "))
		sleep_durations.append(duration)

	plt.plot(mission_days, sleep_durations, marker="o", label="Hours slept")
	plt.axhline(8, color="gray", linestyle="--", linewidth=1, label="8-hour baseline")
	plt.xlabel("Mission day, t (days)")
	plt.ylabel("Hours of sleep")
	plt.title("Daily Sleep Duration")
	plt.xticks(mission_days)
	plt.legend()
	plt.grid(True, alpha=0.3)
	plt.tight_layout()
	plt.show()


if __name__ == "__main__":
	main()

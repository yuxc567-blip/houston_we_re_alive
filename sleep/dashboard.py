"""Serve the offline sleep/reaction dashboard: python sleep/dashboard.py."""
import argparse
import copy
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import statistics
import sys
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sleep.sleep_duration import analyze_sleep
from sleep.reactiontime import positive, process_reaction_times, save_results

WEB = Path(__file__).with_name("web")


def new_data():
    return {"baseline_hours": 8, "sleep": [], "reaction_baseline": None, "reaction_sessions": []}


def day_number(value):
    value = positive(value, "Mission day")
    if not value.is_integer():
        raise ValueError("Mission day must be a positive whole number.")
    return int(value)


def summary(data):
    sleep = data["sleep"]
    result = {"data": data, "sleep_analysis": None, "reaction_analysis": []}
    if sleep:
        result["sleep_analysis"] = analyze_sleep([r["hours"] for r in sleep], [r["day"] for r in sleep], data["baseline_hours"])
    if data["reaction_sessions"]:
        if data["reaction_baseline"] is None:
            raise ValueError("Reaction sessions require a baseline.")
        rows = data["reaction_sessions"]
        result["reaction_analysis"] = process_reaction_times([r["day"] for r in rows], [r["mean_ms"] for r in rows], data["reaction_baseline"]["mean_ms"])
    return result


def trial_record(body):
    trials = body["trials_ms"]
    if not isinstance(trials, list) or len(trials) != 5:
        raise ValueError("Complete five valid trials before saving.")
    trials = [positive(value, "Reaction time") for value in trials]
    if any(value > 5000 for value in trials):
        raise ValueError("A trial exceeded the five-second response window.")
    counts = {}
    for key in ("early_clicks", "timeouts"):
        value = body.get(key, 0)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("Trial counters must be nonnegative whole numbers.")
        counts[key] = value
    return {"trials_ms": trials, "mean_ms": statistics.mean(trials), "median_ms": statistics.median(trials), **counts}


def load_data(path):
    if not path.exists():
        return new_data()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data["sleep"], list) or not isinstance(data["reaction_sessions"], list):
        raise ValueError("Invalid saved data.")
    analyze_sleep([8], [1], data["baseline_hours"])
    if data["reaction_baseline"] is not None:
        record = trial_record(data["reaction_baseline"])
        if record["mean_ms"] != data["reaction_baseline"]["mean_ms"]:
            raise ValueError("Saved baseline does not match its trials.")
    for record in data["reaction_sessions"]:
        if trial_record(record)["mean_ms"] != record["mean_ms"]:
            raise ValueError("Saved reaction result does not match its trials.")
    summary(data)
    return data


def make_handler(path):
    data = load_data(path)

    class Handler(BaseHTTPRequestHandler):
        def send(self, status, body, mime="application/json; charset=utf-8"):
            if not isinstance(body, bytes):
                body = json.dumps(body, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            route = urlparse(self.path).path
            if route in ("/api/state", "/api/export"):
                return self.send(200, summary(data))
            files = {"/": ("index.html", "text/html"), "/index.html": ("index.html", "text/html"), "/app.js": ("app.js", "application/javascript"), "/style.css": ("style.css", "text/css")}
            if route in files:
                name, mime = files[route]
                return self.send(200, (WEB / name).read_bytes(), mime + "; charset=utf-8")
            self.send(404, {"error": "Not found."})

        def do_POST(self):
            nonlocal data
            if self.headers.get("Origin") not in (None, "http://" + self.headers.get("Host", "")):
                return self.send(403, {"error": "Use the local dashboard to save results."})
            try:
                length = int(self.headers.get("Content-Length", 0))
                if not 0 < length <= 16384:
                    raise ValueError("Invalid request size.")
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError("Expected a JSON object.")
                candidate = copy.deepcopy(data)
                route = urlparse(self.path).path
                if route == "/api/sleep":
                    day = day_number(body["day"])
                    baseline = body.get("baseline_hours", candidate["baseline_hours"])
                    if candidate["sleep"] and float(baseline) != candidate["baseline_hours"]:
                        raise ValueError("The sleep reference is fixed after the first record.")
                    analysis = analyze_sleep([body["hours"]], [day], baseline)
                    if any(r["day"] == day for r in candidate["sleep"]):
                        raise ValueError("This mission day already has a sleep record.")
                    candidate["baseline_hours"] = analysis["baseline_hours"]
                    candidate["sleep"].append({"day": day, "hours": analysis["records"][0]["sleep_hours"]})
                    candidate["sleep"].sort(key=lambda r: r["day"])
                elif route == "/api/reaction":
                    record = trial_record(body)
                    if body["mode"] == "baseline":
                        if candidate["reaction_baseline"] is not None:
                            raise ValueError("A baseline is already saved. Use a new --data file for a new baseline.")
                        candidate["reaction_baseline"] = record
                    elif body["mode"] == "session":
                        if candidate["reaction_baseline"] is None:
                            raise ValueError("Measure your baseline first.")
                        day = day_number(body["day"])
                        if any(r["day"] == day for r in candidate["reaction_sessions"]):
                            raise ValueError("This mission day already has a reaction-time session.")
                        candidate["reaction_sessions"].append({"day": day, **record})
                        candidate["reaction_sessions"].sort(key=lambda r: r["day"])
                    else:
                        raise ValueError("Choose baseline or session.")
                else:
                    return self.send(404, {"error": "Not found."})
                response = summary(candidate)
                save_results(path, candidate)
                data = candidate
                self.send(200, response)
            except (ValueError, KeyError, TypeError, OverflowError) as error:
                self.send(400, {"error": str(error)})
            except OSError:
                self.send(500, {"error": "Could not save results. Check the data-file location."})

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--data", type=Path, default=Path(__file__).with_name("wellness_results.json"))
    args = parser.parse_args()
    try:
        server = HTTPServer(("127.0.0.1", args.port), make_handler(args.data.resolve()))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(f"Could not start; existing data was not overwritten: {error}")
    print(f"Sleep & reaction dashboard: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

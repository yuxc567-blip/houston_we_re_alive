#!/usr/bin/env python3
"""SANS / TRT monitor prototype. Python 3.9+, standard library only.

Run: python3 sans.py
Demo: python3 sans.py --demo
Optional experimental rule: python3 sans.py --rate-review-threshold 1.0
Optional linear extrapolation: python3 sans.py --prediction-days 7

Adapted from the team's Deviation / Error / AccumulatedError /
DeteriorationRate / InterventionStatus / Urgency / HealthController design.
This is a monitoring prototype, not a validated diagnostic or PID controller.

Measurement: per-eye mean TRT in the BMO-to-250-um annulus, in micrometres.
Research rule: change from preflight baseline > 19.4 um suggests early ODE.
Laurie et al. 2020, doi:10.1001/jamaophthalmol.2019.5261.
Method: Macias et al. 2020, doi:10.1001/jamaophthalmol.2020.0673.
No validated rate, integral, critical-severity, or forecast rule is asserted.
The stored baseline is fixed. Integral starts at the first recorded in-flight
measurement, not an assumed zero at launch, and is signed (negative cancels
positive). Rates are interval averages; interpolation is an assumption.
One data file represents one astronaut and one mission. Keep it private.
"""

import argparse
import csv
import html
import json
import math
import os
from pathlib import Path
import tempfile
from enum import Enum


ODE_THRESHOLD_UM = 19.4
EYES = ("R", "L")
EYE_NAMES = {"R": "右眼", "L": "左眼"}


def number(value, name, minimum=None, strictly_positive=False):
    if isinstance(value, bool):
        raise ValueError(f"{name} 必须是有限数值。")
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} 必须是数值。") from None
    if not math.isfinite(result):
        raise ValueError(f"{name} 不能是 NaN 或无穷大。")
    if strictly_positive and result <= 0:
        raise ValueError(f"{name} 必须大于 0。")
    if minimum is not None and result < minimum:
        raise ValueError(f"{name} 必须不小于 {minimum}。")
    return result


# 1. DEVIATION: positive means thickening, unlike the original sign.
class Deviation:
    def __init__(self, baseline, current):
        self.baseline = baseline
        self.current = current

    def calculate(self):
        return None if self.baseline is None else self.current - self.baseline


# 2. ERROR: descriptive relative change, never compared to a um threshold.
class Error(Deviation):
    def calculate(self):
        deviation = super().calculate()
        return None if deviation is None else deviation / self.baseline


# 3. ACCUMULATED ERROR: trapezoidal integral of absolute-unit delta TRT.
class AccumulatedError:
    def __init__(self):
        self.previous_error = None
        self.previous_time = None
        self.start_time = None
        self.total = 0.0

    def calculate(self, flight_day, error):
        if error is None:
            return None
        if self.previous_time is None:
            self.previous_error = error
            self.previous_time = self.start_time = flight_day
            return 0.0
        dt = flight_day - self.previous_time
        if dt <= 0:
            raise ValueError("Flight Day 必须递增。")
        self.total += (self.previous_error + error) / 2 * dt
        self.previous_error = error
        self.previous_time = flight_day
        return self.total


# 4. DETERIORATION RATE: signed average rate, not automatically deterioration.
class DeteriorationRate:
    def __init__(self):
        self.previous_value = None
        self.previous_time = None

    def calculate(self, flight_day, current_value):
        if self.previous_time is None:
            self.previous_value = current_value
            self.previous_time = flight_day
            return None
        dt = flight_day - self.previous_time
        if dt <= 0:
            raise ValueError("Flight Day 必须递增。")
        rate = (current_value - self.previous_value) / dt
        self.previous_value = current_value
        self.previous_time = flight_day
        return rate


# 5. INTERVENTION STATUS: a research-threshold finding, not a diagnosis.
class Status(Enum):
    NOT_ASSESSED = "NOT_ASSESSED"
    NOT_EXCEEDED = "TRT_THRESHOLD_NOT_EXCEEDED"
    EXCEEDED = "EARLY_ODE_RESEARCH_THRESHOLD_EXCEEDED"


class InterventionStatus:
    def evaluate(self, delta_trt):
        if delta_trt is None:
            return Status.NOT_ASSESSED
        # Strict >, consistent with the research rule used in this prototype.
        exceeded = delta_trt > ODE_THRESHOLD_UM and not math.isclose(
            delta_trt, ODE_THRESHOLD_UM, rel_tol=0, abs_tol=1e-9
        )
        return Status.EXCEEDED if exceeded else Status.NOT_EXCEEDED


# 6. URGENCY ADAPTED: optional change-review flag, no invented medical urgency.
class Urgency:
    def __init__(self, rate_review_threshold=None, prediction_days=None):
        self.rate_review_threshold = (
            None if rate_review_threshold is None else
            number(rate_review_threshold, "实验性变化率核查界限", strictly_positive=True)
        )
        self.prediction_days = (
            None if prediction_days is None else
            number(prediction_days, "外推天数", strictly_positive=True)
        )

    def evaluate(self, delta_trt, rate):
        if rate is None:
            review = "INSUFFICIENT_HISTORY"
        elif self.rate_review_threshold is None:
            review = "RULE_NOT_CONFIGURED"
        elif abs(rate) >= self.rate_review_threshold:
            review = "CHANGE_REVIEW_SUGGESTED_EXPERIMENTAL"
        else:
            review = "EXPERIMENTAL_RULE_NOT_TRIGGERED"
        predicted = None
        if rate is not None and delta_trt is not None and self.prediction_days is not None:
            predicted = delta_trt + rate * self.prediction_days
        return {
            "change_review_status": review,
            "rate_review_threshold_um_per_day": self.rate_review_threshold,
            "forecast_delta_trt_um": predicted,
            "forecast_horizon_days": self.prediction_days,
        }


# 7. GENERAL HEALTH CONTROLLER ADAPTED TO TRT.
class HealthController:
    def __init__(self, baseline=None, rate_review_threshold=None, prediction_days=None):
        self.baseline = None if baseline is None else number(baseline, "基线 TRT", strictly_positive=True)
        self.accumulated = AccumulatedError()
        self.deterioration = DeteriorationRate()
        self.status = InterventionStatus()
        self.urgency = Urgency(rate_review_threshold, prediction_days)
        self.previous_day = None
        self.previous_value = None

    def process(self, flight_day, current_value):
        day = number(flight_day, "Flight Day", minimum=0)
        current = number(current_value, "TRT", strictly_positive=True)
        # Validate before changing any state.
        if self.previous_day is not None and day <= self.previous_day:
            raise ValueError("同一只眼的 Flight Day 必须递增，不能重复。")
        delta = Deviation(self.baseline, current).calculate()
        relative = Error(self.baseline, current).calculate()
        change = None if self.previous_value is None else current - self.previous_value
        interval = None if self.previous_day is None else day - self.previous_day
        integral = self.accumulated.calculate(day, delta)
        rate = self.deterioration.calculate(day, current)
        result = {
            "flight_day": day,
            "current_trt_um": current,
            "baseline_trt_um": self.baseline,
            "delta_trt_um": delta,
            "relative_change_percent": None if relative is None else relative * 100,
            "change_since_previous_um": change,
            "interval_days": interval,
            "rate_um_per_day": rate,
            "rate_magnitude_um_per_day": None if rate is None else abs(rate),
            "accumulated_deviation_um_days": integral,
            "integral_start_flight_day": self.accumulated.start_time,
            "threshold_um": ODE_THRESHOLD_UM,
            "threshold_status": self.status.evaluate(delta).value,
        }
        result.update(self.urgency.evaluate(delta, rate))
        self.previous_day, self.previous_value = day, current
        return result


def new_data():
    return {"schema_version": 1, "region": "BMO_TO_250_UM", "unit": "um",
            "eyes": {e: {"baseline": None, "records": []} for e in EYES}}


def validate_data(data):
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("不支持的数据文件版本。")
    if data.get("region") != "BMO_TO_250_UM" or data.get("unit") != "um":
        raise ValueError("数据必须对应 BMO–250 μm 区域，单位为 μm。")
    if not isinstance(data.get("eyes"), dict) or set(data["eyes"]) != set(EYES):
        raise ValueError("数据必须包含独立的 R、L 眼记录。")
    for eye in EYES:
        item = data["eyes"][eye]
        if not isinstance(item, dict) or "baseline" not in item or not isinstance(item.get("records"), list):
            raise ValueError("眼部数据结构错误。")
        if item["baseline"] is not None:
            number(item["baseline"], "基线 TRT", strictly_positive=True)
        days = set()
        for record in item["records"]:
            day = number(record["flight_day"], "Flight Day", minimum=0)
            number(record["trt_um"], "TRT", strictly_positive=True)
            if record.get("quality_confirmed") is not True:
                raise ValueError("历史记录包含未经质量确认的数据。")
            if day in days:
                raise ValueError("数据包含同一只眼、同一 Flight Day 的重复测量。")
            days.add(day)
    return data


def load_data(path):
    if not path.exists():
        return new_data()
    try:
        return validate_data(json.loads(path.read_text(encoding="utf-8")))
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError(f"数据文件无法读取；不会自动清空或覆盖：{exc}") from exc


def save_data(path, data):
    validate_data(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replacement; leave the preceding complete version as .bak.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=path.name + ".", delete=False) as f:
        temp = Path(f.name)
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
    try:
        if path.exists():
            path.with_suffix(path.suffix + ".bak").write_bytes(path.read_bytes())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def analyze(data, eye, rate_review_threshold=None, prediction_days=None):
    item = data["eyes"][eye]
    controller = HealthController(item["baseline"], rate_review_threshold, prediction_days)
    return [controller.process(r["flight_day"], r["trt_um"])
            for r in sorted(item["records"], key=lambda x: x["flight_day"])]


def fmt(value, digits=2, signed=False):
    if value is None:
        return "暂无数据"
    return format(value, ("+" if signed else "") + f".{digits}f")


def summary(eye, r):
    text = f"{EYE_NAMES[eye]} FD{r['flight_day']:g}，BMO–250 μm 区域当前 TRT 为 {fmt(r['current_trt_um'])} μm。"
    if r["delta_trt_um"] is None:
        text += "缺少飞行前基线，无法计算 ΔTRT 或进行阈值判读。"
    else:
        text += f"较飞行前变化 {fmt(r['delta_trt_um'], signed=True)} μm（{fmt(r['relative_change_percent'], signed=True)}%）。"
    if r["change_since_previous_um"] is None:
        text += "这是首条在轨记录，尚不能计算相对上次变化或变化率。"
    else:
        text += (f"较上次变化 {fmt(r['change_since_previous_um'], signed=True)} μm；"
                 f"间隔 {r['interval_days']:g} 天，平均变化率为 {fmt(r['rate_um_per_day'], 3, True)} μm/天。")
        if r["change_since_previous_um"] < 0 and r["delta_trt_um"] is not None and r["delta_trt_um"] > 0:
            text += "本次测得的增厚量有所回落，但仍高于个人基线。"
    if r["threshold_status"] == Status.EXCEEDED.value:
        text += "超过所采用研究的 +19.4 μm 早期 ODE 阈值，提示早期视盘水肿迹象，需加强监测与专业评估。"
    elif r["threshold_status"] == Status.NOT_EXCEEDED.value:
        text += "本次未超过该 TRT 阈值；不能据此排除 SANS。"
    if r["change_review_status"] == "CHANGE_REVIEW_SUGGESTED_EXPERIMENTAL":
        text += "触发团队设定的实验性变化核查规则：请核对输入、测量条件和质量，必要时复测；这不是医学紧急程度分级。"
    text += "本结果不直接代表视力损伤或 SANS 严重程度。"
    return text


def report_text(data, rate_review_threshold=None, prediction_days=None):
    lines = ["SANS / TRT MONITOR", "区域：BMO–250 μm；单位：μm；左右眼独立分析。",
             "19.4 μm 是相对个人基线的增厚阈值，不是绝对厚度上限。"]
    if rate_review_threshold is None:
        lines.append("变化核查规则：未配置。显示实际速度，不生成快速变化警报或紧急程度等级。")
    else:
        lines.append(f"实验性核查规则：|变化率| ≥ {rate_review_threshold:g} μm/天；团队自定，未经医学验证。")
    for eye in EYES:
        rows = analyze(data, eye, rate_review_threshold, prediction_days)
        lines.extend(["", f"--- {EYE_NAMES[eye]} ({eye}) ---",
                      f"飞行前基线：{fmt(data['eyes'][eye]['baseline'])} μm"])
        if not rows:
            lines.append("尚无在轨记录。")
            continue
        lines.append("FD | TRT μm | ΔTRT μm | 较上次 μm | μm/天 | 累计 μm·天")
        for r in rows:
            lines.append(f"{r['flight_day']:g} | {fmt(r['current_trt_um'])} | "
                         f"{fmt(r['delta_trt_um'], signed=True)} | "
                         f"{fmt(r['change_since_previous_um'], signed=True)} | "
                         f"{fmt(r['rate_um_per_day'], 3, True)} | "
                         f"{fmt(r['accumulated_deviation_um_days'])}")
        last = rows[-1]
        lines.extend(["", summary(eye, last)])
        if last["accumulated_deviation_um_days"] is not None:
            lines.append(f"累计偏离量：{fmt(last['accumulated_deviation_um_days'])} μm·天，"
                         f"覆盖 FD{last['integral_start_flight_day']:g}–FD{last['flight_day']:g}。"
                         "使用有符号梯形积分；不是累计损伤，且负偏离会抵消正偏离。")
        if last["forecast_delta_trt_um"] is not None:
            lines.append(f"探索性外推：假设最近平均速度持续，{prediction_days:g} 天后 ΔTRT ≈ "
                         f"{fmt(last['forecast_delta_trt_um'], signed=True)} μm。"
                         "非临床预测，不参与阈值状态或紧急程度判断。")
    lines.extend(["", "变化率是相邻测量间的平均速度，无法确定变化具体发生在哪一天。",
                  "研究来源：Laurie 2020，DOI 10.1001/jamaophthalmol.2019.5261；"
                  "Macias 2020，DOI 10.1001/jamaophthalmol.2020.0673。"])
    return "\n".join(lines)


def chart_svg(rows, eye):
    valid = [r for r in rows if r["delta_trt_um"] is not None]
    if not valid:
        return "<p>尚无可绘制的 ΔTRT 数据：需要基线和至少一次在轨测量。</p>"
    width, height = 800, 330
    left, right, top, bottom = 72, 30, 25, 55
    days = [r["flight_day"] for r in valid]
    values = [r["delta_trt_um"] for r in valid] + [0, ODE_THRESHOLD_UM]
    xmin, xmax = min(days), max(days)
    if xmin == xmax:
        xmin, xmax = max(0, xmin - 5), xmax + 5
    ymin, ymax = min(values), max(values)
    pad = max(5, (ymax - ymin) * 0.12)
    ymin, ymax = ymin - pad, ymax + pad
    x = lambda day: left + (day - xmin) / (xmax - xmin) * (width-left-right)
    y = lambda value: height-bottom - (value-ymin) / (ymax-ymin) * (height-top-bottom)
    svg = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{EYE_NAMES[eye]} ΔTRT 随 Flight Day 变化">',
           f'<rect x="{left}" y="{top}" width="{width-left-right}" height="{height-top-bottom}" fill="none" stroke="#bbb"/>']
    for i in range(5):
        v = ymin + (ymax-ymin) * i/4
        svg.append(f'<text x="{left-8}" y="{y(v)+4:.2f}" text-anchor="end">{v:.1f}</text>')
        d = xmin+(xmax-xmin)*i/4
        svg.append(f'<text x="{x(d):.2f}" y="{height-bottom+22}" text-anchor="middle">{d:g}</text>')
    for v, label, color in [(0, "个人基线 Δ=0", "#666"), (ODE_THRESHOLD_UM, "+19.4 μm", "#a44824")]:
        svg.append(f'<line x1="{left}" y1="{y(v):.2f}" x2="{width-right}" y2="{y(v):.2f}" stroke="{color}" stroke-dasharray="5 4"/>')
        svg.append(f'<text x="{left+5}" y="{y(v)-6:.2f}" fill="{color}">{label}</text>')
    points = " ".join(f"{x(r['flight_day']):.2f},{y(r['delta_trt_um']):.2f}" for r in valid)
    svg.append(f'<polyline points="{points}" fill="none" stroke="#176f91" stroke-width="2"/>')
    for r in valid:
        svg.append(f'<circle cx="{x(r["flight_day"]):.2f}" cy="{y(r["delta_trt_um"]):.2f}" r="4" fill="#176f91">'
                   f'<title>FD{r["flight_day"]:g}: ΔTRT {r["delta_trt_um"]:+.2f} μm</title></circle>')
    svg.extend([f'<text x="{width/2}" y="{height-6}" text-anchor="middle">Flight Day（实际间隔）</text>',
                f'<text transform="translate(18 {height/2}) rotate(-90)" text-anchor="middle">ΔTRT (μm)</text>', '</svg>'])
    return "".join(svg)


def export_report(path, data, rate_review_threshold=None, prediction_days=None):
    text = report_text(data, rate_review_threshold, prediction_days)
    sections = []
    for eye in EYES:
        sections.append(f'<h2>{EYE_NAMES[eye]} ({eye})</h2>' + chart_svg(analyze(data, eye, rate_review_threshold, prediction_days), eye))
    document = ('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>SANS TRT report</title><style>'
                'body{max-width:1000px;margin:30px auto;padding:0 20px;font:16px/1.7 system-ui;color:#222;background:#fff}'
                'svg{width:100%;height:auto}svg text{font:14px system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.7 monospace}'
                '</style><h1>SANS / TRT 监测报告</h1><p>示意连线连接测量点，不代表期间连续测量。</p>'
                + ''.join(sections) + '<h2>数据与解释</h2><pre>' + html.escape(text) + '</pre></html>')
    path.write_text(document, encoding="utf-8")


def export_csv(path, data, rate_review_threshold=None, prediction_days=None):
    all_rows = [dict(eye=eye, **r) for eye in EYES for r in analyze(data, eye, rate_review_threshold, prediction_days)]
    if not all_rows:
        raise ValueError("尚无测量数据可导出。")
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)


def ask_eye():
    eye = input("眼别：R=右眼，L=左眼：").strip().upper()
    if eye not in EYES:
        raise ValueError("请输入 R 或 L。")
    return eye


def quality_confirmation():
    answer = input("确认这些值均为 BMO–250 μm 平均 TRT、测量方法一致且质量合格？输入 y 确认：").strip().lower()
    if answer != 'y':
        raise ValueError("未确认可比性与质量，本次不保存；请先核对 OCT 分析结果。")


def add_record(data, eye, day, value):
    day = number(day, "Flight Day", minimum=0)
    value = number(value, "TRT", strictly_positive=True)
    records = data['eyes'][eye]['records']
    if any(r['flight_day'] == day for r in records):
        raise ValueError(f"{eye} 眼 FD{day:g} 已有记录；请先删除旧记录再更正。")
    records.append({'flight_day': day, 'trt_um': value, 'quality_confirmed': True})
    records.sort(key=lambda r: r['flight_day'])


def demo_data():
    data = new_data()
    data['eyes']['R']['baseline'] = 400.0
    data['eyes']['L']['baseline'] = 390.0
    for day, value in [(10,410),(20,414),(30,412),(40,419),(50,423),(60,426),(70,430),(80,428),(90,422),(100,420)]:
        add_record(data, 'R', day, value)
        add_record(data, 'L', day, 390 + (value-400)*0.4)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--data', type=Path, default=Path(__file__).resolve().parents[1] / 'sans_data.json', help='单个宇航员、单次任务的数据文件')
    parser.add_argument('--demo', action='store_true', help='展示虚构100天数据，绝不读写真实数据文件')
    parser.add_argument('--rate-review-threshold', type=float, default=None, help='团队自定实验性核查界限，μm/天；默认不启用')
    parser.add_argument('--prediction-days', type=float, default=None, help='探索性线性外推天数；默认关闭')
    args = parser.parse_args()
    Urgency(args.rate_review_threshold, args.prediction_days)  # validate configuration
    if args.demo:
        data = demo_data()
        print('*** DEMO：全部数值为虚构数据，不代表研究原始数据。***')
        print(report_text(data, args.rate_review_threshold, args.prediction_days))
        out = Path(__file__).resolve().parents[1] / 'sans_demo_report.html'
        export_report(out, data, args.rate_review_threshold, args.prediction_days)
        print(f'\n演示曲线：{out}')
        return
    path = args.data.expanduser().resolve()
    data = load_data(path)
    print(f'SANS / TRT monitor\n数据文件：{path}\n每个文件只记录一名宇航员的一次任务。')
    while True:
        print('\n1 建立某眼基线\n2 新增一次测量\n3 批量输入历史测量\n4 查看全部数据与总结\n5 导出曲线报告 HTML\n6 导出结果 CSV\n7 删除错误测量\n0 退出')
        choice = input('选择：').strip()
        try:
            if choice == '0':
                return
            if choice in ('1', '2', '3', '7'):
                # Work on a copy; commit only after validation and successful save.
                candidate = json.loads(json.dumps(data))
                eye = ask_eye()
                if choice == '1':
                    if candidate['eyes'][eye]['baseline'] is not None:
                        raise ValueError('基线已建立，不能在监测过程中直接重设；新任务请使用新的 --data 文件。')
                    value = number(input('飞行前基线 TRT (μm)：'), '基线 TRT', strictly_positive=True)
                    quality_confirmation()
                    candidate['eyes'][eye]['baseline'] = value
                elif choice == '2':
                    day = input('Flight Day（例如 100）：')
                    value = input('当前 TRT (μm)：')
                    quality_confirmation()
                    add_record(candidate, eye, day, value)
                elif choice == '3':
                    print('每行：Flight Day,TRT，例如 10,412。空行结束。整批验证后一次保存。')
                    entries = []
                    while True:
                        line = input().strip()
                        if not line:
                            break
                        entries.append(line)
                    if not entries:
                        raise ValueError('未输入测量。')
                    for line in entries:
                        parts = line.replace('，', ',').split(',')
                        if len(parts) != 2:
                            raise ValueError('每行必须恰好包含 Flight Day,TRT。')
                        add_record(candidate, eye, *parts)
                    quality_confirmation()
                else:
                    day = number(input('删除哪一个 Flight Day：'), 'Flight Day', minimum=0)
                    records = candidate['eyes'][eye]['records']
                    remaining = [r for r in records if r['flight_day'] != day]
                    if len(remaining) == len(records):
                        raise ValueError('找不到该测量。')
                    if input(f'确认删除 {eye} 眼 FD{day:g}？输入 y：').strip().lower() != 'y':
                        continue
                    candidate['eyes'][eye]['records'] = remaining
                save_data(path, candidate)
                data = candidate
                print('已保存。历史顺序、变化率和积分将重新计算。')
                rows = analyze(data, eye, args.rate_review_threshold, args.prediction_days)
                if rows:
                    print(summary(eye, rows[-1]))
            elif choice == '4':
                print(report_text(data, args.rate_review_threshold, args.prediction_days))
            elif choice in ('5', '6'):
                suffix = '.html' if choice == '5' else '.csv'
                out = path.with_name(path.stem + '_report' + suffix)
                if choice == '5':
                    export_report(out, data, args.rate_review_threshold, args.prediction_days)
                else:
                    export_csv(out, data, args.rate_review_threshold, args.prediction_days)
                print(f'已导出：{out}')
                if choice == '5':
                    print('用浏览器打开此文件即可查看左右眼 ΔTRT 曲线。')
            else:
                print('请输入菜单中的数字。')
        except (ValueError, OSError, KeyError, TypeError) as exc:
            print(f'操作未完成：{exc}')


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print('\n已退出。此前成功保存的数据仍在。')
    except (ValueError, OSError) as exc:
        print(f'无法启动：{exc}')
        raise SystemExit(1)

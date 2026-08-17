#!/usr/bin/env python3
"""Query GSA (Global Solar Atlas) pvcalc API for PV performance data.

Directly returns annual / monthly / monthly-hourly (typical-day) data as JSON,
replacing the browser-click + XLSX-download path in Mode B of the skill.

Usage:
    python3 gsa_pvcalc.py --loc 30.274100,120.058900 --type medium \
        --capacity 1000 --tilt 15 --azimuth 180 [--gmt-offset 28800] \
        [--format json|table]

Type mapping (source: GSA frontend bundle chunk-CD6ZCY4X.js, enum n_):
    GSA URL pv= param  ->  pvcalc `type`
    small              ->  rooftopSmall              (小型住宅屋顶)
    medium             ->  rooftopLargeFlat          (工商业平屋顶)
    large              ->  groundFixed               (地面固定式)
    floating           ->  hydroMountedLargeScale    (水面/水库漂浮式)
    (also valid: rooftopLargeTilted, buildingIntegrated,
     trackerOneAxisHorizontalNS, noPvSystem)

Notes:
- PVOUT_specific is normalized (kWh/kWp), independent of `capacity`; pass the
  REAL project capacity so PVOUT_total is already project-scoped (kWh / Wh).
- monthly-hourly is a TYPICAL DAY (24 values/month); multiply by days-in-month
  to get monthly totals. Monthly totals are also given directly in `monthly`.
- The API does NOT validate coordinates: ocean coords return data, invalid
  coords return HTTP 500. This script validates lat/lng itself and maps 500
  to a readable error.
- gmtOffset: seconds east of UTC. China = 28800, Vietnam = 25200.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime

API_URL = "https://2eueu84zmf.execute-api.eu-west-1.amazonaws.com/prod/data/pvcalc"

# GSA frontend pv= param -> pvcalc type
TYPE_MAP = {
    "small": "rooftopSmall",
    "medium": "rooftopLargeFlat",
    "large": "groundFixed",
    "floating": "hydroMountedLargeScale",
}

VALID_TYPES = {
    "rooftopSmall", "rooftopLargeFlat", "rooftopLargeTilted",
    "buildingIntegrated", "groundFixed", "trackerOneAxisHorizontalNS",
    "hydroMountedLargeScale", "noPvSystem",
}

MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
MONTH_NAMES = ["1月", "2月", "3月", "4月", "5月", "6月",
               "7月", "8月", "9月", "10月", "11月", "12月"]


def validate_location(lat, lng):
    """The API does not validate coords; we must."""
    if not isinstance(lat, (int, float)) or not (-90 <= lat <= 90):
        raise ValueError(f"纬度超出范围: {lat}（应为 [-90, 90]）")
    if not isinstance(lng, (int, float)) or not (-180 <= lng <= 180):
        raise ValueError(f"经度超出范围: {lng}（应为 [-180, 180]）")


def resolve_type(pv_type):
    t = TYPE_MAP.get(pv_type, pv_type)
    if t not in VALID_TYPES:
        raise ValueError(
            f"无效 type: {pv_type}。可用: {sorted(TYPE_MAP)} 或 {sorted(VALID_TYPES)}"
        )
    return t


def query_pvcalc(lat, lng, pv_type, capacity, tilt, azimuth, gmt_offset, timeout=30):
    """POST pvcalc API. Returns parsed JSON or raises RuntimeError."""
    validate_location(lat, lng)
    pv_type = resolve_type(pv_type)
    if not isinstance(capacity, (int, float)) or capacity <= 0:
        raise ValueError(f"容量必须为正数: {capacity}")
    if not (-90 <= tilt <= 90):
        raise ValueError(f"倾角超出范围: {tilt}")
    if not (-360 <= azimuth <= 360):
        raise ValueError(f"方位角超出范围: {azimuth}")

    url = f"{API_URL}?loc={lat},{lng}&gmtOffset={gmt_offset}"
    body = json.dumps({
        "type": pv_type,
        "systemSize": {"type": "capacity", "value": capacity},
        "orientation": {"azimuth": azimuth, "tilt": tilt},
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 500:
            raise RuntimeError("该坐标无有效数据（接口返回 500），请检查经纬度是否正确")
        raise RuntimeError(f"接口 HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"网络错误: {e.reason}")
    except TimeoutError:
        raise RuntimeError("请求超时，请稍后重试")

    if "annual" not in data or "data" not in data.get("annual", {}):
        raise RuntimeError("接口返回异常（无 annual.data），请稍后重试")
    return data


def format_table(data, capacity):
    """Human-readable table output (annual + monthly + Jul/Dec typical day)."""
    annual = data["annual"]["data"]
    monthly = data["monthly"]["data"]
    hourly = data.get("monthly-hourly", {}).get("data", {})

    lines = []
    lines.append("## 年累计")
    lines.append("")
    lines.append(f"- PVOUT（比光伏出力）: {annual['PVOUT_specific']:.2f} kWh/kWp")
    lines.append(f"- PVOUT（年发电量, {capacity:g} kWp）: {annual['PVOUT_total']:,.1f} kWh")
    lines.append(f"- GTI（组件平面辐射）: {annual['GTI']:.2f} kWh/m²")
    lines.append(f"- DNI（直接法向辐射）: {annual['DNI']:.2f} kWh/m²")
    lines.append("")
    lines.append("## 月度数据")
    lines.append("")
    lines.append("| 月份 | 发电量 (kWh) | 单位出力 (kWh/kWp) | GTI (kWh/m²) | DNI (kWh/m²) |")
    lines.append("|------|-------------|-------------------|-------------|-------------|")
    for i in range(12):
        lines.append(f"| {MONTH_NAMES[i]} | {monthly['PVOUT_total'][i]:,.1f} "
                     f"| {monthly['PVOUT_specific'][i]:.2f} "
                     f"| {monthly['GTI'][i]:.2f} | {monthly['DNI'][i]:.2f} |")
    lines.append(f"| **年** | **{annual['PVOUT_total']:,.1f}** "
                 f"| **{annual['PVOUT_specific']:.2f}** "
                 f"| **{annual['GTI']:.2f}** | **{annual['DNI']:.2f}** |")
    lines.append("")

    if hourly and "PVOUT_total" in hourly:
        lines.append("## 逐时发电量（典型日，单位 Wh）")
        lines.append("")
        lines.append("> 注：monthly-hourly 为典型日 24 小时值，日值 × 当月天数 = 月累计。")
        lines.append("")
        for mi in (6, 11):  # 7月(夏季峰值) + 12月(冬季低谷)
            m = MONTH_NAMES[mi]
            lines.append(f"### {m}（典型日）")
            lines.append("")
            lines.append("| 小时 | 出力 (Wh) | 占比 (%) |")
            lines.append("|------|----------|---------|")
            day_total = sum(hourly["PVOUT_total"][mi])
            for h in range(24):
                v = hourly["PVOUT_total"][mi][h]
                pct = v / day_total * 100 if day_total else 0
                lines.append(f"| {h:02d}:00-{h+1:02d}:00 | {v:,.1f} | {pct:.1f} |")
            lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Query GSA pvcalc API")
    parser.add_argument("--loc", required=True,
                        help="经纬度，格式: 纬度,经度 (如 30.274100,120.058900)")
    parser.add_argument("--type", default="medium",
                        help="系统类型: small/medium/large/floating 或 pvcalc 原生值")
    parser.add_argument("--capacity", type=float, default=100,
                        help="装机容量 kWp（项目实际容量，默认 100）")
    parser.add_argument("--tilt", type=float, required=True, help="组件倾角 °")
    parser.add_argument("--azimuth", type=float, default=180, help="方位角 °（默认 180 正南）")
    parser.add_argument("--gmt-offset", type=int, default=28800,
                        help="时区偏移秒（中国 28800，越南 25200）")
    parser.add_argument("--format", choices=["json", "table"], default="json")
    parser.add_argument("--timeout", type=int, default=30)

    args = parser.parse_args()
    try:
        lat, lng = (float(x) for x in args.loc.split(","))
    except (ValueError, AttributeError):
        print("ERROR: --loc 格式错误，应为 纬度,经度", file=sys.stderr)
        sys.exit(1)

    try:
        data = query_pvcalc(lat, lng, args.type, args.capacity, args.tilt,
                            args.azimuth, args.gmt_offset, args.timeout)
    except (ValueError, RuntimeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if args.format == "table":
        print(format_table(data, args.capacity))
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

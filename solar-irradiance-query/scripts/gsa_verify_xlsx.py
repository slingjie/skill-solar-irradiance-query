#!/usr/bin/env python3
"""Verify pvcalc API data against the original GSA XLSX report.

Used after Mode B data acquisition: cross-check pvcalc JSON (optimized path)
against the downloaded original XLSX (gsa_report_parser.py output). Only
report results when deviations stay within tolerance.

Tolerances (based on 2026-08 measured deviations, with 10x margin):
    annual PVOUT  < 0.5%
    monthly PVOUT < 0.5%   (XLSX rounds hourly to integer Wh)
    hourly peak   < 1.0%

Usage:
    python3 gsa_verify_xlsx.py --pvcalc <pvcalc.json> --xlsx <GSA_Report.xlsx> \
        [--capacity 1000] [--format json|table]

Exit codes:
    0  通过（所有指标在容差内）
    1  有指标超容差（复核失败）
    2  文件缺失/解析失败
"""
import argparse
import json
import os
import subprocess
import sys

MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

TOL = {'annual': 0.5, 'monthly': 0.5, 'hourly_peak': 1.0}


def parse_xlsx(xlsx_path, parser_path):
    """用 gsa_report_parser.py 解析 XLSX，返回结构化 dict。"""
    r = subprocess.run([sys.executable, parser_path, xlsx_path, "--format", "json"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"XLSX 解析失败: {r.stderr[:300] or r.stdout[:300]}")
    return json.loads(r.stdout)


def compare(pv, xl, capacity):
    """对比 pvcalc JSON 与 XLSX 解析结果，返回指标列表。"""
    pa = pv['annual']['data']
    pm = pv['monthly']['data']
    ph = pv['monthly-hourly']['data']['PVOUT_total']

    xl_m = xl['sheets']['Monthly_averages']
    xl_pvout = {}
    for month, vals in xl_m.items():
        if isinstance(vals, dict):
            for h, v in vals.items():
                if 'PVOUT' in h and 'total' in h.lower():
                    xl_pvout[month] = float(str(v).replace(',', ''))

    # 1. 年发电量（XLSX Yearly 行 或 12 月求和）
    xl_annual = xl_pvout.get('Yearly', sum(xl_pvout.get(m, 0) for m in MONTHS))
    pv_annual = pa['PVOUT_total']

    results = []
    results.append(_row('年发电量 (kWh)', pv_annual, xl_annual, 'annual'))

    # 2. 月度 PVOUT（12 个月）
    for i, m in enumerate(MONTHS):
        a = pm['PVOUT_total'][i]
        b = xl_pvout.get(m)
        if b is None:
            continue
        results.append(_row(f'{m} 月度发电量 (kWh)', a, b, 'monthly'))

    # 3. 逐时峰值（7月/12月典型日 max）
    xh = xl['sheets']['Hourly_profiles']
    for mi, mname in [(6, 'Jul'), (11, 'Dec')]:
        xl_h = xh['pvout_total'].get(mname, {})
        if not xl_h:
            continue
        xl_peak = max(float(v) for v in xl_h.values())
        pv_peak = max(ph[mi])
        results.append(_row(f'{mname} 逐时峰值 (Wh)', pv_peak, xl_peak, 'hourly_peak'))

    return results


def _row(label, pv_val, xl_val, kind):
    if xl_val == 0:
        return {'label': label, 'kind': kind, 'pvcalc': pv_val, 'xlsx': xl_val,
                'diff_pct': None, 'pass': None}
    diff = (pv_val - xl_val) / abs(xl_val) * 100
    return {'label': label, 'kind': kind, 'pvcalc': round(pv_val, 3),
            'xlsx': round(xl_val, 3), 'diff_pct': round(diff, 4),
            'pass': abs(diff) < TOL[kind]}


def format_table(results, capacity):
    lines = ["## 数据复核（pvcalc vs GSA XLSX 原件）", ""]
    lines.append(f"- 复核容量：{capacity:g} kWp | 容差：年/月 <0.5%，逐时峰值 <1.0%")
    lines.append("")
    lines.append("| 指标 | pvcalc | XLSX 原件 | 偏差 % | 结果 |")
    lines.append("|------|--------|-----------|--------|------|")
    n_pass = 0
    for r in results:
        if r['diff_pct'] is None:
            lines.append(f"| {r['label']} | {r['pvcalc']:,.1f} | {r['xlsx']:,.1f} | - | 跳过 |")
            continue
        mark = "✅ 通过" if r['pass'] else "⚠️ 超容差"
        if r['pass']:
            n_pass += 1
        lines.append(f"| {r['label']} | {r['pvcalc']:,.1f} | {r['xlsx']:,.1f} | {r['diff_pct']:+.3f}% | {mark} |")
    ok = n_pass == sum(1 for r in results if r['diff_pct'] is not None)
    lines.append("")
    lines.append("✅ 复核通过，数据一致，可输出结论" if ok else
                 "⚠️ 存在超容差项，报告中将标注异常，XLSX 原件供用户复核")
    return "\n".join(lines), ok


def main():
    parser = argparse.ArgumentParser(description="pvcalc vs XLSX 数据复核")
    parser.add_argument("--pvcalc", required=True, help="gsa_pvcalc.py 输出的 JSON")
    parser.add_argument("--xlsx", required=True, help="GSA 原始 XLSX 报告")
    parser.add_argument("--capacity", type=float, default=1000, help="装机容量 kWp")
    parser.add_argument("--format", choices=["json", "table"], default="table")
    parser.add_argument("--parser", default=None,
                        help="gsa_report_parser.py 路径（默认同目录）")
    args = parser.parse_args()

    if not os.path.exists(args.pvcalc) or not os.path.exists(args.xlsx):
        print("ERROR: pvcalc JSON 或 XLSX 文件不存在", file=sys.stderr)
        sys.exit(2)

    parser_path = args.parser or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                              "gsa_report_parser.py")
    try:
        pv = json.load(open(args.pvcalc, encoding='utf-8'))
        xl = parse_xlsx(args.xlsx, parser_path)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    results = compare(pv, xl, args.capacity)
    n = sum(1 for r in results if r['diff_pct'] is not None)
    ok = n > 0 and sum(1 for r in results if r['pass']) == n
    if args.format == "json":
        out = {'ok': ok, 'results': results}
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        table, ok = format_table(results, args.capacity)
        print(table)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

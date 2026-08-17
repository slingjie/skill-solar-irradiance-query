#!/usr/bin/env python3
"""Download the original GSA (Global Solar Atlas) XLSX report via headless browser.

Used in Mode B / A+B as a verification artifact: the downloaded XLSX is parsed
by gsa_report_parser.py and cross-checked against the pvcalc API data
(gsa_verify_xlsx.py), so users can also review the original file.

Usage:
    python3 gsa_download_xlsx.py --loc 30.380793,120.296665 --type medium \
        --capacity 1000 --tilt 0 --azimuth 180 [--out ~/Downloads/xxx.xlsx]

    # 或直接给 GSA map URL（跳过参数构造）
    python3 gsa_download_xlsx.py --url "https://globalsolaratlas.info/map?s=...,10&pv=medium,180,0,1000"

Exit codes:
    0  下载成功，打印文件路径
    2  playwright 不可用（打印 GSA URL，调用方可提示用户手动下载）
    1  其他错误

Dependencies: playwright + chromium（Hermes venv 已装；缺失时优雅降级）。
"""
import argparse
import os
import sys
import time


def build_gsa_url(lat, lng, pv_type, capacity, tilt, azimuth):
    """构造 GSA map URL（与 SKILL.md 降级路径同款）。"""
    return (f"https://globalsolaratlas.info/map?s={lat},{lng},10"
            f"&pv={pv_type},{azimuth},{tilt},{int(capacity)}")


def try_download(url, out_path, timeout_s=120):
    """Playwright 无头下载。返回 True 或抛异常。"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(accept_downloads=True)
        page = ctx.new_page()
        page.set_default_timeout(60000)
        page.goto(url, wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(12000)  # 等地图/面板加载

        body = page.inner_text("body")
        if "Reports" not in body:
            raise RuntimeError("页面未出现 Reports 按钮（可能加载失败/被拦）")
        page.get_by_text("Reports", exact=False).first.click()
        page.wait_for_timeout(4000)
        page.get_by_text("XLSX").first.click()
        page.wait_for_timeout(2000)

        with page.expect_download(timeout=90000) as dl_info:
            page.get_by_text("Download", exact=False).last.click()
        dl = dl_info.value
        dl.save_as(out_path)
        browser.close()
    return True


def main():
    parser = argparse.ArgumentParser(description="下载 GSA 原始 XLSX 报告（headless）")
    parser.add_argument("--loc", default=None, help="纬度,经度（与 --type/--capacity/--tilt/--azimuth 配合）")
    parser.add_argument("--type", default="medium", help="small/medium/large/floating")
    parser.add_argument("--capacity", type=float, default=1000, help="装机容量 kWp（导出固定 1000 精度最高）")
    parser.add_argument("--tilt", type=float, default=15, help="倾角 °")
    parser.add_argument("--azimuth", type=float, default=180, help="方位角 °")
    parser.add_argument("--url", default=None, help="直接给 GSA map URL，跳过参数构造")
    parser.add_argument("--out", required=True, help="XLSX 保存路径（含文件名）")
    parser.add_argument("--timeout", type=int, default=120, help="下载超时秒")
    args = parser.parse_args()

    if args.url:
        url = args.url
    else:
        lat, lng = (float(x) for x in args.loc.split(","))
        url = build_gsa_url(lat, lng, args.type, args.capacity, args.tilt, args.azimuth)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    try:
        try_download(url, args.out, args.timeout)
    except ImportError:
        # playwright 缺失：优雅降级，打印 URL 供手动下载
        print(f"NOTE: playwright 不可用，无法自动下载。请手动打开: {url}")
        print(f"NOTE: 下载后保存为: {args.out}")
        sys.exit(2)
    except Exception as e:
        print(f"ERROR: 下载失败: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"OK: {args.out}")
    sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
GSA 报告综合绘图脚本 — matplotlib 版
用法:
    python3 gsa_plot_summary.py <GSA_Report.xlsx> [--out DIR] [--all]
    python3 gsa_plot_summary.py <pvcalc.json> [--loc 纬度,经度] [--location 地点名] [--all]

支持两种输入：
- GSA XLSX 报告（gsa_report_parser.py 同源，浏览器下载或 pvcalc 失败降级路径）
- pvcalc 接口 JSON（gsa_pvcalc.py --format json 输出，主路径；--loc 用于补 GHI/DIF/GTI_opta）

默认生成 1 张 2×2 综合汇总图（09_combined_summary.png）
--all 生成全部 9 种科研绘图（01-09）

依赖: pandas, numpy, matplotlib (建议用 ~/.hermes/hermes-agent/venv/bin/python3 运行)
"""
import json
import os
import sys
import argparse
import urllib.request

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

MONTHS = ['1月', '2月', '3月', '4月', '5月', '6月',
          '7月', '8月', '9月', '10月', '11月', '12月']
LTA_URL = "https://api.globalsolaratlas.info/data/lta"


def load_data(xlsx_path):
    """从 GSA XLSX 提取全部绘图数据"""
    df_m = pd.read_excel(xlsx_path, sheet_name='Monthly_averages', header=None)
    pvout_specific = df_m.iloc[4:16, 1].astype(float).tolist()
    pvout_total = [float(str(x).replace(',', '')) for x in df_m.iloc[4:16, 2].tolist()]
    dni_monthly = df_m.iloc[4:16, 3].astype(float).tolist()

    df_h = pd.read_excel(xlsx_path, sheet_name='Hourly_profiles', header=None)
    pvout_hourly = df_h.iloc[5:29, 1:13].astype(float).values   # 24h × 12月
    pvout_daily = df_h.iloc[29, 1:13].astype(float).tolist()    # Wh/day
    dni_hourly = df_h.iloc[34:58, 1:13].astype(float).values    # 24h × 12月

    df_map = pd.read_excel(xlsx_path, sheet_name='Map_data', header=None)
    dni = float(df_map.iloc[2, 2])
    ghi = float(df_map.iloc[3, 2])
    dif = float(df_map.iloc[4, 2])
    gti_opta = float(df_map.iloc[5, 2])

    # 地点名（从 Site_info 或 Overview 提取）
    try:
        df_site = pd.read_excel(xlsx_path, sheet_name='Site_info', header=None)
        location = str(df_site.iloc[1, 1]) if df_site.shape[1] > 1 else 'Unknown'
    except Exception:
        location = 'Unknown'

    return {
        'location': location,
        'pvout_specific': pvout_specific,
        'pvout_total': pvout_total,
        'dni_monthly': dni_monthly,
        'pvout_hourly': pvout_hourly,
        'pvout_daily': pvout_daily,
        'dni_hourly': dni_hourly,
        'irr': {'GHI': ghi, 'DNI': dni, 'DIF': dif, 'GTI_opta': gti_opta},
    }


def load_data_json(json_path, location='GSA pvcalc', loc=None):
    """从 gsa_pvcalc.py 输出的 JSON 构造与 XLSX 等价的数据结构。

    loc: "纬度,经度"，用于补 lta 的 GHI/DIF/GTI_opta（pvcalc 只有 DNI/GTI）。
    """
    with open(json_path, encoding='utf-8') as f:
        raw = json.load(f)
    monthly = raw['monthly']['data']
    hourly = raw['monthly-hourly']['data']
    annual = raw['annual']['data']

    pvout_hourly = np.array(hourly['PVOUT_total']).T   # 12×24 → 24×12
    dni_hourly = np.array(hourly['DNI']).T
    pvout_daily = [float(np.sum(hourly['PVOUT_total'][i])) for i in range(12)]  # 典型日 Wh

    irr = {'DNI': float(annual['DNI']), 'GTI_opta': float(annual['GTI'])}
    if loc:
        try:
            lat, lng = (float(x) for x in str(loc).split(','))
            with urllib.request.urlopen(f"{LTA_URL}?loc={lat},{lng}", timeout=30) as r:
                lta_annual = json.load(r)['annual']['data']
            irr.update({'GHI': lta_annual['GHI'], 'DIF': lta_annual['DIF'],
                        'GTI_opta': lta_annual['GTI_opta']})
        except Exception:
            irr.setdefault('GHI', irr['GTI_opta'])
            irr.setdefault('DIF', irr['DNI'])
    else:
        irr['GHI'] = irr['GTI_opta']
        irr['DIF'] = irr['DNI']

    return {
        'location': location,
        'pvout_specific': list(monthly['PVOUT_specific']),
        'pvout_total': list(monthly['PVOUT_total']),
        'dni_monthly': list(monthly['DNI']),
        'pvout_hourly': pvout_hourly,
        'pvout_daily': pvout_daily,
        'dni_hourly': dni_hourly,
        'irr': irr,
    }


def setup_style():
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['PingFang SC', 'Arial Unicode MS', 'Hiragino Sans GB', 'DejaVu Sans'],
        'font.size': 10,
        'axes.titlesize': 12,
        'axes.titleweight': 'bold',
        'figure.dpi': 150,
        'savefig.dpi': 150,
        'savefig.bbox': 'tight',
        'axes.spines.top': False,
        'axes.spines.right': False,
    })


def plot_hourly_curves(d, out_path):
    """图1: 12条逐时曲线叠加（鸭舌帽图）"""
    fig, ax = plt.subplots(figsize=(10, 6))
    hours = list(range(24))
    colors = plt.cm.viridis(np.linspace(0.1, 0.9, 12))
    for i, (month, color) in enumerate(zip(MONTHS, colors)):
        ax.plot(hours, d['pvout_hourly'][:, i], color=color, linewidth=2, label=month)
    ax.set_xlabel('小时')
    ax.set_ylabel('出力 [Wh]')
    ax.set_title(f'逐时出力曲线（按月份）- {d["location"]}')
    ax.set_xlim(0, 23)
    ax.set_xticks(range(0, 24, 2))
    ax.legend(loc='upper left', ncol=3, frameon=False, fontsize=8)
    plt.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_hourly_heatmap(d, out_path):
    """图2: 逐时热力图（24h×12月）"""
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(d['pvout_hourly'].T, aspect='auto', cmap='YlOrRd', origin='lower')
    ax.set_xlabel('小时')
    ax.set_ylabel('月份')
    ax.set_title(f'逐时出力热力图 [Wh] - {d["location"]}')
    ax.set_xticks(range(0, 24, 2))
    ax.set_xticklabels(range(0, 24, 2))
    ax.set_yticks(range(12))
    ax.set_yticklabels(MONTHS)
    plt.colorbar(im, ax=ax, shrink=0.8, label='出力 [Wh]')
    plt.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_monthly_bar_dni(d, out_path):
    """图3: 月度发电量柱状图 + DNI 折线（双Y轴）"""
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.bar(MONTHS, [x / 1000 for x in d['pvout_total']],
            color='#f39c12', alpha=0.85, label='月度发电量')
    ax1.set_xlabel('月份')
    ax1.set_ylabel('月度发电量 [MWh]', color='#f39c12')
    ax1.tick_params(axis='y', labelcolor='#f39c12')
    ax1.set_ylim(0, max(d['pvout_total']) / 1000 * 1.2)
    ax2 = ax1.twinx()
    ax2.plot(MONTHS, d['dni_monthly'], color='#e74c3c', marker='o',
             linewidth=2, markersize=6, label='DNI')
    ax2.set_ylabel('DNI [kWh/m²]', color='#e74c3c')
    ax2.tick_params(axis='y', labelcolor='#e74c3c')
    l1, lab1 = ax1.get_legend_handles_labels()
    l2, lab2 = ax2.get_legend_handles_labels()
    ax1.legend(l1 + l2, lab1 + lab2, loc='upper left', frameon=False)
    ax1.set_title(f'月度发电量与 DNI - {d["location"]}')
    plt.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_daily_hbar(d, out_path):
    """图4: 日均发电量横向条形图"""
    fig, ax = plt.subplots(figsize=(10, 6))
    daily_kwh = [x / 1000 for x in d['pvout_daily']]
    bars = ax.barh(MONTHS, daily_kwh,
                   color=plt.cm.RdYlGn(np.linspace(0.2, 0.9, 12)),
                   edgecolor='white', linewidth=0.5)
    ax.set_xlabel('日均发电量 [kWh/天]')
    ax.set_title(f'各月日均发电量 - {d["location"]}')
    for bar, val in zip(bars, daily_kwh):
        ax.text(bar.get_width() + 20, bar.get_y() + bar.get_height() / 2,
                f'{val:.0f}', va='center', fontsize=9)
    ax.set_xlim(0, max(daily_kwh) * 1.15)
    plt.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_polar_rose(d, out_path):
    """图5: 极坐标玫瑰图（月均日发电量）"""
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
    theta = np.linspace(0, 2 * np.pi, 13)[:-1]
    radii = np.array([x / 1000 for x in d['pvout_daily']])
    norm = plt.Normalize(radii.min(), radii.max())
    ax.bar(theta, radii, width=2 * np.pi / 12 * 0.8, bottom=0.0,
           color=plt.cm.YlOrRd(norm(radii)), edgecolor='white')
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_xticks(theta)
    ax.set_xticklabels(MONTHS)
    ax.set_title(f'月发电量极坐标玫瑰图 - {d["location"]}\n（日均 kWh/天）', pad=20)
    sm = plt.cm.ScalarMappable(cmap='YlOrRd', norm=norm)
    sm.set_array([])
    plt.colorbar(sm, ax=ax, shrink=0.6, pad=0.1, label='kWh/天')
    plt.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_irradiation(d, out_path):
    """图6: GHI/DNI/DIF/GTI 年辐照对比"""
    fig, ax = plt.subplots(figsize=(8, 6))
    x = np.arange(4)
    labels = ['GHI', 'DNI', 'DIF', 'GTI\n最佳倾角']
    colors = ['#3498db', '#e74c3c', '#95a5a6', '#f39c12']
    vals = [d['irr']['GHI'], d['irr']['DNI'], d['irr']['DIF'], d['irr']['GTI_opta']]
    bars = ax.bar(x, vals, color=colors, edgecolor='white', linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel('年辐照量 [kWh/m²]')
    ax.set_title(f'年辐照量组成 - {d["location"]}')
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 20,
                f'{val:.1f}', ha='center', va='bottom', fontweight='bold', fontsize=10)
    ax.set_ylim(0, max(vals) * 1.15)
    plt.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_scatter(d, out_path):
    """图7: PVOUT vs DNI 散点图 + 趋势线"""
    fig, ax = plt.subplots(figsize=(8, 6))
    sc = ax.scatter(d['dni_monthly'], d['pvout_specific'], c=range(12),
                    cmap='viridis', s=120, edgecolors='white', linewidth=1.5)
    for i, month in enumerate(MONTHS):
        ax.annotate(month, (d['dni_monthly'][i], d['pvout_specific'][i]),
                    textcoords="offset points", xytext=(8, 5), fontsize=9)
    z = np.polyfit(d['dni_monthly'], d['pvout_specific'], 1)
    p = np.poly1d(z)
    xl = np.linspace(min(d['dni_monthly']) - 5, max(d['dni_monthly']) + 5, 100)
    ax.plot(xl, p(xl), 'r--', alpha=0.5, label=f'趋势: y={z[0]:.2f}x+{z[1]:.1f}')
    ax.set_xlabel('DNI [kWh/m²]')
    ax.set_ylabel('单位出力 [kWh/kWp]')
    ax.set_title(f'单位出力与 DNI 关系 - {d["location"]}')
    ax.legend(frameon=False)
    plt.colorbar(sc, ax=ax, shrink=0.8, label='月份')
    plt.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_area(d, out_path):
    """图8: 月发电量面积图"""
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.fill_between(MONTHS, d['pvout_specific'], alpha=0.4, color='#f39c12')
    ax.plot(MONTHS, d['pvout_specific'], color='#e67e22', linewidth=2, marker='o')
    ax.set_xlabel('月份')
    ax.set_ylabel('单位出力 [kWh/kWp]')
    ax.set_title(f'各月单位出力面积图 - {d["location"]}')
    for m, v in zip(MONTHS, d['pvout_specific']):
        ax.annotate(f'{v:.1f}', (m, v), textcoords="offset points",
                    xytext=(0, 8), ha='center', fontsize=8)
    ax.set_ylim(0, max(d['pvout_specific']) * 1.15)
    plt.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_combined(d, out_path):
    """图9: 2×2 综合汇总图（默认生成）"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    hours = list(range(24))

    # 左上: 逐时曲线
    ax = axes[0, 0]
    for i, (month, color) in enumerate(zip(MONTHS, plt.cm.viridis(np.linspace(0.1, 0.9, 12)))):
        ax.plot(hours, d['pvout_hourly'][:, i], color=color, linewidth=1.5, label=month)
    ax.set_xlabel('小时')
    ax.set_ylabel('出力 [Wh]')
    ax.set_title('(a) 逐时出力曲线')
    ax.set_xlim(0, 23)
    ax.legend(loc='upper left', ncol=4, frameon=False, fontsize=7)

    # 右上: 月度柱状图 + DNI
    ax = axes[0, 1]
    ax.bar(MONTHS, [x / 1000 for x in d['pvout_total']], color='#f39c12', alpha=0.85)
    ax.set_xlabel('月份')
    ax.set_ylabel('发电量 [MWh]', color='#f39c12')
    ax2 = ax.twinx()
    ax2.plot(MONTHS, d['dni_monthly'], 'ro-', linewidth=1.5, markersize=4)
    ax2.set_ylabel('DNI [kWh/m²]', color='#e74c3c')
    ax.set_title('(b) 月度发电量与 DNI')

    # 左下: 热力图
    ax = axes[1, 0]
    im = ax.imshow(d['pvout_hourly'].T, aspect='auto', cmap='YlOrRd', origin='lower')
    ax.set_xlabel('小时')
    ax.set_ylabel('月份')
    ax.set_yticks(range(12))
    ax.set_yticklabels(MONTHS)
    ax.set_title('(c) 逐时热力图 [Wh]')
    plt.colorbar(im, ax=ax, shrink=0.8)

    # 右下: 辐照对比
    ax = axes[1, 1]
    x_pos = np.arange(4)
    ax.bar(x_pos, [d['irr']['GHI'], d['irr']['DNI'], d['irr']['DIF'], d['irr']['GTI_opta']],
           color=['#3498db', '#e74c3c', '#95a5a6', '#f39c12'])
    ax.set_xticks(x_pos)
    ax.set_xticklabels(['GHI', 'DNI', 'DIF', 'GTI\n最佳倾角'])
    ax.set_ylabel('kWh/m²')
    ax.set_title('(d) 年辐照量对比')

    fig.suptitle(f'GSA 光伏报告汇总 - {d["location"]}',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    fig.savefig(out_path, bbox_inches='tight')
    plt.close(fig)
    return out_path


ALL_PLOTS = [
    ('01_hourly_curves.png', plot_hourly_curves, '12条逐时曲线'),
    ('02_hourly_heatmap.png', plot_hourly_heatmap, '逐时热力图'),
    ('03_monthly_bar_dni_line.png', plot_monthly_bar_dni, '月度柱状+DNI'),
    ('04_daily_horizontal_bar.png', plot_daily_hbar, '日均横向条形'),
    ('05_polar_rose.png', plot_polar_rose, '极坐标玫瑰'),
    ('06_irradiation_comparison.png', plot_irradiation, '辐照对比'),
    ('07_pvout_vs_dni_scatter.png', plot_scatter, 'PVOUT-DNI散点'),
    ('08_area_chart.png', plot_area, '面积图'),
    ('09_combined_summary.png', plot_combined, '2×2综合汇总'),
]


def main():
    parser = argparse.ArgumentParser(description='GSA 报告 matplotlib 综合绘图')
    parser.add_argument('input', help='GSA_Report_*.xlsx 或 gsa_pvcalc.py --format json 输出的 .json')
    parser.add_argument('--out', default=None, help='输出目录（默认: 输入文件同级 charts/ 目录）')
    parser.add_argument('--all', action='store_true', help='生成全部 9 种图（默认只生成 2×2 综合图）')
    parser.add_argument('--loc', default=None, help='经纬度 纬度,经度（JSON 输入时补 GHI/DIF/GTI_opta）')
    parser.add_argument('--location', default=None, help='地点名（JSON 输入时标题用）')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        sys.exit(f'ERROR: 文件不存在: {args.input}')

    out_dir = args.out or os.path.join(os.path.dirname(os.path.abspath(args.input)), 'charts')
    os.makedirs(out_dir, exist_ok=True)

    setup_style()
    if args.input.lower().endswith('.json'):
        d = load_data_json(args.input, args.location or 'GSA pvcalc', args.loc)
    else:
        d = load_data(args.input)
    print(f'地点: {d["location"]}')

    targets = ALL_PLOTS if args.all else ALL_PLOTS[-1:]  # 默认只出综合图
    for fname, fn, desc in targets:
        path = os.path.join(out_dir, fname)
        fn(d, path)
        print(f'✓ {fname} ({desc})')

    print(f'\n输出目录: {out_dir}')


if __name__ == '__main__':
    main()

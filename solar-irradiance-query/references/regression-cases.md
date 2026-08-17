# 回归测试语料（Regression Cases）

> 实测来源：2026-08-17 实跑（Solargis v2.2.68 / GSA lta + pvcalc API / 高德 Web 服务 API）
> 用途：改动 `gsa_pvcalc.py` / `gsa_report_parser.py` / 升级 GSA 接口后，跑 `scripts/regression_test.py`
> 验证口径不回归。容差：数值 ±3%（GSA 数据集升级会导致整体偏移，属于预期漂移，非 bug）。

## Case 1 — 模式A：中文地址 → 地理编码 → lta
- 输入：`杭州市西湖区`（city=杭州）
- 期望：高德编码 → 经度 `120.130396`，纬度 `30.259242`（注意：高德返回「经度,纬度」，传给 GSA 必须交换为「纬度,经度」）
- 期望 lta：GHI=1292.2 kWh/m² | DNI=770.1 | DIF=768.7 | GTI_opta=1374.3 | OPTA=23° | PVOUT_csi=1114.1 kWh/kWp | TEMP=17.1°C | ELE=102m

## Case 2 — 模式A：直接坐标 → lta
- 输入：`31.2304,121.4737`（上海）
- 期望：GHI=1324.6 | DNI=821.2 | DIF=778.7 | OPTA=25° | PVOUT_csi=1166.1 kWh/kWp | TEMP=16.7°C | ELE=9m

## Case 3 — 模式B：中文地址 + PV 配置 → pvcalc
- 输入：`深圳市南山区`（city=深圳）→ OPTA=19° → `gsa_pvcalc.py --loc 22.533191,113.930478 --type medium --capacity 100 --tilt 19 --azimuth 180 --gmt-offset 28800`
- 期望：年 PVOUT_total = **123,363 kWh**（PVOUT_specific=1233.6 kWh/kWp）；7月=12,091 kWh，2月最低=8,489 kWh
- **不变量**：12 个月 PVOUT_total 求和 = 年 PVOUT_total（防「典型日×天数」口径回归，即 SKILL 坑②）

## Case 4 — 模式B：海外坐标 → pvcalc（时区偏移）
- 输入：`21.0285,105.8542`（越南河内）→ `--type medium --capacity 100 --tilt 15 --azimuth 180 --gmt-offset 25200`
- 期望：年 PVOUT_total = **106,085 kWh**（PVOUT_specific=1060.8 kWh/kWp）；7月峰值月=10,839 kWh
- 不变量：月合计 = 年值（同上）

## Case 5 — 异常路径
- a) 海洋坐标 `0,150`：lta **仍返回数据**（GHI≈1978.8）→ 断言「接口不校验坐标」成立，输出必须提示人工合理性判断，不得静默出图
- b) 非法纬度 `120.13,30.26`：lta 必须报错（HTTP 500）→ 走「坐标无效/无数据」异常提示

## 运行方式
```bash
AMAP_WEBSERVICE_KEY=你的key python3 scripts/regression_test.py
# 不传 key 则自动尝试 source ~/.hermes/.env 或 ~/.hermes/profiles/coding/.env
```
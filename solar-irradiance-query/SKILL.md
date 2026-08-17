---
name: solar-irradiance-query
description: "通过地址名称或经纬度查询光伏辐照度(GHI/DNI/PVOUT)、月度发电量、逐时发电曲线。支持两种模式：(A) 基础辐照查询 (B) 逐时发电量+图表。"
triggers:
  # === 基础辐照查询（仅调 API） ===
  - 辐照度、GHI、DNI、散射辐射、DIF
  - 太阳能资源、光伏资源评估
  - 比光伏出力、PVOUT、kWh/kWp
  - 最佳倾角、OPTA、方位角
  - 年等效利用小时、年发电量、kWh/kWp
  - "查一下{地点}的辐照度"
  - "{地点} 太阳能怎么样"
  - "经纬度 {lat}, {lng} 辐照"
  - "坐标 {lat} {lng} 光伏"
  - "{地点} 年发电量"
  - "光伏 年等效利用小时"
  # === 逐时发电量（pvcalc 接口/降级 XLSX + 解析 + 图表） ===
  - 逐时、小时分布、hourly profile、每小时
  - 出力曲线、发电曲线、功率曲线
  - 小时占比、出力集中度
  - "{地点} 逐时发电量"
  - "{地点} 出力曲线"
  - "24小时发电分布"
  - "月度发电量 柱状图"
  - "发电量 曲线图"
  # === 组合查询 ===
  - "{地点} 光伏数据 分析"
  - "{地点} 辐照度 逐时"
  - "{地点} 完整报告"
  - "全面分析 {地点} 光伏"
  - "{地点} 资源评估 发电量"
  # === 地址/坐标 ===
  - 小区、楼宇、厂房、园区、工业园区
  - 经纬度、坐标、latitude、longitude
  # === 行业术语 ===
  - EPC、工商业屋顶、分布式光伏、地面电站
  - 组件倾角、方位角、装机容量、kWp、MWp
  - 辐照量、峰值日照时数、PSH
---

# Solar Irradiance Query SOP

## 两种查询模式

### 模式 A：基础辐照查询（快速，仅调 GSA API）
**触发**：用户问 GHI/DNI/PVOUT/最佳倾角/年发电量 等基础参数
**流程**：地址 → 地理编码 → GSA API → 直接输出表格

### 模式 B：逐时发电量 + 图表（需下载 XLSX 报告）
**触发**：用户问 逐时/小时分布/出力曲线/图表/曲线图 等
**流程**：地址 → 地理编码 → GSA API + clarify PV 配置 → 浏览器下载 XLSX → 解析 → 表格 + 图表

### 自动判断
| 关键词 | 模式 |
|--------|------|
| 辐照度/GHI/DNI/PVOUT/最佳倾角/年发电量 | A |
| 逐时/小时/出力曲线/曲线图/柱状图 | B |
| "分析"/"完整报告"/同时包含辐照+发电量 | A+B |

## 输入格式

**A. 地址/名称**（优先）：用户提供地名、小区、楼宇、地标等  
**B. 经纬度**：用户直接给坐标（跳过地理编码步骤）

## 核心流程

### Step 1：判断输入类型 + 模式

| 输入类型 | 模式判断 |
|----------|----------|
| 经纬度（数字+度） | 用户问的是辐照度 → A；问的是逐时/曲线 → B |
| 地址/名称（中文/文字） | 同上，按关键词判断 |

### Step 2：地理编码（地址 → 经纬度）

**方案优先级：高德 Web 服务 API（首选）> Web Search > 浏览器高德地图**

#### 方案 A：高德 Web 服务 API（首选，一键直达）

直接调高德 REST API 返回精确经纬度，**无需浏览器**（高德/百度/腾讯网页版均有滑块验证码，headless 基本不可用）。

**前置条件**：环境变量 `AMAP_WEBSERVICE_KEY`（高德开放平台 Web 服务 Key）：

```bash
# 已配置于 ~/.hermes/.env（Hermes 全局 env，不在 GitHub 仓库内）
# 后台 terminal 不继承环境变量，先 source：
source ~/.hermes/.env 2>/dev/null
# 或临时指定：export AMAP_WEBSERVICE_KEY=你的key
```

**地理编码**（地名 → 坐标）：

```bash
curl -s "https://restapi.amap.com/v3/geocode/geo?address={地址}&city={城市}&output=JSON&key=${AMAP_WEBSERVICE_KEY}"
```

返回 `geocodes[0].location`，格式 `经度,纬度`。

**POI 搜索**（地理编码查不到的 POI，如已撤并的学校/村庄）：

```bash
curl -s "https://restapi.amap.com/v3/place/text?keywords={关键词}&city={城市}&output=JSON&key=${AMAP_WEBSERVICE_KEY}"
```

返回 `pois[0].location`，可能有多个候选，按 name/address 匹配判断。

**解析规则：**
- `status` = "1" 且 `count` > 0 → 提取 `geocodes[0].location` / `pois[0].location`
- 多个候选 → 列出让用户选择
- `status` ≠ "1" → key 无效或地址无效
- 查不到 → 进入方案 B

**实测案例**（2026-08）：某已撤并的乡镇小学（已并入镇中心小学），web_search/高德网页/腾讯/百度地图全部被验证码拦截，高德 API 一次返回精确坐标。

#### 方案 B：Web Search（兜底）

用 web_search 搜索 `{地址名称} 经纬度` 或 `{地址名称} 坐标`。

**解析规则：**
- 搜索结果中明确包含 `地理坐标：`、`经纬度：`、`坐标：` 等关键词的 → 提取数字
- 结果为高德/百度地图链接且描述中含坐标 → 提取坐标
- 搜索结果模糊或不含坐标 → 进入方案 C

#### 方案 C：浏览器高德地图（最后兜底）

```bash
browser_navigate("https://www.amap.com/")
browser_type 搜索框 → 输入地址
browser_snapshot → 提取结果
```

> ⚠️ 2026-08 实测：高德/百度/腾讯网页版均有滑块验证码，headless 浏览器基本不可用；此方案仅作最后手段。

#### 方案 D：无法获取经纬度（异常处理）

若方案 A/B/C 均无法获取经纬度，或搜索结果有多个候选位置无法确定唯一匹配：

**必须向用户反馈，示例回复：**

```
⚠️ 无法找到"{地址名称}"的精确经纬度。

请提供以下任一信息：
1. 更详细的地址（如：XX市XX区XX路XX号）
2. 高德/百度地图中的坐标（如：30.44, 120.29）
3. 高德地图链接（如：https://www.amap.com/place/xxx）
```

**禁止行为：**
- ❌ 搜索结果模糊时自行选取第一个结果
- ❌ 搜索不到时用"附近"或"城市中心"坐标替代
- ❌ 静默失败后继续输出数据

### Step 3：坐标系处理

- 高德/百度坐标为 GCJ-02 → 若需精确（非光伏可忽略），转换为 WGS-84
- GSA API 对 GCJ-02 和 WGS-84 的辐照度差异 <0.1%，可直接使用 GCJ-02
- 全球其他地区坐标 → 确认坐标系（默认 WGS-84）

### Step 4：调用 GSA API

```bash
curl -s "https://api.globalsolaratlas.info/data/lta?loc=纬度,经度"
```

**API 返回判断：**
- 正常返回 JSON 含 `annual.data.GHI` → 继续
- 返回空 JSON 或无 `annual` 字段 → 该坐标无数据（海洋/极地/异常坐标）
- HTTP 错误/超时 → 网络异常

**⚠️ 字段名注意（实测 2026-08）：** lta 接口 `annual.data` 的比光伏出力字段是 **`PVOUT_csi`**（不是 `PVOUT`，按 `PVOUT` 取值会 KeyError）。完整字段：`PVOUT_csi` / `DNI` / `GHI` / `DIF` / `GTI_opta` / `OPTA` / `TEMP` / `ELE`。

### Step 5：异常处理

| 场景 | 处理 |
|------|------|
| API 返回正常 JSON | 继续 |
| API 返回空数据或报错 | 回复用户：该坐标暂无法获取辐照度数据，请确认地址是否正确 |
| API 超时/HTTP 错误 | 回复用户：辐照度服务暂时不可用，请稍后重试 |
| 地理编码失败 | 按方案 C 反馈用户 |

## 输出格式（严格固定）

### 模式 A：基础辐照查询输出

```
📍 **{位置名称}** ({纬度}°, {经度}°)

## 辐照度数据（年累计）
- **GHI（总水平辐射）**: {X} kWh/m²
- DNI（直接法向）: {X} kWh/m²
- DIF（散射水平）: {X} kWh/m²
- GTI opta（最佳倾角）: {X} kWh/m²
- 最佳倾角: {X}°

## 光伏数据
- **PVOUT（比光伏出力）**: {X} kWh/kWp（lta 接口字段名 `PVOUT_csi`）
- 气温: {X} °C
- 海拔: {X} m

## 月度数据
| 月份 | GHI | DNI | DIF | GTI | PVOUT | 气温 |
|------|-----|-----|-----|-----|-------|------|
| 1月  |     |     |     |     |       |      |
| 2月  |     |     |     |     |       |      |
| 3月  |     |     |     |     |       |      |
| 4月  |     |     |     |     |       |      |
| 5月  |     |     |     |     |       |      |
| 6月  |     |     |     |     |       |      |
| 7月  |     |     |     |     |       |      |
| 8月  |     |     |     |     |       |      |
| 9月  |     |     |     |     |       |      |
| 10月 |     |     |     |     |       |      |
| 11月 |     |     |     |     |       |      |
| 12月 |     |     |     |     |       |      |

## 发电量估算
- 1kWp 年发电量 ≈ {PVOUT_csi} kWh
```

### 模式 B：逐时发电量 + 图表输出（详见下方逐时数据获取）

## 月度数据填充规则

- `monthly.data.GHI` 为 12 元素数组，index 0 = 1月，index 11 = 12月
- 数值保留两位小数（或按原始精度）
- 表格中数字右对齐可用 `:---:`，左对齐 `:---`

## 地理编码质量检查

获取坐标后，必须执行：

1. **数量检查**：是否只有唯一结果？多个候选 → 列出让用户选择
2. **合理性检查**：纬度 [-90, 90]，经度 [-180, 180]；中国境内纬度约 18-54°，经度约 73-135°
3. **描述匹配**：搜索结果描述中的地址是否与用户输入匹配？

## 错误示例

**错误输出（禁止）：**

> 查询了该小区的辐照度，GHI 为 1325 kWh/m²...

（原因：地址模糊时自行取了结果，未反馈用户确认）

**正确输出：**

> ⚠️ 搜索"XX花园"找到多个候选位置：
> 1. XX花园 - XX市XX区（坐标 30.44, 120.29）
> 2. XX花园 - XX市XX区（坐标 31.23, 121.47）
> 请确认是哪个位置？

## API 技术规格

- 无需认证 / API Key
- CORS 开放
- 坐标顺序：`纬度,经度`（lat,lng）
- 响应 <200ms
- 数据版本：Solargis v2.2.68
- 数据来源：GHI/DNI/TEMP/OPTA/ALBEDO/ELE

## 工具依赖

| 步骤 | 工具 |
|------|------|
| 地理编码（首选） | `terminal` (curl 高德 REST API，key 取自 `$AMAP_WEBSERVICE_KEY`) |
| 地理编码（兜底） | `web_search` |
| 地理编码（最后兜底） | `browser_navigate`, `browser_type`, `browser_snapshot` |
| 辐照度查询（模式 A） | `terminal` (curl lta API) |
| 逐时数据（模式 B 首选） | `terminal` (`gsa_pvcalc.py` → pvcalc API，见上方 Step 3) |
| 逐时数据（模式 B 降级） | `browser` 下载 XLSX + `gsa_report_parser.py` |
| 坐标系转换 | `terminal` (python3) |
| 图表生成 | `gsa_plot_summary.py`（matplotlib，9 种图，见 5.8） |

## 逐时数据获取（模式 B 专用）

**触发条件**：用户说"逐时"、"小时分布"、"hourly profile"、"每小时"、"出力曲线"、"曲线图"、"柱状图"等关键词。

**流程**：

### Step 1：确认 PV 系统配置（必须问用户，用选择项）

使用 `clarify` 工具逐项询问，**禁止让用户自由输入**。

**1.1 系统类型**（单选）：

```
choices=["Small residential（住宅）", "Medium size commercial（工商业屋顶）", "Ground-mounted large scale（地面电站）", "Floating large scale（水面）"]
```

**1.2 装机容量**（单选）：

```
choices=["10 kWp", "50 kWp", "100 kWp", "500 kWp", "1000 kWp (1MW)", "5000 kWp (5MW)", "10000 kWp (10MW)"]
```

**1.3 组件倾角**（单选）：

先调 GSA API 获取最佳倾角（OPTA），然后：

```
choices=[f"最佳倾角（{OPTA}°）", "平铺（0°）", "15°", "20°", "25°", "30°", "35°", "40°"]
```

**1.4 方位角**（单选）：

```
choices=["正南（180°）", "东南（135°）", "西南（225°）", "正东（90°）", "正西（270°）"]
```

**禁止行为**：
- ❌ 不询问用户就默认选 medium 100kWp
- ❌ 让用户自由输入容量/类型
- ❌ 用纯气象报告（只有 DNI）冒充 PV 报告

### Step 2：获取坐标 + OPTA

1. 地理编码获取经纬度
2. 调用 GSA API 获取最佳倾角（OPTA）

```bash
curl -s "https://api.globalsolaratlas.info/data/lta?loc=纬度,经度" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['annual']['data']['OPTA'])"
```

### Step 3：获取逐时数据（首选 pvcalc 接口，XLSX 下载降级）

**主路径（首选）：调用 GSA pvcalc 接口，一次返回年/月/逐时全部数据，无需浏览器。**

```bash
python3 <skill目录>/scripts/gsa_pvcalc.py \
  --loc 纬度,经度 --type medium --capacity 1000 \
  --tilt 15 --azimuth 180 --gmt-offset 28800 --format json
```

| 参数 | 说明 | 可选值 |
|------|------|--------|
| `--loc` | 经纬度 | `纬度,经度`（如 `30.274100,120.058900`） |
| `--type` | 系统类型 | `small` / `medium` / `large` / `floating` |
| `--capacity` | 装机容量 kWp | **传项目实际容量**（脚本按此换算 PVOUT_total，零换算） |
| `--tilt` | 倾角 ° | 度数或 OPTA 值 |
| `--azimuth` | 方位角 ° | `180`=正南（默认） |
| `--gmt-offset` | 时区偏移秒 | 中国 `28800`，越南 `25200` |
| `--format` | 输出 | `json`（默认）/ `table` |

**type → pvcalc 原生值映射**（来源：GSA 前端 bundle `chunk-CD6ZCY4X.js` 枚举 `n_`，2026-08 实测验证）：

| GSA URL pv= 参数 | pvcalc `type` | 含义 |
|---|---|---|
| `small` | `rooftopSmall` | 小型住宅屋顶 |
| `medium` | `rooftopLargeFlat` | 工商业平屋顶 |
| `large` | `groundFixed` | 地面固定式 |
| `floating` | `hydroMountedLargeScale` | 水面/水库漂浮式 |
| （另有） | `rooftopLargeTilted` / `buildingIntegrated` / `trackerOneAxisHorizontalNS` / `noPvSystem` | 斜屋顶 / BIPV / 单轴跟踪 / 无系统 |

**返回结构（对应 XLSX 分表）：**
- `annual.data` — 年累计（PVOUT_specific: kWh/kWp、PVOUT_total: kWh、GTI、DNI）
- `monthly.data` — 月度（各 12 元素数组）
- `monthly-hourly.data` — **典型日**逐时（各 12×24：PVOUT_specific: Wh/kWp、PVOUT_total: Wh、DNI: Wh/m²、GTI: Wh/m²）

**⚠️ 三个已知坑（2026-08 实测）：**
1. **接口不校验坐标**：海洋坐标也返回数据；非法坐标/极地返回 HTTP 500（脚本已捕获并提示"坐标无效"）。地理编码后仍需人工确认坐标合理。
2. **monthly-hourly 是典型日**：日值 × 当月天数 = 月累计（实测 12 个月全部精确吻合）。逐时表标注"典型日"口径；月累计直接用 `monthly.data`，不要自乘天数。
3. **接口为非公开网关**（execute-api），可能变更；失败时降级走 XLSX 路径（见下）。

**降级路径（pvcalc 失败时）：构造 GSA URL 下载 XLSX**

GSA 支持 URL 参数预配置 PV 系统，可直接跳转：

```
https://globalsolaratlas.info/map?s=纬度,经度,10&pv=类型,方位角,倾角,容量
```

| 参数 | 说明 | 可选值 |
|------|------|--------|
| `s=` | 坐标+缩放 | `纬度,经度,10`（10=缩放级别） |
| `pv=` | PV 配置 | `类型,方位角,倾角,容量` |
| 类型 | 系统类型 | `small` / `medium` / `large` / `floating` |
| 方位角 | 朝向 | `180`=正南（默认） |
| 倾角 | 角度 | 度数或 OPTA 值 |
| 容量 | 装机容量 | **导出固定用 `1000`**（1kWp 文件小时值四舍五入严重，1000kWp 精度高；输出时按项目容量换算） |

**下载步骤**：
1. `browser_navigate` 到构造的 URL
2. 等待页面加载（右侧面板应显示 PV 系统数据）
3. 找到并点击 `Reports` 按钮
4. 选择 `Data – XLSX format`
5. 点击 `Download`
6. 文件保存到 `~/Downloads/GSA_Report_<地点名>.xlsx`

### Step 4：解析数据

**pvcalc 主路径（JSON 已结构化，无需额外解析）：**

```bash
# 直接解析 gsa_pvcalc.py 输出的 JSON：
# - annual.data          → 年累计
# - monthly.data         → 月度（12 元素数组）
# - monthly-hourly.data  → 典型日逐时（12×24）
# 也可直接看 --format table 的可读输出
python3 <skill目录>/scripts/gsa_pvcalc.py --loc ... --tilt ... --format table
```

**XLSX 降级路径（pvcalc 失败时）：**

```bash
python3 <skill目录>/scripts/gsa_report_parser.py <file.xlsx> --format json
```

返回结构包含：
- `Overview` — 报告概览
- `Site_info` — 站点信息
- `PV_config` — PV 系统配置（容量、倾角、方位角）
- `Map_data` — 年累计辐照度
- `Monthly_averages` — **月发电量**（PVOUT_specific + PVOUT_total + DNI）
- `Hourly_profiles` — **逐时发电量**（PVOUT_total: Wh）+ 逐时 DNI（Wh/m²）

**异常处理：**
- pvcalc 返回 `ERROR:` 开头 → 按错误信息处理（坐标无效/网络/超时），确认后可降级 XLSX
- 脚本返回 `ERROR:` 开头 → 回复用户：XLSX 解析失败，请检查文件是否完整
- 脚本返回 `error` 字段在某个 sheet → 回复用户：部分数据解析异常，可用 `--format table` 查看详情
- 下载后文件不存在 → 回复用户：下载失败，请手动下载后重试
- 文件存在但解析结果全为空 → 回复用户：报告数据为空，可能坐标无数据

### Step 5：输出结果（模式 B 固化格式）

解析完成后，**必须按以下顺序输出**，不得省略：

**⛔ 最高优先级规则：所有数字必须来自解析脚本输出，禁止任何形式的编造、推算、四舍五入。直接复制粘贴 parser 输出的表格内容。**

**5.1 数据来源**

```text
📡 数据来源：GSA pvcalc API（2026-08-08，Solargis v2.2.68）   ← pvcalc 主路径
📁 或已保存：~/Downloads/GSA_Report_<地点名>.xlsx            ← XLSX 降级路径
```

**5.2 站点概览**

```
📍 地点：<位置名称>
🗺 坐标：lat°, lng°（海拔 m）
🕐 时区：Asia/Shanghai
📅 报告日期：YYYY-MM-DD
```

**5.3 PV 系统配置**

```
⚡ PV 配置：<类型> | <容量> kWp | 倾角 <°> | 方位角 <°>
```

**5.4 年累计数据（表格）**

| 指标 | 值 |
|------|-----|
| GHI | xxx kWh/m² |
| DNI | xxx kWh/m² |
| DIF | xxx kWh/m² |
| GTI_opta | xxx kWh/m² |
| **年发电量** | **xxx,xxx kWh (x.xx GWh)** |
| 年等效利用小时 | xxx h（= 年发电量 ÷ 装机容量 = 单位出力 PVOUT_specific） |
| 最佳倾角 | xxx° |
| 海拔 | xxx m |
| 年均温度 | xx.x °C |

**⚠️ 口径注意（2026-08 实测修正）：**
- **等效利用小时** = 年发电量 ÷ 装机容量 = **单位出力 PVOUT_specific**（kWh/kWp 数值上即小时数），如 1026.71 kWh/kWp → ≈1027 h
- **PSH（峰值日照小时）** = GTI ÷ 1000 W/m²（如 1286.4 kWh/m² → 1286.4 h），是**理论辐射资源**，不是发电利用小时
- 禁止用 GTI/PSH 冒充等效利用小时；两者关系：单位出力 = GTI × 系统效率（≈0.80）

**5.5 月度数据（表格，全年 12 个月）**

| 月 | 发电量 (kWh) | 单位出力 (kWh/kWp) | DNI (kWh/m²) |
|----|-------------|-------------------|--------------|
| 1月 | xxx | xx.x | xx.x |
| 2月 | xxx | xx.x | xx.x |
| ... | ... | ... | ... |
| **年** | **xxx,xxx** | **xxx.x** | **xxx.x** |

**5.6 逐时发电量**

- 默认展示 7月（夏季峰值）和 12月（冬季低谷），**合并为一张表格**
- 用户指定月份 → 展示该月 24 小时
- 用户明确要求"全年" → 展示 12 个月完整数据
- 展示 PVOUT（Wh）+ **小时占比（%）**
- 占比 = 小时 PVOUT / 当日（典型日）24h 总和 × 100%（monthly-hourly 为典型日口径，分母用当天 24h 之和，勿用月累计值）

**默认展示格式（7月+12月合表）：**

| 小时 | 7月 出力 (Wh) | 7月 占比 | 12月 出力 (Wh) | 12月 占比 |
|------|-------------|---------|-------------|----------|
| 0 - 1 | | | | |
| ... | ... | ... | ... | ... |

输出后提示：
```
以上是 7月（夏季峰值）和 12月（冬季低谷）逐时发电量及占比。如需其他月份请告知。
```

**5.7 验证提示**

```
✓ 校验：Jan PVOUT 月累计 xxx Wh × 31天 = xx,xxx kWh ≈ 月度数据 xx,xxx kWh ✓
```

**5.8 matplotlib 综合图（2×2 汇总，所有图表统一走此方案）**

用户要"汇总图/综合图/科研绘图/报告图"时，用 matplotlib 生成 2×2 综合图：

```bash
# 默认：只生成 2×2 综合图 → <xlsx目录>/charts/09_combined_summary.png
~/.hermes/hermes-agent/venv/bin/python3 <skill目录>/scripts/gsa_plot_summary.py "<file.xlsx>"

# 全部 9 种科研绘图（01-09）
~/.hermes/hermes-agent/venv/bin/python3 <skill目录>/scripts/gsa_plot_summary.py "<file.xlsx>" --all

# pvcalc 主路径（JSON 输入，无需 XLSX）：--loc 补 GHI/DIF/GTI_opta，--location 设地点名
~/.hermes/hermes-agent/venv/bin/python3 <skill目录>/scripts/gsa_plot_summary.py <pvcalc.json> --loc 纬度,经度 --location "地点名" [--all]
```

**9 种图清单：**

| 文件 | 内容 | 用途 |
|------|------|------|
| 01_hourly_curves.png | 12条逐时曲线叠加 | 鸭舌帽图，日变化+季节对比 |
| 02_hourly_heatmap.png | 24h×12月热力图 | 紧凑看双维变化 |
| 03_monthly_bar_dni_line.png | 月度柱状+DNI双Y轴 | 可研报告经典图 |
| 04_daily_horizontal_bar.png | 日均发电量横向条形 | 快速对比月份 |
| 05_polar_rose.png | 极坐标玫瑰图 | 报告封面/视觉冲击 |
| 06_irradiation_comparison.png | GHI/DNI/DIF/GTI对比 | 资源评估 |
| 07_pvout_vs_dni_scatter.png | PVOUT-DNI散点+趋势线 | 相关性分析 |
| 08_area_chart.png | 月度面积图 | 总量感 |
| 09_combined_summary.png | 2×2 综合汇总 | 一页看全 |

**注意：**
- 必须用 `~/.hermes/hermes-agent/venv/bin/python3` 运行（matplotlib 装在该 venv）
- 输出默认到 `<xlsx同目录>/charts/`，用 `--out` 指定目录
- 生成后用 `open_preview` 或 MEDIA: 路径展示给用户

## 回归测试

改动 `gsa_pvcalc.py` / `gsa_report_parser.py` 或怀疑 GSA 接口口径变化时，跑回归比对：

```bash
python3 scripts/regression_test.py   # 需 AMAP_WEBSERVICE_KEY（脚本自动 source ~/.hermes/.env 或 coding .env）
```

语料与期望值见 `references/regression-cases.md`：5 个案例、18 项断言（含「月合计=年值」口径不变量与异常路径），容差 ±3%。退出码 0 = 全部通过。

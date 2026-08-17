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

**输出：按下方「📄 报告 A：基础辐照查询」模板输出（5 节，emoji 1️⃣-5️⃣），数据日期、时区取当前查询实际值。模式 A 无需确认 PV 配置、无需下载 XLSX。**

### Step 5：异常处理

| 场景 | 处理 |
|------|------|
| API 返回正常 JSON | 继续 |
| API 返回空数据或报错 | 回复用户：该坐标暂无法获取辐照度数据，请确认地址是否正确 |
| API 超时/HTTP 错误 | 回复用户：辐照度服务暂时不可用，请稍后重试 |
| 地理编码失败 | 按方案 C 反馈用户 |

## 输出格式（严格固定，三份报告模板）

**⛔ 最高优先级规则：所有数字必须来自脚本输出，禁止编造、推算、四舍五入。**
**所有报告必须按下述章节顺序、emoji 编号输出，不得省略、不得改序、不得改名。**

### 全局字段来源映射

| 输出字段 | 来源接口 | 说明 |
|---|---|---|
| GHI / DIF / GTI_opta / OPTA / TEMP / ELE / PVOUT_csi | lta annual / monthly | 气象口径，模式 A 数据源 |
| PVOUT_specific / PVOUT_total / GTI(配置倾角) | pvcalc annual / monthly | 按用户 PV 配置 |
| 年 DNI | pvcalc（已自动覆盖为 lta 气象口径） | gsa_pvcalc.py 处理 |
| 月度 DNI | pvcalc monthly | 配置口径，与 GSA XLSX Monthly_averages 一致 |
| 逐时 PVOUT / DNI | pvcalc monthly-hourly | **典型日**口径（日值 × 当月天数 = 月累计） |
| GHI / DIF / GTI_opta（模式 B 年累计表需要时） | lta annual | pvcalc 不返回，须额外调 lta 补齐 |

### 全局数值精度

| 类型 | 精度 | 示例 |
|---|---|---|
| 辐照 kWh/m²（年累计/月度） | 1 位小数 | 1329.5 |
| 发电量 kWh | 整数 + 千分位 | 1,060,570 |
| 单位出力 kWh/kWp | 2 位小数 | 1060.57 |
| 逐时出力 Wh | 整数 + 千分位 | 506,410 |
| 占比 % | 1 位小数 | 12.6% |
| 等效利用小时 h | 整数 | 1061 |
| 坐标 | 6 位小数 | 30.380793 |

### 文件输出约定（固化）

**输出根目录**：`<用户下载目录>/solar-reports/`（macOS `~/Downloads/solar-reports/`；可用环境变量 `SOLAR_REPORT_ROOT` 覆盖，给别人用时同理）。

每次查询在 `{根目录}/{位置名称}/{YYYYMMDD}/` 新建目录，历史留档不覆盖：

```
solar-reports/{位置名称}/{YYYYMMDD}/
├── charts/
│   ├── 09_combined_summary.png   ← 默认必有（2×2 综合图）
│   └── 01~08_*.png               ← --all 时 01-09 全出
├── {位置名称}_pvcalc.json        ← pvcalc 原始数据
├── {位置名称}_报告.md            ← 报告全文（与聊天输出一致）
└── GSA_Report_{位置名称}.xlsx    ← GSA 原件（gsa_download_xlsx.py 自动下载，复核用）
```

### 📄 报告 A：基础辐照查询（模式 A，共 5 节）

```markdown
# 📍 {位置名称} — 光伏辐照报告（模式 A）

1️⃣ **站点信息**
📍 地点：{位置名称} | 🗺 坐标：{lat}°, {lng}°（海拔 {ELE} m）| 🕐 时区：{Asia/Shanghai 等} | 📅 数据日期：{YYYY-MM-DD} | 📡 数据源：GSA lta（Solargis v2.2.68）

2️⃣ **辐照资源（年累计）**

| 指标 | 值 |
|---|---|
| GHI（总水平辐射） | {X} kWh/m² |
| DNI（直接法向） | {X} kWh/m² |
| DIF（散射水平） | {X} kWh/m² |
| GTI_opta（最佳倾角辐射） | {X} kWh/m² |
| 最佳倾角 OPTA | {X}° |

3️⃣ **光伏参数**

| 指标 | 值 |
|---|---|
| PVOUT_csi（标准比出力） | {X} kWh/kWp |
| 年均温度 | {X} °C |
| 海拔 | {X} m |

4️⃣ **月度辐照**

| 月份 | GHI (kWh/m²) | DNI (kWh/m²) | DIF (kWh/m²) | GTI_opta (kWh/m²) | PVOUT_csi (kWh/kWp) | 气温 (°C) |
|------|------|------|------|------|------|------|
| 1月 | {X} | {X} | {X} | {X} | {X} | {X} |
| 2月 | | | | | | |
| ...（12 个月全列） | | | | | | |
| **年** | **{12月求和}** | | | | | |

5️⃣ **发电量估算**
- 1kWp 年发电量 ≈ {PVOUT_csi} kWh
```

### 📄 报告 B：逐时发电量（模式 B，共 7 节）

```markdown
# 📍 {位置名称} — 光伏发电量报告（模式 B）

1️⃣ **站点信息**
📍 地点：{位置名称} | 🗺 坐标：{lat}°, {lng}°（海拔 {ELE} m）| 🕐 时区：{时区} | 📅 数据日期：{YYYY-MM-DD} | 📡 数据源：GSA pvcalc + XLSX 复核（Solargis v2.2.68）

2️⃣ **PV 系统配置**
⚡ {类型} | {容量} kWp | 倾角 {tilt}° | 方位角 {azimuth}°

3️⃣ **年累计发电量**

| 指标 | 值 |
|---|---|
| **年发电量** | **{X} kWh（{Y} GWh）** |
| 单位出力 | {X} kWh/kWp |
| 等效利用小时 | {X} h（= 年发电量 ÷ 容量，禁止用 GTI/PSH 冒充） |
| GTI（{tilt}° 组件平面） | {X} kWh/m² |
| DNI（气象口径） | {X} kWh/m² |
| 最佳倾角 | {X}° |
| 海拔 | {X} m |
| 年均温度 | {X} °C |

4️⃣ **月度发电量**

| 月 | 发电量 (kWh) | 单位出力 (kWh/kWp) | DNI (kWh/m²) |
|----|-------------|-------------------|--------------|
| 1月 | {X} | {X} | {X} |
| ...（12 个月全列） | | | |
| **年** | **{12月求和}** | **{X}** | **{X}** |

5️⃣ **逐时发电量（典型日）**

- 默认 7月（夏季峰值）+ 12月（冬季低谷）合并一张表，24 行全列
- 用户指定月份 → 该月 24 小时；要求全年 → 12 个月完整数据
- 占比 = 小时 PVOUT ÷ 当日 24h 总和 × 100%（典型日口径，分母用当天 24h 之和）

| 小时 | 7月 出力 (Wh) | 7月 占比 | 12月 出力 (Wh) | 12月 占比 |
|------|-------------|---------|-------------|----------|
| 00-01 | {X} | {X}% | {X} | {X}% |
| ...（24 行全列） | | | | |

> 输出后附提示：以上是 7月（夏季峰值）和 12月（冬季低谷）逐时发电量及占比，典型日口径。如需其他月份请告知。

6️⃣ **数据校验**

```
✓ 7月典型日 {X} Wh × 31天 = {Y} kWh = 月度数据 {Z} kWh ✓（12 个月全部吻合）
✓ 数据复核：pvcalc vs GSA XLSX 原件 → 年/月/逐时峰值偏差 <0.5%/1.0%，✅ 通过
```

- 复核失败 → 标注 ⚠️ 并附 gsa_verify_xlsx.py 偏差表，XLSX 原件供用户复核
- XLSX 不可用 → 标注"未复核，原件请到 GSA 官网下载"

7️⃣ **图表附件**

```
📊 综合图：{输出目录}/charts/09_combined_summary.png
📁 文件目录：{输出目录}/（json / xlsx / 报告.md / charts/）
```

- 图表用 matplotlib（gsa_plot_summary.py，见下），MEDIA: 或 open_preview 展示综合图
```

### 📄 报告 A+B：完整报告（10 节 + 📊 图表）

```markdown
# 📍 {位置名称} — 光伏辐照完整报告

## 第一部分 · 辐照资源

1️⃣ **站点信息**（同报告 A 1️⃣，数据源标注 lta + pvcalc）
2️⃣ **辐照资源（年累计）**（同报告 A 2️⃣）
3️⃣ **光伏参数**（同报告 A 3️⃣）
4️⃣ **月度辐照**（同报告 A 4️⃣）
5️⃣ **发电量估算（标准配置）**（同报告 A 5️⃣）

## 第二部分 · 发电量（按实际 PV 配置）

6️⃣ **PV 系统配置**（同报告 B 2️⃣）
7️⃣ **年累计发电量**（同报告 B 3️⃣）
8️⃣ **月度发电量**（同报告 B 4️⃣）
9️⃣ **逐时发电量（典型日）**（同报告 B 5️⃣）
🔟 **数据校验**（同报告 B 6️⃣）

📊 **图表附件**（同报告 B 7️⃣）
```

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
| XLSX 原件下载（复核用） | `gsa_download_xlsx.py`（Playwright 无头，缺失时给出 GSA URL 手动下载） |
| 数据复核 | `gsa_verify_xlsx.py`（pvcalc vs XLSX，容差 0.5%/1.0%，见 Step 4.5） |
| 逐时数据（模式 B 降级） | `browser` 下载 XLSX + `gsa_report_parser.py` |
| 坐标系转换 | `terminal` (python3) |
| 图表生成 | `gsa_plot_summary.py`（matplotlib，9 种图，见「输出格式」📄 报告 B 7️⃣） |

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

**XLSX 原件下载（模式 B 常规步骤，复核用）：**

每次模式 B / A+B 都下载 GSA 原始 XLSX 到输出目录，供复核与用户留档：

```bash
~/.hermes/hermes-agent/venv/bin/python3 <skill目录>/scripts/gsa_download_xlsx.py \
  --loc 纬度,经度 --type medium --capacity 1000 --tilt 0 --azimuth 180 \
  --out "{输出目录}/GSA_Report_{位置名称}.xlsx"
```

- 脚本用 Playwright 无头浏览器自动点击下载（约 15-20 秒），无需人工
- playwright 缺失 → 脚本 exit 2 并打印 GSA URL，报告标注"原件请到 GSA 官网下载"
- 手动兜底：打开构造的 URL → 点 `Reports` → `Data – XLSX format` → `Download`

**降级路径（pvcalc 失败时）：构造 GSA URL 下载 XLSX 并用 parser 解析**

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

### Step 4.5：数据复核（模式 B / A+B 必做）

pvcalc 数据与 XLSX 原件交叉核对，**一致后才输出结论**：

```bash
~/.hermes/hermes-agent/venv/bin/python3 <skill目录>/scripts/gsa_verify_xlsx.py \
  --pvcalc {输出目录}/{位置名称}_pvcalc.json \
  --xlsx {输出目录}/GSA_Report_{位置名称}.xlsx --capacity 1000
```

- 容差：年/月 <0.5%，逐时峰值 <1.0%（XLSX 小时值四舍五入所致）
- 退出码 0 → 复核通过，正常输出报告
- 退出码 1 → 存在超容差项，报告 6️⃣ 数据校验节标注 ⚠️ 并附偏差表，XLSX 原件供用户复核
- XLSX 不可用（playwright 缺失/下载失败）→ 跳过复核，报告标注"未复核，原件请到 GSA 官网下载"

### Step 5：输出报告

按「## 输出格式（严格固定，三份报告模板）」输出，模式决定报告版本：

| 模式 | 输出 |
|------|------|
| 模式 A | 📄 报告 A（5 节，emoji 1️⃣-5️⃣） |
| 模式 B | 📄 报告 B（7 节，emoji 1️⃣-7️⃣） |
| 模式 A+B | 📄 报告 A+B（10 节 + 📊 图表） |

输出步骤（顺序固定）：

1. **生成图表** → `{输出目录}/charts/`（gsa_plot_summary.py，JSON 输入；默认 09 综合图，用户要"科研图/全套图"则 `--all` 出 01-09）
2. **保存报告全文** → `{输出目录}/{位置名称}_报告.md`（与聊天输出逐字一致）
3. **展示**：MEDIA: 路径展示综合图，必要时 open_preview
4. 全部数字来自脚本输出，禁止推算（见「输出格式」顶部 ⛔ 规则）

## 回归测试

改动 `gsa_pvcalc.py` / `gsa_report_parser.py` 或怀疑 GSA 接口口径变化时，跑回归比对：

```bash
python3 scripts/regression_test.py   # 需 AMAP_WEBSERVICE_KEY（脚本自动 source ~/.hermes/.env 或 coding .env）
```

语料与期望值见 `references/regression-cases.md`：5 个案例、18 项断言（含「月合计=年值」口径不变量与异常路径），容差 ±3%。退出码 0 = 全部通过。

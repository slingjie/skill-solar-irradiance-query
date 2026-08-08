---
name: solar-irradiance-query
description: "通过地址名称或经纬度查询光伏辐照度(GHI)、比光伏出力(PVOUT)和月度数据。地址需先转为经纬度，搜索失败时必须反馈用户。"
triggers:
  - 用户给出地址名称（小区、楼宇、地名等）
  - 用户给出经纬度坐标
  - 需要查询某地辐照度/GHI/光伏数据
  - 光伏发电量估算、资源评估
---

# Solar Irradiance Query SOP

## 输入格式（两种）

**A. 地址/名称**（优先）：用户提供地名、小区、楼宇、地标等  
**B. 经纬度**：用户直接给坐标（跳过地理编码步骤）

## 核心流程

### Step 1：判断输入类型

| 输入类型 | 处理 |
|----------|------|
| 经纬度（数字+度） | 跳过 Step 2，直接进入 Step 3 |
| 地址/名称（中文/文字） | 进入 Step 2 地理编码 |

### Step 2：地理编码（地址 → 经纬度）

**方案优先级：Web Search > 浏览器高德地图**

#### 方案 A：Web Search（首选，快速）

用 web_search 搜索 `{地址名称} 经纬度` 或 `{地址名称} 坐标`。

示例搜索词：
- `"杭州逸都花苑小区 经纬度"`
- `"上海市浦东新区 coordinates"`

**解析规则：**
- 搜索结果中明确包含 `地理坐标：`、`经纬度：`、`坐标：` 等关键词的 → 提取数字
- 结果为高德/百度地图链接且描述中含坐标 → 提取坐标
- 搜索结果模糊或不含坐标 → 进入方案 B

#### 方案 B：浏览器高德地图（备用）

```bash
browser_navigate("https://www.amap.com/")
browser_type 搜索框 → 输入地址
browser_snapshot → 提取结果
```

#### 方案 C：无法获取经纬度（异常处理）

若方案 A 和 B 均无法获取经纬度，或搜索结果有多个候选位置无法确定唯一匹配：

**必须向用户反馈，示例回复：**

```
⚠️ 无法找到"{地址名称}"的精确经纬度。

请提供以下任一信息：
1. 更详细的地址（如：杭州市临平区北沙西路28号逸都花苑）
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

### Step 5：异常处理

| 场景 | 处理 |
|------|------|
| API 返回正常 JSON | 进入 Step 6 输出 |
| API 返回空数据或报错 | 回复用户：该坐标暂无法获取辐照度数据，请确认地址是否正确 |
| API 超时/HTTP 错误 | 回复用户：辐照度服务暂时不可用，请稍后重试 |
| 地理编码失败 | 按方案 C 反馈用户 |

## 输出格式（严格固定）

**必须按以下 Markdown 模板输出，不可省略字段、不可调整顺序：**

```markdown
📍 **{位置名称}** ({纬度}°, {经度}°)

## 辐照度数据（年累计）
- **GHI（总水平辐射）**: {X} kWh/m²
- DNI（直接法向）: {X} kWh/m²
- DIF（散射水平）: {X} kWh/m²
- GTI opta（最佳倾角）: {X} kWh/m²
- 最佳倾角: {X}°

## 光伏数据
- **PVOUT（比光伏出力）**: {X} kWh/kWp
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

> 查询了杭州逸都花苑的辐照度，GHI 为 1325 kWh/m²...

（原因：地址模糊时自行取了结果，未反馈用户确认）

**正确输出：**

> ⚠️ 搜索"逸都花苑"找到多个候选位置：
> 1. 逸都·花苑 - 杭州市临平区北沙西路28号（坐标 30.44, 120.29）
> 2. 逸都花园 - 银川市某区（坐标 38.5, 106.3）
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
| 地理编码 | `web_search` |
| 地理编码（备用） | `browser_navigate`, `browser_type`, `browser_snapshot` |
| 辐照度查询 | `terminal` (curl) |
| 坐标系转换 | `terminal` (python3) |
| 逐时数据解析 | `gsa_report_parser.py` (见下方) |

## 逐时数据获取（仅当用户明确需要时）

**触发条件**：用户说"逐时"、"小时分布"、"hourly profile"、"每小时"、"发电量"等关键词。

**流程**：

### Step 1：确认 PV 系统配置（必须问用户，用选择项）

使用 `clarize` 工具逐项询问，**禁止让用户自由输入**。

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

### Step 3：构造 GSA URL 并下载报告

GSA 支持 URL 参数预配置 PV 系统，可直接跳转：

```
https://globalsolaratlas.info/map?s=纬度,经度,10&pv=类型,方位角,倾角,容量
```

示例：
```
https://globalsolaratlas.info/map?s=30.4405,120.2868,10&pv=medium,180,24,100
```

| 参数 | 说明 | 可选值 |
|------|------|--------|
| `s=` | 坐标+缩放 | `纬度,经度,10`（10=缩放级别） |
| `pv=` | PV 配置 | `类型,方位角,倾角,容量` |
| 类型 | 系统类型 | `small` / `medium` / `large` / `floating` |
| 方位角 | 朝向 | `180`=正南（默认） |
| 倾角 | 角度 | 度数或 OPTA 值 |
| 容量 | 装机容量 | kWp（如 `100` / `500`） |

**下载步骤**：
1. `browser_navigate` 到构造的 URL
2. 等待页面加载（右侧面板应显示 PV 系统数据）
3. 找到并点击 `Reports` 按钮
4. 选择 `Data – XLSX format`
5. 点击 `Download`
6. 文件保存到 `~/Downloads/GSA_Report_<地点名>.xlsx`

### Step 4：解析 XLSX 报告

```bash
python3 ~/.hermes/scripts/gsa_report_parser.py <file.xlsx> --format json
```

返回结构包含：
- `Overview` — 报告概览
- `Site_info` — 站点信息
- `PV_config` — PV 系统配置（容量、倾角、方位角）
- `Map_data` — 年累计辐照度
- `Monthly_averages` — **月发电量**（PVOUT_specific + PVOUT_total + DNI）
- `Hourly_profiles` — **逐时发电量**（PVOUT_total: Wh）+ 逐时 DNI（Wh/m²）

**异常处理：**
- 脚本返回 `ERROR:` 开头 → 回复用户：XLSX 解析失败，请检查文件是否完整
- 脚本返回 `error` 字段在某个 sheet → 回复用户：部分数据解析异常，可用 `--format table` 查看详情
- 下载后文件不存在 → 回复用户：下载失败，请手动下载后重试
- 文件存在但解析结果全为空 → 回复用户：报告数据为空，可能坐标无数据

### Step 4.5：输出截断策略

**全年逐时发电量默认只展示 7月（夏季峰值）和 12月（冬季低谷）作为代表。**
只有用户明确要求"全年逐时"或"所有月份"时，才展示完整 12 个月。

示例话术：
```
以上是 7月（夏季）和 12月（冬季）的逐时发电量。
如需查看其他月份，请告诉我具体月份（如"3月"、"6月"）。
如需全年 12 个月完整数据，请说"全年逐时"。
```

### Step 5：输出结果（固化格式标准）

解析完成后，**必须按以下顺序输出**，不得省略：

**⛔ 最高优先级规则：所有数字必须来自解析脚本输出，禁止任何形式的编造、推算、四舍五入。直接复制粘贴 parser 输出的表格内容。**

**5.1 文件信息**

```
📁 已保存：~/Downloads/GSA_Report_<地点名>.xlsx
```

**5.2 站点概览**

```
📍 地点：<位置名称>
🗺 坐标：lat°, lng°（海拔 m）
🕐 时区：Asia/Shanghai
📅 报告日期：2026-08-08
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
| 年等效利用小时 | xxx h |
| 最佳倾角 | xxx° |
| 海拔 | xxx m |
| 年均温度 | xx.x °C |

**5.5 月度数据（表格，全年 12 个月）**

| 月 | 发电量 (kWh) | 单位出力 (kWh/kWp) | DNI (kWh/m²) |
|----|-------------|-------------------|--------------|
| 1月 | xxx | xx.x | xx.x |
| 2月 | xxx | xx.x | xx.x |
| ... | ... | ... | ... |
| **年** | **xxx,xxx** | **xxx.x** | **xxx.x** |

**逐时发电量曲线图（12条曲线叠加）：**

从 XLSX 报告的 Hourly_profiles sheet 提取 PVOUT_total 数据，生成 12 个月的逐时发电量曲线（X 轴 0-24h，Y 轴 Wh），12 条曲线叠加在一张图上。

**图表样式：**
- 背景：白色 `#ffffff`
- 网格线：灰色 `#e0e0e0`
- 柱体：蓝灰渐变
- 折线：红色/彩色
- 字体颜色：深灰 `#333` / `#666`
- 边框：1px solid `#e0e0e0`
- 圆角容器

**交互功能：**
1. **柱状图点击**：点击任意月份柱体，高亮显示该月曲线（其余变暗）
2. **悬停提示**：鼠标悬停在柱体或曲线上显示具体数值
3. **图例点击**：点击图例可显示/隐藏对应月份
4. **按钮控制**：显示全部 / 隐藏全部 / 仅夏季 / 仅冬季 / 重置缩放
5. **滚轮缩放**：在曲线图上滚动鼠标滚轮，缩放 X 轴时间范围
6. **悬停高亮**：鼠标悬停在图例上，临时高亮对应曲线

生成步骤：
1. 打开报告的 Hourly_profiles sheet
2. 定位 "Total photovoltaic power output [Wh]" section
3. 逐行读取 0-24 小时数据，按月份分组
4. 使用 HTML Canvas 绘制 12 条曲线（每条对应一个月）
5. 添加交互事件（click、mousemove、wheel）
6. 保存为 HTML 文件到 `~/Downloads/solar_charts_combined.html`
7. 使用 `open_preview` 工具展示图表
8. 在输出中提供文件路径

示例 Python 代码框架：
```python
import openpyxl
import json
wb = openpyxl.load_workbook('<file.xlsx>', data_only=True)
ws = wb['Hourly_profiles']
month_names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
# 状态机读取 PVOUT section（跳过 DNI section）
in_pvout_section = False
found_month_header = False
hour_labels = []
pvout_by_month = {m: {} for m in month_names}
for row in ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=True):
    row_text = " ".join(str(c or "") for c in row)
    if "photovoltaic power output" in row_text.lower():
        in_pvout_section = True; found_month_header = False; continue
    if not in_pvout_section: continue
    if not found_month_header:
        if len(row) >= 13 and row[1] in month_names: found_month_header = True
        continue
    if "direct normal irradiation" in row_text.lower(): break
    if row[0] and str(row[0]).strip().lower() == "sum": continue
    if row[0] and str(row[0]).strip():
        hour_labels.append(str(row[0]).strip())
        for i, m in enumerate(month_names):
            if row[i+1] is not None: pvout_by_month[m][str(row[0]).strip()] = row[i+1]
# 然后生成 HTML canvas 12 条曲线
```

图表规格：
- 尺寸：1050×480 px
- 背景：深色 `#1a1a2e`
- 12 条曲线，每种月份一个颜色
- 线宽：2px，带圆角连接
- Y 轴：发电量（Wh），自动缩放
- X 轴：0-24 小时
- 峰值标记：每个圆点标注
- 图例：12 个月份，网格布局
- 标题：包含地点和 PV 配置

**5.6 逐时发电量**

- 默认展示 7月（夏季峰值）和 12月（冬季低谷），**合并为一张表格**
- 用户指定月份 → 展示该月 24 小时
- 用户明确要求"全年" → 展示 12 个月完整数据
- 展示 PVOUT（Wh）+ **小时占比（%）**
- 占比 = 小时 PVOUT / 当月总 PVOUT × 100%

**默认展示格式（7月+12月合表）：**

| 小时 | 7月 出力 (Wh) | 7月 占比 | 12月 出力 (Wh) | 12月 占比 |
|------|-------------|---------|-------------|----------|
| 0 - 1 | | | | |
| 7-8 | 192,515 | 5.0% | 47,885 | 6.4% |
| ... | ... | ... | ... | ... |

输出后提示：
```
以上是 7月（夏季峰值）和 12月（冬季低谷）逐时发电量及占比。如需其他月份请告知。
```

**5.7 验证提示**

```
✓ 校验：Jan PVOUT 月累计 xxx Wh × 31天 = xx,xxx kWh ≈ 月度数据 xx,xxx kWh ✓
```

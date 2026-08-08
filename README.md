# solar-irradiance-query

光伏辐照度查询 Skill（标准 Agent Skill 格式）— 通过地址名称或经纬度查询 Global Solar Atlas 辐照度数据，下载完整 PV 报告，生成月度发电量柱状图 + 逐时发电量曲线图 + 2×2 matplotlib 综合汇总图（共 9 种科研绘图）。

> 标准 Agent Skill：YAML frontmatter + Markdown，兼容 Hermes、Claude Code、Codex 等主流 Agent。

## 效果预览

[**点击查看交互图表预览 →**](https://cdn.jsdelivr.net/gh/slingjie/solar-irradiance-query@main/solar-irradiance-query/assets/solar_charts_combined.html)

或直接下载 [solar-irradiance-query/assets/solar_charts_combined.html](solar-irradiance-query/assets/solar_charts_combined.html) 在浏览器中打开。

## 安装

### 方式一：直接复制 skill 文件夹（推荐）

```bash
git clone https://github.com/slingjie/solar-irradiance-query.git
cd solar-irradiance-query

# 复制整个 skill 文件夹（脚本、资源随 skill 一起分发）
cp -r solar-irradiance-query ~/.hermes/skills/          # Hermes
cp -r solar-irradiance-query ~/.claude/skills/          # Claude Code
cp -r solar-irradiance-query ~/.codex/skills/           # Codex
```

### 方式二：项目级安装（仅当前项目使用）

```bash
cp -r solar-irradiance-query ./.claude/skills/          # Claude Code
cp -r solar-irradiance-query ./.codex/skills/           # Codex
```

> 脚本引用为相对路径 `scripts/gsa_report_parser.py`，无需额外复制到全局目录。

## 使用触发词

| 模式 | 触发词 | 示例 |
|------|--------|------|
| **基础辐照** | "GHI"、"辐照度"、"PVOUT"、"最佳倾角"、"年发电量" | "查一下上海市浦东新区的辐照度" |
| **逐时曲线** | "逐时"、"小时分布"、"出力曲线"、"曲线图" | "31.23, 121.47 逐时发电量" |
| **组合查询** | "光伏数据分析"、"完整报告"、"全面分析" | "XX产业园 光伏数据分析" |

### 更多触发词示例

**基础辐照查询：**
- "XX市XX区 太阳能资源"
- "坐标 39.9, 116.4 光伏"
- "XX厂房 年发电量"
- "XX园区 等效利用小时"

**逐时发电量：**
- "XX楼宇 出力曲线"
- "XX项目 24小时发电分布"
- "XX市 光伏 月度发电量柱状图"

**组合查询：**
- "XX园区 辐照度 逐时"
- "XX厂房 完整报告"

## 数据来源

- **GSA API**：`https://api.globalsolaratlas.info/data/lta?loc=lat,lng`
- **完整报告**：浏览器自动化下载 XLSX（含 PV 配置）
- **数据版本**：Solargis v2.2.68

## 地理编码（地址 → 经纬度）

输入中文地址/地名时，skill 默认调用**高德 Web 服务 API**（`restapi.amap.com/v3/geocode/geo` 或 `/v3/place/text`）将地址解析为经纬度，再查询 GSA。高德网页版有滑块验证码，REST API 是首选方案；Web Search 与浏览器仅作兜底。

需要设置环境变量 `AMAP_WEBSERVICE_KEY`（高德开放平台 Web 服务 Key，免费申请：https://lbs.amap.com/api/webservice/create-project-and-key）：

```bash
# 建议写入本机环境文件（如 ~/.hermes/.env），不要提交到仓库
export AMAP_WEBSERVICE_KEY=你的key
```

> ⚠️ **安全**：key 只存本地环境变量，仓库内所有文件（含 README/SKILL.md/示例）均不含真实 key；`.gitignore` 已忽略 `.env`、`config.json` 等敏感文件。

## 依赖

- Python 3.x
- openpyxl（读取 XLSX）
- pandas、numpy、matplotlib（matplotlib 综合图）
- 支持浏览器自动化的 Agent 环境（下载 GSA 报告时）
- `AMAP_WEBSERVICE_KEY` 环境变量（中文地址地理编码时）

## 文件结构

```
solar-irradiance-query/               # GitHub 仓库
└── solar-irradiance-query/           # Skill 文件夹（复制到任意 Agent 的 skills 目录）
    ├── SKILL.md                      # 必须：技能说明（YAML frontmatter + Markdown）
    ├── scripts/                      # 可选：脚本文件
    │   ├── gsa_report_parser.py      #   XLSX 报告解析脚本
    │   └── gsa_plot_summary.py       #   matplotlib 综合绘图（2×2 汇总 / 全部 9 种）
    └── assets/                       # 可选：静态资源
        └── solar_charts_combined.html #  交互式图表示例
```

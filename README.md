# solar-irradiance-query

光伏辐照度查询 Skill for Hermes Agent — 通过地址名称或经纬度查询 Global Solar Atlas 辐照度数据，下载完整 PV 报告，生成月度发电量柱状图 + 逐时发电量曲线图。

## 效果预览

[**点击查看交互图表预览 →**](https://cdn.jsdelivr.net/gh/slingjie/solar-irradiance-query@main/solar-irradiance-query/assets/solar_charts_combined.html)

或直接下载 [solar-irradiance-query/assets/solar_charts_combined.html](solar-irradiance-query/assets/solar_charts_combined.html) 在浏览器中打开。

## 安装

```bash
# 1. 克隆仓库
git clone https://github.com/slingjie/solar-irradiance-query.git
cd solar-irradiance-query

# 2. 复制整个 skill 文件夹到 Hermes skills 目录
cp -r solar-irradiance-query ~/.hermes/skills/

# 3. 复制解析脚本到 Hermes 全局脚本目录（skill 运行时调用）
cp solar-irradiance-query/scripts/gsa_report_parser.py ~/.hermes/scripts/
```

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

## 依赖

- Python 3.x
- openpyxl（读取 XLSX）
- Hermes Agent

## 文件结构

```
solar-irradiance-query/               # GitHub 仓库
└── solar-irradiance-query/           # Skill 文件夹（复制到 ~/.hermes/skills/）
    ├── SKILL.md                      # 必须：技能说明（YAML frontmatter + Markdown）
    ├── scripts/                      # 可选：脚本文件
    │   └── gsa_report_parser.py      #   XLSX 报告解析脚本
    └── assets/                       # 可选：静态资源
        └── solar_charts_combined.html #  交互式图表示例
```

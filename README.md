# solar-irradiance-query

光伏辐辐度查询 Skill for Hermes Agent — 通过地址名称或经纬度查询 Global Solar Atlas 辐照度数据，下载完整 PV 报告，生成月度发电量柱状图 + 逐时发电量曲线图。

## 功能

- 🌞 **基础辐照查询**：地址/经纬度 → GHI / DNI / DIF / GTI / PVOUT
- 📊 **逐时发电量**：下载 GSA 完整 PV 报告，解析 12 个月 × 24 小时数据
- 📈 **可视化图表**：
  - 月度发电量柱状图 + 趋势线
  - 逐时发电量曲线图（12 个月叠加）
- 🖱 **交互功能**：
  - 点击柱体高亮对应月份
  - 图例点击显示/隐藏
  - 滚轮缩放 X 轴
  - 悬停显示具体数值

## 安装

```bash
# 复制 skill 到 Hermes
cp -r solar-irradiance-query ~/.hermes/skills/

# 复制解析脚本
cp gsa_report_parser.py ~/.hermes/scripts/
```

## 使用触发词

- "杭州西溪乐谷 辐照度"
- "上海市浦东新区 光伏数据"
- "31.23, 121.47 发电量"
- "逸都花苑 逐时曲线"

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
solar-irradiance-query/
├── SKILL.md              # Skill 定义（触发条件、流程、输出标准）
├── gsa_report_parser.py  # XLSX 报告解析脚本
└── README.md
```

# 农业：农产品价格监控预警

[该 MCP 服务围绕农产品价格监控预警，提供农产品价格行情、农业价格指数和日周月市场报告查询能力，为价格波动识别和市场趋势研判提供数据依据。](https://www.handaas.com/)

> 所属板块：市场贸易

## 主要功能

- 农产品价格行情监控
- 产地与市场价格比较
- 农业价格指数跟踪
- 农业市场分析与预警研判

## 服务设计说明

- 服务提供价格监控和预警研判所需的查询数据，不在后台持续运行，也不主动发送告警通知。
- 服务提供 3 个只读 Tool，单次 Tool 调用只访问一个 Product ID。
- 翻页结果统一收口为 `total` 与 `resultList`。
- 成功响应自动兼容 Gateway业务 data和内部 `stat/data` 两种形态。
- 请求超时可通过 `HANDAAS_REQUEST_TIMEOUT` 配置，默认30秒。

## 环境要求

- Python 3.10+
- 依赖：`mcp`、`python-dotenv`、`requests`

## 本地快速启动

```bash
cd agriculture-mcp-server
python3 -m venv mcp_env
source mcp_env/bin/activate
pip install -r requirements.txt
cp .env.example .env
python server/mcp_server.py streamable-http
```

服务默认地址：`http://127.0.0.1:8000/mcp`。支持 `stdio`、`sse` 和 `streamable-http`。

## 环境变量

```env
INTEGRATOR_ID=your_integrator_id
SECRET_ID=your_secret_id
SECRET_KEY=your_secret_key
HANDAAS_REQUEST_TIMEOUT=30
```

真实凭据只能保存在本地 `.env` 或部署密钥中。

## Cursor / Cherry Studio配置

```json
{
  "mcpServers": {
    "agriculture-mcp-server": {
      "type": "streamableHttp",
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

## 可用 Tool 与 Product ID

| MCP Tool | 使用场景 | Product ID | 关键输入 |
| --- | --- | --- | --- |
| `agriculture_product_search` | 查询农产品最新行情与高低价 | `6a7c58fd71276c00fb93e980` | `productName`、分页 |
| `agriculture_price_index` | 查询指定日期农业价格指数 | `6a7c626971276c00fb93eab7` | `publishTime` |
| `agriculture_market_report` | 查询日周月农业市场分析报告 | `6a7c637bc90c69ced247c56c` | `reportType`、`size` |

## 推荐分析流程

1. 使用 `agriculture_product_search` 查询目标农产品的当前均价、高低价、涨跌和产地市场差异。
2. 使用 `agriculture_price_index` 查询同一日期的整体价格指数。
3. 使用 `agriculture_market_report` 获取日度、周度或月度报告，解释波动原因并形成预警研判。

本服务提供监控预警所需数据，不在后台持续运行，也不主动发送告警。

## Tool 详细说明

### 1. agriculture_product_search

**何时使用**：查询某种农产品的最新价格、涨跌幅、高低价市场和产地差异，或分页浏览全部农产品。

**关键参数**：`productName` 支持模糊搜索；`pageIndex` 从 1 开始；`pageSize` 最大 50。

**返回说明**：返回分类、产品名、行情日期、均价、高低价、市场和产地信息。所有价格必须结合返回的 `unit` 解读。

### 2. agriculture_price_index

**何时使用**：查询某一天的农产品批发、菜篮子、粮油等整体价格指数。

**关键参数**：`publishTime` 必填，格式为 `YYYY-MM-DD`。

**返回说明**：返回指数名称、当前值、前日值和环比；缺失日期不插值，直接返回空结果。

### 3. agriculture_market_report

**何时使用**：需要用市场报告解释近期价格变化、供需情况或形成风险预警依据时使用。

**关键参数**：`reportType` 仅支持 `day`、`week`、`month`；`size` 范围为 1 至 9。

**返回说明**：返回报告日期、标题、正文、类型和来源；`resultList` 最多包含 `size` 条记录。

## 使用示例

### 示例一：查询农产品行情

> 查询白菜最近的均价、最高价、最低价和涨跌情况。

```json
{
  "tool": "agriculture_product_search",
  "arguments": {
    "productName": "白菜",
    "pageIndex": 1,
    "pageSize": 10
  }
}
```

### 示例二：查询价格指数

> 查询 2026 年 8 月 11 日的农业价格指数及环比变化。

```json
{
  "tool": "agriculture_price_index",
  "arguments": {
    "publishTime": "2026-08-11"
  }
}
```

### 示例三：形成周度预警研判

> 获取最近 3 份农业周报，结合白菜价格判断是否存在明显波动。

```json
{
  "tool": "agriculture_market_report",
  "arguments": {
    "reportType": "week",
    "size": 3
  }
}
```

## 使用注意事项

1. 价格单位使用接口返回的 `unit`，不自行换算。
2. 指数缺失日期不做插值。
3. 报告数量 `size` 范围为 1 至 9。
4. 预警结论应综合行情、指数和报告，不应只依据单一价格点。

## 测试验证

```bash
python -m py_compile server/mcp_server.py
python -m unittest discover -s tests -v
```

单元测试使用 Mock 响应；真实验证通过本地 `.env` 调用 HandaaS Integrator Gateway。

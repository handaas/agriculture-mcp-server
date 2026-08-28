# 农业：农产品价格监控预警

[该MCP服务提供农产品价格行情、批发市场、每日价格、农业价格指数和日周月市场分析报告查询功能，为价格监控、流通分析和预警研判提供数据。](https://www.handaas.com/)


## 主要功能

- 🥬 农产品价格行情搜索
- 🏪 农产品批发市场及市场规模查询
- 📅 农产品每日产地与市场价格查询
- 📈 农产品高低价和涨跌监控
- 📊 农业价格指数查询
- 📰 日度、周度和月度市场报告

## 环境要求

- Python 3.10+
- 依赖包：python-dotenv, requests, mcp

## 本地快速启动

### 1. 克隆项目
```bash
git clone https://github.com/handaas/agriculture-mcp-server
cd agriculture-mcp-server
```

### 2. 创建虚拟环境&安装依赖

```bash
python -m venv mcp_env && source mcp_env/bin/activate
pip install -r requirements.txt
```

### 3. 环境配置

复制环境变量模板并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下环境变量：

```env
INTEGRATOR_ID=your_integrator_id
SECRET_ID=your_secret_id
SECRET_KEY=your_secret_key
HANDAAS_REQUEST_TIMEOUT=30
```

### 4. streamable-http启动服务

```bash
python server/mcp_server.py streamable-http
```

服务将在 `http://localhost:8000` 启动，MCP 地址为 `http://127.0.0.1:8000/mcp`。

#### 支持启动方式 stdio 或 sse 或 streamable-http

### 5. Cursor / Cherry Studio MCP配置

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

## STDIO版安装部署

### 设置Cursor / Cherry Studio MCP配置

```json
{
  "mcpServers": {
    "agriculture-mcp-server": {
      "command": "uv",
      "args": ["run", "mcp", "run", "{workdir}/server/mcp_server.py"],
      "env": {
        "PATH": "{workdir}/mcp_env/bin:$PATH",
        "PYTHONPATH": "{workdir}/mcp_env",
        "INTEGRATOR_ID": "your_integrator_id",
        "SECRET_ID": "your_secret_id",
        "SECRET_KEY": "your_secret_key"
      }
    }
  }
}
```

## 使用官方Remote服务

当前服务暂未开放官方 Remote 地址。请使用本地 `stdio`、`sse` 或 `streamable-http` 方式运行；官方 Remote 地址开放后将在本节补充配置。

### 注意：integrator_id、secret_id、secret_key及Remote token需要登录 https://www.handaas.com/ 进行注册开通平台获取


## 推荐调用流程

1. 使用 `agriculture_product_search` 按名称搜索农产品，获取稳定的 `productId` 和最新行情摘要。
2. 使用 `agriculture_wholesale_market_list` 查询该农产品覆盖的批发市场、历史价格和市场规模。
3. 使用 `agriculture_daily_price_list` 按产地和日期范围查询每日价格，分析时间趋势与区域价差。
4. 使用 `agriculture_price_index` 获取指定日期的农业价格指数，判断整体市场变化。
5. 使用 `agriculture_market_report` 获取日度、周度或月度报告，为价格波动和预警结论补充市场解释。

用户未指定具体农产品时，批发市场和每日价格 Tool 也支持不传 `productId` 分页浏览；需要围绕单一农产品分析时，应优先完成第1步。


## 可用工具

### 1. agriculture_product_search
**功能**: 农产品价格行情搜索

**Product ID**: `6a7c58fd71276c00fb93e980`

按农产品名称发现标准农产品记录，返回最新行情、产地和市场摘要，并为后续批发市场和每日价格查询提供 `productId`。

**参数**:
- `productName` (可选): 农产品名称，支持模糊搜索
- `pageIndex` (可选): 页码，从1开始
- `pageSize` (可选): 每页条数，默认10，最大10

**返回值**:
- `total`: 农产品总数
- `resultList`: 农产品行情列表
  - `classification`: 产品分类
  - `productId`: 农产品ID，供批发市场和每日价格明细查询使用
  - `productName`: 产品名称
  - `date`: 行情日期
  - `doD`: 涨跌幅
  - `bulkAveragePrice`: 大宗均价
  - `highPrice`: 最高价
  - `lowPrice`: 最低价
  - `unit`: 价格单位
  - `marketNameCount`: 有行情数据的市场数量
  - `originCount`: 有行情数据的产地数量
  - `originBulkAveragePriceList`: 产地均价列表
  - `highPriceMarket` / `lowPriceMarket`: 高低价市场
  - `highPriceOrigin` / `lowPriceOrigin`: 高低价产地
  - `priceChange`: 价格变动
  - `newHighPriceMarket` / `newLowPriceMarket`: 最新高低价市场

### 2. agriculture_wholesale_market_list
**功能**: 农产品批发市场明细查询

**Product ID**: `6a8447989fbf4ea45da8d758`

通过农产品ID查询其覆盖的批发市场、历史价格和市场规模，也可不传农产品ID分页浏览全部记录。

**参数**:
- `productId` (可选): 农产品ID，建议使用 `agriculture_product_search` 返回的 `productId`
- `pageIndex` (可选): 页码，从1开始，默认1
- `pageSize` (可选): 每页条数，默认10，最大10

**返回值**:
- `total`: 批发市场记录总数
- `resultList`: 批发市场明细列表
  - `marketName`: 市场名称
  - `marketType`: 市场类型
  - `province`: 所属地区
  - `maxPrice`: 历史最高价，单位元/公斤
  - `minPrice`: 历史最低价，单位元/公斤
  - `avgPrice`: 历史均价，单位元/公斤；MCP根据上游 `avg` 字段补充该稳定别名
  - `avg`: 上游原始历史均价值，保留用于兼容已有调用方
  - `newMarketName`: 标准化市场名称，上游存在时返回
  - `siteArea`: 占地面积，单位平方米
  - `buildingArea`: 建筑面积，单位平方米

### 3. agriculture_daily_price_list
**功能**: 农产品每日价格明细查询

**Product ID**: `6a844b2a9fbf4ea45da8d7b2`

按农产品、产地和日期范围查询各批发市场每日价格，支持价格趋势、产地价差和市场行情分析。

**参数**:
- `productId` (可选): 农产品ID，建议使用 `agriculture_product_search` 返回的 `productId`
- `origin` (可选): 产地，使用省份全称，例如广东省
- `startDate` (可选): 起始日期，格式YYYY-MM-DD
- `endDate` (可选): 截止日期，格式YYYY-MM-DD
- `pageIndex` (可选): 页码，从1开始，默认1
- `pageSize` (可选): 每页条数，默认10，最大10

**返回值**:
- `total`: 每日价格记录总数
- `resultList`: 每日价格明细列表
  - `marketName`: 市场名称
  - `origin`: 产地
  - `highestPrice`: 最高价，单位元/公斤
  - `lowestPrice`: 最低价，单位元/公斤
  - `bulkPrice`: 大宗均价，单位元/公斤
  - `date`: 日期

### 4. agriculture_price_index
**功能**: 农业价格指数查询

**Product ID**: `6a7c626971276c00fb93eab7`

按发布日期查询农产品批发、菜篮子、粮油等价格指数，返回当前值、前日值和环比变化。

**参数**:
- `publishTime` (必需): 发布日期，格式YYYY-MM-DD

**返回值**:
- `total`: 指数记录数量
- `resultList`: 价格指数列表
  - `publishTime`: 发布日期
  - `currentIndexValue`: 当前指数值
  - `previousIndexValue`: 前日指数值
  - `indexName`: 指数名称
  - `indexType`: 指数类型
  - `chainRatio`: 环比变化

### 5. agriculture_market_report
**功能**: 农业市场分析报告查询

**Product ID**: `6a7c637bc90c69ced247c56c`

查询最近的农业市场日度、周度或月度报告，用于解释价格波动、供需变化和阶段性市场趋势。

**参数**:
- `reportType` (必需): 报告类型，可选day、week、month
- `size` (可选): 返回报告数量，默认3，范围1至9

**返回值**:
- `total`: 上游报告总数
- `resultList`: 最近报告列表，最多返回 `size` 条
  - `publishTime`: 发布日期
  - `reportTitle`: 报告标题
  - `reportContent`: 报告内容
  - `reportType`: 报告类型
  - `reportSource`: 报告来源

## 使用注意事项

1. **农产品ID**: 批发市场和每日价格查询建议先调用 `agriculture_product_search` 获取 `productId`。
2. **分页限制**: 所有分页查询一页最多10条。
3. **价格单位**: 批发市场和每日价格明细统一为元/公斤；价格行情需结合返回的 `unit` 解读。
4. **产地格式**: 每日价格明细的 `origin` 使用省份全称，例如广东省。
5. **日期范围**: `startDate` 不能晚于 `endDate`，格式均为YYYY-MM-DD。
6. **指数日期**: 指数缺失日期不做插值，直接返回合法空结果。
7. **报告类型**: `reportType` 只支持day、week、month，`size` 范围为1至9。
8. **预警边界**: 服务提供监控和研判数据，不在后台持续运行，也不主动发送告警。
9. **405诊断**: 如果返回HTML类型的HTTP 405，通常是本机DNS Fake-IP、PAC或透明代理拒绝POST，并非对接器未配置商品。
10. **统一响应**: 成功响应顶层统一为 `total/resultList`；详情未命中时返回 `total=0` 和空列表。
11. **错误响应**: 参数校验失败会返回 `error` 和 `parameter`；网关失败会返回 `error`、`statusCode`，HTML 405还会返回 `diagnostic`。

## 使用提问示例

### agriculture_product_search (农产品价格行情搜索)
1. 查询白菜最近的均价和涨跌情况
2. 查看苹果的最高价和最低价市场
3. 搜索名称中包含“猪肉”的农产品行情

### agriculture_wholesale_market_list (农产品批发市场明细查询)
1. 查询白菜覆盖了哪些批发市场
2. 查看该农产品各批发市场的历史最高价、最低价和均价
3. 分析该农产品批发市场的地区分布和市场规模

### agriculture_daily_price_list (农产品每日价格明细查询)
1. 查询白菜最近30天在各批发市场的每日价格
2. 查看广东省苹果在指定日期范围内的最高价和最低价
3. 对比同一农产品不同产地的大宗均价变化

### agriculture_price_index (农业价格指数查询)
1. 查询2026年8月11日的农业价格指数
2. 查看指定日期菜篮子指数的环比变化
3. 对比当天指数当前值和前日值

### agriculture_market_report (农业市场分析报告查询)
1. 获取最近3份农业周报
2. 查询最近2份农业日报
3. 获取最近6个月的农业月度市场报告

## 测试验证

```bash
python -m py_compile server/mcp_server.py
python -m unittest discover -s tests -v
```

当前服务包含 12 个离线单元测试。

真实接口 smoke 测试：

```bash
python tests/live_api_smoke.py
```

如果本机代理将 `console.handaas.com` 解析为 `198.18.x.x` Fake-IP，可临时指定由网络管理员或公共DNS确认的真实网关IP：

```bash
HANDAAS_GATEWAY_RESOLVE_IP=<real_gateway_ip> python tests/live_api_smoke.py
```

smoke 测试只输出记录数量和字段名，不输出真实业务内容、请求签名或凭据。

可通过环境变量调整 smoke 测试样本：

```bash
HANDAAS_TEST_PRODUCT_NAME=苹果 \
HANDAAS_TEST_INDEX_DATE=2026-08-12 \
python tests/live_api_smoke.py
```

### 2026-08-25 真实验证结果

| Tool | 验证条件 | 上游总数 | 结果 |
| --- | --- | ---: | --- |
| `agriculture_product_search` | 关键词“白菜” | 3 | 通过 |
| `agriculture_wholesale_market_list` | 使用搜索返回的 `productId` | 76 | 通过 |
| `agriculture_daily_price_list` | 使用搜索返回的 `productId` | 17657 | 通过 |
| `agriculture_price_index` | `publishTime=2026-08-11` | 9 | 通过 |
| `agriculture_market_report` | `reportType=week, size=2` | 240 | 通过 |

本地 Streamable HTTP 服务启动、MCP初始化、5个Tool注册和5次真实MCP调用均已通过。工作区全部7个新服务的扩展验证矩阵为45/45通过。

### HTTP 405排障

当 `console.handaas.com` 被本机代理解析为 `198.18.x.x` Fake-IP 时，POST可能在代理边缘被拒绝并返回HTML 405。此时应优先将该域名加入代理直连或 Fake-IP 排除规则。`HANDAAS_GATEWAY_RESOLVE_IP` 仅用于本地测试时临时验证真实网关，不建议将固定IP写入生产配置。

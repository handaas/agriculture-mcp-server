# 农业：农产品价格监控预警

[该MCP服务提供农产品价格行情、农业价格指数和日周月市场分析报告查询功能，为价格监控和预警研判提供数据。](https://www.handaas.com/)


## 主要功能

- 🥬 农产品价格行情搜索
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


## 可用工具

### 1. agriculture_product_search
**功能**: 农产品价格行情搜索

**参数**:
- `productName` (可选): 农产品名称，支持模糊搜索
- `pageIndex` (可选): 页码，从1开始
- `pageSize` (可选): 每页条数，默认10，最大50

**返回值**:
- `total`: 农产品总数
- `resultList`: 农产品行情列表
  - `Classification`: 产品分类
  - `productName`: 产品名称
  - `date`: 行情日期
  - `doD`: 涨跌幅
  - `bulkAveragePrice`: 大宗均价
  - `highPrice`: 最高价
  - `lowPrice`: 最低价
  - `unit`: 价格单位
  - `originBulkAveragePriceList`: 产地均价列表
  - `highPriceMarket` / `lowPriceMarket`: 高低价市场
  - `highPriceOrigin` / `lowPriceOrigin`: 高低价产地
  - `priceChange`: 价格变动

### 2. agriculture_price_index
**功能**: 农业价格指数查询

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

### 3. agriculture_market_report
**功能**: 农业市场分析报告查询

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

1. **价格单位**: 所有价格必须结合返回的 `unit` 解读，不自行换算。
2. **指数日期**: 指数缺失日期不做插值，直接返回合法空结果。
3. **报告类型**: `reportType` 只支持day、week、month。
4. **报告数量**: `size` 范围为1至9。
5. **预警边界**: 服务提供监控和研判数据，不在后台持续运行，也不主动发送告警。

## 使用提问示例

### agriculture_product_search (农产品价格行情搜索)
1. 查询白菜最近的均价和涨跌情况
2. 查看苹果的最高价和最低价市场
3. 搜索名称中包含“猪肉”的农产品行情

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

当前服务包含 7 个离线单元测试。真实接口验证需在本地 `.env` 配置有效凭据后执行，测试输出不得提交真实业务响应或凭据。

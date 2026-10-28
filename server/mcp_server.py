
"""HandaaS 农产品价格监控预警 MCP 服务。"""

import json
import os
import sys
from hashlib import md5
from typing import Any, Literal
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations


load_dotenv()

mcp = FastMCP(
    "农产品价格监控预警",
    instructions=(
        "先搜索农产品取得 productId，再查询批发市场分布和每日价格明细；"
        "结合价格指数与日周月市场报告，支持价格监控、流通分析和预警研判。"
    ),
    dependencies=["python-dotenv", "requests"],
)

GATEWAY_BASE_URL = "https://console.handaas.com/api/v1/integrator/call_api"
DEFAULT_TIMEOUT_SECONDS = 30.0

PRODUCT_IDS = {
    "product_search": "6a7c58fd71276c00fb93e980",
    "wholesale_markets": "6a8447989fbf4ea45da8d758",
    "daily_prices": "6a844b2a9fbf4ea45da8d7b2",
    "price_index": "6a7c626971276c00fb93eab7",
    "market_report": "6a7c637bc90c69ced247c56c",
}

READ_ONLY_TOOL = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


def _request_timeout() -> float:
    raw = os.environ.get("HANDAAS_REQUEST_TIMEOUT", "")
    try:
        value = float(raw) if raw else DEFAULT_TIMEOUT_SECONDS
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_TIMEOUT_SECONDS


def _credential(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    if not value or value.startswith("your_"):
        return None
    return value


def _compact_params(params: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in params.items() if value is not None}


def _build_signature(call_params: dict[str, str], secret_key: str) -> str:
    plain = "".join(str(call_params[key]) for key in sorted(call_params))
    return md5(f"{plain}{secret_key}".encode("utf-8")).hexdigest()


def call_api(product_id: str, params: dict[str, Any]) -> Any:
    """调用 HandaaS Integrator Gateway并返回业务 data。"""
    integrator_id = _credential("INTEGRATOR_ID")
    secret_id = _credential("SECRET_ID")
    secret_key = _credential("SECRET_KEY")
    if not integrator_id:
        return {"error": "INTEGRATOR_ID 未配置"}
    if not secret_id:
        return {"error": "SECRET_ID 未配置"}
    if not secret_key:
        return {"error": "SECRET_KEY 未配置"}
    if not product_id:
        return {"error": "Product ID 不能为空"}

    call_params = {
        "product_id": product_id,
        "secret_id": secret_id,
        "params": json.dumps(
            _compact_params(params), ensure_ascii=False, separators=(",", ":")
        ),
    }
    call_params["signature"] = _build_signature(call_params, secret_key)
    url = f"{GATEWAY_BASE_URL}/{quote(integrator_id, safe='')}"
    try:
        response = requests.post(url, data=call_params, timeout=_request_timeout())
    except requests.RequestException:
        return {"error": "HandaaS 网关请求失败，请稍后重试"}
    if response.status_code != 200:
        result = {
            "error": "HandaaS 网关返回非成功状态",
            "statusCode": response.status_code,
        }
        content_type = response.headers.get("content-type", "")
        if response.status_code == 405 and "text/html" in content_type.lower():
            result["diagnostic"] = (
                "请求被网关边缘或本地代理拒绝，请检查 console.handaas.com 的 DNS、"
                "PAC/透明代理规则和 POST 放行情况"
            )
        return result
    try:
        payload = response.json()
    except (ValueError, requests.exceptions.JSONDecodeError):
        return {"error": "HandaaS 网关返回了无法解析的响应"}
    if not isinstance(payload, dict):
        return {"error": "HandaaS 网关返回格式异常"}
    if "data" in payload:
        return payload["data"]
    error = payload.get("msgCN") or payload.get("message") or "HandaaS 网关未返回 data"
    if str(payload.get("code")) == "10001" or error == "查询数据为空":
        return {"total": 0, "resultList": []}
    result = {"error": error}
    if payload.get("code") is not None:
        result["code"] = payload["code"]
    return result


def _unwrap_backend_data(result: Any) -> Any:
    """兼容 Product API直接返回业务 data或保留内部 stat/data 外层。"""
    if not isinstance(result, dict) or "error" in result:
        return result
    if "stat" not in result:
        return result
    if result.get("stat") != 1:
        return {
            "error": result.get("msg") or "上游数据接口返回失败",
            "code": result.get("err"),
        }
    return result.get("data")


def _pagination_error(page_index: int, page_size: int, maximum: int = 10) -> dict[str, Any] | None:
    if page_index < 1:
        return {"error": "pageIndex 必须大于等于 1", "parameter": "pageIndex"}
    if page_size < 1 or page_size > maximum:
        return {"error": f"pageSize 必须在 1 到 {maximum} 之间", "parameter": "pageSize"}
    return None


def _normalize_paged(result: Any) -> Any:
    result = _unwrap_backend_data(result)
    if not isinstance(result, dict) or "error" in result:
        return result
    if isinstance(result.get("resultList"), list):
        records = result["resultList"]
        total = result.get("total", len(records))
        return {"total": total, "resultList": records}
    if isinstance(result.get("dataList"), list):
        records = result["dataList"]
        total = result.get("dataTotal", result.get("dataCount", len(records)))
        return {"total": total, "resultList": records}
    if isinstance(result.get("indexList"), list):
        records = result["indexList"]
        return {"total": result.get("count", len(records)), "resultList": records}
    return result


def _normalize_single(result: Any) -> Any:
    result = _unwrap_backend_data(result)
    if not isinstance(result, dict) or "error" in result:
        return result
    if set(result) == {"total", "resultList"} and isinstance(result.get("resultList"), list):
        return result
    if not result:
        return {"total": 0, "resultList": []}
    return {"total": 1, "resultList": [result]}


def _with_product_id_alias(result: Any) -> Any:
    """为农产品搜索结果补充后续明细 Tool 使用的 productId。"""
    if not isinstance(result, dict) or not isinstance(result.get("resultList"), list):
        return result
    records = []
    for item in result["resultList"]:
        if isinstance(item, dict) and not item.get("productId") and item.get("_id"):
            records.append({**item, "productId": item["_id"]})
        else:
            records.append(item)
    return {**result, "resultList": records}


def _with_wholesale_market_aliases(result: Any) -> Any:
    """按公开合同补充批发市场历史均价字段。"""
    if not isinstance(result, dict) or not isinstance(result.get("resultList"), list):
        return result
    records = []
    for item in result["resultList"]:
        if isinstance(item, dict) and item.get("avgPrice") is None and item.get("avg") is not None:
            records.append({**item, "avgPrice": item["avg"]})
        else:
            records.append(item)
    return {**result, "resultList": records}


def _number_range_error(
    minimum: int | float | None,
    maximum: int | float | None,
    minimum_name: str,
    maximum_name: str,
) -> dict[str, Any] | None:
    if minimum is not None and maximum is not None and minimum > maximum:
        return {
            "error": f"{minimum_name} 不能大于 {maximum_name}",
            "parameter": minimum_name,
        }
    return None


def _date_range_error(
    start: str | None,
    end: str | None,
    start_name: str,
    end_name: str,
) -> dict[str, Any] | None:
    if start and end and start > end:
        return {
            "error": f"{start_name} 不能晚于 {end_name}",
            "parameter": start_name,
        }
    return None

ReportType = Literal["day", "week", "month"]


@mcp.tool(
    title="农产品价格行情监控",
    description=(
        "按农产品名称模糊搜索最新行情，用于比较均价、高低价、涨跌幅、产地和市场差异。"
        "不传 productName 时分页浏览全部品类；pageIndex 从 1 开始，pageSize 最大 10，"
        "价格必须结合结果中的 unit 解读。"
    ),
    annotations=READ_ONLY_TOOL,
)
def agriculture_product_search(productName: str | None = None, pageIndex: int = 1, pageSize: int = 10) -> dict[str, Any]:
    """分页返回农产品、分类、产地、市场和最新高低价。"""
    if error := _pagination_error(pageIndex, pageSize, maximum=10):
        return error
    return _with_product_id_alias(
        _normalize_paged(
            call_api(
                PRODUCT_IDS["product_search"],
                {
                    "productName": productName,
                    "pageIndex": pageIndex,
                    "pageSize": pageSize,
                },
            )
        )
    )


@mcp.tool(
    title="农产品批发市场明细",
    description=(
        "查询指定农产品覆盖的批发市场、市场类型、所属地区、历史最高价、最低价、均价和市场规模。"
        "productId 建议使用 agriculture_product_search 返回的 productId；不传时分页浏览全部记录。"
        "pageIndex 从 1 开始，pageSize 最大 10；价格单位为元/公斤，面积单位为平方米。"
    ),
    annotations=READ_ONLY_TOOL,
)
def agriculture_wholesale_market_list(
    productId: str | None = None,
    pageIndex: int = 1,
    pageSize: int = 10,
) -> dict[str, Any]:
    """分页查询农产品批发市场及其历史价格和市场规模。"""
    if error := _pagination_error(pageIndex, pageSize):
        return error
    return _with_wholesale_market_aliases(
        _normalize_paged(
            call_api(
                PRODUCT_IDS["wholesale_markets"],
                {
                    "productId": productId,
                    "pageIndex": pageIndex,
                    "pageSize": pageSize,
                },
            )
        )
    )


@mcp.tool(
    title="农产品每日价格明细",
    description=(
        "按农产品、产地和日期区间查询各批发市场每日最高价、最低价和大宗均价，"
        "适用于价格趋势、产地价差和市场行情分析。productId 建议来自 agriculture_product_search，"
        "origin 使用省份全称，日期格式为 YYYY-MM-DD；pageSize 最大 10，价格单位为元/公斤。"
    ),
    annotations=READ_ONLY_TOOL,
)
def agriculture_daily_price_list(
    productId: str | None = None,
    origin: str | None = None,
    startDate: str | None = None,
    endDate: str | None = None,
    pageIndex: int = 1,
    pageSize: int = 10,
) -> dict[str, Any]:
    """分页查询农产品在各产地和批发市场的每日价格。"""
    if error := _pagination_error(pageIndex, pageSize):
        return error
    if error := _date_range_error(startDate, endDate, "startDate", "endDate"):
        return error
    return _normalize_paged(
        call_api(
            PRODUCT_IDS["daily_prices"],
            {
                "productId": productId,
                "origin": origin,
                "startDate": startDate,
                "endDate": endDate,
                "pageIndex": pageIndex,
                "pageSize": pageSize,
            },
        )
    )


@mcp.tool(
    title="农业价格指数查询",
    description=(
        "按 publishTime 查询指定日期的农产品批发、菜篮子、粮油等价格指数，"
        "返回当前值、前日值和环比。日期格式必须为 YYYY-MM-DD；无数据日期返回合法空结果。"
    ),
    annotations=READ_ONLY_TOOL,
)
def agriculture_price_index(publishTime: str) -> dict[str, Any]:
    """按发布日期查询农产品批发、菜篮子和粮油等价格指数。"""
    return _normalize_paged(call_api(PRODUCT_IDS["price_index"], {"publishTime": publishTime}))


@mcp.tool(
    title="农业价格监控分析报告",
    description=(
        "查询最近的农业市场日度、周度或月度分析报告，用于解释价格波动并形成预警研判。"
        "reportType 仅支持 day、week、month，size 为 1 至 9；返回 total 与最多 size 条 resultList。"
    ),
    annotations=READ_ONLY_TOOL,
)
def agriculture_market_report(reportType: ReportType, size: int = 3) -> dict[str, Any]:
    """查询最近的日度、周度或月度农业市场分析报告。"""
    if size < 1 or size > 9: return {"error": "size 必须在 1 到 9 之间", "parameter": "size"}
    result = _normalize_paged(
        call_api(
            PRODUCT_IDS["market_report"],
            {"reportType": reportType, "size": size},
        )
    )
    if isinstance(result, dict) and isinstance(result.get("resultList"), list):
        return {**result, "resultList": result["resultList"][:size]}
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    transport = arguments[0] if arguments else "stdio"
    if transport not in {"stdio", "sse", "streamable-http"}:
        print("启动方式必须是 stdio、sse 或 streamable-http", file=sys.stderr)
        return 2
    mcp.run(transport=transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

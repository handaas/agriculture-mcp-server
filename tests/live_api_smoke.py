#!/usr/bin/env python3
"""真实验证农业 MCP 的 5 个只读 Tool，仅输出脱敏结构摘要。"""

from __future__ import annotations

import importlib.util
import json
import os
import socket
from pathlib import Path
from typing import Any


SERVER_PATH = Path(__file__).parents[1] / "server" / "mcp_server.py"
SPEC = importlib.util.spec_from_file_location("agriculture_live_smoke", SERVER_PATH)
assert SPEC and SPEC.loader
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


def _install_optional_dns_override() -> None:
    """绕过本机代理 Fake-IP，仍使用原域名完成 TLS/SNI 校验。"""
    resolve_ip = os.environ.get("HANDAAS_GATEWAY_RESOLVE_IP", "").strip()
    if not resolve_ip:
        return
    original = socket.getaddrinfo

    def resolved(host: str, port: int, *args: Any, **kwargs: Any) -> list[Any]:
        rows = original(host, port, *args, **kwargs)
        if host != "console.handaas.com":
            return rows
        replaced = []
        for family, socktype, proto, canonname, sockaddr in rows:
            if family == socket.AF_INET:
                replaced.append(
                    (family, socktype, proto, canonname, (resolve_ip, sockaddr[1]))
                )
        return replaced or rows

    socket.getaddrinfo = resolved


def _validated_summary(
    tool_name: str,
    result: dict[str, Any],
    required_fields: set[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if "error" in result:
        raise RuntimeError(
            f"{tool_name}: {result.get('error')} "
            f"status={result.get('statusCode')} diagnostic={result.get('diagnostic')}"
        )
    records = result.get("resultList")
    if not isinstance(result.get("total"), int) or not isinstance(records, list):
        raise RuntimeError(f"{tool_name}: 响应不是 total/resultList")
    if not records or not isinstance(records[0], dict):
        raise RuntimeError(f"{tool_name}: 未返回可验证样本")
    missing = required_fields - set(records[0])
    if missing:
        raise RuntimeError(f"{tool_name}: 缺少字段 {sorted(missing)}")
    return (
        {
            "tool": tool_name,
            "total": result["total"],
            "resultCount": len(records),
            "fields": sorted(records[0]),
        },
        records,
    )


def main() -> int:
    _install_optional_dns_override()
    for name in ("INTEGRATOR_ID", "SECRET_ID", "SECRET_KEY"):
        if not server._credential(name):
            raise RuntimeError(f"{name} 未配置")

    summaries = []
    summary, products = _validated_summary(
        "agriculture_product_search",
        server.agriculture_product_search(
            os.environ.get("HANDAAS_TEST_PRODUCT_NAME", "白菜"), pageSize=3
        ),
        {"productId", "productName", "unit"},
    )
    summaries.append(summary)
    product_id = str(products[0]["productId"])

    summary, _ = _validated_summary(
        "agriculture_wholesale_market_list",
        server.agriculture_wholesale_market_list(product_id, pageSize=3),
        {"marketName", "province", "maxPrice", "minPrice", "avgPrice"},
    )
    summaries.append(summary)

    summary, _ = _validated_summary(
        "agriculture_daily_price_list",
        server.agriculture_daily_price_list(product_id, pageSize=3),
        {"marketName", "origin", "highestPrice", "lowestPrice", "bulkPrice", "date"},
    )
    summaries.append(summary)

    summary, _ = _validated_summary(
        "agriculture_price_index",
        server.agriculture_price_index(
            os.environ.get("HANDAAS_TEST_INDEX_DATE", "2026-08-11")
        ),
        {"publishTime", "currentIndexValue", "previousIndexValue", "chainRatio"},
    )
    summaries.append(summary)

    summary, _ = _validated_summary(
        "agriculture_market_report",
        server.agriculture_market_report("week", 2),
        {"publishTime", "reportTitle", "reportContent", "reportType"},
    )
    summaries.append(summary)

    print(json.dumps({"passed": len(summaries), "results": summaries}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

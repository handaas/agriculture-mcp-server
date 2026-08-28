
import asyncio
import importlib.util
import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

SERVER_PATH = Path(__file__).parents[1] / "server" / "mcp_server.py"
SPEC = importlib.util.spec_from_file_location("agriculture_mcp_server", SERVER_PATH)
assert SPEC and SPEC.loader
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


class ContractTests(TestCase):
    def test_registered_tools_and_annotations(self) -> None:
        tools = asyncio.run(server.mcp.list_tools())
        self.assertEqual(server.mcp.name, '农业：农产品价格监控预警')
        self.assertEqual(
            {tool.name for tool in tools},
            {
                "agriculture_product_search",
                "agriculture_wholesale_market_list",
                "agriculture_daily_price_list",
                "agriculture_price_index",
                "agriculture_market_report",
            },
        )
        for tool in tools:
            self.assertEqual(tool.outputSchema.get("type"), "object")
            self.assertTrue(tool.annotations.readOnlyHint)
            self.assertFalse(tool.annotations.destructiveHint)
            self.assertTrue(tool.annotations.idempotentHint)
            self.assertGreaterEqual(len(tool.description or ""), 50)
            self.assertTrue(tool.annotations.openWorldHint)

    def test_product_ids_include_new_agriculture_details(self) -> None:
        self.assertEqual(
            server.PRODUCT_IDS,
            {
                "product_search": "6a7c58fd71276c00fb93e980",
                "wholesale_markets": "6a8447989fbf4ea45da8d758",
                "daily_prices": "6a844b2a9fbf4ea45da8d7b2",
                "price_index": "6a7c626971276c00fb93eab7",
                "market_report": "6a7c637bc90c69ced247c56c",
            },
        )

    def test_missing_credentials_blocks_http(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch.object(server.requests, "post") as post:
            result = server.call_api("product", {})
        self.assertEqual(result, {"error": "INTEGRATOR_ID 未配置"})
        post.assert_not_called()

    def test_backend_envelope_and_pagination_are_normalized(self) -> None:
        wrapped = {"stat": 1, "data": {"dataList": [{"id": 1}], "dataTotal": 3}}
        self.assertEqual(server._normalize_paged(wrapped), {"total": 3, "resultList": [{"id": 1}]})
        self.assertEqual(server._normalize_single({"stat": 1, "data": {"id": 1}}), {"total": 1, "resultList": [{"id": 1}]})
        self.assertEqual(server._normalize_single({"stat": 1, "data": {}}), {"total": 0, "resultList": []})

    def test_product_search_adds_stable_product_id_alias(self) -> None:
        result = server._with_product_id_alias(
            {"total": 2, "resultList": [{"_id": "p-1"}, {"productId": "p-2"}]}
        )
        self.assertEqual(result["resultList"][0]["productId"], "p-1")
        self.assertEqual(result["resultList"][1]["productId"], "p-2")

    def test_wholesale_market_adds_documented_average_price_alias(self) -> None:
        result = server._with_wholesale_market_aliases(
            {"total": 2, "resultList": [{"avg": 5.5}, {"avgPrice": 6.5}]}
        )
        self.assertEqual(result["resultList"][0]["avgPrice"], 5.5)
        self.assertEqual(result["resultList"][1]["avgPrice"], 6.5)

    def test_invalid_pagination_is_actionable(self) -> None:
        error = server._pagination_error(0, 10)
        self.assertEqual(error["parameter"], "pageIndex")
        error = server._pagination_error(1, 11)
        self.assertEqual(error["parameter"], "pageSize")

    def test_empty_business_response_is_normalized(self) -> None:
        response = Mock(status_code=200)
        response.json.return_value = {"code": "10001", "msgCN": "查询数据为空"}
        credentials = {"INTEGRATOR_ID": "integrator", "SECRET_ID": "secret-id", "SECRET_KEY": "secret-key"}
        with patch.dict(os.environ, credentials, clear=True), patch.object(server.requests, "post", return_value=response):
            result = server.call_api("product", {})
        self.assertEqual(result, {"total": 0, "resultList": []})

    def test_html_405_returns_actionable_network_diagnostic(self) -> None:
        response = Mock(status_code=405)
        response.headers = {"content-type": "text/html; charset=utf-8"}
        credentials = {"INTEGRATOR_ID": "integrator", "SECRET_ID": "secret-id", "SECRET_KEY": "secret-key"}
        with patch.dict(os.environ, credentials, clear=True), patch.object(server.requests, "post", return_value=response):
            result = server.call_api("product", {})
        self.assertEqual(result["statusCode"], 405)
        self.assertIn("DNS", result["diagnostic"])
        self.assertIn("PAC", result["diagnostic"])


class RoutingTests(TestCase):
    def test_all_product_routes_and_mapping(self) -> None:
        with patch.object(server, "call_api", return_value={"dataList": [], "dataTotal": 0}) as call:
            server.agriculture_product_search("苹果")
        self.assertEqual(call.call_args.args[0], server.PRODUCT_IDS["product_search"])
        self.assertEqual(
            call.call_args.args[1],
            {"productName": "苹果", "pageIndex": 1, "pageSize": 10},
        )

        with patch.object(server, "call_api", return_value={"resultList": [], "total": 0}) as call:
            server.agriculture_wholesale_market_list("product-1", pageSize=10)
        call.assert_called_once_with(
            server.PRODUCT_IDS["wholesale_markets"],
            {"productId": "product-1", "pageIndex": 1, "pageSize": 10},
        )

        with patch.object(server, "call_api", return_value={"resultList": [], "total": 0}) as call:
            server.agriculture_daily_price_list(
                "product-1",
                origin="广东省",
                startDate="2026-08-01",
                endDate="2026-08-25",
                pageSize=10,
            )
        call.assert_called_once_with(
            server.PRODUCT_IDS["daily_prices"],
            {
                "productId": "product-1",
                "origin": "广东省",
                "startDate": "2026-08-01",
                "endDate": "2026-08-25",
                "pageIndex": 1,
                "pageSize": 10,
            },
        )

        with patch.object(server, "call_api", return_value={"indexList": [{"indexName": "示例"}], "count": 1}) as call:
            result = server.agriculture_price_index("2026-08-21")
        call.assert_called_once_with(server.PRODUCT_IDS["price_index"], {"publishTime": "2026-08-21"})
        self.assertEqual(result, {"total": 1, "resultList": [{"indexName": "示例"}]})

        reports = [{"id": index} for index in range(5)]
        with patch.object(server, "call_api", return_value={"resultList": reports, "total": 5}) as call:
            result = server.agriculture_market_report("week", 3)
        call.assert_called_once_with(server.PRODUCT_IDS["market_report"], {"reportType": "week", "size": 3})
        self.assertEqual(result, {"total": 5, "resultList": reports[:3]})

    def test_invalid_report_size_is_rejected(self) -> None:
        with patch.object(server, "call_api") as call:
            result = server.agriculture_market_report("month", 0)
        self.assertEqual(result["parameter"], "size")
        call.assert_not_called()

    def test_new_detail_filters_are_validated_before_api_call(self) -> None:
        with patch.object(server, "call_api") as call:
            result = server.agriculture_wholesale_market_list(pageSize=11)
        self.assertEqual(result["parameter"], "pageSize")
        call.assert_not_called()

        with patch.object(server, "call_api") as call:
            result = server.agriculture_daily_price_list(
                startDate="2026-08-25",
                endDate="2026-08-01",
            )
        self.assertEqual(result["parameter"], "startDate")
        call.assert_not_called()

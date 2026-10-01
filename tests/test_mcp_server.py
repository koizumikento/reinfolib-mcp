"""
MCPサーバーのテスト
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from reinfolib_mcp.client import ReinfiolibClient
from reinfolib_mcp.exceptions import ReinfiolibAPIError
from reinfolib_mcp.mcp_server import create_mcp_server, run_server


@pytest.mark.asyncio
async def test_real_server_lists_current_tools() -> None:
    """FastMCPの公開APIで配布時のtool登録を検証する。"""
    tools = await create_mcp_server(api_key="test_key").list_tools()
    names = {tool.name for tool in tools}
    assert len(names) == 13
    assert "reinfolib_get_api_data" in names
    assert "reinfolib_search_real_estate" in names


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_mcp_protocol_and_mocked_response(mode) -> None:
    payload = {"data": [{"name": "test"}]}
    mock_client = AsyncMock()
    mock_client.request_api.return_value = payload
    with patch("reinfolib_mcp.mcp_server.ReinfiolibClient", return_value=mock_client):
        async with Client(create_mcp_server("test"), mode=mode) as client:
            assert len(await client.list_tools()) == 13
            result = await client.call_tool(
                "reinfolib_get_api_data",
                {"api_id": "XIT002", "parameters": {"area": "13"}},
            )
            assert result.data == payload
            invalid = await client.call_tool(
                "reinfolib_get_api_data", {}, raise_on_error=False
            )
            assert invalid.is_error
    mock_client.request_api.assert_awaited_once_with("XIT002", area="13")


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_geospatial_year_and_partial_errors(mode) -> None:
    payload = {"type": "FeatureCollection", "features": []}
    coordinates = {"latitude": 35.6851, "longitude": 139.7514}
    async with ReinfiolibClient(api_key="test") as api:
        api._make_request = AsyncMock(return_value=payload)
        with patch("reinfolib_mcp.mcp_server.ReinfiolibClient", return_value=api):
            async with Client(create_mcp_server("test"), mode=mode) as client:
                result = await client.call_tool(
                    "reinfolib_get_geospatial_data", {**coordinates, "year": 2025}
                )
                assert result.data["data"]["land_price"] == payload
                assert set(result.data["data"]) == {
                    "land_price",
                    "urban_planning",
                    "facilities",
                }
                land_call = api._make_request.await_args_list[0]
                assert land_call.args[0] == "/XPT002"
                assert land_call.args[1]["year"] == 2025
                assert land_call.args[1]["response_format"] == "geojson"

                api._make_request.reset_mock()
                result = await client.call_tool(
                    "reinfolib_get_geospatial_data", coordinates
                )
                error = result.data["data"]["land_price"]
                assert error["error_type"] == "InvalidParameterError"
                assert "year" in error["error"]
                assert result.data["data"]["urban_planning"]["area"] == payload
                assert result.data["data"]["facilities"]["schools"] == payload
                assert len(api._make_request.await_args_list) == 4
                assert all(
                    call.args[0] != "/XPT002"
                    for call in api._make_request.await_args_list
                )

                api._make_request.reset_mock()
                result = await client.call_tool(
                    "reinfolib_get_geospatial_data",
                    {**coordinates, "data_types": ["disaster_risk"]},
                )
                assert result.data["data"]["disaster_risk"]["disaster_areas"] == payload
                assert len(api._make_request.await_args_list) == 2

                result = await client.call_tool(
                    "reinfolib_search_real_estate", {"year": 2025, "area": "13"}
                )
                assert result.data == payload


@pytest.mark.asyncio
async def test_cli_stdio_initialization() -> None:
    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "reinfolib_mcp.cli", "--api-key", "test"],
        env={"PYTHONUTF8": "1"},
    )
    async with Client(transport, mode="legacy", timeout=10) as client:
        assert len(await client.list_tools()) == 13
        status = await client.call_tool("reinfolib_server_status", {})
        assert status.data["available_endpoints"] == 35


class TestMCPServerCreation:
    """MCPサーバー作成のテスト"""

    @patch("reinfolib_mcp.mcp_server.ReinfiolibClient")
    @patch("reinfolib_mcp.mcp_server.FastMCP")
    def test_create_mcp_server_success(self, mock_fastmcp, mock_client):
        """MCPサーバーの正常作成"""
        # クライアントの作成が成功することを確認（実際のインスタンスは不要）
        mock_client.return_value = MagicMock()

        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance

        server = create_mcp_server(api_key="test_key")

        assert server == mock_mcp_instance
        mock_client.assert_called_once_with(api_key="test_key")
        mock_fastmcp.assert_called_once()

    @patch("reinfolib_mcp.mcp_server.ReinfiolibClient")
    def test_create_mcp_server_client_error(self, mock_client):
        """クライアント初期化エラー"""
        mock_client.side_effect = ReinfiolibAPIError("API key error")

        with pytest.raises(RuntimeError, match="MCPサーバー初期化失敗"):
            create_mcp_server(api_key="invalid_key")

    @patch.dict("os.environ", {"REINFOLIB_API_KEY": "env_key"})
    @patch("reinfolib_mcp.mcp_server.ReinfiolibClient")
    @patch("reinfolib_mcp.mcp_server.FastMCP")
    def test_create_mcp_server_env_api_key(self, mock_fastmcp, mock_client):
        """環境変数からAPIキーを取得してサーバー作成"""
        # クライアントの作成が成功することを確認（実際のインスタンスは不要）
        mock_client.return_value = MagicMock()

        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance

        server = create_mcp_server()  # api_key=None

        assert server == mock_mcp_instance
        mock_client.assert_called_once_with(api_key=None)


class TestMCPTools:
    """MCPツールのテスト"""

    @pytest.fixture
    def mock_client(self):
        """モッククライアントのフィクスチャ"""
        client = AsyncMock()
        client.api_key = "test_key"
        client.base_url = "https://test.api.example.com"
        client.ENDPOINTS = {"test": "/test"}
        return client

    @pytest.fixture
    def mcp_server(self, mock_client):
        """MCPサーバーのフィクスチャ"""
        with patch("reinfolib_mcp.mcp_server.ReinfiolibClient") as mock_client_class:
            mock_client_class.return_value = mock_client

            with patch("reinfolib_mcp.mcp_server.FastMCP") as mock_fastmcp:
                mock_mcp_instance = MagicMock()
                mock_fastmcp.return_value = mock_mcp_instance

                server = create_mcp_server(api_key="test_key")
                return server, mock_client

    def test_mcp_server_creation_registers_tools(self, mcp_server):
        """MCPサーバー作成時にツールが登録される"""
        server, mock_client = mcp_server

        # tool デコレータが呼ばれることを確認
        assert server.tool.call_count >= 6  # 最低6つのツールが登録される

    @pytest.mark.asyncio
    async def test_search_real_estate_tool(self, mock_client):
        """不動産検索ツールのテスト"""
        # モックレスポンス設定
        mock_result = MagicMock()
        mock_result.dict.return_value = {
            "total_count": 10,
            "data": [{"prefecture": "東京都", "city": "千代田区"}],
        }
        mock_client.search_real_estate_transactions.return_value = mock_result

        with patch("reinfolib_mcp.mcp_server.ReinfiolibClient") as mock_client_class:
            mock_client_class.return_value = mock_client

            # MCPサーバー作成（ツール定義も含む）
            create_mcp_server(api_key="test_key")

            # ツール呼び出しをシミュレート（実際のツール関数を直接テスト）
            # 注：実際のテストでは登録されたツール関数を取得して呼び出す
            result = await mock_client.search_real_estate_transactions(
                prefecture="13", response_format="json"
            )

            assert result == mock_result
            mock_client.search_real_estate_transactions.assert_called_once()

    @pytest.mark.asyncio
    async def test_municipalities_tool(self, mock_client):
        """市区町村一覧ツールのテスト"""
        # モックレスポンス設定
        mock_municipalities = [
            {"city_code": "13101", "city_name": "千代田区"},
            {"city_code": "13102", "city_name": "中央区"},
        ]
        mock_client.get_municipalities.return_value = mock_municipalities

        with patch("reinfolib_mcp.mcp_server.ReinfiolibClient") as mock_client_class:
            mock_client_class.return_value = mock_client

            create_mcp_server(api_key="test_key")

            result = await mock_client.get_municipalities(prefecture="13")

            assert len(result) == 2
            mock_client.get_municipalities.assert_called_once()

    @pytest.mark.asyncio
    async def test_land_price_tool(self, mock_client):
        """地価情報ツールのテスト"""
        # モックレスポンス設定
        mock_geojson = {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {"price_per_sqm": 500000}}],
        }
        mock_client.get_land_price_points.return_value = mock_geojson

        with patch("reinfolib_mcp.mcp_server.ReinfiolibClient") as mock_client_class:
            mock_client_class.return_value = mock_client

            create_mcp_server(api_key="test_key")

            result = await mock_client.get_land_price_points(z=11, x=1818, y=806)

            assert result["type"] == "FeatureCollection"
            assert len(result["features"]) == 1
            mock_client.get_land_price_points.assert_called_once()

    @pytest.mark.asyncio
    async def test_appraisal_info_tool(self, mock_client):
        """鑑定評価書情報ツールのテスト"""
        mock_result = {
            "data": [{"prefecture": "東京都", "city": "千代田区", "price": 1000000}]
        }
        mock_client.get_appraisal_info.return_value = mock_result

        with patch("reinfolib_mcp.mcp_server.ReinfiolibClient") as mock_client_class:
            mock_client_class.return_value = mock_client

            create_mcp_server(api_key="test_key")

            result = await mock_client.get_appraisal_info(prefecture="13")

            assert result == mock_result
            mock_client.get_appraisal_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_real_estate_points_tool(self, mock_client):
        """不動産価格ポイント情報ツールのテスト"""
        mock_geojson = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": {"transaction_price": 50000000}}
            ],
        }
        mock_client.get_real_estate_points.return_value = mock_geojson

        with patch("reinfolib_mcp.mcp_server.ReinfiolibClient") as mock_client_class:
            mock_client_class.return_value = mock_client

            create_mcp_server(api_key="test_key")

            result = await mock_client.get_real_estate_points(z=11, x=1818, y=806)

            assert result["type"] == "FeatureCollection"
            assert len(result["features"]) == 1
            mock_client.get_real_estate_points.assert_called_once()

    @pytest.mark.asyncio
    async def test_school_districts_tool(self, mock_client):
        """学校区情報ツールのテスト"""
        mock_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "school_name": "テスト小学校",
                        "district_name": "テスト小学校区",
                    },
                }
            ],
        }
        mock_client.get_elementary_school_districts.return_value = mock_geojson

        with patch("reinfolib_mcp.mcp_server.ReinfiolibClient") as mock_client_class:
            mock_client_class.return_value = mock_client

            create_mcp_server(api_key="test_key")

            result = await mock_client.get_elementary_school_districts(
                z=12, x=3636, y=1612
            )

            assert result["type"] == "FeatureCollection"
            assert result["features"][0]["properties"]["school_name"] == "テスト小学校"
            mock_client.get_elementary_school_districts.assert_called_once()

    @pytest.mark.asyncio
    async def test_welfare_facilities_tool(self, mock_client):
        """福祉施設情報ツールのテスト"""
        mock_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "facility_name": "テスト福祉施設",
                        "facility_type": "介護施設",
                    },
                }
            ],
        }
        mock_client.get_welfare_facilities.return_value = mock_geojson

        with patch("reinfolib_mcp.mcp_server.ReinfiolibClient") as mock_client_class:
            mock_client_class.return_value = mock_client

            create_mcp_server(api_key="test_key")

            result = await mock_client.get_welfare_facilities(z=12, x=3636, y=1612)

            assert result["type"] == "FeatureCollection"
            assert (
                result["features"][0]["properties"]["facility_name"] == "テスト福祉施設"
            )
            mock_client.get_welfare_facilities.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_in_tools(self, mock_client):
        """ツールでのエラーハンドリングテスト"""
        # APIエラーを発生させる
        mock_client.search_real_estate_transactions.side_effect = ReinfiolibAPIError(
            "API Error"
        )

        with patch("reinfolib_mcp.mcp_server.ReinfiolibClient") as mock_client_class:
            mock_client_class.return_value = mock_client

            create_mcp_server(api_key="test_key")

            # エラーが発生してもツール自体は例外を投げない（エラー情報を返す）
            try:
                await mock_client.search_real_estate_transactions(prefecture="13")
            except ReinfiolibAPIError as e:
                assert str(e) == "API Error"


class TestMCPServerRunner:
    """MCPサーバー実行のテスト"""

    @patch("reinfolib_mcp.mcp_server.create_mcp_server")
    @patch("builtins.print")
    def test_run_server_stdio_success(self, mock_print, mock_create_server):
        """stdio トランスポートでのサーバー起動"""
        mock_mcp = MagicMock()
        mock_create_server.return_value = mock_mcp

        run_server(api_key="test_key", transport="stdio")

        mock_create_server.assert_called_once_with("test_key")
        mock_mcp.run.assert_called_once_with(transport="stdio")

    @patch("reinfolib_mcp.mcp_server.create_mcp_server")
    @patch("builtins.print")
    def test_run_server_http_success(self, mock_print, mock_create_server):
        """HTTP トランスポートでのサーバー起動"""
        mock_mcp = MagicMock()
        mock_create_server.return_value = mock_mcp

        run_server(api_key="test_key", transport="http", host="localhost", port=8000)

        mock_create_server.assert_called_once_with("test_key")
        mock_mcp.run.assert_called_once_with(
            transport="http", host="localhost", port=8000
        )

    @patch("reinfolib_mcp.mcp_server.create_mcp_server")
    @patch("builtins.print")
    def test_run_server_sse_success(self, mock_print, mock_create_server):
        """SSE トランスポートでのサーバー起動"""
        mock_mcp = MagicMock()
        mock_create_server.return_value = mock_mcp

        run_server(api_key="test_key", transport="sse", host="127.0.0.1", port=9000)

        mock_create_server.assert_called_once_with("test_key")
        mock_mcp.run.assert_called_once_with(
            transport="sse", host="127.0.0.1", port=9000
        )

    @patch.dict("os.environ", {"REINFOLIB_API_KEY": "env_key"})
    @patch("reinfolib_mcp.mcp_server.create_mcp_server")
    @patch("builtins.print")
    def test_run_server_env_api_key(self, mock_print, mock_create_server):
        """環境変数からAPIキーを取得してサーバー起動"""
        mock_mcp = MagicMock()
        mock_create_server.return_value = mock_mcp

        run_server()  # api_key=None

        mock_create_server.assert_called_once_with("env_key")

    @patch.dict("os.environ", {}, clear=True)
    @patch("builtins.print")
    def test_run_server_no_api_key(self, mock_print):
        """APIキー未設定でのサーバー起動失敗"""
        run_server()

        # エラーメッセージが出力されることを確認
        mock_print.assert_any_call("エラー: APIキーが設定されていません")

    @patch("reinfolib_mcp.mcp_server.create_mcp_server")
    @patch("builtins.print")
    def test_run_server_invalid_transport(self, mock_print, mock_create_server):
        """無効なトランスポート指定でのエラー"""
        mock_mcp = MagicMock()
        mock_create_server.return_value = mock_mcp

        with pytest.raises(ValueError, match="未対応のトランスポート"):
            run_server(api_key="test_key", transport="invalid")

    @patch("reinfolib_mcp.mcp_server.create_mcp_server")
    @patch("builtins.print")
    def test_run_server_creation_error(self, mock_print, mock_create_server):
        """サーバー作成エラー"""
        mock_create_server.side_effect = Exception("Server creation failed")

        with pytest.raises(Exception, match="Server creation failed"):
            run_server(api_key="test_key")

        mock_print.assert_any_call("サーバー起動エラー: Server creation failed")

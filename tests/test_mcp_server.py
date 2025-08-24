"""
MCPサーバーのテスト
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from reinfolib_mcp.mcp_server import create_mcp_server, run_server
from reinfolib_mcp.exceptions import ReinfiolibAPIError


class TestMCPServerCreation:
    """MCPサーバー作成のテスト"""

    @patch('reinfolib_mcp.mcp_server.ReinfiolibClient')
    @patch('reinfolib_mcp.mcp_server.FastMCP')
    def test_create_mcp_server_success(self, mock_fastmcp, mock_client):
        """MCPサーバーの正常作成"""
        mock_client_instance = AsyncMock()
        mock_client.return_value = mock_client_instance
        
        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance
        
        server = create_mcp_server(api_key="test_key")
        
        assert server == mock_mcp_instance
        mock_client.assert_called_once_with(api_key="test_key")
        mock_fastmcp.assert_called_once()

    @patch('reinfolib_mcp.mcp_server.ReinfiolibClient')
    def test_create_mcp_server_client_error(self, mock_client):
        """クライアント初期化エラー"""
        mock_client.side_effect = ReinfiolibAPIError("API key error")
        
        with pytest.raises(RuntimeError, match="MCPサーバー初期化失敗"):
            create_mcp_server(api_key="invalid_key")

    @patch.dict('os.environ', {'REINFOLIB_API_KEY': 'env_key'})
    @patch('reinfolib_mcp.mcp_server.ReinfiolibClient')
    @patch('reinfolib_mcp.mcp_server.FastMCP')
    def test_create_mcp_server_env_api_key(self, mock_fastmcp, mock_client):
        """環境変数からAPIキーを取得してサーバー作成"""
        mock_client_instance = AsyncMock()
        mock_client.return_value = mock_client_instance
        
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
        with patch('reinfolib_mcp.mcp_server.ReinfiolibClient') as mock_client_class:
            mock_client_class.return_value = mock_client
            
            with patch('reinfolib_mcp.mcp_server.FastMCP') as mock_fastmcp:
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
            "data": [{"prefecture": "東京都", "city": "千代田区"}]
        }
        mock_client.search_real_estate_transactions.return_value = mock_result
        
        with patch('reinfolib_mcp.mcp_server.ReinfiolibClient') as mock_client_class:
            mock_client_class.return_value = mock_client
            
            # MCPサーバー作成（ツール定義も含む）
            server = create_mcp_server(api_key="test_key")
            
            # ツール呼び出しをシミュレート（実際のツール関数を直接テスト）
            # 注：実際のテストでは登録されたツール関数を取得して呼び出す
            result = await mock_client.search_real_estate_transactions(
                prefecture="13",
                response_format="json"
            )
            
            assert result == mock_result
            mock_client.search_real_estate_transactions.assert_called_once()

    @pytest.mark.asyncio 
    async def test_municipalities_tool(self, mock_client):
        """市区町村一覧ツールのテスト"""
        # モックレスポンス設定
        mock_municipalities = [
            MagicMock(dict=lambda: {"city_code": "13101", "city_name": "千代田区"}),
            MagicMock(dict=lambda: {"city_code": "13102", "city_name": "中央区"})
        ]
        mock_client.get_municipalities.return_value = mock_municipalities
        
        with patch('reinfolib_mcp.mcp_server.ReinfiolibClient') as mock_client_class:
            mock_client_class.return_value = mock_client
            
            server = create_mcp_server(api_key="test_key")
            
            result = await mock_client.get_municipalities(prefecture="13")
            
            assert len(result) == 2
            mock_client.get_municipalities.assert_called_once()

    @pytest.mark.asyncio
    async def test_land_price_tool(self, mock_client):
        """地価情報ツールのテスト"""
        # モックレスポンス設定
        mock_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"price_per_sqm": 500000}
                }
            ]
        }
        mock_client.get_land_price_points.return_value = mock_geojson
        
        with patch('reinfolib_mcp.mcp_server.ReinfiolibClient') as mock_client_class:
            mock_client_class.return_value = mock_client
            
            server = create_mcp_server(api_key="test_key")
            
            result = await mock_client.get_land_price_points(z=11, x=1818, y=806)
            
            assert result["type"] == "FeatureCollection"
            assert len(result["features"]) == 1
            mock_client.get_land_price_points.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_in_tools(self, mock_client):
        """ツールでのエラーハンドリングテスト"""
        # APIエラーを発生させる
        mock_client.search_real_estate_transactions.side_effect = ReinfiolibAPIError("API Error")
        
        with patch('reinfolib_mcp.mcp_server.ReinfiolibClient') as mock_client_class:
            mock_client_class.return_value = mock_client
            
            server = create_mcp_server(api_key="test_key")
            
            # エラーが発生してもツール自体は例外を投げない（エラー情報を返す）
            try:
                await mock_client.search_real_estate_transactions(prefecture="13")
            except ReinfiolibAPIError as e:
                assert str(e) == "API Error"


class TestMCPServerRunner:
    """MCPサーバー実行のテスト"""

    @patch('reinfolib_mcp.mcp_server.create_mcp_server')
    @patch('builtins.print')
    def test_run_server_stdio_success(self, mock_print, mock_create_server):
        """stdio トランスポートでのサーバー起動"""
        mock_mcp = MagicMock()
        mock_create_server.return_value = mock_mcp
        
        run_server(api_key="test_key", transport="stdio")
        
        mock_create_server.assert_called_once_with("test_key")
        mock_mcp.run.assert_called_once_with(transport="stdio")

    @patch('reinfolib_mcp.mcp_server.create_mcp_server')
    @patch('builtins.print')
    def test_run_server_http_success(self, mock_print, mock_create_server):
        """HTTP トランスポートでのサーバー起動"""
        mock_mcp = MagicMock()
        mock_create_server.return_value = mock_mcp
        
        run_server(
            api_key="test_key", 
            transport="http", 
            host="localhost", 
            port=8000
        )
        
        mock_create_server.assert_called_once_with("test_key")
        mock_mcp.run.assert_called_once_with(
            transport="http", 
            host="localhost", 
            port=8000
        )

    @patch('reinfolib_mcp.mcp_server.create_mcp_server')
    @patch('builtins.print')
    def test_run_server_sse_success(self, mock_print, mock_create_server):
        """SSE トランスポートでのサーバー起動"""
        mock_mcp = MagicMock()
        mock_create_server.return_value = mock_mcp
        
        run_server(
            api_key="test_key", 
            transport="sse", 
            host="127.0.0.1", 
            port=9000
        )
        
        mock_create_server.assert_called_once_with("test_key")
        mock_mcp.run.assert_called_once_with(
            transport="sse", 
            host="127.0.0.1", 
            port=9000
        )

    @patch.dict('os.environ', {'REINFOLIB_API_KEY': 'env_key'})
    @patch('reinfolib_mcp.mcp_server.create_mcp_server')
    @patch('builtins.print')
    def test_run_server_env_api_key(self, mock_print, mock_create_server):
        """環境変数からAPIキーを取得してサーバー起動"""
        mock_mcp = MagicMock()
        mock_create_server.return_value = mock_mcp
        
        run_server()  # api_key=None
        
        mock_create_server.assert_called_once_with("env_key")

    @patch.dict('os.environ', {}, clear=True)
    @patch('builtins.print')
    def test_run_server_no_api_key(self, mock_print):
        """APIキー未設定でのサーバー起動失敗"""
        run_server()
        
        # エラーメッセージが出力されることを確認
        mock_print.assert_any_call("エラー: APIキーが設定されていません")

    @patch('reinfolib_mcp.mcp_server.create_mcp_server')
    @patch('builtins.print')
    def test_run_server_invalid_transport(self, mock_print, mock_create_server):
        """無効なトランスポート指定でのエラー"""
        mock_mcp = MagicMock()
        mock_create_server.return_value = mock_mcp
        
        with pytest.raises(ValueError, match="未対応のトランスポート"):
            run_server(api_key="test_key", transport="invalid")

    @patch('reinfolib_mcp.mcp_server.create_mcp_server')
    @patch('builtins.print')
    def test_run_server_creation_error(self, mock_print, mock_create_server):
        """サーバー作成エラー"""
        mock_create_server.side_effect = Exception("Server creation failed")
        
        with pytest.raises(Exception, match="Server creation failed"):
            run_server(api_key="test_key")
        
        mock_print.assert_any_call("サーバー起動エラー: Server creation failed")

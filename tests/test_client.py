"""
APIクライアントのテスト
"""

import pytest
from unittest.mock import AsyncMock, patch
import httpx

from reinfolib_mcp.client import ReinfiolibClient, SyncReinfiolibClient
from reinfolib_mcp.exceptions import (
    AuthenticationError,
    InvalidParameterError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ReinfiolibAPIError,
    ServerError,
)
from reinfolib_mcp.models import Language, ResponseFormat


class TestReinfiolibClient:
    """非同期APIクライアントのテスト"""

    def test_client_initialization_with_api_key(self):
        """APIキー指定でのクライアント初期化"""
        client = ReinfiolibClient(api_key="test_api_key")
        
        assert client.api_key == "test_api_key"
        assert client.base_url == "https://www.reinfolib.mlit.go.jp/ex-api/external"
        assert client.timeout == 30.0

    def test_client_initialization_without_api_key(self):
        """APIキー未設定での初期化エラー"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ReinfiolibAPIError, match="APIキーが設定されていません"):
                ReinfiolibClient()

    @patch.dict('os.environ', {'REINFOLIB_API_KEY': 'env_api_key'})
    def test_client_initialization_from_env(self):
        """環境変数からのAPIキー取得"""
        client = ReinfiolibClient()
        assert client.api_key == "env_api_key"

    def test_custom_base_url_and_timeout(self):
        """カスタムベースURLとタイムアウトの設定"""
        client = ReinfiolibClient(
            api_key="test_key",
            base_url="https://custom.api.example.com",
            timeout=60.0
        )
        
        assert client.base_url == "https://custom.api.example.com"
        assert client.timeout == 60.0

    @pytest.mark.asyncio
    async def test_successful_real_estate_search(self):
        """不動産検索の成功テスト"""
        mock_response_data = {
            "total_count": 100,
            "page": 1,
            "per_page": 100,
            "data": [
                {
                    "prefecture": "東京都",
                    "city": "千代田区",
                    "transaction_price": 50000000,
                    "area": 100.5,
                    "transaction_period": "2023年第1四半期"
                }
            ]
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_client.return_value.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client.return_value
            mock_client.return_value.__aexit__.return_value = None

            client = ReinfiolibClient(api_key="test_key")
            result = await client.search_real_estate_transactions(
                prefecture="13",
                city="13101"
            )

            assert result.total_count == 100
            assert len(result.data) == 1
            assert result.data[0].prefecture == "東京都"

    @pytest.mark.asyncio
    async def test_municipalities_list(self):
        """市区町村一覧取得のテスト"""
        mock_response_data = {
            "data": [
                {
                    "prefecture_code": "13",
                    "prefecture_name": "東京都",
                    "city_code": "13101",
                    "city_name": "千代田区"
                },
                {
                    "prefecture_code": "13",
                    "prefecture_name": "東京都",
                    "city_code": "13102",
                    "city_name": "中央区"
                }
            ]
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_client.return_value.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client.return_value
            mock_client.return_value.__aexit__.return_value = None

            client = ReinfiolibClient(api_key="test_key")
            result = await client.get_municipalities(
                prefecture="13",
                lang=Language.JAPANESE
            )

            assert len(result) == 2
            assert result[0].city_name == "千代田区"
            assert result[1].city_name == "中央区"

    @pytest.mark.asyncio
    async def test_geojson_response(self):
        """GeoJSONレスポンスのテスト"""
        mock_geojson_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [139.7514, 35.6851]
                    },
                    "properties": {
                        "price_per_sqm": 500000,
                        "year": 2023
                    }
                }
            ]
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_geojson_data
            mock_client.return_value.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client.return_value
            mock_client.return_value.__aexit__.return_value = None

            client = ReinfiolibClient(api_key="test_key")
            result = await client.get_land_price_points(
                z=11, x=1818, y=806,
                response_format=ResponseFormat.GEOJSON
            )

            assert result["type"] == "FeatureCollection"
            assert len(result["features"]) == 1
            assert result["features"][0]["properties"]["price_per_sqm"] == 500000

    @pytest.mark.asyncio
    async def test_authentication_error(self):
        """認証エラーのテスト"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_client.return_value.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client.return_value
            mock_client.return_value.__aexit__.return_value = None

            client = ReinfiolibClient(api_key="invalid_key")
            
            with pytest.raises(AuthenticationError):
                await client.search_real_estate_transactions(prefecture="13")

    @pytest.mark.asyncio
    async def test_invalid_parameter_error(self):
        """パラメータエラーのテスト"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 400
            mock_client.return_value.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client.return_value
            mock_client.return_value.__aexit__.return_value = None

            client = ReinfiolibClient(api_key="test_key")
            
            with pytest.raises(InvalidParameterError):
                await client.search_real_estate_transactions(prefecture="invalid")

    @pytest.mark.asyncio
    async def test_not_found_error(self):
        """404エラーのテスト"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 404
            mock_client.return_value.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client.return_value
            mock_client.return_value.__aexit__.return_value = None

            client = ReinfiolibClient(api_key="test_key")
            
            with pytest.raises(NotFoundError):
                await client.get_municipalities(prefecture="99")

    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        """レート制限エラーのテスト"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 429
            mock_client.return_value.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client.return_value
            mock_client.return_value.__aexit__.return_value = None

            client = ReinfiolibClient(api_key="test_key")
            
            with pytest.raises(RateLimitError):
                await client.search_real_estate_transactions(prefecture="13")

    @pytest.mark.asyncio
    async def test_server_error(self):
        """サーバーエラーのテスト"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_client.return_value.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client.return_value
            mock_client.return_value.__aexit__.return_value = None

            client = ReinfiolibClient(api_key="test_key")
            
            with pytest.raises(ServerError):
                await client.get_land_price_points(z=11, x=1818, y=806)

    @pytest.mark.asyncio
    async def test_network_error(self):
        """ネットワークエラーのテスト"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.get.side_effect = httpx.ConnectError("Connection failed")
            mock_client.return_value.__aenter__.return_value = mock_client.return_value
            mock_client.return_value.__aexit__.return_value = None

            client = ReinfiolibClient(api_key="test_key")
            
            with pytest.raises(NetworkError):
                await client.search_real_estate_transactions(prefecture="13")

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """コンテキストマネージャーのテスト"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_client.return_value
            mock_client.return_value.__aexit__.return_value = None
            mock_client.return_value.aclose = AsyncMock()

            async with ReinfiolibClient(api_key="test_key") as client:
                assert client.api_key == "test_key"
            
            # acloseが呼ばれることを確認
            mock_client.return_value.aclose.assert_called_once()


class TestSyncReinfiolibClient:
    """同期APIクライアントのテスト"""

    def test_sync_client_initialization(self):
        """同期クライアントの初期化"""
        with patch('reinfolib_mcp.client.ReinfiolibClient') as mock_async_client:
            mock_async_client.return_value = AsyncMock()
            
            client = SyncReinfiolibClient(api_key="test_key")
            assert client._async_client is not None

    def test_sync_search_real_estate_transactions(self):
        """同期版不動産検索のテスト"""
        mock_result = AsyncMock()
        mock_result.total_count = 50
        
        with patch('reinfolib_mcp.client.ReinfiolibClient') as mock_async_client:
            mock_instance = AsyncMock()
            mock_instance.search_real_estate_transactions.return_value = mock_result
            mock_async_client.return_value = mock_instance
            
            with patch('asyncio.run') as mock_run:
                mock_run.return_value = mock_result
                
                client = SyncReinfiolibClient(api_key="test_key")
                result = client.search_real_estate_transactions(prefecture="13")
                
                assert result == mock_result
                mock_run.assert_called_once()

    def test_sync_get_municipalities(self):
        """同期版市区町村一覧取得のテスト"""
        mock_result = [AsyncMock(), AsyncMock()]
        
        with patch('reinfolib_mcp.client.ReinfiolibClient') as mock_async_client:
            mock_instance = AsyncMock()
            mock_instance.get_municipalities.return_value = mock_result
            mock_async_client.return_value = mock_instance
            
            with patch('asyncio.run') as mock_run:
                mock_run.return_value = mock_result
                
                client = SyncReinfiolibClient(api_key="test_key")
                result = client.get_municipalities(prefecture="13")
                
                assert result == mock_result
                mock_run.assert_called_once()

    def test_sync_context_manager(self):
        """同期版コンテキストマネージャーのテスト"""
        with patch('reinfolib_mcp.client.ReinfiolibClient') as mock_async_client:
            mock_instance = AsyncMock()
            mock_async_client.return_value = mock_instance
            
            with patch('asyncio.run') as mock_run:
                with SyncReinfiolibClient(api_key="test_key") as client:
                    assert client is not None
                
                # closeが呼ばれることを確認
                mock_run.assert_called_once()

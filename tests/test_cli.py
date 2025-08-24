"""
CLIのテスト
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner

from reinfolib_mcp.cli import main
from reinfolib_mcp.exceptions import ReinfiolibAPIError


class TestCLIMain:
    """メインCLIコマンドのテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.runner = CliRunner()

    def test_cli_help(self):
        """ヘルプ表示のテスト"""
        result = self.runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        assert "不動産情報ライブラリMCPツール" in result.output
        assert "国土交通省の不動産情報ライブラリAPI" in result.output

    def test_cli_version(self):
        """バージョン表示のテスト"""
        result = self.runner.invoke(main, ['--version'])
        
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    @patch('reinfolib_mcp.cli.run_server')
    def test_cli_default_mcp_server(self, mock_run_server):
        """デフォルトでMCPサーバー起動"""
        result = self.runner.invoke(main, ['--api-key', 'test_key'])
        
        assert result.exit_code == 0
        mock_run_server.assert_called_once_with(
            api_key='test_key',
            transport='stdio',
            host='localhost',
            port=8000
        )

    @patch('reinfolib_mcp.cli.run_server')
    def test_cli_http_transport(self, mock_run_server):
        """HTTPトランスポートでのサーバー起動"""
        result = self.runner.invoke(main, [
            '--api-key', 'test_key',
            '--transport', 'http',
            '--host', '0.0.0.0',
            '--port', '9000'
        ])
        
        assert result.exit_code == 0
        mock_run_server.assert_called_once_with(
            api_key='test_key',
            transport='http',
            host='0.0.0.0',
            port=9000
        )

    @patch.dict('os.environ', {'REINFOLIB_API_KEY': 'env_key'})
    @patch('reinfolib_mcp.cli.run_server')
    def test_cli_env_api_key(self, mock_run_server):
        """環境変数からAPIキーを取得"""
        result = self.runner.invoke(main, [])
        
        assert result.exit_code == 0
        mock_run_server.assert_called_once_with(
            api_key='env_key',
            transport='stdio',
            host='localhost',
            port=8000
        )

    @patch.dict('os.environ', {}, clear=True)
    @patch('sys.stdin.isatty', return_value=False)
    def test_cli_no_api_key_non_interactive(self, mock_isatty):
        """非対話モードでAPIキー未設定の場合のエラー"""
        result = self.runner.invoke(main, [])
        
        assert result.exit_code == 1
        assert "APIキーが設定されていません" in result.output


class TestCLISearchCommand:
    """検索コマンドのテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.runner = CliRunner()

    @patch('reinfolib_mcp.cli.ReinfiolibClient')
    def test_search_command_success(self, mock_client_class):
        """検索コマンドの成功テスト"""
        # モッククライアントの設定
        mock_client = AsyncMock()
        mock_result = MagicMock()
        mock_result.dict.return_value = {
            "total_count": 2,
            "data": [
                {
                    "prefecture": "東京都",
                    "city": "千代田区",
                    "transaction_price": 50000000,
                    "area": 100.5,
                    "transaction_period": "2023年第1四半期"
                },
                {
                    "prefecture": "東京都", 
                    "city": "中央区",
                    "transaction_price": 60000000,
                    "area": 120.0,
                    "transaction_period": "2023年第2四半期"
                }
            ]
        }
        mock_client.search_real_estate_transactions.return_value = mock_result
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        result = self.runner.invoke(main, [
            '--api-key', 'test_key',
            'search',
            '--prefecture', '13',
            '--limit', '2'
        ])

        assert result.exit_code == 0
        assert "検索結果: 2件" in result.output
        assert "千代田区" in result.output
        assert "中央区" in result.output

    @patch('reinfolib_mcp.cli.ReinfiolibClient')
    def test_search_command_json_format(self, mock_client_class):
        """JSON形式での検索結果出力"""
        mock_client = AsyncMock()
        mock_result = MagicMock()
        mock_result.dict.return_value = {
            "total_count": 1,
            "data": [
                {
                    "prefecture": "東京都",
                    "city": "千代田区",
                    "transaction_price": 50000000
                }
            ]
        }
        mock_client.search_real_estate_transactions.return_value = mock_result
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        result = self.runner.invoke(main, [
            '--api-key', 'test_key',
            'search',
            '--prefecture', '13',
            '--format', 'json'
        ])

        assert result.exit_code == 0
        
        # JSON出力の確認 - 複数行JSONを処理
        output_lines = result.output.strip().split('\n')
        json_start_idx = None
        for i, line in enumerate(output_lines):
            if line.startswith('{'):
                json_start_idx = i
                break
        
        assert json_start_idx is not None, "JSON output not found"
        json_content = '\n'.join(output_lines[json_start_idx:])
        json_output = json.loads(json_content)
        
        assert json_output is not None
        assert json_output["total_count"] == 1

    @patch('reinfolib_mcp.cli.ReinfiolibClient')
    def test_search_command_api_error(self, mock_client_class):
        """API エラー時の検索コマンド"""
        mock_client = AsyncMock()
        mock_client.search_real_estate_transactions.side_effect = ReinfiolibAPIError("API Error")
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        result = self.runner.invoke(main, [
            '--api-key', 'test_key',
            'search',
            '--prefecture', '13'
        ])

        assert result.exit_code == 1
        assert "APIエラー: API Error" in result.output

    def test_search_command_missing_prefecture(self):
        """必須パラメータ不足のエラー"""
        result = self.runner.invoke(main, [
            '--api-key', 'test_key',
            'search'
        ])

        assert result.exit_code == 2  # Click validation error
        assert "Missing option" in result.output or "Error" in result.output

    @patch('reinfolib_mcp.cli.ReinfiolibClient')
    def test_search_command_all_options(self, mock_client_class):
        """全オプション指定での検索"""
        mock_client = AsyncMock()
        mock_result = MagicMock()
        mock_result.dict.return_value = {"total_count": 0, "data": []}
        mock_client.search_real_estate_transactions.return_value = mock_result
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        result = self.runner.invoke(main, [
            '--api-key', 'test_key',
            'search',
            '--prefecture', '13',
            '--city', '13101',
            '--from-date', '20230101',
            '--to-date', '20231231',
            '--property-type', '1',
            '--language', 'en',
            '--limit', '5',
            '--format', 'table'
        ])

        assert result.exit_code == 0
        mock_client.search_real_estate_transactions.assert_called_once()


class TestCLIMunicipalitiesCommand:
    """市区町村コマンドのテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.runner = CliRunner()

    @patch('reinfolib_mcp.cli.ReinfiolibClient')
    def test_municipalities_command_success(self, mock_client_class):
        """市区町村コマンドの成功テスト"""
        mock_client = AsyncMock()
        mock_municipalities = [
            MagicMock(
                prefecture_name="東京都",
                city_code="13101",
                city_name="千代田区",
                city_name_en="Chiyoda City"
            ),
            MagicMock(
                prefecture_name="東京都",
                city_code="13102", 
                city_name="中央区",
                city_name_en="Chuo City"
            )
        ]
        mock_client.get_municipalities.return_value = mock_municipalities
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        result = self.runner.invoke(main, [
            '--api-key', 'test_key',
            'municipalities',
            '--prefecture', '13'
        ])

        assert result.exit_code == 0
        assert "市区町村一覧: 2件" in result.output
        assert "千代田区" in result.output
        assert "中央区" in result.output

    @patch('reinfolib_mcp.cli.ReinfiolibClient')
    def test_municipalities_command_json_format(self, mock_client_class):
        """JSON形式での市区町村一覧出力"""
        mock_client = AsyncMock()
        mock_municipality = MagicMock()
        mock_municipality.dict.return_value = {
            "prefecture_code": "13",
            "prefecture_name": "東京都",
            "city_code": "13101",
            "city_name": "千代田区"
        }
        mock_client.get_municipalities.return_value = [mock_municipality]
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        result = self.runner.invoke(main, [
            '--api-key', 'test_key',
            'municipalities',
            '--prefecture', '13',
            '--format', 'json'
        ])

        assert result.exit_code == 0
        
        # JSON出力の確認 - 複数行JSONを処理
        output_lines = result.output.strip().split('\n')
        json_start_idx = None
        for i, line in enumerate(output_lines):
            if line.startswith('{'):
                json_start_idx = i
                break
        
        assert json_start_idx is not None, "JSON output not found"
        json_content = '\n'.join(output_lines[json_start_idx:])
        json_output = json.loads(json_content)
        assert json_output["total_count"] == 1


class TestCLILocationCommand:
    """位置情報コマンドのテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.runner = CliRunner()

    @patch('reinfolib_mcp.cli.ReinfiolibClient')
    def test_location_command_success(self, mock_client_class):
        """位置情報コマンドの成功テスト"""
        mock_client = AsyncMock()
        
        # 各データタイプのモックレスポンス
        mock_client.get_land_price_points.return_value = {"features": [{"properties": {"price": 500000}}]}
        mock_client.get_urban_planning_area.return_value = {"features": []}
        mock_client.get_land_use_zones.return_value = {"features": []}
        
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        result = self.runner.invoke(main, [
            '--api-key', 'test_key',
            'location',
            '--latitude', '35.6851',
            '--longitude', '139.7514',
            '--zoom', '12',
            '--data-types', 'land_price',
            '--data-types', 'urban_planning'
        ])

        assert result.exit_code == 0
        assert "位置情報: 緯度35.6851, 経度139.7514" in result.output
        assert "land_price:" in result.output
        assert "urban_planning:" in result.output

    def test_location_command_missing_coordinates(self):
        """座標パラメータ不足のエラー"""
        result = self.runner.invoke(main, [
            '--api-key', 'test_key',
            'location',
            '--latitude', '35.6851'
            # --longitudeが不足
        ])

        assert result.exit_code == 2  # Click validation error


class TestCLIStatusCommand:
    """ステータスコマンドのテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.runner = CliRunner()

    @patch('reinfolib_mcp.cli.ReinfiolibClient')
    def test_status_command_success(self, mock_client_class):
        """ステータスコマンドの成功テスト"""
        mock_client = AsyncMock()
        mock_client.base_url = "https://test.api.example.com"
        mock_client.ENDPOINTS = {"test": "/test"}
        mock_client.get_municipalities.return_value = [MagicMock(), MagicMock()]
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        result = self.runner.invoke(main, [
            '--api-key', 'test_key',
            'status'
        ])

        assert result.exit_code == 0
        assert "不動産情報ライブラリMCP 状態確認" in result.output
        assert "バージョン: 0.1.0" in result.output
        assert "APIキー設定: ✓" in result.output
        assert "API接続: ✓" in result.output

    def test_status_command_no_api_key(self):
        """APIキー未設定でのステータス確認"""
        result = self.runner.invoke(main, ['status'])

        assert result.exit_code == 0
        assert "APIキー設定: ✗" in result.output
        assert "環境変数REINFOLIB_API_KEYでAPIキーを設定してください" in result.output

    @patch('reinfolib_mcp.cli.ReinfiolibClient')
    def test_status_command_api_error(self, mock_client_class):
        """API接続エラー時のステータス確認"""
        mock_client = AsyncMock()
        mock_client.get_municipalities.side_effect = ReinfiolibAPIError("Connection failed")
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        result = self.runner.invoke(main, [
            '--api-key', 'test_key',
            'status'
        ])

        assert result.exit_code == 0
        assert "API接続: ✗" in result.output
        assert "Connection failed" in result.output


class TestCLIValidation:
    """CLI バリデーションのテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.runner = CliRunner()

    def test_invalid_transport_option(self):
        """無効なトランスポートオプション"""
        result = self.runner.invoke(main, [
            '--api-key', 'test_key',
            '--transport', 'invalid'
        ])

        assert result.exit_code == 2  # Click validation error

    def test_invalid_language_option(self):
        """無効な言語オプション"""
        result = self.runner.invoke(main, [
            '--api-key', 'test_key',
            'search',
            '--prefecture', '13',
            '--language', 'invalid'
        ])

        assert result.exit_code == 2  # Click validation error

    def test_invalid_format_option(self):
        """無効なフォーマットオプション"""
        result = self.runner.invoke(main, [
            '--api-key', 'test_key',
            'search',
            '--prefecture', '13',
            '--format', 'invalid'
        ])

        assert result.exit_code == 2  # Click validation error

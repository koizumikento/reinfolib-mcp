#!/usr/bin/env python3
"""
不動産情報ライブラリMCP クライアント使用例

このスクリプトはMCPサーバーとして起動した不動産情報ライブラリAPIとの
クライアント側での連携例を示します。
"""

import json
import os
import subprocess
import time
from typing import Dict, Any, List


class MCPServerManager:
    """MCPサーバーの管理クラス"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.server_process = None
    
    def start_server(self, transport: str = "http", port: int = 8000) -> bool:
        """MCPサーバーを起動"""
        try:
            # uvxを使ってMCPサーバーを起動
            cmd = [
                "uvx", "--from", ".", "reinfolib-mcp",
                "--transport", transport,
                "--port", str(port)
            ]
            
            env = os.environ.copy()
            env["REINFOLIB_API_KEY"] = self.api_key
            
            print(f"MCPサーバーを起動中: {' '.join(cmd)}")
            self.server_process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # サーバーの起動を待つ
            time.sleep(5)
            
            if self.server_process.poll() is None:
                print(f"MCPサーバーが正常に起動しました（PID: {self.server_process.pid}）")
                return True
            else:
                print("MCPサーバーの起動に失敗しました")
                return False
                
        except Exception as e:
            print(f"サーバー起動エラー: {e}")
            return False
    
    def stop_server(self):
        """MCPサーバーを停止"""
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
            print("MCPサーバーを停止しました")


def simulate_mcp_client_requests():
    """MCPクライアントのリクエストをシミュレート"""
    print("=== MCPクライアントリクエストシミュレーション ===")
    
    # MCPクライアントからのリクエスト例を表示
    mcp_requests = [
        {
            "method": "tools/list",
            "description": "利用可能なツールの一覧を取得"
        },
        {
            "method": "tools/call",
            "params": {
                "name": "reinfolib_search_real_estate",
                "arguments": {
                    "prefecture": "13",
                    "city": "13101",
                    "from_date": "20230101",
                    "to_date": "20231231"
                }
            },
            "description": "東京都千代田区の不動産取引価格を検索"
        },
        {
            "method": "tools/call",
            "params": {
                "name": "reinfolib_get_municipalities",
                "arguments": {
                    "prefecture": "13",
                    "language": "ja"
                }
            },
            "description": "東京都の市区町村一覧を取得"
        },
        {
            "method": "tools/call",
            "params": {
                "name": "reinfolib_get_land_price",
                "arguments": {
                    "zoom_level": 11,
                    "tile_x": 1818,
                    "tile_y": 806,
                    "response_format": "geojson"
                }
            },
            "description": "地価公示・調査ポイント情報を取得"
        },
        {
            "method": "tools/call",
            "params": {
                "name": "reinfolib_get_urban_planning",
                "arguments": {
                    "zoom_level": 12,
                    "tile_x": 3636,
                    "tile_y": 1612,
                    "info_type": "zones",
                    "response_format": "geojson"
                }
            },
            "description": "都市計画情報（用途地域）を取得"
        },
        {
            "method": "tools/call",
            "params": {
                "name": "reinfolib_search_facilities",
                "arguments": {
                    "zoom_level": 12,
                    "tile_x": 3636,
                    "tile_y": 1612,
                    "facility_type": "schools",
                    "response_format": "geojson"
                }
            },
            "description": "周辺学校情報を検索"
        },
        {
            "method": "tools/call",
            "params": {
                "name": "reinfolib_get_disaster_risk",
                "arguments": {
                    "zoom_level": 12,
                    "tile_x": 3636,
                    "tile_y": 1612,
                    "risk_type": "liquefaction",
                    "response_format": "geojson"
                }
            },
            "description": "液状化発生傾向情報を取得"
        },
        {
            "method": "tools/call",
            "params": {
                "name": "reinfolib_get_geospatial_data",
                "arguments": {
                    "latitude": 35.6851,
                    "longitude": 139.7514,
                    "zoom_level": 12,
                    "data_types": ["land_price", "urban_planning", "facilities"],
                    "response_format": "geojson"
                }
            },
            "description": "東京駅周辺の統合地理空間データを取得"
        },
        {
            "method": "tools/call",
            "params": {
                "name": "reinfolib_server_status",
                "arguments": {}
            },
            "description": "MCPサーバーの状態を確認"
        }
    ]
    
    for i, request in enumerate(mcp_requests, 1):
        print(f"\n{i}. {request['description']}")
        print("   MCPリクエスト:")
        print(f"   {json.dumps(request, indent=4, ensure_ascii=False)}")


def claude_desktop_config_example():
    """Claude Desktop設定例"""
    print("\n=== Claude Desktop 設定例 ===")
    
    config = {
        "mcpServers": {
            "reinfolib": {
                "command": "uvx",
                "args": ["reinfolib-mcp"],
                "env": {
                    "REINFOLIB_API_KEY": "your_api_key_here"
                }
            }
        }
    }
    
    print("config.json に以下の設定を追加:")
    print(json.dumps(config, indent=2, ensure_ascii=False))
    
    print("\n設定手順:")
    print("1. Claude Desktop の設定ファイルを開く")
    print("   - macOS: ~/Library/Application Support/Claude/config.json")
    print("   - Windows: %APPDATA%\\Claude\\config.json")
    print("2. 上記の設定を追加")
    print("3. REINFOLIB_API_KEY を実際のAPIキーに置き換え")
    print("4. Claude Desktop を再起動")


def cursor_mcp_config_example():
    """Cursor MCP設定例"""
    print("\n=== Cursor MCP 設定例 ===")
    
    config = {
        "mcpServers": {
            "reinfolib": {
                "command": "uvx",
                "args": ["reinfolib-mcp"],
                "env": {
                    "REINFOLIB_API_KEY": "your_api_key_here"
                }
            }
        }
    }
    
    print("Cursor の設定に以下を追加:")
    print(json.dumps(config, indent=2, ensure_ascii=False))
    
    print("\n使用例:")
    examples = [
        "東京都千代田区の不動産価格を教えて",
        "大阪府の市区町村一覧を取得して",
        "東京駅周辺の地価情報を調べて",
        "渋谷区の学校と医療機関の情報を取得",
        "新宿駅周辺の災害リスク情報を確認",
        "横浜市中区の都市計画情報を表示",
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"{i}. {example}")


def uvx_usage_examples():
    """uvx実行パターンの例"""
    print("\n=== uvx実行パターン例 ===")
    
    examples = [
        {
            "command": "uvx reinfolib-mcp",
            "description": "MCPサーバーをstdioトランスポートで起動（デフォルト）"
        },
        {
            "command": "uvx reinfolib-mcp --transport http --port 8000",
            "description": "HTTPサーバーとして起動"
        },
        {
            "command": "uvx reinfolib-mcp --transport sse --host 0.0.0.0 --port 9000",
            "description": "SSEサーバーとして起動"
        },
        {
            "command": "uvx reinfolib-mcp search --prefecture 13 --limit 5",
            "description": "東京都の不動産情報を直接検索"
        },
        {
            "command": "uvx reinfolib-mcp municipalities --prefecture 27",
            "description": "大阪府の市区町村一覧を取得"
        },
        {
            "command": "uvx reinfolib-mcp location --latitude 35.6851 --longitude 139.7514",
            "description": "東京駅周辺の地理空間データを取得"
        },
        {
            "command": "uvx reinfolib-mcp status",
            "description": "システム状態とAPI接続を確認"
        },
        {
            "command": "REINFOLIB_API_KEY=your_key uvx reinfolib-mcp",
            "description": "環境変数でAPIキーを設定して起動"
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"{i}. {example['description']}")
        print(f"   $ {example['command']}")
        print()


def integration_workflow_example():
    """統合ワークフロー例"""
    print("\n=== 統合ワークフロー例 ===")
    
    workflow_steps = [
        {
            "step": "1. 地域選定",
            "action": "不動産投資候補地域の選定",
            "tools": [
                "reinfolib_search_real_estate（価格相場調査）",
                "reinfolib_get_municipalities（エリア一覧取得）"
            ]
        },
        {
            "step": "2. 詳細調査",
            "action": "選定地域の詳細情報収集",
            "tools": [
                "reinfolib_get_land_price（地価動向分析）",
                "reinfolib_get_urban_planning（都市計画制限確認）"
            ]
        },
        {
            "step": "3. 周辺環境分析",
            "action": "生活利便性と将来性評価",
            "tools": [
                "reinfolib_search_facilities（学校・医療機関調査）",
                "reinfolib_get_geospatial_data（統合情報取得）"
            ]
        },
        {
            "step": "4. リスク評価",
            "action": "災害リスクと安全性確認",
            "tools": [
                "reinfolib_get_disaster_risk（災害危険区域確認）",
                "液状化発生傾向分析"
            ]
        },
        {
            "step": "5. 総合判定",
            "action": "全情報を統合した投資判断",
            "tools": [
                "reinfolib_server_status（システム状態確認）",
                "データ統合・可視化"
            ]
        }
    ]
    
    for workflow in workflow_steps:
        print(f"{workflow['step']}: {workflow['action']}")
        for tool in workflow['tools']:
            print(f"   - {tool}")
        print()


def performance_tips():
    """パフォーマンス最適化のヒント"""
    print("\n=== パフォーマンス最適化のヒント ===")
    
    tips = [
        {
            "category": "APIリクエスト最適化",
            "tips": [
                "必要最小限のデータ範囲を指定",
                "日付範囲を適切に制限",
                "レスポンス形式を用途に応じて選択",
                "非同期クライアントで並行処理を活用"
            ]
        },
        {
            "category": "MCPサーバー運用",
            "tips": [
                "HTTPトランスポートは開発・テスト用",
                "本番環境ではstdioトランスポートを推奨",
                "適切なタイムアウト設定",
                "エラーログの監視"
            ]
        },
        {
            "category": "データ処理効率化",
            "tips": [
                "タイル座標の事前計算",
                "GeoJSONデータのキャッシュ活用",
                "バイナリベクトルタイル（PBF）の利用",
                "データの段階的取得"
            ]
        },
        {
            "category": "統合利用パターン",
            "tips": [
                "複数データソースの組み合わせ",
                "地理空間データの可視化",
                "時系列分析での期間指定最適化",
                "結果データのローカルキャッシュ"
            ]
        }
    ]
    
    for tip_category in tips:
        print(f"【{tip_category['category']}】")
        for tip in tip_category['tips']:
            print(f"  • {tip}")
        print()


def main():
    """メイン実行関数"""
    print("不動産情報ライブラリMCP クライアント使用例")
    print("=" * 60)
    
    # APIキーの確認
    api_key = os.getenv("REINFOLIB_API_KEY")
    if not api_key:
        print("⚠️  環境変数REINFOLIB_API_KEYが設定されていません")
        print("実際の動作確認には APIキーが必要です")
        print()
    
    # 各種例の表示
    simulate_mcp_client_requests()
    claude_desktop_config_example()
    cursor_mcp_config_example()
    uvx_usage_examples()
    integration_workflow_example()
    performance_tips()
    
    print("\n" + "=" * 60)
    print("MCPクライアント使用例の説明が完了しました")
    
    if api_key:
        print("\n実際にMCPサーバーを起動してテストしますか？ (y/n): ", end="")
        try:
            response = input().lower()
            if response == 'y':
                print("MCPサーバーのテスト起動...")
                manager = MCPServerManager(api_key)
                
                if manager.start_server(transport="http", port=8000):
                    print("MCPサーバーが起動しました")
                    print("http://localhost:8000 でアクセス可能です")
                    print("終了するには Ctrl+C を押してください")
                    
                    try:
                        while True:
                            time.sleep(1)
                    except KeyboardInterrupt:
                        print("\n終了します...")
                        manager.stop_server()
                else:
                    print("MCPサーバーの起動に失敗しました")
        except KeyboardInterrupt:
            print("\n中断されました")


if __name__ == "__main__":
    main()

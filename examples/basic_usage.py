#!/usr/bin/env python3
"""
不動産情報ライブラリAPI 基本使用例

このスクリプトは不動産情報ライブラリAPIクライアントの基本的な使用方法を示します。
"""

import asyncio
import os
from typing import List

from reinfolib_mcp import (
    ReinfiolibClient,
    SyncReinfiolibClient,
    ReinfiolibAPIError,
    Language,
    ResponseFormat,
)


async def basic_async_usage():
    """非同期クライアントの基本使用例"""
    print("=== 非同期クライアント使用例 ===")
    
    # APIキーを環境変数から取得
    api_key = os.getenv("REINFOLIB_API_KEY")
    if not api_key:
        print("環境変数REINFOLIB_API_KEYを設定してください")
        return
    
    try:
        # 非同期クライアントを作成（コンテキストマネージャー使用）
        async with ReinfiolibClient(api_key=api_key) as client:
            print(f"APIベースURL: {client.base_url}")
            print(f"利用可能エンドポイント数: {len(client.ENDPOINTS)}")
            
            # 1. 東京都の市区町村一覧を取得
            print("\n--- 東京都の市区町村一覧 ---")
            municipalities = await client.get_municipalities(
                prefecture="13",  # 東京都
                lang=Language.JAPANESE
            )
            
            print(f"市区町村数: {len(municipalities)}")
            for municipality in municipalities[:5]:  # 最初の5つを表示
                print(f"- {municipality.city_code}: {municipality.city_name}")
            
            if len(municipalities) > 5:
                print(f"... 他 {len(municipalities) - 5} 件")
            
            # 2. 東京都千代田区の不動産取引価格を検索
            print("\n--- 東京都千代田区の不動産取引価格 ---")
            transactions = await client.search_real_estate_transactions(
                prefecture="13",       # 東京都
                city="13101",         # 千代田区
                from_date="20230101", # 2023年1月から
                to_date="20231231",   # 2023年12月まで
                property_type="1",    # 宅地
                response_format=ResponseFormat.JSON,
                lang=Language.JAPANESE
            )
            
            print(f"検索結果: {transactions.total_count}件")
            print(f"取得データ: {len(transactions.data)}件")
            
            # 取引データを表示
            for i, transaction in enumerate(transactions.data[:3], 1):
                print(f"\n{i}. {transaction.city} {transaction.district or ''}")
                if transaction.transaction_price:
                    print(f"   価格: {transaction.transaction_price:,}円")
                if transaction.area:
                    print(f"   面積: {transaction.area}㎡")
                if transaction.price_per_unit_area:
                    print(f"   ㎡単価: {transaction.price_per_unit_area:,}円")
                print(f"   取引時期: {transaction.transaction_period or 'N/A'}")
            
            # 3. 地価公示・調査ポイント情報を取得（タイル座標指定）
            print("\n--- 地価公示・調査ポイント情報 ---")
            land_price_data = await client.get_land_price_points(
                z=11,    # ズームレベル
                x=1818,  # タイルX座標（東京駅周辺）
                y=806,   # タイルY座標
                response_format=ResponseFormat.GEOJSON
            )
            
            if land_price_data.get("features"):
                print(f"地価ポイント数: {len(land_price_data['features'])}")
                
                # 最初の地価ポイントの詳細を表示
                first_point = land_price_data['features'][0]
                properties = first_point.get('properties', {})
                coordinates = first_point.get('geometry', {}).get('coordinates', [])
                
                print(f"地点名: {properties.get('point_name', 'N/A')}")
                print(f"住所: {properties.get('address', 'N/A')}")
                if coordinates:
                    print(f"座標: 経度{coordinates[0]}, 緯度{coordinates[1]}")
                if properties.get('price_per_sqm'):
                    print(f"㎡単価: {properties['price_per_sqm']:,}円")
            else:
                print("該当エリアに地価ポイントはありません")
            
    except ReinfiolibAPIError as e:
        print(f"APIエラー: {e}")
        print(f"エラータイプ: {type(e).__name__}")
    except Exception as e:
        print(f"予期しないエラー: {e}")


def basic_sync_usage():
    """同期クライアントの基本使用例"""
    print("\n=== 同期クライアント使用例 ===")
    
    # APIキーを環境変数から取得
    api_key = os.getenv("REINFOLIB_API_KEY")
    if not api_key:
        print("環境変数REINFOLIB_API_KEYを設定してください")
        return
    
    try:
        # 同期クライアントを作成（コンテキストマネージャー使用）
        with SyncReinfiolibClient(api_key=api_key) as client:
            # 大阪府の市区町村一覧を取得
            print("\n--- 大阪府の市区町村一覧 ---")
            municipalities = client.get_municipalities(
                prefecture="27",  # 大阪府
                lang=Language.JAPANESE
            )
            
            print(f"市区町村数: {len(municipalities)}")
            for municipality in municipalities[:10]:  # 最初の10つを表示
                print(f"- {municipality.city_code}: {municipality.city_name}")
            
            # 大阪府の不動産取引価格を検索
            print("\n--- 大阪府の不動産取引価格（中古マンション） ---")
            transactions = client.search_real_estate_transactions(
                prefecture="27",       # 大阪府
                from_date="20230401", # 2023年4月から
                to_date="20230630",   # 2023年6月まで
                property_type="2",    # 中古マンション
                response_format=ResponseFormat.JSON,
                lang=Language.JAPANESE
            )
            
            print(f"検索結果: {transactions.total_count}件")
            
            # 統計情報を計算
            if transactions.data:
                prices = [t.transaction_price for t in transactions.data if t.transaction_price]
                if prices:
                    avg_price = sum(prices) / len(prices)
                    min_price = min(prices)
                    max_price = max(prices)
                    
                    print(f"価格統計:")
                    print(f"  平均価格: {avg_price:,.0f}円")
                    print(f"  最低価格: {min_price:,}円")
                    print(f"  最高価格: {max_price:,}円")
            
    except ReinfiolibAPIError as e:
        print(f"APIエラー: {e}")
    except Exception as e:
        print(f"予期しないエラー: {e}")


async def facility_and_risk_analysis():
    """施設情報と災害リスク情報の分析例"""
    print("\n=== 施設情報と災害リスク分析 ===")
    
    api_key = os.getenv("REINFOLIB_API_KEY")
    if not api_key:
        print("環境変数REINFOLIB_API_KEYを設定してください")
        return
    
    try:
        async with ReinfiolibClient(api_key=api_key) as client:
            # 東京駅周辺の施設と災害リスク情報を取得
            z, x, y = 12, 3636, 1612  # 東京駅周辺のタイル座標
            
            print(f"分析エリア: ズーム{z}, タイル座標({x}, {y})")
            
            # 学校情報を取得
            print("\n--- 周辺学校情報 ---")
            schools = await client.get_schools(
                z=z, x=x, y=y,
                response_format=ResponseFormat.GEOJSON
            )
            
            school_features = schools.get("features", [])
            print(f"学校数: {len(school_features)}")
            
            if school_features:
                for i, school in enumerate(school_features[:3], 1):
                    props = school.get("properties", {})
                    print(f"{i}. {props.get('school_name', 'N/A')}")
                    print(f"   種別: {props.get('school_type', 'N/A')}")
                    print(f"   住所: {props.get('address', 'N/A')}")
            
            # 医療機関情報を取得
            print("\n--- 周辺医療機関 ---")
            medical = await client.get_medical_facilities(
                z=z, x=x, y=y,
                response_format=ResponseFormat.GEOJSON
            )
            
            medical_features = medical.get("features", [])
            print(f"医療機関数: {len(medical_features)}")
            
            if medical_features:
                for i, facility in enumerate(medical_features[:3], 1):
                    props = facility.get("properties", {})
                    print(f"{i}. {props.get('facility_name', 'N/A')}")
                    print(f"   種別: {props.get('facility_type', 'N/A')}")
                    print(f"   住所: {props.get('address', 'N/A')}")
            
            # 災害危険区域情報を取得
            print("\n--- 災害リスク情報 ---")
            disaster_risk = await client.get_disaster_risk_areas(
                z=z, x=x, y=y,
                response_format=ResponseFormat.GEOJSON
            )
            
            disaster_features = disaster_risk.get("features", [])
            print(f"災害危険区域数: {len(disaster_features)}")
            
            if disaster_features:
                for i, area in enumerate(disaster_features[:3], 1):
                    props = area.get("properties", {})
                    print(f"{i}. {props.get('area_name', 'N/A')}")
                    print(f"   災害種別: {props.get('disaster_type', 'N/A')}")
                    print(f"   指定機関: {props.get('authority', 'N/A')}")
            
            # 液状化発生傾向を取得
            print("\n--- 液状化発生傾向 ---")
            liquefaction = await client.get_liquefaction_tendency(
                z=z, x=x, y=y,
                response_format=ResponseFormat.GEOJSON
            )
            
            liquefaction_features = liquefaction.get("features", [])
            print(f"液状化リスクエリア数: {len(liquefaction_features)}")
            
            if liquefaction_features:
                for i, area in enumerate(liquefaction_features[:3], 1):
                    props = area.get("properties", {})
                    print(f"{i}. メッシュコード: {props.get('mesh_code', 'N/A')}")
                    print(f"   微地形区分: {props.get('topographic_classification_name_ja', 'N/A')}")
                    print(f"   液状化発生傾向: {props.get('liquefaction_tendency_level', 'N/A')}")
            
    except ReinfiolibAPIError as e:
        print(f"APIエラー: {e}")
    except Exception as e:
        print(f"予期しないエラー: {e}")


def error_handling_examples():
    """エラーハンドリングの例"""
    print("\n=== エラーハンドリング例 ===")
    
    # 無効なAPIキーでのテスト
    try:
        with SyncReinfiolibClient(api_key="invalid_key") as client:
            municipalities = client.get_municipalities(prefecture="13")
    except ReinfiolibAPIError as e:
        print(f"予期されたAPIエラー: {e}")
        print(f"エラーコード: {e.status_code}")
    
    # APIキー未設定のテスト
    try:
        with SyncReinfiolibClient() as client:
            pass
    except ReinfiolibAPIError as e:
        print(f"設定エラー: {e}")


def main():
    """メイン実行関数"""
    print("不動産情報ライブラリAPI 基本使用例")
    print("=" * 50)
    
    # APIキーの確認
    api_key = os.getenv("REINFOLIB_API_KEY")
    if not api_key:
        print("⚠️  環境変数REINFOLIB_API_KEYが設定されていません")
        print("以下のコマンドでAPIキーを設定してください:")
        print("export REINFOLIB_API_KEY='your_api_key_here'")
        print()
        print("APIキー取得方法:")
        print("https://www.reinfolib.mlit.go.jp/help/apiManual/")
        return
    
    # 非同期例の実行
    asyncio.run(basic_async_usage())
    
    # 同期例の実行
    basic_sync_usage()
    
    # 施設・災害リスク分析例の実行
    asyncio.run(facility_and_risk_analysis())
    
    # エラーハンドリング例の実行
    error_handling_examples()
    
    print("\n" + "=" * 50)
    print("基本使用例の実行が完了しました")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
不動産情報ライブラリAPI 地理空間データ分析例

このスクリプトは不動産情報ライブラリAPIを使用した
地理空間データ分析の高度な使用例を示します。
"""

import asyncio
import math
import os
from dataclasses import dataclass

from reinfolib_mcp import ReinfiolibAPIError, ReinfiolibClient, ResponseFormat


@dataclass
class AnalysisPoint:
    """分析ポイントの座標情報"""
    name: str
    latitude: float
    longitude: float
    description: str = ""


@dataclass
class AreaAnalysisResult:
    """エリア分析結果"""
    point: AnalysisPoint
    tile_coords: tuple[int, int, int]  # (z, x, y)
    real_estate_count: int
    average_price: float | None
    land_price_points: int
    school_count: int
    medical_count: int
    disaster_risk_areas: int
    liquefaction_risk_level: str
    urban_planning_zones: list[str]


class GeospatialAnalyzer:
    """地理空間データ分析クラス"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None

    async def __aenter__(self):
        self.client = ReinfiolibClient(api_key=self.api_key)
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)

    @staticmethod
    def lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
        """緯度経度をタイル座標に変換"""
        n = 2.0 ** zoom
        x = int((lon + 180.0) / 360.0 * n)
        lat_rad = math.radians(lat)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return x, y

    @staticmethod
    def tile_to_lat_lon(x: int, y: int, zoom: int) -> tuple[float, float]:
        """タイル座標を緯度経度に変換"""
        n = 2.0 ** zoom
        lon = x / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        lat = math.degrees(lat_rad)
        return lat, lon

    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """2点間の距離を計算（km）"""
        r = 6371  # 地球の半径（km）

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return r * c

    async def analyze_area(self, point: AnalysisPoint, zoom: int = 12) -> AreaAnalysisResult:
        """指定地点の包括的エリア分析"""
        print(f"\n分析開始: {point.name} ({point.latitude}, {point.longitude})")

        # タイル座標計算
        tile_x, tile_y = self.lat_lon_to_tile(point.latitude, point.longitude, zoom)
        print(f"タイル座標: ズーム{zoom}, X={tile_x}, Y={tile_y}")

        result = AreaAnalysisResult(
            point=point,
            tile_coords=(zoom, tile_x, tile_y),
            real_estate_count=0,
            average_price=None,
            land_price_points=0,
            school_count=0,
            medical_count=0,
            disaster_risk_areas=0,
            liquefaction_risk_level="不明",
            urban_planning_zones=[]
        )

        try:
            # 1. 不動産取引価格分析
            await self._analyze_real_estate_prices(result, point)

            # 2. 地価公示・調査分析
            await self._analyze_land_prices(result, zoom, tile_x, tile_y)

            # 3. 施設情報分析
            await self._analyze_facilities(result, zoom, tile_x, tile_y)

            # 4. 都市計画情報分析
            await self._analyze_urban_planning(result, zoom, tile_x, tile_y)

            # 5. 災害リスク分析
            await self._analyze_disaster_risks(result, zoom, tile_x, tile_y)

        except Exception as e:
            print(f"分析エラー: {e}")

        return result

    async def _analyze_real_estate_prices(self, result: AreaAnalysisResult, point: AnalysisPoint):
        """不動産価格分析"""
        try:
            # 都道府県コードを座標から推定（簡易実装）
            prefecture_code = self._estimate_prefecture_code(point.latitude, point.longitude)

            if prefecture_code:
                transactions = await self.client.search_real_estate_transactions(
                    prefecture=prefecture_code,
                    from_date="20230101",
                    to_date="20231231",
                    response_format=ResponseFormat.JSON
                )

                result.real_estate_count = transactions.total_count

                # 価格統計計算
                prices = [t.transaction_price for t in transactions.data
                         if t.transaction_price and t.longitude and t.latitude]

                if prices:
                    # 指定地点から1km以内の取引のみを対象
                    nearby_prices = []
                    for t in transactions.data:
                        if (t.transaction_price and t.longitude and t.latitude):
                            distance = self.calculate_distance(
                                point.latitude, point.longitude,
                                t.latitude, t.longitude
                            )
                            if distance <= 1.0:  # 1km以内
                                nearby_prices.append(t.transaction_price)

                    if nearby_prices:
                        result.average_price = sum(nearby_prices) / len(nearby_prices)
                        print(f"  不動産取引: {result.real_estate_count}件, 1km以内平均価格: {result.average_price:,.0f}円")
                    else:
                        print(f"  不動産取引: {result.real_estate_count}件, 1km以内の取引なし")
                else:
                    print(f"  不動産取引: {result.real_estate_count}件, 価格情報なし")

        except Exception as e:
            print(f"  不動産価格分析エラー: {e}")

    async def _analyze_land_prices(self, result: AreaAnalysisResult, z: int, x: int, y: int):
        """地価分析"""
        try:
            land_price_data = await self.client.get_land_price_points(
                z=z, x=x, y=y,
                response_format=ResponseFormat.GEOJSON
            )

            features = land_price_data.get("features", [])
            result.land_price_points = len(features)

            if features:
                prices = [f.get("properties", {}).get("price_per_sqm")
                         for f in features
                         if f.get("properties", {}).get("price_per_sqm")]

                if prices:
                    avg_land_price = sum(prices) / len(prices)
                    print(f"  地価ポイント: {result.land_price_points}件, 平均㎡単価: {avg_land_price:,.0f}円")
                else:
                    print(f"  地価ポイント: {result.land_price_points}件, 価格情報なし")
            else:
                print("  地価ポイント: なし")

        except Exception as e:
            print(f"  地価分析エラー: {e}")

    async def _analyze_facilities(self, result: AreaAnalysisResult, z: int, x: int, y: int):
        """施設情報分析"""
        try:
            # 学校情報
            schools = await self.client.get_schools(
                z=z, x=x, y=y,
                response_format=ResponseFormat.GEOJSON
            )
            result.school_count = len(schools.get("features", []))

            # 医療機関情報
            medical = await self.client.get_medical_facilities(
                z=z, x=x, y=y,
                response_format=ResponseFormat.GEOJSON
            )
            result.medical_count = len(medical.get("features", []))

            print(f"  周辺施設: 学校{result.school_count}件, 医療機関{result.medical_count}件")

        except Exception as e:
            print(f"  施設分析エラー: {e}")

    async def _analyze_urban_planning(self, result: AreaAnalysisResult, z: int, x: int, y: int):
        """都市計画分析"""
        try:
            # 用途地域情報
            zones = await self.client.get_land_use_zones(
                z=z, x=x, y=y,
                response_format=ResponseFormat.GEOJSON
            )

            zone_features = zones.get("features", [])
            zone_types = set()

            for feature in zone_features:
                zone_type = feature.get("properties", {}).get("zone_type")
                if zone_type:
                    zone_types.add(zone_type)

            result.urban_planning_zones = list(zone_types)
            print(f"  用途地域: {len(result.urban_planning_zones)}種類 - {', '.join(result.urban_planning_zones) if result.urban_planning_zones else 'なし'}")

        except Exception as e:
            print(f"  都市計画分析エラー: {e}")

    async def _analyze_disaster_risks(self, result: AreaAnalysisResult, z: int, x: int, y: int):
        """災害リスク分析"""
        try:
            # 災害危険区域
            disaster_areas = await self.client.get_disaster_risk_areas(
                z=z, x=x, y=y,
                response_format=ResponseFormat.GEOJSON
            )
            result.disaster_risk_areas = len(disaster_areas.get("features", []))

            # 液状化発生傾向
            liquefaction = await self.client.get_liquefaction_tendency(
                z=z, x=x, y=y,
                response_format=ResponseFormat.GEOJSON
            )

            liquefaction_features = liquefaction.get("features", [])
            if liquefaction_features:
                # 最初の特徴から液状化リスクレベルを取得
                first_feature = liquefaction_features[0]
                risk_level = first_feature.get("properties", {}).get("liquefaction_tendency_level", "不明")
                result.liquefaction_risk_level = str(risk_level)

            print(f"  災害リスク: 危険区域{result.disaster_risk_areas}件, 液状化リスク: {result.liquefaction_risk_level}")

        except Exception as e:
            print(f"  災害リスク分析エラー: {e}")

    def _estimate_prefecture_code(self, lat: float, lon: float) -> str | None:
        """座標から都道府県コードを推定（簡易実装）"""
        # 主要都市の座標範囲による簡易判定
        if 35.5 <= lat <= 35.9 and 139.3 <= lon <= 139.9:
            return "13"  # 東京都
        elif 34.6 <= lat <= 34.8 and 135.3 <= lon <= 135.7:
            return "27"  # 大阪府
        elif 35.0 <= lat <= 35.3 and 139.5 <= lon <= 139.8:
            return "14"  # 神奈川県
        elif 35.1 <= lat <= 35.4 and 136.8 <= lon <= 137.0:
            return "23"  # 愛知県
        else:
            return None  # 判定不可

    async def compare_areas(self, points: list[AnalysisPoint]) -> list[AreaAnalysisResult]:
        """複数エリアの比較分析"""
        print("=== 複数エリア比較分析 ===")

        results = []
        for point in points:
            result = await self.analyze_area(point)
            results.append(result)

        return results

    def generate_analysis_report(self, results: list[AreaAnalysisResult]) -> str:
        """分析レポート生成"""
        report = "# 地理空間データ分析レポート\n\n"

        # 個別エリア分析結果
        report += "## 個別エリア分析結果\n\n"
        for i, result in enumerate(results, 1):
            report += f"### {i}. {result.point.name}\n\n"
            report += f"- **座標**: 緯度{result.point.latitude}, 経度{result.point.longitude}\n"
            report += f"- **タイル座標**: ズーム{result.tile_coords[0]}, X={result.tile_coords[1]}, Y={result.tile_coords[2]}\n"
            report += f"- **不動産取引件数**: {result.real_estate_count}件\n"

            if result.average_price:
                report += f"- **平均取引価格**: {result.average_price:,.0f}円\n"
            else:
                report += "- **平均取引価格**: データなし\n"

            report += f"- **地価ポイント数**: {result.land_price_points}件\n"
            report += f"- **周辺学校数**: {result.school_count}件\n"
            report += f"- **周辺医療機関数**: {result.medical_count}件\n"
            report += f"- **災害危険区域数**: {result.disaster_risk_areas}件\n"
            report += f"- **液状化リスク**: {result.liquefaction_risk_level}\n"

            if result.urban_planning_zones:
                report += f"- **用途地域**: {', '.join(result.urban_planning_zones)}\n"
            else:
                report += "- **用途地域**: データなし\n"

            report += f"\n{result.point.description}\n\n"

        # 比較分析
        if len(results) > 1:
            report += "## 比較分析\n\n"

            # 価格比較
            price_results = [(r.point.name, r.average_price) for r in results if r.average_price]
            if price_results:
                price_results.sort(key=lambda x: x[1], reverse=True)
                report += "### 平均価格ランキング\n\n"
                for i, (name, price) in enumerate(price_results, 1):
                    report += f"{i}. {name}: {price:,.0f}円\n"
                report += "\n"

            # 利便性比較
            report += "### 生活利便性スコア\n\n"
            for result in results:
                convenience_score = result.school_count + result.medical_count
                report += f"- {result.point.name}: {convenience_score}点 (学校{result.school_count} + 医療{result.medical_count})\n"
            report += "\n"

            # 安全性比較
            report += "### 安全性評価\n\n"
            for result in results:
                safety_score = max(0, 10 - result.disaster_risk_areas)
                report += f"- {result.point.name}: {safety_score}/10点 (災害危険区域: {result.disaster_risk_areas}件)\n"
            report += "\n"

        report += "---\n"
        report += f"*分析日時: {import_time_datetime().now().strftime('%Y-%m-%d %H:%M:%S')}*\n"

        return report


def import_time_datetime():
    """datetime モジュールの動的インポート"""
    import datetime
    return datetime


async def tokyo_station_area_analysis():
    """東京駅周辺エリア分析例"""
    print("=== 東京駅周辺エリア分析 ===")

    api_key = os.getenv("REINFOLIB_API_KEY")
    if not api_key:
        print("環境変数REINFOLIB_API_KEYが設定されていません")
        return

    # 分析対象地点の定義
    analysis_points = [
        AnalysisPoint(
            name="東京駅",
            latitude=35.6812,
            longitude=139.7671,
            description="東京の中心部、ビジネス・商業の中心地"
        ),
        AnalysisPoint(
            name="品川駅",
            latitude=35.6284,
            longitude=139.7387,
            description="交通の要衝、リニア新幹線の起点予定地"
        ),
        AnalysisPoint(
            name="新宿駅",
            latitude=35.6896,
            longitude=139.7006,
            description="世界最大の乗降客数を誇るターミナル駅"
        ),
        AnalysisPoint(
            name="渋谷駅",
            latitude=35.6580,
            longitude=139.7016,
            description="若者文化の発信地、IT企業の集積地"
        )
    ]

    try:
        async with GeospatialAnalyzer(api_key) as analyzer:
            # 複数エリアの比較分析実行
            results = await analyzer.compare_areas(analysis_points)

            # 分析レポート生成
            report = analyzer.generate_analysis_report(results)

            # レポート表示
            print("\n" + "=" * 60)
            print(report)

            # レポートをファイルに保存
            with open("geospatial_analysis_report.md", "w", encoding="utf-8") as f:
                f.write(report)
            print("分析レポートを 'geospatial_analysis_report.md' に保存しました")

    except ReinfiolibAPIError as e:
        print(f"API エラー: {e}")
    except Exception as e:
        print(f"分析エラー: {e}")


async def real_estate_investment_analysis():
    """不動産投資分析例"""
    print("\n=== 不動産投資分析例 ===")

    api_key = os.getenv("REINFOLIB_API_KEY")
    if not api_key:
        print("環境変数REINFOLIB_API_KEYが設定されていません")
        return

    # 投資候補地点
    investment_candidates = [
        AnalysisPoint(
            name="武蔵小杉駅周辺",
            latitude=35.5781,
            longitude=139.6575,
            description="再開発が進む新興住宅地、タワーマンション群"
        ),
        AnalysisPoint(
            name="吉祥寺駅周辺",
            latitude=35.7022,
            longitude=139.5803,
            description="住みたい街ランキング上位の人気エリア"
        ),
        AnalysisPoint(
            name="二子玉川駅周辺",
            latitude=35.6119,
            longitude=139.6331,
            description="高級住宅地、ファミリー層に人気"
        )
    ]

    try:
        async with GeospatialAnalyzer(api_key) as analyzer:
            print("不動産投資候補地の分析を実行中...")

            investment_results = []
            for candidate in investment_candidates:
                result = await analyzer.analyze_area(candidate, zoom=13)

                # 投資スコア計算（簡易）
                investment_score = 0

                # 価格適正性（平均価格が一定範囲内）
                if result.average_price:
                    if 30000000 <= result.average_price <= 80000000:  # 3000万〜8000万円
                        investment_score += 25

                # 利便性（学校・医療機関の充実度）
                convenience = result.school_count + result.medical_count
                investment_score += min(convenience * 2, 25)  # 最大25点

                # 安全性（災害リスクの低さ）
                safety = max(0, 25 - result.disaster_risk_areas * 5)
                investment_score += safety

                # 地価安定性（地価ポイントの存在）
                if result.land_price_points > 0:
                    investment_score += 25

                investment_results.append((candidate.name, investment_score, result))
                print(f"{candidate.name}: 投資スコア {investment_score}/100点")

            # 投資ランキング
            investment_results.sort(key=lambda x: x[1], reverse=True)

            print("\n--- 投資候補地ランキング ---")
            for i, (name, score, result) in enumerate(investment_results, 1):
                print(f"{i}位: {name} (スコア: {score}/100点)")
                print(f"     平均価格: {result.average_price:,.0f}円" if result.average_price else "     平均価格: データなし")
                print(f"     利便性: 学校{result.school_count}件, 医療{result.medical_count}件")
                print(f"     安全性: 災害リスク{result.disaster_risk_areas}件")
                print()

    except Exception as e:
        print(f"投資分析エラー: {e}")


def main():
    """メイン実行関数"""
    print("不動産情報ライブラリAPI 地理空間データ分析例")
    print("=" * 60)

    # APIキーの確認
    api_key = os.getenv("REINFOLIB_API_KEY")
    if not api_key:
        print("⚠️  環境変数REINFOLIB_API_KEYが設定されていません")
        print("以下のコマンドでAPIキーを設定してください:")
        print("export REINFOLIB_API_KEY='your_api_key_here'")
        return

    print("分析を開始します...")

    # 分析例の実行
    asyncio.run(tokyo_station_area_analysis())
    asyncio.run(real_estate_investment_analysis())

    print("\n" + "=" * 60)
    print("地理空間データ分析が完了しました")


if __name__ == "__main__":
    main()

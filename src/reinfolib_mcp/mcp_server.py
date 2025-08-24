"""
不動産情報ライブラリMCPサーバー実装

FastMCPライブラリを使用して不動産情報ライブラリAPIをMCPツールとして提供
"""

import json
import os
from typing import Any, Dict, List, Optional, Union

from fastmcp import FastMCP

from .client import ReinfiolibClient
from .exceptions import ReinfiolibAPIError
from .models import Language, ResponseFormat


def create_mcp_server(api_key: Optional[str] = None) -> FastMCP:
    """
    不動産情報ライブラリMCPサーバーを作成します

    Args:
        api_key: APIキー（Noneの場合は環境変数から取得）

    Returns:
        FastMCP: 設定済みのMCPサーバー
    """
    # MCPサーバー初期化
    mcp = FastMCP("不動産情報ライブラリMCP")

    # APIクライアント初期化
    try:
        client = ReinfiolibClient(api_key=api_key)
    except ReinfiolibAPIError as e:
        raise RuntimeError(f"MCPサーバー初期化失敗: {e}")

    # === 不動産価格情報ツール ===

    @mcp.tool(
        name="reinfolib_search_real_estate",
        description="不動産取引価格情報を検索します。都道府県や市区町村、期間を指定して取引データを取得できます。",
        tags={"real-estate", "price", "transaction"}
    )
    async def search_real_estate_transactions(
        prefecture: str,
        city: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        property_type: Optional[str] = None,
        language: str = "ja"
    ) -> Dict[str, Any]:
        """
        不動産取引価格情報を検索します。
        
        Args:
            prefecture: 都道府県コード（01-47）例：東京都=13、大阪府=27
            city: 市区町村コード（オプション）例：千代田区=13101
            from_date: 取引時期開始（YYYYMMDD形式）例：20230101
            to_date: 取引時期終了（YYYYMMDD形式）例：20231231
            property_type: 不動産種別（1:宅地、2:中古マンション等、3:中古戸建住宅）
            language: 言語（ja:日本語、en:英語）
            
        Returns:
            不動産取引データ（最大100件）
        """
        try:
            lang = Language.ENGLISH if language == "en" else Language.JAPANESE
            
            result = await client.search_real_estate_transactions(
                prefecture=prefecture,
                city=city,
                from_date=from_date,
                to_date=to_date,
                property_type=property_type,
                response_format=ResponseFormat.JSON,
                lang=lang
            )
            
            # Pydanticモデルの場合は辞書に変換
            if hasattr(result, 'dict'):
                return result.dict()
            
            return result
            
        except ReinfiolibAPIError as e:
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "total_count": 0,
                "data": []
            }

    @mcp.tool(
        name="reinfolib_get_municipalities",
        description="指定都道府県の市区町村一覧を取得します。都道府県コードから配下の全市区町村情報を取得できます。",
        tags={"administrative", "municipalities"}
    )
    async def get_municipalities(
        prefecture: str,
        language: str = "ja"
    ) -> Dict[str, Any]:
        """
        指定都道府県の市区町村一覧を取得します。
        
        Args:
            prefecture: 都道府県コード（01-47）例：東京都=13、京都府=26
            language: 言語（ja:日本語、en:英語）
            
        Returns:
            市区町村情報のリスト
        """
        try:
            lang = Language.ENGLISH if language == "en" else Language.JAPANESE
            
            municipalities = await client.get_municipalities(
                prefecture=prefecture,
                lang=lang
            )
            
            return {
                "total_count": len(municipalities),
                "data": [m.dict() for m in municipalities]
            }
            
        except ReinfiolibAPIError as e:
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "total_count": 0,
                "data": []
            }

    # === 地価情報ツール ===

    @mcp.tool(
        name="reinfolib_get_land_price",
        description="地価公示・地価調査のポイント情報を取得します。指定座標周辺の地価情報をGeoJSON形式で取得できます。",
        tags={"land-price", "geospatial"}
    )
    async def get_land_price_points(
        zoom_level: int,
        tile_x: int,
        tile_y: int,
        response_format: str = "geojson"
    ) -> Dict[str, Any]:
        """
        地価公示・地価調査のポイント情報を取得します。
        
        Args:
            zoom_level: ズームレベル（1-18）
            tile_x: タイルX座標
            tile_y: タイルY座標  
            response_format: レスポンス形式（geojson、pbf）
            
        Returns:
            地価ポイント情報（GeoJSON形式）
        """
        try:
            format_enum = ResponseFormat.PBF if response_format == "pbf" else ResponseFormat.GEOJSON
            
            result = await client.get_land_price_points(
                z=zoom_level,
                x=tile_x,
                y=tile_y,
                response_format=format_enum
            )
            
            return result
            
        except ReinfiolibAPIError as e:
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "type": "FeatureCollection",
                "features": []
            }

    # === 都市計画情報ツール ===

    @mcp.tool(
        name="reinfolib_get_urban_planning",
        description="都市計画区域・用途地域などの都市計画情報を取得します。指定エリアの都市計画制限情報を確認できます。",
        tags={"urban-planning", "zoning", "geospatial"}
    )
    async def get_urban_planning_info(
        zoom_level: int,
        tile_x: int,
        tile_y: int,
        info_type: str = "area",
        response_format: str = "geojson"
    ) -> Dict[str, Any]:
        """
        都市計画情報を取得します。
        
        Args:
            zoom_level: ズームレベル（1-18）
            tile_x: タイルX座標
            tile_y: タイルY座標
            info_type: 情報種別（area:都市計画区域、zones:用途地域）
            response_format: レスポンス形式（geojson、pbf）
            
        Returns:
            都市計画情報（GeoJSON形式）
        """
        try:
            format_enum = ResponseFormat.PBF if response_format == "pbf" else ResponseFormat.GEOJSON
            
            if info_type == "zones":
                result = await client.get_land_use_zones(
                    z=zoom_level,
                    x=tile_x,
                    y=tile_y,
                    response_format=format_enum
                )
            else:  # デフォルトは都市計画区域
                result = await client.get_urban_planning_area(
                    z=zoom_level,
                    x=tile_x,
                    y=tile_y,
                    response_format=format_enum
                )
            
            return result
            
        except ReinfiolibAPIError as e:
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "type": "FeatureCollection",
                "features": []
            }

    # === 施設情報ツール ===

    @mcp.tool(
        name="reinfolib_search_facilities",
        description="周辺施設情報を検索します。学校、医療機関、図書館などの施設情報を地図データで取得できます。",
        tags={"facilities", "schools", "medical", "geospatial"}
    )
    async def search_facilities(
        zoom_level: int,
        tile_x: int,
        tile_y: int,
        facility_type: str = "schools",
        response_format: str = "geojson"
    ) -> Dict[str, Any]:
        """
        周辺施設情報を検索します。
        
        Args:
            zoom_level: ズームレベル（1-18）
            tile_x: タイルX座標
            tile_y: タイルY座標
            facility_type: 施設種別（schools:学校、medical:医療機関）
            response_format: レスポンス形式（geojson、pbf）
            
        Returns:
            施設情報（GeoJSON形式）
        """
        try:
            format_enum = ResponseFormat.PBF if response_format == "pbf" else ResponseFormat.GEOJSON
            
            if facility_type == "medical":
                result = await client.get_medical_facilities(
                    z=zoom_level,
                    x=tile_x,
                    y=tile_y,
                    response_format=format_enum
                )
            else:  # デフォルトは学校
                result = await client.get_schools(
                    z=zoom_level,
                    x=tile_x,
                    y=tile_y,
                    response_format=format_enum
                )
            
            return result
            
        except ReinfiolibAPIError as e:
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "type": "FeatureCollection",
                "features": []
            }

    # === 災害リスク情報ツール ===

    @mcp.tool(
        name="reinfolib_get_disaster_risk",
        description="災害リスク情報を取得します。災害危険区域、液状化発生傾向など防災関連情報を確認できます。",
        tags={"disaster", "risk", "safety", "geospatial"}
    )
    async def get_disaster_risk_info(
        zoom_level: int,
        tile_x: int,
        tile_y: int,
        risk_type: str = "disaster_areas",
        response_format: str = "geojson"
    ) -> Dict[str, Any]:
        """
        災害リスク情報を取得します。
        
        Args:
            zoom_level: ズームレベル（1-18）
            tile_x: タイルX座標
            tile_y: タイルY座標
            risk_type: リスク種別（disaster_areas:災害危険区域、liquefaction:液状化発生傾向）
            response_format: レスポンス形式（geojson、pbf）
            
        Returns:
            災害リスク情報（GeoJSON形式）
        """
        try:
            format_enum = ResponseFormat.PBF if response_format == "pbf" else ResponseFormat.GEOJSON
            
            if risk_type == "liquefaction":
                result = await client.get_liquefaction_tendency(
                    z=zoom_level,
                    x=tile_x,
                    y=tile_y,
                    response_format=format_enum
                )
            else:  # デフォルトは災害危険区域
                result = await client.get_disaster_risk_areas(
                    z=zoom_level,
                    x=tile_x,
                    y=tile_y,
                    response_format=format_enum
                )
            
            return result
            
        except ReinfiolibAPIError as e:
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "type": "FeatureCollection",
                "features": []
            }

    # === 汎用地理データ取得ツール ===

    @mcp.tool(
        name="reinfolib_get_geospatial_data",
        description="指定座標周辺の地理空間データを取得します。緯度経度からタイル座標を計算して各種GISデータを取得できます。",
        tags={"geospatial", "coordinates", "tiles"}
    )
    async def get_geospatial_data(
        latitude: float,
        longitude: float,
        zoom_level: int = 12,
        data_types: List[str] = ["land_price", "urban_planning", "facilities"],
        response_format: str = "geojson"
    ) -> Dict[str, Any]:
        """
        緯度経度を指定して周辺の地理空間データを取得します。
        
        Args:
            latitude: 緯度（-90.0 〜 90.0）
            longitude: 経度（-180.0 〜 180.0）
            zoom_level: ズームレベル（1-18）
            data_types: 取得データ種別のリスト（land_price、urban_planning、facilities、disaster_risk）
            response_format: レスポンス形式（geojson、pbf）
            
        Returns:
            統合地理空間データ
        """
        try:
            # 緯度経度からタイル座標を計算
            import math
            
            # Web Mercator投影でのタイル座標計算
            n = 2.0 ** zoom_level
            tile_x = int((longitude + 180.0) / 360.0 * n)
            lat_rad = math.radians(latitude)
            tile_y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
            
            results = {
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "zoom_level": zoom_level,
                    "tile_x": tile_x,
                    "tile_y": tile_y
                },
                "data": {}
            }
            
            format_enum = ResponseFormat.PBF if response_format == "pbf" else ResponseFormat.GEOJSON
            
            # 各データ種別を順次取得
            for data_type in data_types:
                try:
                    if data_type == "land_price":
                        data = await client.get_land_price_points(
                            z=zoom_level, x=tile_x, y=tile_y, response_format=format_enum
                        )
                        results["data"]["land_price"] = data
                        
                    elif data_type == "urban_planning":
                        area_data = await client.get_urban_planning_area(
                            z=zoom_level, x=tile_x, y=tile_y, response_format=format_enum
                        )
                        zone_data = await client.get_land_use_zones(
                            z=zoom_level, x=tile_x, y=tile_y, response_format=format_enum
                        )
                        results["data"]["urban_planning"] = {
                            "area": area_data,
                            "zones": zone_data
                        }
                        
                    elif data_type == "facilities":
                        schools_data = await client.get_schools(
                            z=zoom_level, x=tile_x, y=tile_y, response_format=format_enum
                        )
                        medical_data = await client.get_medical_facilities(
                            z=zoom_level, x=tile_x, y=tile_y, response_format=format_enum
                        )
                        results["data"]["facilities"] = {
                            "schools": schools_data,
                            "medical": medical_data
                        }
                        
                    elif data_type == "disaster_risk":
                        disaster_data = await client.get_disaster_risk_areas(
                            z=zoom_level, x=tile_x, y=tile_y, response_format=format_enum
                        )
                        liquefaction_data = await client.get_liquefaction_tendency(
                            z=zoom_level, x=tile_x, y=tile_y, response_format=format_enum
                        )
                        results["data"]["disaster_risk"] = {
                            "disaster_areas": disaster_data,
                            "liquefaction": liquefaction_data
                        }
                        
                except ReinfiolibAPIError as e:
                    results["data"][data_type] = {
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
            
            return results
            
        except Exception as e:
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                }
            }

    # サーバークリーンアップ処理登録
    @mcp.tool(
        name="reinfolib_server_status",
        description="MCPサーバーの状態を確認します。接続状況やAPIキー設定状況を確認できます。",
        tags={"server", "status", "health"}
    )
    async def get_server_status() -> Dict[str, Any]:
        """
        MCPサーバーの状態を確認します。
        
        Returns:
            サーバー状態情報
        """
        return {
            "server_name": "不動産情報ライブラリMCP",
            "version": "0.1.0",
            "api_key_configured": bool(client.api_key),
            "base_url": client.base_url,
            "available_endpoints": len(client.ENDPOINTS),
            "endpoints": list(client.ENDPOINTS.keys()),
            "status": "healthy"
        }

    return mcp


def run_server(
    api_key: Optional[str] = None,
    transport: str = "stdio",
    host: str = "localhost",
    port: int = 8000
) -> None:
    """
    MCPサーバーを起動します

    Args:
        api_key: APIキー
        transport: トランスポート方式（stdio、http、sse）
        host: HTTPホスト名
        port: HTTPポート番号
    """
    # APIキーの取得
    if not api_key:
        api_key = os.getenv("REINFOLIB_API_KEY")
    
    if not api_key:
        print("エラー: APIキーが設定されていません")
        print("環境変数REINFOLIB_API_KEYを設定するか、--api-keyオプションで指定してください")
        return

    try:
        # MCPサーバー作成と起動
        mcp = create_mcp_server(api_key)
        
        print(f"不動産情報ライブラリMCPサーバーを起動中...")
        print(f"トランスポート: {transport}")
        
        if transport == "stdio":
            mcp.run(transport="stdio")
        elif transport == "http":
            print(f"HTTPサーバー: http://{host}:{port}")
            mcp.run(transport="http", host=host, port=port)
        elif transport == "sse":
            print(f"SSEサーバー: http://{host}:{port}")
            mcp.run(transport="sse", host=host, port=port)
        else:
            raise ValueError(f"未対応のトランスポート: {transport}")
            
    except Exception as e:
        print(f"サーバー起動エラー: {e}")
        raise


if __name__ == "__main__":
    run_server()

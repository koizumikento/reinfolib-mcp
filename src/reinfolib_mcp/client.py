"""
不動産情報ライブラリAPIクライアント実装

国土交通省の不動産情報ライブラリAPIにアクセスするためのクライアントライブラリ
公式API仕様: https://www.reinfolib.mlit.go.jp/help/apiManual/
"""

import asyncio
import os
from typing import Any
from urllib.parse import urljoin

import httpx
from asyncio_throttle import Throttler

from .exceptions import (
    AuthenticationError,
    DataFormatError,
    InvalidParameterError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ReinfiolibAPIError,
    ServerError,
    TimeoutError,
)
from .models import (
    Language,
    Municipality,
    RealEstateSearchResult,
    ResponseFormat,
    TileCoordinates,
)


class ReinfiolibClient:
    """
    不動産情報ライブラリAPI非同期クライアント

    公式API仕様に基づく30種類のAPIエンドポイントをサポート
    """

    # APIエンドポイント定義（公式マニュアルに準拠）
    ENDPOINTS = {
        # 不動産価格情報系
        "real_estate_transactions": "/XIT001",      # 不動産価格（取引価格・成約価格）情報取得API
        "municipalities": "/XIT002",                # 都道府県内市区町村一覧取得API
        "appraisal_info": "/XIT003",               # 鑑定評価書情報API
        "real_estate_points": "/XIT004",           # 不動産価格情報のポイント (点) API
        "land_price_points": "/XIT005",            # 地価公示・地価調査のポイント（点）API

        # 都市計画決定GISデータ系
        "urban_planning_area": "/XKT001",          # 都市計画区域/区域区分
        "land_use_zones": "/XKT002",               # 用途地域
        "location_optimization_plan": "/XKT003",   # 立地適正化計画
        "fire_prevention_areas": "/XKT004",        # 防火・準防火地域
        "district_plan": "/XKT005",                # 地区計画
        "intensive_use_district": "/XKT006",       # 高度利用地区

        # 国土数値情報系（教育・文化施設）
        "elementary_school_districts": "/XKT007",  # 小学校区
        "junior_high_school_districts": "/XKT008", # 中学校区
        "schools": "/XKT009",                      # 学校
        "kindergartens": "/XKT010",                # 保育園・幼稚園等
        "libraries": "/XKT022",                    # 図書館

        # 国土数値情報系（医療・福祉施設）
        "medical_facilities": "/XKT011",           # 医療機関
        "welfare_facilities": "/XKT012",           # 福祉施設

        # 国土数値情報系（交通インフラ）
        "station_passenger_data": "/XKT020",       # 駅別乗降客数

        # 国土数値情報系（人口・統計）
        "population_mesh": "/XKT013",              # 将来推計人口250mメッシュ

        # 国土数値情報系（公共・行政施設）
        "municipal_facilities": "/XKT023",         # 市区町村役場及び集会施設等

        # 国土数値情報系（災害・防災情報）
        "disaster_risk_areas": "/XKT021",          # 災害危険区域
        "large_scale_fill": "/XKT025",             # 大規模盛土造成地マップ
        "landslide_prevention": "/XKT026",         # 地すべり防止地区
        "steep_slope_collapse": "/XKT027",         # 急傾斜地崩壊危険区域
        "liquefaction_tendency": "/XKT028",        # 地形区分に基づく液状化の発生傾向図

        # 国土数値情報系（自然・環境）
        "natural_parks": "/XKT024",                # 自然公園地域
    }

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://www.reinfolib.mlit.go.jp/ex-api/external",
        timeout: float = 30.0,
        max_retries: int = 3,
        rate_limit_per_minute: int = 60,
    ) -> None:
        """
        クライアントを初期化します。

        Args:
            api_key: APIキー（Noneの場合は環境変数REINFOLIB_API_KEYを使用）
            base_url: APIベースURL
            timeout: リクエストタイムアウト（秒）
            max_retries: 最大リトライ回数
            rate_limit_per_minute: 1分間あたりのリクエスト制限数

        Raises:
            ConfigurationError: APIキーが設定されていない場合
        """
        self.api_key = api_key or os.getenv("REINFOLIB_API_KEY")
        if not self.api_key:
            raise ReinfiolibAPIError(
                "APIキーが設定されていません。引数で指定するか、環境変数REINFOLIB_API_KEYを設定してください。"
            )

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        # HTTPクライアント設定
        self._client = httpx.AsyncClient(
            headers={
                "Ocp-Apim-Subscription-Key": self.api_key,
                "User-Agent": "reinfolib-mcp/0.1.0",
            },
            timeout=httpx.Timeout(timeout),
        )

        # レート制限設定
        self._throttler = Throttler(rate_limit=rate_limit_per_minute, period=60.0)

    async def __aenter__(self) -> "ReinfiolibClient":
        """非同期コンテキストマネージャー開始"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """非同期コンテキストマネージャー終了"""
        await self.close()

    async def close(self) -> None:
        """クライアントを閉じます"""
        await self._client.aclose()

    async def _make_request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        retries: int = 0,
    ) -> dict[str, Any]:
        """
        APIリクエストを実行します（内部メソッド）

        Args:
            endpoint: APIエンドポイント
            params: リクエストパラメータ
            retries: 現在のリトライ回数

        Returns:
            Dict[str, Any]: APIレスポンス

        Raises:
            ReinfiolibAPIError: APIエラーが発生した場合
        """
        # レート制限適用
        async with self._throttler:
            try:
                url = urljoin(self.base_url, endpoint)
                response = await self._client.get(url, params=params)

                # ステータスコード別エラーハンドリング
                if response.status_code == 200:
                    try:
                        return response.json()
                    except Exception as e:
                        # バイナリレスポンス（PBF）の場合
                        if params and params.get("response_format") == "pbf":
                            return {"data": response.content, "format": "pbf"}
                        raise DataFormatError(f"レスポンスのパース失敗: {e}") from e

                elif response.status_code == 401:
                    raise AuthenticationError("APIキーが無効です")

                elif response.status_code == 400:
                    raise InvalidParameterError("リクエストパラメータが不正です")

                elif response.status_code == 404:
                    raise NotFoundError("指定されたリソースが見つかりません")

                elif response.status_code == 429:
                    raise RateLimitError("レート制限に達しました")

                elif response.status_code >= 500:
                    raise ServerError(f"サーバーエラー: {response.status_code}")

                else:
                    raise ReinfiolibAPIError(
                        f"APIエラー: {response.status_code}",
                        status_code=response.status_code
                    )

            except httpx.ConnectError as e:
                raise NetworkError(f"接続エラー: {e}") from e

            except httpx.TimeoutException as e:
                if retries < self.max_retries:
                    await asyncio.sleep(2 ** retries)  # Exponential backoff
                    return await self._make_request(endpoint, params, retries + 1)
                raise TimeoutError(f"リクエストタイムアウト: {e}") from e

            except Exception as e:
                raise ReinfiolibAPIError(f"予期しないエラー: {e}") from e

    # === 不動産価格情報API ===

    async def get_appraisal_info(
        self,
        prefecture: str | None = None,
        city: str | None = None,
        response_format: ResponseFormat = ResponseFormat.JSON,
        lang: Language = Language.JAPANESE,
    ) -> dict[str, Any]:
        """
        鑑定評価書情報を取得します（XIT003）

        Args:
            prefecture: 都道府県コード（01-47）
            city: 市区町村コード
            response_format: レスポンス形式
            lang: 言語（日本語/英語）

        Returns:
            Dict[str, Any]: 鑑定評価書情報
        """
        params = {
            "response_format": response_format.value,
            "lang": lang.value,
        }

        # オプションパラメータ追加
        for key, value in {
            "prefecture": prefecture,
            "city": city,
        }.items():
            if value is not None:
                params[key] = value

        return await self._make_request(
            self.ENDPOINTS["appraisal_info"],
            params
        )

    async def get_real_estate_points(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
    ) -> dict[str, Any]:
        """
        不動産価格情報のポイント（点）を取得します（XIT004）

        Args:
            z: ズームレベル
            x: タイルX座標
            y: タイルY座標
            response_format: レスポンス形式

        Returns:
            Dict[str, Any]: 不動産価格ポイント情報
        """
        coords = TileCoordinates(z=z, x=x, y=y)

        params = {
            "response_format": response_format.value,
            "z": coords.z,
            "x": coords.x,
            "y": coords.y,
        }

        return await self._make_request(
            self.ENDPOINTS["real_estate_points"],
            params
        )

    async def search_real_estate_transactions(
        self,
        prefecture: str | None = None,
        city: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        property_type: str | None = None,
        response_format: ResponseFormat = ResponseFormat.JSON,
        lang: Language = Language.JAPANESE,
    ) -> dict[str, Any] | RealEstateSearchResult:
        """
        不動産取引価格情報を検索します（XIT001）

        Args:
            prefecture: 都道府県コード（01-47）
            city: 市区町村コード
            from_date: 取引時期開始（YYYYMMDD形式）
            to_date: 取引時期終了（YYYYMMDD形式）
            property_type: 不動産種別（1:宅地、2:中古マンション等）
            response_format: レスポンス形式
            lang: 言語（日本語/英語）

        Returns:
            Union[Dict[str, Any], RealEstateSearchResult]: 検索結果
        """
        params = {
            "response_format": response_format.value,
            "lang": lang.value,
        }

        # オプションパラメータ追加
        for key, value in {
            "prefecture": prefecture,
            "city": city,
            "from": from_date,
            "to": to_date,
            "type": property_type,
        }.items():
            if value is not None:
                params[key] = value

        result = await self._make_request(
            self.ENDPOINTS["real_estate_transactions"],
            params
        )

        # JSON形式の場合はPydanticモデルに変換
        if response_format == ResponseFormat.JSON:
            return RealEstateSearchResult(**result)

        return result

    async def get_municipalities(
        self,
        prefecture: str,
        lang: Language = Language.JAPANESE,
    ) -> list[Municipality]:
        """
        指定都道府県の市区町村一覧を取得します（XIT002）

        Args:
            prefecture: 都道府県コード（01-47）
            lang: 言語（日本語/英語）

        Returns:
            List[Municipality]: 市区町村情報リスト
        """
        params = {
            "response_format": "json",
            "prefecture": prefecture,
            "lang": lang.value,
        }

        result = await self._make_request(
            self.ENDPOINTS["municipalities"],
            params
        )

        return [Municipality(**item) for item in result.get("data", [])]

    # === 地価情報API ===

    async def get_land_price_points(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
    ) -> dict[str, Any]:
        """
        地価公示・地価調査のポイント情報を取得します（XIT005）

        Args:
            z: ズームレベル
            x: タイルX座標
            y: タイルY座標
            response_format: レスポンス形式

        Returns:
            Dict[str, Any]: 地価ポイント情報
        """
        coords = TileCoordinates(z=z, x=x, y=y)

        params = {
            "response_format": response_format.value,
            "z": coords.z,
            "x": coords.x,
            "y": coords.y,
        }

        return await self._make_request(
            self.ENDPOINTS["land_price_points"],
            params
        )

    # === 都市計画情報API ===

    async def get_urban_planning_area(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
    ) -> dict[str, Any]:
        """
        都市計画区域/区域区分情報を取得します（XKT001）

        Args:
            z: ズームレベル
            x: タイルX座標
            y: タイルY座標
            response_format: レスポンス形式

        Returns:
            Dict[str, Any]: 都市計画区域情報
        """
        coords = TileCoordinates(z=z, x=x, y=y)

        params = {
            "response_format": response_format.value,
            "z": coords.z,
            "x": coords.x,
            "y": coords.y,
        }

        return await self._make_request(
            self.ENDPOINTS["urban_planning_area"],
            params
        )

    async def get_land_use_zones(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
    ) -> dict[str, Any]:
        """
        用途地域情報を取得します（XKT002）

        Args:
            z: ズームレベル
            x: タイルX座標
            y: タイルY座標
            response_format: レスポンス形式

        Returns:
            Dict[str, Any]: 用途地域情報
        """
        coords = TileCoordinates(z=z, x=x, y=y)

        params = {
            "response_format": response_format.value,
            "z": coords.z,
            "x": coords.x,
            "y": coords.y,
        }

        return await self._make_request(
            self.ENDPOINTS["land_use_zones"],
            params
        )

    # === 施設情報API ===

    async def get_schools(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
    ) -> dict[str, Any]:
        """
        学校情報を取得します（XKT009）

        Args:
            z: ズームレベル
            x: タイルX座標
            y: タイルY座標
            response_format: レスポンス形式

        Returns:
            Dict[str, Any]: 学校情報
        """
        coords = TileCoordinates(z=z, x=x, y=y)

        params = {
            "response_format": response_format.value,
            "z": coords.z,
            "x": coords.x,
            "y": coords.y,
        }

        return await self._make_request(
            self.ENDPOINTS["schools"],
            params
        )

    async def get_medical_facilities(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
    ) -> dict[str, Any]:
        """
        医療機関情報を取得します（XKT011）

        Args:
            z: ズームレベル
            x: タイルX座標
            y: タイルY座標
            response_format: レスポンス形式

        Returns:
            Dict[str, Any]: 医療機関情報
        """
        coords = TileCoordinates(z=z, x=x, y=y)

        params = {
            "response_format": response_format.value,
            "z": coords.z,
            "x": coords.x,
            "y": coords.y,
        }

        return await self._make_request(
            self.ENDPOINTS["medical_facilities"],
            params
        )

    # === 教育・文化・福祉施設API ===

    async def get_elementary_school_districts(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
    ) -> dict[str, Any]:
        """
        小学校区情報を取得します（XKT007）

        Args:
            z: ズームレベル
            x: タイルX座標
            y: タイルY座標
            response_format: レスポンス形式

        Returns:
            Dict[str, Any]: 小学校区情報
        """
        coords = TileCoordinates(z=z, x=x, y=y)

        params = {
            "response_format": response_format.value,
            "z": coords.z,
            "x": coords.x,
            "y": coords.y,
        }

        return await self._make_request(
            self.ENDPOINTS["elementary_school_districts"],
            params
        )

    async def get_junior_high_school_districts(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
    ) -> dict[str, Any]:
        """
        中学校区情報を取得します（XKT008）

        Args:
            z: ズームレベル
            x: タイルX座標
            y: タイルY座標
            response_format: レスポンス形式

        Returns:
            Dict[str, Any]: 中学校区情報
        """
        coords = TileCoordinates(z=z, x=x, y=y)

        params = {
            "response_format": response_format.value,
            "z": coords.z,
            "x": coords.x,
            "y": coords.y,
        }

        return await self._make_request(
            self.ENDPOINTS["junior_high_school_districts"],
            params
        )

    async def get_kindergartens(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
    ) -> dict[str, Any]:
        """
        保育園・幼稚園等情報を取得します（XKT010）

        Args:
            z: ズームレベル
            x: タイルX座標
            y: タイルY座標
            response_format: レスポンス形式

        Returns:
            Dict[str, Any]: 保育園・幼稚園等情報
        """
        coords = TileCoordinates(z=z, x=x, y=y)

        params = {
            "response_format": response_format.value,
            "z": coords.z,
            "x": coords.x,
            "y": coords.y,
        }

        return await self._make_request(
            self.ENDPOINTS["kindergartens"],
            params
        )

    async def get_welfare_facilities(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
    ) -> dict[str, Any]:
        """
        福祉施設情報を取得します（XKT012）

        Args:
            z: ズームレベル
            x: タイルX座標
            y: タイルY座標
            response_format: レスポンス形式

        Returns:
            Dict[str, Any]: 福祉施設情報
        """
        coords = TileCoordinates(z=z, x=x, y=y)

        params = {
            "response_format": response_format.value,
            "z": coords.z,
            "x": coords.x,
            "y": coords.y,
        }

        return await self._make_request(
            self.ENDPOINTS["welfare_facilities"],
            params
        )

    # === 災害リスク情報API ===

    async def get_disaster_risk_areas(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
    ) -> dict[str, Any]:
        """
        災害危険区域情報を取得します（XKT021）

        Args:
            z: ズームレベル
            x: タイルX座標
            y: タイルY座標
            response_format: レスポンス形式

        Returns:
            Dict[str, Any]: 災害危険区域情報
        """
        coords = TileCoordinates(z=z, x=x, y=y)

        params = {
            "response_format": response_format.value,
            "z": coords.z,
            "x": coords.x,
            "y": coords.y,
        }

        return await self._make_request(
            self.ENDPOINTS["disaster_risk_areas"],
            params
        )

    async def get_liquefaction_tendency(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
    ) -> dict[str, Any]:
        """
        地形区分に基づく液状化の発生傾向図を取得します（XKT028）

        Args:
            z: ズームレベル
            x: タイルX座標
            y: タイルY座標
            response_format: レスポンス形式

        Returns:
            Dict[str, Any]: 液状化発生傾向情報
        """
        coords = TileCoordinates(z=z, x=x, y=y)

        params = {
            "response_format": response_format.value,
            "z": coords.z,
            "x": coords.x,
            "y": coords.y,
        }

        return await self._make_request(
            self.ENDPOINTS["liquefaction_tendency"],
            params
        )


class SyncReinfiolibClient:
    """
    不動産情報ライブラリAPI同期クライアント

    ReinfiolibClientの同期版ラッパー
    """

    def __init__(self, **kwargs) -> None:
        """同期クライアントを初期化します"""
        self._async_client = ReinfiolibClient(**kwargs)

    def __enter__(self) -> "SyncReinfiolibClient":
        """同期コンテキストマネージャー開始"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """同期コンテキストマネージャー終了"""
        self.close()

    def close(self) -> None:
        """クライアントを閉じます"""
        asyncio.run(self._async_client.close())

    def search_real_estate_transactions(self, **kwargs) -> dict[str, Any] | RealEstateSearchResult:
        """不動産取引価格情報を検索します（同期版）"""
        return asyncio.run(self._async_client.search_real_estate_transactions(**kwargs))

    def get_municipalities(self, **kwargs) -> list[Municipality]:
        """市区町村一覧を取得します（同期版）"""
        return asyncio.run(self._async_client.get_municipalities(**kwargs))

    def get_land_price_points(self, **kwargs) -> dict[str, Any]:
        """地価公示・地価調査のポイント情報を取得します（同期版）"""
        return asyncio.run(self._async_client.get_land_price_points(**kwargs))

    def get_urban_planning_area(self, **kwargs) -> dict[str, Any]:
        """都市計画区域情報を取得します（同期版）"""
        return asyncio.run(self._async_client.get_urban_planning_area(**kwargs))

    def get_land_use_zones(self, **kwargs) -> dict[str, Any]:
        """用途地域情報を取得します（同期版）"""
        return asyncio.run(self._async_client.get_land_use_zones(**kwargs))

    def get_schools(self, **kwargs) -> dict[str, Any]:
        """学校情報を取得します（同期版）"""
        return asyncio.run(self._async_client.get_schools(**kwargs))

    def get_medical_facilities(self, **kwargs) -> dict[str, Any]:
        """医療機関情報を取得します（同期版）"""
        return asyncio.run(self._async_client.get_medical_facilities(**kwargs))

    def get_disaster_risk_areas(self, **kwargs) -> dict[str, Any]:
        """災害危険区域情報を取得します（同期版）"""
        return asyncio.run(self._async_client.get_disaster_risk_areas(**kwargs))

    def get_liquefaction_tendency(self, **kwargs) -> dict[str, Any]:
        """液状化発生傾向情報を取得します（同期版）"""
        return asyncio.run(self._async_client.get_liquefaction_tendency(**kwargs))

    def get_appraisal_info(self, **kwargs) -> dict[str, Any]:
        """鑑定評価書情報を取得します（同期版）"""
        return asyncio.run(self._async_client.get_appraisal_info(**kwargs))

    def get_real_estate_points(self, **kwargs) -> dict[str, Any]:
        """不動産価格ポイント情報を取得します（同期版）"""
        return asyncio.run(self._async_client.get_real_estate_points(**kwargs))

    def get_elementary_school_districts(self, **kwargs) -> dict[str, Any]:
        """小学校区情報を取得します（同期版）"""
        return asyncio.run(self._async_client.get_elementary_school_districts(**kwargs))

    def get_junior_high_school_districts(self, **kwargs) -> dict[str, Any]:
        """中学校区情報を取得します（同期版）"""
        return asyncio.run(self._async_client.get_junior_high_school_districts(**kwargs))

    def get_kindergartens(self, **kwargs) -> dict[str, Any]:
        """保育園・幼稚園等情報を取得します（同期版）"""
        return asyncio.run(self._async_client.get_kindergartens(**kwargs))

    def get_welfare_facilities(self, **kwargs) -> dict[str, Any]:
        """福祉施設情報を取得します（同期版）"""
        return asyncio.run(self._async_client.get_welfare_facilities(**kwargs))

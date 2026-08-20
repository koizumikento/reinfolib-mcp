"""不動産情報ライブラリの現行公開APIクライアント。"""

import asyncio
import os
from dataclasses import dataclass
from typing import Any

import httpx
from asyncio_throttle import Throttler

from . import __version__
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
from .models import Language, ResponseFormat, TileCoordinates


@dataclass(frozen=True)
class APIContract:
    """公式マニュアルに記載されたAPI名と入力パラメータ。"""

    title: str
    required: frozenset[str]
    optional: frozenset[str] = frozenset()
    one_of: frozenset[str] = frozenset()

    @property
    def parameters(self) -> frozenset[str]:
        return self.required | self.optional | self.one_of


def _contract(
    title: str,
    required: tuple[str, ...],
    optional: tuple[str, ...] = (),
    one_of: tuple[str, ...] = (),
) -> APIContract:
    return APIContract(
        title=title,
        required=frozenset(required),
        optional=frozenset(optional),
        one_of=frozenset(one_of),
    )


_TILE_REQUIRED = ("response_format", "z", "x", "y")

# 公式公開API一覧（2026-08-20確認）を正とする。
API_CONTRACTS: dict[str, APIContract] = {
    "XIT001": _contract(
        "不動産価格（取引価格・成約価格）情報取得API",
        ("year",),
        ("priceClassification", "quarter", "language"),
        ("area", "city", "station"),
    ),
    "XIT002": _contract("都道府県内市区町村一覧取得API", ("area",), ("language",)),
    "XCT001": _contract("鑑定評価書情報API", ("year", "area", "division")),
    "XPT001": _contract(
        "不動産価格情報のポイントAPI",
        (*_TILE_REQUIRED, "from", "to"),
        ("priceClassification", "landTypeCode"),
    ),
    "XPT002": _contract(
        "地価公示・地価調査のポイントAPI",
        (*_TILE_REQUIRED, "year"),
        ("priceClassification", "useCategoryCode"),
    ),
    "XKT001": _contract("都市計画区域・区域区分API", _TILE_REQUIRED),
    "XKT002": _contract("用途地域API", _TILE_REQUIRED),
    "XKT003": _contract("立地適正化計画API", _TILE_REQUIRED),
    "XKT004": _contract("小学校区API", _TILE_REQUIRED, ("administrativeAreaCode",)),
    "XKT005": _contract("中学校区API", _TILE_REQUIRED, ("administrativeAreaCode",)),
    "XKT006": _contract("学校API", _TILE_REQUIRED),
    "XKT007": _contract("保育園・幼稚園等API", _TILE_REQUIRED),
    "XKT010": _contract("医療機関API", _TILE_REQUIRED),
    "XKT011": _contract(
        "福祉施設API",
        _TILE_REQUIRED,
        (
            "administrativeAreaCode",
            "welfareFacilityClassCode",
            "welfareFacilityMiddleClassCode",
            "welfareFacilityMinorClassCode",
        ),
    ),
    "XKT013": _contract("将来推計人口250mメッシュAPI", _TILE_REQUIRED),
    "XKT014": _contract("防火・準防火地域API", _TILE_REQUIRED),
    "XKT015": _contract("駅別乗降客数API", _TILE_REQUIRED),
    "XKT016": _contract("災害危険区域API", _TILE_REQUIRED, ("administrativeAreaCode",)),
    "XKT017": _contract("図書館API", _TILE_REQUIRED, ("administrativeAreaCode",)),
    "XKT018": _contract("市区町村役場及び集会施設等API", _TILE_REQUIRED),
    "XKT019": _contract(
        "自然公園地域API", _TILE_REQUIRED, ("prefectureCode", "districtCode")
    ),
    "XKT020": _contract("大規模盛土造成地マップAPI", _TILE_REQUIRED),
    "XKT021": _contract(
        "地すべり防止地区API",
        _TILE_REQUIRED,
        ("prefectureCode", "administrativeAreaCode"),
    ),
    "XKT022": _contract(
        "急傾斜地崩壊危険区域API",
        _TILE_REQUIRED,
        ("prefectureCode", "administrativeAreaCode"),
    ),
    "XKT023": _contract("地区計画API", _TILE_REQUIRED),
    "XKT024": _contract("高度利用地区API", _TILE_REQUIRED),
    "XKT025": _contract("液状化の発生傾向図API", _TILE_REQUIRED),
    "XKT026": _contract("洪水浸水想定区域API", _TILE_REQUIRED),
    "XKT027": _contract("高潮浸水想定区域API", _TILE_REQUIRED),
    "XKT028": _contract("津波浸水想定API", _TILE_REQUIRED),
    "XKT029": _contract("土砂災害警戒区域API", _TILE_REQUIRED),
    "XKT030": _contract("都市計画道路API", _TILE_REQUIRED),
    "XKT031": _contract("人口集中地区API", _TILE_REQUIRED, ("administrativeAreaCode",)),
    "XGT001": _contract("指定緊急避難場所API", _TILE_REQUIRED),
    "XST001": _contract("災害履歴API", _TILE_REQUIRED, ("disastertype_code",)),
}


class ReinfiolibClient:
    """国土交通省 不動産情報ライブラリAPIの非同期クライアント。"""

    ENDPOINTS = {api_id: f"/{api_id}" for api_id in API_CONTRACTS}

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://www.reinfolib.mlit.go.jp/ex-api/external",
        timeout: float = 30.0,
        max_retries: int = 3,
        rate_limit_per_minute: int = 60,
    ) -> None:
        self.api_key = api_key or os.getenv("REINFOLIB_API_KEY")
        if not self.api_key:
            raise ReinfiolibAPIError(
                "APIキーが設定されていません。引数またはREINFOLIB_API_KEYで設定してください。"
            )
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = httpx.AsyncClient(
            headers={
                "Ocp-Apim-Subscription-Key": self.api_key,
                "User-Agent": f"reinfolib-mcp/{__version__}",
            },
            timeout=httpx.Timeout(timeout),
        )
        self._throttler = Throttler(rate_limit=rate_limit_per_minute, period=60.0)

    async def __aenter__(self) -> "ReinfiolibClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    async def _make_request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        retries: int = 0,
    ) -> Any:
        async with self._throttler:
            try:
                response = await self._client.get(
                    f"{self.base_url}/{endpoint.lstrip('/')}", params=params
                )
                if response.status_code == 200:
                    if params and params.get("response_format") == "pbf":
                        return {"data": response.content, "format": "pbf"}
                    try:
                        return response.json()
                    except ValueError as exc:
                        raise DataFormatError(
                            f"レスポンスのJSON解析に失敗しました: {exc}"
                        ) from exc
                if response.status_code == 400:
                    raise InvalidParameterError("リクエストパラメータが不正です")
                if response.status_code == 401:
                    raise AuthenticationError("APIキーが無効です")
                if response.status_code == 404:
                    raise NotFoundError("指定されたデータが見つかりません")
                if response.status_code == 429:
                    raise RateLimitError("レート制限に達しました")
                if response.status_code >= 500:
                    raise ServerError(f"サーバーエラー: {response.status_code}")
                raise ReinfiolibAPIError(
                    f"APIエラー: {response.status_code}",
                    status_code=response.status_code,
                )
            except ReinfiolibAPIError:
                raise
            except httpx.TimeoutException as exc:
                if retries < self.max_retries:
                    await asyncio.sleep(2**retries)
                    return await self._make_request(endpoint, params, retries + 1)
                raise TimeoutError(f"リクエストタイムアウト: {exc}") from exc
            except httpx.HTTPError as exc:
                raise NetworkError(f"接続エラー: {exc}") from exc

    async def request_api(self, api_id: str, **params: Any) -> Any:
        """API IDと公式パラメータ名を指定して任意の公開APIを呼び出す。"""

        api_id = api_id.upper()
        contract = API_CONTRACTS.get(api_id)
        if contract is None:
            raise InvalidParameterError(f"未公開または廃止されたAPI IDです: {api_id}")
        clean_params = {
            key: value for key, value in params.items() if value is not None
        }
        unknown = set(clean_params) - contract.parameters
        if unknown:
            raise InvalidParameterError(
                f"{api_id}で使用できないパラメータです: {', '.join(sorted(unknown))}"
            )
        missing = contract.required - set(clean_params)
        if missing:
            raise InvalidParameterError(
                f"{api_id}の必須パラメータがありません: {', '.join(sorted(missing))}"
            )
        if contract.one_of and not contract.one_of.intersection(clean_params):
            raise InvalidParameterError(
                f"{api_id}では次のいずれかが必要です: "
                f"{', '.join(sorted(contract.one_of))}"
            )
        return await self._make_request(self.ENDPOINTS[api_id], clean_params)

    async def _tile_request(
        self,
        api_id: str,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat,
        **params: Any,
    ) -> Any:
        coords = TileCoordinates(z=z, x=x, y=y)
        return await self.request_api(
            api_id,
            response_format=response_format.value,
            z=coords.z,
            x=coords.x,
            y=coords.y,
            **params,
        )

    async def search_real_estate_transactions(
        self,
        year: int,
        quarter: int | None = None,
        area: str | None = None,
        city: str | None = None,
        station: str | None = None,
        price_classification: str | None = None,
        lang: Language = Language.JAPANESE,
    ) -> Any:
        return await self.request_api(
            "XIT001",
            year=year,
            quarter=quarter,
            area=area,
            city=city,
            station=station,
            priceClassification=price_classification,
            language=lang.value,
        )

    async def get_municipalities(
        self, area: str, lang: Language = Language.JAPANESE
    ) -> Any:
        return await self.request_api("XIT002", area=area, language=lang.value)

    async def get_appraisal_info(self, year: int, area: str, division: str) -> Any:
        return await self.request_api("XCT001", year=year, area=area, division=division)

    async def get_real_estate_points(
        self,
        z: int,
        x: int,
        y: int,
        from_period: str,
        to_period: str,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
        price_classification: str | None = None,
        land_type_code: str | None = None,
    ) -> Any:
        return await self._tile_request(
            "XPT001",
            z,
            x,
            y,
            response_format,
            **{
                "from": from_period,
                "to": to_period,
                "priceClassification": price_classification,
                "landTypeCode": land_type_code,
            },
        )

    async def get_land_price_points(
        self,
        z: int,
        x: int,
        y: int,
        year: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
        price_classification: str | None = None,
        use_category_code: str | None = None,
    ) -> Any:
        return await self._tile_request(
            "XPT002",
            z,
            x,
            y,
            response_format,
            year=year,
            priceClassification=price_classification,
            useCategoryCode=use_category_code,
        )

    async def get_urban_planning_area(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
    ) -> Any:
        return await self._tile_request("XKT001", z, x, y, response_format)

    async def get_land_use_zones(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
    ) -> Any:
        return await self._tile_request("XKT002", z, x, y, response_format)

    async def get_elementary_school_districts(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
        administrative_area_code: str | None = None,
    ) -> Any:
        return await self._tile_request(
            "XKT004",
            z,
            x,
            y,
            response_format,
            administrativeAreaCode=administrative_area_code,
        )

    async def get_junior_high_school_districts(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
        administrative_area_code: str | None = None,
    ) -> Any:
        return await self._tile_request(
            "XKT005",
            z,
            x,
            y,
            response_format,
            administrativeAreaCode=administrative_area_code,
        )

    async def get_schools(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
    ) -> Any:
        return await self._tile_request("XKT006", z, x, y, response_format)

    async def get_kindergartens(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
    ) -> Any:
        return await self._tile_request("XKT007", z, x, y, response_format)

    async def get_medical_facilities(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
    ) -> Any:
        return await self._tile_request("XKT010", z, x, y, response_format)

    async def get_welfare_facilities(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
        **filters: Any,
    ) -> Any:
        return await self._tile_request("XKT011", z, x, y, response_format, **filters)

    async def get_disaster_risk_areas(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
        administrative_area_code: str | None = None,
    ) -> Any:
        return await self._tile_request(
            "XKT016",
            z,
            x,
            y,
            response_format,
            administrativeAreaCode=administrative_area_code,
        )

    async def get_liquefaction_tendency(
        self,
        z: int,
        x: int,
        y: int,
        response_format: ResponseFormat = ResponseFormat.GEOJSON,
    ) -> Any:
        return await self._tile_request("XKT025", z, x, y, response_format)


class SyncReinfiolibClient:
    """同期呼び出しが必要な利用者向けの薄いラッパー。"""

    def __init__(self, **kwargs: Any) -> None:
        self._async_client = ReinfiolibClient(**kwargs)

    def __enter__(self) -> "SyncReinfiolibClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        asyncio.run(self._async_client.close())

    def _run(self, method: str, **kwargs: Any) -> Any:
        return asyncio.run(getattr(self._async_client, method)(**kwargs))

    def request_api(self, api_id: str, **params: Any) -> Any:
        return asyncio.run(self._async_client.request_api(api_id, **params))

    def search_real_estate_transactions(self, **kwargs: Any) -> Any:
        return self._run("search_real_estate_transactions", **kwargs)

    def get_municipalities(self, **kwargs: Any) -> Any:
        return self._run("get_municipalities", **kwargs)

    def get_appraisal_info(self, **kwargs: Any) -> Any:
        return self._run("get_appraisal_info", **kwargs)

    def get_real_estate_points(self, **kwargs: Any) -> Any:
        return self._run("get_real_estate_points", **kwargs)

    def get_land_price_points(self, **kwargs: Any) -> Any:
        return self._run("get_land_price_points", **kwargs)

    def get_urban_planning_area(self, **kwargs: Any) -> Any:
        return self._run("get_urban_planning_area", **kwargs)

    def get_land_use_zones(self, **kwargs: Any) -> Any:
        return self._run("get_land_use_zones", **kwargs)

    def get_schools(self, **kwargs: Any) -> Any:
        return self._run("get_schools", **kwargs)

    def get_medical_facilities(self, **kwargs: Any) -> Any:
        return self._run("get_medical_facilities", **kwargs)

    def get_disaster_risk_areas(self, **kwargs: Any) -> Any:
        return self._run("get_disaster_risk_areas", **kwargs)

    def get_liquefaction_tendency(self, **kwargs: Any) -> Any:
        return self._run("get_liquefaction_tendency", **kwargs)

    def get_elementary_school_districts(self, **kwargs: Any) -> Any:
        return self._run("get_elementary_school_districts", **kwargs)

    def get_junior_high_school_districts(self, **kwargs: Any) -> Any:
        return self._run("get_junior_high_school_districts", **kwargs)

    def get_kindergartens(self, **kwargs: Any) -> Any:
        return self._run("get_kindergartens", **kwargs)

    def get_welfare_facilities(self, **kwargs: Any) -> Any:
        return self._run("get_welfare_facilities", **kwargs)

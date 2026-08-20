"""
不動産情報ライブラリAPI用データモデル群
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ResponseFormat(str, Enum):
    """APIレスポンス形式"""

    JSON = "json"
    GEOJSON = "geojson"
    PBF = "pbf"  # バイナリベクトルタイル


class PropertyType(str, Enum):
    """不動産種別"""

    RESIDENTIAL_LAND = "01"  # 宅地（土地）
    LAND_AND_BUILDING = "02"  # 宅地（土地と建物）
    USED_MANSION = "07"  # 中古マンション等
    AGRICULTURAL_LAND = "10"  # 農地
    FOREST_LAND = "11"  # 林地


class Language(str, Enum):
    """言語設定"""

    JAPANESE = "ja"
    ENGLISH = "en"


# 基本レスポンスモデル
class BaseResponse(BaseModel):
    """APIレスポンスベースモデル"""

    status: str = Field(default="success", description="レスポンスステータス")
    message: str | None = Field(None, description="メッセージ")


# 不動産取引価格情報モデル
class RealEstateTransaction(BaseModel):
    """不動産取引価格情報モデル"""

    prefecture: str = Field(description="都道府県名")
    prefecture_code: str | None = Field(None, description="都道府県コード")
    city: str = Field(description="市区町村名")
    city_code: str | None = Field(None, description="市区町村コード")
    district: str | None = Field(None, description="地区名")
    nearest_station: str | None = Field(None, description="最寄駅名")
    distance_to_station: int | None = Field(None, description="駅距離（分）")

    # 価格情報
    transaction_price: int | None = Field(None, description="取引価格（円）")
    price_per_unit_area: int | None = Field(None, description="㎡単価（円）")

    # 面積情報
    area: float | None = Field(None, description="面積（㎡）")
    land_shape: str | None = Field(None, description="土地の形状")
    frontage: float | None = Field(None, description="間口（m）")

    # 建物情報
    building_year: str | None = Field(None, description="建築年")
    structure: str | None = Field(None, description="構造")
    usage: str | None = Field(None, description="用途")
    floors: str | None = Field(None, description="階数")

    # 取引情報
    transaction_period: str | None = Field(None, description="取引時期")
    renovation: str | None = Field(None, description="改装")
    remarks: str | None = Field(None, description="取引の事情等")

    # 地理情報
    longitude: float | None = Field(None, description="経度")
    latitude: float | None = Field(None, description="緯度")


class RealEstateSearchResult(BaseModel):
    """不動産取引価格検索結果モデル"""

    data: list[RealEstateTransaction] = Field(
        default_factory=list, description="取引データ"
    )
    total_count: int = Field(description="総件数")
    page: int = Field(default=1, description="ページ番号")
    per_page: int = Field(default=100, description="1ページあたりの件数")
    has_next: bool = Field(default=False, description="次ページの有無")


# 地価公示・調査モデル
class LandPricePoint(BaseModel):
    """地価公示・調査ポイントモデル"""

    point_name: str = Field(description="地点名")
    point_code: str | None = Field(None, description="地点コード")
    address: str = Field(description="住所")
    prefecture: str = Field(description="都道府県名")
    city: str = Field(description="市区町村名")

    # 価格情報
    price_per_sqm: int = Field(description="㎡単価（円）")
    year: int = Field(description="調査年")
    survey_type: str | None = Field(None, description="調査種別（公示/調査）")

    # 土地情報
    land_use: str | None = Field(None, description="用途")
    land_shape: str | None = Field(None, description="土地の形状")
    area: float | None = Field(None, description="面積（㎡）")

    # 位置情報
    longitude: float = Field(description="経度")
    latitude: float = Field(description="緯度")

    # その他情報
    surrounding_land_use: str | None = Field(None, description="周辺の土地利用状況")
    remarks: str | None = Field(None, description="備考")


# 市区町村情報モデル
class Municipality(BaseModel):
    """市区町村情報モデル"""

    prefecture_code: str = Field(description="都道府県コード")
    prefecture_name: str = Field(description="都道府県名")
    city_code: str = Field(description="市区町村コード")
    city_name: str = Field(description="市区町村名")
    city_name_en: str | None = Field(None, description="市区町村名（英語）")


# 都市計画情報モデル
class UrbanPlanningInfo(BaseModel):
    """都市計画情報モデル"""

    area_type: str = Field(description="区域種別")
    area_name: str | None = Field(None, description="区域名")
    designation_date: str | None = Field(None, description="指定年月日")
    area_size: float | None = Field(None, description="面積（㎡）")
    regulations: str | None = Field(None, description="規制内容")

    # 地理情報
    geometry: dict[str, Any] | None = Field(None, description="ジオメトリ情報")


# 災害リスク情報モデル
class DisasterRiskInfo(BaseModel):
    """災害リスク情報モデル"""

    risk_type: str = Field(description="災害種別")
    risk_level: str | None = Field(None, description="リスクレベル")
    area_name: str | None = Field(None, description="地域名")
    designation_authority: str | None = Field(None, description="指定機関")
    designation_date: str | None = Field(None, description="指定年月日")

    # 地理情報
    geometry: dict[str, Any] | None = Field(None, description="ジオメトリ情報")


# 施設情報モデル
class FacilityInfo(BaseModel):
    """施設情報モデル"""

    facility_type: str = Field(description="施設種別")
    facility_name: str = Field(description="施設名")
    address: str | None = Field(None, description="住所")
    prefecture: str | None = Field(None, description="都道府県名")
    city: str | None = Field(None, description="市区町村名")

    # 位置情報
    longitude: float | None = Field(None, description="経度")
    latitude: float | None = Field(None, description="緯度")

    # 追加情報
    capacity: int | None = Field(None, description="収容人数")
    establishment_year: int | None = Field(None, description="設立年")
    operator: str | None = Field(None, description="運営者")


# GeoJSONレスポンス用モデル
class GeoJSONResponse(BaseModel):
    """GeoJSONレスポンスモデル"""

    type: str = Field(default="FeatureCollection")
    features: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ["FeatureCollection", "Feature"]:
            raise ValueError("typeはFeatureCollectionまたはFeatureである必要があります")
        return v


# APIリクエストパラメータモデル
class RealEstateSearchParams(BaseModel):
    """不動産検索パラメータモデル"""

    year: int = Field(description="取引年", ge=2005)
    quarter: int | None = Field(None, description="四半期", ge=1, le=4)
    area: str | None = Field(None, description="都道府県コード（01-47）")
    city: str | None = Field(None, description="市区町村コード")
    station: str | None = Field(None, description="駅コード")
    price_classification: str | None = Field(None, description="価格情報区分")
    language: Language = Field(default=Language.JAPANESE)

    @field_validator("area")
    @classmethod
    def validate_area(cls, v: str | None) -> str | None:
        if v is not None:
            if not (v.isdigit() and 1 <= int(v) <= 47):
                raise ValueError("都道府県コードは01-47の範囲で指定してください")
        return v

    @model_validator(mode="after")
    def validate_location(self) -> "RealEstateSearchParams":
        if not any((self.area, self.city, self.station)):
            raise ValueError("area、city、stationのいずれかを指定してください")
        return self


class TileCoordinates(BaseModel):
    """タイル座標モデル"""

    z: int = Field(description="ズームレベル", ge=1, le=18)
    x: int = Field(description="タイルX座標", ge=0)
    y: int = Field(description="タイルY座標", ge=0)

    @field_validator("x", "y")
    @classmethod
    def validate_tile_coords(cls, v: int, info) -> int:
        if info.data and "z" in info.data:
            max_coord = 2 ** info.data["z"] - 1
            if v < 0 or v > max_coord:
                raise ValueError(
                    f"座標値はズームレベル{info.data['z']}では0-{max_coord}の範囲で指定してください"
                )
        return v


# エラーレスポンスモデル
class ErrorResponse(BaseModel):
    """APIエラーレスポンスモデル"""

    error: dict[str, str | int] = Field(description="エラー情報")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "INVALID_PARAMETER",
                    "message": "パラメータが不正です",
                    "details": "prefecture code must be between 01 and 47",
                }
            }
        }
    )

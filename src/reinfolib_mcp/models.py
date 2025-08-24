"""
不動産情報ライブラリAPI用データモデル群
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator
from geojson import Feature, FeatureCollection, Point, Polygon


class ResponseFormat(str, Enum):
    """APIレスポンス形式"""
    JSON = "json"
    GEOJSON = "geojson"
    PBF = "pbf"  # バイナリベクトルタイル


class PropertyType(str, Enum):
    """不動産種別"""
    RESIDENTIAL_LAND = "1"  # 宅地（土地）
    USED_MANSION = "2"      # 中古マンション等
    USED_HOUSE = "3"        # 中古戸建住宅
    FOREST_LAND = "4"       # 林地
    AGRICULTURAL_LAND = "5" # 農地


class Language(str, Enum):
    """言語設定"""
    JAPANESE = "ja"
    ENGLISH = "en"


# 基本レスポンスモデル
class BaseResponse(BaseModel):
    """APIレスポンスベースモデル"""
    status: str = Field(default="success", description="レスポンスステータス")
    message: Optional[str] = Field(None, description="メッセージ")


# 不動産取引価格情報モデル
class RealEstateTransaction(BaseModel):
    """不動産取引価格情報モデル"""
    prefecture: str = Field(description="都道府県名")
    prefecture_code: Optional[str] = Field(None, description="都道府県コード")
    city: str = Field(description="市区町村名") 
    city_code: Optional[str] = Field(None, description="市区町村コード")
    district: Optional[str] = Field(None, description="地区名")
    nearest_station: Optional[str] = Field(None, description="最寄駅名")
    distance_to_station: Optional[int] = Field(None, description="駅距離（分）")
    
    # 価格情報
    transaction_price: Optional[int] = Field(None, description="取引価格（円）")
    price_per_unit_area: Optional[int] = Field(None, description="㎡単価（円）")
    
    # 面積情報
    area: Optional[float] = Field(None, description="面積（㎡）")
    land_shape: Optional[str] = Field(None, description="土地の形状")
    frontage: Optional[float] = Field(None, description="間口（m）")
    
    # 建物情報
    building_year: Optional[str] = Field(None, description="建築年")
    structure: Optional[str] = Field(None, description="構造")
    usage: Optional[str] = Field(None, description="用途")
    floors: Optional[str] = Field(None, description="階数")
    
    # 取引情報
    transaction_period: Optional[str] = Field(None, description="取引時期")
    renovation: Optional[str] = Field(None, description="改装")
    remarks: Optional[str] = Field(None, description="取引の事情等")
    
    # 地理情報
    longitude: Optional[float] = Field(None, description="経度")
    latitude: Optional[float] = Field(None, description="緯度")


class RealEstateSearchResult(BaseModel):
    """不動産取引価格検索結果モデル"""
    data: List[RealEstateTransaction] = Field(default_factory=list, description="取引データ")
    total_count: int = Field(description="総件数")
    page: int = Field(default=1, description="ページ番号")
    per_page: int = Field(default=100, description="1ページあたりの件数")
    has_next: bool = Field(default=False, description="次ページの有無")


# 地価公示・調査モデル
class LandPricePoint(BaseModel):
    """地価公示・調査ポイントモデル"""
    point_name: str = Field(description="地点名")
    point_code: Optional[str] = Field(None, description="地点コード")
    address: str = Field(description="住所")
    prefecture: str = Field(description="都道府県名")
    city: str = Field(description="市区町村名")
    
    # 価格情報
    price_per_sqm: int = Field(description="㎡単価（円）")
    year: int = Field(description="調査年")
    survey_type: Optional[str] = Field(None, description="調査種別（公示/調査）")
    
    # 土地情報
    land_use: Optional[str] = Field(None, description="用途")
    land_shape: Optional[str] = Field(None, description="土地の形状")
    area: Optional[float] = Field(None, description="面積（㎡）")
    
    # 位置情報
    longitude: float = Field(description="経度")
    latitude: float = Field(description="緯度")
    
    # その他情報
    surrounding_land_use: Optional[str] = Field(None, description="周辺の土地利用状況")
    remarks: Optional[str] = Field(None, description="備考")


# 市区町村情報モデル
class Municipality(BaseModel):
    """市区町村情報モデル"""
    prefecture_code: str = Field(description="都道府県コード")
    prefecture_name: str = Field(description="都道府県名")
    city_code: str = Field(description="市区町村コード")
    city_name: str = Field(description="市区町村名")
    city_name_en: Optional[str] = Field(None, description="市区町村名（英語）")


# 都市計画情報モデル
class UrbanPlanningInfo(BaseModel):
    """都市計画情報モデル"""
    area_type: str = Field(description="区域種別")
    area_name: Optional[str] = Field(None, description="区域名")
    designation_date: Optional[str] = Field(None, description="指定年月日")
    area_size: Optional[float] = Field(None, description="面積（㎡）")
    regulations: Optional[str] = Field(None, description="規制内容")
    
    # 地理情報
    geometry: Optional[Dict[str, Any]] = Field(None, description="ジオメトリ情報")


# 災害リスク情報モデル  
class DisasterRiskInfo(BaseModel):
    """災害リスク情報モデル"""
    risk_type: str = Field(description="災害種別")
    risk_level: Optional[str] = Field(None, description="リスクレベル")
    area_name: Optional[str] = Field(None, description="地域名")
    designation_authority: Optional[str] = Field(None, description="指定機関")
    designation_date: Optional[str] = Field(None, description="指定年月日")
    
    # 地理情報
    geometry: Optional[Dict[str, Any]] = Field(None, description="ジオメトリ情報")


# 施設情報モデル
class FacilityInfo(BaseModel):
    """施設情報モデル"""
    facility_type: str = Field(description="施設種別")
    facility_name: str = Field(description="施設名")
    address: Optional[str] = Field(None, description="住所")
    prefecture: Optional[str] = Field(None, description="都道府県名")
    city: Optional[str] = Field(None, description="市区町村名")
    
    # 位置情報
    longitude: Optional[float] = Field(None, description="経度")
    latitude: Optional[float] = Field(None, description="緯度")
    
    # 追加情報
    capacity: Optional[int] = Field(None, description="収容人数")
    establishment_year: Optional[int] = Field(None, description="設立年")
    operator: Optional[str] = Field(None, description="運営者")


# GeoJSONレスポンス用モデル
class GeoJSONResponse(BaseModel):
    """GeoJSONレスポンスモデル"""
    type: str = Field(default="FeatureCollection")
    features: List[Dict[str, Any]] = Field(default_factory=list)
    
    @validator('type')
    def validate_type(cls, v: str) -> str:
        if v not in ["FeatureCollection", "Feature"]:
            raise ValueError("typeはFeatureCollectionまたはFeatureである必要があります")
        return v


# APIリクエストパラメータモデル
class RealEstateSearchParams(BaseModel):
    """不動産検索パラメータモデル"""
    response_format: ResponseFormat = Field(default=ResponseFormat.JSON)
    prefecture: Optional[str] = Field(None, description="都道府県コード（01-47）")
    city: Optional[str] = Field(None, description="市区町村コード")
    from_date: Optional[str] = Field(None, description="取引時期開始（YYYYMMDD）")
    to_date: Optional[str] = Field(None, description="取引時期終了（YYYYMMDD）")
    property_type: Optional[PropertyType] = Field(None, description="不動産種別")
    
    @validator('prefecture')
    def validate_prefecture(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not (v.isdigit() and 1 <= int(v) <= 47):
                raise ValueError("都道府県コードは01-47の範囲で指定してください")
        return v
    
    @validator('from_date', 'to_date')
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if len(v) != 8 or not v.isdigit():
                raise ValueError("日付はYYYYMMDD形式で指定してください")
        return v


class TileCoordinates(BaseModel):
    """タイル座標モデル"""
    z: int = Field(description="ズームレベル", ge=1, le=18)
    x: int = Field(description="タイルX座標", ge=0)
    y: int = Field(description="タイルY座標", ge=0)
    
    @validator('x', 'y')
    def validate_tile_coords(cls, v: int, values: Dict[str, Any]) -> int:
        if 'z' in values:
            max_coord = 2 ** values['z'] - 1
            if v < 0 or v > max_coord:
                raise ValueError(f"座標値はズームレベル{values['z']}では0-{max_coord}の範囲で指定してください")
        return v


# エラーレスポンスモデル
class ErrorResponse(BaseModel):
    """APIエラーレスポンスモデル"""
    error: Dict[str, Union[str, int]] = Field(description="エラー情報")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "INVALID_PARAMETER",
                    "message": "パラメータが不正です",
                    "details": "prefecture code must be between 01 and 47"
                }
            }
        }

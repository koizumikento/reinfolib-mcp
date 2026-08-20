"""
データモデルのテスト
"""

import pytest
from pydantic import ValidationError

from reinfolib_mcp.models import (
    Language,
    Municipality,
    PropertyType,
    RealEstateSearchParams,
    RealEstateTransaction,
    ResponseFormat,
    TileCoordinates,
)


class TestEnums:
    """列挙型のテスト"""

    def test_response_format_values(self):
        """ResponseFormat列挙型の値を確認"""
        assert ResponseFormat.JSON == "json"
        assert ResponseFormat.GEOJSON == "geojson"
        assert ResponseFormat.PBF == "pbf"

    def test_language_values(self):
        """Language列挙型の値を確認"""
        assert Language.JAPANESE == "ja"
        assert Language.ENGLISH == "en"

    def test_property_type_values(self):
        """PropertyType列挙型の値を確認"""
        assert PropertyType.RESIDENTIAL_LAND == "01"
        assert PropertyType.LAND_AND_BUILDING == "02"
        assert PropertyType.USED_MANSION == "07"
        assert PropertyType.AGRICULTURAL_LAND == "10"
        assert PropertyType.FOREST_LAND == "11"


class TestRealEstateTransaction:
    """不動産取引情報モデルのテスト"""

    def test_create_basic_transaction(self):
        """基本的な取引情報の作成"""
        transaction = RealEstateTransaction(
            prefecture="東京都", city="千代田区", transaction_price=50000000, area=100.5
        )

        assert transaction.prefecture == "東京都"
        assert transaction.city == "千代田区"
        assert transaction.transaction_price == 50000000
        assert transaction.area == 100.5

    def test_create_full_transaction(self):
        """全フィールドを含む取引情報の作成"""
        transaction = RealEstateTransaction(
            prefecture="東京都",
            prefecture_code="13",
            city="千代田区",
            city_code="13101",
            district="永田町",
            nearest_station="国会議事堂前駅",
            distance_to_station=3,
            transaction_price=50000000,
            price_per_unit_area=500000,
            area=100.5,
            building_year="平成20年",
            structure="RC",
            usage="住宅",
            transaction_period="2023年第1四半期",
            longitude=139.7514,
            latitude=35.6851,
        )

        assert transaction.prefecture_code == "13"
        assert transaction.nearest_station == "国会議事堂前駅"
        assert transaction.longitude == 139.7514
        assert transaction.latitude == 35.6851

    def test_optional_fields_none(self):
        """オプションフィールドがNoneでも作成可能"""
        transaction = RealEstateTransaction(prefecture="大阪府", city="大阪市")

        assert transaction.transaction_price is None
        assert transaction.area is None
        assert transaction.building_year is None


class TestMunicipality:
    """市区町村情報モデルのテスト"""

    def test_create_municipality(self):
        """市区町村情報の作成"""
        municipality = Municipality(
            prefecture_code="13",
            prefecture_name="東京都",
            city_code="13101",
            city_name="千代田区",
        )

        assert municipality.prefecture_code == "13"
        assert municipality.prefecture_name == "東京都"
        assert municipality.city_code == "13101"
        assert municipality.city_name == "千代田区"

    def test_create_municipality_with_english(self):
        """英語名付き市区町村情報の作成"""
        municipality = Municipality(
            prefecture_code="13",
            prefecture_name="東京都",
            city_code="13101",
            city_name="千代田区",
            city_name_en="Chiyoda City",
        )

        assert municipality.city_name_en == "Chiyoda City"


class TestTileCoordinates:
    """タイル座標モデルのテスト"""

    def test_valid_tile_coordinates(self):
        """有効なタイル座標の作成"""
        coords = TileCoordinates(z=10, x=500, y=300)

        assert coords.z == 10
        assert coords.x == 500
        assert coords.y == 300

    def test_invalid_zoom_level(self):
        """無効なズームレベルでバリデーションエラー"""
        with pytest.raises(ValidationError):
            TileCoordinates(z=0, x=0, y=0)  # z < 1

        with pytest.raises(ValidationError):
            TileCoordinates(z=19, x=0, y=0)  # z > 18

    def test_negative_coordinates(self):
        """負のタイル座標でバリデーションエラー"""
        with pytest.raises(ValidationError):
            TileCoordinates(z=10, x=-1, y=0)

        with pytest.raises(ValidationError):
            TileCoordinates(z=10, x=0, y=-1)


class TestRealEstateSearchParams:
    """不動産検索パラメータモデルのテスト"""

    def test_valid_search_params(self):
        """有効な検索パラメータの作成"""
        params = RealEstateSearchParams(
            year=2025,
            area="13",
            city="13101",
            quarter=2,
            price_classification="01",
        )

        assert params.year == 2025
        assert params.area == "13"
        assert params.city == "13101"
        assert params.quarter == 2
        assert params.price_classification == "01"

    def test_invalid_prefecture_code(self):
        """無効な都道府県コードでバリデーションエラー"""
        with pytest.raises(ValidationError):
            RealEstateSearchParams(year=2025, area="00")  # < 1

        with pytest.raises(ValidationError):
            RealEstateSearchParams(year=2025, area="48")  # > 47

        with pytest.raises(ValidationError):
            RealEstateSearchParams(year=2025, area="XX")  # 非数値

    def test_requires_current_time_and_location_parameters(self):
        """年・四半期・地域条件を検証する"""
        with pytest.raises(ValidationError):
            RealEstateSearchParams(year=2004, area="13")

        with pytest.raises(ValidationError):
            RealEstateSearchParams(year=2025, quarter=5, area="13")

        with pytest.raises(ValidationError):
            RealEstateSearchParams(year=2025)

    def test_default_values(self):
        """デフォルト値の確認"""
        params = RealEstateSearchParams(year=2025, area="13")

        assert params.language == Language.JAPANESE
        assert params.area == "13"
        assert params.city is None

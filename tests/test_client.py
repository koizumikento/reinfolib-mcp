"""現行の不動産情報ライブラリAPI契約に対する回帰テスト。"""

from unittest.mock import AsyncMock, patch

import pytest

from reinfolib_mcp.client import API_CONTRACTS, ReinfiolibClient, SyncReinfiolibClient
from reinfolib_mcp.exceptions import (
    AuthenticationError,
    InvalidParameterError,
    ReinfiolibAPIError,
)
from reinfolib_mcp.models import Language

EXPECTED_API_PARAMETERS = {
    "XIT001": (
        {"year"},
        {"priceClassification", "quarter", "language"},
        {"area", "city", "station"},
    ),
    "XIT002": ({"area"}, {"language"}, set()),
    "XCT001": ({"year", "area", "division"}, set(), set()),
    "XPT001": (
        {"response_format", "z", "x", "y", "from", "to"},
        {"priceClassification", "landTypeCode"},
        set(),
    ),
    "XPT002": (
        {"response_format", "z", "x", "y", "year"},
        {"priceClassification", "useCategoryCode"},
        set(),
    ),
    "XKT001": ({"response_format", "z", "x", "y"}, set(), set()),
    "XKT002": ({"response_format", "z", "x", "y"}, set(), set()),
    "XKT003": ({"response_format", "z", "x", "y"}, set(), set()),
    "XKT004": ({"response_format", "z", "x", "y"}, {"administrativeAreaCode"}, set()),
    "XKT005": ({"response_format", "z", "x", "y"}, {"administrativeAreaCode"}, set()),
    "XKT006": ({"response_format", "z", "x", "y"}, set(), set()),
    "XKT007": ({"response_format", "z", "x", "y"}, set(), set()),
    "XKT010": ({"response_format", "z", "x", "y"}, set(), set()),
    "XKT011": (
        {"response_format", "z", "x", "y"},
        {
            "administrativeAreaCode",
            "welfareFacilityClassCode",
            "welfareFacilityMiddleClassCode",
            "welfareFacilityMinorClassCode",
        },
        set(),
    ),
    "XKT013": ({"response_format", "z", "x", "y"}, set(), set()),
    "XKT014": ({"response_format", "z", "x", "y"}, set(), set()),
    "XKT015": ({"response_format", "z", "x", "y"}, set(), set()),
    "XKT016": ({"response_format", "z", "x", "y"}, {"administrativeAreaCode"}, set()),
    "XKT017": ({"response_format", "z", "x", "y"}, {"administrativeAreaCode"}, set()),
    "XKT018": ({"response_format", "z", "x", "y"}, set(), set()),
    "XKT019": (
        {"response_format", "z", "x", "y"},
        {"prefectureCode", "districtCode"},
        set(),
    ),
    "XKT020": ({"response_format", "z", "x", "y"}, set(), set()),
    "XKT021": (
        {"response_format", "z", "x", "y"},
        {"prefectureCode", "administrativeAreaCode"},
        set(),
    ),
    "XKT022": (
        {"response_format", "z", "x", "y"},
        {"prefectureCode", "administrativeAreaCode"},
        set(),
    ),
    "XKT023": ({"response_format", "z", "x", "y"}, set(), set()),
    "XKT024": ({"response_format", "z", "x", "y"}, set(), set()),
    "XKT025": ({"response_format", "z", "x", "y"}, set(), set()),
    "XKT026": ({"response_format", "z", "x", "y"}, set(), set()),
    "XKT027": ({"response_format", "z", "x", "y"}, set(), set()),
    "XKT028": ({"response_format", "z", "x", "y"}, set(), set()),
    "XKT029": ({"response_format", "z", "x", "y"}, set(), set()),
    "XKT030": ({"response_format", "z", "x", "y"}, set(), set()),
    "XKT031": ({"response_format", "z", "x", "y"}, {"administrativeAreaCode"}, set()),
    "XGT001": ({"response_format", "z", "x", "y"}, set(), set()),
    "XST001": ({"response_format", "z", "x", "y"}, {"disastertype_code"}, set()),
}


def test_official_api_contract_is_complete() -> None:
    assert len(API_CONTRACTS) == 35
    assert set(API_CONTRACTS) == set(EXPECTED_API_PARAMETERS)
    for api_id, (required, optional, one_of) in EXPECTED_API_PARAMETERS.items():
        contract = API_CONTRACTS[api_id]
        assert contract.required == required
        assert contract.optional == optional
        assert contract.one_of == one_of


def test_removed_api_ids_are_not_exposed() -> None:
    assert {"XIT003", "XIT004", "XIT005", "XKT008", "XKT009", "XKT012"}.isdisjoint(
        API_CONTRACTS
    )


def test_client_requires_api_key() -> None:
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ReinfiolibAPIError, match="APIキーが設定されていません"):
            ReinfiolibClient()


@pytest.mark.asyncio
async def test_xit001_uses_current_parameters() -> None:
    client = ReinfiolibClient(api_key="test")
    client._make_request = AsyncMock(return_value={"data": []})

    result = await client.search_real_estate_transactions(
        year=2025,
        quarter=2,
        city="13102",
        price_classification="01",
        lang=Language.JAPANESE,
    )

    assert result == {"data": []}
    client._make_request.assert_awaited_once_with(
        "/XIT001",
        {
            "year": 2025,
            "quarter": 2,
            "city": "13102",
            "priceClassification": "01",
            "language": "ja",
        },
    )
    await client.close()


@pytest.mark.asyncio
async def test_xpt_endpoints_use_current_ids_and_required_parameters() -> None:
    client = ReinfiolibClient(api_key="test")
    client._make_request = AsyncMock(return_value={"features": []})

    await client.get_real_estate_points(
        z=14, x=14624, y=6016, from_period="20252", to_period="20252"
    )
    await client.get_land_price_points(z=14, x=14624, y=6016, year=2025)

    assert client._make_request.await_args_list[0].args[0] == "/XPT001"
    assert client._make_request.await_args_list[0].args[1]["from"] == "20252"
    assert client._make_request.await_args_list[1].args[0] == "/XPT002"
    assert client._make_request.await_args_list[1].args[1]["year"] == 2025
    await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "expected_id"),
    [
        ("get_elementary_school_districts", "XKT004"),
        ("get_junior_high_school_districts", "XKT005"),
        ("get_schools", "XKT006"),
        ("get_kindergartens", "XKT007"),
        ("get_medical_facilities", "XKT010"),
        ("get_welfare_facilities", "XKT011"),
        ("get_disaster_risk_areas", "XKT016"),
        ("get_liquefaction_tendency", "XKT025"),
    ],
)
async def test_compatibility_methods_map_to_current_ids(
    method: str, expected_id: str
) -> None:
    client = ReinfiolibClient(api_key="test")
    client._make_request = AsyncMock(return_value={"features": []})
    await getattr(client, method)(z=14, x=14624, y=6016)
    assert client._make_request.await_args.args[0] == f"/{expected_id}"
    await client.close()


@pytest.mark.asyncio
async def test_contract_validation_rejects_missing_unknown_and_removed_inputs() -> None:
    client = ReinfiolibClient(api_key="test")
    with pytest.raises(InvalidParameterError, match="いずれかが必要"):
        await client.request_api("XIT001", year=2025)
    with pytest.raises(InvalidParameterError, match="必須パラメータ"):
        await client.request_api("XPT002", response_format="geojson", z=14, x=1, y=1)
    with pytest.raises(InvalidParameterError, match="使用できない"):
        await client.request_api(
            "XKT001", response_format="geojson", z=14, x=1, y=1, year=2025
        )
    with pytest.raises(InvalidParameterError, match="廃止"):
        await client.request_api("XIT003")
    await client.close()


@pytest.mark.asyncio
async def test_http_authentication_error_keeps_specific_type() -> None:
    client = ReinfiolibClient(api_key="invalid")
    response = AsyncMock(status_code=401)
    client._client.get = AsyncMock(return_value=response)
    with pytest.raises(AuthenticationError):
        await client._make_request("/XIT002", {"area": "13"})
    await client.close()


def test_sync_client_delegates_to_async_client() -> None:
    with patch("reinfolib_mcp.client.ReinfiolibClient") as async_client:
        async_client.return_value.get_municipalities.return_value = [{"id": "13101"}]
        with patch(
            "reinfolib_mcp.client.asyncio.run", return_value=[{"id": "13101"}]
        ) as run:
            client = SyncReinfiolibClient(api_key="test")
            assert client.get_municipalities(area="13") == [{"id": "13101"}]
            run.assert_called_once()

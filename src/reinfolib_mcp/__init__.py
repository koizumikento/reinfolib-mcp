"""
不動産情報ライブラリMCPサーバーとPythonライブラリ

国土交通省の不動産情報ライブラリAPIを使用したMCPサーバーとPythonクライアント
"""

__version__ = "0.1.0"
__author__ = "Developer"
__email__ = "dev@example.com"

# メインクラスとツールをエクスポート
from .client import ReinfiolibClient, SyncReinfiolibClient
from .exceptions import (
    AuthenticationError,
    InvalidParameterError,
    NetworkError,
    RateLimitError,
    ReinfiolibAPIError,
)
from .models import (
    DisasterRiskInfo,
    LandPricePoint,
    Municipality,
    RealEstateSearchResult,
    RealEstateTransaction,
    UrbanPlanningInfo,
)

__all__ = [
    # Client classes
    "ReinfiolibClient",
    "SyncReinfiolibClient",
    # Exception classes
    "ReinfiolibAPIError",
    "AuthenticationError",
    "InvalidParameterError",
    "RateLimitError",
    "NetworkError",
    # Data models
    "RealEstateTransaction",
    "RealEstateSearchResult",
    "LandPricePoint",
    "Municipality",
    "UrbanPlanningInfo",
    "DisasterRiskInfo",
]

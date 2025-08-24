"""
不動産情報ライブラリAPI用カスタム例外クラス群
"""

from typing import Optional


class ReinfiolibAPIError(Exception):
    """不動産情報ライブラリAPI基底例外クラス"""

    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        details: Optional[str] = None
    ) -> None:
        """
        API例外を初期化します。

        Args:
            message: エラーメッセージ
            status_code: HTTPステータスコード
            error_code: APIエラーコード
            details: エラー詳細情報
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details
        super().__init__(message)

    def __str__(self) -> str:
        """エラー情報の文字列表現"""
        error_info = [self.message]
        
        if self.status_code:
            error_info.append(f"Status: {self.status_code}")
        
        if self.error_code:
            error_info.append(f"Code: {self.error_code}")
            
        if self.details:
            error_info.append(f"Details: {self.details}")
            
        return " | ".join(error_info)


class AuthenticationError(ReinfiolibAPIError):
    """認証エラー（401 Unauthorized）"""

    def __init__(
        self, 
        message: str = "APIキーが無効です。認証に失敗しました。", 
        **kwargs
    ) -> None:
        super().__init__(message, status_code=401, **kwargs)


class InvalidParameterError(ReinfiolibAPIError):
    """パラメータエラー（400 Bad Request）"""

    def __init__(
        self, 
        message: str = "リクエストパラメータが不正です。", 
        **kwargs
    ) -> None:
        super().__init__(message, status_code=400, **kwargs)


class RateLimitError(ReinfiolibAPIError):
    """レート制限エラー（429 Too Many Requests）"""

    def __init__(
        self, 
        message: str = "レート制限に達しました。しばらく時間をおいて再試行してください。", 
        retry_after: Optional[int] = None,
        **kwargs
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, status_code=429, **kwargs)


class NotFoundError(ReinfiolibAPIError):
    """リソース未発見エラー（404 Not Found）"""

    def __init__(
        self, 
        message: str = "指定されたリソースが見つかりません。", 
        **kwargs
    ) -> None:
        super().__init__(message, status_code=404, **kwargs)


class ServerError(ReinfiolibAPIError):
    """サーバーエラー（500 Internal Server Error）"""

    def __init__(
        self, 
        message: str = "サーバー内部でエラーが発生しました。", 
        **kwargs
    ) -> None:
        super().__init__(message, status_code=500, **kwargs)


class NetworkError(ReinfiolibAPIError):
    """ネットワークエラー"""

    def __init__(
        self, 
        message: str = "ネットワーク接続エラーが発生しました。", 
        **kwargs
    ) -> None:
        super().__init__(message, **kwargs)


class TimeoutError(ReinfiolibAPIError):
    """タイムアウトエラー"""

    def __init__(
        self, 
        message: str = "リクエストがタイムアウトしました。", 
        timeout_seconds: Optional[float] = None,
        **kwargs
    ) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(message, **kwargs)


class DataFormatError(ReinfiolibAPIError):
    """データ形式エラー"""

    def __init__(
        self, 
        message: str = "レスポンスデータの形式が不正です。", 
        **kwargs
    ) -> None:
        super().__init__(message, **kwargs)


class GeospatialError(ReinfiolibAPIError):
    """地理空間データエラー"""

    def __init__(
        self, 
        message: str = "地理空間データの処理でエラーが発生しました。", 
        **kwargs
    ) -> None:
        super().__init__(message, **kwargs)


class ConfigurationError(ReinfiolibAPIError):
    """設定エラー"""

    def __init__(
        self, 
        message: str = "設定に問題があります。", 
        **kwargs
    ) -> None:
        super().__init__(message, **kwargs)

"""Authenticated, stateless backend for the Sites Worker (public read-only data)."""

import hashlib
import hmac
import os

from fastmcp.server.auth import AccessToken, TokenVerifier
from starlette.applications import Starlette

from .mcp_server import create_mcp_server


class ServiceTokenVerifier(TokenVerifier):
    """Verify only the dedicated Worker credential, never a visitor identity."""

    def __init__(self, token: str) -> None:
        super().__init__()
        if len(token) < 32:
            raise ValueError(
                "REINFOLIB_BACKEND_TOKEN must contain at least 32 characters"
            )
        self._digest = hashlib.sha256(token.encode()).digest()

    async def verify_token(self, token: str) -> AccessToken | None:
        if not hmac.compare_digest(
            self._digest, hashlib.sha256(token.encode()).digest()
        ):
            return None
        return AccessToken(token=token, client_id="sites-worker", scopes=[])


def create_app() -> Starlette:
    """Uvicorn factory; fail closed when runtime secrets are absent."""
    verifier = ServiceTokenVerifier(os.environ["REINFOLIB_BACKEND_TOKEN"])
    server = create_mcp_server()
    server.auth = verifier
    server.strict_input_validation = True
    return server.http_app(
        path="/mcp",
        stateless_http=True,
        json_response=True,
        host_origin_protection=True,
        allowed_hosts=[os.environ["REINFOLIB_BACKEND_HOST"]],
        allowed_origins=[],
    )

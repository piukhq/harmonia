import typing as t
from functools import wraps

from azure_oidc import OIDCConfig
from azure_oidc.integrations.flask_decorator import FlaskOIDCAuthDecorator
from flask import request

import settings


class AuthError(Exception):
    """Error type for 401 responses"""


oidc_config = OIDCConfig(
    base_url=f"https://login.microsoftonline.com/{settings.AAD_TENANT_ID}/v2.0",
    issuer=f"https://sts.windows.net/{settings.AAD_TENANT_ID}/",
    audience=settings.AAD_APPLICATION_URI,
)

_requires_auth = None


def _nop_decorator(*args, **kwargs):
    return lambda fn: fn


def auth_decorator() -> t.Callable:
    if settings.API_AUTH_ENABLED is False:
        return _nop_decorator

    global _requires_auth
    if _requires_auth is None:
        _requires_auth = FlaskOIDCAuthDecorator(oidc_config)
    return _requires_auth


def requires_service_auth(fn):
    """
    View decorator that ensures the request has the service API key in the authorization header as follows:
    Token <SERVICE_API_KEY>
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise AuthError("Authorization header is missing")

        prefix, token = auth_header.split(maxsplit=1)
        if prefix.lower() != "token":
            raise AuthError("Authorization header is missing token prefix")

        if token != settings.SERVICE_API_KEY:
            raise AuthError("Invalid token")

        return fn(*args, **kwargs)

    return wrapper

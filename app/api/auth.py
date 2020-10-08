from azure_oidc import OIDCConfig
from azure_oidc.integrations.flask_decorator import FlaskOIDCAuthDecorator

import settings


oidc_config = OIDCConfig(
    base_url=f"https://login.microsoftonline.com/{settings.AAD_TENANT_ID}/v2.0",
    issuer=f"https://sts.windows.net/{settings.AAD_TENANT_ID}/",
    audience=settings.AAD_APPLICATION_URI,
)

_requires_auth = None


def auth_decorator() -> FlaskOIDCAuthDecorator:
    global _requires_auth
    if _requires_auth is None:
        _requires_auth = FlaskOIDCAuthDecorator(oidc_config)
    return _requires_auth

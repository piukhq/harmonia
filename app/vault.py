import json
from functools import cache

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

import settings


@cache
def get_aes_key(secret_name):
    client = connect_to_vault()
    vault_aes_keys = client.get_secret(secret_name).value
    aes_key = json.loads(vault_aes_keys)["AES_KEY"]
    return aes_key.encode()


def connect_to_vault():
    kv_credential = DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_shared_token_cache_credential=True,
        exclude_visual_studio_code_credential=True,
        exclude_interactive_browser_credential=True,
        additionally_allowed_tenants=[settings.AAD_TENANT_ID],
    )
    return SecretClient(vault_url=settings.VAULT_URL, credential=kv_credential)

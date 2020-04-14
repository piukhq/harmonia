from base64 import b64encode, b64decode

import hvac

import settings


class KeyDoesNotExistError(Exception):
    pass


class KeyManager:
    def __init__(self):
        self.client = hvac.Client(url=settings.VAULT_URL, token=settings.VAULT_TOKEN)

    @staticmethod
    def _vault_key_path(slug: str):
        return f"{settings.VAULT_KEY_PREFIX}/key/{slug}"

    def read_key(self, slug: str) -> bytes:
        path = self._vault_key_path(slug)
        key_data = self.client.read(path)
        if key_data is None:
            raise KeyDoesNotExistError(f"No such key: {slug}")
        return b64decode(key_data["data"]["data"])

    def write_key(self, slug: str, key_data: bytes):
        path = self._vault_key_path(slug)
        self.client.write(path, data=b64encode(key_data).decode())

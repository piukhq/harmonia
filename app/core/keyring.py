import typing as t
from base64 import b64encode, b64decode

import hvac

import settings


RING_TYPES = ["pubring.gpg", "secring.gpg", "trustdb.gpg"]


class KeyringDoesNotExistError(Exception):
    pass


class KeyringManager:
    def __init__(self):
        self.client = hvac.Client(url=settings.VAULT_URL, token=settings.VAULT_TOKEN)

    @staticmethod
    def _keyring_path(slug: str):
        return f"secret/keyrings/{slug}"

    def get_keyring(self, slug: str) -> t.Iterator[t.Tuple[str, t.IO]]:
        path = self._keyring_path(slug)
        keyring_data = self.client.read(path)
        if keyring_data is None:
            raise KeyringDoesNotExistError(f"No such keyring: {slug}")
        yield from ((ring_type, b64decode(data)) for ring_type, data in keyring_data["data"]["data"].items())

    def create_keyring(self, slug: str, *, pubring: t.IO, secring: t.IO, trustdb: t.IO):
        ring_files = (
            ("pubring.gpg", pubring),
            ("secring.gpg", secring),
            ("trustdb.gpg", trustdb),
        )
        keyring_data = {ring_type: b64encode(buf.read()).decode() for ring_type, buf in ring_files}
        self.client.write(self._keyring_path(slug), data=keyring_data)

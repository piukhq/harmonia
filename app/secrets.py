import json
from pathlib import Path

import settings


class SecretNotFound(Exception):
    ...


def get(slug: str) -> str:
    path = Path(settings.SECRETS_DIR) / slug
    try:
        return path.read_text()
    except OSError as ex:
        raise SecretNotFound(path) from ex


def get_json(slug: str) -> dict:
    content = get(slug)
    return json.loads(content)

from unittest.mock import Mock

import requests
from requests.models import Response

from app.service.acteol import ActeolAPI


class ActeolMockAPI(ActeolAPI):
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def post(
        self,
        endpoint: str,
        body: dict | None = None,
        *,
        name: str,
    ) -> requests.models.Response:
        response = Mock(spec=Response)
        response.json.return_value = {"Message": "success"}
        response.status_code = 200
        return response

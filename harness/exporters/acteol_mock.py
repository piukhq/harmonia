from unittest.mock import Mock

import requests
from requests.models import Response


class ActeolMockAPI:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def post_matched_transaction(self, body: dict, endpoint: str) -> requests.models.Response:
        response = Mock(spec=Response)
        response.json.return_value = {"Message": "success"}
        response.status_code = 200
        return response

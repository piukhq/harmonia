import requests

from unittest.mock import Mock
from requests.models import Response


class IcelandMockAPI:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def merchant_request(self, request_data) -> requests.Response:
        response = Mock(spec=Response)
        response.json.return_value = ""
        response.status_code = 200
        return response

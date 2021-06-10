import requests

from unittest.mock import Mock
from requests.models import Response


class BplMockAPI:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def post_matched_transaction(self, body: dict) -> requests.models.Response:
        response = Mock(spec=Response)
        response.json.return_value = {"transaction_id": "BPL1234567890", "transaction_status": "awarded"}
        response.status_code = 200
        return response

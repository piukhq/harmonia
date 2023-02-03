from unittest.mock import Mock

import requests
from requests.models import Response

from app.core.requests_retry import requests_retry_session
from app.reporting import get_logger

log = get_logger("acteol")


class ActeolAPI:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests_retry_session()

    def post(self, endpoint: str, body: dict = None, *, name: str) -> requests.models.Response:
        response = Mock(spec=Response)
        response.json.return_value = {"Message": "success"}
        response.status_code = 200
        return response
        # log.debug(f"Posting {name} request with parameters: {body}.")
        # url = f"{self.base_url}{endpoint}"
        # # url = f"http://localhost:6402/mock/api{endpoint}"
        # response = self.session.post(url, json=body)
        # response.raise_for_status()
        # return response

    def post_matched_transaction(self, body: dict, endpoint: str) -> requests.models.Response:
        return self.post(endpoint, body, name="post_matched_transaction")

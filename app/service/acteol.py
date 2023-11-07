import requests

from app.core.requests_retry import requests_retry_session
from app.reporting import get_logger

log = get_logger("acteol")


class InternalError(requests.RequestException):
    def __init__(self):
        super().__init__("atreemo raised an internal error")


class ActeolAPI:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests_retry_session()

    def post(self, endpoint: str, body: dict = None, *, name: str) -> requests.models.Response:
        log.debug(f"Posting {name} request with parameters: {body}.")
        url = f"{self.base_url}{endpoint}"
        response = self.session.post(url, json=body)
        response.raise_for_status()
        json = response.json()
        if json.get("ResponseStatus") is False and json["Errors"][0]["ErrorDescription"] == "Internal Error":
            raise InternalError
        return response

    def post_matched_transaction(self, body: dict, endpoint: str) -> requests.models.Response:
        return self.post(endpoint, body, name="post_matched_transaction")

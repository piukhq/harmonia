from urllib.parse import urljoin

from app.core.requests_retry import requests_retry_session
from app.reporting import get_logger
import settings


log = get_logger("hermes")


class Hermes:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests_retry_session()

    @staticmethod
    def _format_slug(slug: str) -> str:
        if settings.HERMES_SLUG_FORMAT_STRING is not None:
            slug = settings.HERMES_SLUG_FORMAT_STRING.format(slug)
        return slug

    def post(self, endpoint: str, body: dict = None, *, name: str) -> dict:
        log.debug(f"Posting {name} request with parameters: {body}.")
        url = urljoin(self.base_url, endpoint)
        response = self.session.post(url, json=body)
        response.raise_for_status()
        return response.json()

    def payment_card_user_info(self, loyalty_scheme_slug: str, payment_card_token: str) -> dict:
        loyalty_scheme_slug = self._format_slug(loyalty_scheme_slug)
        endpoint = f"/payment_cards/accounts/payment_card_user_info/{loyalty_scheme_slug}"
        return self.post(endpoint, {"payment_cards": [payment_card_token]}, name="payment card user info")

    def create_join_scheme_account(self, loyalty_scheme_slug: str, user_id: int) -> dict:
        loyalty_scheme_slug = self._format_slug(loyalty_scheme_slug)
        endpoint = f"/accounts/join/{loyalty_scheme_slug}/{user_id}"
        return self.post(endpoint, name="create join scheme account")


hermes = Hermes(settings.HERMES_URL)

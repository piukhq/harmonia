from enum import Enum

from app.core.requests_retry import requests_retry_session
from app.reporting import get_logger
import settings


log = get_logger("hermes")


class PaymentProviderSlug(str, Enum):
    AMEX = "amex"
    VISA = "visa"
    MASTERCARD = "mastercard"
    BINK_PAYMENT = "bink-payment"


class Hermes:
    def __init__(self, base_url: str) -> None:
        if not settings.HERMES_URL:
            raise settings.ConfigVarRequiredError("Use of the Hermes service class requires that HERMES_URL is set.")

        self.base_url = base_url
        self.session = requests_retry_session(retries=5)

        self._headers = {"Authorization": f"Token {settings.SERVICE_API_KEY}"}

    @staticmethod
    def _format_slug(slug: str) -> str:
        if slug in settings.HERMES_SLUGS_TO_FORMAT and settings.HERMES_SLUG_FORMAT_STRING is not None:
            slug = settings.HERMES_SLUG_FORMAT_STRING.format(slug)
        return slug

    def post(self, endpoint: str, body: dict = None, *, name: str) -> dict:
        log.debug(f"Posting {name} request with parameters: {body}.")
        url = f"{self.base_url}{endpoint}"
        response = self.session.post(url, json=body, headers=self._headers)
        log.debug(f"Response to {name} request: {response.status_code} {response.reason}")
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

from app.core.requests_retry import requests_retry_session, requests
from app.reporting import get_logger
import settings


log = get_logger("hermes")


class Hermes:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests_retry_session()

    def payment_card_user_info(
        self, loyalty_scheme_slug: str, payment_card_token: str
    ) -> requests.Response:
        log.debug(
            f"Sending payment card user info request for loyalty scheme {loyalty_scheme_slug} and payment card token "
            f"{payment_card_token}."
        )
        return self.session.post(
            f"{self.base_url}/payment_cards/accounts/payment_card_user_info/{loyalty_scheme_slug}",
            json={"payment_cards": [payment_card_token]},
        )


hermes = Hermes(settings.HERMES_URL)

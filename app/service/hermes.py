from app.core.requests_retry import requests_retry_session, requests
import settings


class Hermes:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests_retry_session()

    def payment_card_user_info(
        self, loyalty_scheme_slug: str, payment_card_token: str
    ) -> requests.Response:
        return self.session.post(
            f"{self.base_url}/payment_cards/accounts/payment_card_user_info/{loyalty_scheme_slug}",
            json={"payment_cards": [payment_card_token]},
        )


hermes = Hermes(settings.HERMES_URL)

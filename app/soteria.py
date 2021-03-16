import settings

from soteria.configuration import Configuration


class SoteriaConfigMixin:
    def get_soteria_config(self):
        if settings.EUROPA_URL is None:
            raise settings.ConfigVarRequiredError(f"The {self.provider_slug} agent requires the Europa URL to be set.")

        if settings.VAULT_URL is None or settings.VAULT_TOKEN is None:
            raise settings.ConfigVarRequiredError(
                f"The {self.provider_slug} agent requires both the Vault URL and token to be set."
            )

        return Configuration(
            self.provider_slug,
            Configuration.TRANSACTION_MATCHING,
            settings.VAULT_URL,
            settings.VAULT_TOKEN,
            settings.EUROPA_URL,
        )

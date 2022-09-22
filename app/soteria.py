from soteria.configuration import Configuration

import settings


class SoteriaConfigMixin:
    def get_soteria_config(self):
        if settings.EUROPA_URL is None:
            raise settings.ConfigVarRequiredError(f"The {self.provider_slug} agent requires the Europa URL to be set.")

        if settings.VAULT_URL is None:
            raise settings.ConfigVarRequiredError(f"The {self.provider_slug} agent requires VAULT_URL to be set.")

        return Configuration(
            self.provider_slug,
            Configuration.TRANSACTION_MATCHING,
            settings.VAULT_URL,
            None,
            settings.EUROPA_URL,
            settings.AAD_TENANT_ID,
        )

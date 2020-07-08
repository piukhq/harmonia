import typing as t

from copy import deepcopy


class BaseImportDataProvider:
    def provide(self, fixture: dict) -> t.Any:
        raise NotImplementedError("provide(fixture) must be overridden by subclasses!")

    def apply_merchant_overrides(self, fixture: dict) -> dict:
        return self._apply_overrides(fixture, field_name="merchant_overrides")

    def apply_payment_provider_overrides(self, fixture: dict) -> dict:
        return self._apply_overrides(fixture, field_name="payment_provider_overrides")

    def _apply_overrides(self, fixture: dict, *, field_name: str) -> dict:
        fixture = deepcopy(fixture)
        for user in fixture["users"]:
            for transaction in user["transactions"]:
                if field_name not in transaction:
                    continue

                for k, v in transaction[field_name].items():
                    transaction[k] = v

        return fixture

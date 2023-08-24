import pendulum
import time_machine

import settings
from app.exports.agents.wasabi import Wasabi

settings.EUROPA_URL = "http://europa"
settings.VAULT_URL = "https://vault"


# Tests that the next available retry time, in this case 7AM on the same day, works for a 5AM transaction.
@time_machine.travel(pendulum.datetime(2020, 1, 4, 5, 0, 1, 0, pendulum.UTC))
def test_next_available_retry_time() -> None:
    wasabi = Wasabi()

    retry_time = wasabi.next_available_retry_time(7)
    assert retry_time.to_datetime_string() == pendulum.datetime(2020, 1, 4, 7, 0, 0).to_datetime_string()


# Tests that the next available retry time, in this case 7AM on the following day, works for a 9AM transaction.
@time_machine.travel(pendulum.datetime(2020, 1, 4, 9, 0, 1, 0, pendulum.UTC))
def test_next_day_available_retry_time() -> None:
    wasabi = Wasabi()

    retry_time = wasabi.next_available_retry_time(7)
    assert retry_time.to_datetime_string() == pendulum.datetime(2020, 1, 5, 7, 0, 0).to_datetime_string()

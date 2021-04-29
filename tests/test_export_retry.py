import pendulum

from freezegun import freeze_time

import settings
from app.exports.agents.wasabi import Wasabi

settings.EUROPA_URL = "http://europa"
settings.ATLAS_URL = "http://atlas"
settings.VAULT_URL = "https://vault"
settings.VAULT_TOKEN = ""


# Tests that the next available retry time, in this case 7AM on the same day, works for a 5AM transaction.
def test_next_available_retry_time() -> None:
    wasabi = Wasabi()

    freezer = freeze_time("2020-01-04 05:00:01", tz_offset=0)
    freezer.start()
    retry_time = wasabi.next_available_retry_time(7)
    assert retry_time.to_datetime_string() == pendulum.datetime(2020, 1, 4, 7, 0, 0).to_datetime_string()
    freezer.stop()


# Tests that the next available retry time, in this case 7AM on the following day, works for a 9AM transaction.
def test_next_day_available_retry_time() -> None:
    wasabi = Wasabi()

    freezer = freeze_time("2020-01-04 09:00:01", tz_offset=0)
    freezer.start()
    retry_time = wasabi.next_available_retry_time(7)
    assert retry_time.to_datetime_string() == pendulum.datetime(2020, 1, 5, 7, 0, 0).to_datetime_string()
    freezer.stop()

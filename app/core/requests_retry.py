import typing as t

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


def requests_retry_session(
    retries: int = 3,
    backoff_factor: float = 0.3,
    status_forcelist: t.Tuple = (500, 502, 504),
    session: requests.Session = None,
) -> requests.Session:
    """Create a requests session with the given retry policy.
    This method will create a new session if an existing one is not provided.
    See here for more information about this functionality:
    https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html?highlight=forcelist#urllib3.util.retry.Retry"""
    if session is None:
        session = requests.Session()

    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )

    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session

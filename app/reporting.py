import logging

import settings


logging.basicConfig(
    level=getattr(settings, "LOG_LEVEL", logging.INFO), format="%(asctime)s | %(name)24s | %(levelname)8s | %(message)s"
)


def get_logger(name: str) -> logging.Logger:
    """
    Returns a correctly configured logger with the given name.
    """
    return logging.getLogger(name.lower().replace(" ", "-"))

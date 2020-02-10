import logging

import settings


LOG_LEVEL = getattr(settings, "LOG_LEVEL", logging.INFO)
LOG_FORMAT = "%(asctime)s | %(name)26s | %(levelname)8s | %(message)s"


def get_logger(name: str) -> logging.Logger:
    """
    Returns a correctly configured logger with the given name.
    """
    logger = logging.getLogger(name.lower().replace(" ", "-"))
    logger.propagate = False

    formatter = logging.Formatter(LOG_FORMAT)

    handler = logging.StreamHandler()
    handler.setLevel(LOG_LEVEL)
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.setLevel(LOG_LEVEL)

    return logger

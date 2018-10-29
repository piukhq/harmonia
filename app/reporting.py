import logging

import settings

logging.basicConfig(
    level=getattr(settings, 'LOG_LEVEL', logging.INFO),
    format='%(asctime)s :: %(name)s :: %(levelname)s :: %(message)s')


def get_logger(tag: str) -> logging.Logger:
    """
    Returns a correctly configured logger for the given logging tag string.
    """
    return logging.getLogger('txmatch.{}'.format(tag.lower()))

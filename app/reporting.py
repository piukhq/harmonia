import logging

import settings

logging.basicConfig(
    level=getattr(settings, 'LOG_LEVEL', logging.INFO),
    format='%(asctime)s :: %(name)s :: %(levelname)s :: %(message)s')


def get_logger(tag):
    """
    Returns a configured logger for the given logging tag string.
    """
    assert len(tag) == 4, 'Logging tags must be exactly 4 characters long'
    return logging.getLogger('txmatch.{}'.format(tag.lower()))

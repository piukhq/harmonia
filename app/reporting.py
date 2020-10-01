import io
import logging

import settings

LOG_FORMAT = "%(asctime)s | %(levelname)8s | %(name)s\n%(message)s"  # only used if JSON logging is disabled.


class JSONFormatter(logging.Formatter):
    def __init__(self):
        if settings.DEVELOPMENT is True:
            from prettyprinter import cpprint

            self._cpprint = cpprint
            self._format_fn = self._format_with_colour
        else:
            import json

            self._format_fn = json.dumps

    def _format_with_colour(self, values: dict) -> str:
        buf = io.StringIO()
        self._cpprint(values, stream=buf, width=120, end="")
        return buf.getvalue()

    def format(self, record):
        return self._format_fn(
            {
                "timestamp": record.created,
                "level": record.levelno,
                "levelname": record.levelname,
                "process": record.processName,
                "thread": record.threadName,
                "file": record.pathname,
                "line": record.lineno,
                "module": record.module,
                "function": record.funcName,
                "name": record.name,
                "message": record.msg,
            }
        )


def get_logger(name: str) -> logging.Logger:
    """
    Returns a correctly configured logger with the given name.
    """
    logger = logging.getLogger(name.lower().replace(" ", "-"))

    # if this logger is already configured, return it now
    if logger.handlers:
        return logger

    logger.propagate = False

    formatter: logging.Formatter
    if settings.LOG_JSON:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(LOG_FORMAT)

    handler = logging.StreamHandler()
    handler.setLevel(settings.LOG_LEVEL)
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.setLevel(settings.LOG_LEVEL)

    return logger

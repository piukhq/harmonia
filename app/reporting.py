import copy
import io
import logging

import settings

LOG_FORMAT = "%(levelname)8s | %(name)s | %(message)s"  # used if JSON logging is disabled.

SENSITIVE_KEYS = {"the-works": {"request": [2, 3], "response": [6]}}


def sanitise_jsonrpc(data, sensitive_keys):
    if data.get("params"):
        sensitive_keys = sensitive_keys["request"]
        log_type = "params"
    else:
        sensitive_keys = sensitive_keys["response"]
        log_type = "result"

    body = copy.deepcopy(data)

    for index in sensitive_keys:
        try:
            body[log_type][index] = "*****"
        except IndexError:
            pass
    return body


def sanitise_logs(data, merchant_slug):
    if data is None or not isinstance(data, dict):
        return data
    if data.get("export.json"):
        data = data["export.json"]
    if data.get("jsonrpc"):
        return sanitise_jsonrpc(data, sensitive_keys=SENSITIVE_KEYS[merchant_slug])
    return data


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

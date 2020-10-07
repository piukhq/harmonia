import collections
import os
import threading
import time
import typing as t
import urllib.error

import settings
from app.reporting import get_logger
from prometheus_client import Counter, Gauge, Histogram, push_to_gateway
from prometheus_client.registry import REGISTRY

logger = get_logger(__name__)


class BinkPrometheus:
    """
    Provides global access to Prometheus metric types through a singleton
    """

    # Enable merchants' exports (by slug) that we want to monitor stats for
    merchant_slugs_export = [
        "harvey-nichols",
        "iceland-bonus-card",
        "wasabi-club",
        "bink-loyalty",
    ]
    # Enable merchants' imports (by slug) that we want to monitor stats for
    merchant_slugs_import = [
        "wasabi-club",
        "visa",
    ]

    def _make_metric_types_dict(self):
        """
        Create an auto-vivified dict
        """
        return collections.defaultdict(self._make_metric_types_dict)

    def _get_metric_types(self) -> t.Dict:
        metric_types = self._make_metric_types_dict()

        # Export section
        for merchant_slug in self.merchant_slugs_export:
            merchant_name = merchant_slug.replace("-", "_")  # Can't use dashes in name
            metric_types["export"][merchant_slug] = {
                "counter": {
                    "transactions": Counter(
                        f"exported_transactions_{merchant_name}", f"Number of transactions sent to {merchant_slug}",
                    ),
                    "requests_sent": Counter(
                        f"requests_sent_{merchant_name}", f"Number of requests sent to {merchant_slug}",
                    ),
                    "failed_requests": Counter(
                        f"failed_requests_{merchant_name}", f"Number of failed requests to {merchant_slug}",
                    ),
                },
                "histogram": {
                    "request_latency": Histogram(
                        f"request_latency_seconds_{merchant_name}", f"Request latency seconds for {merchant_slug}",
                    )
                },
            }

        # Import section
        for merchant_slug in self.merchant_slugs_import:
            merchant_name = merchant_slug.replace("-", "_")  # Can't use dashes in name
            metric_types["import"][merchant_slug] = {
                "counter": {
                    "transactions": Counter(
                        f"imported_transactions_{merchant_name}", f"Number of transactions imported to {merchant_slug}",
                    ),
                    "settlement_transactions": Counter(
                        f"imported_settlement_transactions_{merchant_name}",
                        f"Number of settlement transactions imported to {merchant_slug}",
                    ),
                    "files_received": Counter(
                        f"files_received_{merchant_name}", f"Number of files received by {merchant_slug}",
                    ),
                },
                "gauge": {
                    "last_file_timestamp": Gauge(
                        f"last_file_timestamp_{merchant_name}", f"Timestamp of last file processed for {merchant_slug}",
                    )
                },
            }

        return metric_types

    @staticmethod
    def increment_counter(obj: object, counter_name: str, increment_by: t.Union[int, float]) -> None:
        """
        Useful function for getting an instance's counter, if it exists,
        and incrementing it
        """
        counter = getattr(obj, counter_name, None)
        if counter:
            counter.inc(increment_by)

    @staticmethod
    def update_gauge(obj: object, gauge_name: str, value: t.Union[int, float]) -> None:
        """
        Useful function for getting an instance's gauge, if it exists,
        and setting it to a value
        """
        gauge = getattr(obj, gauge_name, None)
        if gauge:
            gauge.set(value)


# Singleton metric types
prometheus_metric_types = BinkPrometheus()._get_metric_types()


class PrometheusPushThread(threading.Thread):
    """
    Thread daemon to push to Prometheus gateway
    """

    SLEEP_INTERVAL = 30
    PUSH_TIMEOUT = 3  # PushGateway should be running in the same pod

    def __init__(self, process_id: str, prometheus_push_gateway: str, prometheus_job: str):
        # Grouping key should not need pod id as prometheus
        # should tag that itself
        self.grouping_key = {"pid": process_id}
        self.prometheus_push_gateway = prometheus_push_gateway
        self.prometheus_job = prometheus_job
        super().__init__()

    def run(self):
        time.sleep(10)
        while True:
            now = time.time()
            try:
                push_to_gateway(
                    gateway=self.prometheus_push_gateway,
                    job=self.prometheus_job,
                    registry=REGISTRY,
                    grouping_key=self.grouping_key,
                    timeout=self.PUSH_TIMEOUT,
                )
                logger.info("Pushed metrics to gateway")
            except (ConnectionRefusedError, urllib.error.URLError):
                logger.warning("Failed to push metrics, connection refused")
            except Exception as err:
                logger.exception("Caught exception whilst posting metrics", exc_info=err)

            remaining = self.SLEEP_INTERVAL - (time.time() - now)
            if remaining > 0:
                time.sleep(remaining)


def get_prometheus_thread():
    """
    The PrometheusPushThread class may well end up in an imported common lib
    """
    process_id = str(os.getpid())
    prometheus_thread = PrometheusPushThread(
        process_id=process_id,
        prometheus_push_gateway=settings.PROMETHEUS_PUSH_GATEWAY,
        prometheus_job=settings.PROMETHEUS_JOB,
    )
    prometheus_thread.daemon = True

    return prometheus_thread


# Singleton thread
prometheus_thread = get_prometheus_thread()

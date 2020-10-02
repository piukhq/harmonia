import collections
import threading
import time
import urllib.error
from typing import Dict

from app.reporting import get_logger
from prometheus_client import Counter, Histogram, push_to_gateway
from prometheus_client.registry import REGISTRY

logger = get_logger(__name__)


class PrometheusMetricTypes:
    merchant_slugs = [
        "harvey-nichols",
        "iceland-bonus-card",
        "wasabi-club",
        "bink-loyalty",
    ]

    def _make_metric_types_dict(self):
        # Create an auto-vivified dict
        return collections.defaultdict(self._make_metric_types_dict)

    def get_metric_types(self) -> Dict:
        metric_types = self._make_metric_types_dict()

        for merchant_slug in self.merchant_slugs:
            merchant_name = merchant_slug.replace("-", "_")
            metric_types["export"][merchant_slug] = {
                "counter": {
                    "transactions": Counter(
                        f"exported_transactions_{merchant_name}",
                        f"Number of transactions sent to {merchant_name}",
                    ),
                    "requests_sent": Counter(
                        f"requests_sent_{merchant_name}",
                        f"Number of requests sent to {merchant_name}",
                    ),
                    "failed_requests": Counter(
                        f"failed_requests_{merchant_name}",
                        f"Number of failed requests to {merchant_name}",
                    ),
                },
                "histogram": {
                    "request_latency": Histogram(
                        f"request_latency_seconds_{merchant_name}",
                        f"Request latency seconds for {merchant_name}",
                    )
                },
            }

        return metric_types


prometheus_metric_types = PrometheusMetricTypes().get_metric_types()


class PrometheusPushThread(threading.Thread):
    SLEEP_INTERVAL = 30
    PUSH_TIMEOUT = 3  # PushGateway should be running in the same pod

    def __init__(
        self, process_id: str, prometheus_push_gateway: str, prometheus_job: str
    ):
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
                logger.exception(
                    "Caught exception whilst posting metrics", exc_info=err
                )

            remaining = self.SLEEP_INTERVAL - (time.time() - now)
            if remaining > 0:
                time.sleep(remaining)

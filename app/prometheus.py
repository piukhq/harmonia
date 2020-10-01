import threading
import time
import urllib.error

from app.reporting import get_logger
from prometheus_client import push_to_gateway
from prometheus_client.registry import REGISTRY

logger = get_logger(__name__)


class PrometheusPushThread(threading.Thread):
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
                    timeout=self.PUSH_TIMEOUT
                )
                logger.info("Pushed metrics to gateway")
            except (ConnectionRefusedError, urllib.error.URLError):
                logger.warning("Failed to push metrics, connection refused")
            except Exception as err:
                logger.exception("Caught exception whilst posting metrics", exc_info=err)

            remaining = self.SLEEP_INTERVAL - (time.time() - now)
            if remaining > 0:
                time.sleep(remaining)

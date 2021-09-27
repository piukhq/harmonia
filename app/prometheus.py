import os
import threading
import typing as t
from contextlib import ExitStack

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)
from prometheus_client.exposition import ThreadingWSGIServer, _SilentHandler, make_server
from prometheus_client.registry import REGISTRY

from app.reporting import get_logger

logger = get_logger(__name__)


class BinkPrometheus:
    def __init__(self):
        self.metric_types = self._get_metric_types()

    def _get_metric_types(self) -> t.Dict:
        """
        Define globally available metric types here (see https://prometheus.io/docs/concepts/metric_types/),
        with the name, description and a list of the labels they expect.

        Agents register the metrics they care about like this:

        self.prometheus_metrics = {
            "counters": ["requests_sent", "failed_requests", "transactions"],
            "histograms": ["request_latency"],
        }

        It's the labels (e.g. transaction_type, slug), passed as parameters when a metric is updated, that determine
        things like whether it's an export or import, or auth or transaction, as well as the slug for the agent.
        """
        metric_types = {
            "counters": {
                "transactions": Counter(
                    name="transactions",
                    documentation="Number of transactions",
                    labelnames=("transaction_type", "process_type", "slug"),
                ),
                "requests_sent": Counter(
                    name="requests_sent",
                    documentation="Number of requests sent",
                    labelnames=("transaction_type", "process_type", "slug"),
                ),
                "failed_requests": Counter(
                    name="failed_requests",
                    documentation="Number of failed requests",
                    labelnames=("transaction_type", "process_type", "slug", "response_result"),
                ),
                "files_received": Counter(
                    name="files_received",
                    documentation="Number of files received",
                    labelnames=("transaction_type", "process_type", "slug"),
                ),
            },
            "histograms": {
                "request_latency": Histogram(
                    name="request_latency_seconds",
                    documentation="Request latency seconds",
                    labelnames=("process_type", "slug"),
                )
            },
            "gauges": {
                "last_file_timestamp": Gauge(
                    name="last_file_timestamp",
                    documentation="Timestamp of last file processed",
                    labelnames=("process_type", "slug"),
                )
            },
        }

        return metric_types

    def increment_counter(
        self,
        agent: object,
        counter_name: str,
        increment_by: t.Union[int, float],
        transaction_type: t.Optional[str] = "",
        process_type: t.Optional[str] = "",
        slug: t.Optional[str] = "",
        **kwargs
    ) -> None:
        """
        Useful method for getting an instance's counter, if it exists,
        and incrementing it

        :param agent: instance of an agent
        :param counter_name: e.g. 'requests_sent'
        :param increment_by: increment by this number
        :param transaction_type: e.g auth or settlement
        :param process_type: e.g import or export
        :param slug: e.g wasabi-club, visa
        :param response_result: The response code returned from merchant receiving txns
        """

        agent_metrics = getattr(agent, "prometheus_metrics", None)
        if agent_metrics:
            if counter_name in agent_metrics.get("counters", []):
                labels = {"transaction_type": transaction_type, "process_type": process_type, "slug": slug}
                labels.update(kwargs)
                self.metric_types["counters"][counter_name].labels(**labels).inc(increment_by)

    def update_gauge(
        self,
        agent: object,
        gauge_name: str,
        value: t.Union[int, float],
        process_type: t.Optional[str] = "",
        slug: t.Optional[str] = "",
    ) -> None:
        """
        Useful method for getting an instance's gauge, if it exists,
        and setting it to a value

        :param agent: instance of an agent
        :param gauge_name: e.g. 'last_file_timestamp'
        :param value: set to this number
        :param process_type: e.g import or export
        :param slug: e.g wasabi-club, visa
        """
        agent_metrics = getattr(agent, "prometheus_metrics", None)
        if agent_metrics:
            if gauge_name in agent_metrics.get("gauges", []):
                self.metric_types["gauges"][gauge_name].labels(process_type=process_type, slug=slug).set(value)

    def use_histogram_context_manager(
        self,
        agent: object,
        histogram_name: str,
        context_manager_stack: ExitStack,
        process_type: t.Optional[str] = "",
        slug: t.Optional[str] = "",
    ) -> None:
        """
        Useful method for using an instance's histogram CM, if it exists,
        by appending it to a CM stack

        :param agent: instance of an agent
        :param histogram_name: e.g. 'request_latency'
        :param context_manager_stack: a contextlib ExitStack instance
        :param process_type: e.g import or export
        :param slug: e.g wasabi-club, visa
        """
        agent_metrics = getattr(agent, "prometheus_metrics", None)
        if agent_metrics:
            if histogram_name in agent_metrics.get("histograms", []):
                context_manager = self.metric_types["histograms"]["request_latency"]
                context_manager_stack.enter_context(context_manager.labels(process_type=process_type, slug=slug).time())


# Singleton metric types
bink_prometheus = BinkPrometheus()


def get_prometheus_thread() -> threading.Thread:
    def prometheus_app(environ, start_response):
        registry = REGISTRY

        if os.getenv("PROMETHEUS_MULTIPROC_DIR"):
            registry = CollectorRegistry()
            multiprocess.MultiProcessCollector(registry)

        header = ("Content-Type", CONTENT_TYPE_LATEST)
        output = generate_latest(registry)
        start_response(200, [header])
        return [output]

    httpd = make_server("", 9100, prometheus_app, ThreadingWSGIServer, handler_class=_SilentHandler)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.daemon = True

    return thread


# Singleton thread
prometheus_thread = get_prometheus_thread()

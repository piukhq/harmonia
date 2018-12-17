from time import sleep

from redis import StrictRedis
import pendulum

import settings
from app.matching import retry
from app.reporting import get_logger
from app.queues import matching_queue


class MatchingRetryWorker:
    def __init__(
        self, name: str, debug: bool = False, redis: StrictRedis = None
    ) -> None:
        self.name = name
        self.debug = debug
        self.log = get_logger(f"matching-retry-worker.{self.name}")

        if redis is not None:
            self.redis = redis
        else:
            self.redis = StrictRedis.from_url(settings.REDIS_DSN)

        if self.debug:
            self.log.warning(
                "Running in debug mode. Exceptions will not be handled gracefully!"
            )

    def tick(self) -> None:
        now = pendulum.now().int_timestamp

        for payment_tx_id, entry in retry.all():
            if now >= entry.retry_at:
                self.log.info(
                    f"Payment transaction #{payment_tx_id} is due for retry. Re-queueing…"
                )
                retry.clear(payment_tx_id)
                matching_queue.push(
                    obj={"payment_transaction_id": payment_tx_id},
                    override_headers={
                        "X-Queued-At": entry.queued_at,
                        "X-Retried-At": now,
                        "X-Retry-Count": entry.retry_count + 1,
                    },
                )
            else:
                friendly_retry = pendulum.from_timestamp(entry.retry_at)
                self.log.debug(
                    f"Payment transaction #{payment_tx_id} will be retried at {friendly_retry}."
                )

    def enter_loop(self) -> None:
        self.log.info(f"Started.")
        while True:
            try:
                self.tick()
            except Exception as ex:
                if self.debug is True:
                    raise ex
                else:
                    self.log.error(ex)
            sleep(30)

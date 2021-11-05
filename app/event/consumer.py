from typing import Optional

from azure.eventhub import EventData, EventHubConsumerClient, PartitionContext
from azure.eventhub.extensions.checkpointstoreblob import BlobCheckpointStore


class Consumer:
    def __init__(
        self,
        blob_storage_dsn: str,
        blob_container_name: str,
        event_hub_dsn: str,
        event_hub_name: str,
    ) -> None:
        self.checkpoint_store = BlobCheckpointStore.from_connection_string(  # type: ignore
            blob_storage_dsn, blob_container_name
        )
        self.client = EventHubConsumerClient.from_connection_string(
            event_hub_dsn,
            consumer_group="$Default",
            eventhub_name=event_hub_name,
            checkpoint_store=self.checkpoint_store,
        )

    def __enter__(self) -> "Consumer":
        self.client.__enter__()
        return self

    def __exit__(self, *args) -> None:
        self.client.__exit__(*args)

    def consume(self) -> None:
        print("Starting consumer loop...")
        self.client.receive(
            on_event=self.on_event,
            starting_position="-1",
        )

    @staticmethod
    def on_event(partition_context: PartitionContext, event: Optional[EventData]) -> None:
        if event:
            print(f'Received event "{event.body_as_str()}"', end="")
        else:
            print("Received null event", end="")
        print(f" from partition {partition_context.partition_id}")
        partition_context.update_checkpoint(event)

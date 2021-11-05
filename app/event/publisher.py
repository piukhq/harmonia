from azure.eventhub import EventData, EventHubProducerClient


class Publisher:
    def __init__(self, event_hub_dsn: str, event_hub_name: str) -> None:
        self.client = EventHubProducerClient.from_connection_string(event_hub_dsn, eventhub_name=event_hub_name)

    def __enter__(self) -> "Publisher":
        self.client.__enter__()
        return self

    def __exit__(self, *args) -> None:
        self.client.__exit__(*args)

    def send(self, event_name: str) -> None:
        print(f'Sending event "{event_name}"...')
        batch = self.client.create_batch()
        batch.add(EventData(event_name))
        self.client.send_batch(batch)

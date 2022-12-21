import fakeredis

import pytest
from app.tasks import LoggedQueue, TasksRedisException


def do_a_job():
    return "job done"


def test_enqueue_exception() -> None:
    server = fakeredis.FakeServer()
    # Make the fake redis server have a connection failure
    server.connected = False
    test_queue = LoggedQueue(name="testing", connection=fakeredis.FakeRedis(server=server))

    with pytest.raises(TasksRedisException):
        test_queue.enqueue(do_a_job, 'test_thing')

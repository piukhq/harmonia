import time

from app.scheduler import CronScheduler


def tick():
    print("i'm the leader!")


scheduler = CronScheduler(name="test-scheduler", schedule_fn=lambda: "* * * * *", callback=tick)
scheduler.run()
while True:
    time.sleep(1)

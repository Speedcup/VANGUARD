import os

import requests
from interactions import Extension, Task, IntervalTrigger


class Uptime(Extension):
    async def async_start(self):
        if self.client.debug:
            self.client.logger.info("Debugging Mode, cancelling uptime heartbeats.")
            return

        # Automatically trigger once so we don't get a gap after restarting while waiting for the first trigger.
        await self.send_heartbeat()
        self.send_heartbeat.start()

    @Task.create(IntervalTrigger(minutes=1))
    async def send_heartbeat(self):
        requests.get(
            f"https://uptime.betterstack.com/api/v1/heartbeat/{os.environ.get("UPTIME_TOKEN")}"
        )
        self.client.logger.debug("Status Heartbeat sent!")

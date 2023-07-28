import asyncio
import logging
from server.util.constants import EVENTS_CHANNEL
from quart import Quart
from server.blueprints.sse import sse
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.getLogger("apscheduler.executors.default").setLevel(logging.ERROR)


async def keep_alive(app: Quart):
    async with app.app_context():
        await sse.publish("\n\n", type="keepalive", channel=EVENTS_CHANNEL)


def start_keepalive(app: Quart):
    loop = asyncio.get_event_loop()
    sched = AsyncIOScheduler(event_loop=loop)
    sched.add_job(keep_alive, "interval", seconds=15, args=(app,))
    sched.start()

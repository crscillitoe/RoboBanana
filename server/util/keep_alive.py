import asyncio
import logging
from server.util.constants import (
    COOL_CHANNEL,
    POLL_ANSWERS_CHANNEL,
    POLLS_CHANNEL,
    PREDICTIONS_CHANNEL,
    SUBS_CHANNEL,
    SUBS_COUNT_CHANNEL,
    TAMAGACHI_CHANNEL,
    TIMER_CHANNEL,
    VOD_REVIEW_CHANNEL,
)
from quart import Quart
from server.blueprints.sse import sse
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.getLogger("apscheduler.executors.default").setLevel(logging.ERROR)


async def keep_alive(app: Quart):
    async with app.app_context():
        await sse.publish("\n\n", type="keepalive", channel=PREDICTIONS_CHANNEL)
        await sse.publish("\n\n", type="keepalive", channel=SUBS_CHANNEL)
        await sse.publish("\n\n", type="keepalive", channel=POLL_ANSWERS_CHANNEL)
        await sse.publish("\n\n", type="keepalive", channel=POLLS_CHANNEL)
        await sse.publish("\n\n", type="keepalive", channel=COOL_CHANNEL)
        await sse.publish("\n\n", type="keepalive", channel=SUBS_COUNT_CHANNEL)
        await sse.publish("\n\n", type="keepalive", channel=TIMER_CHANNEL)
        await sse.publish("\n\n", type="keepalive", channel=VOD_REVIEW_CHANNEL)
        await sse.publish("\n\n", type="keepalive", channel=TAMAGACHI_CHANNEL)


def start_keepalive(app: Quart):
    loop = asyncio.get_event_loop()
    sched = AsyncIOScheduler(event_loop=loop)
    sched.add_job(keep_alive, "interval", seconds=15, args=(app,))
    sched.start()

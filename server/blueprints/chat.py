from server.util.constants import (
    CHAT_MESSAGE_TEST_TYPE,
    CHAT_MESSAGE_STREAM_TYPE,
    EVENTS_CHANNEL,
)
from .sse import sse


async def publish_chat(chat_message, stream):
    try:
        if not stream:
            await sse.publish(
                chat_message, type=CHAT_MESSAGE_TEST_TYPE, channel=EVENTS_CHANNEL
            )
        else:
            await sse.publish(
                chat_message, type=CHAT_MESSAGE_STREAM_TYPE, channel=EVENTS_CHANNEL
            )
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)

from quart import Blueprint, request
from server.util.token_required import token_required
from server.util.constants import (
    CHAT_MESSAGE_TEST_TYPE,
    CHAT_MESSAGE_STREAM_TYPE,
    EVENTS_CHANNEL,
)
from .sse import sse
import re
import logging

LOG = logging.getLogger(__name__)

CUSTOM_EMOJI_PATTERN = re.compile(r"<:[a-zA-Z]+:[0-9]+>")

chat_blueprint = Blueprint("chat", __name__)


@chat_blueprint.route("/publish-chat", methods=["POST"])
@token_required
async def receive_chat():
    try:
        LOG.info("received chat message")
        json = await request.get_json()
        await sse.publish(json, type=CHAT_MESSAGE_STREAM_TYPE, channel=EVENTS_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)


async def publish_chat(chat_message):
    try:
        await sse.publish(
            chat_message, type=CHAT_MESSAGE_STREAM_TYPE, channel=EVENTS_CHANNEL
        )
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)

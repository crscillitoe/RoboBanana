from quart import Blueprint, request
from server.util.token_required import token_required
from server.util.constants import STREAMDECK_TYPE, EVENTS_CHANNEL
from .sse import sse
import logging

streamdeck_blueprint = Blueprint("streamdeck", __name__)

LOG = logging.getLogger(__name__)


@streamdeck_blueprint.route("/publish-streamdeck", methods=["POST"])
@token_required
async def publish_streamdeck():
    try:
        request_json = await request.get_json()
        await sse.publish(request_json, type=STREAMDECK_TYPE, channel=EVENTS_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)

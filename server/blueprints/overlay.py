from quart import Blueprint, request
from server.util.token_required import token_required
from server.util.constants import OVERLAY_TYPE, EVENTS_CHANNEL
from .sse import sse
import logging

overlay_blueprint = Blueprint("overlay", __name__)

LOG = logging.getLogger(__name__)


@overlay_blueprint.route("/publish-overlay", methods=["PATCH"])
@token_required
async def publish_overlay():
    try:
        request_json = await request.get_json()
        await sse.publish(request_json, type=OVERLAY_TYPE, channel=EVENTS_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)

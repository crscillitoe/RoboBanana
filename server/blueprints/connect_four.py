from quart import Blueprint, request
from server.util.token_required import token_required
from server.util.constants import CONNECT_FOUR_TYPE, EVENTS_CHANNEL
from .sse import sse

connect_four_blueprint = Blueprint("connect-four", __name__)


@connect_four_blueprint.route("/publish-connect-four", methods=["POST"])
@token_required
async def publish_connect_four():
    try:
        to_publish = await request.get_json()
        await sse.publish(to_publish, type=CONNECT_FOUR_TYPE, channel=EVENTS_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)

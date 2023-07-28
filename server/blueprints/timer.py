from quart import Blueprint, request
from server.util.token_required import token_required
from server.util.constants import TIMER_TYPE, EVENTS_CHANNEL
from server.util.parse_schema import SchemaValueType, parse_body
from .sse import sse

timer_blueprint = Blueprint("timer", __name__)


@timer_blueprint.route("/publish-timer", methods=["POST"])
@token_required
async def publish_timer():
    valid_request = {
        "time": SchemaValueType.Integer,
        "direction": SchemaValueType.String,
    }
    try:
        to_publish = await parse_body(request, valid_request)
        await sse.publish(to_publish, type=TIMER_TYPE, channel=EVENTS_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)

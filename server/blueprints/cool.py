from quart import Blueprint, request
from server.util.token_required import token_required
from server.util.constants import COOL_TYPE, EVENTS_CHANNEL
from server.util.parse_schema import SchemaValueType, parse_body
from .sse import sse

cool_blueprint = Blueprint("cool", __name__)


@cool_blueprint.route("/publish-cool", methods=["POST"])
@token_required
async def publish_cool():
    valid_request = {"cool": SchemaValueType.Integer}
    try:
        to_publish = await parse_body(request, valid_request)
        await sse.publish(to_publish, type=COOL_TYPE, channel=EVENTS_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)

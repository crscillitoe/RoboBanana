from quart import Blueprint, request
from server.util.token_required import token_required
from server.util.constants import TAMAGACHI_TYPE, EVENTS_CHANNEL
from server.util.parse_schema import SchemaValueType, parse_body
from .sse import sse

tamagachi_blueprint = Blueprint("tamagachi", __name__)


@tamagachi_blueprint.route("/publish-tamagachi", methods=["POST"])
@token_required
async def publish_tamagachi():
    valid_request = {
        "feederName": SchemaValueType.String,
        "numFed": SchemaValueType.Integer,
        "fruit": SchemaValueType.String,
    }
    try:
        to_publish = await parse_body(request, valid_request)
        await sse.publish(to_publish, type=TAMAGACHI_TYPE, channel=EVENTS_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)

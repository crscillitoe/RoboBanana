from quart import Blueprint, request
from server.util.token_required import token_required
from server.util.constants import VOD_REVIEW_TYPE, EVENTS_CHANNEL
from server.util.parse_schema import SchemaValueType, parse_body
from .sse import sse

vod_blueprint = Blueprint("vod", __name__)


@vod_blueprint.route("/publish-vod", methods=["POST"])
@token_required
async def publish_vod():
    valid_request = {
        "complete": SchemaValueType.String,
        "username": SchemaValueType.String,
        "userid": SchemaValueType.Integer,
        "rank": SchemaValueType.String,
        "riotid": SchemaValueType.String,
    }
    try:
        to_publish = await parse_body(request, valid_request)
        await sse.publish(to_publish, type=VOD_REVIEW_TYPE, channel=EVENTS_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)

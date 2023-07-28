from quart import Blueprint, request
from server.util.token_required import token_required
from server.util.constants import SUBS_TYPE, SUBS_COUNT_TYPE, EVENTS_CHANNEL
from server.util.parse_schema import SchemaValueType, parse_body
from .sse import sse

sub_blueprint = Blueprint("sub", __name__)


@sub_blueprint.route("/publish-sub", methods=["POST"])
@token_required
async def publish_sub():
    valid_request = {
        "name": SchemaValueType.String,
        "tier": SchemaValueType.String,
        "message": SchemaValueType.String,
    }
    try:
        to_publish = await parse_body(request, valid_request)
        await sse.publish(to_publish, type=SUBS_TYPE, channel=EVENTS_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)


@sub_blueprint.route("/publish-sub-count", methods=["POST"])
@token_required
async def publish_sub_count():
    valid_request = {
        "tier1Count": SchemaValueType.Integer,
        "tier2Count": SchemaValueType.Integer,
        "tier3Count": SchemaValueType.Integer,
    }
    try:
        to_publish = await parse_body(request, valid_request)
        await sse.publish(to_publish, type=SUBS_COUNT_TYPE, channel=EVENTS_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)

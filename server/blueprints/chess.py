from quart import Blueprint, request
from server.util.token_required import token_required
from server.util.constants import CHESS_TYPE, EVENTS_CHANNEL
from server.util.parse_schema import SchemaValueType, parse_body
from .sse import sse

chess_blueprint = Blueprint("chess", __name__)


@chess_blueprint.route("/publish-chess", methods=["POST"])
@token_required
async def publish_poll():
    valid_request = {
        "open": SchemaValueType.Integer,
        "naScore": SchemaValueType.Integer,
        "euScore": SchemaValueType.Integer,
    }
    try:
        to_publish = await parse_body(request, valid_request)
        await sse.publish(to_publish, type=CHESS_TYPE, channel=EVENTS_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)

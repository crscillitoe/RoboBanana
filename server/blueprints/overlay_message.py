from quart import Blueprint, request
from server.util.constants import CHESS_TYPE, EVENTS_CHANNEL
from server.controllers.overlay_message_controller import OverlayMessageController
from server.util.parse_schema import SchemaValueType, parse_body
from .sse import sse

overlay_message_blueprint = Blueprint("overlay_message", __name__)


@overlay_message_blueprint.route("/publish-overlay-message", methods=["POST"])
async def publish_overlay_message():
    valid_request = {
        "token": SchemaValueType.String,
        "message": SchemaValueType.String,
    }
    try:
        to_publish = await parse_body(request, valid_request)
        await OverlayMessageController.send_message(
            to_publish["message"], to_publish["token"]
        )
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)

from quart import Blueprint, request
from server.util.token_required import token_required
from server.util.constants import POLLS_TYPE, POLL_ANSWERS_TYPE, EVENTS_CHANNEL
from server.util.parse_schema import SchemaValueType, parse_body
from .sse import sse

poll_blueprint = Blueprint("poll", __name__)


@poll_blueprint.route("/publish-poll", methods=["POST"])
@token_required
async def publish_poll():
    valid_request = {"title": SchemaValueType.String, "options": SchemaValueType.List}
    try:
        to_publish = await parse_body(request, valid_request)
        await sse.publish(to_publish, type=POLLS_TYPE, channel=EVENTS_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)


@poll_blueprint.route("/publish-poll-answer", methods=["POST"])
@token_required
async def publish_poll_answer():
    valid_request = {
        "userID": SchemaValueType.String,
        "optionNumber": SchemaValueType.Integer,
        "userRoleIDs": SchemaValueType.List,
    }
    try:
        to_publish = await parse_body(request, valid_request)
        await sse.publish(to_publish, type=POLL_ANSWERS_TYPE, channel=EVENTS_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)

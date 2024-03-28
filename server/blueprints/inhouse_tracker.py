from quart import Blueprint, request
from server.util.token_required import token_required
from server.util.constants import INHOUSE_DATA_TYPE, INHOUSE_TRACKER_CHANNEL
from .sse import sse
import logging

LOG = logging.getLogger(__name__)

inhouse_tracker_blueprint = Blueprint("inhouse-tracker", __name__)


@inhouse_tracker_blueprint.route("/publish-inhouse-data", methods=["POST"])
@token_required
async def publish_inhouse_data():
    try:
        request_json = await request.get_json()
        await sse.publish(
            request_json, type=INHOUSE_DATA_TYPE, channel=INHOUSE_TRACKER_CHANNEL
        )
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)


# Keeping this here for the setup routes potentially
# @sub_blueprint.route("/publish-sub-count", methods=["POST"])
# @token_required
# async def publish_sub_count():
#     valid_request = {
#         "tier1Count": SchemaValueType.Integer,
#         "tier2Count": SchemaValueType.Integer,
#         "tier3Count": SchemaValueType.Integer,
#     }
#     try:
#         to_publish = await parse_body(request, valid_request)
#         await sse.publish(to_publish, type=SUBS_COUNT_TYPE, channel=EVENTS_CHANNEL)
#         return ("OK", 200)
#     except (KeyError, ValueError):
#         return ("Bad Request", 400)

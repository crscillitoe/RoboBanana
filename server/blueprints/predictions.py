from quart import Blueprint, request
from db.models import PredictionChoice
from server.controllers.prediction_controller import PredictionController
from server.models.quick_prediction import QuickPrediction

from server.util.constants import PREDICTIONS_TYPE, EVENTS_CHANNEL
from server.util.discord_client import DISCORD_CLIENT
from server.util.token_required import token_required
from server.util.parse_schema import parse_body, SchemaValueType
from .sse import sse

prediction_blueprint = Blueprint("predictions", __name__)


@prediction_blueprint.route("/publish-prediction", methods=["POST"])
@token_required
async def publish_prediction():
    valid_request = {
        "description": SchemaValueType.String,
        "optionOne": SchemaValueType.String,
        "optionTwo": SchemaValueType.String,
        "optionOnePoints": SchemaValueType.Integer,
        "optionTwoPoints": SchemaValueType.Integer,
        "acceptingEntries": SchemaValueType.String,
        "ended": SchemaValueType.String,
    }
    try:
        to_publish = await parse_body(request, valid_request)
        await sse.publish(to_publish, type=PREDICTIONS_TYPE, channel=EVENTS_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)


@prediction_blueprint.route("/quick-prediction", methods=["POST"])
@token_required
async def quick_prediction():
    valid_request = {
        "description": SchemaValueType.String,
        "optionOne": SchemaValueType.String,
        "optionTwo": SchemaValueType.String,
        "duration": SchemaValueType.Integer,
    }
    try:
        prediction_body = await parse_body(request, valid_request)
        prediction_details = QuickPrediction(
            prediction_body["description"],
            prediction_body["optionOne"],
            prediction_body["optionTwo"],
            prediction_body["duration"],
        )
        status = await PredictionController.create_prediction(
            prediction_details, DISCORD_CLIENT
        )
        if not status:
            return ("Bad Request", 400)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)


@prediction_blueprint.route("/close-prediction", methods=["GET"])
@token_required
async def close_prediction():
    await PredictionController.close_prediction(DISCORD_CLIENT)
    return ("OK", 200)


@prediction_blueprint.route("/refund-prediction", methods=["GET"])
@token_required
async def refund_prediction():
    status = await PredictionController.refund_prediction(DISCORD_CLIENT)
    if not status:
        return ("Bad Request", 400)
    return ("OK", 200)


@prediction_blueprint.route("/payout-prediction", methods=["POST"])
@token_required
async def payout_prediction():
    valid_request = {"choice": SchemaValueType.String}
    try:
        body = await parse_body(request, valid_request)
        choice = PredictionChoice[body["choice"]]
        await PredictionController.payout_prediction(choice, DISCORD_CLIENT)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)

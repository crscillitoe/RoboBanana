from discord import Client
from controllers.predictions.create_prediction_controller import (
    CreatePredictionController,
)
from controllers.predictions.close_prediction_controller import (
    ClosePredictionController,
)
from controllers.predictions.payout_prediction_controller import (
    PayoutPredictionController,
)
from config import YAMLConfig as Config
import logging
from db.models import PredictionChoice

from server.models.quick_prediction import QuickPrediction

GUILD_ID = Config.CONFIG["Discord"]["GuildID"]
PREDICTION_CHANNEL_ID = Config.CONFIG["Discord"]["Predictions"]["Channel"]

LOG = logging.getLogger(__name__)


class PredictionController:
    async def create_prediction(prediction_details: QuickPrediction, client: Client):
        if CreatePredictionController.has_ongoing_prediction(GUILD_ID):
            LOG.info("Ongoing prediction running")
            return False

        LOG.info("Creating new quick prediction")
        await client.wait_until_ready()
        message = await client.get_channel(PREDICTION_CHANNEL_ID).send(
            "STARTING NEW QUICK PREDICTION"
        )
        await CreatePredictionController.create_prediction(
            GUILD_ID,
            PREDICTION_CHANNEL_ID,
            message,
            prediction_details.description,
            prediction_details.option_one,
            prediction_details.option_two,
            prediction_details.duration,
            client,
        )
        return True

    async def close_prediction():
        LOG.info("Closing ongoing prediction")
        await ClosePredictionController.close_prediction(GUILD_ID)

    async def payout_prediction(option: PredictionChoice, client: Client):
        LOG.info(f"Paying out current prediction to {option}")
        await client.wait_until_ready()
        status, _ = await PayoutPredictionController.payout_prediction_for_guild(
            option, GUILD_ID, client
        )
        return status

    async def refund_prediction(client: Client):
        LOG.info("Refunding current prediction")
        await client.wait_until_ready()
        status, _ = await PayoutPredictionController.refund_prediction_for_guild(
            GUILD_ID, client
        )
        return status

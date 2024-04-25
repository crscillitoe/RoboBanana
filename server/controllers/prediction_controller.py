from discord import AllowedMentions, ChannelType, Client
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
from db import DB
from db.models import PredictionChoice

from server.models.quick_prediction import QuickPrediction

GUILD_ID = Config.CONFIG["Discord"]["GuildID"]
PREDICTION_CHANNEL_ID = Config.CONFIG["Discord"]["Predictions"]["Channel"]
PREDICTION_AUDIT_CHANNEL = Config.CONFIG["Discord"]["Predictions"]["AuditChannel"]

LOG = logging.getLogger(__name__)


class PredictionController:
    async def create_prediction(prediction_details: QuickPrediction, client: Client):
        if CreatePredictionController.has_ongoing_prediction(GUILD_ID):
            LOG.info("Ongoing prediction running")
            return False

        LOG.info("Creating new quick prediction")
        await client.wait_until_ready()
        prediction_thread = await client.get_channel(
            PREDICTION_CHANNEL_ID
        ).create_thread(
            name=prediction_details.description, type=ChannelType.public_thread
        )
        prediction_message = await prediction_thread.send(
            prediction_details.description
        )
        await CreatePredictionController.create_prediction(
            GUILD_ID,
            prediction_thread.id,
            prediction_message,
            prediction_details.description,
            prediction_details.option_one,
            prediction_details.option_two,
            prediction_details.duration,
            False,
            client,
        )

        audit_channel = client.get_channel(PREDICTION_AUDIT_CHANNEL)
        await audit_channel.send(
            f"*Streamdeck* started prediction `{prediction_details.description}` here: {prediction_thread.mention} (In {prediction_thread.parent.mention}).",
            allowed_mentions=AllowedMentions.none(),
        )
        return True

    async def close_prediction(client: Client):
        if not DB().has_ongoing_prediction(GUILD_ID):
            return False
        LOG.info("Closing ongoing prediction")
        audit_channel = client.get_channel(PREDICTION_AUDIT_CHANNEL)
        await audit_channel.send(
            f"*Streamdeck* closed the current prediction.",
            allowed_mentions=AllowedMentions.none(),
        )

        try:
            prediction_id = DB().get_ongoing_prediction_id(GUILD_ID)
            prediction_message_id = DB().get_prediction_message_id(prediction_id)
            prediction_channel_id = DB().get_prediction_channel_id(prediction_id)
            prediction_message = await client.get_channel(
                prediction_channel_id
            ).fetch_message(prediction_message_id)
            await prediction_message.reply("Prediction closed!")
        except Exception:
            pass

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

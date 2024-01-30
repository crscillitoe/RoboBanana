from datetime import datetime, timedelta
from discord import Client, Message
from controllers.predictions.update_prediction_controller import (
    UpdatePredictionController,
)
from db import DB
from config import YAMLConfig as Config
import logging
from views.predictions.close_prediction_embed import ClosePredictionEmbed
from views.predictions.close_prediction_view import ClosePredictionView

from views.predictions.prediction_embed import PredictionEmbed
from views.predictions.prediction_view import PredictionView

PENDING_REWARDS_CHAT_ID = Config.CONFIG["Discord"]["ChannelPoints"][
    "PendingRewardChannel"
]

LOG = logging.getLogger(__name__)

REFUND_PREDICTION_CHOICE = -1


class CreatePredictionController:
    @staticmethod
    def has_ongoing_prediction(guild_id: int):
        return DB().has_ongoing_prediction(guild_id)

    @staticmethod
    async def create_prediction(
        guild_id: int,
        channel_id: int,
        message: Message,
        description: str,
        option_one: str,
        option_two: str,
        duration: int,
        set_nickname: bool,
        client: Client,
    ):
        end_time = datetime.now() + timedelta(seconds=duration)
        DB().create_prediction(
            guild_id,
            channel_id,
            message.id,
            description,
            option_one,
            option_two,
            end_time,
            set_nickname,
        )
        prediction_id = DB().get_ongoing_prediction_id(guild_id)
        UpdatePredictionController.publish_prediction_summary(prediction_id)
        prediction_embed = PredictionEmbed(guild_id, description, end_time)
        prediction_view = PredictionView(
            prediction_embed, option_one, option_two, client
        )
        await message.edit(content="", embed=prediction_embed, view=prediction_view)

        close_prediction_embed = ClosePredictionEmbed(description, end_time)
        close_prediction_view = ClosePredictionView(
            close_prediction_embed, prediction_embed, prediction_view, client
        )
        await client.get_channel(PENDING_REWARDS_CHAT_ID).send(
            content="", embed=close_prediction_embed, view=close_prediction_view
        )

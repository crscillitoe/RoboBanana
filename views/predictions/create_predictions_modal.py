from discord import TextStyle, Interaction, Client
from discord.ui import Modal, TextInput
from datetime import datetime, timedelta
from config import Config
from db import DB

from .close_prediction_embed import ClosePredictionEmbed
from .close_prediction_view import ClosePredictionView
from .prediction_embed import PredictionEmbed
from .prediction_view import PredictionView

PENDING_REWARDS_CHAT_ID = int(Config.CONFIG["Discord"]["PendingRewardChannel"])


class CreatePredictionModal(Modal, title="Start new prediction"):
    def __init__(self, client: Client):
        super().__init__(timeout=None)
        self.client = client
        self.description = TextInput(
            label="Description",
            placeholder="What are viewers trying to predict?",
            required=True,
        )
        self.option_one = TextInput(
            label="Option 1",
            placeholder="BELIEF",
            required=True,
        )
        self.option_two = TextInput(
            label="Option 2",
            placeholder="DOUBT",
            required=True,
        )
        self.duration = TextInput(
            label="Duration (in seconds)",
            default="120",
            style=TextStyle.short,
            required=True,
            min_length=1,
        )

        self.add_item(self.description)
        self.add_item(self.option_one)
        self.add_item(self.option_two)
        self.add_item(self.duration)

    async def on_submit(self, interaction: Interaction):
        try:
            duration = int(self.duration.value)
        except ValueError:
            await interaction.response.send_message(
                "Invalid prediction duration.", ephemeral=True
            )
            return
        await interaction.response.send_message("Creating prediction...")

        end_time = datetime.now() + timedelta(seconds=duration)
        prediction_message = await interaction.original_response()
        DB().create_prediction(
            interaction.guild_id,
            prediction_message.id,
            self.description.value,
            self.option_one.value,
            self.option_two.value,
            end_time,
        )
        prediction_embed = PredictionEmbed(
            interaction.guild_id, self.description.value, end_time
        )
        prediction_view = PredictionView(
            prediction_embed, self.option_one.value, self.option_two.value, self.client
        )
        await prediction_message.edit(
            content="", embed=prediction_embed, view=prediction_view
        )

        close_prediction_embed = ClosePredictionEmbed(self.description.value, end_time)
        close_prediction_view = ClosePredictionView(
            close_prediction_embed, prediction_embed, prediction_view, self.client
        )
        await self.client.get_channel(PENDING_REWARDS_CHAT_ID).send(
            content="", embed=close_prediction_embed, view=close_prediction_view
        )

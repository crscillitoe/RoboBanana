from discord import AllowedMentions, ChannelType, TextStyle, Interaction, Client
from discord.ui import Modal, TextInput
import logging
from config import YAMLConfig as Config

from controllers.predictions.create_prediction_controller import (
    CreatePredictionController,
)
from db import DB

LOG = logging.getLogger(__name__)
PREDICTION_AUDIT_CHANNEL = Config.CONFIG["Discord"]["Predictions"]["AuditChannel"]
PREDICTION_THREAD_TARGET_CHANNEL = Config.CONFIG["Discord"]["Predictions"]["Channel"]


class CreatePredictionModal(Modal, title="Start new prediction"):
    def __init__(self, client: Client, set_nickname=False):
        super().__init__(timeout=None)
        self.client = client
        self.description = TextInput(
            label="Description",
            placeholder="What are viewers trying to predict?",
            required=True,
            min_length=1,
            max_length=24,
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
        self.set_nickname = set_nickname

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
        if DB().has_ongoing_prediction(interaction.guild_id):
            return await interaction.response.send_message(
                "There is already an ongoing prediction!", ephemeral=True
            )

        thread_target_channel = interaction.guild.get_channel(
            PREDICTION_THREAD_TARGET_CHANNEL
        )
        prediction_thread = await thread_target_channel.create_thread(
            name=self.description.value, type=ChannelType.public_thread
        )
        prediction_message = await prediction_thread.send(self.description.value)

        audit_channel = interaction.guild.get_channel(PREDICTION_AUDIT_CHANNEL)
        await audit_channel.send(
            f"{interaction.user.mention} started prediction `{self.description.value}` here: {prediction_thread.mention} (In {prediction_thread.parent.mention}).",
            allowed_mentions=AllowedMentions.none(),
        )

        await interaction.response.send_message("Starting prediction", ephemeral=True)

        await CreatePredictionController.create_prediction(
            interaction.guild_id,
            prediction_thread.id,
            prediction_message,
            self.description.value,
            self.option_one.value,
            self.option_two.value,
            duration,
            self.set_nickname,
            self.client,
        )

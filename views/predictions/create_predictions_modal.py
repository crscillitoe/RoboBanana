from discord import ChannelType, TextStyle, Interaction, Client
from discord.ui import Modal, TextInput
from datetime import datetime, timedelta

from controllers.predictions.create_prediction_controller import (
    CreatePredictionController,
)


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

        prediction_thread = await interaction.channel.create_thread(
            name=self.description.value,
            type=ChannelType.public_thread
        )
        prediction_message = await prediction_thread.send(self.description.value)

        await interaction.response.send_message("Starting prediction", ephemeral=True)

        await CreatePredictionController.create_prediction(
            interaction.guild_id,
            prediction_thread.id,
            prediction_message,
            self.description.value,
            self.option_one.value,
            self.option_two.value,
            duration,
            self.client,
        )

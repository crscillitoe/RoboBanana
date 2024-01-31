from discord import TextStyle, Interaction, Client
from discord.ui import Modal, TextInput
from controllers.predictions.prediction_entry_controller import (
    PredictionEntryController,
)
from db import DB
from db.models import PredictionChoice

from .prediction_embed import PredictionEmbed


class PredictionVoteModal(Modal, title="Cast your vote!"):
    def __init__(
        self,
        parent: PredictionEmbed,
        guess: PredictionChoice,
        point_balance: int,
        client: Client,
    ):
        super().__init__(timeout=None)
        self.guess = guess
        self.parent = parent
        self.point_balance = point_balance
        self.client = client
        self.channel_points = TextInput(
            label=f"Channel Points ({point_balance})",
            placeholder="50",
            style=TextStyle.short,
            min_length=1,
            required=True,
        )
        self.add_item(self.channel_points)

    async def on_submit(self, interaction: Interaction):
        try:
            channel_points = int(self.channel_points.value)
        except ValueError:
            await interaction.response.send_message(
                "Invalid point value", ephemeral=True
            )
            return

        await PredictionEntryController.create_prediction_entry(
            channel_points, self.guess, interaction, self.client
        )
        self.parent.update_fields()

        prediction_id = DB().get_ongoing_prediction_id(interaction.guild_id)
        prediction_message_id = DB().get_prediction_message_id(prediction_id)
        prediction_summary = DB().get_prediction_summary(prediction_id)
        prediction_message = await interaction.channel.fetch_message(
            prediction_message_id
        )
        await prediction_message.edit(embed=self.parent)

        append = ""
        oldname = interaction.user.display_name
        chosen = prediction_summary.option_one if self.guess.name == "left" else prediction_summary.option_two
        if prediction_summary.set_nickname:
            if len(oldname) + len(chosen) + 1 > 32:
                append = "\nCould not set your nickname, as it would exceed the nickname length limit of 32."
            else:
                oldname = oldname.replace(f"{chosen} ", "", 1)
                append = f"\nTo change your name back to your original name, use the `/nick` slash commands with the value `{oldname}`"

        await interaction.response.send_message(
            f"Vote cast with {channel_points} points!{append}", ephemeral=True
        )

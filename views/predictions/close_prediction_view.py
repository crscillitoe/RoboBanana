from discord import AllowedMentions, ButtonStyle, Interaction, Client
from discord.ui import View, Button
from controllers.predictions.close_prediction_controller import (
    ClosePredictionController,
)
from db import DB
from config import YAMLConfig as Config

from .payout_prediction_view import PayoutPredictionView
from .close_prediction_embed import ClosePredictionEmbed
from .prediction_embed import PredictionEmbed
from .prediction_view import PredictionView

STREAM_CHAT = Config.CONFIG["Discord"]["Channels"]["Stream"]
PENDING_REWARDS_CHAT_ID = Config.CONFIG["Discord"]["ChannelPoints"][
    "PendingRewardChannel"
]
PREDICTION_AUDIT_CHANNEL = Config.CONFIG["Discord"]["Predictions"]["AuditChannel"]


class ClosePredictionView(View):
    def __init__(
        self,
        parent: ClosePredictionEmbed,
        entry_embed: PredictionEmbed,
        entry_view: PredictionView,
        client: Client,
    ) -> None:
        super().__init__(timeout=None)
        self.parent = parent
        self.entry_embed = entry_embed
        self.entry_view = entry_view
        self.client = client

        self.close_prediction_button = Button(
            label="Close Prediction",
            style=ButtonStyle.red,
            custom_id="prediction_view:end_prediction_button",
        )
        self.close_prediction_button.callback = self.close_prediction_onclick
        self.add_item(self.close_prediction_button)

    async def close_prediction_onclick(self, interaction: Interaction):
        await ClosePredictionController.close_prediction(interaction.guild_id)
        self.entry_embed.update_fields()

        self.close_prediction_button.disabled = True
        self.entry_view.vote_one_button.disabled = True
        self.entry_view.vote_two_button.disabled = True

        prediction_id = DB().get_ongoing_prediction_id(interaction.guild_id)
        prediction_message_id = DB().get_prediction_message_id(prediction_id)
        prediction_channel_id = DB().get_prediction_channel_id(prediction_id)
        prediction_message = await self.client.get_channel(
            prediction_channel_id
        ).fetch_message(prediction_message_id)
        await prediction_message.edit(embed=self.entry_embed, view=self.entry_view)
        await interaction.message.edit(content="", embed=self.parent, view=self)

        audit_channel = interaction.guild.get_channel(PREDICTION_AUDIT_CHANNEL)
        await audit_channel.send(
            f"{interaction.user.mention} closed the current prediction.",
            allowed_mentions=AllowedMentions.none(),
        )

        payout_prediction_view = PayoutPredictionView(
            self.entry_view.option_one, self.entry_view.option_two, self.client
        )
        await prediction_message.reply("Prediction closed!")
        await interaction.response.send_message("Prediction closed!", ephemeral=True)

        await self.client.get_channel(PENDING_REWARDS_CHAT_ID).send(
            "Payout Prediction!",
            view=payout_prediction_view,
        )

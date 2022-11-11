import discord
from discord import ButtonStyle, Interaction, Client
from discord.ui import View, Button
from db import DB
from config import Config

from .payout_prediction_modal import PayoutPredictionView
from .prediction_embed import PredictionEmbed
from .prediction_vote_modal import PredictionVoteModal

PENDING_REWARDS_CHAT_ID = int(Config.CONFIG["Discord"]["PendingRewardChannel"])


class PredictionView(View):
    def __init__(
        self, parent: PredictionEmbed, option_one: str, option_two: str, client: Client
    ) -> None:
        super().__init__(timeout=None)

        self.parent = parent
        self.client = client
        self.option_one = option_one
        self.option_two = option_two

        self.vote_one_button = Button(
            label=option_one,
            style=ButtonStyle.blurple,
            custom_id="prediction_view:vote_one_button",
        )
        self.vote_one_button.callback = self.vote_one_button_onclick
        self.add_item(self.vote_one_button)

        self.vote_two_button = Button(
            label=option_two,
            style=ButtonStyle.secondary,
            custom_id="prediction_view:vote_two_button",
        )
        self.vote_two_button.callback = self.vote_two_button_onclick
        self.add_item(self.vote_two_button)

        self.end_prediction_button = Button(
            label="End Prediction",
            style=ButtonStyle.red,
            custom_id="prediction_view:end_prediction_button",
        )
        self.end_prediction_button.callback = self.end_prediction_button_onclick
        self.add_item(self.end_prediction_button)

    async def user_eligible(self, interaction: Interaction) -> bool:
        entry = DB().get_user_prediction_entry(
            interaction.guild_id, interaction.user.id
        )
        if entry is not None:
            await interaction.response.send_message(
                "You have already entered the prediction!", ephemeral=True
            )
            return False

        if not DB().accepting_prediction_entries(interaction.guild_id):
            await interaction.response.send_message(
                "Prediction has been closed!", ephemeral=True
            )
            return False
        return True

    def has_role(self, role_name: str, interaction: Interaction) -> bool:
        role = discord.utils.get(interaction.user.roles, name=role_name)
        return role is not None

    async def end_prediction_button_onclick(self, interaction: Interaction):
        if not self.has_role("Mod", interaction):
            return await interaction.response.send_message(
                "You must be a mod to do that!", ephemeral=True
            )

        DB().close_prediction(interaction.guild_id)
        self.parent.update_fields()

        self.vote_one_button.disabled = True
        self.vote_two_button.disabled = True
        self.end_prediction_button.disabled = True

        prediction_message_id = DB().get_prediction_message_id(interaction.guild_id)
        prediction_message = await interaction.channel.fetch_message(
            prediction_message_id
        )
        await prediction_message.edit(embed=self.parent, view=self)

        payout_prediction_view = PayoutPredictionView(self.option_one, self.option_two)
        await self.client.get_channel(PENDING_REWARDS_CHAT_ID).send(
            f"Payout Prediction!",
            view=payout_prediction_view,
        )

        await interaction.response.send_message("Prediction closed!")

    async def vote_one_button_onclick(self, interaction: Interaction):
        if not await self.user_eligible(interaction):
            return
        point_balance = DB().get_point_balance(interaction.user.id)
        modal = PredictionVoteModal(self.parent, 0, point_balance)
        await interaction.response.send_modal(modal)

    async def vote_two_button_onclick(self, interaction: Interaction):
        if not await self.user_eligible(interaction):
            return
        point_balance = DB().get_point_balance(interaction.user.id)
        modal = PredictionVoteModal(self.parent, 1, point_balance)
        await interaction.response.send_modal(modal)

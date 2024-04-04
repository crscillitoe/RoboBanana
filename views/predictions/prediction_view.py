import discord
from discord import ButtonStyle, Interaction, Client
from discord.ui import View, Button
from db import DB
from config import YAMLConfig as Config
from db.models import PredictionChoice

from .prediction_embed import PredictionEmbed
from .prediction_vote_modal import PredictionVoteModal

PENDING_REWARDS_CHAT_ID = Config.CONFIG["Discord"]["ChannelPoints"][
    "PendingRewardChannel"
]


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

    async def user_eligible(self, interaction: Interaction) -> bool:
        if not DB().accepting_prediction_entries(interaction.guild_id):
            await interaction.response.send_message(
                "Prediction has been closed!", ephemeral=True
            )
            return False
        return True

    def has_role(self, role_name: str, interaction: Interaction) -> bool:
        role = discord.utils.get(interaction.user.roles, name=role_name)
        return role is not None

    async def vote_one_button_onclick(self, interaction: Interaction):
        if not await self.user_eligible(interaction):
            return
        point_balance = DB().get_point_balance(interaction.user.id)
        modal = PredictionVoteModal(
            self.parent, PredictionChoice.left, point_balance, self.client
        )
        await interaction.response.send_modal(modal)

    async def vote_two_button_onclick(self, interaction: Interaction):
        if not await self.user_eligible(interaction):
            return
        point_balance = DB().get_point_balance(interaction.user.id)
        modal = PredictionVoteModal(
            self.parent, PredictionChoice.right, point_balance, self.client
        )
        await interaction.response.send_modal(modal)

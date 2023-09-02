from discord import User, Client, ButtonStyle, Interaction
from discord.ui import View, Button
from controllers.point_history_controller import PointHistoryController

from db import DB
from db.models import ChannelReward
from config import YAMLConfig as Config
from models.transaction import Transaction

STREAM_CHAT_ID = Config.CONFIG["Discord"]["Channels"]["Stream"]


class PendingRewardView(View):
    def __init__(self, reward: ChannelReward, user: User, client: Client) -> None:
        super().__init__(timeout=None)

        self.reward = reward
        self.user = user
        self.client = client

        self.complete_reward_button = Button(
            label="Complete reward",
            style=ButtonStyle.blurple,
            custom_id="pending_reward_view:complete_button",
        )
        self.complete_reward_button.callback = self.complete_reward_onclick
        self.add_item(self.complete_reward_button)

        self.refund_reward_button = Button(
            label="Refund reward",
            style=ButtonStyle.red,
            custom_id="pending_reward_view:refund_button",
        )
        self.refund_reward_button.callback = self.refund_reward_onclick
        self.add_item(self.refund_reward_button)

    async def complete_reward_onclick(self, interaction: Interaction):
        self.complete_reward_button.disabled = True
        self.refund_reward_button.disabled = True
        await self.client.get_channel(STREAM_CHAT_ID).send(
            f"Completed reward for {self.user.mention}"
        )

        await interaction.response.send_message(
            f"Reward completed for {self.user.mention}"
        )
        await interaction.message.edit(content="Reward no longer pending", view=self)

    async def refund_reward_onclick(self, interaction: Interaction):
        success, new_balance = DB().deposit_points(self.user.id, self.reward.point_cost)
        PointHistoryController.record_transaction(
            Transaction(
                self.user.id,
                self.reward.point_cost,
                new_balance - self.reward.point_cost,
                new_balance,
                "Reward Refund",
            )
        )
        if not success:
            return await interaction.response.send_message(
                f"Failed to refund points to {self.user.mention} - please try again.",
                ephemeral=True,
            )

        await self.client.get_channel(STREAM_CHAT_ID).send(
            f"Refunded reward for {self.user.mention}"
        )

        self.complete_reward_button.disabled = True
        self.refund_reward_button.disabled = True
        await interaction.message.edit(content="Reward no longer pending", view=self)

        await interaction.response.send_message(
            f"Refunded {self.reward.point_cost} points for {self.user.mention}",
            ephemeral=True,
        )

from discord import Client, SelectOption, Interaction
from discord.ui import View, Select
from controllers.point_history_controller import PointHistoryController

from db import DB
from db.models import ChannelReward
from config import YAMLConfig as Config
from models.transaction import Transaction

from .pending_reward_view import PendingRewardView


STREAM_CHAT_ID = Config.CONFIG["Discord"]["Channels"]["Stream"]
PENDING_REWARDS_CHAT_ID = Config.CONFIG["Discord"]["ChannelPoints"][
    "PendingRewardChannel"
]


class RedeemRewardView(View):
    def __init__(
        self, user_points: int, channel_rewards: list[ChannelReward], client: Client
    ):
        super().__init__(timeout=None)
        self.options = []
        self.client = client
        self.user_points = user_points
        self.reward_lookup = {
            channel_reward.id: channel_reward for channel_reward in channel_rewards
        }
        for channel_reward in channel_rewards:
            # Only display options the user can afford
            if channel_reward.point_cost > user_points:
                continue

            self.options.append(
                SelectOption(
                    label=f"({channel_reward.point_cost}) {channel_reward.name}",
                    value=channel_reward.id,
                )
            )
        self.select = Select(placeholder="Reward to redeem", options=self.options)

        self.add_item(self.select)

    async def interaction_check(self, interaction: Interaction):
        redeemed_reward = self.reward_lookup.get(int(self.select.values[0]))
        if redeemed_reward is None:
            return await interaction.response.send_message(
                "Invalid reward redeemed", ephemeral=True
            )
        if redeemed_reward.point_cost > self.user_points:
            return await interaction.response.send_message(
                "Not enough channel points to redeem this reward - try again later!",
                ephemeral=True,
            )

        success, balance = DB().withdraw_points(
            interaction.user.id, redeemed_reward.point_cost
        )
        if not success:
            return await interaction.response.send_message(
                "Failed to redeem reward - please try again.", ephemeral=True
            )

        PointHistoryController.record_transaction(
            Transaction(
                interaction.user.id,
                -redeemed_reward.point_cost,
                self.user_points,
                balance,
                "Redeemed Reward",
            )
        )

        await interaction.response.send_message(
            f"Redeemed! You have {balance} points remaining.", ephemeral=True
        )
        await self.client.get_channel(STREAM_CHAT_ID).send(
            f"{interaction.user.mention} redeemed {redeemed_reward.name}!"
        )

        pending_reward_view = PendingRewardView(
            redeemed_reward, interaction.user, self.client
        )
        await self.client.get_channel(PENDING_REWARDS_CHAT_ID).send(
            f"Pending {redeemed_reward.name} for {interaction.user.mention}",
            view=pending_reward_view,
        )

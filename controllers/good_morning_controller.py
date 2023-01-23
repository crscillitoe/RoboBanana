from discord import Interaction
from db import DB
from config import Config
import asyncio

STREAM_CHAT_ID = int(Config.CONFIG["Discord"]["StreamChannel"])
REWARD_ROLE_ID = int(Config.CONFIG["Discord"]["GoodMorningRewardRoleID"])
REWARD_REDEMPTION_CHANNEL_ID = int(
    Config.CONFIG["Discord"]["GoodMorningRewardRedemptionChannelID"]
)
GOOD_MORNING_EXPLANATION = "What's this message? <#1064317660084584619>"


class GoodMorningController:
    async def get_morning_points(interaction: Interaction):
        points = DB().get_morning_points(interaction.user.id)
        await interaction.response.send_message(
            f"Your current weekly count is {points}!", ephemeral=True
        )

    async def accrue_good_morning(interaction: Interaction):
        if interaction.channel.id != STREAM_CHAT_ID:
            return await interaction.response.send_message(
                f"You can only say good morning in <#{STREAM_CHAT_ID}>!", ephemeral=True
            )

        accrued = DB().accrue_morning_points(interaction.user.id)
        if not accrued:
            return await interaction.response.send_message(
                "You've already said good morning today!", ephemeral=True
            )

        points = DB().get_morning_points(interaction.user.id)
        await interaction.response.send_message(
            (
                f"Good morning {interaction.user.mention}! "
                f"Your current weekly count is {points}! "
                f"{GOOD_MORNING_EXPLANATION}"
            )
        )

    async def reward_users(interaction: Interaction):
        rewarded_user_ids = DB().get_morning_reward_winners()
        if len(rewarded_user_ids) == 0:
            return await interaction.response.send_message(
                "No users to reward!", ephemeral=True
            )

        reward_role = interaction.guild.get_role(REWARD_ROLE_ID)

        # Assign roles
        for user_id in rewarded_user_ids:
            member = interaction.guild.get_member(user_id)
            if member is None:
                continue
            await member.add_roles(reward_role)

            # Rate limit
            await asyncio.sleep(1)

        reward_message = (
            f"Congrats {reward_role.mention}!"
            f" Head over to <#{REWARD_REDEMPTION_CHANNEL_ID}> to redeem your reward!"
        )
        await interaction.response.send_message(reward_message)

    async def reset_all_morning_points(interaction: Interaction):
        DB().reset_all_morning_points()
        await interaction.response.send_message(
            "Successfully reset weekly good morning points!", ephemeral=True
        )

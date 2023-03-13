from discord import Interaction, Message, Thread
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

        await interaction.response.send_message("Good Morning Reward Progress")
        response_message = await interaction.original_response()

        thread: Thread = await response_message.create_thread(
            name="Good Morning Reward Progress"
        )

        reward_count = len(rewarded_user_ids)

        await thread.send(f"Distributing good morning rewards to {reward_count} users.")

        progress_threshold = 0.25

        # Assign roles
        for idx, user_id in enumerate(rewarded_user_ids):
            member = interaction.guild.get_member(user_id)
            if member is None:
                continue

            await member.add_roles(reward_role)

            num_rewarded = idx + 1
            if (num_rewarded / reward_count) > progress_threshold:
                await thread.send(f"{num_rewarded}/{reward_count} rewarded...")
                progress_threshold += 0.25

            # Rate limit
            await asyncio.sleep(1)

        reward_message = (
            f"Congrats {reward_role.mention}!"
            f" Head over to <#{REWARD_REDEMPTION_CHANNEL_ID}> to redeem your reward!"
        )
        await interaction.followup.send(reward_message)

    async def reset_all_morning_points(interaction: Interaction):
        DB().reset_all_morning_points()
        await interaction.response.send_message(
            "Successfully reset weekly good morning points!", ephemeral=True
        )

    async def good_morning_increment(points: int, interaction: Interaction):
        DB().manual_increment_morning_points(points)
        await interaction.response.send_message(
            f"Successfully gave all users {points} good morning points!", ephemeral=True
        )

from discord import Interaction, Thread
from db import DB
from config import Config
from datetime import datetime
from time import mktime as epochtime
from pytz import timezone
import asyncio


STREAM_CHAT_ID = int(Config.CONFIG["Discord"]["StreamChannel"])
REWARD_ROLE_ID = int(Config.CONFIG["Discord"]["GoodMorningRewardRoleID"])
REWARD_REDEMPTION_CHANNEL_ID = int(
    Config.CONFIG["Discord"]["GoodMorningRewardRedemptionChannelID"]
)
GOOD_MORNING_EXPLANATION = "What's this message? <#1064317660084584619>"

PACIFIC_TZ = timezone("US/Pacific")
UTC_TZ = timezone("UTC")
START_TIME = PACIFIC_TZ.localize(datetime.utcnow().replace(hour=9, minute=0)).time()
END_TIME = PACIFIC_TZ.localize(datetime.utcnow().replace(hour=11, minute=30)).time()


class GoodMorningController:
    async def get_morning_points(interaction: Interaction):
        points = DB().get_morning_points(interaction.user.id)
        await interaction.response.send_message(
            f"Your current weekly count is {points}!", ephemeral=True
        )

    def valid_accrual_time(interaction_datetime: datetime):
        pacific_interaction_time = interaction_datetime.astimezone(PACIFIC_TZ).time()
        return START_TIME < pacific_interaction_time < END_TIME

    def to_utc(timestamp: datetime):
        return PACIFIC_TZ.normalize(PACIFIC_TZ.localize(timestamp)).astimezone(UTC_TZ)

    def outside_window_response():
        start_time = datetime.combine(datetime.utcnow().date(), START_TIME)
        end_time = datetime.combine(datetime.utcnow().date(), END_TIME)
        start_time_epoch = epochtime(
            GoodMorningController.to_utc(start_time).timetuple()
        )
        end_time_epoch = epochtime(GoodMorningController.to_utc(end_time).timetuple())
        start_time_str = f"<t:{start_time_epoch:.0f}:t>"
        end_time_str = f"<t:{end_time_epoch:.0f}:t>"
        return (
            f"You can only say good morning between {start_time_str} and"
            f" {end_time_str}!"
        )

    async def accrue_good_morning(interaction: Interaction):
        if not GoodMorningController.valid_accrual_time(interaction.created_at):
            return await interaction.response.send_message(
                GoodMorningController.outside_window_response(), ephemeral=True
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
            ),
            ephemeral=True,
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

from discord import Client, Interaction, Thread
from db import DB
from config import YAMLConfig as Config
from datetime import datetime, timedelta
from time import mktime as epochtime
from pytz import timezone
import asyncio
from controllers.temprole_controller import TempRoleController
import logging
from discord.ext import tasks

LOG = logging.getLogger(__name__)

STREAM_CHAT_ID = Config.CONFIG["Discord"]["Channels"]["Stream"]
REWARD_ROLE_ID = Config.CONFIG["Discord"]["GoodMorning"]["RewardRole"]
REWARD_REDEMPTION_CHANNEL_ID = Config.CONFIG["Discord"]["GoodMorning"][
    "RedemptionChannel"
]
REWARD_PROGRESS_CHANNEL = Config.CONFIG["Discord"]["GoodMorning"]["ProgressChannel"]
GOOD_MORNING_EXPLANATION = "What's this message? <#1064317660084584619>"

PACIFIC_TZ = timezone("US/Pacific")
UTC_TZ = timezone("UTC")
START_TIME = PACIFIC_TZ.localize(datetime.utcnow().replace(hour=8, minute=30)).time()
END_TIME = PACIFIC_TZ.localize(datetime.utcnow().replace(hour=14, minute=0)).time()
# The time on the upcoming sunday the temporary GM role will expire. Setting this AFTER the automatic distribution time ensures a seamless role transition.
GM_TEMPROLE_TARGET_TIME = PACIFIC_TZ.localize(
    datetime.utcnow().replace(hour=23, minute=30, second=0, microsecond=0)
).time()
# The time each day we run the `auto_reward_users` method. The method itself checks if it's sunday as that seems to be the easiest way to only do this on sundays.
GM_TEMPROLE_AUTO_TIME = PACIFIC_TZ.localize(
    datetime.utcnow().replace(hour=23, minute=00, second=0, microsecond=0)
).time()


class GoodMorningController:
    def __init__(self, client: Client):
        self.client = client

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
            f"Good morning {interaction.user.mention}! "
            f"Your current weekly count is {points}! "
            f"{GOOD_MORNING_EXPLANATION}",
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

        await GoodMorningController.tempreward_upcoming_sunday(
            thread, rewarded_user_ids, reward_role
        )

        reward_message = (
            f"Congrats {reward_role.mention}!"
            f" Head over to <#{REWARD_REDEMPTION_CHANNEL_ID}> to redeem your reward!"
        )
        await interaction.followup.send(reward_message)

    @tasks.loop(time=GM_TEMPROLE_AUTO_TIME)
    async def auto_reward_users(self):
        current_weekday = datetime.now(tz=PACIFIC_TZ).weekday()
        if current_weekday != 6:
            # fail silently as it is not sunday
            return

        LOG.info("[AUTO GM TASK] Running automatic GM reward distribution...")

        rewarded_user_ids = DB().get_morning_reward_winners()
        if len(rewarded_user_ids) == 0:
            LOG.info("[AUTO GM TASK] No users to reward")
            return

        guild = self.client.get_guild(Config.CONFIG["Discord"]["GuildID"])
        reward_role = guild.get_role(REWARD_ROLE_ID)
        progres_channel = guild.get_channel(REWARD_PROGRESS_CHANNEL)

        original_message = await progres_channel.send("Good Morning Reward Progress")
        thread: Thread = await original_message.create_thread(
            name="Good Morning Reward Progress",
        )

        await self.tempreward_upcoming_sunday(thread, rewarded_user_ids, reward_role)

        DB().reset_all_morning_points()

        reward_message = (
            f"Congrats {reward_role.mention}!"
            f" Head over to <#{REWARD_REDEMPTION_CHANNEL_ID}> to redeem your reward!"
        )
        await progres_channel.send(reward_message)

    @staticmethod
    async def tempreward_upcoming_sunday(thread, rewarded_user_ids, reward_role):
        reward_count = len(rewarded_user_ids)

        await thread.send(f"Distributing good morning rewards to {reward_count} users.")

        progress_threshold = 0.25

        current_time = datetime.now(tz=PACIFIC_TZ)
        day_delta = 6 - current_time.weekday()
        if (
            day_delta == 0
        ):  # If it is currently sunday, manually add 7 days since we want the upcoming sunday, not the current one
            day_delta = 7
        upcoming_sunday = current_time + timedelta(days=day_delta)
        upcoming_sunday = upcoming_sunday.replace(
            hour=GM_TEMPROLE_TARGET_TIME.hour, minute=GM_TEMPROLE_TARGET_TIME.minute
        )
        temprole_duration = int(
            (upcoming_sunday - current_time) / timedelta(minutes=1)
        )  # Convert to how many minutes are in this delta, then to int to drop any decimals eventhough there shouldn't be any

        # Assign roles
        for idx, user_id in enumerate(rewarded_user_ids):
            await TempRoleController.set_role(
                user_id, reward_role, str(temprole_duration) + "m"
            )

            num_rewarded = idx + 1
            if (num_rewarded / reward_count) > progress_threshold:
                await thread.send(f"{num_rewarded}/{reward_count} rewarded...")
                progress_threshold += 0.25

            # Rate limit
            await asyncio.sleep(1)

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

from datetime import datetime, timedelta
from discord import app_commands, Interaction, Client, User
from discord.app_commands.errors import AppCommandError, CheckFailure
from controllers.prediction_controller import PredictionController
from controllers.good_morning_controller import (
    GoodMorningController,
    GOOD_MORNING_EXPLANATION,
)
from controllers.prediction_controller import PredictionController
from db import DB, RaffleType
from db.models import PredictionChoice, PredictionOutcome
from views.predictions.create_predictions_modal import CreatePredictionModal
from views.raffle.new_raffle_modal import NewRaffleModal
from views.rewards.add_reward_modal import AddRewardModal
from controllers.raffle_controller import RaffleController
from config import Config
import logging
import random
from threading import Thread
import requests
import enum

LOG = logging.getLogger(__name__)
JOEL_DISCORD_ID = 112386674155122688
HOOJ_DISCORD_ID = 82969926125490176
POINTS_AUDIT_CHANNEL = int(Config.CONFIG["Discord"]["PointsAuditChannel"])

AUTH_TOKEN = Config.CONFIG["Server"]["AuthToken"]
PUBLISH_POLL_URL = "http://localhost:3000/publish-poll"
PUBLISH_TIMER_URL = "http://localhost:3000/publish-timer"


class ChannelPerms(enum.Enum):
    t3jail = 1
    t3chat = 2
    everyonechat = 3
    subchat = 4
    off = 5


class TimerDirection(enum.Enum):
    increment = "inc"
    decrement = "dec"


@app_commands.guild_only()
class ModCommands(app_commands.Group, name="mod"):
    def __init__(self, tree: app_commands.CommandTree, client: Client) -> None:
        super().__init__()
        self.tree = tree
        self.client = client

    @staticmethod
    def check_owner(interaction: Interaction) -> bool:
        return interaction.user.id == JOEL_DISCORD_ID

    @staticmethod
    def check_hooj(interaction: Interaction) -> bool:
        return interaction.user.id == HOOJ_DISCORD_ID

    async def on_error(self, interaction: Interaction, error: AppCommandError):
        if isinstance(error, CheckFailure):
            return await interaction.response.send_message(
                "Failed to perform command - please verify permissions.", ephemeral=True
            )
        logging.error(error)
        return await super().on_error(interaction, error)

    @app_commands.command(name="sync")
    @app_commands.checks.has_role("Mod")
    async def sync(self, interaction: Interaction) -> None:
        """Manually sync slash commands to guild"""

        guild = interaction.guild
        self.tree.clear_commands(guild=guild)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        await interaction.response.send_message("Commands synced", ephemeral=True)

    @app_commands.command(name="reset_vod_submission")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(user_id="Discord User ID")
    async def reset_vod_submission(
        self, interaction: Interaction, user_id: str
    ) -> None:
        """Allows the given userID to submit a VOD."""
        DB().reset_user(user_id)
        await interaction.response.send_message("Success!", ephemeral=True)

    @app_commands.command(name="timer")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(time="Time in seconds")
    async def timer(
        self,
        interaction: Interaction,
        time: int,
        direction: TimerDirection = TimerDirection.decrement,
    ) -> None:
        """Display a timer on stream of the given length"""
        Thread(
            target=publish_timer,
            args=(
                time,
                direction,
            ),
        ).start()

        await interaction.response.send_message("Timer created!", ephemeral=True)

    @app_commands.command(name="poll")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(title="title")
    @app_commands.describe(option_one="option_one")
    @app_commands.describe(option_two="option_two")
    @app_commands.describe(option_three="option_three")
    @app_commands.describe(option_four="option_four")
    async def poll(
        self,
        interaction: Interaction,
        title: str,
        option_one: str,
        option_two: str,
        option_three: str = "",
        option_four: str = "",
    ) -> None:
        """Run the given poll, 2-4 options"""
        Thread(
            target=publish_poll,
            args=(
                title,
                option_one,
                option_two,
                option_three,
                option_four,
            ),
        ).start()

        await interaction.response.send_message("Poll created!", ephemeral=True)

    @app_commands.command(name="gift")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(num_winners="num_winners")
    @app_commands.describe(oprah="Oprah")
    async def gift(self, interaction: Interaction, oprah: str, num_winners: int):
        Tier1 = int(Config.CONFIG["Discord"]["Tier1RoleID"])
        Tier2 = int(Config.CONFIG["Discord"]["Tier2RoleID"])
        Tier3 = int(Config.CONFIG["Discord"]["Tier3RoleID"])
        BotRole = int(Config.CONFIG["Discord"]["BotRoleID"])
        GiftedTier1 = int(Config.CONFIG["Discord"]["GiftedTier1RoleID"])
        GiftedTier3 = int(Config.CONFIG["Discord"]["GiftedTier3RoleID"])
        Mod = int(Config.CONFIG["Discord"]["ModRoleID"])

        await interaction.response.send_message("Choosing random gifted sub winners...")
        potential_winners = []
        for member in interaction.channel.members:
            can_win = True
            for role in member.roles:
                if role.id in [
                    Tier1,
                    Tier2,
                    Tier3,
                    BotRole,
                    GiftedTier1,
                    GiftedTier3,
                    Mod,
                ]:
                    can_win = False

            if can_win:
                potential_winners.append(member.mention)

        winners = random.choices(potential_winners, k=num_winners)
        for winner in winners:
            await interaction.channel.send(
                f"{oprah} has gifted {winner} a T1 Subscription!"
            )

    @app_commands.command(name="start")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(raffle_type="Raffle Type (default: normal)")
    async def start(
        self, interaction: Interaction, raffle_type: RaffleType = RaffleType.normal
    ):
        """Starts a new raffle"""

        if DB().has_ongoing_raffle(interaction.guild.id):
            await interaction.response.send_message(
                "There is already an ongoing raffle!"
            )
            return

        modal = NewRaffleModal(raffle_type=raffle_type)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="end")
    @app_commands.checks.has_role("Mod")
    async def end(
        self,
        interaction: Interaction,
        num_winners: int = 1,
    ) -> None:
        """Closes an existing raffle and pick the winner(s)"""

        if not DB().has_ongoing_raffle(interaction.guild.id):
            await interaction.response.send_message(
                "There is no ongoing raffle! You need to start a new one."
            )
            return

        raffle_message_id = DB().get_raffle_message_id(interaction.guild.id)
        if raffle_message_id is None:
            await interaction.response.send_message(
                "Oops! That raffle does not exist anymore."
            )
            return

        await RaffleController._end_raffle_impl(
            interaction, raffle_message_id, num_winners
        )
        DB().close_raffle(interaction.guild.id, end_time=datetime.now())

    @app_commands.command(name="add_reward")
    @app_commands.checks.has_role("Mod")
    async def add_reward(self, interaction: Interaction):
        """Creates new channel reward for redemption"""
        modal = AddRewardModal()
        await interaction.response.send_modal(modal)

    @app_commands.command(name="remove_reward")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(name="Name of reward to remove")
    async def remove_reward(self, interaction: Interaction, name: str):
        """Removes channel reward for redemption"""
        DB().remove_channel_reward(name)
        await interaction.response.send_message(
            f"Successfully removed {name}!", ephemeral=True
        )

    @app_commands.command(name="allow_redemptions")
    @app_commands.checks.has_role("Mod")
    async def allow_redemptions(self, interaction: Interaction):
        """Allow rewards to be redeemed"""
        DB().allow_redemptions()
        await interaction.response.send_message(
            "Redemptions are now enabled", ephemeral=True
        )

    @app_commands.command(name="pause_redemptions")
    @app_commands.checks.has_role("Mod")
    async def pause_redemptions(self, interaction: Interaction):
        """Pause rewards from being redeemed"""
        DB().pause_redemptions()
        await interaction.response.send_message(
            "Redemptions are now paused", ephemeral=True
        )

    @app_commands.command(name="check_redemption_status")
    @app_commands.checks.has_role("Mod")
    async def check_redemption_status(self, interaction: Interaction):
        """Check whether or not rewards are eligible to be redeemed"""
        status = DB().check_redemption_status()
        status_message = "allowed" if status else "paused"
        await interaction.response.send_message(
            f"Redemptions are currently {status_message}.", ephemeral=True
        )

    @app_commands.command(name="start_prediction")
    @app_commands.checks.has_role("Mod")
    async def start_prediction(self, interaction: Interaction):
        """Start new prediction"""
        if DB().has_ongoing_prediction(interaction.guild_id):
            return await interaction.response.send_message(
                "There is already an ongoing prediction!", ephemeral=True
            )
        await interaction.response.send_modal(CreatePredictionModal(self.client))

    @app_commands.command(name="refund_prediction")
    @app_commands.checks.has_role("Mod")
    async def refund_prediction(self, interaction: Interaction):
        """Refund ongoing prediction, giving users back the points they wagered"""
        await PredictionController.refund_prediction(interaction, self.client)

    @app_commands.command(name="close_prediction")
    @app_commands.checks.has_role("Mod")
    async def close_prediction(self, interaction: Interaction):
        """CLOSE PREDICTION"""
        await PredictionController.close_prediction(interaction.guild_id)
        prediction_id = DB().get_ongoing_prediction_id(interaction.guild_id)
        prediction_message_id = DB().get_prediction_message_id(prediction_id)
        prediction_channel_id = DB().get_prediction_channel_id(prediction_id)
        prediction_message = await self.client.get_channel(
            prediction_channel_id
        ).fetch_message(prediction_message_id)

        await prediction_message.reply("Prediction closed!")
        await interaction.response.send_message("Prediction closed!", ephemeral=True)

    @app_commands.command(name="payout_prediction")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(option="Option to payout")
    async def payout_prediction(
        self, interaction: Interaction, option: PredictionChoice
    ):
        """Payout predicton to option pink or blue"""
        await PredictionController.payout_prediction(option, interaction, self.client)

    @app_commands.command(name="redo_payout")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(option="Option to payout")
    async def redo_payout(self, interaction: Interaction, option: PredictionOutcome):
        """Redo the last prediction's payout"""
        await PredictionController.redo_payout(option, interaction, self.client)

    @app_commands.command(name="set_chat_mode")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(mode="Chat Mode")
    async def set_chat_mode(self, interaction: Interaction, mode: ChannelPerms):
        stream_chat_id = 1037040541017309225

        t3_role_role = interaction.guild.get_role(1036807951484203099)
        gifted_t3_role = interaction.guild.get_role(1045466382470484040)
        twitch_t3 = interaction.guild.get_role(935319103302926409)

        discord_t2 = interaction.guild.get_role(1036807522457231384)
        gifted_t2 = interaction.guild.get_role(1046886011071905933)
        t2_good_morning = interaction.guild.get_role(1069255940181856327)

        discord_t1 = interaction.guild.get_role(1036801694564102174)
        gifted_t1 = interaction.guild.get_role(1038174011034710128)
        twitch_sub = interaction.guild.get_role(935319103302926406)

        t3_subs = [t3_role_role, gifted_t3_role, twitch_t3]
        t2_subs = [discord_t2, gifted_t2, t2_good_morning]
        t1_subs = [discord_t1, gifted_t1, twitch_sub]

        all_subs = t3_subs + t2_subs + t1_subs

        everyone = interaction.guild.get_role(915336728707989534)

        channel = self.client.get_channel(stream_chat_id)

        if mode == ChannelPerms.t3jail:
            for t3 in t3_subs:
                await channel.set_permissions(t3, send_messages=False)

            for t2 in t2_subs:
                await channel.set_permissions(t2, send_messages=True)

            for t1 in t1_subs:
                await channel.set_permissions(t1, send_messages=True)

            await channel.set_permissions(
                everyone,
                create_private_threads=False,
                create_public_threads=False,
                send_messages=True,
                use_external_emojis=False,
                embed_links=False,
                attach_files=False,
                use_external_stickers=False,
            )

        if mode == ChannelPerms.t3chat:
            for t3 in t3_subs:
                await channel.set_permissions(t3, send_messages=True)

            for t2 in t2_subs:
                await channel.set_permissions(t2, send_messages=False)

            for t1 in t1_subs:
                await channel.set_permissions(t1, send_messages=False)

            await channel.set_permissions(
                everyone,
                create_private_threads=False,
                create_public_threads=False,
                send_messages=False,
                use_external_emojis=False,
                embed_links=False,
                attach_files=False,
                use_external_stickers=False,
            )

        if mode == ChannelPerms.off:
            for sub in all_subs:
                await channel.set_permissions(sub, send_messages=False)

            await channel.set_permissions(
                everyone,
                create_private_threads=False,
                create_public_threads=False,
                send_messages=False,
                use_external_emojis=False,
                embed_links=False,
                attach_files=False,
                use_external_stickers=False,
            )

        if mode == ChannelPerms.everyonechat:
            for sub in all_subs:
                await channel.set_permissions(sub, send_messages=True)

            await channel.set_permissions(
                everyone,
                create_private_threads=False,
                create_public_threads=False,
                send_messages=True,
                use_external_emojis=False,
                embed_links=False,
                attach_files=False,
                use_external_stickers=False,
            )

        if mode == ChannelPerms.subchat:
            for sub in all_subs:
                await channel.set_permissions(sub, send_messages=True)

            await channel.set_permissions(
                everyone,
                create_private_threads=False,
                create_public_threads=False,
                send_messages=False,
                use_external_emojis=False,
                embed_links=False,
                attach_files=False,
                use_external_stickers=False,
            )

        await interaction.response.send_message("Done!", ephemeral=True)

    @app_commands.command(name="give_points")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(user="User ID to award points")
    @app_commands.describe(points="Number of points to award")
    @app_commands.describe(reason="Reason for awarding points")
    async def give_points(
        self, interaction: Interaction, user: User, points: int, reason: str = None
    ):
        """Manually give points to user"""
        audit_output = f"{interaction.user.mention} gave {user.mention} {points}pts"
        if reason is not None:
            audit_output += f': "{reason}"'

        if reason is None and not self.check_hooj(interaction):
            return await interaction.response.send_message(
                "Please provide a reason for awarding points", ephemeral=True
            )

        logging.info(POINTS_AUDIT_CHANNEL)
        await self.client.get_channel(POINTS_AUDIT_CHANNEL).send(audit_output)
        success, _ = DB().deposit_points(user.id, points)
        if not success:
            return await interaction.response.send_message(
                "Failed to award points - please try again.", ephemeral=True
            )
        await interaction.response.send_message(
            "Successfully awarded points!", ephemeral=True
        )

    @app_commands.command(name="good_morning_count")
    @app_commands.checks.has_role("Mod")
    async def good_morning_count(self, interaction: Interaction):
        """Check how many users have said good morning today!"""
        count = DB().get_today_morning_count()
        await interaction.response.send_message(
            f"{count} users have said good morning today! {GOOD_MORNING_EXPLANATION}"
        )

    @app_commands.command(name="good_morning_reward")
    @app_commands.checks.has_role("Mod")
    async def good_morning_reward(self, interaction: Interaction):
        """Reward users who have met the 'Good Morning' threshold"""
        await GoodMorningController.reward_users(interaction)

    @app_commands.command(name="good_morning_reset")
    @app_commands.checks.has_role("Mod")
    async def good_morning_reset(self, interaction: Interaction):
        """Reset all weekly good morning points to 0"""
        await GoodMorningController.reset_all_morning_points(interaction)

    @app_commands.command(name="good_morning_increment")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(points="Number of points to award")
    async def good_morning_increment(self, interaction: Interaction, points: int):
        """Give all users a fixed number of good morning points"""
        await GoodMorningController.good_morning_increment(points, interaction)

    @app_commands.command(name="remove_raffle_winner")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(user="User ID to remove win from")
    async def remove_raffle_winner(self, interaction: Interaction, user: User):
        one_week_ago = datetime.now().date() - timedelta(days=6)

        if not DB().remove_raffle_winner(interaction.guild_id, user.id, one_week_ago):
            await interaction.response.send_message(
                "This user has not recently won a raffle!"
            )
            return

        await interaction.response.send_message("Winner removed!")


def publish_poll(title, option_one, option_two, option_three, option_four):
    payload = {
        "title": title,
        "options": [option_one, option_two, option_three, option_four],
    }

    response = requests.post(
        url=PUBLISH_POLL_URL, json=payload, headers={"x-access-token": AUTH_TOKEN}
    )

    if response.status_code != 200:
        LOG.error(f"Failed to publish poll: {response.text}")


def publish_timer(time, direction: TimerDirection):
    payload = {
        "time": time,
        "direction": direction.value,
    }

    response = requests.post(
        url=PUBLISH_TIMER_URL, json=payload, headers={"x-access-token": AUTH_TOKEN}
    )

    if response.status_code != 200:
        LOG.error(f"Failed to publish timer: {response.text}")

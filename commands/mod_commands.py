from asyncio import Lock
from datetime import datetime, timedelta
from typing import Optional
from discord import (
    AllowedMentions,
    Role,
    app_commands,
    Interaction,
    Client,
    User,
    TextChannel,
)
from discord.app_commands.errors import AppCommandError, CheckFailure
from discord.ext import tasks
from commands import t3_commands, viewer_commands
from controllers.good_morning_controller import (
    GoodMorningController,
    GOOD_MORNING_EXPLANATION,
)
from controllers.point_history_controller import PointHistoryController
from controllers.temprole_controller import TempRoleController
from db import DB, RaffleType
from models.transaction import Transaction
from views.raffle.new_raffle_modal import NewRaffleModal
from views.rewards.add_reward_modal import AddRewardModal
from controllers.raffle_controller import RaffleController
from config import YAMLConfig as Config
from util.server_utils import get_base_url
import logging
import random
from threading import Thread
import requests
import enum

LOG = logging.getLogger(__name__)
JOEL_DISCORD_ID = 112386674155122688
HOOJ_DISCORD_ID = 82969926125490176
POINTS_AUDIT_CHANNEL = Config.CONFIG["Discord"]["ChannelPoints"]["PointsAuditChannel"]
TIER1_ROLE = Config.CONFIG["Discord"]["Subscribers"]["Tier1Role"]
TIER2_ROLE = Config.CONFIG["Discord"]["Subscribers"]["Tier2Role"]
TIER3_ROLE = Config.CONFIG["Discord"]["Subscribers"]["Tier3Role"]
BOT_ROLE = Config.CONFIG["Discord"]["Roles"]["Bot"]
GIFTED_TIER1_ROLE = Config.CONFIG["Discord"]["Subscribers"]["GiftedTier1Role"]
GIFTED_TIER3_ROLE = Config.CONFIG["Discord"]["Subscribers"]["GiftedTier3Role"]
MOD_ROLE = Config.CONFIG["Discord"]["Roles"]["Mod"]
# these are hardcoded until raze to radiant is over, or config file changes are allowed
# for testing on own setup, these need to be changed to your appropriate IDs
# HIDDEN_MOD_ROLE should be 1040337265790042172 when committing and refers to the Mod (Role Hidden)
HIDDEN_MOD_ROLE = 1040337265790042172

AUTH_TOKEN = Config.CONFIG["Secrets"]["Server"]["Token"]
PUBLISH_POLL_URL = f"{get_base_url()}/publish-poll"
PUBLISH_TIMER_URL = f"{get_base_url()}/publish-timer"
PUBLISH_CHESS_URL = f"{get_base_url()}/publish-chess"

ACTIVE_DURATION = 5 * 60
ACTIVE_CHATTERS = {}
ACTIVE_T3_CHATTERS = {}

PERMISSION_LOCK = Lock()


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

    @app_commands.command(name="reset_vod_submission")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(user="Discord User to reset vod submission for")
    async def reset_vod_submission(self, interaction: Interaction, user: User) -> None:
        """Allows the given userID to submit a VOD."""
        DB().reset_user(user.id)
        await interaction.response.send_message("Success!", ephemeral=True)

    @app_commands.command(name="chess")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(open_value="1 for yes 0 for no")
    @app_commands.describe(na_score="-1 for no change")
    @app_commands.describe(eu_score="-1 for no change")
    async def chess(
        self, interaction: Interaction, open_value: int, na_score: int, eu_score: int
    ) -> None:
        """Open NA vs NOT NA Chess"""
        Thread(
            target=publish_chess,
            args=(
                open_value,
                na_score,
                eu_score,
            ),
        ).start()

        await interaction.response.send_message("Chess event sent!", ephemeral=True)

    @app_commands.command(name="get_active_chatters")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(amount="Amount of active chatters to get")
    @app_commands.describe(
        t3_only="Whether or not to only select T3 subs (default: False)"
    )
    @app_commands.describe(
        grant_role="The role to temporarily grant all selected chatters"
    )
    @app_commands.describe(
        grant_duration="How long to grant the role for (default: 1h)"
    )
    async def get_active_chatters(
        self,
        interaction: Interaction,
        amount: int,
        t3_only: Optional[bool] = False,
        grant_role: Optional[Role] = None,
        grant_duration: Optional[str] = "1h",
    ) -> None:
        """Returns a given amount of active chatters, can be restricted to an amount and automatically grant a role"""

        try:
            if t3_only:
                active_chatters = list(ACTIVE_T3_CHATTERS.keys())
            else:
                active_chatters = list(ACTIVE_CHATTERS.keys())
            random_chatters = random.sample(active_chatters, amount)
        except Exception as e:
            return await interaction.response.send_message(
                f"An error occurred: {str(e)}", ephemeral=True
            )

        selected = ""
        for user_id in random_chatters:
            member = interaction.guild.get_member(user_id)
            selected += f" {member.mention}"

            if grant_role is not None:
                try:
                    success, message = await TempRoleController(self).set_role(
                        member.id, grant_role, grant_duration
                    )
                except Exception as e:
                    return await interaction.response.send_message(
                        f"An error occurred: {str(e)}", ephemeral=True
                    )
                if not success:
                    return await interaction.response.send_message(
                        f"Failed to grant role: {message}", ephemeral=True
                    )

        send_message = (
            f"The following {amount} active chatters were selected:{selected}."
        )
        if t3_only:
            send_message = (
                f"The following {amount} active T3 chatters were selected:{selected}."
            )

        if grant_role is not None:
            send_message += f" They were granted the role {grant_role.mention} for {grant_duration}."

        if viewer_commands.ACTIVE_CHATTER_KEYWORD is not None:
            send_message += f" Active chatter keyword is set to `{viewer_commands.ACTIVE_CHATTER_KEYWORD}`."

        await interaction.response.send_message(
            send_message,
            ephemeral=True,
            allowed_mentions=AllowedMentions.none(),
        )

    @app_commands.command(name="set_active_chatter_keyword")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(keyword="keyword")
    async def set_active_chatter_keyword(
        self,
        interaction: Interaction,
        keyword: str,
    ) -> None:
        """Sets the keyword to be used for active chatter tracking"""
        viewer_commands.ACTIVE_CHATTER_KEYWORD = keyword
        ACTIVE_CHATTERS.clear()
        ACTIVE_T3_CHATTERS.clear()

        await interaction.response.send_message(
            f"Keyword set to `{viewer_commands.ACTIVE_CHATTER_KEYWORD}`!",
            ephemeral=True,
        )

    @app_commands.command(name="poll")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
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
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(num_winners="num_winners")
    @app_commands.describe(oprah="Oprah")
    async def gift(self, interaction: Interaction, oprah: str, num_winners: int):
        await interaction.response.send_message("Choosing random gifted sub winners...")
        potential_winners = []
        for member in interaction.channel.members:
            can_win = True
            for role in member.roles:
                if role.id in [
                    TIER1_ROLE,
                    TIER2_ROLE,
                    TIER3_ROLE,
                    BOT_ROLE,
                    GIFTED_TIER1_ROLE,
                    GIFTED_TIER3_ROLE,
                    MOD_ROLE,
                    HIDDEN_MOD_ROLE,
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
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
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
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
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
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    async def add_reward(self, interaction: Interaction):
        """Creates new channel reward for redemption"""
        modal = AddRewardModal()
        await interaction.response.send_modal(modal)

    @app_commands.command(name="remove_reward")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(name="Name of reward to remove")
    async def remove_reward(self, interaction: Interaction, name: str):
        """Removes channel reward for redemption"""
        DB().remove_channel_reward(name)
        await interaction.response.send_message(
            f"Successfully removed {name}!", ephemeral=True
        )

    @app_commands.command(name="allow_redemptions")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    async def allow_redemptions(self, interaction: Interaction):
        """Allow rewards to be redeemed"""
        DB().allow_redemptions()
        await interaction.response.send_message(
            "Redemptions are now enabled", ephemeral=True
        )

    @app_commands.command(name="pause_redemptions")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    async def pause_redemptions(self, interaction: Interaction):
        """Pause rewards from being redeemed"""
        DB().pause_redemptions()
        await interaction.response.send_message(
            "Redemptions are now paused", ephemeral=True
        )

    @app_commands.command(name="check_redemption_status")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    async def check_redemption_status(self, interaction: Interaction):
        """Check whether or not rewards are eligible to be redeemed"""
        status = DB().check_redemption_status()
        status_message = "allowed" if status else "paused"
        await interaction.response.send_message(
            f"Redemptions are currently {status_message}.", ephemeral=True
        )

    @app_commands.command(name="set_chat_mode")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(mode="Chat Mode")
    @app_commands.describe(channel="Channel")
    async def set_chat_mode(
        self, interaction: Interaction, mode: ChannelPerms, channel: TextChannel
    ):
        await PERMISSION_LOCK.acquire()
        try:
            await interaction.response.send_message(
                "Updating chat mode...", ephemeral=True
            )

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

            channel = self.client.get_channel(channel.id)

            if mode == ChannelPerms.t3jail:
                for t3 in t3_subs:
                    await channel.set_permissions(
                        t3, send_messages=False, view_channel=True
                    )

                for t2 in t2_subs:
                    await channel.set_permissions(t2, view_channel=True)

                for t1 in t1_subs:
                    await channel.set_permissions(t1, view_channel=True)

                await channel.set_permissions(
                    everyone,
                    create_private_threads=False,
                    create_public_threads=False,
                    use_external_emojis=False,
                    embed_links=False,
                    attach_files=False,
                    use_external_stickers=False,
                )

            if mode == ChannelPerms.t3chat:
                for t3 in t3_subs:
                    await channel.set_permissions(
                        t3, send_messages=True, view_channel=True
                    )

                for t2 in t2_subs:
                    await channel.set_permissions(
                        t2, send_messages=False, view_channel=False
                    )

                for t1 in t1_subs:
                    await channel.set_permissions(
                        t1, send_messages=False, view_channel=False
                    )

                await channel.set_permissions(
                    everyone,
                    view_channel=False,
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
                    await channel.set_permissions(
                        sub, send_messages=False, view_channel=False
                    )

                await channel.set_permissions(
                    everyone,
                    view_channel=False,
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
                    await channel.set_permissions(
                        sub, send_messages=True, view_channel=True
                    )

                await channel.set_permissions(
                    everyone,
                    view_channel=True,
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
                    await channel.set_permissions(
                        sub, send_messages=True, view_channel=True
                    )

                await channel.set_permissions(
                    everyone,
                    view_channel=False,
                    create_private_threads=False,
                    create_public_threads=False,
                    send_messages=False,
                    use_external_emojis=False,
                    embed_links=False,
                    attach_files=False,
                    use_external_stickers=False,
                )
        finally:
            PERMISSION_LOCK.release()

    @app_commands.command(name="give_points")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
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

        await self.client.get_channel(POINTS_AUDIT_CHANNEL).send(audit_output)
        success, new_balance = DB().deposit_points(user.id, points)
        if not success:
            return await interaction.response.send_message(
                "Failed to award points - please try again.", ephemeral=True
            )
        PointHistoryController.record_transaction(
            Transaction(
                user.id, points, new_balance - points, new_balance, "Give Points"
            )
        )
        await interaction.response.send_message(
            "Successfully awarded points!", ephemeral=True
        )

    @app_commands.command(name="good_morning_increment")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(points="Number of points to award")
    async def good_morning_increment(self, interaction: Interaction, points: int):
        """Give all users a fixed number of good morning points"""
        await GoodMorningController.good_morning_increment(points, interaction)

    @app_commands.command(name="remove_raffle_winner")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(user="User ID to remove win from")
    async def remove_raffle_winner(self, interaction: Interaction, user: User):
        one_week_ago = datetime.now().date() - timedelta(days=6)

        if not DB().remove_raffle_winner(interaction.guild_id, user.id, one_week_ago):
            await interaction.response.send_message(
                "This user has not recently won a raffle!"
            )
            return

        await interaction.response.send_message("Winner removed!")

    @app_commands.command(name="enable_tts_redemptions")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    async def enable_tts_redemptions(self, interaction: Interaction) -> None:
        """Enables the T3 TTS redemption"""
        t3_commands.T3_TTS_ENABLED = True

        await interaction.response.send_message(
            "T3 TTS redemption enabled!", ephemeral=True
        )

    @app_commands.command(name="disable_tts_redemptions")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    async def disable_tts_redemptions(self, interaction: Interaction) -> None:
        """Disables the T3 TTS redemption until it is reenabled with the enable command or by a bot restart"""
        t3_commands.T3_TTS_ENABLED = False

        await interaction.response.send_message(
            "T3 TTS redemption disabled!", ephemeral=True
        )

    @app_commands.command(name="set_tts_cost")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(
        cost="The cost to use T3 TTS redemption. Set to 10k by default."
    )
    async def set_tts_cost(self, interaction: Interaction, cost: int) -> None:
        """Temporarily sets the cost of the T3 TTS redemption. Cost resets to 10k on bot restarts."""
        t3_commands.T3_TTS_REQUIRED_POINTS = cost

        await interaction.response.send_message(
            f"T3 TTS cost set to {cost} points! Will reset to 10k points on bot restart.",
            ephemeral=True,
        )


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


def publish_chess(openValue, na, eu):
    payload = {"open": openValue, "naScore": na, "euScore": eu}

    response = requests.post(
        url=PUBLISH_CHESS_URL, json=payload, headers={"x-access-token": AUTH_TOKEN}
    )

    if response.status_code != 200:
        LOG.error(f"Failed to publish chess: {response.text}")


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


@tasks.loop(seconds=30)
async def remove_inactive_chatters():
    for user_id, time in list(ACTIVE_CHATTERS.items()):
        if time < (datetime.now() - timedelta(seconds=ACTIVE_DURATION)).timestamp():
            del ACTIVE_CHATTERS[user_id]
            try:
                del ACTIVE_T3_CHATTERS[user_id]
            except Exception:
                pass

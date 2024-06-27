from discord import Colour, Member, app_commands, Interaction, Client, AllowedMentions
from discord.app_commands import Choice, Range
from typing import Optional
from controllers.good_morning_controller import GoodMorningController
from controllers.point_history_controller import PointHistoryController
from controllers.predictions.prediction_entry_controller import (
    PredictionEntryController,
)
from controllers.temprole_controller import TempRoleController
from db import DB
from db.models import PredictionChoice
from models.transaction import Transaction
from util.discord_utils import DiscordUtils
from views.rewards.redeem_reward_view import RedeemRewardView
from threading import Thread
import requests
import logging
import datetime
import time
from pytz import timezone
from config import YAMLConfig as Config
from discord.app_commands.errors import AppCommandError, CheckFailure
from util.server_utils import get_base_url

from views.vod_submission.vod_submission_modal import NewVodSubmissionModal

LOG = logging.getLogger(__name__)

POKEMON_THREAD_ID = 1233467109485314150
PUBLISH_POLL_URL = f"{get_base_url()}/publish-poll-answer"
POKEMON_PUBLISH_URL = f"{get_base_url()}/publish-streamdeck"

HIDDEN_MOD_ROLE = 1040337265790042172
STAFF_DEVELOPER_ROLE = 1226317841272279131
MOD_ROLE = Config.CONFIG["Discord"]["Roles"]["Mod"]
GIFTED_T2_ROLE = Config.CONFIG["Discord"]["Subscribers"]["GiftedTier2Role"]
TEMPROLE_AUDIT_CHANNEL = 1225769539267199026

AUTH_TOKEN = Config.CONFIG["Secrets"]["Server"]["Token"]

# It's stupid that it's here but I don't know how else to make it work
ACTIVE_CHATTER_KEYWORD = None

PACIFIC_TZ = timezone("US/Pacific")
# Number representing day of the week, from 0 through to 6
VOD_REVIEW_DAY = 3
VOD_REVIEW_DAY_END = 23

GIFTED_T2_ENABLED = True
GIFTED_T2_REQUIRED_POINTS = 50000


@app_commands.guild_only()
class ViewerCommands(app_commands.Group, name="hooj"):
    def __init__(self, tree: app_commands.CommandTree, client: Client) -> None:
        super().__init__()
        self.tree = tree
        self.client = client

    async def on_error(self, interaction: Interaction, error: AppCommandError):
        if isinstance(error, CheckFailure):
            return await interaction.response.send_message(
                "Failed to perform command - please verify permissions.", ephemeral=True
            )
        logging.error(error)
        return await super().on_error(interaction, error)

    @app_commands.command(name="redeem")
    async def redeem_reward(self, interaction: Interaction):
        """Redeem an available channel reward"""
        redemptions_allowed = DB().check_redemption_status()
        if not redemptions_allowed:
            return await interaction.response.send_message(
                "Sorry! Reward redemptions are currently paused. Try again during"
                " stream!",
                ephemeral=True,
            )

        rewards = DB().get_channel_rewards()
        user_points = DB().get_point_balance(interaction.user.id)
        view = RedeemRewardView(user_points, rewards, self.client)
        await interaction.response.send_message(
            f"You currently have {user_points} points", view=view, ephemeral=True
        )

    @app_commands.command(name="list_rewards")
    async def list_rewards(self, interaction: Interaction):
        """List all available channel rewards"""
        rewards = DB().get_channel_rewards()
        return_message = "The rewards currently available to redeem are:\n\n"
        for reward in rewards:
            return_message += f"({reward.point_cost}) {reward.name}\n"
        await interaction.response.send_message(return_message, ephemeral=True)

    @app_commands.command(name="point_balance")
    async def point_balance(self, interaction: Interaction):
        """Get your current number of channel points"""
        user_points = DB().get_point_balance(interaction.user.id)
        await interaction.response.send_message(
            f"You currently have {user_points} points", ephemeral=True
        )

    @app_commands.command(name="vote")
    @app_commands.choices(
        option_number=[
            Choice(name="1", value=1),
            Choice(name="2", value=2),
            Choice(name="3", value=3),
            Choice(name="4", value=4),
        ]
    )
    async def vote(self, interaction: Interaction, option_number: int):
        """Places your vote on the thing, if you revote it updates your choice"""
        Thread(
            target=publish_poll_answer,
            args=(
                interaction.user.id,
                option_number,
                [r.id for r in interaction.user.roles],
            ),
        ).start()

        await interaction.response.send_message("Poll answer sent!", ephemeral=True)

    @app_commands.command(name="submit_vod")
    async def start(self, interaction: Interaction):
        """Opens the VOD Submission Prompt"""
        today = datetime.datetime.now(PACIFIC_TZ)
        # Disable submissions on vod review day and inform user what time they can submit again
        if today.weekday() == VOD_REVIEW_DAY:
            today = today.replace(hour=VOD_REVIEW_DAY_END, minute=0)
            vod_review_date = (
                today + datetime.timedelta((VOD_REVIEW_DAY - today.weekday()) % 7)
            ).astimezone(timezone("UTC"))
            unixtime = time.mktime(vod_review_date.timetuple())

            return await interaction.response.send_message(
                f"No new vods are accepted on vod review day, you can submit again at <t:{unixtime:.0f}:f>",
                ephemeral=True,
            )
        modal = NewVodSubmissionModal(self.client)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="bet")
    @app_commands.describe(choice="Choice to bet points on")
    @app_commands.describe(points="Number of channel points to bet")
    async def bet(
        self, interaction: Interaction, choice: PredictionChoice, points: int
    ):
        """Place bet on currently ongoing prediction"""
        await interaction.response.defer(thinking=True, ephemeral=True)
        success = await PredictionEntryController.create_prediction_entry(
            points, choice, interaction, self.client
        )

        if not success:
            return

    @app_commands.command(name="pokemon")
    @app_commands.describe(move="Button to press")
    @app_commands.describe(amount="Times to press (only affects movement keys)")
    @app_commands.choices(
        move=[
            Choice(name="A", value="A"),
            Choice(name="B", value="B"),
            Choice(name="Start", value="Start"),
            Choice(name="Select", value="Select"),
            Choice(name="Right", value="Right"),
            Choice(name="Left", value="Left"),
            Choice(name="Up", value="Up"),
            Choice(name="Down", value="Down"),
            Choice(name="R", value="R"),
            Choice(name="L", value="L"),
        ]
    )
    async def pokemon_move(
        self,
        interaction: Interaction,
        move: str,
        amount: Optional[Range[int, 1, 9]] = 1,
    ):
        """Send a move to the Pokemon game"""
        if move not in ["Right", "Left", "Up", "Down"]:
            amount = 1

        Thread(
            target=publish_pokemon_move,
            args=(interaction.user.display_name, move, amount),
        ).start()

        await interaction.guild.get_thread(POKEMON_THREAD_ID).send(
            f"{interaction.user.mention} played: {move} {amount} times!",
            allowed_mentions=AllowedMentions.none(),
        )

        await interaction.response.send_message(
            f"Successfully sent move: {move} {amount} times!", ephemeral=True
        )

    @app_commands.command(name="good_morning")
    async def good_morning(self, interaction: Interaction):
        """Say good morning! Check #good-morning-faq for details"""
        await GoodMorningController.accrue_good_morning(interaction)

    @app_commands.command(name="good_morning_points")
    async def good_morning_points(self, interaction: Interaction):
        """Check your current good morning points! Check #good-morning-faq for details"""
        await GoodMorningController.get_morning_points(interaction)

    @app_commands.command(name="gift_t2")
    @app_commands.describe(member="The member to gift 1 month of T2 to.")
    async def gift_t2(self, interaction: Interaction, member: Member) -> None:
        """Gift a member 1 month of T2 subscription (costs 50k Hoojbucks normally)"""

        if GIFTED_T2_ENABLED == False:
            return await interaction.response.send_message(
                f"Gifting T2 is currently disabled.",
                ephemeral=True,
            )

        required_points = GIFTED_T2_REQUIRED_POINTS

        if any(
            role.id in [MOD_ROLE, HIDDEN_MOD_ROLE, STAFF_DEVELOPER_ROLE]
            for role in interaction.user.roles
        ):
            required_points = 0

        user_points = DB().get_point_balance(interaction.user.id)
        if not user_points:
            return await interaction.response.send_message(
                "Failed to retrieve point balance - please try again.", ephemeral=True
            )

        if user_points < required_points:
            return await interaction.response.send_message(
                f"You need {required_points} points to redeem a TTS message. You currently have: {user_points}",
                ephemeral=True,
            )

        if required_points > 0:
            success, balance = DB().withdraw_points(
                interaction.user.id, required_points
            )
            if not success:
                return await interaction.response.send_message(
                    "Failed to redeem reward - please try again.", ephemeral=True
                )

            PointHistoryController.record_transaction(
                Transaction(
                    interaction.user.id,
                    -required_points,
                    user_points,
                    balance,
                    "TTS Redemption",
                )
            )
        else:
            balance = DB().get_point_balance(interaction.user.id)

        gifted_role = interaction.guild.get_role(GIFTED_T2_ROLE)
        success, message = await TempRoleController.extend_role(
            member._user, gifted_role, "31d"
        )

        audit_channel = interaction.guild.get_channel(TEMPROLE_AUDIT_CHANNEL)
        await DiscordUtils.audit(
            interaction=interaction,
            user=interaction.user,
            message=f"{member.name} (ID {member.id}) has been gifted one month of T2 by {interaction.user.name} (ID {interaction.user.id})",
            color=Colour.green(),
            channel=audit_channel,
        )

        if not success:
            return await interaction.response.send_message(
                f"Failed to gift T2: {message}", ephemeral=True
            )

        await interaction.response.send_message(
            f"{member.mention} has been gifted one month of T2 by {interaction.user.mention}!"
        )


def publish_poll_answer(user_id, choice, roles):
    """
    Option Number is 1-indexed
    {
        "userID": 12938123,
        "optionNumber": 1,
        "userRoleIDs": [123, 823, 231, 293]
    }
    """
    payload = {
        "userID": user_id,
        "optionNumber": choice,
        "userRoleIDs": roles,
    }

    response = requests.post(
        url=PUBLISH_POLL_URL, json=payload, headers={"x-access-token": AUTH_TOKEN}
    )

    if response.status_code != 200:
        LOG.error(f"Failed to publish poll answer: {response.text}")


def publish_pokemon_move(user_name, move, number):
    payload = {
        "type": "pokemon-move",
        "move": move,
        "userName": user_name,
        "number": number,
    }

    response = requests.post(
        url=POKEMON_PUBLISH_URL, json=payload, headers={"x-access-token": AUTH_TOKEN}
    )

    if response.status_code != 200:
        LOG.error(f"Failed to publish pokemon move: {response.text}")

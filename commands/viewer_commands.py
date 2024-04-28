from discord import app_commands, Interaction, Client, AllowedMentions
from discord.app_commands import Choice, Range
from typing import Optional
from controllers.good_morning_controller import GoodMorningController
from controllers.predictions.prediction_entry_controller import (
    PredictionEntryController,
)
from db import DB
from db.models import PredictionChoice
from views.rewards.redeem_reward_view import RedeemRewardView
from threading import Thread
import requests
import logging
from config import YAMLConfig as Config
from discord.app_commands.errors import AppCommandError, CheckFailure
from util.server_utils import get_base_url

from views.vod_submission.vod_submission_modal import NewVodSubmissionModal

LOG = logging.getLogger(__name__)

POKEMON_THREAD_ID = 1233467109485314150
PUBLISH_POLL_URL = f"{get_base_url()}/publish-poll-answer"
POKEMON_PUBLISH_URL = f"{get_base_url()}/publish-streamdeck"

AUTH_TOKEN = Config.CONFIG["Secrets"]["Server"]["Token"]

# It's stupid that it's here but I don't know how else to make it work
ACTIVE_CHATTER_KEYWORD = None


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

        await interaction.response.send_message(
            "VOD Submissions are currently closed until Hooj has hit Radiant!",
            ephemeral=True,
        )
        return

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

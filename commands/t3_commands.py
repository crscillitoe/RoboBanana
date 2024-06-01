import re
from threading import Thread
from discord import (
    app_commands,
    Interaction,
    Client,
)
from discord.app_commands.errors import AppCommandError, CheckFailure
import enum

import requests

from controllers.point_history_controller import PointHistoryController
from db import DB
from config import YAMLConfig as Config
import logging

from models.transaction import Transaction
from util.server_utils import get_base_url
from views.rewards.redeem_tts_view import RedeemTTSView

LOG = logging.getLogger(__name__)

PUBLISH_URL = f"{get_base_url()}/publish-streamdeck"
AUTH_TOKEN = Config.CONFIG["Secrets"]["Server"]["Token"]


class VoiceAI(enum.Enum):
    Brad = "XPbvdPpvVOOvvOgaEkUH"
    Penflash = "wfj4mbx3FyRr0vexLOne"
    Zammey = "kHJKvB4RUxjPGdVzk2zm"
    Dunkel = "fdbOZcQA0oWqnGGHHQWX"
    Lily = "9s2MtAKWAcnqeGs40PUF"
    Zendikar = "4buL9d7MYa8n9JHLaR33"
    Gallomancer = "DNeMEYNTm7bcNbHypgqb"
    Doran = "KUQLVcPb4XIWEYZ3k5KH"
    Rare = "mkCayQGnpQ76siqz2ADL"
    Bread = "IFuhhf9MMNJdHeGo5gmc"
    Dune = "Cy75Wpk4KAnCucPsDmQK"
    Ulius = "iaQJDqRU1tDyF3NIhqsE"
    noodabooda = "zZnQVN1B20Q4qqE0fg8e"
    Woohoojin = "7ZWN6n7MF2qj1tgTiosb"
    PeppaPig = "rCmVtv8cYU60uhlsOo1M"
    LuckyGood = "SyxY6Mf6tHxMbEqcVguz"
    LuckyFried = "4yqaHlXmTcFs0xjmQ6if"


class EmoteAnimation(enum.Enum):
    Fountains = "fountains"
    Fireworks = "fireworks"


T3_ROLE = Config.CONFIG["Discord"]["Subscribers"]["Tier3Role"]
GIFTED_T3_ROLE = Config.CONFIG["Discord"]["Subscribers"]["GiftedTier3Role"]
TWITCH_T3_ROLE = Config.CONFIG["Discord"]["Subscribers"]["TwitchTier3Role"]

HIDDEN_MOD_ROLE = 1040337265790042172
STAFF_DEVELOPER_ROLE = 1226317841272279131
MOD_ROLE = Config.CONFIG["Discord"]["Roles"]["Mod"]

T3_TTS_ENABLED = True
T3_TTS_REQUIRED_POINTS = 10000

T3_EMOTE_ANIMATION_ENABLED = True
T3_EMOTE_ANIMATION_REQUIRED_POINTS = 10000
CUSTOM_EMOTE_PATTERN = re.compile("(<a?:\w+:\d{17,19}>?)")


@app_commands.guild_only()
class T3Commands(app_commands.Group, name="tier3"):
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

    @app_commands.command(name="dnd")
    @app_commands.checks.has_any_role(
        T3_ROLE,
        GIFTED_T3_ROLE,
        TWITCH_T3_ROLE,
        MOD_ROLE,
        HIDDEN_MOD_ROLE,
        STAFF_DEVELOPER_ROLE,
    )
    @app_commands.describe(voice="The voice your character will use in the overlay")
    @app_commands.describe(
        use_spells="Set to True if you are comfortable with spell casting"
    )
    async def dnd(
        self, interaction: Interaction, voice: VoiceAI, use_spells: bool
    ) -> None:
        """Enter the raffle to play DND live on stream"""

        Thread(
            target=publish_dnd,
            args=(interaction.user.id, voice.value, use_spells),
        ).start()

        return await interaction.response.send_message(
            "You have entered the DND raffle!", ephemeral=True
        )

    @app_commands.command(name="tts")
    @app_commands.checks.has_any_role(
        T3_ROLE,
        GIFTED_T3_ROLE,
        TWITCH_T3_ROLE,
        MOD_ROLE,
        HIDDEN_MOD_ROLE,
        STAFF_DEVELOPER_ROLE,
    )
    @app_commands.describe(voice="The voice to use for the TTS message.")
    async def tts(self, interaction: Interaction, voice: VoiceAI) -> None:
        """Submit a phrase to be read out on stream by TTS system"""

        if T3_TTS_ENABLED == False:
            return await interaction.response.send_message(
                f"The TTS redemption is currently disabled.",
                ephemeral=True,
            )

        required_points = T3_TTS_REQUIRED_POINTS

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

        modal = RedeemTTSView(
            user_points, voice.value, voice.name, required_points, self.client
        )
        await interaction.response.send_modal(modal)

    @app_commands.command(name="emote_animation")
    @app_commands.checks.has_any_role(
        T3_ROLE,
        GIFTED_T3_ROLE,
        TWITCH_T3_ROLE,
        MOD_ROLE,
        HIDDEN_MOD_ROLE,
        STAFF_DEVELOPER_ROLE,
    )
    @app_commands.describe(animation="The emote animation to play.")
    @app_commands.describe(
        emote="Must be at least one custom emote. Not all animations support multiple emote, defaulting to the first."
    )
    async def emote_animation(
        self, interaction: Interaction, animation: EmoteAnimation, emote: str
    ) -> None:
        """Pay to play an emote animation on stream"""

        if T3_EMOTE_ANIMATION_ENABLED == False:
            return await interaction.response.send_message(
                f"The emote animation redemption is currently disabled.",
                ephemeral=True,
            )

        required_points = T3_EMOTE_ANIMATION_REQUIRED_POINTS

        custom_emotes = CUSTOM_EMOTE_PATTERN.findall(emote)
        if len(custom_emotes) == 0:
            return await interaction.response.send_message(
                f"Please provide at least one custom emote for the emote animation.",
                ephemeral=True,
            )

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
                    self.user_points,
                    balance,
                    "TTS Redemption",
                )
            )
        else:
            balance = DB().get_point_balance(interaction.user.id)

        custom_emote_links = []
        for emote in custom_emotes:
            custom_emote_type = "gif" if emote.startswith("<a") else "png"
            custom_emote_id = emote.split(":")[-1].replace(">", "")
            custom_emote_links.append(
                f"https://cdn.discordapp.com/emojis/{custom_emote_id}.{custom_emote_type}"
            )

        Thread(
            target=publish_emote_animation,
            args=(animation.value, custom_emote_links),
        ).start()

        await interaction.response.send_message(
            f"Emote animation redeemed! You have {balance} points remaining after spending {required_points}.",
            ephemeral=True,
        )


def publish_emote_animation(animation: str, emotes: list[str]):
    payload = {
        "type": "happy-emotes",
        "location": "special",
        "animation": animation,
        "emotes": ",".join(emotes),
    }

    response = requests.post(
        url=PUBLISH_URL, json=payload, headers={"x-access-token": AUTH_TOKEN}
    )

    if response.status_code != 200:
        LOG.error(f"Failed to publish emote animation: {response.text}")


def publish_dnd(user_id: str, voice_id: str, can_mage: bool):
    payload = {
        "type": "dnd",
        "user_id": user_id,
        "voice_id": voice_id,
        "can_mage": can_mage,
    }

    response = requests.post(
        url=PUBLISH_URL, json=payload, headers={"x-access-token": AUTH_TOKEN}
    )

    if response.status_code != 200:
        LOG.error(f"Failed to dnd: {response.text}")

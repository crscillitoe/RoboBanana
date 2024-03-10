from copy import copy
from typing import Optional
from discord import (
    Color,
    Embed,
    Guild,
    app_commands,
    Interaction,
    Client,
    User,
)
from discord.app_commands.errors import AppCommandError, CheckFailure
import enum

from db import DB
from config import YAMLConfig as Config
import logging
from util.discord_utils import DiscordUtils

from views.rewards.redeem_tts_view import RedeemTTSView

class VoiceAI(enum.Enum):
    Brad = "XPbvdPpvVOOvvOgaEkUH"
    Penflash = "wfj4mbx3FyRr0vexLOne"
    Zammey = "kHJKvB4RUxjPGdVzk2zm"
    Dunkel = "fdbOZcQA0oWqnGGHHQWX"
    Lily = "9s2MtAKWAcnqeGs40PUF"
    Zendikar = "4buL9d7MYa8n9JHLaR33"


T3_ROLE = Config.CONFIG["Discord"]["Subscribers"]["Tier3Role"]
GIFTED_T3_ROLE = Config.CONFIG["Discord"]["Subscribers"]["GiftedTier3Role"]
TWITCH_T3_ROLE = Config.CONFIG["Discord"]["Subscribers"]["TwitchTier3Role"]


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

    @app_commands.command(name="tts")
    @app_commands.checks.has_any_role(T3_ROLE, GIFTED_T3_ROLE, TWITCH_T3_ROLE)
    @app_commands.describe(voice="Voice")
    async def flag_vod(
        self, interaction: Interaction, voice: VoiceAI
    ) -> None:
        """Submit a phrase to be read out on stream by TTS system"""

        user_points = DB().get_point_balance(interaction.user.id)

        required_points = 10000
        if user_points < required_points:
            return await interaction.response.send_message(
                f"You need {required_points} points to redeem a TTS message. You currently have: {user_points}", ephemeral=True
            )

        modal = RedeemTTSView(user_points, voice.value, required_points, self.client)
        await interaction.response.send_modal(modal)

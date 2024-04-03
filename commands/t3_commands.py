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

from views.rewards.redeem_tts_view import RedeemTTSView


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


T3_ROLE = Config.CONFIG["Discord"]["Subscribers"]["Tier3Role"]
GIFTED_T3_ROLE = Config.CONFIG["Discord"]["Subscribers"]["GiftedTier3Role"]
TWITCH_T3_ROLE = Config.CONFIG["Discord"]["Subscribers"]["TwitchTier3Role"]
T3_TTS_ENABLED = True
T3_TTS_REQUIRED_POINTS = 10000


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
    async def flag_vod(self, interaction: Interaction, voice: VoiceAI) -> None:
        """Submit a phrase to be read out on stream by TTS system"""

        if T3_TTS_ENABLED == False:
            return await interaction.response.send_message(
                f"The TTS redemption is currently disabled.",
                ephemeral=True,
            )

        user_points = DB().get_point_balance(interaction.user.id)

        if user_points < T3_TTS_REQUIRED_POINTS:
            return await interaction.response.send_message(
                f"You need {T3_TTS_REQUIRED_POINTS} points to redeem a TTS message. You currently have: {user_points}",
                ephemeral=True,
            )

        modal = RedeemTTSView(
            user_points, voice.value, voice.name, T3_TTS_REQUIRED_POINTS, self.client
        )
        await interaction.response.send_modal(modal)

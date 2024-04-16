from datetime import date, datetime, timedelta
import time
import re
from discord import ChannelType, Guild, Interaction, app_commands, Client
from discord.ext import tasks
import requests
from config import YAMLConfig as Config
import logging
from discord.app_commands.errors import AppCommandError, CheckFailure

from util.command_utils import CommandUtils

LOG = logging.getLogger(__name__)

MARKER_CHANNEL = 1099680985467064360  # Change to config option once RtR is done - 1099680985467064360 on live
MARKER_LOCKOUT_SECONDS = 180
MARKER_SUBTRACT_SECONDS = 60

MOD_ROLE = Config.CONFIG["Discord"]["Roles"]["Mod"]
CHAT_MOD_ROLE = Config.CONFIG["Discord"]["Roles"]["CMChatModerator"]
TRUSTWORTHY = Config.CONFIG["Discord"]["Roles"]["Trustworthy"]
TIER3_ROLE_12MO = Config.CONFIG["Discord"]["Subscribers"]["12MonthTier3Role"]
TIER3_ROLE_18MO = Config.CONFIG["Discord"]["Subscribers"]["18MonthTier3Role"]
# these are hardcoded until raze to radiant is over, or config file changes are allowed
# for testing on own setup, these need to be changed to your appropriate IDs
# HIDDEN_MOD_ROLE should be 1040337265790042172 when committing and refers to the Mod (Role Hidden)
HIDDEN_MOD_ROLE = 1040337265790042172


@app_commands.guild_only()
class MarkerCommands(app_commands.Group, name="marker"):
    STREAM_START_TIME = 0
    CURRENT_THREAD_ID = 0
    THREAD_MESSAGE_ID = 0
    THREAD_TEXT = "0:00 Start"
    LAST_MARKER_TIME = time.time()

    def __init__(self, tree: app_commands.CommandTree, client: Client) -> None:
        super().__init__()
        self.tree = tree
        self.client = client
        self.check_online.start()

    async def on_error(self, interaction: Interaction, error: AppCommandError):
        if isinstance(error, CheckFailure):
            return await interaction.response.send_message(
                "Failed to perform command - please verify permissions.", ephemeral=True
            )
        logging.error(error)
        return await super().on_error(interaction, error)

    @app_commands.command(name="vod_review")
    @app_commands.checks.has_any_role(
        MOD_ROLE,
        HIDDEN_MOD_ROLE,
        CHAT_MOD_ROLE,
        TRUSTWORTHY,
        TIER3_ROLE_12MO,
        TIER3_ROLE_18MO,
    )
    @app_commands.describe(agent="Agent")
    @app_commands.describe(map="Map")
    @app_commands.describe(rank="Player Rank")
    async def vod_review_segment(
        self,
        interaction: Interaction,
        agent: CommandUtils.Agents,
        map: CommandUtils.Maps,
        rank: CommandUtils.Ranks,
    ) -> None:
        """Sets a VOD Review marker"""
        if self.STREAM_START_TIME == 0:
            await interaction.response.send_message(
                f"Stream is not live - please allow up to 3 minutes for the stream to be detected",
                ephemeral=True,
            )
            return
        if (time.time() - MARKER_LOCKOUT_SECONDS) < self.LAST_MARKER_TIME:
            await interaction.response.send_message(
                f"Last marker was set within {MARKER_LOCKOUT_SECONDS} seconds, aborting",
                ephemeral=True,
            )
            return
        self.LAST_MARKER_TIME = time.time()

        formatted_time = self.get_timestamp()
        formatted_full = (
            f"{formatted_time} VOD Review - {agent.value} {map.value} {rank.value}"
        )
        await self.post_to_markers(interaction.guild, formatted_full)
        await interaction.response.send_message(
            f"VOD Review marker set!", ephemeral=True
        )

    @app_commands.command(name="woohoojin_live")
    @app_commands.checks.has_any_role(
        MOD_ROLE,
        HIDDEN_MOD_ROLE,
        CHAT_MOD_ROLE,
        TRUSTWORTHY,
        TIER3_ROLE_12MO,
        TIER3_ROLE_18MO,
    )
    @app_commands.describe(agent="Agent")
    @app_commands.describe(map="Map")
    @app_commands.describe(rank="Hooj Rank")
    async def woohoojin_live_segment(
        self,
        interaction: Interaction,
        agent: CommandUtils.Agents,
        map: CommandUtils.Maps,
        rank: CommandUtils.Ranks,
    ) -> None:
        """Sets a Woohoojin LIVE marker"""
        if self.STREAM_START_TIME == 0:
            await interaction.response.send_message(
                f"Stream is not live - please allow up to 3 minutes for the stream to be detected",
                ephemeral=True,
            )
            return
        if (time.time() - MARKER_LOCKOUT_SECONDS) < self.LAST_MARKER_TIME:
            await interaction.response.send_message(
                f"Last marker was set within {MARKER_LOCKOUT_SECONDS} seconds, aborting",
                ephemeral=True,
            )
            return
        self.LAST_MARKER_TIME = time.time()

        formatted_time = self.get_timestamp()
        formatted_full = (
            f"{formatted_time} Woohoojin LIVE - {agent.value} {map.value} {rank.value}"
        )
        await self.post_to_markers(interaction.guild, formatted_full)
        await interaction.response.send_message(
            f"Woohoojin LIVE marker set!", ephemeral=True
        )

    @app_commands.command(name="live_viewer_ranked")
    @app_commands.checks.has_any_role(
        MOD_ROLE,
        HIDDEN_MOD_ROLE,
        CHAT_MOD_ROLE,
        TRUSTWORTHY,
        TIER3_ROLE_12MO,
        TIER3_ROLE_18MO,
    )
    @app_commands.describe(agent="Agent")
    @app_commands.describe(map="Map")
    @app_commands.describe(rank="Viewer Rank")
    async def live_viewer_ranked_segment(
        self,
        interaction: Interaction,
        agent: CommandUtils.Agents,
        map: CommandUtils.Maps,
        rank: CommandUtils.Ranks,
    ) -> None:
        """Sets a Live Viewer Ranked marker"""
        if self.STREAM_START_TIME == 0:
            await interaction.response.send_message(
                f"Stream is not live - please allow up to 3 minutes for the stream to be detected",
                ephemeral=True,
            )
            return
        if (time.time() - MARKER_LOCKOUT_SECONDS) < self.LAST_MARKER_TIME:
            await interaction.response.send_message(
                f"Last marker was set within {MARKER_LOCKOUT_SECONDS} seconds, aborting",
                ephemeral=True,
            )
            return
        self.LAST_MARKER_TIME = time.time()

        formatted_time = self.get_timestamp()
        formatted_full = f"{formatted_time} Live Viewer Ranked - {agent.value} {map.value} {rank.value}"
        await self.post_to_markers(interaction.guild, formatted_full)
        await interaction.response.send_message(
            f"Live Viewer Ranked marker set!", ephemeral=True
        )

    @app_commands.command(name="team_vs_team")
    @app_commands.checks.has_any_role(
        MOD_ROLE,
        HIDDEN_MOD_ROLE,
        CHAT_MOD_ROLE,
        TRUSTWORTHY,
        TIER3_ROLE_12MO,
        TIER3_ROLE_18MO,
    )
    @app_commands.describe(team_left="Left Team")
    @app_commands.describe(team_right="Right Team")
    @app_commands.describe(map="Map")
    @app_commands.describe(game_nr="Game #")
    async def team_vs_team_segment(
        self,
        interaction: Interaction,
        team_left: str,
        team_right: str,
        map: CommandUtils.Maps,
        game_nr: int,
    ) -> None:
        """Sets a Team VS Team marker"""
        if self.STREAM_START_TIME == 0:
            await interaction.response.send_message(
                f"Stream is not live - please allow up to 3 minutes for the stream to be detected",
                ephemeral=True,
            )
            return
        if (time.time() - MARKER_LOCKOUT_SECONDS) < self.LAST_MARKER_TIME:
            await interaction.response.send_message(
                f"Last marker was set within {MARKER_LOCKOUT_SECONDS} seconds, aborting",
                ephemeral=True,
            )
            return
        self.LAST_MARKER_TIME = time.time()

        formatted_time = self.get_timestamp()
        formatted_full = (
            f"{formatted_time} {team_left} vs {team_right} {map.value} Game {game_nr}"
        )
        await self.post_to_markers(interaction.guild, formatted_full)
        await interaction.response.send_message(
            f"Team VS Team marker set!", ephemeral=True
        )

    @app_commands.command(name="inhouse_block")
    @app_commands.checks.has_any_role(
        MOD_ROLE,
        HIDDEN_MOD_ROLE,
        CHAT_MOD_ROLE,
        TRUSTWORTHY,
        TIER3_ROLE_12MO,
        TIER3_ROLE_18MO,
    )
    @app_commands.describe(type="Viewer Rank")
    @app_commands.describe(agent="Agent")
    @app_commands.describe(map="Map")
    async def inhouse_block_segment(
        self,
        interaction: Interaction,
        type: str,
        agent: CommandUtils.Agents,
        map: CommandUtils.Maps,
    ) -> None:
        """Sets a Inhouse Block marker"""
        if self.STREAM_START_TIME == 0:
            await interaction.response.send_message(
                f"Stream is not live - please allow up to 3 minutes for the stream to be detected",
                ephemeral=True,
            )
            return
        if (time.time() - MARKER_LOCKOUT_SECONDS) < self.LAST_MARKER_TIME:
            await interaction.response.send_message(
                f"Last marker was set within {MARKER_LOCKOUT_SECONDS} seconds, aborting",
                ephemeral=True,
            )
            return
        self.LAST_MARKER_TIME = time.time()

        formatted_time = self.get_timestamp()
        formatted_full = f"{formatted_time} {type} Block - {agent.value} {map.value}"
        await self.post_to_markers(interaction.guild, formatted_full)
        await interaction.response.send_message(
            f"Inhouse Block marker set!", ephemeral=True
        )

    @app_commands.command(name="wildcard")
    @app_commands.checks.has_any_role(
        MOD_ROLE, CHAT_MOD_ROLE, TRUSTWORTHY, TIER3_ROLE_12MO, TIER3_ROLE_18MO
    )
    @app_commands.describe(text="Wildcard text")
    async def wildcard_segment(
        self,
        interaction: Interaction,
        text: str,
    ) -> None:
        """Sets a Wildcard marker (any text)"""
        if self.STREAM_START_TIME == 0:
            await interaction.response.send_message(
                f"Stream is not live - please allow up to 3 minutes for the stream to be detected",
                ephemeral=True,
            )
            return
        if (time.time() - MARKER_LOCKOUT_SECONDS) < self.LAST_MARKER_TIME:
            await interaction.response.send_message(
                f"Last marker was set within {MARKER_LOCKOUT_SECONDS} seconds, aborting",
                ephemeral=True,
            )
            return
        self.LAST_MARKER_TIME = time.time()

        formatted_time = self.get_timestamp()
        formatted_full = f"{formatted_time} {text}"
        await self.post_to_markers(interaction.guild, formatted_full)
        await interaction.response.send_message(f"Wildcard marker set!", ephemeral=True)

    @tasks.loop(seconds=15)
    async def check_online(self):
        check = requests.get("https://decapi.me/twitch/uptime/Woohoojin").text
        if "offline" in check:
            return

        LOG.info("Streamer detected as live!")
        self.check_offline.start()
        self.check_online.stop()

        segments = re.findall(r"\d+", check)
        time = ":".join(segments)
        if len(segments) == 3:
            time = datetime.strptime(time, "%H:%M:%S")
        if len(segments) == 2:
            time = datetime.strptime(time, "%M:%S")
        if len(segments) == 1:
            time = datetime.strptime(time, "%S")

        delta = time - datetime(1900, 1, 1)

        self.STREAM_START_TIME = datetime.now() - delta
        LOG.info(f"Start time: {self.STREAM_START_TIME}")

    @tasks.loop(minutes=1)
    async def check_offline(self):
        check = requests.get("https://decapi.me/twitch/uptime/Woohoojin").text
        if "offline" in check:
            LOG.info("Streamer detected as offline!")
            self.check_online.start()
            self.check_offline.stop()
            self.STREAM_START_TIME = 0.0
            self.CURRENT_THREAD_ID = 0

    def get_timestamp(self) -> str:
        elapsed = datetime.now() - self.STREAM_START_TIME
        nice = str(
            timedelta(seconds=int(elapsed.seconds))
            - timedelta(seconds=MARKER_SUBTRACT_SECONDS)
        )
        return nice

    async def post_to_markers(self, guild: Guild, text: str):
        if self.CURRENT_THREAD_ID == 0:
            start = self.STREAM_START_TIME.strftime("Stream %m/%d/%Y, %H:%M:%S")
            self.CURRENT_THREAD_ID = (
                await guild.get_channel(MARKER_CHANNEL).create_thread(
                    name=start, type=ChannelType.public_thread
                )
            ).id
            msg = await guild.get_thread(self.CURRENT_THREAD_ID).send("0:00 Start")
            self.THREAD_MESSAGE_ID = msg.id

        self.THREAD_TEXT = self.THREAD_TEXT + "\n" + text
        await (
            await guild.get_thread(self.CURRENT_THREAD_ID).fetch_message(
                self.THREAD_MESSAGE_ID
            )
        ).edit(content=self.THREAD_TEXT)

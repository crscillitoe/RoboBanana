from typing import Optional
from discord import app_commands, Interaction, Client, User
from threading import Thread
from config import YAMLConfig as Config
from util.server_utils import get_base_url
import requests
import logging
from discord.app_commands.errors import AppCommandError, CheckFailure

PUBLISH_URL = f"{get_base_url()}/publish-vod"
LOG = logging.getLogger(__name__)
AUTH_TOKEN = Config.CONFIG["Secrets"]["Server"]["Token"]
MOD_ROLE = Config.CONFIG["Discord"]["Roles"]["Mod"]
# these are hardcoded until raze to radiant is over, or config file changes are allowed
# for testing on own setup, these need to be changed to your appropriate IDs
# HIDDEN_MOD_ROLE should be 1040337265790042172 when committing and refers to the Mod (Role Hidden)
HIDDEN_MOD_ROLE = 1040337265790042172


@app_commands.guild_only()
class VodCommands(app_commands.Group, name="vod"):
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

    @app_commands.command(name="start")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(user="Discord User")
    @app_commands.describe(riotid="riotid")
    @app_commands.describe(rank="rank")
    @app_commands.describe(username="Override Discord Display Name")
    async def vod(
        self,
        interaction: Interaction,
        user: User,
        riotid: str,
        rank: str,
        username: Optional[str] = None,
    ) -> None:
        """Start a VOD review for the given username"""
        Thread(
            target=publish_update,
            args=(
                user.display_name if username is None else username,
                user.id,
                riotid,
                rank,
                False,
            ),
        ).start()

        await interaction.response.send_message("VOD start event sent!", ephemeral=True)

    @app_commands.command(name="end")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    async def complete(self, interaction: Interaction) -> None:
        """Start a VOD review for the given username"""
        Thread(
            target=publish_update,
            args=(
                "",
                -1,
                "",
                "",
                True,
            ),
        ).start()

        await interaction.response.send_message(
            "VOD Complete Event sent!", ephemeral=True
        )


def publish_update(username: str, user_id: int, riotid: str, rank: str, complete: bool):
    payload = {
        "username": username,
        "userid": user_id,
        "riotid": riotid,
        "rank": rank,
        "complete": complete,
    }

    response = requests.post(
        url=PUBLISH_URL, json=payload, headers={"x-access-token": AUTH_TOKEN}
    )

    if response.status_code != 200:
        LOG.error(f"Failed to publish updated prediction summary: {response.text}")

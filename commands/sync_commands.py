from discord import Interaction, app_commands, Client
from config import YAMLConfig as Config
from util.sync_utils import SyncUtils
import logging

LOG = logging.getLogger(__name__)

MOD_ROLE = Config.CONFIG["Discord"]["Roles"]["Mod"]


@app_commands.guild_only()
class SyncCommands(app_commands.Group, name="sync"):
    def __init__(self, tree: app_commands.CommandTree, client: Client) -> None:
        super().__init__()
        self.tree = tree
        self.client = client

    @app_commands.command(name="sync")
    @app_commands.checks.has_role(MOD_ROLE)
    async def sync(self, interaction: Interaction) -> None:
        """Manually sync slash commands to guild"""
        guild = interaction.guild
        self.tree.clear_commands(guild=guild)
        SyncUtils.add_commands_to_tree(self.tree, self.client, override=True)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        await interaction.response.send_message("Commands synced", ephemeral=True)

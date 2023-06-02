from discord import app_commands, Interaction, Client, User, ForumTag
from discord.app_commands.errors import AppCommandError, CheckFailure
from discord import Object
from config import Config
import enum
import logging


class VODType(enum.Enum):
    approved = 1
    rejected = 2
    complete = 3


@app_commands.guild_only()
class ManagerCommands(app_commands.Group, name="manager"):
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

    @app_commands.command(name="flag_vod")
    @app_commands.checks.has_role("Community Manager")
    @app_commands.describe(vod_type="VOD Type (Approved/Rejected/Complete)")
    async def art(self, interaction: Interaction, vod_type: VODType) -> None:
        """Flag a VOD as the given type"""

        tag_id = 0
        if vod_type == VODType.approved:
            tag_id = 1055308435882774538
        elif vod_type == VODType.rejected:
            tag_id = 1055365088489508956
        elif vod_type == VODType.complete:
            tag_id = 1055504114978664498

        await interaction.channel.add_tags(Object(id=tag_id))
        await interaction.response.send_message("Applied tag.", ephemeral=True)

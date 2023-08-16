from discord import app_commands, Interaction, Client, User, ForumTag
from discord.app_commands.errors import AppCommandError, CheckFailure
from discord import Object
from config import Config
import enum
import logging

from controllers.temprole_controller import TempRoleController

APPROVED_TAG = int(Config.CONFIG["VODApproval"]["ApprovedTag"])
REJECTED_TAG = int(Config.CONFIG["VODApproval"]["RejectedTag"])
APPROVED_ROLE = int(Config.CONFIG["VODApproval"]["ApprovedRole"])
REJECTED_ROLE = int(Config.CONFIG["VODApproval"]["RejectedRole"])

LOG = logging.getLogger(__name__)


class VODType(enum.Enum):
    approved = 1
    rejected = 2


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
    @app_commands.describe(vod_type="VOD Type (Approved/Rejected)")
    @app_commands.describe(duration="Duration to add to temprole")
    async def flag_vod(
        self, interaction: Interaction, vod_type: VODType, duration: str = "7d"
    ) -> None:
        """Flag a VOD as the given type"""

        if vod_type == VODType.approved:
            await ManagerCommands.process_vod(
                APPROVED_TAG, APPROVED_ROLE, duration, interaction
            )
        elif vod_type == VODType.rejected:
            await ManagerCommands.process_vod(
                REJECTED_TAG, REJECTED_ROLE, duration, interaction
            )

    @staticmethod
    async def process_vod(
        tag_id: int, role_id: int, duration: str, interaction: Interaction
    ):
        role = interaction.guild.get_role(role_id)
        if role is None:
            return await interaction.response.send_message(
                f"Could not find VOD role id={role_id}", ephemeral=True
            )

        owner = interaction.channel.owner
        if owner is None:
            return await interaction.response.send_message(
                "Could not find author of this forum post", ephemeral=True
            )

        await TempRoleController.set_role(owner, role, duration, interaction)

        await interaction.channel.remove_tags(*interaction.channel.applied_tags)
        await interaction.channel.add_tags(Object(id=tag_id))
        response_content = await interaction.original_response()
        await response_content.reply("Applied tag and temprole.")

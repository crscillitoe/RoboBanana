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
from config import YAMLConfig as Config
import enum
import logging
import random
import re

from controllers.temprole_controller import TempRoleController
from controllers.vod_review_bank_controller import VODReviewBankController
from util.discord_utils import DiscordUtils

APPROVED_TAG = Config.CONFIG["Discord"]["VODReview"]["ApprovedTag"]
REJECTED_TAG = Config.CONFIG["Discord"]["VODReview"]["RejectedTag"]
APPROVED_ROLE = Config.CONFIG["Discord"]["VODReview"]["ApprovedRole"]
REJECTED_ROLE = Config.CONFIG["Discord"]["VODReview"]["RejectedRole"]
MOD_ROLE = Config.CONFIG["Discord"]["Roles"]["Mod"]
CM_ROLE = Config.CONFIG["Discord"]["Roles"]["CMChatModerator"]
VOD_TEAM_ROLE = Config.CONFIG["Discord"]["VODReview"]["ReviewerRole"]
USER_ID_PATTERN = re.compile(r"(<@([0-9]+)>)")
# these are hardcoded until raze to radiant is over, or config file changes are allowed
# for testing on own setup, these need to be changed to your appropriate IDs
# HIDDEN_MOD_ROLE should be 1040337265790042172 when committing and refers to the Mod (Role Hidden)
HIDDEN_MOD_ROLE = 1040337265790042172

LOG = logging.getLogger(__name__)


class VODType(enum.Enum):
    approved = 1
    rejected = 2


FIRST_HALF_STARTING_ROUNDS = [1, 2, 3]
FIRST_HALF_NORMAL_ROUNDS_START = 4
FIRST_HALF_NORMAL_ROUNDS_END = 12
SECOND_HALF_STARTING_ROUNDS = [13, 14, 15]
SECOND_HALF_NORMAL_ROUNDS_START = 16


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
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE, CM_ROLE, VOD_TEAM_ROLE)
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

    @app_commands.command(name="add_balance")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(user="Community Manager to add VOD Review credit for")
    @app_commands.describe(duration="Amount of time to add to user's balance")
    async def add_balance(self, interaction: Interaction, user: User, duration: str):
        """Award Gifted T3 credit to Community Manager bank"""
        await VODReviewBankController.add_balance(user, duration, interaction)

    @app_commands.command(name="balance")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE, CM_ROLE, VOD_TEAM_ROLE)
    async def balance(self, interaction: Interaction) -> None:
        """Check Gifted T3 credit"""
        await VODReviewBankController.get_balance(interaction.user, interaction)

    @app_commands.command(name="balance_for")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(user="Community Manager to check VOD Review credit for")
    async def balance_for(self, interaction: Interaction, user: User) -> None:
        """Check Gifted T3 credit for specified user"""
        await VODReviewBankController.get_balance(user, interaction)

    @app_commands.command(name="redeem")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE, CM_ROLE, VOD_TEAM_ROLE)
    @app_commands.describe(user="Community Manager to check VOD Review credit for")
    @app_commands.describe(
        duration="Duration to redeem T3 for (if balance is sufficient)"
    )
    async def redeem(
        self,
        interaction: Interaction,
        user: Optional[User] = None,
        duration: Optional[str] = None,
    ) -> None:
        """Redeem the specified duration of gifted t3 to specified user"""
        if user is None:
            await VODReviewBankController.redeem_gifted_t3(
                interaction.user, duration, interaction
            )
        else:
            await VODReviewBankController.redeem_gifted_t3(user, duration, interaction)

    @staticmethod
    async def remove_incorrect_role(user: User, interaction: Interaction):
        approved_role = interaction.guild.get_role(APPROVED_ROLE)
        rejected_role = interaction.guild.get_role(REJECTED_ROLE)

        if TempRoleController.user_has_temprole(user, approved_role):
            await TempRoleController.remove_role(user, approved_role)
        if TempRoleController.user_has_temprole(user, rejected_role):
            await TempRoleController.remove_role(user, rejected_role)

    @staticmethod
    def get_owner(content: str, guild: Guild):
        """VODs are submitted by RoboBanana.
        Grab the VOD owner's Discord Member by
        searching for a user mention included
        in the forum post

        Args:
            content (str): Forum Post content as generated by submit_vod command
            guild (Guild): Guild that forum post belongs to

        Returns:
            Member: VOD Owner's Discord Member
        """
        user_id_matches = USER_ID_PATTERN.findall(content)
        user_id = int(user_id_matches[0][1])
        return guild.get_member(user_id)

    @staticmethod
    async def process_vod(
        tag_id: int, role_id: int, duration: str, interaction: Interaction
    ):
        role = interaction.guild.get_role(role_id)
        if role is None:
            return await interaction.response.send_message(
                f"Could not find VOD role id={role_id}", ephemeral=True
            )

        starter_message = await interaction.channel.fetch_message(
            interaction.channel.id
        )
        owner = ManagerCommands.get_owner(starter_message.content, interaction.guild)
        if owner is None:
            return await interaction.response.send_message(
                "Could not find author of this forum post", ephemeral=True
            )

        await ManagerCommands.remove_incorrect_role(owner, interaction)
        success, message = await TempRoleController.set_role(owner, role, duration)
        if not success:
            embed = Embed(
                title="Failed to apply TempRole", description=message, color=Color.red()
            )
            return await DiscordUtils.reply(interaction, embed=embed)
        embed = Embed(
            title="Successfully Applied Temprole",
            description=message,
            color=Color.green(),
        )
        await DiscordUtils.reply(interaction, embed=embed)

        forum_tag = interaction.channel.parent.get_tag(tag_id)
        embed = Embed(
            title="Tag and Temprole",
            description=f"Applied {forum_tag.name} and {role.mention}.",
            color=0xF9D60D,
        )
        await interaction.channel.add_tags(forum_tag)
        tags_to_remove = copy(interaction.channel.applied_tags)
        tags_to_remove.remove(forum_tag)
        await interaction.channel.remove_tags(*tags_to_remove)

        await interaction.followup.send(embed=embed)
        await VODReviewBankController.increment_balance(interaction.user, interaction)

    @app_commands.command(name="get_review_rounds")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE, CM_ROLE, VOD_TEAM_ROLE)
    @app_commands.describe(total_rounds="total number of rounds in VOD")
    async def get_review_rounds(
        self, interaction: Interaction, total_rounds: int
    ) -> None:
        """Generates rounds to check for the pre-round comms requirement"""
        if total_rounds < 21:
            await interaction.response.send_message(
                "Not enough rounds in VOD. Match must be 13-8 or"
                " closer.\n;rejectedforfinalscore",
                ephemeral=True,
            )
            return
        roundsToCheck = []
        returnString = "Pre-round Comms:"
        random.shuffle(
            FIRST_HALF_STARTING_ROUNDS
        )  # Get two rounds from the first 3 rounds of each half
        random.shuffle(SECOND_HALF_STARTING_ROUNDS)
        roundsToCheck += FIRST_HALF_STARTING_ROUNDS[:2]
        roundsToCheck += SECOND_HALF_STARTING_ROUNDS[:2]
        roundsToCheck.append(
            random.randint(FIRST_HALF_NORMAL_ROUNDS_START, FIRST_HALF_NORMAL_ROUNDS_END)
        )
        roundsToCheck.append(
            random.randint(SECOND_HALF_NORMAL_ROUNDS_START, total_rounds)
        )  # Game ends at total round number
        roundsToCheck.sort()
        for num in roundsToCheck:
            returnString += (  # Generates response that VOD Reviewer can copy-paste into the forum
                f"\nRound {num}:"
            )

        await interaction.response.send_message(returnString, ephemeral=True)

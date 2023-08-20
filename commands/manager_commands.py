from discord import app_commands, Interaction, Client, User, ForumTag
from discord.app_commands.errors import AppCommandError, CheckFailure
from discord import Object
from config import Config
import enum
import logging
import random

class VODType(enum.Enum):
    approved = 1
    rejected = 2
    complete = 3

FIRST_HALF_STARTING_ROUNDS = [1,2,3]
FIRST_HALF_NORMAL_ROUNDS_START = 4
FIRST_HALF_NORMAL_ROUNDS_END = 12
SECOND_HALF_STARTING_ROUNDS = [13,14,15]
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

    @app_commands.command(name="get_review_rounds")
    @app_commands.checks.has_role("VOD Review Team")
    @app_commands.describe(total_rounds="total number of rounds in VOD")
    async def get_review_rounds(
        self, interaction: Interaction, total_rounds: int
    ) -> None:
        """Generates rounds to check for the pre-round comms requirement"""
        if (total_rounds < 21):
            await interaction.response.send_message("Not enough rounds in VOD. Match must be 13-8 or closer.\n;rejectedforfinalscore", ephemeral=True)
            return
        roundsToCheck = []
        returnString = "Pre-round Comms:"
        random.shuffle(FIRST_HALF_STARTING_ROUNDS) # Get two rounds from the first 3 rounds of each half
        random.shuffle(SECOND_HALF_STARTING_ROUNDS)
        roundsToCheck += FIRST_HALF_STARTING_ROUNDS[:2]
        roundsToCheck += SECOND_HALF_STARTING_ROUNDS[:2]
        roundsToCheck.append(random.randint(FIRST_HALF_NORMAL_ROUNDS_START, FIRST_HALF_NORMAL_ROUNDS_END))
        roundsToCheck.append(random.randint(SECOND_HALF_NORMAL_ROUNDS_START, total_rounds)) # Game ends at total round number
        roundsToCheck.sort()
        for num in roundsToCheck:
            returnString += f"\nRound {num}:" # Generates response that VOD Reviewer can copy-paste into the forum 

        await interaction.response.send_message(returnString, ephemeral=True)

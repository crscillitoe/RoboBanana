import logging
import time
from discord import (
    Embed,
    app_commands,
    Interaction,
    Client,
    User,
)
from config import YAMLConfig as Config
from discord.app_commands.errors import AppCommandError, CheckFailure

from controllers.point_history_controller import PointHistoryController
from db.models import PointsHistory

MOD_ROLE = Config.CONFIG["Discord"]["Roles"]["Mod"]
# these are hardcoded until raze to radiant is over, or config file changes are allowed
# for testing on own setup, these need to be changed to your appropriate IDs
# HIDDEN_MOD_ROLE should be 1040337265790042172 when committing and refers to the Mod (Role Hidden)
HIDDEN_MOD_ROLE = 1040337265790042172


@app_commands.guild_only()
class PointHistoryCommands(app_commands.Group, name="points_history"):
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

    @app_commands.command(name="mine")
    async def mine(self, interaction: Interaction):
        """View your own point transaction history"""
        user_history = PointHistoryController.get_transaction_history(
            interaction.user.id
        )
        embed = PointHistoryCommands.format_reply(user_history, interaction.user)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="user")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(user="User to check point transaction history for")
    async def user(self, interaction: Interaction, user: User):
        """View point transaction history for specified user"""
        user_history = PointHistoryController.get_transaction_history(user.id)
        embed = PointHistoryCommands.format_reply(user_history, user)
        await interaction.response.send_message(embed=embed)

    @staticmethod
    def format_reply(user_history: list[PointsHistory], user: User) -> Embed:
        timestamps = list(
            map(
                lambda transaction: (
                    f"<t:{time.mktime(transaction.timestamp.timetuple()):.0f}:R>"
                ),
                user_history,
            )
        )
        balance_summary = list(
            map(
                lambda transaction: (
                    f"{transaction.points_delta:+} ({str(transaction.starting_balance) + ' -> ' + str(transaction.ending_balance)})"
                ),
                user_history,
            )
        )
        reasons = list(map(lambda transaction: transaction.reason, user_history))

        timestamps = "\n".join(timestamps)
        balance_summary = "\n".join(balance_summary)
        reasons = "\n".join(reasons)

        embed = Embed(
            title=f"Last {len(user_history)} Transactions",
            description=f"History for {user.mention}",
            color=user.color,
        )
        embed.add_field(name="Timestamp", value=timestamps)
        embed.add_field(
            name="Change (Start -> End)", value=balance_summary, inline=True
        )
        embed.add_field(name="Reason", value=reasons, inline=True)
        return embed

import logging
from discord import app_commands, Interaction, Client, User
from discord.ext.commands import Cog
from config import YAMLConfig as Config
from db import DB
from discord.app_commands.errors import AppCommandError, CheckFailure


MOD_ROLE = Config.CONFIG["Discord"]["Roles"]["Mod"]
# these are hardcoded until raze to radiant is over, or config file changes are allowed
# for testing on own setup, these need to be changed to your appropriate IDs
# HIDDEN_MOD_ROLE should be 1040337265790042172 when committing and refers to the Mod (Role Hidden)
HIDDEN_MOD_ROLE = 1040337265790042172


@app_commands.guild_only()
class ReactionCommands(app_commands.Group, name="reactions"):
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

    @app_commands.command(name="toggle_emoji")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(user="User ID to remove win from")
    @app_commands.describe(emoji="Emoji to toggle reaction for")
    async def toggle_emoji(self, interaction: Interaction, user: User, emoji: str):
        result = DB().toggle_emoji_reaction(user.id, emoji)
        toggle_desc = "ON" if result else "OFF"
        await interaction.response.send_message(f"Reaction toggled {toggle_desc}!")

    @app_commands.command(name="set_emoji_reaction_delay")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(delay_time="Delay time in seconds for Robomojis")
    async def set_emoji_reaction_delay(self, interaction: Interaction, delay_time: int):
        """Sets delay time in seconds between Robomoji reactions for users"""
        result = DB().set_emoji_reaction_delay(delay_time)
        await interaction.response.send_message(
            f"Robomoji delay time set to {result} seconds!"
        )

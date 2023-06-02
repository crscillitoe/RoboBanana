from discord import app_commands, Interaction, Client, User
from discord.ext.commands import Cog
from db import DB


@app_commands.guild_only()
class ReactionCommands(app_commands.Group, name="reactions"):
    def __init__(self, tree: app_commands.CommandTree, client: Client) -> None:
        super().__init__()
        self.tree = tree
        self.client = client

    @app_commands.command(name="toggle_emoji")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(user="User ID to remove win from")
    @app_commands.describe(emoji="Emoji to toggle reaction for")
    async def toggle_emoji(self, interaction: Interaction, user: User, emoji: str):
        result = DB().toggle_emoji_reaction(user.id, emoji)
        toggle_desc = "ON" if result else "OFF"
        await interaction.response.send_message(f"Reaction toggled {toggle_desc}!")

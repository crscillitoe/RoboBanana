from discord import Interaction, app_commands, Client

from controllers.aimlabs_tracking import AimlabsTrackingController


@app_commands.guild_only()
class AimlabsCommands(app_commands.Group, name="aimlabs"):
    def __init__(self, tree: app_commands.CommandTree, client: Client) -> None:
        super().__init__()
        self.tree = tree
        self.client = client

    @app_commands.command(name="register")
    @app_commands.checks.has_role("Mod")  # TODO: Change to a custom validator for T3s
    @app_commands.describe(aimlabs_id="Aimlabs User ID to track")
    async def register(self, interaction: Interaction, aimlabs_id: str):
        AimlabsTrackingController.register_user(interaction.user, aimlabs_id)
        await interaction.response.send_message("Registered user!", ephemeral=True)

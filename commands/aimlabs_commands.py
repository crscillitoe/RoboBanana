from discord import Interaction, app_commands, Client
from controllers.aimlabs_tracking import AimlabsTrackingController
import pytz


@app_commands.guild_only()
class AimlabsCommands(app_commands.Group, name="aimlabs"):
    def __init__(self, tree: app_commands.CommandTree, client: Client) -> None:
        super().__init__()
        self.tree = tree
        self.client = client

    @app_commands.command(name="timezones")
    async def timezones(self, interaction: Interaction):
        await interaction.response.send_message(
            (
                "Find a list of all valid timezones at the following URL:\n"
                "https://gist.github.com/braddotcoffee/189f4af603d73448a1ce8f62b923d429"
            ),
            ephemeral=True,
        )

    @app_commands.command(name="register")
    @app_commands.checks.has_role("Mod")  # TODO: Change to a custom validator for T3s
    @app_commands.describe(aimlabs_id="Aimlabs User ID to track")
    @app_commands.describe(timezone="Your local timezone")
    async def register(
        self,
        interaction: Interaction,
        aimlabs_id: str,
        timezone: str,
    ):
        await AimlabsTrackingController.register_user(aimlabs_id, timezone, interaction)

from discord import Role, app_commands, Interaction, Client, User, TextChannel

from controllers.temprole_controller import TempRoleController


@app_commands.guild_only()
class TemproleCommands(app_commands.Group, name="temprole"):
    def __init__(self, tree: app_commands.CommandTree, client: Client) -> None:
        super().__init__()
        self.tree = tree
        self.client = client

    @app_commands.command(name="add_role")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(user="Discord User to assign role to")
    @app_commands.describe(role="Discord Role to assign role to")
    @app_commands.describe(duration="Duration of temprole")
    async def add_role(
        self, interaction: Interaction, user: User, role: Role, duration: str
    ):
        """Assign temprole to a user for a specified time"""
        await TempRoleController.add_temprole(user, role, duration, interaction)

    @app_commands.command(name="view_user_roles")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(user="Discord User to check roles for")
    async def view_user_roles(self, interaction: Interaction, user: User):
        """See expriations for all temproles currently assigned to given user"""
        await TempRoleController.view_temproles(user, interaction)

    @app_commands.command(name="view_roles")
    async def view_roles(self, interaction: Interaction):
        """See expriations for all temproles currently assigned to you"""
        await TempRoleController.view_temproles(interaction.user, interaction)

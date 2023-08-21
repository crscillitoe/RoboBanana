from discord import Role, app_commands, Interaction, Client, User, TextChannel

from controllers.temprole_controller import TempRoleController


@app_commands.guild_only()
class TemproleCommands(app_commands.Group, name="temprole"):
    def __init__(self, tree: app_commands.CommandTree, client: Client) -> None:
        super().__init__()
        self.tree = tree
        self.client = client

    @app_commands.command(name="set")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(user="Discord User to assign role to")
    @app_commands.describe(role="Discord Role to assign role to")
    @app_commands.describe(duration="Duration of temprole")
    async def set_role(
        self, interaction: Interaction, user: User, role: Role, duration: str
    ):
        """Assign temprole to a user for a specified time (10m, 30d, 3w, etc)"""
        await TempRoleController.set_role(user, role, duration, interaction)

    @app_commands.command(name="extend")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(user="Discord User to extend role for")
    @app_commands.describe(role="Discord Role to extend duration for")
    @app_commands.describe(duration="Duration to add to temprole")
    async def extend_role(
        self, interaction: Interaction, user: User, role: Role, duration: str
    ):
        """Assign temprole to a user for a specified time (10m, 30d, 3w, etc)"""
        await TempRoleController.extend_role(user, role, duration, interaction)

    @app_commands.command(name="remove")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(user="Discord User to remove role from")
    @app_commands.describe(role="Discord Role to remove")
    async def remove_role(self, interaction: Interaction, user: User, role: Role):
        """Assign temprole to a user for a specified time (10m, 30d, 3w, etc)"""
        await TempRoleController.remove_role(user, role, interaction)

    @app_commands.command(name="status")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(user="Discord User to check roles for")
    async def status(self, interaction: Interaction, user: User):
        """See expirations for all temproles currently assigned to given user"""
        await TempRoleController.view_temproles(user, interaction)

    @app_commands.command(name="mine")
    async def mine(self, interaction: Interaction):
        """See expirations for all temproles currently assigned to you"""
        await TempRoleController.view_temproles(interaction.user, interaction)

    @app_commands.command(name="view")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(role="Discord Role to check users for")
    async def view(self, interaction: Interaction, role: Role):
        """See expirations for all users that currently have a given role"""
        await TempRoleController.view_users(role, interaction)

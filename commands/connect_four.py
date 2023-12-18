import enum
import logging
from discord import Client, Interaction, User, app_commands
import requests
from config import YAMLConfig as Config
from controllers.connect_four.connect_four_controller import ConnectFourController

from controllers.connect_four.game_orchestrator import GameOrchestrator
from util.server_utils import get_base_url

PUBLISH_CONNECT_FOUR_URL = f"{get_base_url()}/publish-connect-four"
AUTH_TOKEN = Config.CONFIG["Secrets"]["Server"]["Token"]

LOG = logging.getLogger(__name__)


@app_commands.guild_only()
class ConnectFourCommands(app_commands.Group, name="connect_four"):
    def __init__(self, tree: app_commands.CommandTree, client: Client) -> None:
        super().__init__()
        self.tree = tree
        self.client = client
        self.enabled = False
        self.orchestrator = GameOrchestrator()
        self.controller = ConnectFourController()

    @app_commands.command()
    @app_commands.checks.has_role("Mod")
    async def enable(self, interaction: Interaction):
        """Allow users to challenge each other to Connect Four"""
        self.enabled = True
        self.orchestrator.reopen_challenges()
        await interaction.response.send_message("Connect Four Enabled!", ephemeral=True)

    @app_commands.command()
    @app_commands.checks.has_role("Mod")
    async def disable(self, interaction: Interaction):
        """Prevent users from challenging each other to Connect Four"""
        self.enabled = False
        await interaction.response.send_message(
            "Connect Four Disabled!", ephemeral=True
        )

    @app_commands.command()
    @app_commands.describe(opponent="Who you'd like to face")
    async def challenge(self, interaction: Interaction, opponent: User):
        """Challenge user to a game of Connect Four"""
        if not self.enabled or not self.orchestrator.accepting_chalenges():
            return await interaction.response.send_message(
                "Unable to challenge players to Connect Four at this time",
                ephemeral=True,
            )

        start_game = self.orchestrator.challenge(interaction.user.id, opponent.id)
        if not start_game:
            return await interaction.response.send_message(
                "Challenge submitted! A game will start once your opponent challenges"
                " you back.",
                ephemeral=True,
            )

        success, first_move_player_id = self.controller.new_game(
            interaction.user.id, opponent.id
        )
        if not success:
            self.orchestrator.reopen_challenges()
            return await interaction.response.send_message(
                "Faled to start game of Connect Four"
            )

        first_move_user = (
            opponent if first_move_player_id == opponent.id else interaction.user
        )
        second_move_user = (
            interaction.user if first_move_player_id == opponent.id else opponent
        )

        publish_new_game(first_move_user, second_move_user)

        await interaction.response.send_message(
            f"Game started! {first_move_user.mention} plays first!"
        )

    @app_commands.command()
    @app_commands.describe(column="Column you'd like to place your piece in")
    async def move(self, interaction: Interaction, column: int):
        """Play your turn in an active Connect Four game!"""
        if not self.enabled:
            return await interaction.response.send_message(
                f"Connect Four is currently disabled", ephemeral=True
            )

        if not self.orchestrator.active_player(interaction.user.id):
            return await interaction.response.send_message(
                f"You are not currently part of a Connect Four game", ephemeral=True
            )

        success, move_summary = self.controller.move(interaction.user.id, column - 1)
        if not success:
            return await interaction.response.send_message(
                f"Invalid move", ephemeral=True
            )

        publish_move(interaction.user, column - 1, move_summary.row, move_summary.win)

        if move_summary.win:
            self.orchestrator.reopen_challenges()
            return await interaction.response.send_message(
                f":tada: WINNER: {interaction.user.mention} :tada:"
            )

        await interaction.response.send_message(
            f"{interaction.user.mention} played {column}"
        )


def publish_move(player: User, column: int, row: int, win: bool):
    payload = {
        "action": "move",
        "player_id": player.id,
        "column": column,
        "row": row,
        "win": win,
    }
    response = requests.post(
        url=PUBLISH_CONNECT_FOUR_URL,
        json=payload,
        headers={"x-access-token": AUTH_TOKEN},
    )

    if response.status_code != 200:
        LOG.error(f"Failed to publish connect four updates: {response.text}")


def publish_new_game(player_one: User, player_two: User):
    payload = {
        "action": "new_game",
        "player_one": {"id": player_one.id, "name": player_one.display_name},
        "player_two": {"id": player_two.id, "name": player_two.display_name},
    }
    response = requests.post(
        url=PUBLISH_CONNECT_FOUR_URL,
        json=payload,
        headers={"x-access-token": AUTH_TOKEN},
    )

    if response.status_code != 200:
        LOG.error(f"Failed to publish connect four updates: {response.text}")

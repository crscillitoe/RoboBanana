from discord import app_commands, Client
from commands.connect_four import ConnectFourCommands
from commands.manager_commands import ManagerCommands
from commands.marker_commands import MarkerCommands
from commands.meme_commands import MemeCommands
from commands.mod_commands import ModCommands
from commands.overlay_commands import OverlayCommands
from commands.point_history_commands import PointHistoryCommands
from commands.prediction_commands import PredictionCommands
from commands.reaction_commands import ReactionCommands
from commands.temprole_commands import TemproleCommands
from commands.viewer_commands import ViewerCommands
from commands.t3_commands import T3Commands
from commands.vod_commands import VodCommands
import logging

LOG = logging.getLogger(__name__)


class SyncUtils:
    @staticmethod
    def add_commands_to_tree(
        tree: app_commands.CommandTree, client: Client, override: bool = False
    ):
        tree.add_command(MemeCommands(tree, client), override=override)
        tree.add_command(ModCommands(tree, client), override=override)
        tree.add_command(PredictionCommands(tree, client), override=override)
        tree.add_command(ViewerCommands(tree, client), override=override)
        tree.add_command(ManagerCommands(tree, client), override=override)
        tree.add_command(ReactionCommands(tree, client), override=override)
        tree.add_command(VodCommands(tree, client), override=override)
        tree.add_command(TemproleCommands(tree, client), override=override)
        tree.add_command(PointHistoryCommands(tree, client), override=override)
        tree.add_command(ConnectFourCommands(tree, client), override=override)
        tree.add_command(T3Commands(tree, client), override=override)
        tree.add_command(MarkerCommands(tree, client), override=override)
        overlay_commands = OverlayCommands(tree, client)
        # LOG.info("---------------------------------------------")
        # for command in overlay_commands.walk_commands():
        #     LOG.info(f"overlay_command: {command.name}")
        # attr = getattr(overlay_commands, "test_command", None)
        # LOG.info(f"{attr=}")
        tree.add_command(overlay_commands, override=override)

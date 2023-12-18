from collections import namedtuple
import enum
import random
from typing import Optional

from controllers.connect_four.game_constants import BOARD_WIDTH

Board = list[list[Optional[int]]]


class Color(enum.Enum):
    RED = "red"
    YELLOW = "yellow"


class MoveSummary(namedtuple("MoveSummary", ["row", "color", "win"])):
    """Summarizes game state after a move

    Fields:
        row (int): Row on which piece "landed" after falling
        color (Color): Color of piece to place based on player turn
        win (bool): Whether move resulted in the end of a game
    """


class GameState:
    def __init__(self, board: Board, player_one_id, player_two_id):
        self.board = board
        self.player_one_id = player_one_id
        self.player_two_id = player_two_id

        player_turns = [player_one_id, player_two_id]
        random.shuffle(player_turns)
        self.player_turn = player_turns[0]

        self.turn = Color.RED
        self.next_row = [0] * BOARD_WIDTH

    def flip_turn(self):
        self.turn = Color.RED if self.turn == Color.YELLOW else Color.YELLOW
        self.player_turn = (
            self.player_one_id
            if self.player_turn == self.player_two_id
            else self.player_two_id
        )

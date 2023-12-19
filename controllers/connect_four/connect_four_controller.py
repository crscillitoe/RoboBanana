from typing import Optional
from controllers.connect_four.game_constants import BOARD_HEIGHT, BOARD_WIDTH
from controllers.connect_four.models import Board, GameState, MoveSummary

from controllers.connect_four.win_checker import WinChecker


class ConnectFourController:
    def __init__(self):
        self.games: dict[int, GameState] = dict()

    @staticmethod
    def _new_board() -> Board:
        return [[None] * BOARD_WIDTH for _ in range(BOARD_HEIGHT)]

    def new_game(self, player_one_id: int, player_two_id: int) -> tuple[bool, int]:
        if player_one_id in self.games or player_two_id in self.games:
            return False, -1
        new_game = GameState(self._new_board(), player_one_id, player_two_id)
        self.games[player_one_id] = new_game
        self.games[player_two_id] = new_game
        return True, new_game.player_turn

    def _is_player_turn(self, move_player_id: int) -> bool:
        if move_player_id not in self.games:
            return False
        game_state = self.games[move_player_id]
        return game_state.player_turn == move_player_id

    def _valid_col(self, column):
        return column in range(BOARD_WIDTH)

    def _valid_row(self, row_placement):
        return row_placement < BOARD_HEIGHT

    def _cleanup_game(self, game_state: GameState):
        del self.games[game_state.player_one_id]
        del self.games[game_state.player_two_id]

    def reset(self):
        self.games = dict()

    def move(
        self, move_player_id: int, column: int
    ) -> tuple[bool, Optional[MoveSummary]]:
        if not self._is_player_turn(move_player_id) or not self._valid_col(column):
            return False, None

        game_state = self.games[move_player_id]
        row_placement = game_state.next_row[column]
        if not self._valid_row(row_placement):
            return False, None

        game_state.next_row[column] += 1
        game_state.board[row_placement][column] = game_state.turn

        win = WinChecker.check_win(game_state, row_placement, column)
        if win:
            self._cleanup_game(game_state)

        move_summary = MoveSummary(row_placement, game_state.turn, win)
        game_state.flip_turn()
        return True, move_summary

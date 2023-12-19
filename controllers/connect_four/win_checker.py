from collections import deque

from controllers.connect_four.game_constants import BOARD_HEIGHT, BOARD_WIDTH, WIN_COUNT
from controllers.connect_four.models import GameState

HORIZONTAL = [[0, 1], [0, -1]]
VERTICAL = [[1, 0], [-1, 0]]
DIAGONAL_RIGHT = [[-1, -1], [1, 1]]
DIAGONAL_LEFT = [[-1, 1], [1, -1]]


class WinChecker:
    @staticmethod
    def _get_adjacent(
        row: int, col: int, directions: list[list[int]]
    ) -> list[tuple[int]]:
        adjacent = []
        for row_delta, col_delta in directions:
            new_row = row + row_delta
            new_col = col + col_delta

            valid_row = new_row in range(BOARD_HEIGHT)
            valid_col = new_col in range(BOARD_WIDTH)

            if valid_row and valid_col:
                adjacent.append((new_row, new_col))
        return adjacent

    @staticmethod
    def _check_direction_win(
        game_state: GameState,
        start_row: int,
        start_col: int,
        directions: list[list[int]],
    ) -> bool:
        color = game_state.board[start_row][start_col]
        queue = deque([(start_row, start_col)])
        visited = set()
        connected_count = 0
        while len(queue) > 0:
            row, col = queue.pop()
            if game_state.board[row][col] != color:
                continue
            if (row, col) in visited:
                continue
            connected_count += 1
            if connected_count == WIN_COUNT:
                return True
            visited.add((row, col))
            queue.extendleft(WinChecker._get_adjacent(row, col, directions))
        return False

    @staticmethod
    def check_win(game_state: GameState, row: int, col: int) -> bool:
        all_directions = [HORIZONTAL, VERTICAL, DIAGONAL_LEFT, DIAGONAL_RIGHT]

        for direction in all_directions:
            if WinChecker._check_direction_win(game_state, row, col, direction):
                return True
        return False

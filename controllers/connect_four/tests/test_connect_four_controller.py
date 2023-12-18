from controllers.connect_four.connect_four_controller import ConnectFourController
from unittest.mock import patch

from controllers.connect_four.game_constants import BOARD_HEIGHT, BOARD_WIDTH, WIN_COUNT
from controllers.connect_four.models import Color


PLAYER_ONE = 1
PLAYER_TWO = 2


def PLAYER_ONE_MOVE_FIRST(_):
    return [PLAYER_ONE, PLAYER_TWO]


def make_successful_move(controller: ConnectFourController, player, column):
    success, move_summary = controller.move(player, column)
    assert success
    return move_summary


def make_successful_new_game(controller: ConnectFourController):
    success, _ = controller.new_game(PLAYER_ONE, PLAYER_TWO)
    assert success


def test_no_game_for_player():
    controller = ConnectFourController()
    success, _ = controller.move(PLAYER_ONE, 0)
    assert not success


def test_make_new_game():
    controller = ConnectFourController()
    success, _ = controller.new_game(PLAYER_ONE, PLAYER_TWO)
    assert success

    success, _ = controller.new_game(PLAYER_ONE, PLAYER_TWO)
    assert not success

    success, _ = controller.new_game(PLAYER_TWO, PLAYER_ONE)
    assert not success


def test_new_game_returns_correct_player():
    controller = ConnectFourController()
    success, player_turn = controller.new_game(PLAYER_ONE, PLAYER_TWO)
    assert success

    success, _ = controller.move(player_turn, 0)
    assert success


@patch("controllers.connect_four.models.random.shuffle", PLAYER_ONE_MOVE_FIRST)
def test_make_move_player_turn():
    controller = ConnectFourController()
    make_successful_new_game(controller)

    success, _ = controller.move(PLAYER_ONE, 0)
    assert success

    success, _ = controller.move(PLAYER_ONE, 0)
    assert not success

    success, _ = controller.move(PLAYER_TWO, 0)
    assert success


@patch("controllers.connect_four.models.random.shuffle", PLAYER_ONE_MOVE_FIRST)
def test_make_move_valid_row():
    controller = ConnectFourController()
    make_successful_new_game(controller)

    for _ in range(BOARD_HEIGHT // 2):
        make_successful_move(controller, PLAYER_ONE, 0)
        make_successful_move(controller, PLAYER_TWO, 0)
    success, _ = controller.move(PLAYER_ONE, 0)
    assert not success


@patch("controllers.connect_four.models.random.shuffle", PLAYER_ONE_MOVE_FIRST)
def test_make_move_valid_col():
    controller = ConnectFourController()
    make_successful_new_game(controller)

    success, _ = controller.move(PLAYER_ONE, BOARD_WIDTH)
    assert not success


@patch("controllers.connect_four.models.random.shuffle", PLAYER_ONE_MOVE_FIRST)
def test_make_move_flips_turn_color():
    controller = ConnectFourController()
    make_successful_new_game(controller)

    move_summary = make_successful_move(controller, PLAYER_ONE, 0)
    assert move_summary.color == Color.RED

    move_summary = make_successful_move(controller, PLAYER_TWO, 0)
    assert move_summary.color == Color.YELLOW


@patch("controllers.connect_four.models.random.shuffle", PLAYER_ONE_MOVE_FIRST)
def test_horizontal_win():
    controller = ConnectFourController()
    make_successful_new_game(controller)

    for i in range(WIN_COUNT - 1):
        make_successful_move(controller, PLAYER_ONE, i)
        make_successful_move(controller, PLAYER_TWO, i)

    move_summary = make_successful_move(controller, PLAYER_ONE, WIN_COUNT - 1)
    assert move_summary.win


@patch("controllers.connect_four.models.random.shuffle", PLAYER_ONE_MOVE_FIRST)
def test_vertical_win():
    controller = ConnectFourController()
    make_successful_new_game(controller)

    for _ in range(WIN_COUNT - 1):
        make_successful_move(controller, PLAYER_ONE, 0)
        make_successful_move(controller, PLAYER_TWO, 1)

    move_summary = make_successful_move(controller, PLAYER_ONE, 0)
    assert move_summary.win


@patch("controllers.connect_four.models.random.shuffle", PLAYER_ONE_MOVE_FIRST)
def test_diagonal_right_win():
    controller = ConnectFourController()
    make_successful_new_game(controller)

    # Fill col 0
    make_successful_move(controller, PLAYER_ONE, 0)

    # Fill col 1
    make_successful_move(controller, PLAYER_TWO, 1)
    make_successful_move(controller, PLAYER_ONE, 1)

    # Fill col 2
    make_successful_move(controller, PLAYER_TWO, 2)
    make_successful_move(controller, PLAYER_ONE, 0)
    make_successful_move(controller, PLAYER_TWO, 2)
    make_successful_move(controller, PLAYER_ONE, 2)

    # Fill col 3
    make_successful_move(controller, PLAYER_TWO, 3)
    make_successful_move(controller, PLAYER_ONE, 2)
    make_successful_move(controller, PLAYER_TWO, 3)
    make_successful_move(controller, PLAYER_ONE, 2)
    make_successful_move(controller, PLAYER_TWO, 3)

    move_summary = make_successful_move(controller, PLAYER_ONE, 3)
    assert move_summary.win


@patch("controllers.connect_four.models.random.shuffle", PLAYER_ONE_MOVE_FIRST)
def test_diagonal_left_win():
    controller = ConnectFourController()
    make_successful_new_game(controller)

    make_successful_move(controller, PLAYER_ONE, 1)

    # Fill col 0
    make_successful_move(controller, PLAYER_TWO, 0)
    make_successful_move(controller, PLAYER_ONE, 0)
    make_successful_move(controller, PLAYER_TWO, 0)
    make_successful_move(controller, PLAYER_ONE, 0)

    # Fill col 1
    make_successful_move(controller, PLAYER_TWO, 1)
    make_successful_move(controller, PLAYER_ONE, 1)

    # Fill col 2
    make_successful_move(controller, PLAYER_TWO, 2)
    make_successful_move(controller, PLAYER_ONE, 2)

    make_successful_move(controller, PLAYER_TWO, 2)

    move_summary = make_successful_move(controller, PLAYER_ONE, 3)
    assert move_summary.win

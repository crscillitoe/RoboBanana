from controllers.connect_four.game_orchestrator import GameOrchestrator


PLAYER_ONE = 1
PLAYER_TWO = 2


def successfully_start_game(orchestrator, player_one, player_two):
    start_game = orchestrator.challenge(player_one, player_two)
    assert not start_game

    start_game = orchestrator.challenge(player_two, player_one)
    assert start_game


def test_challenge_success():
    orchestrator = GameOrchestrator()
    start_game = orchestrator.challenge(PLAYER_ONE, PLAYER_TWO)
    assert not start_game

    start_game = orchestrator.challenge(PLAYER_TWO, PLAYER_ONE)
    assert start_game


def test_not_accepting_challenges_with_active_game():
    orchestrator = GameOrchestrator()
    successfully_start_game(orchestrator, PLAYER_ONE, PLAYER_TWO)

    start_game = orchestrator.challenge(PLAYER_ONE, PLAYER_TWO)
    assert not start_game

    start_game = orchestrator.challenge(PLAYER_TWO, PLAYER_ONE)
    assert not start_game


def test_reopen_challenges():
    orchestrator = GameOrchestrator()
    successfully_start_game(orchestrator, PLAYER_ONE, PLAYER_TWO)

    start_game = orchestrator.challenge(PLAYER_ONE, PLAYER_TWO)
    assert not start_game

    start_game = orchestrator.challenge(PLAYER_TWO, PLAYER_ONE)
    assert not start_game

    orchestrator.reopen_challenges()
    successfully_start_game(orchestrator, PLAYER_ONE, PLAYER_TWO)


def test_challenge_only_one_person():
    orchestrator = GameOrchestrator()
    start_game = orchestrator.challenge(PLAYER_ONE, PLAYER_TWO)
    assert not start_game

    start_game = orchestrator.challenge(PLAYER_ONE, 3)
    assert not start_game

    start_game = orchestrator.challenge(PLAYER_TWO, PLAYER_ONE)
    assert not start_game


def test_not_accepting_challenges_after_game_start():
    orchestrator = GameOrchestrator()
    assert orchestrator.accepting_chalenges()

    successfully_start_game(orchestrator, PLAYER_ONE, PLAYER_TWO)

    assert not orchestrator.accepting_chalenges()

    orchestrator.reopen_challenges()
    assert orchestrator.accepting_chalenges()


def test_active_players():
    orchestrator = GameOrchestrator()
    assert not orchestrator.active_player(PLAYER_ONE)
    assert not orchestrator.active_player(PLAYER_TWO)

    successfully_start_game(orchestrator, PLAYER_ONE, PLAYER_TWO)

    assert orchestrator.active_player(PLAYER_ONE)
    assert orchestrator.active_player(PLAYER_TWO)

    orchestrator.reopen_challenges()
    assert not orchestrator.active_player(PLAYER_ONE)
    assert not orchestrator.active_player(PLAYER_TWO)


def test_wipe_challenges_on_game_start():
    orchestrator = GameOrchestrator()
    successfully_start_game(orchestrator, PLAYER_ONE, PLAYER_TWO)
    orchestrator.reopen_challenges()
    start_game = orchestrator.challenge(PLAYER_TWO, PLAYER_ONE)
    assert not start_game


def test_cannot_challenge_self():
    orchestrator = GameOrchestrator()
    start_game = orchestrator.challenge(PLAYER_ONE, PLAYER_ONE)
    assert not start_game

    start_game = orchestrator.challenge(PLAYER_ONE, PLAYER_ONE)
    assert not start_game

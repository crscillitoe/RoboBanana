class GameOrchestrator:
    def __init__(self):
        self.challenges: dict[int, int] = dict()
        self.active_game = False
        self.active_players = set()

    def reopen_challenges(self):
        self.active_game = False
        self.active_players = set()

    def accepting_chalenges(self):
        """Returns True if there is no active game happening"""
        return not self.active_game

    def active_player(self, player_id: int):
        """Check if provided player is one of the challengers in the active game"""
        return player_id in self.active_players

    def challenge(self, challenger: int, opponent: int) -> bool:
        """Challenge opponent to game of ConnectFour. If the opponent
        has already challenged you, both challenges are removed so
        a game may be started.

        Args:
            challenger (int): Discord ID of the challenger
            opponent (int): Discord ID of the person they'd like to face

        Returns:
            bool: True if game should be started
        """
        if self.active_game or challenger == opponent:
            return False

        if opponent not in self.challenges:
            self.challenges[challenger] = opponent
            return False

        if self.challenges[opponent] != challenger:
            self.challenges[challenger] = opponent
            return False
        self.active_game = True
        self.active_players.add(challenger)
        self.active_players.add(opponent)
        self.challenges = dict()
        return True

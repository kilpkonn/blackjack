"""Strategy."""
from strategy import Strategy
from game_view import Move


class StudentStrategy(Strategy):
    """Student strategy class"""

    def __init__(self, other_players: list, house, decks_count):
        """Init."""
        super().__init__(other_players, house, decks_count)

    def play_move(self, hand) -> Move:
        """Get next move."""
        return Move.STAND

    def on_card_drawn(self, card) -> None:
        """Called every time card is drawn."""

    def on_game_end(self) -> None:
        """Called on game end."""

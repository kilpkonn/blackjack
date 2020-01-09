"""Deck."""
import itertools
from typing import Optional, List

import requests


class Card:
    """Simple dataclass for holding card information."""

    def __init__(self, value: str, suit: str, code: str):
        """Constructor."""
        self.value = value
        self.suit = suit
        self.code = code
        self.top_down = False

    def __str__(self):
        """Str."""
        return self.code if not self.top_down else '??'

    def __repr__(self) -> str:
        """Repr."""
        return self.code

    def __eq__(self, o) -> bool:
        """Eq."""
        return isinstance(o, Card) and o.value == self.value and o.suit == self.suit and o.code == self.code


class Deck:
    """Deck."""

    DECK_BASE_API = "https://deckofcardsapi.com/api/deck/"

    def __init__(self, deck_count: int = 1, shuffle: bool = False):
        """Constructor."""
        self._backup_deck = list(itertools.chain(*[self._generate_backup_pile() for _ in range(deck_count)]))
        self.remaining = -1
        self.id = None
        self.deck_count = deck_count
        self.is_shuffled = shuffle
        shuffle_param = 'shuffle/' if shuffle else ''
        result = self._request(Deck.DECK_BASE_API + f"/new/{shuffle_param}?deck_count={deck_count}")
        if 'remaining' in result:
            self.remaining = result['remaining']
            self.id = result['deck_id']

        pass

    def shuffle(self) -> None:
        """Shuffle the deck."""
        self._request(Deck.DECK_BASE_API + self.id + "/suhffle")

    def draw_card(self, top_down: bool = False) -> Optional[Card]:
        """
        Draw card from the deck.

        :return: card instance.
        """
        c = None
        if self.id is not None:
            result = self._request(Deck.DECK_BASE_API + self.id + "/draw/?count=1")
            result = result['cards'][0]
            c = Card(result['value'], result['suit'], result['code'])
        if c is not None:
            if c in self._backup_deck:
                self._backup_deck.remove(c)
            else:
                c = None
        if c is None:
            if len(self._backup_deck) > 0:
                c = self._backup_deck.pop()
            else:
                return None
        c.top_down = top_down
        self.remaining = len(self._backup_deck)
        return c

    def _request(self, url: str) -> dict:
        """Update deck."""
        return requests.get(url).json()

    @staticmethod
    def _generate_backup_pile() -> List[Card]:
        """Generate backup pile."""
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'JACK', 'QUEEN', 'KING', 'ACE']
        suits = ['SPADES', 'DIAMONDS', 'HEARTS', 'CLUBS']

        return [Card(v, s, (v[-1] if v.isdigit() else v[0]) + s[0]) for v in values for s in suits]


if __name__ == '__main__':
    d = Deck(shuffle=True, deck_count=3)
    print(d.remaining)  # 52
    card1 = d.draw_card()  # Random card
    print(card1 in d._backup_deck)  # False
    print(d._backup_deck)  # 51 shuffled cards
    d2 = Deck(deck_count=2)
    print(d2._backup_deck)  # 104 ordered cards (deck after deck)
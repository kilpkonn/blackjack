"""Blackjack."""
import copy
import importlib
import itertools
import os
import pkgutil
import random

import requests

from game_view import GameView, TournamentView, Move
from strategy import Strategy, HumanStrategy


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
        return "??" if self.top_down else self.code

    def __repr__(self) -> str:
        """Repr."""
        return self.code

    def __eq__(self, o) -> bool:
        """Eq."""
        return isinstance(o, Card) and self.value == o.value and self.suit == o.suit and self.code == o.code


class Deck:
    """Deck."""

    DECK_BASE_API = "https://deckofcardsapi.com/api/deck/"

    def __init__(self, deck_count: int = 1, shuffle: bool = True):
        """Constructor."""
        self.deck_count = deck_count
        self.is_shuffled = shuffle
        self.id = None
        self._backup_deck = list(itertools.chain(*[self._generate_backup_pile() for _ in range(deck_count)]))
        self.remaining = len(self._backup_deck)

        if shuffle:
            random.shuffle(self._backup_deck)

        # self._request(self.DECK_BASE_API + f"new/{'shuffle/' if shuffle else ''}?deck_count={deck_count}")

    def shuffle(self) -> None:
        """Shuffle the deck."""
        if self.id:
            self._request(self.DECK_BASE_API + f"{self.id}/shuffle")

        random.shuffle(self._backup_deck)

    def draw_card(self, top_down: bool = False) -> Card:
        """
        Draw card from the deck.

        :return: card instance.
        """
        if self.id:
            resp = self._request(self.DECK_BASE_API + f"{self.id}/draw/?count=1")
            try:
                if not resp["cards"]:
                    return None
                card = Card(resp["cards"][0]["value"], resp["cards"][0]["suit"], resp["cards"][0]["code"])
                self._backup_deck.remove(card)
            except ValueError:
                card = self._backup_deck.pop()
                self.remaining = len(self._backup_deck)
        else:
            card = self._backup_deck.pop()
            self.remaining = len(self._backup_deck)

        card.top_down = top_down
        return card

    def _request(self, url: str) -> dict:
        """Update deck."""
        resp = None
        try:
            resp = requests.get(url).json()
            self.is_shuffled = resp["shuffled"] if "shuffled" in resp else self.is_shuffled
            self.id = resp["deck_id"]
            self.remaining = resp["remaining"]
        except KeyError or requests.exceptions.RequestException or ValueError:
            self.id = None
        return resp

    @staticmethod
    def _generate_backup_pile() -> list:
        """Generate backup pile."""
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'JACK', 'QUEEN', 'KING', 'ACE']
        suits = ['SPADES', 'DIAMONDS', 'HEARTS', 'CLUBS']

        return [Card(v, s, (v[-1] if v.isdigit() else v[0]) + s[0]) for v in values for s in suits]


class Hand:
    """Hand."""

    def __init__(self, cards: list = None):
        """Init."""
        self.cards = cards if cards else []
        self.is_double_down = False
        self.is_surrendered = False

    def add_card(self, card: Card) -> None:
        """Add card to hand."""
        self.cards.append(card)

    def double_down(self, card: Card) -> None:
        """Double down."""
        self.add_card(card)
        self.is_double_down = True

    def split(self):
        """Split hand."""
        if not self.can_split:
            raise ValueError("Invalid hand to split!")
        return Hand([self.cards.pop()])

    @property
    def can_split(self) -> bool:
        """Check if hand can be split."""
        return len(self.cards) == 2 and self.cards[0].value == self.cards[1].value

    @property
    def is_blackjack(self) -> bool:
        """Check if is blackjack"""
        return len(self.cards) == 2 and self.score == 21

    @property
    def is_soft_hand(self):
        """Check if is soft hand."""
        return max(self.cards, key=lambda x: x.value == 'ACE').value == 'ACE' if len(self.cards) > 0 else False

    @property
    def score(self):
        """Get score of hand."""
        score = 0
        aces_count = 0
        for card in self.cards:
            if card.value == "JACK" or card.value == "QUEEN" or card.value == "KING":
                score += 10
            elif card.value == "ACE":
                score += 1
                aces_count += 1
            else:
                score += int(card.value)
        for _ in range(aces_count):
            score += 10 if score + 10 <= 21 else 0
        return score


class Player:
    """Player."""

    def __init__(self, name: str, strategy: Strategy, coins: int = 100):
        """Init."""
        self.name = name
        self.hands = []
        self.coins = coins
        self.strategy = strategy
        strategy.player = self

    def join_table(self):
        """Join table."""
        self.hands = [Hand()]

    def play_move(self, hand: Hand) -> Move:
        """Play move."""
        return self.strategy.play_move(hand)

    def split_hand(self, hand: Hand) -> None:
        """Split hand."""
        if hand in self.hands:
            self.hands.append(hand.split())


class GameController:
    """Game controller."""

    PLAYER_START_COINS = 1000
    BUY_IN_COST = 10

    def __init__(self, view: GameView):
        """Init."""
        self.view = view
        self.house = Hand()
        self.players = []
        self.deck = None

    def start_game(self, strategy_classes=None) -> None:
        """Start game"""
        decks_count = self.view.ask_decks_count()
        players_count = self.view.ask_players_count()
        bots_count = self.view.ask_bots_count()

        # strategies = self.load_strategies()
        strategies = []

        self.deck = Deck(decks_count, True)
        self.house = Hand()

        for i in range(players_count):
            player = Player(self.view.ask_name(i + 1),
                            HumanStrategy(self.players, self.house, decks_count, self.view),
                            self.PLAYER_START_COINS)
            self.players.append(player)

        if strategy_classes is None:
            for i in range(bots_count):
                bot = Player(f"Bot #{i + 1}",
                             random.choice(strategies)(self.players, self.house, decks_count),
                             self.PLAYER_START_COINS)
                self.players.append(bot)
        else:  # predefined strategy classes
            for i, strat_class in enumerate(strategy_classes):
                name = strat_class.__name__
                if hasattr(strat_class, "name"):
                    name = getattr(strat_class, "name")

                print(strat_class)
                bot = Player(name, strat_class(self.players, self.house, decks_count), self.PLAYER_START_COINS)

                self.players.append(bot)

    def play_round(self) -> bool:
        """Play round."""
        random.shuffle(self.players)
        if all([player.coins < self.BUY_IN_COST for player in self.players]):
            return False

        # Remove broke players
        self.active_players = list(filter(lambda x: x.coins >= self.BUY_IN_COST, self.players))

        for player in self.players:
            if player.coins >= self.BUY_IN_COST:
                player.coins -= self.BUY_IN_COST
                player.join_table()

        self.house = Hand()
        for player in self.active_players:
            for hand in player.hands:
                hand.add_card(self._draw_card())
        self.house.add_card(self._draw_card())
        for player in self.active_players:
            for hand in player.hands:
                hand.add_card(self._draw_card())

        house_copy = copy.deepcopy(self.house)
        house_cards = self.house.cards[:]

        # Make strategy reference correct fake house (without top_down card)
        for p in self.active_players:
            p.strategy.house = copy.deepcopy(self.house)

        for player in self.active_players:

            for hand in player.hands:
                playing = True
                while playing:
                    self.view.show_table(self.players, house_copy, hand)
                    move = player.play_move(player.hands[0])
                    if move == Move.HIT:
                        hand.add_card(self._draw_card())
                    elif move == Move.SPLIT:
                        if hand.can_split:
                            player.split_hand(hand)
                            player.coins -= self.BUY_IN_COST
                            for h in player.hands:
                                while len(h.cards) < 2:
                                    h.add_card(self._draw_card())
                        else:
                            print("CANNOT SPLIT NOW")
                    elif move == Move.DOUBLE_DOWN:
                        player.coins -= self.BUY_IN_COST
                        hand.double_down(self._draw_card())
                        playing = False
                    elif move == Move.STAND:
                        playing = False
                    elif move == Move.SURRENDER:
                        playing = False
                        hand.is_surrendered = True
                    else:
                        print("ILLEGAL MOVE", move)
                        playing = False
                        # raise ValueError("Illegal move!")

                    if hand.score > 21:
                        playing = False

        # Basic house logic
        for p in self.active_players:
            p.strategy.house = self.house

        self.house = Hand(house_cards)
        self.house.add_card(self.deck.draw_card())  # Do not show players

        """
        for c in self.house.cards:
            if c.top_down:
                c.top_down = False
                for p in self.active_players:
                    p.strategy.house = self.house
                    p.strategy.on_card_drawn(c)
        """

        while self.house.score <= 16 or (self.house.score <= 17 and self.house.is_soft_hand):
            self.house.add_card(self._draw_card())
            self.view.show_table(self.players, self.house, None)

        # Pay players at 1:1 ratio on bets, 3:2 for blackjack
        for player in self.active_players:
            for hand in player.hands:
                if hand.is_surrendered:
                    player.coins += 0.5 * self.BUY_IN_COST
                elif hand.score == 21 and hand.is_blackjack:
                    player.coins += 3 * self.BUY_IN_COST
                elif self.house.score < hand.score <= 21 or self.house.score > 21 >= hand.score:
                    player.coins += self.BUY_IN_COST * 4 if hand.is_double_down else self.BUY_IN_COST * 2
                elif self.house.score == hand.score <= 21:
                    player.coins += self.BUY_IN_COST if not hand.is_double_down else self.BUY_IN_COST * 2

            player.strategy.on_game_end()
        return True

    def _draw_card(self) -> Card:
        """Draw card."""
        c = self.deck.draw_card()
        for p in self.players:
            p.strategy.on_card_drawn(c)
        return c

    @staticmethod
    def load_strategies() -> list:
        """Load strategies"""
        pkg_dir = os.path.dirname(__file__)
        for (module_loader, name, is_pkg) in pkgutil.iter_modules([pkg_dir]):
            importlib.import_module('.' + name, 'ex13_blackjack')
        return list(filter(lambda x: x.__name__ != HumanStrategy.__name__, Strategy.__subclasses__()))


if __name__ == '__main__':

    # Move imports to top of file? not sure if tester likes it.
    from matplotlib import pyplot as plt
    from student_strategy import StudentStrategy

    # players here
    strategy_list = [StudentStrategy, StudentStrategy]

    rounds_count = 1000
    GameController.PLAYER_START_COINS = 1000

    game_controller = GameController(TournamentView(len(strategy_list), rounds_count))
    game_controller.start_game(strategy_list)
    players_coins_history = {p: [game_controller.PLAYER_START_COINS] for p in game_controller.players}
    color_options = ["red", "green", "blue", "cyan", "purple", "olive", "black", "hotpink", "orange"]
    colors = {p: color_options[i] for i, p in enumerate(game_controller.players)}
    rounds = [0]
    last_rounds = {p: 0 for p in game_controller.players}
    n = 0

    plt.ion()
    fig, axs = plt.subplots(1, 1)
    ax = axs

    # fig.canvas.draw()
    plt.show()

    while game_controller.play_round():
        n += 1
        print("ROUND", n, game_controller.deck.remaining)
        rounds.append(n)

        if any([p.coins < game_controller.BUY_IN_COST for p in game_controller.players]):
            for p in game_controller.players:
                if p.coins < game_controller.BUY_IN_COST:
                    plt.savefig(f"{p.name}.png")
        ax.clear()

        # Sort players for legend
        game_controller.players = sorted(game_controller.players, key=lambda x: x.coins, reverse=True)

        for p in game_controller.players:
            players_coins_history[p].append(p.coins)
            ax.plot(rounds, players_coins_history[p], label=p.name, color=colors[p])
            if p.coins >= GameController.BUY_IN_COST:
                last_rounds[p] = n
        # Draw reference line for profit / loss
        ax.plot(rounds, [GameController.PLAYER_START_COINS for _ in rounds], color="lightcoral")

        ax.legend()
        plt.xlabel("Round")
        plt.ylabel("Coins")
        fig.canvas.draw()
        plt.show()
        plt.pause(0.05)  # 2fast2quick

        if n > rounds_count:
            break
        else:
            random.shuffle(game_controller.players)  # shuffle for new round

    plt.savefig("final.png")
    print("RESULTS:")
    for p in game_controller.players:
        print(p.name, p.coins, last_rounds[p])

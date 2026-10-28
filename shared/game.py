import random
from typing import List, Dict, Tuple, Optional

class Card:
    SUITS = ["Spades", "Hearts", "Diamonds", "Clubs"]
    RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "Jack", "Queen", "King", "Ace"]

    def __init__(self, suit: str, rank: str):
        self.suit = suit
        self.rank = rank
        # 2-13 of Spades have 2 uses. Everything else has 1 use.
        self.uses_left = 2 if suit == "Spades" and rank != "Ace" else 1

    def to_net_id(self) -> int:
        """Translates a card instance into an integer (1 to 54) for low network bytes."""
        if self.suit == "Joker":
            return 53 if self.rank == "Red" else 54
        s_idx = Card.SUITS.index(self.suit)
        r_idx = Card.RANKS.index(self.rank)
        return (s_idx * 13) + r_idx + 1

    @classmethod
    def from_net_id(cls, card_id: int):
        """Factory: Reconstructs a full Card instance from a single network ID."""
        if card_id == 53:
            return cls("Joker", "Red")
        if card_id == 54:
            return cls("Joker", "Black")
            
        card_id -= 1
        suit = cls.SUITS[card_id // 13]
        rank = cls.RANKS[card_id % 13]
        return cls(suit, rank)


class Player:
    def __init__(self, player_id: int):
        self.player_id = player_id
        self.is_dead = False
        self.hand: List[Card] = []

    def to_net_dict(self, include_hand_contents: bool, cooldown_count: int, support_count: int) -> dict:
        """Serializes player properties. Hides hand cards from opponents but exposes public board metrics."""
        return {
            "id": self.player_id,
            "dead": self.is_dead,
            "hand_count": len(self.hand),
            "cooldown_count": cooldown_count,  # Visible to everyone physically
            "support_count": support_count,    # Visible to everyone physically
            # Secret: Only the owner gets the exact IDs
            "hand_ids": [c.to_net_id() for c in self.hand] if include_hand_contents else []
        }


class GameState:
    def __init__(self, allow_red_joker: bool = False):
        self.turn_number = 1
        self.active_player_id = 1
        self.allow_red_joker = allow_red_joker
        
        self.players: Dict[int, Player] = {}
        self.deck: List[Card] = []
        self.discard_pile: List[Card] = []
        self.banish_pile: List[Card] = []
        self.pending_supports: Dict[int, List[Card]] = {}
        self.cooldown_schedule: Dict[int, List[Tuple[Card, int]]] = {}

    @staticmethod
    def calculate_initial_stack(num_players: int) -> int:
        """max(14 - (players - 1) * 2, 9)"""
        return max(14 - (num_players - 1) * 2, 9)

    def initialize_deck(self):
        self.deck.clear()
        for suit in Card.SUITS:
            for rank in Card.RANKS:
                self.deck.append(Card(suit, rank))
        self.deck.append(Card("Joker", "Black"))
        if self.allow_red_joker:
            self.deck.append(Card("Joker", "Red"))
        random.shuffle(self.deck)

    def get_player_cooldown_metrics(self, player_id: int) -> Tuple[int, List[int]]:
        """Calculates total card count on cooldown and provides raw IDs for the owner."""
        total_count = 0
        private_ids = []
        for entries in self.cooldown_schedule.values():
            for card_obj, owner_id in entries:
                if owner_id == player_id:
                    total_count += 1
                    private_ids.append(card_obj.to_net_id())
        return total_count, private_ids

    def to_net_snapshot(self, requesting_player_id: int) -> dict:
        """Transforms engine data into public/private primitives under our 1.4KB limit."""
        net_players = {}
        
        for p_id, player_obj in self.players.items():
            # Get cooldown counts for this player
            cd_count, cd_ids = self.get_player_cooldown_metrics(p_id)
            # Get support count for this player
            supp_count = len(self.pending_supports.get(p_id, []))
            
            # Build the base dictionary
            is_owner = (p_id == requesting_player_id)
            p_dict = player_obj.to_net_dict(is_owner, cd_count, supp_count)
            
            # Security Addition: If they are the owner, attach their specific cooldown IDs
            if is_owner:
                p_dict["cooldown_ids"] = cd_ids
                # Show them their own pending support cards
                p_dict["support_ids"] = [c.to_net_id() for c in self.pending_supports.get(p_id, [])]
                
            net_players[p_id] = p_dict

        return {
            "turn": self.turn_number,
            "active_p": self.active_player_id,
            "red_joker_enabled": self.allow_red_joker,
            "deck_count": len(self.deck),
            "discard_top": self.discard_pile[-1].to_net_id() if self.discard_pile else None,
            "banish_count": len(self.banish_pile),
            "players": net_players
        }

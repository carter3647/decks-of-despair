from shared.useful import sprint, warn, error
from typing import List, Dict, Tuple, Optional

class card:
	SUITS = ["Spades", "Hearts", "Diamonds", "Clubs"]
	RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "Jack", "Queen", "King", "Ace"]

	def __init__(self, suit: str, rank: str):
		self.suit = suit
		self.rank = rank
		# 2-13 of Spades have 2 uses. Everything else (Aces, Jokers, Blocks) has 1 use.
		self.uses_left = 2 if suit == "Spades" and rank != "Ace" else 1

	def to_net_id(self) -> int:
		if self.suit == "Joker":
			return 53 if self.rank == "Red" else 54
		s_idx = card.SUITS.index(self.suit)
		r_idx = card.RANKS.index(self.rank)
		return (s_idx * 13) + r_idx + 1

	@classmethod
	def from_net_id(cls, card_id: int):
		if card_id == 53: return cls("Joker", "Red")
		if card_id == 54: return cls("Joker", "Black")
		card_id -= 1
		return cls(cls.SUITS[card_id // 13], cls.RANKS[card_id % 13])

	def get_combat_value(self) -> int:
		"""Translates card ranks into raw mathematical power indices (2-15)."""
		if self.suit == "Joker":
			return 15  # Jokers beat Aces (14)
		return card.RANKS.index(self.rank) + 2


class Player:
	def __init__(self, player_id: int):
		self.player_id = player_id
		self.is_dead = False
		self.hand: List[card] = []

	def has_card(self, card_id: int) -> bool:
		"""Verifies true physical ownership of a card inside their hand stack."""
		return any(c.to_net_id() == card_id for c in self.hand)

	def extract_card(self, card_id: int) -> Optional[card]:
		"""Removes a card instance from hand for placement on board/discard piles."""
		for c in self.hand:
			if c.to_net_id() == card_id:
				self.hand.remove(c)
				return c
		return None

	def to_net_dict(self, include_hand_contents: bool, cooldown_count: int, support_count: int) -> dict:
		return {
			"id": self.player_id,
			"dead": self.is_dead,
			"hand_count": len(self.hand),
			"cooldown_count": cooldown_count,
			"support_count": support_count,
			"hand_ids": [c.to_net_id() for c in self.hand] if include_hand_contents else []
		}


class GameState:
	def __init__(self, allow_red_joker: bool = False):
		self.turn_number = 1
		self.active_player_id = 1
		self.allow_red_joker = allow_red_joker
		
		self.players: Dict[int, Player] = {}
		self.deck: List[card] = []
		self.discard_pile: List[card] = []
		self.banish_pile: List[card] = []
		
		self.pending_supports: Dict[int, List[card]] = {}
		self.cooldown_schedule: Dict[int, List[Tuple[card, int]]] = {}
		
		# ─── ACTIVE COMBAT STATE TRACKER ───
		self.pending_attack_card: Optional[card] = None
		self.attacker_id: Optional[int] = None
		self.target_id: Optional[int] = None

	def initialize_deck(self):
		self.deck.clear()
		for suit in card.SUITS:
			for rank in card.RANKS:
				self.deck.append(card(suit, rank))
		self.deck.append(card("Joker", "Black"))
		if self.allow_red_joker:
			self.deck.append(card("Joker", "Red"))
		import random
		random.shuffle(self.deck)

	def process_turn_increment(self):
		self.turn_number += 1
		
		# Clear out current turn combat residues safely
		self.pending_attack_card = None
		self.attacker_id = None
		self.target_id = None

		# Automate cards coming off cooldown row and returning to player hands
		if self.turn_number in self.cooldown_schedule:
			returning_items = self.cooldown_schedule[self.turn_number]
			for card_obj, owner_id in returning_items:
				if owner_id in self.players and not self.players[owner_id].is_dead:
					self.players[owner_id].hand.append(card_obj)
					sprint(f"card {card_obj.to_net_id()} has finished cooldown and popped into Player {owner_id}'s hand.")
			del self.cooldown_schedule[self.turn_number]

	def verify_and_process_attack(self, attacker_id: int, target_id: int, card_id: int) -> Tuple[bool, str]:
		"""Validates and stages an offensive action card onto the board authority arena."""
		if self.active_player_id != attacker_id:
			return False, "Rejected: It is not your turn phase."
		if self.pending_attack_card is not None:
			return False, "Rejected: An un-resolved attack is already active on the table."
		if attacker_id == target_id or self.players.get(target_id) is None or self.players[target_id].is_dead:
			return False, "Rejected: Invalid or deceased defender target selected."
			
		attacker = self.players[attacker_id]
		if not attacker.has_card(card_id):
			return False, "Anti-Cheat: Requested action card is missing from physical hand layout."

		# Extract card from possession to process rules mechanics
		card_obj = attacker.extract_card(card_id)
		
		# Rule Check: Ace of Spades (Unblockable damage)
		if card_obj.suit == "Spades" and card_obj.rank == "Ace":
			self.banish_pile.append(card_obj)
			sprint(f"Player {attacker_id} unleashed an unblockable Ace of Spades!")
			# Target player forced to drop cards or manage impact immediately
			return True, "ATTACK_UNBLOCKABLE"

		# Rule Check: Normal 2-13 Spades (Cooldown usage thresholds)
		if card_obj.suit == "Spades":
			card_obj.uses_left -= 1
			if card_obj.uses_left > 0:
				# Schedule return automatically exactly 1 turn away
				unlock_turn = self.turn_number + 1
				if unlock_turn not in self.cooldown_schedule:
					self.cooldown_schedule[unlock_turn] = []
				self.cooldown_schedule[unlock_turn].append((card_obj, attacker_id))
				sprint(f"Spade {card_id} placed on 1-turn cooldown. (1 Use left).")
			else:
				self.banish_pile.append(card_obj)
				sprint(f"Spade {card_id} has exhausted all utility uses and entered the Banish Pile.")
				
			self.pending_attack_card = card_obj
			self.attacker_id = attacker_id
			self.target_id = target_id
			return True, "ATTACK_STAGED"

		# Return card to hand if it wasn't an attack card
		attacker.hand.append(card_obj)
		return False, "Rejected: The selected card asset is not a valid offensive weapon class."

	def verify_and_process_defense(self, defender_id: int, block_card_ids: List[int]) -> Tuple[bool, str]:
		"""Resolves defensive card math layers against staged attack frames safely."""
		if self.target_id != defender_id or self.pending_attack_card is None:
			return False, "Rejected: No active attack threat requires your defensive clearance right now."
			
		defender = self.players[defender_id]
		
		# Confirm absolute physical ownership of all declared blocking cards
		for cid in block_card_ids:
			if not defender.has_card(cid):
				return False, f"Anti-Cheat: Missing card {cid} from hand inventory profiles."

		atk_value = self.pending_attack_card.get_combat_value()
		
		# Unpack, extract, and convert cards to verify values
		def_cards = [defender.extract_card(cid) for cid in block_card_ids]
		total_def_power = sum(c.get_combat_value() for c in def_cards)
		
		has_diamonds = any(c.suit == "Diamonds" for c in def_cards)
		has_hearts = any(c.suit == "Hearts" for c in def_cards)

		# ─── ENFORCE DIAMOND BLOCK RULES ───
		if has_diamonds:
			# Diamond blocks can be thrown alone, OR as 2 cards total (1 Diamond + 1 Support card max)
			if len(def_cards) > 2:
				# Refund cards back to hand on failure rule
				defender.hand.extend(def_cards)
				return False, "Rejected: Diamonds cannot stack beyond 1 support card total."
			
			if total_def_power >= atk_value:
				# Successful Diamond defense route cards to top of the discard pile
				self.discard_pile.extend(def_cards)
				sprint(f"Player {defender_id} cleanly blocked attack with Diamond combo. Discarded.")
				self.pending_attack_card = None  # Attack resolved
				return True, "DEFENSE_SUCCESS"

		# ─── ENFORCE HEART HEAL RULES ───
		elif has_hearts:
			# Hearts can stack infinitely together to merge values
			if any(c.suit != "Hearts" for c in def_cards):
				defender.hand.extend(def_cards)
				return False, "Rejected: Hearts can only combine exclusively with other Heart cards."
				
			if total_def_power >= atk_value:
				# Successful Heart defense routes cards permanently into the banish pile
				self.banish_pile.extend(def_cards)
				sprint(f"Player {defender_id} burned Hearts to survive the damage! cards Banished.")
				self.pending_attack_card = None  # Attack resolved
				return True, "DEFENSE_SUCCESS"

		# Refund all cards if defensive thresholds fail to meet math conditions
		defender.hand.extend(def_cards)
		
		# Kill enforcement route: Player unable to match values is defeated
		defender.is_dead = True
		# Move their remaining hand to discard pile
		self.discard_pile.extend(defender.hand)
		defender.hand.clear()
		sprint(f"Player {defender_id} was unable to block value {atk_value} and was killed.")
		return True, "DEFENDER_KILLED"

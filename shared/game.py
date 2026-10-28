import random
import pickle
from shared.useful import Event,_Connection

class card:
	suits = ["Spades","Clubs","Diamonds","Hearts"]
	ranks = ["2","3","4","5","6","7","8","9","10","Jack","Queen","King","Ace"]
	def __init__(self,s,r):
		self.suit = s
		self.rank = r
		if self.suit == "Spades": self.uses = 0
	def toID(self):
		if self.suit=="Black":return 53
		if self.suit=="Red":return 54
		id = card.suits.index(self.suit)*13+card.ranks.index(self.ranks)

	@classmethod
	def fromID(cls,id):
		if id==53:return card("Black","Joker")
		if id==54:return card("Red","Joker")
		id-=1
		suit = id//13
		rank = id%13
		return card(cls.suits[suit],cls.ranks[rank])

def setupCards():
	unsorted:card = []
	for rank in ["Hearts","Spades","Diamonds","Clubs"]:
		for suit in range(1,13):
			unsorted.append(suit,rank)
	unsorted.append(card("Black","Joker"))
	random.shuffle(unsorted)
	return unsorted

class Player:
	def __init__(self):
		self.turn = 0
		self.curr_player = 0
		
		self.players = []
		
		self.cards = []
		self.cooldown = {}



class GameState:
	def __init__(self):
		self.turn = 0
		self.curr_player = 0

		self.players = []

		self.drawpile = []
		self.discard = []
		self.banished = []

		self.CardOwnership = {}

class ClientState:
	def __init__(self):
		self.turn = 0
		self.curr_player = 0

		self.players = []

		self.cards = []
		self.cooldown = {}
		


def turn(state:GameState):
	for player in state.players:
		pass
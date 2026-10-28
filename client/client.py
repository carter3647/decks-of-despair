import socket
from shared.useful import *
from shared import game
from client import gui

port = 80


	
class GameState:
	def __init__(self):
		self.turn = 0
		self.curr_player = 0

		self.players = []

		self.cards = []
		self.cooldown = {}


import pygame
import socket
import json
import sys
from shared.useful import *  # Pulls your custom startasync, send, waitForData, sprint, etc.
from shared import game
from client import gui

# ─── PYGAME WINDOW CONFIGURATION ───
pygame.init()
WIDTH, HEIGHT = 1024, 768
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Decks of Despair - Client")
clock = pygame.time.Clock()

# Fonts and Colors
FONT = pygame.font.SysFont("Arial", 20)
COLOR_BG = (20, 20, 25)
COLOR_CARD = (240, 240, 245)
COLOR_TEXT = (255, 255, 255)
COLOR_ACCENT = (255, 165, 0)

# Local Client Memory Cache
my_player_id = None
local_game_snapshot = None
client_socket = None

# ─── NETWORKING RECEIVER LOOP ───
@startasync
def listen_to_server(connection: socket.socket):
	"""
	Background worker loop using your @startasync framework.
	Continuously intercepts server states via your 0x00 null delimiter.
	"""
	global local_game_snapshot
	sprint("Async server message monitoring thread active.")
	try:
		while True:
			# Reads until hitting your custom 0x00 null delimiter
			raw_bytes = waitForData(connection, buffersize=4096)
			if not raw_bytes:
				sprint("Disconnected from server.")
				break
				
			# Strip trailing null-bytes and parse incoming JSON message array
			clean_json = raw_bytes.rstrip(b"\x00").decode("utf-8")
			msg_type, payload = json.loads(clean_json)
			
			match msg_type:
				case "STATE_UPDATE":
					# Updates local memory state cache instantly for the drawing framework
					local_game_snapshot = payload
					
				case "CHAT_BROADCAST":
					sprint(f"[CHAT] {payload}")
					
				case "PLAYER_DROPPED":
					warn(payload)
					
	except Exception as e:
		error(f"Loss of sync in server message pipeline: {e}")
	finally:
		connection.close()

def connect_to_server(host: str, port: int) -> bool:
	"""Handles the synchronous connection protocol handshake with your server."""
	global client_socket, my_player_id
	try:
		client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		client_socket.connect((host, port))
		
		# 1. Read greeting string: e.g. "CONNECT 5000\x00"
		greeting = waitForData(client_socket).decode("utf-8").rstrip("\x00")
		if not greeting.startswith("CONNECT"):
			return False
			
		# 2. Complete your custom handshake rule sequence
		send(client_socket, f"{port} CONNECTED")
		sprint("Handshake authenticated with server.")
		
		# Spawn your async server listener channel
		listen_to_server(client_socket)
		return True
	except Exception as e:
		error(f"Failed to connect to server pool: {e}")
		return False

# ─── ACTION PACKET SENDER INTERFACES ───
def send_action(msg_type: str, payload: dict):
	"""Encapsulates actions into json strings and dispatches over your null-byte socket layer."""
	if client_socket:
		packet = json.dumps([msg_type, payload])
		send(client_socket, packet)

# ─── DRAWING UTILITIES ───
def draw_card(screen, x, y, card_id, is_active=False):
	"""Draws a visual card surface representing translated server indices."""
	# Convert numerical card ID back into a readable suit and rank string locally
	translated_card = game.Card.from_net_id(card_id)
	
	card_rect = pygame.Rect(x, y, 90, 130)
	border_color = COLOR_ACCENT if is_active else (100, 100, 100)
	
	pygame.draw.rect(screen, COLOR_CARD, card_rect, border_size:=0, border_radius:=8)
	pygame.draw.rect(screen, border_color, card_rect, border_size:=3, border_radius:=8)
	
	# Render shorthand identity text onto the face of the card
	text_surf = FONT.render(f"{translated_card.rank}", True, (0, 0, 0))
	suit_surf = FONT.render(f"{translated_card.suit[:3]}", True, (200, 0, 0) if translated_card.suit in ["Hearts", "Diamonds"] else (0, 0, 0))
	
	screen.blit(text_surf, (x + 10, y + 15))
	screen.blit(suit_surf, (x + 10, y + 45))

# ─── MAIN USER INTERFACE LOOP ───
def main():
	# Prompt connection parameters on shell boot
	print("=" * 55)
	print("        DECKS OF DESPAIR - CLIENT INTERFACE")
	print("=" * 55)
	server_address = input("Enter server IP (e.g. 127.0.0.1 or ngrok host): ").strip()
	server_port = int(input("Enter server Port: ").strip())
	print("=" * 55)
	
	if not connect_to_server(server_address, server_port):
		return

	running = True
	while running:
		# 1. Capture user environment clicks and window hooks
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False
				
			elif event.type == pygame.MOUSEBUTTONDOWN:
				mx, my = pygame.mouse.get_pos()
				# Example: If a player clicks an action button, transmit their selection intent
				# send_action("PLAY_CARD", {"card_id": 14, "target": 2})
				pass

		# 2. Rendering Phase
		screen.fill(COLOR_BG)
		
		if local_game_snapshot:
			# Display current global turn metrics
			turn_text = FONT.render(f"Turn: {local_game_snapshot['turn']}", True, COLOR_TEXT)
			active_p_text = FONT.render(f"Active Player: {local_game_snapshot['active_p']}", True, COLOR_TEXT)
			screen.blit(turn_text, (20, 20))
			screen.blit(active_p_text, (20, 50))
			
			# Find the active user's local instance data inside the unshielded state object
			# Note: We need to figure out which player ID belongs to this specific socket connection
			# For testing layout, we assume player object payload exists
			pass
		else:
			waiting_text = FONT.render("Awaiting game deployment snapshot from room host...", True, COLOR_TEXT)
			screen.blit(waiting_text, (WIDTH // 2 - 200, HEIGHT // 2))

		pygame.display.flip()
		clock.tick(60)  # Locked to standard clean 60 FPS window rules

	pygame.quit()
	if client_socket:
		client_socket.close()

main()

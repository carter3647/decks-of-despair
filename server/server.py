import socket
import ngrok
import os
import queue
import threading
import json
from shared.useful import *  # Pulls startasync, send, waitForData, sprint, error, etc.
from sys import argv
from shared import game
from server import forwarding
from server.gui import *

headless = False
max_players = 0
forward = False
port = 5000

args = argv[1:]
for index, arg in enumerate(args):
	match arg:
		case "-h":
			headless = True
		case "-max-players":
			max_players = int(args[index+1])
		case "-p":
			port = int(args[index+1])
		case "-f":
			forward = bool(args[index+1])

def load_ngrok_token():
	if os.path.exists("token.txt"):
		with open("token.txt", "r") as f:
			return f.read().strip()
	return None

# ─── CENTRAL GAME PIPELINE QUEUE ───
network_action_queue = queue.Queue()
active_clients = {}
clients_lock = threading.Lock()

def game_logic_engine():
	"""Background engine thread to execute player intents sequentially (O(1) safety)."""
	global gameState
	sprint("Sequential rule processing engine activated.")
	while True:
		try:
			player_id, message_type, payload = network_action_queue.get(timeout=1)
			
			match message_type:
				case "PLAY_CARD":
					card_id = payload.get("card_id")
					target = payload.get("target")
					sprint(f"[ACTION] Player {player_id} played Card {card_id} on Target {target}")
					# Process single-deck rules and turn cooldowns here
					
				case "CHAT":
					sprint(f"[CHAT] Player {player_id}: {payload}")
					broadcast_message("CHAT_BROADCAST", f"Player {player_id}: {payload}")
					
				case "END_TURN":
					gameState.process_turn_increment()
					broadcast_state_snapshots()

			network_action_queue.task_done()
		except queue.Empty:
			continue
		except Exception as e:
			error(f"Engine logic processing collapsed: {e}")

# ─── CUSTOM UTILITY APPLIED: AUTOMATIC ASYNC PACKET MONITORING ───
@startasync
def run_client_receiver_loop(connection, player_id):
	"""
	Spawns automatically as an independent background listener thread.
	Uses your custom delimiter system rules to capture actions cleanly.
	"""
	sprint(f"Async network worker thread engaged for Player {player_id}")
	try:
		while True:
			# Native implementation: Reads until hitting your custom 0x00 null delimiter
			raw_bytes = waitForData(connection, buffersize=4096)
			if not raw_bytes:
				break
				
			# Strip your delimiter and decode to plain text json string payload
			clean_json = raw_bytes.rstrip(b"\x00").decode("utf-8")
			message_type, payload = json.loads(clean_json)
			
			# Pipe data safely into your global logic processing queue
			network_action_queue.put((player_id, message_type, payload))
			
	except Exception as e:
		warn(f"Socket interface link closed for Player {player_id}: {e}")
	finally:
		with clients_lock:
			if player_id in active_clients:
				del active_clients[player_id]
		connection.close()
		broadcast_message("PLAYER_DROPPED", f"Player {player_id} has left the match.")

def broadcast_message(msg_type, payload):
	"""Broadcasts a json message using your custom null delimiter suffix mechanics."""
	packet = json.dumps([msg_type, payload]) + "\x00"
	with clients_lock:
		for conn in active_clients.values():
			try:
				send(conn, packet)
			except:
				continue

def broadcast_state_snapshots():
	"""Enforces server-side anti-cheat masking filters across all game sessions."""
	global gameState
	with clients_lock:
		for p_id, conn in active_clients.items():
			try:
				# Custom securely filtered snapshot so players can't inspect opponents' cards
				snapshot = gameState.to_net_snapshot(requesting_player_id=p_id)
				packet = json.dumps(["STATE_UPDATE", snapshot]) + "\x00"
				send(conn, packet)
			except:
				continue

def handleClient(connection: socket.socket, addy: tuple[str, int], player_id: int):
	"""Executes handshake sequentially, registers connections, then kicks off a nested background receiver."""
	send(connection, f"CONNECT {port}")
	connected = waitForData(connection) == f"{port} CONNECTED".encode() + b"\x00"
	
	if connected:return None
	with clients_lock:active_clients[player_id] = connection
		
	gameState.players.append({
		"id": player_id,
		"connection": connection,
	})
	
	@startasync
	def client_receiver():
		sprint(f"Async network worker thread engaged for Player {player_id}")
		try:
			while True:
				# Reads until hitting your custom 0x00 null delimiter
				raw_bytes = waitForData(connection, buffersize=4096)
				if not raw_bytes:break
					
				# Strip delimiter and decode to plain text JSON string
				clean_json = raw_bytes.rstrip(b"\x00").decode("utf-8")
				message_type, payload = json.loads(clean_json)
				
				# Pipe data safely into your global logic processing queue
				network_action_queue.put((player_id, message_type, payload))
				
		except Exception as e:
			warn(f"Socket interface link closed for Player {player_id}: {e}")
		finally:
			with clients_lock:
				if player_id in active_clients: del active_clients[player_id]
			connection.close()
			broadcast_message("PLAYER_DROPPED", f"Player {player_id} has left the match.")

	# Execute the nested async thread loop immediately
	client_receiver()
	
	return {"connection": connection, "id": player_id}


cardOwnership: dict[int, game.card] = {}
gameState = None

startEarlyEvent = Event()

def startServer(max_players, recvport, forward_mode, allow_red_joker=False):
	global startEarly, port, gameState
	startEarly = False
	port = recvport if recvport else port
	num_players = 0

	gameState = game.GameState(allow_red_joker=allow_red_joker)
	
	engine_thread = threading.Thread(target=game_logic_engine, daemon=True)
	engine_thread.start()

	addy = ['', port]
	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	ngrokURL = ""
	
	match forward_mode:
		case "Local Machine":
			addy[0] = "127.0.0.1"
		case "Local Network":
			sprint("Starting local connection!")
			addy[0] = "0.0.0.0"
		case "Online (UPnP)":
			sprint("Starting UPnP connection!")
			forwarding.add_port_forward(port, 80)
			addy[1] = 80
			addy[0] = "0.0.0.0"
		case "Online (ngrok)":
			sprint("Initializing ngrok!")
			addy[0] = "127.0.0.1"
			try:
				token = load_ngrok_token()
				if not token:
					tunnel = ngrok.forward(addr=addy[1], proto="tcp", authtoken_from_env=True)
					ngrokURL = tunnel.url()
				else:
					tunnel = ngrok.forward(addr=addy[1], proto="tcp", authtoken=token)
					ngrokURL = tunnel.url()
				sprint(f"ngrok active! Public forwarding link: {ngrokURL}")
			except Exception as Error:
				error(f"Failed to initialize ngrok! {Error}")

	server.bind(tuple(addy))
	server.listen()

	PlayerConnections = []

	@startEarlyEvent.Once
	def startEarlyEv():
		global startEarly
		startEarly = True
	
	player_id_counter = 1
	while num_players < max_players:
		if startEarly:
			break
			
		# Unpack connection and kick off secure handshake process
		client_sock, client_addr = server.accept()
		cl = handleClient(client_sock, client_addr, player_id_counter)
		if cl:
			PlayerConnections.append(cl)
			num_players += 1
			player_id_counter += 1
			
			# Auto-start rules execution block once sufficient players fill the slots
			if num_players >= 2 and len(gameState.deck) == 0:
				sprint("Room filled. Initializing card deck rules...")
				gameState.initialize_deck()
				broadcast_state_snapshots()

if not headless:
    gui = ServerGUIApp()

    # Decorate your launch block so Python backgrounds it automatically!
    @startasync
    def background_launcher(max_p, p, f):
        startServer(max_p, p, f, gui_instance=gui)

    gui.startServerEvent.Connect(background_launcher)
    
    # This runs on the main thread, keeping the debugger and Tkinter perfectly synced
    gui.run() 
else:
	startServer(max_players,port,"Online (ngrok)" if forward else "Local Machine",False)

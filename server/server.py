import socket
import ngrok
import os
from shared.useful import *
from sys import argv
from shared import game
from server import forwarding
from server.gui import *

headless = False
max_players = 0
forward = False

args = argv[1:]
for index,arg in enumerate(args):
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
    # Looks for a file named token.txt in the same folder as the game
    if os.path.exists("token.txt"):
        with open("token.txt", "r") as f:
            return f.read().strip()
    return None
 
def handleClient(connection:socket.socket,addy:tuple[str,int]):
	send(connection,f"CONNECT {port}")
	connected = waitForData(connection)==f"{port} CONNECTED".encode()
	if connected:
		gameState.players.append({
			"connection": connection,
		})

cardOwnership:dict[int,game.card] = {}
gameState = game.GameState()

startEarlyEvent = Event()
def startServer(max_players,recvport,forward):
	startEarly = False

	global port;port = recvport if recvport else port
	num_players = 0

	addy = ['',port]
	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	ngrokURL = ""
	match forward:
		case "Local Machine":
			addy[0] = "127.0.0.1"
		case "Local Network":
			sprint("Starting local conncetion!")
			addy[0] = "0.0.0.0"
			
		case "Online (UPnP)":
			sprint("Starting UPnP connection!")
			forwarding.add_port_forward(port,80)
			addy[1] = 80
			addy[0] = "0.0.0.0"
		case "Online (ngrok)":
			sprint("Initializing ngrok!")
			addy[0] = "127.0.0.1"
			try:
				token = load_ngrok_token()
				if not token:
					tunnel = ngrok.forward(addr=addy[1],listener="tcp",authtoken_from_env = True)
					ngrokURL = tunnel.url()
				else:
					tunnel = ngrok.forward(addr=addy[1],listener="tcp",authtoken = token)
					ngrokURL = tunnel.url()
			except Exception as Error:
				error(f"Failed to initialize ngrok! {Error}")


	server.bind(tuple(addy))

	server.listen()

	PlayerConnections = []

	@startEarlyEvent.Once
	def startEarlyEv():
		global startEarly
		startEarly=True
	
	while num_players<max_players:
		if startEarly:break
		cl = handleClient(*server.accept())
		if cl:PlayerConnections.append(cl)
if not headless:
	gui = MainGUI()
	gui.startServer.Connect(startServer)
	gui.run()
	startEarlyEvent.Fire()
else:
	startServer(max_players,None,forward)
import tkinter
import sys
from shared.useful import *  # Pulls startasync, Event, sprint, etc.

class ConsoleRedirector:
	def __init__(self, text_widget, original_stream):
		self.text_widget = text_widget          
		self.original_stream = original_stream  

	def write(self, text):
		self.original_stream.write(text)
		self.original_stream.flush()
		if self.text_widget and self.text_widget.winfo_exists():
			self.text_widget.after(0, self._append_text, text)

	def _append_text(self, text):
		self.text_widget.insert("end", text)
		self.text_widget.see("end")  

	def flush(self):
		self.original_stream.flush()


class SetupScreen(tkinter.Frame):
	def __init__(self, parent, controller):
		super().__init__(parent)
		self.controller = controller
		self.grid_columnconfigure(0, weight=1)

		tkinter.Label(self, text="Decks of Despair Server", font=("Arial", 14, "bold")).grid(row=0, sticky="ew", pady=10)

		tkinter.Label(self, text="Max Players").grid(row=1, sticky="ew")
		self.max_player_inp = tkinter.Entry(self, justify="center")
		self.max_player_inp.insert(0, "2")
		self.max_player_inp.grid(row=2, pady=5)

		tkinter.Label(self, text="Port").grid(row=3, sticky="ew")
		self.port_inp = tkinter.Entry(self, justify="center")
		self.port_inp.insert(0, "8080")
		self.port_inp.grid(row=4, pady=5)

		onlinetypes = ("Local Machine", "Local Network", "Online (UPnP)", "Online (ngrok)")
		self.controller.on_line_type_var.set("Local Network")
		self.onlinetype = tkinter.OptionMenu(self, self.controller.on_line_type_var, *onlinetypes)
		self.onlinetype.grid(row=5, pady=5)

		tkinter.Button(self, text="Start Server", command=self.launch_server_action).grid(row=6, pady=15)

	def launch_server_action(self):
		max_players = int(self.max_player_inp.get() if self.max_player_inp.get() else 2)
		port_num = int(self.port_inp.get() if self.port_inp.get() else 8080)
		mode = self.controller.on_line_type_var.get()

		# Fire off your background server trigger event
		self.controller.startServerEvent.Fire(max_players, port_num, mode)
		self.controller.switch_screen(LiveServerScreen)


class LiveServerScreen(tkinter.Frame):
	def __init__(self, parent, controller):
		super().__init__(parent)
		self.controller = controller
		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(1, weight=1)

		current_mode = self.controller.on_line_type_var.get()
		tkinter.Label(self, text=f"Active Server Engine Logs ({current_mode})", font=("Arial", 11, "bold")).grid(row=0, sticky="w", padx=10, pady=5)

		self.log_display = tkinter.Text(self, bg="black", fg="#a9b7c6", font=("Consolas", 10))
		self.log_display.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

		# Redirect standard printing streams safely into the text area window panel
		sys.stdout = ConsoleRedirector(self.log_display, sys.stdout)
		sys.stderr = ConsoleRedirector(self.log_display, sys.stderr)

		share_frame = tkinter.Frame(self)
		share_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
		share_frame.grid_columnconfigure(1, weight=1)

		tkinter.Label(share_frame, text="Share Link:").grid(row=0, column=0, padx=(0, 5))
		self.controller.link_entry = tkinter.Entry(share_frame)
		self.controller.link_entry.grid(row=0, column=1, sticky="ew")
		
		if self.controller.pending_link_str:
			self.controller.link_entry.insert(0, self.controller.pending_link_str)


class ServerGUIApp(tkinter.Tk):
	def __init__(self):
		super().__init__()
		self.title("Decks of Despair Server")
		self.geometry("600x450")

		self.startServerEvent = Event()  # Shared event contract
		self.on_line_type_var = tkinter.StringVar()
		self.link_entry = None
		self.pending_link_str = ""

		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(0, weight=1)

		self.container = tkinter.Frame(self)
		self.container.grid(row=0, column=0, sticky="nsew")
		self.container.grid_columnconfigure(0, weight=1)
		self.container.grid_rowconfigure(0, weight=1)

		self.active_frame = None
		self.switch_screen(SetupScreen)

	def switch_screen(self, screen_class):
		new_frame = screen_class(parent=self.container, controller=self)
		if self.active_frame is not None:
			self.active_frame.destroy()
		self.active_frame = new_frame
		self.active_frame.grid(row=0, column=0, sticky="nsew")

	def run(self):
		sprint("Tkinter Server GUI initialized smoothly.")
		self.mainloop()

	def showLink(self, link):
		self.pending_link_str = link
		if self.link_entry and self.link_entry.winfo_exists():
			self.link_entry.delete(0, tkinter.END)
			self.link_entry.insert(0, link)

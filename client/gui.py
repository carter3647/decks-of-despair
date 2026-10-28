import tkinter
from shared.useful import *

class joinGUI(tkinter.Tk):
    def __init__(self):
        super().__init__()
        self.title("Decks of Despair - Join Game")
        self.geometry("400x200")

        self.joinGame = Event()

        self.mainFrame = tkinter.Frame(self)
        self.mainFrame.grid_columnconfigure(0,weight=1)
        self.mainFrame.pack(anchor="center",fill="both",expand=True)

import tkinter
from shared.useful import *

class MainGUI(tkinter.Tk):
    def __init__(self):
        super().__init__()
        self.title("Decks of Despair Server")
        self.geometry("400x200")

        self.startServer = Event()

        self.grid_columnconfigure(0,weight=1)
        self.grid_rowconfigure(0,weight=1)

        frame = tkinter.Frame(self)
        frame.grid_columnconfigure(0,weight=1)
        frame.grid(row=0,column=0,sticky="nsew")

        tkinter.Label(frame,text="Decks of Despair Server").grid(row=0,sticky="ew")

        tkinter.Label(frame,text="Max Players").grid(row=1,sticky="ew")
        self.max_player_inp = tkinter.Entry(frame)
        self.max_player_inp.grid(row=2)

        tkinter.Label(frame,text="Port").grid(row=3,sticky="ew")
        self.port_inp = tkinter.Entry(frame)
        self.port_inp.insert(0,"8080")
        self.port_inp.grid(row=4)

        self.onlinetypevar = tkinter.StringVar()
        onlinetypes = (
            "Local Machine",
            "Local Network",
            "Online (UPnP)",
            "Online (ngrok)"
        )
        self.onlinetype = tkinter.OptionMenu(frame,self.onlinetypevar,"Local Network",onlinetypes)
        tkinter.Button(frame,text="Start Server",
                command=lambda:(self.startServer.Fire(
                    int(self.max_player_inp.get()if self.max_player_inp.get()else 0),
                    int(self.port_inp.get()if self.port_inp.get()else 8080),
                    self.onlinetypevar.get()
                    ))
            ).grid(row=7)
        tkinter.Label(frame,text="Share Link")
        self.link = tkinter.Entry(state="readonly")

    @startasync
    def run(self):
        sprint("Tkinter initialized!")
        self.mainloop()

    def showLink(self,link):
        self.link.delete(0,tkinter.END)
        self.link.insert(0,link)
        


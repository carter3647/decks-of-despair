from threading import Thread as _thread
import socket
import json

def startasync(fn):
	def set_doc(doc,name):
		def decorator(func):
			func.__doc__ = doc
			func.__name__ = name
			return func
		return decorator
	@set_doc(fn.__doc__,fn.__name__)
	def wrapper(*args,**kwargs):
		_thread(target=fn,args=args,kwargs=kwargs).start()
	return wrapper

def send(conn:socket.socket,data:bytes|str):
	if type(data)==bytes:conn.sendall(data+b"\x00")
	if type(data)==str:conn.sendall(data.encode()+b"\x00")

def waitForData(connection:socket.socket,buffersize=1024):
	segments = []
	while True:
		data = connection.recv(buffersize)
		if not data: error("Data was incomplete, returning.");return bytes()
		segments.append(data)
		if data[-1]==0x00: break
	return bytes().join(segments)

def warn(text):
	chop = text.split("\n")
	unchop = ""
	for index,splice in enumerate(chop):
		if index==0:unchop+=splice;continue
		unchop += "\n         "
		unchop += splice
	print(f"\033[1;38;2;255;165;0mWARNING: {unchop}\033[0m")

def error(text):
	chop = text.split("\n")
	unchop = ""
	for index,splice in enumerate(chop):
		if index==0:unchop+=splice;continue
		unchop += "\n         "
		unchop += splice
	print(f"\033[1;38;2;255;0;0mERROR:   {unchop}\033[0m")

def sprint(text:str):
	chop = text.split("\n")
	unchop = ""
	for index,splice in enumerate(chop):
		if index==0:unchop+=splice;continue
		unchop += "\n         "
		unchop += splice
	print(f"INFO:    {unchop}")

class _Connection():
	def Disconnect(self):
		self.__table.pop(self.__index)
	def __init__(self,table,index):
		self.__table:list = table
		self.__index = index

class Event:
	def __init__(self):
		self.__connections = []
		self.__otc = []
	def Connect(self,func):
		self.__connections.append(func)
		return _Connection(self.__connections,len(self.__connections)-1)
	def Once(self,func):
		self.__otc.append(func)
	def Fire(self,*args,**kwargs):
		for function in self.__connections:
			_thread(target=function,args=args,kwargs=kwargs).run()
		for function in self.__otc:
			_thread(target=function,args=args,kwargs=kwargs).run()
			self.__otc.remove(function)


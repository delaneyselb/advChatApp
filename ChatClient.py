# Delaney Selb; CMSC440 Advanced Chat Application; 4/5/2026

# IMPLEMENTATION PLAN:
# ChatClient.py:
# 7. startup and arg validation (DONE)
# 8. connect, register, framing (DONE)
# 9. receive thread and display
# 10. input loop and commands
# 11. heartbeat and summary

from datetime import datetime
from socket import *
import sys
import struct
import json # struct and json will help with framing
import threading

running = True # flag for exit detection

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# NETWORK PROTOCOL: FRAMED MSGS OVER TCP
def recv_all(sock,n):
    data = b''
    while len(data)<n:
        chunk = sock.recv(n-len(data))
        if not chunk: return None
        data += chunk
    return data

def recv_msg(sock):
    raw_len = recv_all(sock,4) # gets exactly 4 bytes
    if not raw_len:return None
    msg_len = struct.unpack('!I',raw_len)[0]
    # If N is invalid (e.g., N == 0 or N > 65536), the receiver must close the connection
    if msg_len == 0 or msg_len>65536: return None
    data = recv_all(sock,msg_len)
    if not data: return None
    return json.loads(data.decode())

def send_msg(sock,msg_dict):
    data = json.dumps(msg_dict).encode()
    msg_len = struct.pack('!I',len(data))
    sock.sendall(msg_len+data)

def listen_server(sock): #thread func listens for msgs froms server
    global running
    while running:
        try:
            msg = recv_msg(sock)
            if msg is None:
                if running:
                    print("Disconnected from server.")
                break

            # now handle different types of messages
            mtype = msg.get("type")
            if mtype == "deliver":
                print(f"[{msg['room']}] {msg['from']}: {msg['text']}")
            elif mtype == "pm":
                print(f"[PM from {msg['from']}] {msg['text']}")
            elif mtype == "system":
                print(f"[SYSTEM] {msg['message']}")
            elif mtype == "history":
                print(f"[HISTORY for {msg['room']}]")
                for m in msg.get("messages", []):
                    print(f"{m['from']}: {m['text']}")
            elif mtype == "ok":
                print(f"[OK] {msg.get('message')}")
            elif mtype == "error":
                print(f"[ERROR] {msg.get('message')}")
            else:
                print(f"[UNKNOWN MSG] {msg}")

        except Exception as e:
            if running: 
                print('Connection lost.')
            else:
                print("Error receiving message:", e)
            break

# accept four command line args:
#  1) <hostname> or <ip> of your chat server
#  2) <port> number your server is running on
#  3) <nickname> (must be unique among currently connected clients)
#  4) <ClientID> (a unique identifier for this client session)
#  Example: ChatClient 10.0.0.1 12345 John 001
args = sys.argv
if len(args) != 5:
    print("ERR - arg 1")
    sys.exit(1)

hostname = args[1]
try:
    port = int(args[2])
    assert 0 < port < 65536
except:
    print("ERR - arg 2")
    sys.exit(1)
nickname = args[3]
clientID = args[4]

try: 
    server_ip = gethostbyname(gethostname())
except:
    print("ERR - arg 1")
    sys.exit(1)


# Create socket and connect to server
clientSocket = socket(AF_INET, SOCK_STREAM)
try:
    clientSocket.connect((server_ip, port))
except Exception as e:
    print("Connection failed:",e)
    sys.exit(1)


# print welcome msg
print(f"ChatClient started with server IP: {server_ip}, port: {port}, nickname: {nickname}, client ID: {clientID}, Date/Time: {now_str()}")

# after connecting, client registers nickname w/ server
# client must allow the user to type while also printing messages from the server at any time
# commands begin with '/' anything else is treated as chat msg

# send registration msg
send_msg(clientSocket,{
    "type": "register", 
    "nickname": nickname, 
    "clientID": clientID,
    "timestamp": now_str()
})

# receive server response
resp = recv_msg(clientSocket)
if not resp or resp.get("type") != "ok":
    print("Registration failed:",resp)
    sys.exit(1)

print(f"Connected to server. Joined room: {resp.get('room')}")
if "history" in resp:
    for m in resp["history"]:
        print(f"[HISTORY] {m['from']}: {m['text']}")

# start listening thread
threading.Thread(target=listen_server, args=(clientSocket,), daemon=True).start()

try:
    while True:
        msg = input("Enter message: ").strip()
        if msg.strip() == "":
            continue # do nothing if empty
        send_msg(clientSocket,{"type":"text","text":msg})
except KeyboardInterrupt:
    print("\nExiting...")
finally:
    running = False # end threat before closing the socket so no issues
    clientSocket.close()

# SUPPORTED COMMANDS
# • /join <room> Join (or create) a room. You leave your previous room
# automatically.
# • /leave Leave the current room and return to lobby.
# • /rooms List active rooms (rooms with at least one connected client).
# • /who <room> List nicknames currently in the specified room.
# • /msg <nickname> <text> Send a private message to a specific nickname (across all
# rooms).
# • /nick <newnick> Change your nickname (must remain unique).
# • /disconnect Gracefully disconnect from the server.

# DISPLAYING MESSAGES RECEIVED FROM SERVER
# <date/time> :: [<room>] <SenderNick>: <message text>
# <date/time> :: [PM from <SenderNick>] <message text>
# <date/time> :: * <system message>

# EXIT CLIENT SESSION SUMMARY
# Summary: start:<start date/time>, end:<end date/time>, room:<last
# room>, rooms joined:<#>, chat sent:<#>, chat rcv:<#>, pm sent:<#>, pm
# rcv:<#>, char sent:<#>, char rcv:<#>

# CLIENT TO SERVER MSG FORMATTING:
# 1) Registration (must be the first message after connect):
# { "type": "register", "nickname": "<nickname>", "clientID":
# "<ClientID>", "timestamp": "<timestamp>" }
# 2) One general outgoing message for BOTH chat and commands:
# The client uses the SAME message format below for normal chat text and for commands. If
# the "text" field begins with “/”, the server treats it as a command; otherwise it is a chat
# message to the current room.
# { "type": "text", "room": "<current room>", "nickname": "<nickname>",
# "clientID": "<ClientID>", "text": "<what the user typed>", "timestamp":
# "<timestamp>" }
# Examples:
# Chat: { "type":"text", "room":"lobby", "nickname":"John",
# "clientID":"001", "text":"hello", "timestamp":"..." }
# Command: { "type":"text", "room":"lobby", "nickname":"John",
# "clientID":"001", "text":"/join lab", "timestamp":"..." }
# Command: { "type":"text", "room":"lab", "nickname":"John",
# "clientID":"001", "text":"/msg Alice hi", "timestamp":"..." }
# 3) Heartbeat ping (sent automatically by the client):
# { "type": "ping", "nickname": "<nickname>", "clientID": "<ClientID>",
# "timestamp": "<timestamp>" }
# 4) Graceful disconnect:
# { "type": "disconnect", "nickname": "<nickname>", "clientID":
# "<ClientID>", "timestamp": "<timestamp>" }

# HEARTBEAT AND TIMEOUT
# To detect broken connections and idle clients, implement an application-layer heartbeat:
# • Client requirement: every 10 seconds (while connected), ChatClient must send a ping
# message.
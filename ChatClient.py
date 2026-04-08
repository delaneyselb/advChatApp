# Delaney Selb; CMSC440 Advanced Chat Application; 4/7/2026
# ChatClient.py

from datetime import datetime
from socket import *
import sys
import struct
import json # struct and json will help with framing
import threading
import time
 
running = True # flag for exit detection
def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
 
start_time = now_str()
current_room = "lobby"
 
rooms_visited = {"lobby"}
chat_sent = 0
chat_rcv = 0
pm_sent = 0
pm_rcv = 0
char_sent = 0
char_rcv = 0
 
def send_heartbeat(sock, nickname, clientID):
    while running:
        time.sleep(10)  # wait 10 seconds
        if not running:
            break
        try:
            send_msg(sock, {
                "type": "ping",
                "nickname": nickname,
                "clientID": clientID,
                "timestamp": now_str() 
            })
        except Exception as e:
            print("Connection lost, stopping heartbeat:", e)
            break
 
# NETWORK PROTOCOL: FRAMED MSGS OVER TCP
def recv_all(sock, n):
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk: return None
        data += chunk
    return data
 
def recv_msg(sock):
    raw_len = recv_all(sock, 4) # gets exactly 4 bytes
    if not raw_len: return None
    msg_len = struct.unpack('!I', raw_len)[0]
    # If N is invalid (e.g., N == 0 or N > 65536), the receiver must close the connection
    if msg_len == 0 or msg_len > 65536: return None
    data = recv_all(sock, msg_len)
    if not data: return None
    return json.loads(data.decode())
 
def send_msg(sock, msg_dict):
    data = json.dumps(msg_dict).encode()
    msg_len = struct.pack('!I', len(data))
    sock.sendall(msg_len + data)
 
def listen_server(sock): # thread func listens for msgs from server
    global running, chat_rcv, pm_rcv, char_rcv, current_room, rooms_visited
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
                print(f"{now_str()} :: [{msg['room']}] {msg['from']}: {msg['text']}")
                chat_rcv += 1
                char_rcv += len(msg["text"])
            elif mtype == "pm":
                print(f"{now_str()} :: [PM from {msg['from']}] {msg['text']}")
                pm_rcv += 1
                char_rcv += len(msg["text"])
            elif mtype == "system":
                message_text = msg.get("message", "")
                print(f"{now_str()} :: * {message_text}")
                if message_text.startswith("joined room "):
                    new_room = message_text[len("joined room "):]
                    current_room = new_room
                    rooms_visited.add(new_room)
            elif mtype == "history":
                # display history in the same format as live messages
                messages = msg.get("messages", [])
                if not messages:
                    continue
                room_name = msg.get("room", current_room)
                print(f"{now_str()} :: * [History for {room_name}]")
                for m in messages:
                    ts = m.get("timestamp", now_str())
                    print(f"{ts} :: [{room_name}] {m['from']}: {m['text']}")
            elif mtype == "ok":
                # ignore registration ok, only print others
                if "registered" not in msg.get("message", ""):
                    print(f"[OK] {msg.get('message')}")
            elif mtype == "error":
                print(f"[ERROR] {msg.get('message')}")
            else:
                print(f"[UNKNOWN MSG] {msg}")
 
        except Exception as e:
            if running: 
                print("Error receiving message:", e)
            break
 
# accept four command line args:
#  1) <hostname> or <ip> of your chat server
#  2) <port> number your server is running on
#  3) <nickname> (must be unique among currently connected clients)
#  4) <ClientID> (a unique identifier for this client session)
#  Example: ChatClient 10.0.0.1 12345 John 001
args = sys.argv
 
if len(args) < 5:
    print(f"ERR - arg {len(args)}")
    sys.exit(1)
 
if len(args) > 5:
    print("ERR - arg 1")
    sys.exit(1)
 
hostname = args[1]
try:
    server_ip = gethostbyname(hostname)
except:
    print("ERR - arg 1")
    sys.exit(1)
 
try:
    port = int(args[2])
    assert 0 < port < 65536
except:
    print("ERR - arg 2")
    sys.exit(1)
 
nickname = args[3]
clientID = args[4]
 
# Create socket and connect to server
clientSocket = socket(AF_INET, SOCK_STREAM)
try:
    clientSocket.connect((server_ip, port))
except Exception as e:
    print("Connection failed:", e)
    sys.exit(1)
 
 
# print welcome msg
print(f"ChatClient started with server IP: {server_ip}, port: {port}, nickname: {nickname}, client ID: {clientID}, Date/Time: {now_str()}")
 
# after connecting, client registers nickname w/ server
# client must allow the user to type while also printing messages from the server at any time
# commands begin with '/' anything else is treated as chat msg
 
# send registration msg
send_msg(clientSocket, {
    "type": "register", 
    "nickname": nickname, 
    "clientID": clientID,
    "timestamp": now_str()
})
 
# receive ok msg first
while True:
    resp = recv_msg(clientSocket)
    if not resp:
        print("Registration failed: no response")
        sys.exit(1)
    if resp.get("type") == "ok":
        print(f"{now_str()} :: * joined room lobby")
        break
    elif resp.get("type") == "error":
        print("Registration failed:", resp.get("message"))
        sys.exit(1)
    else:
        # ignore anything else before ok 
        continue
 
# start listening thread
threading.Thread(target=listen_server, args=(clientSocket,), daemon=True).start()
# start heartbeat thread
threading.Thread(target=send_heartbeat, args=(clientSocket, nickname, clientID), daemon=True).start()
 
try:
    while True:
        msg = input().strip()
        if msg.strip() == "":
            continue # do nothing if empty
        if msg == "/disconnect":
            send_msg(clientSocket, {"type": "disconnect", "nickname": nickname, "clientID": clientID, "timestamp": now_str()})
            break # exit loop but still hit finally
        # handle /nick before /msg so its not counted as a pm
        if msg.startswith("/nick"):
            parts = msg.split()
            if len(parts) == 2:
                nickname = parts[1]
        elif msg.startswith("/msg"):
            pm_sent += 1
            pm_text = " ".join(msg.split()[2:])
            char_sent += len(pm_text)
        elif not msg.startswith("/"):
            chat_sent += 1
            char_sent += len(msg)
        send_msg(clientSocket, {
            "type": "text",
            "room": current_room,
            "nickname": nickname,
            "clientID": clientID,
            "text": msg,
            "timestamp": now_str()
        })
except KeyboardInterrupt:
    pass # still goes to the finally block
finally:
    running = False # end thread before closing the socket so no issues
    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rooms_joined_count = len(rooms_visited) 
 
    print(f"Summary: start:{start_time}, end:{end_time}, "
        f"room:{current_room}, rooms joined:{rooms_joined_count}, "
        f"chat sent:{chat_sent}, chat rcv:{chat_rcv}, "
        f"pm sent:{pm_sent}, pm rcv:{pm_rcv}, "
        f"char sent:{char_sent}, char rcv:{char_rcv}")
    clientSocket.close()
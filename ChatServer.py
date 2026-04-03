# Delaney Selb; CMSC440 Advanced Chat Application; 4/5/2026

# IMPLEMENTATION PLAN:
# ChatServer.py:
# 1. startup and arg validation (DONE)
# 2. accept one client, framing (DONE)
# 3. registration and lobby
# 4. multiple clients and rooms
# 5. commands and private messages
# 6. heartbeat timeout

from datetime import datetime
from socket import *
import sys
import struct
import json # struct and json will help with framing
import time 
import threading

clients = {}  
# nickname -> {
#   "socket": socket,
#   "clientID": str,
#   "room": str,
#   "last_seen": time
# }

rooms = {
    "lobby": {
        "members": set(),
        "history": []
    }
}

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# HANDLE CLIENTS
# HANDLE CLIENTS
def handle_client(conn, addr):
    nickname = None  # define here to ensure finally block works
    try:
        # registration!
        msg = recv_msg(conn)
        if not msg or msg.get("type") != "register":
            conn.close()
            return
        nickname = msg["nickname"]
        clientID = msg["clientID"]

        # check duplicate nickname
        if nickname in clients:
            send_msg(conn, {
                "type": "error",
                "message": "nickname already in use",
                "timestamp": now_str()
            })
            conn.close()
            return

        # register client
        clients[nickname] = {
            "socket": conn,
            "clientID": clientID,
            "room": "lobby",
            "last_seen": time.time()
        }
        rooms["lobby"]["members"].add(nickname)

        # log connection
        print(f"{now_str()} :: {nickname}: connected. (ClientID={clientID})")
        print(f"{now_str()} :: {nickname}: joined room lobby.")

        # send ok for registration + lobby history
        send_msg(conn, {
            "type": "ok",
            "message": "registered",
            "room": "lobby",
            "history": rooms["lobby"]["history"],
            "timestamp": now_str()
        })

        # main loop
        while True:
            msg = recv_msg(conn)
            if not msg:
                break
            clients[nickname]["last_seen"] = time.time()

            if msg.get("type") != "text":
                continue

            text = msg.get("text")
            room = clients[nickname]["room"]

            # commands
            if text.startswith("/"):
                parts = text.split()
                command = parts[0]

                # /join <room>
                if command == "/join":
                    if len(parts) != 2:
                        send_msg(conn, {
                            "type": "error",
                            "message": "Usage: /join <room>",
                            "timestamp": now_str()
                        })
                    new_room = parts[1]
                    old_room = clients[nickname]["room"]

                    # leave old room
                    rooms[old_room]["members"].discard(nickname)

                    # join new room
                    if new_room not in rooms:
                        rooms[new_room] = {"members": set(), "history": []}
                    rooms[new_room]["members"].add(nickname)
                    clients[nickname]["room"] = new_room

                    # send confirmation + room history
                    send_msg(conn, {
                        "type": "ok",
                        "message": f"joined {new_room}",
                        "room": new_room,
                        "history": rooms[new_room]["history"],
                        "timestamp": now_str()
                    })
                    print(f"{now_str()} :: {nickname}: joined room {new_room}.")
                elif command == "/leave":
                    if len(parts) != 1:
                        send_msg(conn, {
                            "type": "error",
                            "message": "Usage: /leave",
                            "timestamp": now_str()
                        })
                    new_room = "lobby"
                    old_room = clients[nickname]["room"]

                    # leave old room
                    rooms[old_room]["members"].discard(nickname)

                    # join new room
                    if new_room not in rooms:
                        rooms[new_room] = {"members": set(), "history": []}
                    rooms[new_room]["members"].add(nickname)
                    clients[nickname]["room"] = new_room

                    # send confirmation + room history
                    send_msg(conn, {
                        "type": "ok",
                        "message": f"joined {new_room}",
                        "room": new_room,
                        "history": rooms[new_room]["history"],
                        "timestamp": now_str()
                    })
                    print(f"{now_str()} :: {nickname}: joined room {new_room}.")   

                elif command == "/rooms":
                    if len(parts) != 1:
                        send_msg(conn, {
                            "type": "error",
                            "message": "Usage: /rooms",
                            "timestamp": now_str()
                        })
                    print("Active Rooms:")
                    for room in rooms:
                        if len(rooms[room]["members"]) >= 1:
                            print(room)

                elif command == "/who":
                    if len(parts) != 2:
                        send_msg(conn, {
                            "type": "error",
                            "message": "Usage: /who <room>",
                            "timestamp": now_str()
                        })
                    room = parts[1]

                    # search for that room then print all members in it
                    if room in rooms:
                        print(f"User(s) currently in {room}:")
                        for member in rooms[room]["members"]:
                            print(member)
                    else: # room DNE
                        print(f"{room} does not currently exist.")

                    # send confirmation + room history
                    send_msg(conn, {
                        "type": "ok",
                        "message": f"joined {new_room}",
                        "room": new_room,
                        "history": rooms[new_room]["history"],
                        "timestamp": now_str()
                    })
                elif command == "/msg":
                    if len(parts) < 3:
                        send_msg(conn, {
                            "type": "error",
                            "message": "Usage: /msg <nickname> <text>",
                            "timestamp": now_str()
                        })
                    target_user = parts[1]
                    text = " ".join(parts[2:])
                    # see if target_user exists in curr client list
                    if target_user not in clients:
                        send_msg(conn, {
                            "type": "error",
                            "message": f"User {target_user} not found",
                            "timestamp": now_str()
                        })
                    else:
                        pm_msg = {
                            "type": "pm",
                            "from": nickname,
                            "text": text,
                            "timestamp": now_str()
                        }

                        try: 
                            send_msg(clients[target_user]["socket"], pm_msg)

                            print(f"PrivateDelivered: From:{nickname}, To:{target_user}, "
                            f"Date/Time:{now_str()}, Msg-Size:{len(text.encode())}")

                        except:
                            # send msg 
                            send_msg(conn, {
                                "type": "error",
                                "message": f"joined {new_room}Failed to send message to {target_user}",
                                "timestamp": now_str()
                            })
                        continue
                else:
                    # other commands can go here (e.g., /list, /leave)
                    send_msg(conn, {
                        "type": "error",
                        "message": f"Unknown command {command}",
                        "timestamp": now_str()
                    })
                    continue

            # reg txt msg
            sender = nickname
            clientID = clients[sender]["clientID"]
            ip, port = addr
            msg_size = len(text.encode())
            print(f"Received: IP:{ip}, Port:{port}, Client-Nickname:{sender}, "
                  f"ClientID:{clientID}, Room:{room}, Date/Time:{now_str()}, Msg-Size:{msg_size}")

            out_msg = {
                "type": "deliver",
                "room": room,
                "from": sender,
                "text": text,
                "timestamp": now_str()
            }

            # append to room history
            history = rooms[room]["history"]
            history.append({"from": sender, "text": text, "timestamp": now_str()})
            if len(history) > 20:  # max prev 20 msgs in room 
                history.pop(0)

            # send to other members
            recipients = []
            for user in rooms[room]["members"]:
                if user != sender:
                    try:
                        send_msg(clients[user]["socket"], out_msg)
                        recipients.append(user)
                    except Exception as e:
                        print("Error:", e)
            if recipients:
                print(f"Delivered(Room={room}): {', '.join(recipients)}")
            else:
                print(f"Delivered(Room={room}): (none)")

    except Exception as e:
        print("Error:", e)
    finally:
        # cleanup on disconnect
        if nickname and nickname in clients:
            room = clients[nickname]["room"]
            rooms[room]["members"].discard(nickname)
            del clients[nickname]
            print(f"{now_str()} :: {nickname}: disconnected.")
        conn.close()

# NETWORK PROTOCOL: FRAMED MSGS OVER TCP
# Every message sent across the network has the following structure:
# 4 bytes: unsigned integer N (big-endian)
# N bytes: message body (UTF-8 text)
# loops until it reads exactly 4 bytes for N, then loops until it reads
# exactly N bytes for the body
def recv_all(sock,n):
    data = b''
    while len(data)<n:
        chunk = sock.recv(n-len(data))
        if not chunk:
            return None
        data += chunk
    return data

def recv_msg(sock):
    raw_len = recv_all(sock,4) # gets exactly 4 bytes
    if not raw_len:
        return None
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

# accept only one command line arg: <port>
args = sys.argv
if len(args) != 2:
    print("ERR - arg 1")
    sys.exit(1)
try: 
    port = int(args[1])
    assert 0<port<65536  # must validate that port is a pos int less than 65536
except(ValueError,AssertionError): # if invalid, exit after printing: ERR - arg 1
    print("ERR - arg 1")
    sys.exit(1)

# Create welcoming socket using the given port
try:
    welcomeSocket = socket(AF_INET, SOCK_STREAM)
    welcomeSocket.bind(('', port))
    welcomeSocket.listen(10) # double check this 10 value
except Exception:
    # If the server cannot bind/listen on the port (e.g., already in use)
    print(f"ERR - cannot create ChatServer socket using port number {port}")
    sys.exit(1)

#IF SERVER SUCCESSFULLY STARTS:
server_ip = gethostbyname(gethostname())
print(f"ChatServer started with server IP: {server_ip}, port: {port}, Date/Time: {now_str()}")

# While loop to handle arbitrary sequence of clients making requests
try:
    while 1:
        conn, addr = welcomeSocket.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
except KeyboardInterrupt:
    print("\nExiting...")

# • Heartbeat Timeout: disconnect clients that go silent for too long (see Heartbeat section).


# SERVER TO CLIENT MSG FORMATTING:
# Server acknowledgement after successful registration:
# { "type": "ok", "message": "registered", "room": "lobby", "timestamp":
# "<timestamp>" }
# Server error (used for duplicate nickname, invalid command, etc.):
# { "type": "error", "message": "<human-readable error>", "timestamp":
# "<timestamp>" }
# Delivered room chat message (server → clients in the room, excluding sender):
# { "type": "deliver", "room": "<room>", "from": "<sender nickname>",
# "text": "<message text>", "timestamp": "<timestamp>" }
# Private message delivery (server → target client):
# { "type": "pm", "from": "<sender nickname>", "text": "<message text>",
# "timestamp": "<timestamp>" }
# System message (join/leave/rename notifications and command responses):
# { "type": "system", "message": "<text>", "timestamp": "<timestamp>" }
# Room history (sent to a client immediately after a successful /join):
# { "type": "history", "room": "<room>", "messages": [
# { "from": "A", "text": "hi", "timestamp": "..." },
# { "from": "B", "text": "hello", "timestamp": "..." }
# ], "timestamp": "<timestamp>" }

#ROOM RULES
# • Room names must be 1–20 characters and may contain letters, digits, underscore (_), or
# hyphen (-). No spaces.
# • Room “lobby” always exists.
# • The server creates a room automatically when the first user joins it.
# • When a user joins a room, the server must: (1) move them from old room to new room,
# (2) notify users in both rooms with a system message, and (3) send the new room
# history to the joining client

# HEARTBEAT AND TIMEOUT
# To detect broken connections and idle clients, implement an application-layer heartbeat:
# • Client requirement: every 10 seconds (while connected), ChatClient must send a ping
# message.
# • Server requirement: update a client's last-seen time whenever ANY valid message is
# received (including ping).
# • If no message is received from a client for 30 seconds, the server must treat the client as
# disconnected and close the socket.

# MORE MSG FORMATTING
# The server must print the following logs to standard output (exact prefixes required).
# 1) On successful connection + registration:
# <date/time> :: <client nickname>: connected. (ClientID=<ClientID>)
# 2) On room change:
# <date/time> :: <client nickname>: joined room <room>.
# 3) On nickname change:
# <date/time> :: <old nickname>: changed nickname to <new nickname>.
# 4) For each text message received (chat or command):
# Received: IP:<ip>, Port:<port>, Client-Nickname:<Client Nickname>,
# ClientID:<ClientID>, Room:<room>, Date/Time:<date/time>, Msg-Size:<msg
# size>
# 5) For each delivered room chat message, print recipients in that room (excluding sender):
# Delivered(Room=<room>): <Client1 Nickname>, <Client2 Nickname>, ...
# If there are no recipients, print:
# Delivered(Room=<room>): (none)
# 6) For private messaging delivery:
# PrivateDelivered: From:<sender>, To:<target>, Date/Time:<date/time>,
# Msg-Size:<msg size>
# 7) On history delivery (after /join):
# HistoryDelivered: Room:<room>, To:<nickname>, Count:<n>
# 8) On disconnect (graceful or timeout):
# <date/time> :: <client nickname>: disconnected.

# OTHER RULES:
# remain running until closed with ctrl c
# handle unexpected client termination (server cleans up the client, logs disconnected, and closes the socket)
# follow the framing rule exactly (4-byte length + msg body)
# use only basic socket classes. external libs are not allowed.
# program must run on VM Linux machines

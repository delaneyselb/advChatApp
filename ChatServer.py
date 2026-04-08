# Delaney Selb; CMSC440 Advanced Chat Application; 4/7/2026
# ChatServer.py

from datetime import datetime
from socket import *
import sys
import struct
import json # struct and json will help with framing
import time 
import threading
import re

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
lock = threading.Lock() # use this since both handle_client and monitoring_timeouts

VALID_ROOM_NAME = re.compile(r'^[A-Za-z0-9_-]{1,20}$') # room name validation pattern

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def monitor_timeouts():
    while True:
        time.sleep(1)
        now = time.time()
        timed_out = []
        with lock:
            for nick in list(clients.keys()):
                if now - clients[nick]["last_seen"] > 30: # 30s timeout
                    timed_out.append(nick)

        for nick in timed_out:
            with lock:
                if nick not in clients:
                    continue
                room = clients[nick]["room"]
                sock = clients[nick]["socket"]
                rooms[room]["members"].discard(nick)
                # snapshot room members before deleting so i can notify them
                room_members = list(rooms[room]["members"])
                del clients[nick]

            print(f"{now_str()} :: {nick}: disconnected.")
            try:
                sock.close()
            except:
                pass

            # notify remaining room members on timeout
            for user in room_members:
                with lock:
                    usock = clients[user]["socket"] if user in clients else None
                if usock:
                    try:
                        send_msg(usock, {
                            "type": "system",
                            "message": f"{nick} has left the room.",
                            "timestamp": now_str()
                        })
                    except:
                        pass

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

        with lock:
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

        # send ok for registration 
        send_msg(conn, {
            "type": "ok",
            "message": "registered",
            "room": "lobby",
            "timestamp": now_str()
        })
        # send lobby history after ok
        with lock:
            lobby_history = list(rooms["lobby"]["history"])
        send_msg(conn, {
            "type": "history",
            "room": "lobby",
            "messages": lobby_history,
            "timestamp": now_str()
        })
        print(f"HistoryDelivered: Room:lobby, To:{nickname}, Count:{len(lobby_history)}")

        # main loop
        while True:
            msg = recv_msg(conn)
            if not msg:
                break
            clients[nickname]["last_seen"] = time.time()
            msg_type = msg.get("type")
            if msg_type == "disconnect":
                break
            # handle heartbeat functionality
            if msg_type == "ping":
                continue # do nothing/stay connected
            if msg_type != "text":
                continue
            text = msg.get("text", "")
            with lock:
                room = clients[nickname]["room"] if nickname in clients else "lobby"

            ip, port = addr
            # note: msg_size is the full encoded message body size, not just the text field
            full_body = json.dumps(msg).encode()
            msg_size = len(full_body)
            print(f"Received: IP:{ip}, Port:{port}, Client-Nickname:{nickname}, "
                  f"ClientID:{clientID}, Room:{room}, Date/Time:{now_str()}, Msg-Size:{msg_size}")
            
            # commands
            if text.startswith("/"):
                parts = text.split()
                command = parts[0]

                # /join 
                if command == "/join":
                    if len(parts) != 2:
                        send_msg(conn, {
                            "type": "error",
                            "message": "Usage: /join <room>",
                            "timestamp": now_str()
                        })
                        continue
                    new_room = parts[1]
                    # validate room name (1-20 chars, letters/digits/underscore/hyphen only)
                    if not VALID_ROOM_NAME.match(new_room):
                        send_msg(conn, {
                            "type": "error",
                            "message": "Invalid room name. Use 1-20 characters: letters, digits, _ or -",
                            "timestamp": now_str()
                        })
                        continue
                    with lock:
                        old_room = clients[nickname]["room"]
                        if old_room == new_room:
                            send_msg(conn, {"type": "system", "message": f"Already in {new_room}.", "timestamp": now_str()})
                            continue
                        rooms[old_room]["members"].discard(nickname)
                        if new_room not in rooms:
                            rooms[new_room] = {"members": set(), "history": []}
                        rooms[new_room]["members"].add(nickname)
                        clients[nickname]["room"] = new_room
                        # snapshot members for notifications and history for delivery
                        old_members = list(rooms[old_room]["members"])
                        new_members = list(rooms[new_room]["members"])
                        new_history = list(rooms[new_room]["history"])
 
                    # notify old room (outside lock — sending can block)
                    for user in old_members:
                        with lock:
                            sock = clients[user]["socket"] if user in clients else None
                        if sock:
                            try:
                                send_msg(sock, {"type": "system", "message": f"{nickname} has left the room.", "timestamp": now_str()})
                            except:
                                pass
 
                    # notify new room excluding self
                    for user in new_members:
                        if user == nickname:
                            continue
                        with lock:
                            sock = clients[user]["socket"] if user in clients else None
                        if sock:
                            try:
                                send_msg(sock, {"type": "system", "message": f"{nickname} has joined the room.", "timestamp": now_str()})
                            except:
                                pass
 
                    # tell joining client and send history
                    send_msg(conn, {"type": "system", "message": f"joined room {new_room}", "timestamp": now_str()})
                    send_msg(conn, {"type": "history", "room": new_room, "messages": new_history, "timestamp": now_str()})
                    print(f"{now_str()} :: {nickname}: joined room {new_room}.")
                    print(f"HistoryDelivered: Room:{new_room}, To:{nickname}, Count:{len(new_history)}")
                    continue
 
                elif command == "/leave":
                    if len(parts) != 1:
                        send_msg(conn, {"type": "error", "message": "Usage: /leave", "timestamp": now_str()})
                        continue

                    with lock:
                        old_room = clients[nickname]["room"]

                    # prevent /leave from lobby
                    if old_room == "lobby":
                        send_msg(conn, {"type": "error", "message": "Already in lobby.", "timestamp": now_str()})
                        continue
                    
                    # change member/room lists, take care of history too
                    new_room = "lobby"
                    with lock:
                        rooms[old_room]["members"].discard(nickname)
                        if new_room not in rooms:
                            rooms[new_room] = {"members": set(), "history": []}
                        rooms[new_room]["members"].add(nickname)
                        clients[nickname]["room"] = new_room
                        old_members = list(rooms[old_room]["members"])
                        new_members = list(rooms[new_room]["members"])
                        new_history = list(rooms[new_room]["history"])
 
                    for user in old_members:
                        with lock:
                            sock = clients[user]["socket"] if user in clients else None
                        if sock:
                            try:
                                send_msg(sock, {"type": "system", "message": f"{nickname} has left the room.", "timestamp": now_str()})
                            except:
                                pass
 
                    for user in new_members:
                        if user == nickname:
                            continue
                        with lock:
                            sock = clients[user]["socket"] if user in clients else None
                        if sock:
                            try:
                                send_msg(sock, {"type": "system", "message": f"{nickname} has joined the room.", "timestamp": now_str()})
                            except:
                                pass
 
                    send_msg(conn, {"type": "system", "message": "joined room lobby", "timestamp": now_str()})
                    send_msg(conn, {"type": "history", "room": new_room, "messages": new_history, "timestamp": now_str()})
                    print(f"{now_str()} :: {nickname}: joined room {new_room}.")
                    print(f"HistoryDelivered: Room:{new_room}, To:{nickname}, Count:{len(new_history)}")
                    continue
 
                elif command == "/rooms":
                    with lock:
                        active = [r for r, data in rooms.items() if data["members"]]
                    room_list = ", ".join(sorted(active)) if active else "(none)"
                    send_msg(conn, {"type": "system", "message": f"Active rooms: {room_list}", "timestamp": now_str()})
                    continue
 
                elif command == "/who":
                    if len(parts) != 2:
                        send_msg(conn, {"type": "error", "message": "Usage: /who <room>", "timestamp": now_str()})
                        continue
                    target_room = parts[1]
                    with lock:
                        if target_room in rooms:
                            members_snap = list(rooms[target_room]["members"])
                        else:
                            members_snap = None
 
                    if members_snap is None:
                        send_msg(conn, {"type": "system", "message": f"Room {target_room} does not exist.", "timestamp": now_str()})
                    else:
                        nick_list = ", ".join(members_snap) if members_snap else "(empty)"
                        send_msg(conn, {"type": "system", "message": f"Users in {target_room}: {nick_list}", "timestamp": now_str()})
                    continue
 
                elif command == "/msg":
                    if len(parts) < 3:
                        send_msg(conn, {"type": "error", "message": "Usage: /msg <nickname> <text>", "timestamp": now_str()})
                        continue
                    target_user = parts[1]
                    pm_text = " ".join(parts[2:])
 
                    with lock:
                        target_sock = clients[target_user]["socket"] if target_user in clients else None
 
                    if target_sock is None:
                        send_msg(conn, {"type": "error", "message": f"User {target_user} not found.", "timestamp": now_str()})
                    else:
                        send_msg(target_sock, {"type": "pm", "from": nickname, "text": pm_text, "timestamp": now_str()})
                        print(f"PrivateDelivered: From:{nickname}, To:{target_user}, Date/Time:{now_str()}, Msg-Size:{len(pm_text.encode())}")
                    continue
 
                elif command == "/nick":
                    if len(parts) != 2:
                        send_msg(conn, {"type": "error", "message": "Usage: /nick <newnickname>", "timestamp": now_str()})
                        continue
                    newnick = parts[1]
                    oldnick = nickname
                    
                    name_taken = False
                    with lock:
                        if newnick not in clients:
                            clients[newnick] = clients.pop(oldnick)
                            current_room = clients[newnick]["room"]
                            rooms[current_room]["members"].discard(oldnick)
                            rooms[current_room]["members"].add(newnick)
                            room_members = list(rooms[current_room]["members"])
                        else: 
                            name_taken = True

                    if name_taken:
                        send_msg(conn, {"type": "error", "message": f"Nickname {newnick} is already in use.", "timestamp": now_str()})
                        continue
 
                    nickname = newnick
                    print(f"{now_str()} :: {oldnick}: changed nickname to {newnick}.")
 
                    # notify everyone in the room (outside lock)
                    for user in room_members:
                        with lock:
                            sock = clients[user]["socket"] if user in clients else None
                        if sock:
                            try:
                                send_msg(sock, {"type": "system", "message": f"{oldnick} is now known as {newnick}.", "timestamp": now_str()})
                            except:
                                pass
                    continue
 
                elif command == "/disconnect":
                    send_msg(conn, {"type": "system", "message": "Disconnecting...", "timestamp": now_str()})
                    break
 
                else:
                    send_msg(conn, {"type": "error", "message": f"Unknown command: {command}", "timestamp": now_str()})
                    continue
 
            # reg chat msg
            ip, port = addr
            with lock:
                sender_clientID = clients[nickname]["clientID"] if nickname in clients else clientID
                room_members = list(rooms[room]["members"])
                # append to history
                entry = {"from": nickname, "text": text, "timestamp": now_str()}
                rooms[room]["history"].append(entry)
                if len(rooms[room]["history"]) > 20:
                    rooms[room]["history"].pop(0)
                # snapshot sockets for delivery
                deliver_targets = {
                    user: clients[user]["socket"]
                    for user in room_members
                    if user != nickname and user in clients
                }
 
            out_msg = {"type": "deliver", "room": room, "from": nickname, "text": text, "timestamp": now_str()}
 
            # send to recipients outside lock
            recipients = []
            for user, sock in deliver_targets.items():
                try:
                    send_msg(sock, out_msg)
                    recipients.append(user)
                except Exception as e:
                    print("Delivery error:", e)
 
            if recipients:
                print(f"Delivered(Room={room}): {', '.join(recipients)}")
            else:
                print(f"Delivered(Room={room}): (none)")
 
    except Exception as e:
        # ignore WinError 10054 (client forcibly closed)
        if hasattr(e, "winerror") and e.winerror == 10054:
            pass
        else:
            print("Error in handle_client:", e)
    finally:
        with lock:
            if nickname and nickname in clients:
                room = clients[nickname]["room"]
                rooms[room]["members"].discard(nickname)
                # snapshot room members before deleting so i can notify them
                room_members = list(rooms[room]["members"])
                del clients[nickname]
                print(f"{now_str()} :: {nickname}: disconnected.")

        # notify remaining room members of disconnect/crash
        for user in room_members:
            with lock:
                sock = clients[user]["socket"] if user in clients else None
            if sock:
                try:
                    send_msg(sock, {
                        "type": "system",
                        "message": f"{nickname} has left the room.",
                        "timestamp": now_str()
                    })
                except:
                    pass

        conn.close()

# NETWORK PROTOCOL: FRAMED MSGS OVER TCP
# Every message sent across the network has the following structure:
# 4 bytes: unsigned integer N (big-endian)
# N bytes: message body (UTF-8 text)
# loops until it reads exactly 4 bytes for N, then loops until it reads
# exactly N bytes for the body
def recv_all(sock, n):
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            return None
        data += chunk
    return data

def recv_msg(sock):
    raw_len = recv_all(sock, 4) # gets exactly 4 bytes
    if not raw_len:
        return None
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

# accept only one command line arg: <port>
args = sys.argv
if len(args) != 2:
    print("ERR - arg 1")
    sys.exit(1)
try: 
    port = int(args[1])
    assert 0 < port < 65536  # must validate that port is a pos int less than 65536
except (ValueError, AssertionError): # if invalid, exit after printing: ERR - arg 1
    print("ERR - arg 1")
    sys.exit(1)

# Create welcoming socket using the given port
try:
    welcomeSocket = socket(AF_INET, SOCK_STREAM)
    welcomeSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    welcomeSocket.bind(('', port))
    welcomeSocket.listen(10)
    welcomeSocket.settimeout(1.0) # do 1s timeout so loop can check KeyboardInterrupt
except Exception:
    # If the server cannot bind/listen on the port (e.g., already in use)
    print(f"ERR - cannot create ChatServer socket using port number {port}")
    sys.exit(1)

# IF SERVER SUCCESSFULLY STARTS:
server_ip = gethostbyname(gethostname())
print(f"ChatServer started with server IP: {server_ip}, port: {port}, Date/Time: {now_str()}")

# While loop to handle arbitrary sequence of clients making requests
try:
    threading.Thread(target=monitor_timeouts, daemon=True).start()
    while 1:
        try:
            conn, addr = welcomeSocket.accept()
        except timeout:
            continue # loops again, checks for ctrl c
        thread = threading.Thread(target=handle_client, args=(conn, addr)).start()
except KeyboardInterrupt:
    pass
finally:
    welcomeSocket.close()
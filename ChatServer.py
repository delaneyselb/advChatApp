# accept one command line arg: <port>
# must validate that it is a pos int less than 65536
# if invalid, exit after printing: ERR - arg 1

#IF SERVER SUCCESSFULLY STARTS, PRINT:
# ChatServer started with server IP: <ip>, port: <port>, Date/Time:
# <date/time>
#ELSE
# If the server cannot bind/listen on the port (e.g., already in use), print and exit:
# ERR - cannot create ChatServer socket using port number <port>

#FUNCTIONALITY:
# • Support multiple clients connected at the same time.
# • Nickname Management: nicknames must be globally unique across all connected
# clients; reject duplicates.
# • Rooms: each connected client is always in exactly one room; new clients start in room
# “lobby”.
# • Room History: store the last 20 chat messages per room. When a client joins a room,
# send that room’s history to that client.
# • Private Messaging: support “/msg <nickname> <text>” (deliver only to the target
# nickname).
# • Heartbeat Timeout: disconnect clients that go silent for too long (see Heartbeat section).

# NETWORK PROTOCOL: FRAMED MSGS OVER TCP
# Every message sent across the network has the following structure:
# 4 bytes: unsigned integer N (big-endian)
# N bytes: message body (UTF-8 text)
# • If N is invalid (e.g., N == 0 or N > 65536), the receiver must close the connection.
# • Your receive code must loop until it reads exactly 4 bytes for N, then loop until it reads
# exactly N bytes for the body.

#MSG BODY FORMAT:
# message body is a structured text record made of named fields

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
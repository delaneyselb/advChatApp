# accept four command line args:
#  1) <hostname> or <ip> of your chat server
#  2) <port> number your server is running on
#  3) <nickname> (must be unique among currently connected clients)
#  4) <ClientID> (a unique identifier for this client session)
#  Example: ChatClient 10.0.0.1 12345 John 001
#  If the first argument is a hostname, you must resolve it to an IP address.
#  If any arguments are missing or incorrect, exit after printing: ERR - arg x (x is the
# argument number).

# upon starting, print:
#ChatClient started with server IP: <ip>, port: <port>, nickname:
#<nickname>, client ID: <ClientID>, Date/Time: <date/time>

# after connecting, client registers nickname w/ server
# client must allow the user to type while also printing messages from the server at any time
# commands begin with '/' anything else is treated as chat msg

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
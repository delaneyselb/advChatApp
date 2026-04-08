# Delaney Selb
## CMSC440 Advanced Chat Application 4/7/2026

# How to Run
## Two files: 
- **ChatServer.py**: manages all connections and chat logic
- **ChatClient.py**: allows users to type either chat text or slash commands

## Command Line Execution:
1. Begin running instance of ChatServer.py via command line
- python ChatServer.py <port number: pos int less than 65536>
2. Run ChatClient.py via command line to create one client connected to the ChatServer
- python ChatClient.py <hostname or ip of chat server> 
<port number that server is running on> <unique nickname> 
<ClientID unique identifier for this session>
3. Can repeat step 2 in different windows to create multiple clients connected to server

# Project Description
- Reliable, interactive room-based chat system using TCP sockets
- Support multiple users simultaneously
- Keep track of what room each user is in
- Deliver messages via room broadcast or private message
- Remain stable upon unexpected disconnects
- Use message framing and structured message formatting

# Implementation Plan
## ChatServer.py
1. Startup and argument validation
2. Accept one client for now, message framing
3. Registration and lobby
4. Multiple clients and rooms
5. Commands and private messages
6. Heartbeat and timeout
7. Final formatting and finishing touches

## ChatClient.py
1. Startup and argument validation
2. Connect, register, framing
3. Receive thread and display
4. Input loop and commands
5. Heartbeat and summary

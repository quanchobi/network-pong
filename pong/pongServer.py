# =================================================================================================
# Contributing Authors:	    <Anyone who touched the code>
# Email Addresses:          <Your uky.edu email addresses>
# Date:                     <The date the file was last edited>
# Purpose:                  <How this file contributes to the project>
# Misc:                     <Not Required.  Anything else you might want to include>
# =================================================================================================

import logging      # A simple logging library. Allows us to log what has occured to stdout
import pickle       # A simple serializing library. Used to serialize data sent/received to/from client
import socket       # A simple networking library. Allows us to communicate with the client.
import threading    # A simple threading library. One thread is used for each client

# Global variables
IP: str = "127.0.0.1"       # IP to connect over
PORT: int = 4567            # Port to bind
WIDTH, HEIGHT = 700, 700    # Window width and height (default pong values)

PACKET_SIZE = 4096  # Packet size for communications between client and server

# Use this file to write your server logic
# You will need to support at least two clients
# You will need to keep track of where on the screen (x,y coordinates) each paddle is, the score
# for each player and where the ball is, and relay that to each client
# I suggest you use the sync variable in pongClient.py to determine how out of sync your two
# clients are and take actions to resync the games

# Class that contains all the data that needs to be transferred between players
class Transfer_Data:
    paddle_pos: tuple[int, int]     # Holds paddle position in x and y coords.
    sync: int                       # Sync variable. Used to ensure players remain in sync.
    id: int                         # Player ID (same as thread id, starts at 0 and counts up)
    points: tuple[int, int] = 0, 0  # Game points, stored in a tuple

# Game class, contains data for one game. Since we can have an arbitrary number of games, we create a new instance of a Game for each game
class Game:
    ball_pos: tuple[int, int]       # Holds balls position
    ball_vel: tuple[int, int]       # Holds ball velocity
    players: list[int] = []         # Player IDs in the game
    ball_direction: int = -1        # Holds ball direction, 1 for right and -1 for left
    id: int                         # Games ID, starts at 0 and counts up
    transfer_data = Transfer_Data() # Data to transfer between clients
    # Initialization function
    def __init__(self, id) -> None:
        self.id = id
# TODO
def update_game(data: Transfer_Data) -> None:
    pass
# Main logic of the server. takes data from the clients and communicates game states to them
def client_thread_start(connection, game: Game, player_id: int) -> None:
    # Set the id of the data to be transferred to the players id
    game.transfer_data.id = player_id

    # Send the game's current state to the player
    connection.send(pickle.dumps(game.transfer_data))
    run: bool = True
    while run:
        try:
            received_data: Transfer_Data = pickle.loads(connection.recv(PACKET_SIZE))
        except Exception as err:
            logging.error("Connection error: %s", err)
            break
        received_data.id = player_id

    # Game is over.
    # TODO: ask the players if they would like to play again
    game.players.remove(player_id)

    # If both players have left, remove the game
    if len(game.players) == 0:
        games.remove(game)

    # Close the connection
    connection.close()

# Finds a game for a client to join.
def find_game(games: list[Game], player_id: int) -> Game:
    if len(games) == 0: # If no games exist, make game 0
        game = Game(0)
        game.players.append(player_id)
        games.append(game)
        return game
    else: # At least one game exists
        for game in games:
            if len(game.players) < 2: # If 1 or 0 players in a game
                game.players.append(player_id)
                return game
        else: # No games with 1 or 0 players, so make a new game
            game = Game(games[-1].id + 1)
            # making the game
            game.id = games[-1].id + 1
            game.players.append(player_id)
            games.append(game)
            return game

if __name__ == "__main__":
    # Set up logging to stdout
    logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.INFO, datefmt="%H:%M:%S")

    # Init socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind to socket, with error handling
    logging.info("Attempting to bind to %s:%d.", IP, PORT)
    try:
        server.bind((IP, PORT))
    except:
        logging.error(socket.error)
    logging.info("Bind successful.")

    # Listen for clients
    server.listen()
    logging.info("Waiting for connections...")

    games: list[Game] = []      # A list of all games active

    client_id: int = 0  # Current client id, starts at 0 and increments for every player that has joined

    # Accept incoming connections, and thread them
    while True:
        connection, address = server.accept()
        logging.info("Incoming connection from %s", address)
        # Make a new player

        game: Game = find_game(games, client_id)
        logging.info("Client %d connected on game %d", client_id, game)

        client_thread = threading.Thread(target=client_thread_start, args=(connection, game, client_id,))
        client_thread.start()
        client_id += 1

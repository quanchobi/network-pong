# =================================================================================================
# Contributing Authors:	    Jacob Hanks
# Email Addresses:          jacob.hanks@uky.edu
# Date:                     Nov 17 2023
# Purpose:                  Server implementation
# Misc:
# =================================================================================================

import logging      # A simple logging library. Allows us to log what has occured to stdout
import pickle       # A simple serializing library. Used to serialize data sent/received to/from client
import socket       # A simple networking library. Allows us to communicate with the client.
import threading    # A simple threading library. One thread is used for each client
from assets.code.helperCode import *

class Player:
    # Author:        Jacob Hanks
    # Purpose:       Contains all data that needs to be transferred back and forth between clients
    # Pre:           When someone joins the game, a new Player is created and they are added to that game
    # Post:          When a player disconnects, they are removed from the game
# ============================================================================
    paddle: Paddle      # Holds data about paddles position, velocity, etc.
    id: int             # Player ID, either 0 or 1 depending on side (0 for left, 1 for right)
    points: int         # Players score
    sync: int           # Sync variable. Used to ensure players remain in sync.
    pause: bool = False # Tells the player if it should pause to allow the other player to catch up
    def __init__(self, id) -> None:
        self.id = id

class Game:
    # Author:        Jacob Hanks
    # Purpose:       Contains all the data to run a game between 2 players
    # Pre:           When a game is started, a Game is created
    # Post:          When a game is ended, the Game is removed from the global game list
# ============================================================================
    id: int                     # Games ID, starts at 0 and counts up
    players: list[Player] = []  # A list of players in a game. Should be less than 2

    # Initialization function
    def __init__(self, id) -> None:
        self.id = id

# Global variables
IP: str = "127.0.0.1"       # IP to connect over
PORT: int = 4567            # Port to bind
WIDTH, HEIGHT = 700, 700    # Window width and height (default pong values)

PACKET_SIZE = 4096          # Packet size for communications between client and conn
GAMES: list[Game] = []      # A list of all games active

def find_game(game_id: int) -> Game:
    # Author:        Jacob Hanks
    # Purpose:       Finds a game from the global game list given an input game id
    # Pre:           Expects that there are valid games in the global games list, and that the game id pass in is among them
    # Post:          Returns the Game from GAMES with ID the same as the passed in game_id
    # Iterate through list of games and find the game with game id matching game_id
# ============================================================================
    for game in GAMES:
        if game_id == game.id:
            return game
    # If we end up here, something went wrong.
    else:
        logging.error("Game with ID %d not found.", game_id)
        return Game(-1)

def join_game() -> tuple[int, int]:
    # Author:        Jacob Hanks
    # Purpose:       Finds an available game to join when a player connects. If no open games exist, it creates one.
    # Pre:           Called when a player connects.
    # Post:          Returns a tuple of the player ID and the game ID that were found for the player to join
# ============================================================================
    if len(GAMES) == 0: # If no GAMES exist, make game 0
        # Initialize game
        game_id: int = 0
        game = Game(game_id)

        # Initialize player
        player_id: int = 0
        player = Player(player_id)

        # Put player in the game and append the game to the list of active GAMES
        game.players.append(player)
        GAMES.append(game)
        return player_id, game.id
    else: # At least one game exists
        for game in GAMES:
            if len(game.players) < 2: # If 1 or 0 players in a game
                if game.players[0].id == 0:
                    player_id = 1
                elif game.players[0].id == 1:
                    player_id = 0
                else:   # Shouldn't happen
                    player_id = -1
                player = Player(player_id)
                game.players.append(player)
                return player_id, game.id
        else: # No games with 1 or 0 players, so make a new game
            # Make a new game, with an ID that hasn't been taken
            game = Game(GAMES[-1].id + 1)

            # Add the player to the game
            player_id: int = 0
            player = Player(player_id)
            game.players.append(player)

            # Add the game to the game list
            GAMES.append(game)
            return player_id, game.id

def remove_player(game_id: int, player_id: int) -> None:
    # Author:        Jacob Hanks
    # Purpose:       Removes a player from the game once they have disconnected
    # Pre:           A player has disconnected
    # Post:          That player is removed from the game
# ============================================================================
    game = find_game(game_id)
    player_index = find_player(game.players, player_id)
    game.players.remove(game.players[player_index])

def find_player(players: list[Player], player_id: int) -> int:
    # Author:        Jacob Hanks
    # Purpose:       Finds a player in a game with a given player ID
    # Pre:           Assumes the list of players passed in and the player ID are valid
    # Post:          Returns the index of the player in the players list of the game
# ============================================================================
    for index, player in enumerate(players):
        if player_id == player.id:
            return index # Index of player found
    else:
        # Player not found. Should never occur, unless a player leaves the game.
        logging.error("Player with id %d not found.", player_id)
        return -1

def client_thread_start(conn: socket.socket, game_id: int, player_id: int) -> None:
    # Author:        Jacob Hanks
    # Purpose:       Thread entry point. Runs the find_game method to find a game for the client to join,
    #                   waits on a 2nd client to join the game, then sends Initializing data to each client.
    #                   then, it transfers data back and forth between clients such that they know where to position
    #                   elements, score, etc.
    # Pre:           Takes a socket, game ID, and player ID as input. It expects the socket to have a valid connection
    # Post:             After this method is finished, the client will disconnect and the player associated with it will be removed from the list.
# ============================================================================
    # Find the game associated with the passed in ID
    game: Game = find_game(game_id)

    # Find the player associated with the passed in ID
    player_index: int = find_player(game.players, player_id)
    logging.info("Player %d's index is %d in game %d", player_id, player_index, game_id)

    # Send height/width and side to client
    logging.info("Client %d on side %d", player_id, player_index)

    # Don't start game until there are 2 players
    while len(game.players) < 2:
        continue

    # Send players width/height data and player index
    conn.sendall(pickle.dumps((WIDTH, HEIGHT, player_index)))

    # Send client initialized player data
    conn.sendall(pickle.dumps(game.players[player_index]))
    logging.info("Sent initial info to player %d in game %d", player_id, game_id)

    # Main logic loop
    while True:
        try: # Get data from client
            received_data: Player = pickle.loads(conn.recv(PACKET_SIZE))
        except Exception as e: # Some exception occured when receiving data
            logging.error("Did not receive data from client: %s", e)
            break
        if not received_data: # If data was not received
            logging.warn("Lost connection to client %d in game %d", player_id, game_id )
            break

        # Update players data with what it has received
        game.players[player_index] = received_data

        # Send client other player's data.
        # if player_index is 1, player_index - 1 will be 0, being the opposite player
        # if player_index is 0, player_index -1 will be -1, which will also be the opposite player, since there are only 2 players.
        conn.sendall(pickle.dumps(game.players[player_index - 1]))

        # Check and see if clients are synced, pause one until theyre synced again
        if game.players[player_index].sync <= game.players[player_index - 1].sync:
            game.players[player_index].pause = False
        else:
            game.players[player_index].pause = True
    # Remove the player from the game
    game.players.remove(game.players[player_index])

    # If there are no players left in the game, remove it from the list
    if len(game.players) == 0:
        GAMES.remove(game)
    # Otherwise reinit the game with default values
    else:
        game.__init__(game_id)
    # Close the connection with the client
    conn.close()


if __name__ == "__main__":
    # Author:        Jacob Hanks
    # Purpose:       Main function. Entry point for the server
    # Pre:           n/a
    # Post:          This function binds to a socket with host IP and port PORT, then it listens on that IP and port
    #                   for a client to attempt to connect. When a client connects, it spawns a new thread for it.
    #                   The new thread has target client_thread_start, which starts the game and data transfer process.
    #                   After it spawns the thread, the main thread should be open for another connection.
# ============================================================================
    # Set up logging to stdout
    logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.INFO, datefmt="%H:%M:%S")

    # Init socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind to socket, with error handling
    logging.info("Attempting to bind to %s:%d.", IP, PORT)
    try:
        server.bind((IP, PORT))
    except:
        logging.error("Socket error: %s", socket.error)
        exit(-1)
    logging.info("Bind successful.")

    logging.info("Waiting for connections...")


    # Initial number of threads, increments for every player that joins
    thread_number = 0

    # Listen for clients
    server.listen(6)
    while True:

        # Accept incoming connections, and thread them
        conn, address = server.accept()
        logging.info("Incoming connection from %s", address)

        # Make a new player, and have them join a game
        player_id, game_id= join_game()

        logging.info("Client %d connected on game %d", thread_number, game_id)

        client_thread = threading.Thread(target=client_thread_start, args=(conn, game_id, player_id))
        client_thread.start()
        thread_number += 1

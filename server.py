from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cosc439_secret!'
# Added log_output=False to reduce the error spam in your terminal
socketio = SocketIO(app, cors_allowed_origins="*", logger=False, engineio_logger=False)

game_state = {
    "board": [""] * 9,
    "turn": "X",
    "players": {}, 
    "winner": None,
    "rematch_requests": set()  # New: Tracks which players want a rematch
}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    sid = request.sid
    if sid not in game_state["players"]:
        if len(game_state["players"]) == 0:
            game_state["players"][sid] = "X"
            emit('assign_player', "X")
        elif len(game_state["players"]) == 1:
            game_state["players"][sid] = "O"
            emit('assign_player', "O")
        else:
            emit('error', 'Game Full')
    
    emit('update_board', {
        "board": game_state["board"], 
        "turn": game_state["turn"],
        "winner": game_state["winner"]
    })

@socketio.on('make_move')
def handle_move(data):
    idx = data['index']
    player = game_state["players"].get(request.sid)

    if player == game_state["turn"] and game_state["board"][idx] == "" and not game_state["winner"]:
        game_state["board"][idx] = player
        
        wins = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
        for a, b, c in wins:
            if game_state["board"][a] == game_state["board"][b] == game_state["board"][c] != "":
                game_state["winner"] = player
        
        if "" not in game_state["board"] and not game_state["winner"]:
            game_state["winner"] = "Tie"

        game_state["turn"] = "O" if player == "X" else "X"
        
        socketio.emit('update_board', {
            "board": game_state["board"], 
            "turn": game_state["turn"],
            "winner": game_state["winner"]
        })

@socketio.on('request_rematch')
def handle_rematch():
    sid = request.sid
    player = game_state["players"].get(sid)
    
    # Only process if the game is actually over
    if player and game_state["winner"]:
        game_state["rematch_requests"].add(player)
        
        # Check if both players have clicked the button
        if len(game_state["rematch_requests"]) == 2:
            
            # --- NEW LOGIC: Loser goes first ---
            if game_state["winner"] == "X":
                next_starter = "O"
            elif game_state["winner"] == "O":
                next_starter = "X"
            else:
                # If the game was a Tie, default back to X 
                next_starter = "X" 
            
            # Reset the game state
            game_state["board"] = [""] * 9
            game_state["winner"] = None
            game_state["turn"] = next_starter
            game_state["rematch_requests"].clear()
            
            # Broadcast the fresh board and new turn to both players
            socketio.emit('update_board', {
                "board": game_state["board"], 
                "turn": game_state["turn"],
                "winner": game_state["winner"]
            })
        else:
            # Tell the clients that one person is waiting
            socketio.emit('rematch_waiting', {"player": player})

if __name__ == '__main__':
    # Running on your specific IP
    socketio.run(app, host='0.0.0.0', port=65432)
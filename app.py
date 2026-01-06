import os
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import string
import json
import socket
from story_data import (
    call_gemini_for_outcome_narrative,
    generate_dilemma_with_gemini,
    EVENT_GENERATION_PROMPT_STATIC,
    OUTCOME_NARRATIVE_PROMPT_STATIC,
    evaluate_player_statements_with_gemini,
)
import io

import torch
import torch.serialization
from TTS.api import TTS
import numpy as np
import wave

# Import the classes we need to allowlist
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import XttsAudioConfig, XttsArgs
from TTS.config.shared_configs import BaseDatasetConfig

# --- Allowlist fix for safe deserialization ---
torch.serialization.add_safe_globals(
    [XttsConfig, XttsAudioConfig, BaseDatasetConfig, XttsArgs]
)
# ----------------------------------------------

# Securely get the API key from the environment
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set!")

model = genai.GenerativeModel("gemini-2.5-flash")

# --- Coqui XTTS v2 Setup ---
# Determine the device to use
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[TTS] Using device: {device}")

# Load the TTS model
# This will download the model on the first run, which may take a while.
print("[TTS] Loading Coqui XTTS v2 model...")
try:
    model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
    config_path = os.path.join(
        "tts_models",
        "tts_models--multilingual--multi-dataset--xtts_v2",
        "config.json",
    )
    model_path = os.path.join(
        "tts_models",
        "tts_models--multilingual--multi-dataset--xtts_v2"
    )

    if not os.path.exists(config_path):
        print(f"[TTS] Model config not found at {config_path}")
        print("[TTS] Please ensure the model is downloaded and accessible.")
        tts_model = None
    else:
        tts_model = TTS(model_path=model_path, config_path=config_path).to(device)
        print("[TTS] Coqui XTTS v2 model loaded successfully.")
except Exception as e:
    print(f"[TTS] Error loading Coqui XTTS model: {e}")
    tts_model = None

# Ensure the 'tts' directory exists for speaker WAVs
if not os.path.exists("tts"):
    os.makedirs("tts")
    print("Created 'tts' directory for speaker WAVs.")
# --- End of Coqui XTTS Setup ---


app = Flask(__name__, static_folder="static", template_folder="templates")
# It is critical to set a secret key for session management and security.
# We will try to load it from an environment variable.
# If it's not set, we'll generate a temporary one and issue a warning.
# For production, you MUST set a persistent, unpredictable FLASK_SECRET_KEY.
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY")
if not app.config["SECRET_KEY"]:
    print("WARNING: The FLASK_SECRET_KEY environment variable is not set.")
    print("Using a temporary, insecure key for this session.")
    print(
        "For production use, you MUST set this environment variable to a persistent, random value."
    )
    app.config["SECRET_KEY"] = "".join(
        random.choices(string.ascii_letters + string.digits, k=32)
    )


# It is critical to set a secret key for session management and security.
# We will try to load it from an environment variable.
# If it's not set, we'll generate a temporary one and issue a warning.
# For production, you MUST set this environment variable to a persistent, random value.


socketio = SocketIO(app, ping_interval=25, ping_timeout=60)

games = {}

GAMES_FILE = "games_data.json"

def save_games():
    try:
        # Create a copy of games to avoid modifying the original while iterating or if we need to filter
        # For now, we assume everything in 'games' is serializable.
        with open(GAMES_FILE, "w") as f:
            json.dump(games, f, indent=4)
        print(f"[PERSISTENCE] Games saved to {GAMES_FILE}")
    except Exception as e:
        print(f"[PERSISTENCE] Error saving games: {e}")

def load_games():
    global games
    if os.path.exists(GAMES_FILE):
        try:
            with open(GAMES_FILE, "r") as f:
                games = json.load(f)
            print(f"[PERSISTENCE] Loaded {len(games)} games from {GAMES_FILE}")
        except Exception as e:
            print(f"[PERSISTENCE] Error loading games: {e}")
            games = {}
    else:
        print("[PERSISTENCE] No existing games file found. Starting with empty games.")
        games = {}

load_games()


def generate_game_id():
    return "".join(random.choices(string.ascii_uppercase, k=4))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/join/<game_id>")
def join_game_page(game_id):
    game = games.get(game_id)
    if not game:
        return "Game not found", 404
    return render_template("join_game.html", game_id=game_id, factions=game["factions"])

@app.route("/player/<game_id>/<player_id>")
def player_controller(game_id, player_id):
    game = games.get(game_id)
    if game and player_id in game["players"]:
        return render_template(
            "player.html",
            game_id=game_id,
            player_id=player_id,
            global_stats=game["global_stats"],
            current_round=game["current_round"],
        )
    return "Game or Player not found", 404


@app.route("/api/tts", methods=["POST"])
def tts():
    if not tts_model:
        print("[TTS] Error: Coqui TTS model not loaded.")
        return jsonify({"error": "TTS service not configured"}), 500

    text = request.json.get("text")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    speaker_wav_path = "tts/Rafal_Walentowicz.wav"
    if not os.path.exists(speaker_wav_path):
        print(f"[TTS] Error: Speaker WAV file not found at {speaker_wav_path}")
        return jsonify({"error": f"Speaker voice file not found. Please place it at {speaker_wav_path}"}), 500

    print(f"[TTS] Received text for Coqui XTTS: {text}")
    
    temp_audio_file = None
    try:
        import tempfile # Ensure tempfile is imported
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
            temp_audio_file = tmpfile.name

        print(f"[TTS] Synthesizing '{text}' using '{speaker_wav_path}' to temporary file {temp_audio_file}...")
        tts_model.tts_to_file(
            text=text,
            speaker_wav=speaker_wav_path,
            language="pl",
            file_path=temp_audio_file,
        )
        print(f"[TTS] Audio synthesized successfully to {temp_audio_file}.")

        return send_file(
            temp_audio_file,
            mimetype='audio/wav',
            as_attachment=False,
            download_name='speech.wav',
            max_age=0
        )
    except Exception as e:
        print(f"[TTS] Error during Coqui XTTS audio generation: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": "TTS synthesis failed"}), 500
    finally:
        if temp_audio_file and os.path.exists(temp_audio_file):
            os.remove(temp_audio_file)


@app.route("/dilemma")
def dilemma():
    # This is a debug route to test the Gemini API call
    game_state_for_gemini = {
        "current_round": 1,
        "global_stats": {"Stability": 50, "Economy": 50, "Faith": 50},
        "event_history": [],
        "player_statements": [],
        "previous_dilemma_outcome": None,
    }
    if generate_dilemma_with_gemini(model, game_state_for_gemini):
        with open("dilemma.json", "r") as f:
            generated_dilemma = json.load(f)
    else:
        generated_dilemma = {"error": "Failed to generate dilemma"}
    return jsonify(generated_dilemma)


@socketio.on("create_game")
def create_game(data):
    game_id = generate_game_id()
    while game_id in games:
        game_id = generate_game_id()

    num_players = data.get("num_players", 1)

    players = {}
    factions = {
        "Syndykat Kupiecki": {
            "power": "Mistrzostwo Handlu",
            "players": [],
            "objectives": [
                {"id": "econ_75", "type": "stat_target", "stat": "Economy", "target": 75, "completed": False, "description": "Zwiększ gospodarkę królestwa do 75 punktów (Złoty Wiek)."},
                {"id": "unanimous_vote_1", "type": "unanimous_vote", "count": 1, "completed": False, "description": "Wszyscy członkowie twojej frakcji głosują tak samo w 1 dylemacie (Jedność Gildii)."},
                {"id": "pass_econ_policies_3", "type": "policies_passed", "stat": "Economy", "count": 3, "completed": False, "description": "Pomyślnie przeprowadź 3 polityki, które pozytywnie wpływają na Gospodarkę (Mistrzowie Negocjacji)."},
                {"id": "econ_sabotage_stab", "type": "stat_lower", "stat": "Stability", "amount": 15, "completed": False, "description": "Wpłyń na radę, aby obniżyć Stabilność królestwa o 15 punktów w jednej rundzie (Sabotaż Gospodarczy)."},
                {"id": "winning_statement_2", "type": "winning_statement", "count": 2, "completed": False, "description": "Oświadczenie członka frakcji zostanie wybrane jako zwycięskie w 2 dylematach (Wpływowy Głos)."}
            ]
        },
        "Wysokie Kapłaństwo": {
            "power": "Boska Łaska",
            "players": [],
            "objectives": [
                {"id": "faith_75", "type": "stat_target", "stat": "Faith", "target": 75, "completed": False, "description": "Zwiększ wiarę królestwa do 75 punktów (Era Wiary)."},
                {"id": "unanimous_vote_1", "type": "unanimous_vote", "count": 1, "completed": False, "description": "Wszyscy członkowie twojej frakcji głosują tak samo w 1 dylemacie (Jedność Wiary)."},
                {"id": "pass_faith_policies_3", "type": "policies_passed", "stat": "Faith", "count": 3, "completed": False, "description": "Pomyślnie przeprowadź 3 polityki, które pozytywnie wpływają na Wiarę (Głos Bogów)."},
                {"id": "faith_purge_econ", "type": "stat_lower", "stat": "Economy", "amount": 15, "completed": False, "description": "Wpłyń na radę, aby obniżyć Gospodarkę królestwa o 15 punktów w jednej rundzie (Czystka Niewiernych)."},
                {"id": "winning_statement_2", "type": "winning_statement", "count": 2, "completed": False, "description": "Oświadczenie członka frakcji zostanie wybrane jako zwycięskie w 2 dylematach (Proroczy Głos)."}
            ]
        },
        "Gwardia Królewska": {
            "power": "Utrzymanie Porządku",
            "players": [],
            "objectives": [
                {"id": "stab_75", "type": "stat_target", "stat": "Stability", "target": 75, "completed": False, "description": "Zwiększ stabilność królestwa do 75 punktów (Królestwo w Pokoju)."},
                {"id": "unanimous_vote_1", "type": "unanimous_vote", "count": 1, "completed": False, "description": "Wszyscy członkowie twojej frakcji głosują tak samo w 1 dylemacie (Żelazna Dyscyplina)."},
                {"id": "pass_stab_policies_3", "type": "policies_passed", "stat": "Stability", "count": 3, "completed": False, "description": "Pomyślnie przeprowadź 3 polityki, które pozytywnie wpływają na Stabilność (Prawo i Porządek)."},
                {"id": "show_of_force_faith", "type": "stat_lower", "stat": "Faith", "amount": 15, "completed": False, "description": "Wpłyń na radę, aby obniżyć Wiarę królestwa o 15 punktów w jednej rundzie (Pokaz Siły)."},
                {"id": "winning_statement_2", "type": "winning_statement", "count": 2, "completed": False, "description": "Oświadczenie członka frakcji zostanie wybrane jako zwycięskie w 2 dylematach (Głos Autorytetu)."}
            ]
        },
    }
    
    # Pre-populate player slots with default data
    for i in range(num_players):
        player_id = f"player_{i+1}" # Use a simple sequential ID for initial slots
        players[player_id] = {
            "id": player_id,
            "sid": None,
            "name": f"Player {i + 1} (Empty)", # Indicate slot is empty
            "avatar": f"/static/avatars/avatar{i + 1}.png",
            "faction": None,
            "choice": None,
            "statements": [],
            "personal_stats": {"Influence": 50, "Spite": 0},
            "ready": False,
            "shamed": False,
            "action_status": "empty", # New status for empty slots
            "current_action": None,
            "action_target": None,
        }

    # Generate a single join URL
    join_url = f"/join/{game_id}"

    game = {
        "host_sid": request.sid,
        "players": players,
        "factions": factions,
        "state": "waiting",
        "dilemma_active": False,
        "current_dilemma": None,
        "global_stats": {
            "Stability": random.randint(35, 55),
            "Economy": random.randint(35, 55),
            "Faith": random.randint(35, 55),
        },
        "current_round": 0,
        "event_history": [],
        "gemini_output": {},
        "next_round_votes": [],
        "policies_passed_counts": {faction_id: {stat: 0 for stat in ["Stability", "Economy", "Faith"]} for faction_id in factions},
        "winning_statement_counts": {faction_id: 0 for faction_id in factions},
        "unanimous_vote_counts": {faction_id: 0 for faction_id in factions},
        "join_url": join_url, # Store join URL in game state
    }
    games[game_id] = game
    join_room(game_id)
    emit(
        "game_created",
        {
            "game_id": game_id,
            "join_url": join_url, # Emit single join URL
            "players": players,
            "factions": factions,
        },
        room=request.sid,
    )
    save_games()


@socketio.on("join_game")
def join_game(data):
    try:
        game_id = data["game_id"]
        player_id = data.get("player_id") # This will be None for initial join via QR
        player_name = data.get("player_name") # New: for initial join via QR
        faction_id = data.get("faction_id") # New: for initial join via QR
        game = games.get(game_id)

        print(f"[DEBUG] join_game received: {data}")

        if not game:
            emit("error", {"message": "Game not found."}, room=request.sid)
            return

        join_room(game_id)

        if player_id: # Player is reconnecting with an existing player_id
            print(f"[DEBUG] Player {player_id} is reconnecting.")
            if player_id in game["players"]:
                game["players"][player_id]["sid"] = request.sid
                game["players"][player_id]["action_status"] = "joined" # Ensure status is correct on reconnect

                player_faction_id = game["players"][player_id]["faction"]
                if player_faction_id:
                    for pid in game["factions"][player_faction_id]["players"]:
                        if pid != player_id and game["players"][pid]["sid"]:
                            emit(
                                "other_player_reconnected",
                                {"player": game["players"][player_id], "player_id": player_id},
                                room=game["players"][pid]["sid"],
                            )

                emit("player_joined", game["players"], room=game["host_sid"])

                # Send full game state to the reconnected player
                player_game_state = {
                    "global_stats": game["global_stats"],
                    "current_round": game["current_round"],
                    "players": game["players"],
                    "factions": game["factions"],
                    "state": game["state"],
                    "current_dilemma": game["current_dilemma"] if game["dilemma_active"] else None,
                    "last_outcome_narrative_data": game.get("last_outcome_narrative_data"),
                }
                emit("game_state_sync", player_game_state, room=request.sid)
                print(f"[DEBUG] Sent game_state_sync to reconnected player {player_id}")

            else:
                emit("error", {"message": "Invalid player ID for reconnection."}, room=request.sid)
                return

        elif player_name: # New player joining via QR code, ignore faction_id
            print(f"[DEBUG] New player '{player_name}' is joining.")
            assigned_player_id = None
            for pid, player_data in game["players"].items():
                if player_data["action_status"] == "empty":
                    assigned_player_id = pid
                    break
            
            if assigned_player_id:
                # Find the faction with the fewest players
                min_players = float('inf')
                least_populated_factions = []
                for f_id, f_data in game["factions"].items():
                    num_players_in_faction = len(f_data["players"])
                    if num_players_in_faction < min_players:
                        min_players = num_players_in_faction
                        least_populated_factions = [f_id]
                    elif num_players_in_faction == min_players:
                        least_populated_factions.append(f_id)
                
                # Randomly choose from the least populated factions
                chosen_faction = random.choice(least_populated_factions)

                print(f"[DEBUG] Assigning new player to slot: {assigned_player_id} in faction {chosen_faction}")
                game["players"][assigned_player_id]["sid"] = request.sid
                game["players"][assigned_player_id]["name"] = player_name
                game["players"][assigned_player_id]["faction"] = chosen_faction
                game["players"][assigned_player_id]["action_status"] = "joined"
                
                game["factions"][chosen_faction]["players"].append(assigned_player_id)

                emit("player_assigned", {"player_id": assigned_player_id}, room=request.sid)
                print(f"[DEBUG] Emitted 'player_assigned' to {assigned_player_id}")
                emit("game_update", {"players": game["players"], "factions": game["factions"]}, room=game_id, broadcast=True)
                print(f"[DEBUG] Emitted 'game_update' to game {game_id}")
            else:
                emit("error", {"message": "No available player slots."}, room=request.sid)
                return

        elif not player_id and not player_name: # Host is joining/reconnecting
            print("[DEBUG] Host is reconnecting.")
            game["host_sid"] = request.sid
        else:
            emit("error", {"message": "Invalid join request."}, room=request.sid)
            return
            
        save_games()
    except Exception as e:
        print(f"[ERROR] Exception in join_game handler: {e}")
        import traceback
        traceback.print_exc()


def start_game_logic(game_id):
    try:
        print(f"[DEBUG] Starting game {game_id}")
        game = games.get(game_id)
        if not game or game["state"] != "waiting":
            print(f"[ERROR] start_game_logic called with invalid game state: {game.get('state') if game else 'No game'}")
            return

        game["state"] = "DILEMMA"

        # Start the first round
        game["current_round"] = 1
        game["dilemma_active"] = True
        for player_id, player in game["players"].items():
            player["choice"] = None
            player.pop("statement", None)
            player.pop("statement_vote", None)
            player["current_action"] = None
            player["action_target"] = None
            player["action_status"] = "waiting"  # Reset action status
            print(f"[DEBUG] Reset player {player_id} for new round.")

        game_state_for_gemini = {
            "current_round": game["current_round"],
            "global_stats": game["global_stats"],
            "event_history": game["event_history"],
            "player_statements": [],
            "previous_dilemma_outcome": None,
        }
        if generate_dilemma_with_gemini(model, game_state_for_gemini):
            print("[DEBUG] Gemini event generation successful.")
            with open("dilemma.json", "r", encoding="utf-8") as f:
                generated_dilemma = json.load(f)
        else:
            print("[DEBUG] Gemini event generation failed, using fallback dilemma.")
            generated_dilemma = {
                "id": "error_dilemma",
                "title": "Chwila ciszy",
                "description": "Wiatry losu milczą. Rada nie jest w stanie się zebrać w tym czasie. Proszę spróbować później.",
                "narrative_prompt": "Królestwo wstrzymuje oddech.",
            }

        game["current_dilemma"] = generated_dilemma
        game["gemini_output"] = generated_dilemma

        print("[DEBUG] Emitting game_started_for_player")
        emit("game_started_for_player", game, room=game_id, broadcast=True)
        print("[DEBUG] Emitting game_started_for_host")
        emit("game_started_for_host", game, room=game["host_sid"])
        print("[DEBUG] Emitting game_event for dilemma_prompt")
        emit(
            "game_event",
            {
                "event": "dilemma_prompt",
                "dilemma_json": json.dumps(game["gemini_output"]),
                "global_stats": game["global_stats"],
                "current_round": game["current_round"],
                "players": game["players"],
            },
            room=game_id,
            broadcast=True,
        )
        save_games()
        print("[DEBUG] start_game_logic completed successfully.")
    except Exception as e:
        print(f"[ERROR] Exception in start_game_logic: {e}")
        import traceback
        traceback.print_exc()


@socketio.on("player_ready")
def player_ready(data):
    try:
        game_id = data["game_id"]
        player_id = data["player_id"]
        game = games.get(game_id)

        if not game or player_id not in game["players"]:
            print(f"[ERROR] player_ready: Invalid game or player ID. Game: {game_id}, Player: {player_id}")
            return

        print(f"[DEBUG] Player {player_id} in game {game_id} is now ready.")
        game["players"][player_id]["ready"] = True
        
        player_statuses = {pid: p['ready'] for pid, p in game['players'].items()}
        print(f"[DEBUG] Player ready statuses: {player_statuses}")

        # Notify host about the player's ready status
        emit(
            "player_ready_update",
            {"player": game["players"][player_id], "player_id": player_id},
            room=game["host_sid"],
        )

        # Check if all *joined* players are ready
        joined_players = [p for p in game["players"].values() if p["action_status"] != "empty"]
        all_joined_ready = all(p["ready"] for p in joined_players)
        
        print(f"[DEBUG] Checking if all joined players are ready: {all_joined_ready}")
        print(f"[DEBUG] Number of joined players: {len(joined_players)}")
        print(f"[DEBUG] Total number of player slots: {len(game['players'])}")

        # The game should only start if all slots are filled and all players are ready
        if len(joined_players) == len(game['players']) and all_joined_ready:
            print("[DEBUG] All player slots are filled and all players are ready. Starting game logic...")
            start_game_logic(game_id)
        else:
            print("[DEBUG] Not all players are ready or not all slots are filled.")
        
        save_games()
    except Exception as e:
        print(f"[ERROR] Exception in player_ready handler: {e}")
        import traceback
        traceback.print_exc()


@socketio.on("game_event")
def handle_game_event(data):
    print(f"Server received game_event: {data} from SID: {request.sid}")
    game_id = data.get("game_id")
    game = games.get(game_id)
    if not game:
        return

    event_type = data.get("event")
    dilemma_data = data.get("dilemma")


def resolve_dilemma(game_id, player_comments=None):
    game = games.get(game_id)
    if not game:
        return

    # Use the winning statement if it exists, otherwise use all statements
    if "winning_statement" in game:
        # winning_statement already has action_card if set in submit_vote
        player_statements_for_gemini = [game["winning_statement"]]
    else:
        player_statements_for_gemini = []
        for player_id, player_data in game["players"].items():
            if "statement" in player_data:
                player_statements_for_gemini.append(
                    {
                        "player_id": player_id, 
                        "statement": player_data["statement"], 
                        "name": player_data["name"],
                        "action_card": player_data.get("current_action")
                    }
                )

    # Call Gemini to evaluate player statements and determine policy/effects
    evaluation_result = evaluate_player_statements_with_gemini(
        model,
        game_state={
            "current_round": game["current_round"],
            "global_stats": game["global_stats"],
            "event_history": game["event_history"],
        },
        player_statements=player_statements_for_gemini,
    )

    chosen_policy = "No policy adopted due to council inaction."
    policy_effects = {}
    narrative_consequence = "The council's indecision led to stagnation."

    # Store initial global stats for comparison with stat_lower objectives
    initial_global_stats = game["global_stats"].copy()

    if evaluation_result:
        chosen_policy = evaluation_result.get("chosen_policy", chosen_policy)
        policy_effects = evaluation_result.get("effects", policy_effects)
        narrative_consequence = evaluation_result.get("narrative_consequence", narrative_consequence)

        for stat, change in policy_effects.items():
            game["global_stats"][stat] += change
            game["global_stats"][stat] = max(0, min(100, game["global_stats"][stat]))

            # Update policies_passed objectives
            if change > 0: # Only count policies that positively affect a stat
                for faction_id in game["factions"]:
                    for objective in game["factions"][faction_id]["objectives"]:
                        if objective["type"] == "policies_passed" and objective["stat"] == stat:
                            game["policies_passed_counts"][faction_id][stat] += 1
                            print(f"[DEBUG] Faction {faction_id} policies_passed for {stat}: {game['policies_passed_counts'][faction_id][stat]}")

    # Check for objective completion
    winning_faction = None
    for faction_id, faction_data in game["factions"].items():
        all_objectives_completed = True
        for objective in faction_data["objectives"]:
            if not objective["completed"]:
                if objective["type"] == "stat_target":
                    if game["global_stats"][objective["stat"]] >= objective["target"]:
                        objective["completed"] = True
                        print(f"[DEBUG] Faction {faction_id} completed objective: {objective['description']}")
                elif objective["type"] == "unanimous_vote":
                    if game["unanimous_vote_counts"][faction_id] >= objective["count"]:
                        objective["completed"] = True
                        print(f"[DEBUG] Faction {faction_id} completed objective: {objective['description']}")
                elif objective["type"] == "policies_passed":
                    if game["policies_passed_counts"][faction_id][objective["stat"]] >= objective["count"]:
                        objective["completed"] = True
                        print(f"[DEBUG] Faction {faction_id} completed objective: {objective['description']}")
                elif objective["type"] == "stat_lower":
                    if initial_global_stats[objective["stat"]] - game["global_stats"][objective["stat"]] >= objective["amount"]:
                        objective["completed"] = True
                        print(f"[DEBUG] Faction {faction_id} completed objective: {objective['description']}")
                elif objective["type"] == "winning_statement":
                    if game["winning_statement_counts"][faction_id] >= objective["count"]:
                        objective["completed"] = True
                        print(f"[DEBUG] Faction {faction_id} completed objective: {objective['description']}")
                
                if not objective["completed"]:
                    all_objectives_completed = False
                    break
        
        if all_objectives_completed:
            winning_faction = faction_id
            break

    if winning_faction:
        game["state"] = "GAME_OVER"
        save_games()
        emit(
            "game_over",
            {"winner": {"name": winning_faction}, "reason": f"The {winning_faction} has achieved its objectives!"},
            room=game_id,
            broadcast=True,
        )
        return

    # Check for kingdom collapse (The Shaming Logic)
    collapsed_stats = [stat for stat, val in game["global_stats"].items() if val <= 0]
    
    if collapsed_stats:
        print(f"[GAME] Kingdom Stability Collapse detected! Stats: {collapsed_stats}")
        
        # 1. Global Penalty: All players lose 50% Influence
        for pid, p in game["players"].items():
            p["personal_stats"]["Influence"] = int(p["personal_stats"]["Influence"] * 0.5)
            
        # 2. The Guilty: Identify players who voted for the option that caused the crash.
        # However, in this system, players vote on *policy* (via dilemmas).
        # But wait, `resolve_dilemma` calculates the policy based on *statements*.
        # Players didn't vote on the policy directly in this version?
        # Let's re-read the flow. 
        # 1. Players submit statements (Declaration).
        # 2. Players vote on statements.
        # 3. Winning statement is used to generate the policy.
        # So the "Guilty" party is effectively the person who made the winning statement 
        # AND anyone who voted for them?
        # The prompt says: "Identify players who voted for the option that caused the crash."
        # In the current code (Gemini generation), the "policy" is derived from the winning statement.
        # So the "option" is the winning statement.
        # Thus, the Guilty are: The Winning Player + Anyone who voted for the Winning Player.
        
        guilty_players = []
        winning_stmt_player = game.get("winning_statement", {}).get("player_id")
        
        if winning_stmt_player:
             guilty_players.append(winning_stmt_player)
             for pid, p in game["players"].items():
                 if p.get("statement_vote") == winning_stmt_player:
                     guilty_players.append(pid)
        
        guilty_players = list(set(guilty_players)) # Deduplicate
        
        for pid in guilty_players:
            if pid in game["players"]:
                 game["players"][pid]["personal_stats"]["Influence"] = 0
                 game["players"][pid]["shamed"] = True # Mark as shamed for UI
                 print(f"[GAME] {pid} is GUILTY! Influence reset to 0.")

        # 3. Reset the stat to 1
        for stat in collapsed_stats:
            game["global_stats"][stat] = 1

        emit(
            "kingdom_collapse", 
            {"collapsed_stats": collapsed_stats, "guilty_players": guilty_players},
            room=game_id, 
            broadcast=True
        )

    # Player influence logic (simplified for now, can be expanded later)
    # For now, players who submitted statements gain a small amount of influence
    # (Removed this because scoring is now handled in voting resolution)
    # for player_id, player_data in game["players"].items():
    #     if "statement" in player_data:
    #         player_data["personal_stats"]["Influence"] = min(
    #             100, player_data["personal_stats"]["Influence"] + 2
    #         )
    #     player_data["personal_stats"]["Influence"] = max(
    #         0, min(100, player_data["personal_stats"]["Influence"])
    #     )

    # Generate outcome narrative using the determined policy and effects
    if call_gemini_for_outcome_narrative(
        model,
        game_state={
            "current_round": game["current_round"],
            "global_stats": game["global_stats"],
            "event_history": game["event_history"],
        },
        chosen_policy=chosen_policy,
        policy_effects=policy_effects,
        faction_votes={}, # No faction votes in this new system
        player_statements=player_statements_for_gemini,
        player_comments=player_comments,
    ):
        with open("outcome.json", "r", encoding="utf-8") as f:
            outcome_narrative_data = json.load(f)
    else:
        outcome_narrative_data = {
            "outcome_narrative": "Pisarze nie są w stanie zapisać wydarzeń tej rady. Wynik został utracony dla czasu.",
            "next_event_hint": "Przyszłość jest niepewna.",
            "kingdom_status_summary": "Królestwo jest w stanie ciągłych zmian.",
        }

    game["event_history"].append(
        {
            "round": game["current_round"],
            "policy_chosen": chosen_policy,
            "effects": policy_effects,
            "faction_votes": {}, # No faction votes in this new system
            "outcome_narrative": outcome_narrative_data["outcome_narrative"],
            "global_stats_after": game["global_stats"].copy(),
        }
    )

    game["last_outcome_narrative_data"] = outcome_narrative_data  # Store for later use

    # Check for win condition by influence
    winner = None
    for pid, p in game["players"].items():
        if p["personal_stats"]["Influence"] >= 100:
            winner = p
            break

    if winner:
        game["state"] = "GAME_OVER"
        save_games()
        emit("game_over", {"winner": winner}, room=game_id, broadcast=True)
        return

    game["dilemma_active"] = False
    game["current_dilemma"] = None
    save_games()


@socketio.on("player_action")
def handle_player_action(data):
    print(f"Server received player_action: {data} from SID: {request.sid}")
    game_id = data.get("game_id")
    player_id = data.get("player_id")
    action = data.get("action")
    game = games.get(game_id)

    if not game or player_id not in game["players"]:
        return

    elif action == "submit_statement":
        if game["state"] != "DILEMMA":
            return
        statement = data.get("statement")
        action_card = data.get("action_card")
        target_player_id = data.get("target_player_id")

        if "statement" in game["players"][player_id]:
            emit("error", {"message": "You have already submitted a statement for this round."}, room=request.sid)
            return

        # Sabotage Cost Check
        if action_card == "Sabotage":
            if game["players"][player_id]["personal_stats"]["Spite"] < 3:
                 emit("error", {"message": "Not enough Spite for Sabotage!"}, room=request.sid)
                 return
            # Deduct Spite immediately or later? 
            # Let's deduct later during resolution to be safe, or reserve it.
            # But simpler to deduct now or check only. Let's strictly check now and deduct in resolution
            # to avoid double deduction if logic reruns, BUT ensuring they have it is key.
            # Actually, standard pattern is verify -> lock in.
        
        game["players"][player_id]["statement"] = statement
        game["players"][player_id]["current_action"] = action_card
        game["players"][player_id]["action_target"] = target_player_id
        game["players"][player_id]["action_status"] = (
            "done"  # Player submitted statement
        )
        emit(
            "game_update",
            {"players": game["players"]},
            room=game_id,
            broadcast=True,
        )

        all_players_submitted = all("statement" in p for p in game["players"].values())

        if all_players_submitted:
            statements = {
                pid: {"statement": p["statement"], "name": f"Player {idx + 1}", "action_card": p.get("current_action")}
                for idx, (pid, p) in enumerate(game["players"].items())
                if "statement" in p
            }
            emit(
                "statements_submitted",
                {"statements": statements},
                room=game["host_sid"],
            )
            game["state"] = "VOTING_PHASE" # Transition to voting phase
            emit(
                "phase_change",
                {"phase": "VOTING_PHASE", "statements": statements},
                room=game_id,
                broadcast=True,
            )

    elif action == "submit_vote":
        if game["state"] != "VOTING_PHASE":
            return
        voted_for_player_id = data.get("voted_for_player_id")
        if voted_for_player_id:
            game["players"][player_id]["statement_vote"] = voted_for_player_id
            game["players"][player_id]["action_status"] = "done"
            emit("game_update", {"players": game["players"]}, room=game_id, broadcast=True)

        all_players_voted = all("statement_vote" in p for p in game["players"].values())

        if all_players_voted:
            # --- Spite System: Resolution Phase ---
            
            # 1. Identify Sabotage Targets (Votes received by these players will be voided)
            sabotaged_players = []
            for pid, p in game["players"].items():
                if p.get("current_action") == "Sabotage" and p.get("action_target"):
                    target = p["action_target"]
                    # Verify cost again just in case
                    if p["personal_stats"]["Spite"] >= 3:
                        sabotaged_players.append(target)
                        p["personal_stats"]["Spite"] -= 3 # Pay the cost
                        print(f"[GAME] Player {pid} sabotaged {target}!")

            # 2. Tally Votes
            vote_counts = {pid: 0 for pid in game["players"]}
            for p in game["players"].values():
                vote = p["statement_vote"] # Who they voted for
                if vote:
                     # If the person they voted for is sabotaged, the vote doesn't count towards the total
                     if vote not in sabotaged_players:
                        vote_counts[vote] += 1
                     else:
                        print(f"[GAME] Vote for {vote} nullified by Sabotage.")
            
            # 3. Determine Winner
            # Handle tie: Randomly pick among top
            max_votes = -1
            winners = []
            for pid, count in vote_counts.items():
                if count > max_votes:
                    max_votes = count
                    winners = [pid]
                elif count == max_votes:
                    winners.append(pid)
            
            winning_player_id = random.choice(winners) if winners else None
            
            # 4. Apply Effects
            for pid, p in game["players"].items():
                action = p.get("current_action")
                target = p.get("action_target")
                votes_received = vote_counts.get(pid, 0)
                
                # A. Winner Bonus
                if pid == winning_player_id:
                    p["personal_stats"]["Influence"] += 4
                    print(f"[GAME] {pid} wins the debate! (+4 Infl)")

                # B. Fail Forward (Losers with 0 votes)
                # Only if they didn't win (in case of 0-0-0 tie where winner has 0)
                if votes_received == 0 and pid != winning_player_id:
                    p["personal_stats"]["Spite"] += 1
                    print(f"[GAME] {pid} received 0 votes. (+1 Spite)")

                # C. Card Effects
                if action == "Diplomacy":
                    p["personal_stats"]["Influence"] += 2
                    print(f"[GAME] {pid} used Diplomacy. (+2 Infl)")
                
                elif action == "Blackmail" and target:
                    # Steal 3 Influence
                    target_p = game["players"].get(target)
                    if target_p:
                        amount = min(3, target_p["personal_stats"]["Influence"])
                        target_p["personal_stats"]["Influence"] -= amount
                        p["personal_stats"]["Influence"] += amount
                        print(f"[GAME] {pid} blackmailed {target}. Stole {amount} Infl.")

                elif action == "Demagoguery":
                    # +1 to Random Stat, +1 Spite
                    stat_to_boost = random.choice(["Stability", "Economy", "Faith"])
                    game["global_stats"][stat_to_boost] = min(100, game["global_stats"][stat_to_boost] + 1)
                    p["personal_stats"]["Spite"] += 1
                    print(f"[GAME] {pid} used Demagoguery. ({stat_to_boost} +1, +1 Spite)")
                
                # Sabotage cost already paid
                
                # Clamp stats
                p["personal_stats"]["Influence"] = max(0, p["personal_stats"]["Influence"]) # No cap for now? Rules say 60 to win.
                p["personal_stats"]["Spite"] = max(0, p["personal_stats"]["Spite"])

            # Find the winning statement for the record
            winning_statement = {
                "player_id": winning_player_id,
                "statement": game["players"][winning_player_id]["statement"],
                "name": game["players"][winning_player_id]["name"],
            }
            game["winning_statement"] = winning_statement # Store winning statement in game

            # Update winning_statement objectives
            winning_faction_id = game["players"][winning_player_id]["faction"]
            if winning_faction_id:
                game["winning_statement_counts"][winning_faction_id] += 1
                print(f"[DEBUG] Faction {winning_faction_id} winning_statement count: {game['winning_statement_counts'][winning_faction_id]}")

            # Update unanimous_vote objectives
            for faction_id, faction_data in game["factions"].items():
                faction_players = [p_id for p_id in game["players"] if game["players"][p_id]["faction"] == faction_id and game["players"][p_id].get("statement_vote")]
                if faction_players: # Only check if there are players in the faction who voted
                    first_player_vote = game["players"][faction_players[0]].get("statement_vote")
                    all_voted_same = True
                    for p_id in faction_players[1:]:
                        if game["players"][p_id].get("statement_vote") != first_player_vote:
                            all_voted_same = False
                            break
                    if all_voted_same:
                        game["unanimous_vote_counts"][faction_id] += 1
                        print(f"[DEBUG] Faction {faction_id} unanimous_vote count: {game['unanimous_vote_counts'][faction_id]}")

            # Emit voting results to the host
            emit(
                "voting_results",
                {"vote_counts": vote_counts, "winning_statement": winning_statement},
                room=game["host_sid"],
            )

            # For now, we will move to the comment phase
            game["state"] = "COMMENT_PHASE"
            emit(
                "phase_change",
                {"phase": "COMMENT_PHASE", "winning_statement": winning_statement},
                room=game_id,
                broadcast=True,
            )

    elif action == "submit_comment":
        if game["state"] != "COMMENT_PHASE":
            return
        comment = data.get(
            "comment", ""
        )
        if "comment" in game["players"][player_id]:
            emit("error", {"message": "You have already submitted a comment for this round."}, room=request.sid)
            return  # Get comment, default to empty string if not provided

        # validation_result = validate_player_input_with_gemini(model, comment)
        # if not validation_result["is_valid"]:
        #     emit("error", {"message": f"Invalid comment: {validation_result['reason']}"}, room=request.sid)
        #     return

        game["players"][player_id]["comment"] = comment
        game["players"][player_id]["action_status"] = "done"

        emit("game_update", {"players": game["players"]}, room=game_id, broadcast=True)

        # Collect player comments for Gemini (always collect, even if not all submitted yet)
        player_comments_for_gemini = []
        for pid, p_data in game["players"].items():
            if "comment" in p_data:
                player_comments_for_gemini.append(
                    {"player_id": pid, "comment": p_data["comment"]}
                )

        all_comments_submitted = all("comment" in p for p in game["players"].values())

        if all_comments_submitted:
            print(
                f"[DEBUG] Game {game_id}: All comments submitted. Calling resolve_dilemma."
            )
            # All comments are in, now proceed to resolve the dilemma and display the outcome narrative
            resolve_dilemma(
                game_id, player_comments_for_gemini
            )  # Pass comments to resolve_dilemma
            print(f"[DEBUG] Game {game_id}: resolve_dilemma completed.")

            # Collect all comments to send to the host (this is already done above, but keeping for clarity)
            all_comments = {
                pid: {"comment": p["comment"], "name": f"Player {idx + 1}"}
                for idx, (pid, p) in enumerate(game["players"].items())
                if "comment" in p
            }

            # The outcome narrative data was stored in game['last_outcome_narrative_data'] by resolve_dilemma
            outcome_narrative_data_from_resolve_dilemma = game.get(
                "last_outcome_narrative_data"
            )
            if outcome_narrative_data_from_resolve_dilemma:
                print(f"[DEBUG] Game {game_id}: Emitting comments_received to host.")
                emit(
                    "comments_received",
                    {  # Emit comments and outcome to host
                        "comments": all_comments,
                        "outcome": outcome_narrative_data_from_resolve_dilemma[
                            "outcome_narrative"
                        ],
                        "global_stats": game["global_stats"],
                        "current_round": game["current_round"],
                        "players": game["players"],
                    },
                    room=game["host_sid"],
                )
                print(
                    f"[DEBUG] Game {game_id}: Emitting dilemma_resolved to all clients."
                )
                emit(
                    "dilemma_resolved",
                    {  # Emit dilemma_resolved to players to trigger narrative display
                        "outcome": outcome_narrative_data_from_resolve_dilemma[
                            "outcome_narrative"
                        ],
                        "global_stats": game["global_stats"],
                        "current_round": game["current_round"],
                        "players": game["players"],
                    },
                    room=game_id,
                    broadcast=True,
                )
            else:
                print(
                    f"[DEBUG] Game {game_id}: Fallback narrative. Emitting comments_received to host."
                )
                # Fallback if narrative data was not stored
                emit(
                    "comments_received",
                    {
                        "comments": all_comments,
                        "outcome": "The council reflects on the comments.",
                        "global_stats": game["global_stats"],
                        "current_round": game["current_round"],
                        "players": game["players"],
                    },
                    room=game["host_sid"],
                )
                print(
                    f"[DEBUG] Game {game_id}: Fallback narrative. Emitting dilemma_resolved to all clients."
                )
                emit(
                    "dilemma_resolved",
                    {
                        "outcome": "The council reflects on the comments.",
                        "global_stats": game["global_stats"],
                        "current_round": game["current_round"],
                        "players": game["players"],
                    },
                    room=game_id,
                    broadcast=True,
                )

            # Reset player comments and statement votes for next round
            for player_id in game["players"]:
                game["players"][player_id].pop("comment", None)
                game["players"][player_id].pop(
                    "statement_vote", None
                )  # Clear statement vote after resolution

            # After displaying outcome, game is ready for next round
            game["state"] = (
                "OUTCOME_DISPLAYED"  # New state to indicate outcome is shown
            )
            print(f"[DEBUG] Game {game_id}: State set to OUTCOME_DISPLAYED.")
            # Host will need a "Next Round" button to trigger next_round event

    elif data.get("event") == "next_round":
        if player_id not in game.get("next_round_votes", []):
            game.setdefault("next_round_votes", []).append(player_id)

        if len(game["next_round_votes"]) == len(game["players"]):
            game["next_round_votes"] = []

            game["state"] = "DILEMMA"
            game["current_round"] += 1
            game["dilemma_active"] = True
            for player in game["players"].values():
                player["choice"] = None
                player.pop("statement", None)
                player.pop("statement_vote", None)
                player["current_action"] = None
                player["action_target"] = None
                player["action_status"] = "waiting"  # Reset action status for new round

            game_state_for_gemini = {
                "current_round": game["current_round"],
                "global_stats": game["global_stats"],
                "event_history": game["event_history"],
                "player_statements": [],
                "previous_dilemma_outcome": game["event_history"][-1]
                if game["event_history"]
                else None,
            }

            if generate_dilemma_with_gemini(model, game_state_for_gemini):
                with open("dilemma.json", "r", encoding="utf-8") as f:
                    generated_dilemma = json.load(f)
            else:
                generated_dilemma = {
                    "id": "error_dilemma",
                    "title": "Chwila ciszy",
                    "description": "Wiatry losu milczą. Rada nie jest w stanie się zebrać w tym czasie. Proszę spróbować później.",
                    "choices": [],
                    "narrative_prompt": "Królestwo wstrzymuje oddech.",
                }

            game["current_dilemma"] = generated_dilemma
            game["gemini_output"] = generated_dilemma

            emit(
                "game_event",
                {
                    "event": "dilemma_prompt",
                    "dilemma_json": json.dumps(game["gemini_output"]),
                    "global_stats": game["global_stats"],
                    "current_round": game["current_round"],
                    "players": game["players"],
                },
                room=game_id,
                broadcast=True,
            )

            emit(
                "game_update",
                {"players": game["players"]},
                room=game_id,
                broadcast=True,
            )
    
    save_games()


@socketio.on("disconnect")
def handle_disconnect():
    disconnected_sid = request.sid

    for game_id, game in list(games.items()):
        if game["host_sid"] == disconnected_sid:
            socketio.close_room(game_id)
            if game_id in games:
                games.pop(game_id)
            print(f"Host disconnected, cleaned up game {game_id}")
            continue

        disconnected_player_id = None
        for player_id, player in game["players"].items():
            if player["sid"] == disconnected_sid:
                disconnected_player_id = player_id
                break

        if disconnected_player_id:
            game["players"][disconnected_player_id]["sid"] = None

            emit(
                "player_disconnected",
                {
                    "player": game["players"][disconnected_player_id],
                    "player_id": disconnected_player_id,
                },
                room=game["host_sid"],
            )

            for pid, p in game["players"].items():
                if p["sid"]:
                    emit(
                        "other_player_disconnected",
                        {
                            "player": game["players"][disconnected_player_id],
                            "player_id": disconnected_player_id,
                        },
                        room=p["sid"],
                    )

            print(
                f"Player {disconnected_player_id} disconnected from game {game_id}. Notifying others."
            )


if __name__ == "__main__":
    # We are using eventlet as the web server, which supports WebSockets.
    # The server is configured to be accessible from other devices on the network (host='0.0.0.0').
    host = "0.0.0.0"
    port = 5000
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(("10.255.255.255", 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        s.close()
    print(f"Starting server on http://{IP}:{port}")
    socketio.run(app, host=host, port=port)

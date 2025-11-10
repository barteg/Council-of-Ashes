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
from elevenlabs.client import ElevenLabs
import io

# Securely get the API key from the environment
api_key = os.getenv("GEMINI_API_KEY")
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set!")

# Initialize ElevenLabs client
if not elevenlabs_api_key:
    print(
        "WARNING: ELEVENLABS_API_KEY environment variable not set! TTS will not work."
    )
    elevenlabs_client = None
else:
    elevenlabs_client = ElevenLabs(api_key=elevenlabs_api_key)


model = genai.GenerativeModel("gemini-2.5-flash")

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


def generate_game_id():
    return "".join(random.choices(string.ascii_uppercase, k=4))


@app.route("/")
def index():
    return render_template("index.html")


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
    if not elevenlabs_client:
        print("[TTS] Error: ElevenLabs client not initialized. Is the API key set?")
        return jsonify({"error": "TTS service not configured"}), 500

    text = request.json.get("text")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    print(f"[TTS] Received text for ElevenLabs: {text}")
    try:
        # Generate audio using ElevenLabs API
        audio_stream = elevenlabs_client.text_to_speech.convert(
            text=text,
            voice_id="H5xTcsAIeS5RAykjz57a",  # Voice ID for Antoni
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )

        print("[TTS] Audio generated successfully by ElevenLabs.")

        # Convert the generator to bytes
        audio_bytes = b"".join(audio_stream)

        # Send the audio data back to the client
        return send_file(
            io.BytesIO(audio_bytes), mimetype="audio/mpeg", as_attachment=False
        )
    except Exception as e:
        print(f"[TTS] Error during ElevenLabs audio generation: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": "TTS synthesis failed"}), 500


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
        "Syndykat Kupiecki": {"power": "Mistrzostwo Handlu", "players": []},
        "Wysokie Kapłaństwo": {"power": "Boska Łaska", "players": []},
        "Gwardia Królewska": {"power": "Utrzymanie Porządku", "players": []},
    }
    player_urls = {}

    for i in range(num_players):
        player_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))

        players[player_id] = {
            "id": player_id,
            "sid": None,
            "name": f"Player {i + 1}",
            "avatar": f"/static/avatars/avatar{i + 1}.png",
            "faction": None,  # Player will choose faction
            "choice": None,
            "statements": [],
            "personal_stats": {"Influence": 50},
            "ready": False,
            "shamed": False,  # Player is shamed if their choice would collapse the kingdom
            "action_status": "joined",  # Initialize action status to 'joined'
        }
        # Construct the player URL using a relative path
        player_urls[player_id] = f"/player/{game_id}/{player_id}"

    games[game_id] = {
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
    }
    join_room(game_id)
    emit(
        "game_created",
        {
            "game_id": game_id,
            "player_urls": player_urls,
            "players": players,
            "factions": factions,
        },
    )


@socketio.on("join_game")
def join_game(data):
    game_id = data["game_id"]
    player_id = data.get("player_id")
    game = games.get(game_id)

    if not game:
        emit("error", {"message": "Game not found."})
        return

    join_room(game_id)

    if player_id and player_id in game["players"]:
        game["players"][player_id]["sid"] = request.sid

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

        if not player_faction_id:
            pass

    elif not player_id:  # Host is joining/reconnecting
        game["host_sid"] = request.sid
    else:
        emit("error", {"message": "Invalid player ID."})
        return


@socketio.on("request_faction_info")
def request_faction_info(data):
    game_id = data["game_id"]
    game = games.get(game_id)
    if game:
        emit("faction_info", {"factions": game["factions"]}, room=request.sid)


@socketio.on("join_faction")
def join_faction(data):
    game_id = data["game_id"]
    player_id = data["player_id"]
    faction_id = data["faction_id"]
    game = games.get(game_id)

    if (
        not game
        or player_id not in game["players"]
        or faction_id not in game["factions"]
    ):
        return

    old_faction = game["players"][player_id]["faction"]
    if old_faction and old_faction in game["factions"]:
        if player_id in game["factions"][old_faction]["players"]:
            game["factions"][old_faction]["players"].remove(player_id)

    game["players"][player_id]["faction"] = faction_id
    game["factions"][faction_id]["players"].append(player_id)

    emit(
        "game_update",
        {"players": game["players"], "factions": game["factions"]},
        room=game_id,
        broadcast=True,
    )


@socketio.on("start_game")
def start_game(data):
    game_id = data["game_id"]
    game = games.get(game_id)
    if game and game["host_sid"] == request.sid:
        print(f"[DEBUG] Host has started game {game_id}")
        start_game_logic(game_id)


@socketio.on("player_name_update")
def player_name_update(data):
    game_id = data["game_id"]
    player_id = data["player_id"]
    new_name = data["name"]
    game = games.get(game_id)

    if not game or player_id not in game["players"]:
        return

    game["players"][player_id]["name"] = new_name

    emit("name_accepted", room=request.sid)
    emit(
        "faction_info", {"factions": game["factions"]}, room=request.sid
    )  # Emit faction info to the player
    emit("game_update", {"players": game["players"]}, room=game_id, broadcast=True)


def start_game_logic(game_id):
    print(f"[DEBUG] Starting game {game_id}")
    game = games.get(game_id)
    if not game or game["state"] != "waiting":
        return

    game["state"] = "DILEMMA"

    # Start the first round
    game["current_round"] = 1
    game["dilemma_active"] = True
    for player in game["players"].values():
        player["choice"] = None
        player.pop("statement", None)
        player.pop("statement_vote", None)
        player["action_status"] = "waiting"  # Reset action status

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
    print("[DEBUG] Emitting game_event")
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


@socketio.on("player_ready")
def player_ready(data):
    game_id = data["game_id"]
    player_id = data["player_id"]
    game = games.get(game_id)

    if not game or player_id not in game["players"]:
        return

    print(f"[DEBUG] Player {player_id} is ready in game {game_id}")
    game["players"][player_id]["ready"] = True
    print(f"[DEBUG] Player statuses: {[p['ready'] for p in game['players'].values()]}")

    # Notify host about the player's ready status
    emit(
        "player_ready_update",
        {"player": game["players"][player_id], "player_id": player_id},
        room=game["host_sid"],
    )

    # Check if all players are ready
    all_ready = all(p["ready"] for p in game["players"].values())
    print(f"[DEBUG] Checking if all players are ready in game {game_id}: {all_ready}")
    if all_ready:
        print("[DEBUG] All players are ready. Notifying host.")
        emit("all_players_ready", room=game["host_sid"])


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

    # Gather all player statements
    player_statements_for_gemini = []
    for player_id, player_data in game["players"].items():
        if "statement" in player_data:
            player_statements_for_gemini.append(
                {"player_id": player_id, "statement": player_data["statement"], "name": player_data["name"]}
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

    if evaluation_result:
        chosen_policy = evaluation_result.get("chosen_policy", chosen_policy)
        policy_effects = evaluation_result.get("effects", policy_effects)
        narrative_consequence = evaluation_result.get("narrative_consequence", narrative_consequence)

        for stat, change in policy_effects.items():
            game["global_stats"][stat] += change
            game["global_stats"][stat] = max(0, min(100, game["global_stats"][stat]))

    # Check for lose condition (kingdom collapse)
    if any(stat <= 0 for stat in game["global_stats"].values()):
        game["state"] = "GAME_OVER"
        emit(
            "game_over",
            {"winner": None, "reason": "The kingdom has collapsed!"},
            room=game_id,
            broadcast=True,
        )
        return

    # Player influence logic (simplified for now, can be expanded later)
    # For now, players who submitted statements gain a small amount of influence
    for player_id, player_data in game["players"].items():
        if "statement" in player_data:
            player_data["personal_stats"]["Influence"] = min(
                100, player_data["personal_stats"]["Influence"] + 2
            )
        player_data["personal_stats"]["Influence"] = max(
            0, min(100, player_data["personal_stats"]["Influence"])
        )

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
        emit("game_over", {"winner": winner}, room=game_id, broadcast=True)
        return

    game["dilemma_active"] = False
    game["current_dilemma"] = None


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
        if statement:
            game["players"][player_id]["statement"] = statement
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
                pid: {"statement": p["statement"], "name": p["name"]}
                for pid, p in game["players"].items()
            }
            emit(
                "statements_submitted",
                {"statements": statements},
                room=game["host_sid"],
            )
            game["state"] = "COMMENT_PHASE" # Directly move to comment phase after statements
            emit(
                "phase_change",
                {"phase": "COMMENT_PHASE", "statements": statements},
                room=game_id,
                broadcast=True,
            )

    elif action == "submit_comment":
        if game["state"] != "COMMENT_PHASE":
            return
        comment = data.get(
            "comment", ""
        )  # Get comment, default to empty string if not provided
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
                pid: {"comment": p["comment"], "name": p["name"]}
                for pid, p in game["players"].items()
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

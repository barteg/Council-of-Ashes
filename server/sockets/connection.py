from flask import request
from flask_socketio import emit, join_room, close_room
from server.extensions import socketio
from server.services.game_manager import game_manager
import random

@socketio.on("create_game")
def handle_create_game(data):
    num_players = data.get("num_players", 1)
    game_id, game = game_manager.create_game(request.sid, num_players)
    
    join_room(game_id)
    emit(
        "game_created",
        {
            "game_id": game_id,
            "join_url": game["join_url"],
            "players": game["players"],
            "factions": game["factions"],
        },
        room=request.sid,
    )

@socketio.on("join_game")
def handle_join_game(data):
    try:
        game_id = data["game_id"]
        player_id = data.get("player_id")
        player_name = data.get("player_name")
        faction_id = data.get("faction_id")
        
        game = game_manager.get_game(game_id)
        print(f"[DEBUG] join_game received: {data}")

        if not game:
            emit("error", {"message": "Game not found."}, room=request.sid)
            return

        join_room(game_id)

        if player_id: # Reconnecting
            print(f"[DEBUG] Player {player_id} is reconnecting.")
            if player_id in game["players"]:
                game["players"][player_id]["sid"] = request.sid
                game["players"][player_id]["action_status"] = "joined"

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

        elif player_name: # New player via QR
            print(f"[DEBUG] New player '{player_name}' is joining.")
            assigned_player_id = None
            for pid, player_data in game["players"].items():
                if player_data["action_status"] == "empty":
                    assigned_player_id = pid
                    break
            
            if assigned_player_id:
                # Find faction with fewest players
                min_players = float('inf')
                least_populated_factions = []
                for f_id, f_data in game["factions"].items():
                    num_players_in_faction = len(f_data["players"])
                    if num_players_in_faction < min_players:
                        min_players = num_players_in_faction
                        least_populated_factions = [f_id]
                    elif num_players_in_faction == min_players:
                        least_populated_factions.append(f_id)
                
                chosen_faction = random.choice(least_populated_factions)

                print(f"[DEBUG] Assigning new player to slot: {assigned_player_id} in faction {chosen_faction}")
                game["players"][assigned_player_id]["sid"] = request.sid
                game["players"][assigned_player_id]["name"] = player_name
                game["players"][assigned_player_id]["faction"] = chosen_faction
                game["players"][assigned_player_id]["action_status"] = "joined"
                
                game["factions"][chosen_faction]["players"].append(assigned_player_id)

                emit("player_assigned", {"player_id": assigned_player_id}, room=request.sid)
                emit("game_update", {"players": game["players"], "factions": game["factions"]}, room=game_id, broadcast=True)
            else:
                emit("error", {"message": "No available player slots."}, room=request.sid)
                return

        elif not player_id and not player_name: # Host Reconnecting
            print("[DEBUG] Host is reconnecting.")
            game["host_sid"] = request.sid
        else:
            emit("error", {"message": "Invalid join request."}, room=request.sid)
            return
            
        game_manager.save_games()
    except Exception as e:
        print(f"[ERROR] Exception in join_game handler: {e}")
        import traceback
        traceback.print_exc()

@socketio.on("disconnect")
def handle_disconnect():
    disconnected_sid = request.sid

    for game_id, game in list(game_manager.games.items()):
        if game["host_sid"] == disconnected_sid:
            close_room(game_id)
            if game_id in game_manager.games:
                game_manager.games.pop(game_id)
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

            print(f"Player {disconnected_player_id} disconnected from game {game_id}.")

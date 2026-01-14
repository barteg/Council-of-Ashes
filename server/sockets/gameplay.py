from flask import request
from flask_socketio import emit
from server.extensions import socketio
from server.services.game_manager import game_manager
from server.services.llm.narrator import narrator
import json
import random

# --- Helper Functions ---

def start_game_logic(game_id):
    try:
        print(f"[DEBUG] Starting game {game_id}")
        game = game_manager.get_game(game_id)
        if not game or game["state"] != "waiting":
            print(f"[ERROR] start_game_logic called with invalid game state")
            return

        game["state"] = "DILEMMA"
        game["current_round"] = 1
        game["dilemma_active"] = True
        
        for player_id, player in game["players"].items():
            player["action_status"] = "waiting"
            player["shadow_action_done"] = False

        game_state_for_gemini = {
            "current_round": game["current_round"],
            "global_stats": game["global_stats"],
            "event_history": game["event_history"],
            "player_statements": [],
            "previous_dilemma_outcome": None,
        }
        
        if narrator.generate_dilemma(game_state_for_gemini):
            with open("dilemma.json", "r", encoding="utf-8") as f:
                generated_dilemma = json.load(f)
        else:
            generated_dilemma = {
                "id": "error_dilemma",
                "title": "Chwila ciszy",
                "description": "Wiatry losu milczą. Rada nie jest w stanie się zebrać w tym czasie.",
                "narrative_prompt": "Królestwo wstrzymuje oddech.",
            }

        game["current_dilemma"] = generated_dilemma
        game["gemini_output"] = generated_dilemma

        emit("game_started_for_player", game, room=game_id, broadcast=True)
        emit("game_started_for_host", game, room=game["host_sid"])
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
        game_manager.save_games()
    except Exception as e:
        print(f"[ERROR] Exception in start_game_logic: {e}")
        import traceback
        traceback.print_exc()

def resolve_dilemma(game_id, player_comments=None):
    game = game_manager.get_game(game_id)
    if not game:
        return

    winning_player_id = game.get("winning_statement", {}).get("player_id")
    winning_player = game["players"].get(winning_player_id)
    initial_global_stats = game["global_stats"].copy()

    # Apply Manual Effects from Winning Statement
    policy_effects = {}
    if winning_player:
        policy_effects = winning_player.get("predicted_effect", {"Stability": 0, "Economy": 0, "Faith": 0})
        for stat, change in policy_effects.items():
            game["global_stats"][stat] += int(change)
            game["global_stats"][stat] = max(0, min(100, game["global_stats"][stat]))

            if int(change) > 0:
                for faction_id in game["factions"]:
                    for objective in game["factions"][faction_id]["objectives"]:
                        if objective["type"] == "policies_passed" and objective["stat"] == stat:
                            game["policies_passed_counts"][faction_id][stat] += 1

    # Check Objectives
    winning_faction = None
    for faction_id, faction_data in game["factions"].items():
        all_objectives_completed = True
        for objective in faction_data["objectives"]:
            if not objective["completed"]:
                if objective["type"] == "stat_target":
                    if game["global_stats"][objective["stat"]] >= objective["target"]:
                        objective["completed"] = True
                elif objective["type"] == "unanimous_vote":
                    if game["unanimous_vote_counts"][faction_id] >= objective["count"]:
                        objective["completed"] = True
                elif objective["type"] == "policies_passed":
                    if game["policies_passed_counts"][faction_id][objective["stat"]] >= objective["count"]:
                        objective["completed"] = True
                elif objective["type"] == "stat_lower":
                    if initial_global_stats[objective["stat"]] - game["global_stats"][objective["stat"]] >= objective["amount"]:
                        objective["completed"] = True
                elif objective["type"] == "winning_statement":
                    if game["winning_statement_counts"][faction_id] >= objective["count"]:
                        objective["completed"] = True
                
                if not objective["completed"]:
                    all_objectives_completed = False
                    break
        
        if all_objectives_completed:
            winning_faction = faction_id
            break

    if winning_faction:
        game["state"] = "GAME_OVER"
        game_manager.save_games()
        socketio.emit(
            "game_over",
            {"winner": {"name": winning_faction}, "reason": f"The {winning_faction} has achieved its objectives!"},
            room=game_id,
        )
        return

    # Check for kingdom collapse
    collapsed_stats = [stat for stat, val in game["global_stats"].items() if val <= 0]
    if collapsed_stats:
        print(f"[GAME] Kingdom Stability Collapse detected! Stats: {collapsed_stats}")
        for pid, p in game["players"].items():
            p["personal_stats"]["Influence"] = int(p["personal_stats"]["Influence"] * 0.5)
            
        guilty_players = []
        winning_stmt_player = game.get("winning_statement", {}).get("player_id")
        if winning_stmt_player:
             guilty_players.append(winning_stmt_player)
             for pid, p in game["players"].items():
                 if p.get("statement_vote") == winning_stmt_player:
                     guilty_players.append(pid)
        
        guilty_players = list(set(guilty_players))
        for pid in guilty_players:
            if pid in game["players"]:
                 game["players"][pid]["personal_stats"]["Influence"] = 0
                 game["players"][pid]["shamed"] = True

        for stat in collapsed_stats:
            game["global_stats"][stat] = 1

        socketio.emit(
            "kingdom_collapse", 
            {"collapsed_stats": collapsed_stats, "guilty_players": guilty_players},
            room=game_id, 
        )

    # Narrative & Next Dilemma Generation (COMBINED)
    player_statements_for_gemini = []
    for pid, p in game["players"].items():
        if p.get("statement"):
            player_statements_for_gemini.append({
                "name": p["name"],
                "statement": p["statement"],
                "is_winner": (pid == winning_player_id)
            })

    chapter_data = narrator.call_gemini_for_next_chapter(
        game_state=game,
        chosen_policy=winning_player["statement"] if winning_player else "Inaction",
        player_statements=player_statements_for_gemini,
        player_comments=player_comments
    )

    if chapter_data:
        outcome_narrative = chapter_data.get("outcome_narrative", "Pisarze zamilkli.")
        # Store pre-generated dilemma
        game["next_round_dilemma"] = chapter_data.get("next_dilemma")
    else:
        outcome_narrative = "Kronikarze nie byli w stanie zapisać tej tury."
        game["next_round_dilemma"] = None

    game["event_history"].append(
        {
            "round": game["current_round"],
            "policy_chosen": winning_player["statement"] if winning_player else "None",
            "effects": policy_effects,
            "outcome_narrative": outcome_narrative,
            "global_stats_after": game["global_stats"].copy(),
        }
    )

    game["last_outcome_narrative_data"] = {"outcome_narrative": outcome_narrative}

    # Emit results after AI generation
    all_comments = {pid: {"comment": p.get("comment", ""), "name": p["name"]} for pid, p in game["players"].items() if p.get("comment")}
    
    socketio.emit("comments_received", {
        "comments": all_comments,
        "outcome": outcome_narrative,
        "global_stats": game["global_stats"],
        "current_round": game["current_round"],
        "players": game["players"]
    }, room=game_id)

    socketio.emit("dilemma_resolved", {
        "outcome": outcome_narrative,
        "global_stats": game["global_stats"],
        "current_round": game["current_round"],
        "players": game["players"]
    }, room=game_id)

    game["state"] = "OUTCOME_DISPLAYED"

# --- Event Handlers ---

@socketio.on("player_ready")
def player_ready(data):
    try:
        game_id = data["game_id"]
        player_id = data["player_id"]
        game = game_manager.get_game(game_id)

        if not game or player_id not in game["players"]:
            return

        game["players"][player_id]["ready"] = True
        emit(
            "player_ready_update",
            {"player": game["players"][player_id], "player_id": player_id},
            room=game["host_sid"],
        )

        joined_players = [p for p in game["players"].values() if p["action_status"] != "empty"]
        all_joined_ready = all(p["ready"] for p in joined_players)
        
        if len(joined_players) == len(game['players']) and all_joined_ready:
            start_game_logic(game_id)
        
        game_manager.save_games()
    except Exception as e:
        print(f"[ERROR] player_ready: {e}")

@socketio.on("game_event")
def handle_game_event(data):
    # This was mostly empty in original code or handled next_round via player_action logic??
    # Ah, handle_game_event only printed debug info in original code.
    # But wait, next_round logic is in player_action/game_event? 
    # Original code had `elif data.get("event") == "next_round":` INSIDE `handle_player_action`.
    # Wait, no. `handle_game_event` was minimal. `handle_player_action` had `if action == ...`.
    # BUT there was `elif data.get("event") == "next_round"` inside `handle_player_action`? 
    # No, looking at `app.py`:
    # `handle_player_action` handled `submit_statement`, `submit_vote`, `submit_comment`, AND `next_round` (via `data.get("event")` check?? No that's mixed).
    # Let's re-read `app.py`.
    # `handle_player_action` handles `action="submit_statement"`, `action="submit_vote"`, `action="submit_comment"`.
    # AND `elif data.get("event") == "next_round":` was... wait.
    # It was `elif data.get("event") == "next_round":` inside `handle_player_action`.
    # That implies the client sends `event: "next_round"` to the `player_action` socket event?
    # Or maybe it was `socketio.on("game_event")`?
    # Original code:
    # @socketio.on("game_event")
    # def handle_game_event(data): ...
    # @socketio.on("player_action")
    # def handle_player_action(data): ...
    #   if action == ...
    #   elif data.get("event") == "next_round": ...
    
    # Yes, it seems `next_round` was handled inside `handle_player_action` (presumably because `data` contained `event` key instead of `action` key? A bit messy).
    # I will support `next_round` in `handle_player_action`.
    pass

@socketio.on("player_action")
def handle_player_action(data):
    game_id = data.get("game_id")
    player_id = data.get("player_id")
    action = data.get("action")
    event_type = data.get("event") # For next_round
    
    game = game_manager.get_game(game_id)
    if not game: 
        return
    # Note: next_round might come from host who doesn't have a player_id in players list?
    # Check original logic: `if not game or player_id not in game["players"]: return`
    # This implies host MUST have a player_id? Or `next_round` was broken?
    # Host usually sends next_round. Host doesn't have player_id in `game["players"]`.
    # In original code: `if not game or player_id not in game["players"]:` is at the top.
    # So host couldn't trigger next_round if they weren't a player?
    # Wait, `game["next_round_votes"]`. It seems players vote for next round.
    
    if player_id not in game["players"]:
        # If it is next_round event, maybe we allow it?
        # But original code blocked it. I will stick to original logic.
        return

    if action == "submit_shadow_action":
        shadow_type = data.get("shadow_type")
        target = data.get("target")
        payload = data.get("payload")
        player = game["players"][player_id]
        
        # Define Costs
        spite_cost = 0
        influence_cost = 0
        
        if shadow_type == "gambler": influence_cost = 5
        elif shadow_type == "veto": spite_cost = 1
        # Curse and Censor are now 0 Spite
        
        # Check Costs
        if player["personal_stats"]["Spite"] < spite_cost:
            emit("error", {"message": f"Za mało Spite! Potrzebujesz {spite_cost}."}, room=request.sid)
            return
        if player["personal_stats"]["Influence"] < influence_cost:
            emit("error", {"message": f"Za mało Influence! Potrzebujesz {influence_cost}."}, room=request.sid)
            return
            
        # Deduct Costs
        player["personal_stats"]["Spite"] -= spite_cost
        player["personal_stats"]["Influence"] -= influence_cost
        player["shadow_action_done"] = True # PERSISTENCE FIX

        effect = {
            "source": player_id,
            "type": shadow_type,
            "target": target,
            "payload": payload,
            "round": game["current_round"]
        }
        
        game.setdefault("shadow_effects", []).append(effect)
        
        emit("game_update", {"players": game["players"]}, room=game_id, broadcast=True)
        return

    if action == "submit_statement":
        if game["state"] != "DILEMMA": return
        statement = data.get("statement")

        if "statement" in game["players"][player_id]:
            emit("error", {"message": "Already submitted."}, room=request.sid)
            return

        # Enforce Shadow Effects
        prev_round = game["current_round"] - 1
        active_effects = [e for e in game.get("shadow_effects", []) if e["round"] == prev_round and e["target"] == player_id]
        
        for effect in active_effects:
            if effect["type"] == "curse":
                word = effect["payload"]
                if word and word.lower() not in statement.lower():
                    game["players"][player_id]["personal_stats"]["Influence"] = max(0, game["players"][player_id]["personal_stats"]["Influence"] - 3)
            elif effect["type"] == "censor":
                char = effect["payload"]
                if char and char.lower() in statement.lower():
                    game["players"][player_id]["personal_stats"]["Influence"] = max(0, game["players"][player_id]["personal_stats"]["Influence"] - 2)

        game["players"][player_id]["statement"] = statement
        game["players"][player_id]["action_status"] = "done"
        
        # Store manual effects provided by player
        manual_effects = data.get("manual_effects", {"Stability": 0, "Economy": 0, "Faith": 0})
        game["players"][player_id]["predicted_effect"] = manual_effects

        emit("game_update", {"players": game["players"]}, room=game_id, broadcast=True)

        if all("statement" in p for p in game["players"].values()):
            statements = {
                pid: {
                    "statement": p["statement"], 
                    "name": p["name"], 
                    "predicted_effect": p.get("predicted_effect", {})
                }
                for pid, p in game["players"].items()
                if "statement" in p
            }
            emit("statements_submitted", {"statements": statements}, room=game_id)
            game["state"] = "VOTING_PHASE"
            emit("phase_change", {"phase": "VOTING_PHASE", "statements": statements}, room=game_id, broadcast=True)

    elif action == "submit_vote":
        if game["state"] != "VOTING_PHASE": return
        voted_for = data.get("voted_for_player_id")
        vote_type = data.get("type", "vote")
        
        if vote_type == "sabotage":
            if game["players"][player_id]["personal_stats"]["Spite"] >= 3:
                game["players"][player_id]["personal_stats"]["Spite"] -= 3
                game["players"][player_id]["statement_vote"] = {"target": voted_for, "type": "sabotage"}
            else:
                emit("error", {"message": "Not enough Spite!"}, room=request.sid)
                return
        else:
            game["players"][player_id]["statement_vote"] = voted_for

        game["players"][player_id]["action_status"] = "done"
        emit("game_update", {"players": game["players"]}, room=game_id, broadcast=True)

        if all("statement_vote" in p for p in game["players"].values()):
            # Resolution
            vote_counts = {pid: 0 for pid in game["players"]}
            sabotage_counts = {pid: 0 for pid in game["players"]}

            for p in game["players"].values():
                v = p["statement_vote"]
                if isinstance(v, dict) and v.get("type") == "sabotage":
                    sabotage_counts[v["target"]] += 1
                elif isinstance(v, str):
                    vote_counts[v] += 1
                elif isinstance(v, dict) and v.get("type") == "vote":
                     vote_counts[v["target"]] += 1
            
            # Determine Winner (Filter out sabotaged)
            valid_candidates = [pid for pid in game["players"] if sabotage_counts[pid] == 0]
            
            if not valid_candidates:
                 # Chaos: If everyone is sabotaged, anyone can win
                 valid_candidates = list(game["players"].keys())

            max_votes = -1
            winners = []
            for pid in valid_candidates:
                count = vote_counts[pid]
                if count > max_votes:
                    max_votes = count
                    winners = [pid]
                elif count == max_votes:
                    winners.append(pid)
            
            winning_player_id = random.choice(winners) if winners else None
            
            # Check Shadow Effects from previous round
            prev_round = game["current_round"] - 1
            shadow_effects = game.get("shadow_effects", [])
            
            bets = [e for e in shadow_effects if e["round"] == prev_round and e["type"] == "gambler"]
            vetoes = [e["target"] for e in shadow_effects if e["round"] == prev_round and e["type"] == "veto"]
            
            for bet in bets:
                if bet["payload"] == winning_player_id:
                    if bet["source"] in game["players"]:
                        game["players"][bet["source"]]["personal_stats"]["Influence"] += 10

            # Apply Influence
            for pid, p in game["players"].items():
                if pid in vetoes:
                    print(f"[GAME] {pid} is VETOED. 0 points.")
                    continue

                votes_rec = vote_counts.get(pid, 0)
                p["personal_stats"]["Influence"] += votes_rec
                
                if pid == winning_player_id:
                    p["personal_stats"]["Influence"] += 4
                elif votes_rec == 0:
                    p["personal_stats"]["Spite"] += 1
                
                p["personal_stats"]["Influence"] = max(0, p["personal_stats"]["Influence"])
                p["personal_stats"]["Spite"] = max(0, p["personal_stats"]["Spite"])

            winning_statement = {
                "player_id": winning_player_id,
                "statement": game["players"][winning_player_id]["statement"],
                "name": game["players"][winning_player_id]["name"],
                "was_blocked": sabotage_counts.get(winning_player_id, 0) > 0
            }
            game["winning_statement"] = winning_statement
            for pid in game["players"]:
                game["players"][pid]["was_blocked"] = (sabotage_counts[pid] > 0)

            # Objectives update (Winning Statement & Unanimous Vote)
            winning_faction_id = game["players"][winning_player_id]["faction"]
            if winning_faction_id:
                game["winning_statement_counts"][winning_faction_id] += 1

            for faction_id in game["factions"]:
                faction_players = [p_id for p_id in game["players"] if game["players"][p_id]["faction"] == faction_id and game["players"][p_id].get("statement_vote")]
                if faction_players:
                    first_vote = game["players"][faction_players[0]].get("statement_vote")
                    if all(game["players"][pid].get("statement_vote") == first_vote for pid in faction_players[1:]):
                        game["unanimous_vote_counts"][faction_id] += 1

            emit("voting_results", {"vote_counts": vote_counts, "winning_statement": winning_statement}, room=game["host_sid"])
            game["state"] = "COMMENT_PHASE"
            emit("phase_change", {"phase": "COMMENT_PHASE", "winning_statement": winning_statement}, room=game_id, broadcast=True)

    elif action == "submit_comment":
        if game["state"] != "COMMENT_PHASE": return
        
        # Check Silence
        prev_round = game["current_round"] - 1
        is_silenced = any(e["type"] == "silence" and e["target"] == player_id and e["round"] == prev_round for e in game.get("shadow_effects", []))
        
        if is_silenced:
             comment = "..."
        else:
             comment = data.get("comment", "")

        if "comment" in game["players"][player_id]: return

        game["players"][player_id]["comment"] = comment
        game["players"][player_id]["action_status"] = "done"
        emit("game_update", {"players": game["players"]}, room=game_id, broadcast=True)

        if all("comment" in p for p in game["players"].values()):
            # Collect comments
            player_comments = [{"player_id": pid, "comment": p["comment"]} for pid, p in game["players"].items() if "comment" in p]
            
            # Start Shadow Phase (Dark Market)
            game["state"] = "SHADOW_PHASE"
            emit("phase_change", {"phase": "SHADOW_PHASE"}, room=game_id, broadcast=True)
            
            # Run resolution in background to allow Shadow Actions while AI thinks
            socketio.start_background_task(resolve_dilemma, game_id, player_comments)

    elif event_type == "next_round":
        if player_id not in game.get("next_round_votes", []):
            game.setdefault("next_round_votes", []).append(player_id)
        
        if len(game["next_round_votes"]) == len(game["players"]):
            game["next_round_votes"] = []
            
            # Start Next Round
            game["state"] = "DILEMMA"
            game["current_round"] += 1
            game["dilemma_active"] = True
            for player in game["players"].values():
                player["choice"] = None
                player.pop("statement", None)
                player.pop("statement_vote", None)
                player["current_action"] = None
                player["action_target"] = None
                player["action_target_stat"] = None
                player["action_status"] = "waiting"
                player["shadow_action_done"] = False

            # Use Pre-generated dilemma from previous AI call
            generated_dilemma = game.get("next_round_dilemma")
            
            if not generated_dilemma:
                # Fallback if something went wrong
                game_state_for_gemini = {
                    "current_round": game["current_round"],
                    "global_stats": game["global_stats"],
                    "event_history": game["event_history"],
                    "player_statements": [],
                    "previous_dilemma_outcome": game["event_history"][-1] if game["event_history"] else None,
                }
                if narrator.generate_dilemma(game_state_for_gemini):
                    with open("dilemma.json", "r") as f:
                        generated_dilemma = json.load(f)
                else:
                    generated_dilemma = {"id": "error", "title": "Error", "description": "...", "narrative_prompt": "..."}

            game["current_dilemma"] = generated_dilemma
            game["gemini_output"] = generated_dilemma

            emit("game_event", {
                "event": "dilemma_prompt",
                "dilemma_json": json.dumps(game["gemini_output"]),
                "global_stats": game["global_stats"],
                "current_round": game["current_round"],
                "players": game["players"]
            }, room=game_id, broadcast=True)
            
            emit("game_update", {"players": game["players"]}, room=game_id, broadcast=True)

    game_manager.save_games()

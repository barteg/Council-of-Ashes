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
            player["choice"] = None
            player.pop("statement", None)
            player.pop("statement_vote", None)
            player["current_action"] = None
            player["action_target"] = None
            player["action_target_stat"] = None
            player["action_status"] = "waiting"

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

    player_statements_for_gemini = []
    winning_player_id = game.get("winning_statement", {}).get("player_id")

    for player_id, player_data in game["players"].items():
        if "statement" in player_data and player_data["statement"]:
            is_winner = (player_id == winning_player_id)
            player_statements_for_gemini.append(
                {
                    "player_id": player_id,
                    "statement": player_data["statement"],
                    "name": player_data["name"],
                    "faction": player_data.get("faction"),
                    "action_card": player_data.get("current_action"),
                    "was_blocked": player_data.get("was_blocked", False),
                    "is_winner": is_winner
                }
            )

    evaluation_result = narrator.evaluate_player_statements(
        game_state={
            "current_round": game["current_round"],
            "global_stats": game["global_stats"],
        },
        player_statements=player_statements_for_gemini,
    )

    chosen_policy = "No policy adopted due to council inaction."
    policy_effects = {}
    narrative_consequence = "The council's indecision led to stagnation."
    initial_global_stats = game["global_stats"].copy()

    if evaluation_result:
        chosen_policy = evaluation_result.get("chosen_policy", chosen_policy)
        policy_effects = evaluation_result.get("effects", policy_effects)
        narrative_consequence = evaluation_result.get("narrative_consequence", narrative_consequence)

        for stat, change in policy_effects.items():
            game["global_stats"][stat] += change
            game["global_stats"][stat] = max(0, min(100, game["global_stats"][stat]))

            if change > 0:
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
        emit(
            "game_over",
            {"winner": {"name": winning_faction}, "reason": f"The {winning_faction} has achieved its objectives!"},
            room=game_id,
            broadcast=True,
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

        emit(
            "kingdom_collapse", 
            {"collapsed_stats": collapsed_stats, "guilty_players": guilty_players},
            room=game_id, 
            broadcast=True
        )

    # Narrative Generation
    gemini_success = narrator.call_gemini_for_outcome_narrative(
        game_state={
            "current_round": game["current_round"],
            "global_stats": game["global_stats"],
        },
        chosen_policy=chosen_policy,
        policy_effects=policy_effects,
        faction_votes={},
        player_statements=player_statements_for_gemini,
        player_comments=player_comments,
    )

    if gemini_success:
        try:
            with open("outcome.json", "r", encoding="utf-8") as f:
                outcome_narrative_data = json.load(f)
        except json.JSONDecodeError:
            outcome_narrative_data = None
    else:
        outcome_narrative_data = None

    if not outcome_narrative_data:
        outcome_narrative_data = {
            "outcome_narrative": "Pisarze nie są w stanie zapisać wydarzeń tej rady.",
            "next_event_hint": "Przyszłość jest niepewna.",
            "kingdom_status_summary": "Królestwo jest w stanie ciągłych zmian.",
        }

    game["event_history"].append(
        {
            "round": game["current_round"],
            "policy_chosen": chosen_policy,
            "effects": policy_effects,
            "faction_votes": {},
            "outcome_narrative": outcome_narrative_data["outcome_narrative"],
            "global_stats_after": game["global_stats"].copy(),
        }
    )

    game["last_outcome_narrative_data"] = outcome_narrative_data

    # Check Influence Win
    winner = None
    for pid, p in game["players"].items():
        if p["personal_stats"]["Influence"] >= 100:
            winner = p
            break

    if winner:
        game["state"] = "GAME_OVER"
        game_manager.save_games()
        emit("game_over", {"winner": winner}, room=game_id, broadcast=True)
        return

    game["dilemma_active"] = False
    game["current_dilemma"] = None
    game_manager.save_games()

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

    if action == "submit_statement":
        if game["state"] != "DILEMMA": return
        statement = data.get("statement")

        if "statement" in game["players"][player_id]:
            emit("error", {"message": "Already submitted."}, room=request.sid)
            return

        game["players"][player_id]["statement"] = statement
        game["players"][player_id]["action_status"] = "done"
        
        emit("game_update", {"players": game["players"]}, room=game_id, broadcast=True)

        if all("statement" in p for p in game["players"].values()):
            # Prepare statements for batch analysis
            statements_for_ai = {
                pid: p["statement"]
                for pid, p in game["players"].items()
                if "statement" in p
            }
            
            # Predict effects using Gemini
            predicted_effects = narrator.analyze_all_statements(statements_for_ai)
            if not predicted_effects:
                predicted_effects = {} # Fallback

            statements = {
                pid: {
                    "statement": p["statement"], 
                    "name": f"Player {idx + 1}", 
                    "predicted_effect": predicted_effects.get(pid, {})
                }
                for idx, (pid, p) in enumerate(game["players"].items())
                if "statement" in p
            }
            emit("statements_submitted", {"statements": statements}, room=game["host_sid"])
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
            
            # Apply Influence
            for pid, p in game["players"].items():
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
        comment = data.get("comment", "")
        if "comment" in game["players"][player_id]: return

        game["players"][player_id]["comment"] = comment
        game["players"][player_id]["action_status"] = "done"
        emit("game_update", {"players": game["players"]}, room=game_id, broadcast=True)

        if all("comment" in p for p in game["players"].values()):
            # Collect comments
            player_comments = [{"player_id": pid, "comment": p["comment"]} for pid, p in game["players"].items() if "comment" in p]
            resolve_dilemma(game_id, player_comments)

            all_comments = {pid: {"comment": p["comment"], "name": f"Player {idx+1}"} for idx, (pid, p) in enumerate(game["players"].items()) if "comment" in p}
            outcome = game.get("last_outcome_narrative_data", {}).get("outcome_narrative", "...")

            emit("comments_received", {
                "comments": all_comments,
                "outcome": outcome,
                "global_stats": game["global_stats"],
                "current_round": game["current_round"],
                "players": game["players"]
            }, room=game["host_sid"])

            emit("dilemma_resolved", {
                "outcome": outcome,
                "global_stats": game["global_stats"],
                "current_round": game["current_round"],
                "players": game["players"]
            }, room=game_id, broadcast=True)

            # Cleanup
            for pid in game["players"]:
                game["players"][pid].pop("comment", None)
                game["players"][pid].pop("statement_vote", None)

            game["state"] = "OUTCOME_DISPLAYED"

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

import json
import os
import random
import string
from flask_socketio import emit, join_room

GAMES_FILE = "games_data.json"

class GameManager:
    def __init__(self):
        self.games = {}
        # Automatic loading is currently disabled in original code to ensure clean state
        # self.load_games() 
        print("[PERSISTENCE] Automatic loading of games disabled to ensure clean state.")

    def save_games(self):
        try:
            with open(GAMES_FILE, "w") as f:
                json.dump(self.games, f, indent=4)
            print(f"[PERSISTENCE] Games saved to {GAMES_FILE}")
        except Exception as e:
            print(f"[PERSISTENCE] Error saving games: {e}")

    def load_games(self):
        if os.path.exists(GAMES_FILE):
            try:
                with open(GAMES_FILE, "r") as f:
                    self.games = json.load(f)
                print(f"[PERSISTENCE] Loaded {len(self.games)} games from {GAMES_FILE}")
            except Exception as e:
                print(f"[PERSISTENCE] Error loading games: {e}")
                self.games = {}
        else:
            print("[PERSISTENCE] No existing games file found. Starting with empty games.")
            self.games = {}

    def get_game(self, game_id):
        return self.games.get(game_id)

    def generate_game_id(self):
        return "".join(random.choices(string.ascii_uppercase, k=4))

    def create_game(self, host_sid, num_players=1):
        game_id = self.generate_game_id()
        while game_id in self.games:
            game_id = self.generate_game_id()

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
            player_id = f"player_{i+1}"
            players[player_id] = {
                "id": player_id,
                "sid": None,
                "name": f"Player {i + 1} (Empty)",
                "avatar": f"/static/avatars/avatar{i + 1}.png",
                "faction": None,
                "choice": None,
                "statements": [],
                "personal_stats": {"Influence": 50, "Spite": 0},
                "ready": False,
                "shamed": False,
                "action_status": "empty",
                "current_action": None,
                "action_target": None,
                "is_host": (i == 0) # Player 1 is host
            }

        join_url = f"/join/{game_id}"

        game = {
            "host_sid": host_sid,
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
            "join_url": join_url,
        }
        
        self.games[game_id] = game
        self.save_games()
        return game_id, game

    def join_player(self, game_id, sid, player_id=None, player_name=None, faction_id=None):
        game = self.games.get(game_id)
        if not game:
            return None, "Game not found"

        # Logic for reconnecting or new player...
        # This part requires socket interaction which we'll handle in the socket handler mostly, 
        # but the state update should be here.
        # For now, let's keep the heavy logic in the socket handler but move state mutations here eventually.
        # To avoid over-engineering in one step, I'll expose the raw game object for now 
        # via get_game() and let the socket handler manipulate it, then call save_games().
        return game

# Create a global instance
game_manager = GameManager()

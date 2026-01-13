from flask import Blueprint, render_template
from server.services.game_manager import game_manager

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def index():
    return render_template("index.html")

@main_bp.route("/join/<game_id>")
def join_game_page(game_id):
    game = game_manager.get_game(game_id)
    if not game:
        return "Game not found", 404
    return render_template("join_game.html", game_id=game_id, factions=game["factions"])

@main_bp.route("/player/<game_id>/<player_id>")
def player_controller(game_id, player_id):
    game = game_manager.get_game(game_id)
    if game and player_id in game["players"]:
        return render_template(
            "player.html",
            game_id=game_id,
            player_id=player_id,
            global_stats=game["global_stats"],
            current_round=game["current_round"],
        )
    return "Game or Player not found", 404

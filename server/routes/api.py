from flask import Blueprint, request, jsonify, send_file
import tempfile
import os
import json
from server.services.tts_service import tts_service
from server.services.llm.narrator import narrator

api_bp = Blueprint('api', __name__)

@api_bp.route("/tts", methods=["POST"])
def tts():
    if not tts_service.model:
        return jsonify({"error": "TTS service not configured"}), 500

    text = request.json.get("text")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    temp_audio_file = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
            temp_audio_file = tmpfile.name

        tts_service.generate_audio(text, temp_audio_file)

        return send_file(
            temp_audio_file,
            mimetype='audio/wav',
            as_attachment=False,
            download_name='speech.wav',
            max_age=0
        )
    except Exception as e:
        print(f"[TTS] Error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if temp_audio_file and os.path.exists(temp_audio_file):
            os.remove(temp_audio_file)

@api_bp.route("/dilemma")
def dilemma():
    # Debug route
    game_state_for_gemini = {
        "current_round": 1,
        "global_stats": {"Stability": 50, "Economy": 50, "Faith": 50},
        "event_history": [],
        "player_statements": [],
        "previous_dilemma_outcome": None,
    }
    if narrator.generate_dilemma(game_state_for_gemini):
        # Narrator service writes to dilemma.json
        with open("dilemma.json", "r") as f:
            generated_dilemma = json.load(f)
    else:
        generated_dilemma = {"error": "Failed to generate dilemma"}
    return jsonify(generated_dilemma)

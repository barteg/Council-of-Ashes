
import json
import sys
import os

# Add current directory to path so we can import story_data
sys.path.append(os.getcwd())

try:
    from story_data import (
        EVENT_GENERATION_PROMPT_STATIC,
        OUTCOME_NARRATIVE_PROMPT_STATIC,
        STATEMENT_EVALUATION_PROMPT_STATIC
    )
    print("Successfully imported story_data.")
except Exception as e:
    print(f"Error importing story_data: {e}")
    sys.exit(1)

def test_event_prompt():
    print("\n--- Testing EVENT_GENERATION_PROMPT_STATIC ---")
    game_state = {"test": "data"}
    try:
        formatted = EVENT_GENERATION_PROMPT_STATIC.format(
            game_state_json=json.dumps(game_state)
        )
        print("Success! Length:", len(formatted))
    except Exception as e:
        print(f"FAILED: {e}")

def test_outcome_prompt():
    print("\n--- Testing OUTCOME_NARRATIVE_PROMPT_STATIC ---")
    data = {
        "game_state_json": "{}",
        "chosen_policy": "Policy",
        "policy_effects_json": "{}",
        "faction_votes_json": "{}",
        "player_statements_json": "{}",
        "player_comments_json": "{}"
    }
    try:
        formatted = OUTCOME_NARRATIVE_PROMPT_STATIC.format(**data)
        print("Success! Length:", len(formatted))
    except Exception as e:
        print(f"FAILED: {e}")

def test_statement_prompt():
    print("\n--- Testing STATEMENT_EVALUATION_PROMPT_STATIC ---")
    data = {
        "game_state_json": "{}",
        "player_statements_json": "{}"
    }
    try:
        formatted = STATEMENT_EVALUATION_PROMPT_STATIC.format(**data)
        print("Success! Length:", len(formatted))
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_event_prompt()
    test_outcome_prompt()
    test_statement_prompt()

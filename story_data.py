import json
import google.generativeai as genai

# Static part of the Gemini prompt for event generation
EVENT_GENERATION_PROMPT_STATIC = """Jesteś narratorem w grze „Rada Popiołów”. Twoim zadaniem jest tworzenie krótkich, klimatycznych dylematów.

## Zasady (Ściśle przestrzegaj):
1.  **Długość:** Opis sytuacji (`description`) na max 3-4 zdania.
2.  **Klimat:** Dark fantasy. Używaj opisów sensorycznych (zapach, dźwięk, chłód).
3.  **Statystyki:** NIGDY nie używaj liczb. Opisuj stan królestwa przez wydarzenia (np. "Głód zagląda w oczy" zamiast "Ekonomia niska").
4.  **Dylemat:** Stwórz nieoczywisty wybór. Unikaj prostego "dobro vs zło".

## Wejście:
```json
{game_state_json}
```

## Format wyjściowy (JSON):
```json
{{
  "id": "event_id",
  "title": "Krótki Tytuł",
  "description": "Opis dylematu (max 3-4 zdania). Skup się na atmosferze i konkretnym problemie.",
  "image": "/static/images/placeholder.png",
  "narrative_prompt": "Jedno zdanie podsumowania kończące się pytaniem do Rady."
}}
```

## Interpretacja Statystyk (0-100) - Użyj jako inspiracji, NIE CYTUJ LICZB:
*   **0-20:** Katastrofa, upadek.
*   **21-40:** Kryzys, bieda, niepokoje.
*   **41-60:** Stabilizacja, drobne problemy.
*   **61-80:** Rozwój, dobrobyt.
*   **81-100:** Potęga, złoty wiek.
"""

# Static part of the Gemini prompt for outcome narrative generation
OUTCOME_NARRATIVE_PROMPT_STATIC = """Jesteś narratorem w grze „Rada Popiołów”. Opisz skutki decyzji Rady.

## Zasady (Ściśle przestrzegaj):
1.  **Długość:** Maksymalnie 3-4 zdania. Bądź zwięzły.
2.  **Cytaty:** Zacytuj zwycięskie `statement` i wymień imię autora.
3.  **Reakcje:** Odnieś się do 1-2 `player_comments`, wymieniając imiona graczy.
4.  **Abstrakcja Statystyk:** NIGDY nie używaj liczb. Opisz zmiany obrazowo (np. wzrost Wiary -> "Świątynie pękają w szwach", spadek Ekonomii -> "Na targu brakuje chleba").
5.  **Świat:** Dodaj jedno zdanie dające wgląd w życie zwykłych ludzi lub tło fabularne świata (backstory).

## Wejście:
```json
{{
  "game_state": {game_state_json},
  "chosen_policy": "{chosen_policy}",
  "policy_effects": {policy_effects_json},
  "faction_votes": {faction_votes_json},
  "player_statements": {player_statements_json},
  "player_comments": {player_comments_json}
}}
```

## Format wyjściowy (JSON):
```json
{{
  "outcome_narrative": "Tekst narracji spełniający powyższe zasady.",
  "next_event_hint": "Krótka, tajemnicza zapowiedź przyszłych problemów.",
  "kingdom_status_summary": "Jedno zdanie o nastrojach w królestwie (np. 'Widmo głodu zagląda ludziom w oczy')."
}}
```
"""

# --- Gemini API Interaction ---
def call_gemini_for_outcome_narrative(model, game_state, chosen_policy, policy_effects, faction_votes, player_statements, player_comments):
    prompt = f"""{OUTCOME_NARRATIVE_PROMPT_STATIC.format(
        game_state_json=json.dumps(game_state, indent=2),
        chosen_policy=chosen_policy,
        policy_effects_json=json.dumps(policy_effects, indent=2),
        faction_votes_json=json.dumps(faction_votes, indent=2),
        player_statements_json=json.dumps(player_statements, indent=2),
        player_comments_json=json.dumps(player_comments, indent=2)
    )}"""
    try:
        response = model.generate_content(prompt)
        print(f"[DEBUG] Gemini Response Object: {response}")
        if not response.candidates:
            print("[DEBUG] No candidates in response. Checking prompt feedback.")
            print(f"[DEBUG] Prompt Feedback: {response.prompt_feedback}")
            return False

        candidate = response.candidates[0]
        print(f"[DEBUG] Candidate: {candidate}")
        if candidate.finish_reason != 'STOP':
            print(f"[DEBUG] Generation finished with reason: {candidate.finish_reason}")

        print(f"[DEBUG] Safety Ratings: {candidate.safety_ratings}")

        gemini_text = candidate.content.parts[0].text
        print(f"[DEBUG] Gemini Outcome Raw Response Text: {gemini_text}")
        
        # Try to find markdown JSON block
        json_block_start = gemini_text.find('```json')
        json_block_end = gemini_text.rfind('```')
        
        if json_block_start != -1 and json_block_end != -1 and json_block_start < json_block_end:
            json_string = gemini_text[json_block_start + 7:json_block_end].strip()
        else:
             # Fallback: Assume the entire text is JSON, or try to find the first { and last }
            json_start = gemini_text.find('{')
            json_end = gemini_text.rfind('}')
            if json_start != -1 and json_end != -1:
                json_string = gemini_text[json_start:json_end+1]
            else:
                json_string = gemini_text

        try:
            # Validate JSON before writing
            parsed_json = json.loads(json_string)
            with open("outcome.json", "w", encoding="utf-8") as f:
                json.dump(parsed_json, f, ensure_ascii=False, indent=2)
            return True
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON from Gemini outcome response: {e}")
            print(f"[ERROR] Malformed JSON string: {json_string}")
            return False
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return False


# Static part of the Gemini prompt for statement evaluation
STATEMENT_EVALUATION_PROMPT_STATIC = """Jesteś Mistrzem Gry w „Radzie Popiołów”. Przetłumacz oświadczenie gracza na politykę i efekty.

## Zasady:
1.  **Polityka:** Zwięzła nazwa (np. "Dekret o racjonowaniu").
2.  **Efekty:** Liczbowe zmiany (-20 do +20) dla Stability, Economy, Faith. Logiczne i wynikające z treści.
3.  **Narracja:** Krótki opis skutków (1-2 zdania). BEZ LICZB w tekście. Użyj opisu świata (np. "Ludzie protestują").

## Wejście:
```json
{{
  "game_state": {game_state_json},
  "player_statements": {player_statements_json}
}}
```

## Format wyjściowy (JSON):
```json
{{
  "chosen_policy": "Nazwa polityki (1 zdanie)",
  "effects": {{
    "Stability": 0,
    "Economy": 0,
    "Faith": 0
  }},
  "narrative_consequence": "Opis skutków (max 2 zdania, bez liczb)."
}}
```
"""

def evaluate_player_statements_with_gemini(model, game_state, player_statements):
    prompt = f"""{STATEMENT_EVALUATION_PROMPT_STATIC.format(
        game_state_json=json.dumps(game_state, indent=2),
        player_statements_json=json.dumps(player_statements, indent=2)
    )}"""
    try:
        response = model.generate_content(prompt)
        print(f"[DEBUG] Gemini Response Object (Statement Evaluation): {response}")
        if not response.candidates:
            print("[DEBUG] No candidates in response. Checking prompt feedback.")
            print(f"[DEBUG] Prompt Feedback: {response.prompt_feedback}")
            return None

        candidate = response.candidates[0]
        print(f"[DEBUG] Candidate (Statement Evaluation): {candidate}")
        if candidate.finish_reason != 'STOP':
            print(f"[DEBUG] Generation finished with reason: {candidate.finish_reason}")

        print(f"[DEBUG] Safety Ratings (Statement Evaluation): {candidate.safety_ratings}")

        gemini_text = candidate.content.parts[0].text
        print(f"[DEBUG] Gemini Statement Evaluation Raw Response Text: {gemini_text}")
        
        # Try to find markdown JSON block
        json_block_start = gemini_text.find('```json')
        json_block_end = gemini_text.rfind('```')
        
        if json_block_start != -1 and json_block_end != -1 and json_block_start < json_block_end:
            json_string = gemini_text[json_block_start + 7:json_block_end].strip()
        else:
             # Fallback: Assume the entire text is JSON, or try to find the first { and last }
            json_start = gemini_text.find('{')
            json_end = gemini_text.rfind('}')
            if json_start != -1 and json_end != -1:
                json_string = gemini_text[json_start:json_end+1]
            else:
                json_string = gemini_text

        try:
            return json.loads(json_string)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON from Gemini statement evaluation response: {e}")
            print(f"[ERROR] Malformed JSON string: {json_string}")
            return None
    except Exception as e:
        print(f"Error calling Gemini API for statement evaluation: {e}")
        return None

def generate_dilemma_with_gemini(model, game_state):
    prompt = f"""{EVENT_GENERATION_PROMPT_STATIC.format(
        game_state_json=json.dumps(game_state, indent=2)
    )}"""
    try:
        response = model.generate_content(prompt)
        print(f"[DEBUG] Gemini Response Object: {response}")
        if not response.candidates:
            print("[DEBUG] No candidates in response. Checking prompt feedback.")
            print(f"[DEBUG] Prompt Feedback: {response.prompt_feedback}")
            return False

        candidate = response.candidates[0]
        print(f"[DEBUG] Candidate: {candidate}")
        if candidate.finish_reason != 'STOP':
            print(f"[DEBUG] Generation finished with reason: {candidate.finish_reason}")

        print(f"[DEBUG] Safety Ratings: {candidate.safety_ratings}")

        gemini_text = candidate.content.parts[0].text
        print(f"[DEBUG] Gemini Dilemma Raw Response Text: {gemini_text}")
        
        # Try to find markdown JSON block
        json_block_start = gemini_text.find('```json')
        json_block_end = gemini_text.rfind('```')
        
        if json_block_start != -1 and json_block_end != -1 and json_block_start < json_block_end:
            json_string = gemini_text[json_block_start + 7:json_block_end].strip()
        else:
             # Fallback: Assume the entire text is JSON, or try to find the first { and last }
            json_start = gemini_text.find('{')
            json_end = gemini_text.rfind('}')
            if json_start != -1 and json_end != -1:
                json_string = gemini_text[json_start:json_end+1]
            else:
                json_string = gemini_text

        print(f"[DEBUG] Extracted JSON string: {json_string!r}")

        try:
            # Attempt to parse the JSON string to validate it
            parsed_json = json.loads(json_string)
            print("[DEBUG] JSON parsed successfully.")
            with open("dilemma.json", "w", encoding="utf-8") as f:
                json.dump(parsed_json, f, ensure_ascii=False, indent=2) # Write validated JSON
            print("[DEBUG] JSON written to file.")
            return True
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON from Gemini response: {e}")
            print(f"[ERROR] Malformed JSON string: {json_string}")
            return False
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return False


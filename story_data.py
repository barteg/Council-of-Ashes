import json
import google.generativeai as genai

# Static part of the Gemini prompt for event generation
EVENT_GENERATION_PROMPT_STATIC = """Jesteś narratorem w grze „Rada Popiołów”. Twoim zadaniem jest tworzenie krótkich, konkretnych dylematów politycznych w świecie Dark Fantasy.

## Zasady (Ściśle przestrzegaj):
1.  **Długość:** Opis sytuacji (`description`) na max 3-4 zdania.
2.  **Styl:** Konkretny, surowy, kronikarski. Unikaj poezji i kwiecistego języka. Skup się na faktach i zagrożeniach.
3.  **Klimat:** Dark fantasy (brud, chłód, głód, korupcja).
4.  **Statystyki:** NIGDY nie używaj liczb. Opisuj stan królestwa przez widoczne skutki (np. "Spichlerze świecą pustkami" zamiast "Niska Ekonomia").
5.  **Dylemat:** Stwórz realny problem wymagający decyzji.

## Wejście:
```json
{game_state_json}
```

## Format wyjściowy (JSON):
```json
{{
  "id": "event_id",
  "title": "Krótki, Konkretny Tytuł",
  "description": "Opis problemu (max 3-4 zdania). Opisz co się dzieje, kto cierpi i co grozi królestwu.",
  "image": "/static/images/placeholder.png",
  "narrative_prompt": "Jedno zdanie podsumowujące problem, kończące się pytaniem do Rady."
}}
```

## Interpretacja Statystyk (0-100) - Użyj jako tła:
*   **0-20:** Katastrofa, głód, anarchia.
*   **21-40:** Bieda, zamieszki, strach.
*   **41-60:** Stabilność, przeciętność.
*   **61-80:** Rozwój, bogactwo.
*   **81-100:** Potęga, dominacja.
"""

# Static part of the Gemini prompt for outcome narrative generation
OUTCOME_NARRATIVE_PROMPT_STATIC = """Jesteś narratorem w grze „Rada Popiołów”. Twoim zadaniem jest opisanie skutków decyzji Rady w sposób logiczny i gramatycznie poprawny.

## Instrukcje Językowe (PRIORYTET):
1.  Pisz w języku **POLSKIM**. Dbaj o poprawną odmianę (przypadki, rodzaje).
2.  Używaj **krótkich, prostych zdań**. Lepiej napisać prosto i poprawnie, niż skomplikowanie i z błędami.
3.  Nie wymyślaj słów (nie używaj "situación", "niszczeniona"). Pisz naturalnie.

## Struktura Historii (Napisz płynny tekst w 5 krokach):
1.  **Krok 1 (Kontekst):** Opisz, jak frakcja zwycięzcy wprowadza zmiany (np. "Kupcy przekupili urzędników...", "Kapłani wyszli na ulice...", "Gwardia użyła siły...").
2.  **Krok 2 (Przyczyna):** Napisz wprost: "Stało się to po słowach [Name], który rzekł: '[Statement]'."
3.  **Krok 3 (Reakcja):** Zacytuj komentarz innego gracza: "W odpowiedzi [Name] stwierdził: '[Comment]'." (Jeśli komentarz jest pusty, napisz: "Rada przyjęła to milczeniem.").
4.  **Krok 4 (Twist):** Dodaj jeden krótki, zaskakujący skutek tej decyzji.
5.  **Krok 5 (Skutek):** Opisz stan królestwa (bieda, strach, bunty) bez używania liczb.

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
  "outcome_narrative": "Tu wpisz historię. Pamiętaj o poprawnej polszczyźnie.",
  "next_event_hint": "Krótka zapowiedź zagrożenia...",
  "kingdom_status_summary": "Krótki opis nastrojów..."
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
STATEMENT_EVALUATION_PROMPT_STATIC = """Jesteś Mistrzem Gry w „Radzie Popiołów”. Twoim zadaniem jest urzeczywistnienie wybranego oświadczenia (statement), biorąc pod uwagę KTO je wygłosił.

## 1. Interpretacja Frakcyjna (JAK to się dzieje?):
*   **Syndykat Kupiecki:** Rynek, pieniądz, przekupstwo, zmiany cen.
*   **Wysokie Kapłaństwo:** Wiara, omeny, cuda, histeria, klątwy.
*   **Gwardia Królewska:** Prawo, siła, wojsko, aresztowania.

## 2. Reguła Kanonu (Dosłowność):
*   **Bierz tekst gracza DOSŁOWNIE.**
*   Jeśli gracz pisze wulgarnie lub absurdalnie -> To się dzieje naprawdę.
*   Nie cenzuruj.

## 3. Bezpieczeństwo:
*   Jedyny wyjątek: "Koniec Świata" (interpretuj lokalnie, np. pożar).

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
  "chosen_policy": "Tu wpisz nazwę wydarzenia (krótko)",
  "effects": {{
    "Stability": 0,
    "Economy": 0,
    "Faith": 0
  }},
  "narrative_consequence": "Tu wpisz opis skutków (zgodnie ze stylem frakcji)..."
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


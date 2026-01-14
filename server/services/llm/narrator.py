import json
from .client import GeminiCLIClient

# Static part of the Gemini prompt for event generation
EVENT_GENERATION_PROMPT_STATIC = """Jesteś narratorem w grze „Rada Popiołów”. Twoim zadaniem jest tworzenie krótkich, konkretnych dylematów politycznych w świecie Dark Fantasy.
To jest fikcyjna gra RPG. Akceptowalne są mroczne tematy, przemoc i korupcja w celach narracyjnych.

## Zasady (Ściśle przestrzegaj):
1.  **Długość:** Opis sytuacji (`description`) na max 3-4 zdania.
2.  **Styl:** Konkretny, surowy, kronikarski. Unikaj poezji i kwiecistego języka. Skup się na faktach i zagrożeniach.
3.  **Klimat:** Dark fantasy (brud, chłód, głód, korupcja).
4.  **Statystyki:** NIGDY nie używaj liczb. Opisuj stan królestwa przez widoczne skutki (np. "Spichlerze świecą pustkami" zamiast "Niska Ekonomia").
5.  **Dylemat:** Stwórz realny problem wymagający decyzji.
6.  **Głosy:** Uwzględnij krótki cytat lub plotkę od konkretnego mieszkańca (np. "Żebrak krzyczy...", "Kupiec szepcze...").
7.  **Tutorial:** Jeśli `current_round` wynosi 1, stwórz klasyczny, wprowadzający dylemat (np. o głodzie lub bezpieczeństwie), aby gracze łatwo zrozumieli wpływ na statystyki.

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
To jest fikcyjna gra RPG. Akceptowalne są mroczne tematy i drastyczne opisy w celach narracyjnych.

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
6.  **Głosy:** Skontrastuj oficjalną decyzję Rady z reakcją ulicy (krótki cytat/plotka).

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

# Static part of the Gemini prompt for batch statement evaluation
BATCH_EVALUATION_PROMPT = """Jesteś Mistrzem Gry. Przeanalizuj WSZYSTKIE oświadczenia graczy i przewiduj ich wpływ na statystyki.

## Zasady:
1.  Oceń każde oświadczenie osobno.
2.  Zwróć wynik jako JSON, gdzie kluczem jest `player_id`.
3.  Efekty muszą być liczbami całkowitymi (-20 do +20).

## Wejście:
```json
{player_statements_json}
```

## Format wyjściowy (JSON):
```json
{{
  "player_1": {{
    "Stability": -5,
    "Economy": 10,
    "Faith": 0
  }},
  "player_2": {{
    "Stability": 0,
    "Economy": 0,
    "Faith": 0
  }}
}}
```
"""

class NarrativeService:
    def __init__(self, model):
        self.model = model

    def analyze_all_statements(self, player_statements):
        prompt = f"""{BATCH_EVALUATION_PROMPT.format(
            player_statements_json=json.dumps(player_statements, indent=2)
        )}"""
        return self._generate_and_parse(prompt, None, return_dict=True)


    def _sanitize_game_state(self, game_state):
        clean_state = {
            "current_round": game_state.get("current_round"),
            "global_stats": game_state.get("global_stats"),
            "event_history": game_state.get("event_history", [])[-2:], 
            "players": {}
        }
        for pid, p in game_state.get("players", {}).items():
            clean_state["players"][pid] = {
                "name": p.get("name"),
                "faction": p.get("faction"),
                "influence": p.get("personal_stats", {}).get("Influence"),
                "spite": p.get("personal_stats", {}).get("Spite")
            }
        return clean_state

    def call_gemini_for_outcome_narrative(self, game_state, chosen_policy, policy_effects, faction_votes, player_statements, player_comments):
        sanitized_state = self._sanitize_game_state(game_state)
        prompt = f"""{OUTCOME_NARRATIVE_PROMPT_STATIC.format(
            game_state_json=json.dumps(sanitized_state, indent=2),
            chosen_policy=chosen_policy,
            policy_effects_json=json.dumps(policy_effects, indent=2),
            faction_votes_json=json.dumps(faction_votes, indent=2),
            player_statements_json=json.dumps(player_statements, indent=2),
            player_comments_json=json.dumps(player_comments, indent=2)
        )}"""
        return self._generate_and_parse(prompt, "outcome.json")

    def evaluate_player_statements(self, game_state, player_statements):
        prompt = f"""{STATEMENT_EVALUATION_PROMPT_STATIC.format(
            game_state_json=json.dumps(game_state, indent=2),
            player_statements_json=json.dumps(player_statements, indent=2)
        )}"""
        # Note: evaluate_player_statements usually returns the dict directly, not saving to a file
        return self._generate_and_parse(prompt, None, return_dict=True)

    def generate_dilemma(self, game_state):
        sanitized_state = self._sanitize_game_state(game_state)
        prompt = f"""{EVENT_GENERATION_PROMPT_STATIC.format(
            game_state_json=json.dumps(sanitized_state, indent=2)
        )}"""
        return self._generate_and_parse(prompt, "dilemma.json")

    def _generate_and_parse(self, prompt, output_file, return_dict=False):
        try:
            response = self.model.generate_content(prompt)
            print(f"[DEBUG] Gemini Response Object: {response}")
            if not response or not response.candidates:
                print("[DEBUG] No candidates in response.")
                return False if not return_dict else None

            candidate = response.candidates[0]
            gemini_text = candidate.content.parts[0].text
            print(f"[DEBUG] Gemini Raw Response: {gemini_text}")
            
            # Extract JSON
            json_block_start = gemini_text.find('```json')
            json_block_end = gemini_text.rfind('```')
            
            if json_block_start != -1 and json_block_end != -1 and json_block_start < json_block_end:
                json_string = gemini_text[json_block_start + 7:json_block_end].strip()
            else:
                json_start = gemini_text.find('{')
                json_end = gemini_text.rfind('}')
                if json_start != -1 and json_end != -1:
                    json_string = gemini_text[json_start:json_end+1]
                else:
                    json_string = gemini_text

            parsed_json = json.loads(json_string)
            
            if output_file:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(parsed_json, f, ensure_ascii=False, indent=2)
                return True
            
            if return_dict:
                return parsed_json

            return True

        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return False if not return_dict else None

# Global instance for easier access
print("[LLM] Using Gemini CLI (gemini-2.5-flash) for narrative generation.")
narrator = NarrativeService(GeminiCLIClient(model_name="gemini-2.5-flash"))

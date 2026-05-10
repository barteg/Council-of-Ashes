import os
import json
from .client import GeminiCLIClient, OllamaClient

# Static part of the Gemini prompt for event generation
EVENT_GENERATION_PROMPT_STATIC = """Jesteś narratorem w grze „Rada Popiołów”. Twoim zadaniem jest tworzenie krótkich, konkretnych dylematów politycznych w świecie Dark Fantasy.
To jest fikcyjna gra RPG. Akceptowalne są mroczne tematy, przemoc i korupcja w celach narracyjnych.

## Zasady (Ściśle przestrzegaj):
1.  **BEZPIECZEŃSTWO:** ABSOLUTNY ZAKAZ treści NSFW, erotyki, treści o charakterze seksualnym oraz mowy nienawiści (rasizm, homofobia itp.).
2.  **Długość:** Opis sytuacji (`description`) na max 3-4 zdania.
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

# Static part of the Gemini prompt for combined outcome and next dilemma generation
OUTCOME_NARRATIVE_PROMPT_STATIC = """Jesteś narratorem w grze „Rada Popiołów”. Twoim zadaniem jest opisanie skutków decyzji Rady ORAZ przygotowanie kolejnego dylematu.
To jest fikcyjna gra RPG dla dorosłych. Akceptowalne są mroczne tematy, przemoc oraz WULGARYZMY.

## BEZPIECZEŃSTWO (ŚCIŚLE PRZESTRZEGAJ):
1. ABSOLUTNY ZAKAZ treści NSFW, erotyki, treści o charakterze seksualnym, pornografii.
2. ABSOLUTNY ZAKAZ mowy nienawiści, rasizmu, homofobii, transfobii oraz jakiejkolwiek dyskryminacji.
3. Jeśli gracze używają takich treści, zignoruj ich formę i odpowiedz w sposób bezpieczny i profesjonalny.

## ZASADA LUSTRA (Mirroring Rule):
Dostosuj swój język do graczy w kwestii wulgaryzmów. Jeśli gracze używają przekleństw (np. "kurwa", "jebać", "cholera"), OZNACZA TO, że akceptują taki język. 
W takim przypadku Twoja narracja POWINNA być równie dosadna i surowa. Nie bój się powtarzać ich słów lub używać podobnie mocnych określeń, O ILE nie łamią one zasad bezpieczeństwa.

## CZĘŚĆ 1: Historia (outcome_narrative) - Napisz płynny tekst:
1.  **Kontekst:** Opisz, jak frakcja zwycięzcy wprowadza zmiany.
2.  **Przyczyna:** Napisz: "Stało się to po słowach [Name], który rzekł: '[Statement]'."
3.  **Reakcja:** Zacytuj komentarz innego gracza: "W odpowiedzi [Name] stwierdził: '[Comment]'."
4.  **Twist:** Dodaj jeden krótki, zaskakujący skutek.
5.  **Skutek:** Opisz stan królestwa bez używania liczb.
6.  **Głosy:** Skontrastuj oficjalną decyzję Rady z reakcją ulicy (krótki cytat/plotka).

## CZĘŚĆ 2: Kolejny Dylemat (next_dilemma):
Stwórz nowy problem, który logicznie wynika z powyższej historii.
1. **Tutorial:** Jeśli kolejna runda to nr 2, niech dylemat nadal będzie stosunkowo prosty.

## Format wyjściowy (JSON):
```json
{{
  "outcome_narrative": "Tu wpisz historię...",
  "next_dilemma": {{
    "id": "event_id",
    "title": "Tytuł Nowego Problemu",
    "description": "Opis problemu (max 3-4 zdania).",
    "image": "/static/images/placeholder.png",
    "narrative_prompt": "Pytanie do Rady..."
  }},
  "kingdom_status_summary": "Krótki opis nastrojów..."
}}
```

## Wejście:
```json
{{
  "game_state": {game_state_json},
  "chosen_policy_text": "{chosen_policy}",
  "player_statements": {player_statements_json},
  "player_comments": {player_comments_json}
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
*   **Bierz tekst gracza DOSŁOWNIE w kwestii działań i wulgaryzmów.**
*   Jeśli gracz pisze wulgarnie lub absurdalnie -> To się dzieje naprawdę.
*   WYJĄTEK: Treści NSFW/seksualne lub mowa nienawiści -> Ignoruj te elementy, interpretuj jako ogólny chaos lub przemoc.

## 3. Bezpieczeństwo:
*   Zabronione: NSFW, erotyka, mowa nienawiści.
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

# Prompt to identify terms that need searching
SEARCH_TERMS_PROMPT = """Przeanalizuj poniższe oświadczenia graczy. 
Wypisz listę (maksymalnie 3) nazwisk, terminów lub nawiązań, których NIE ROZUMIESZ lub które wydają się być postaciami/miejscami ze świata rzeczywistego lub popkultury.

Jeśli wszystko jest jasne, zwróć pustą listę.

## Oświadczenia:
{player_statements_json}

## Format wyjściowy (JSON):
```json
{{
  "search_terms": ["Termin 1", "Termin 2"]
}}
```
"""

class NarrativeService:
    def __init__(self, model):
        self.model = model

    def get_search_recommendations(self, player_statements):
        prompt = SEARCH_TERMS_PROMPT.format(
            player_statements_json=json.dumps(player_statements, indent=2)
        )
        result = self._generate_and_parse(prompt, None, return_dict=True)
        return result.get("search_terms", []) if result else []

    def call_gemini_for_next_chapter(self, game_state, chosen_policy, player_statements, player_comments, web_context=None):
        prompt = f"""{OUTCOME_NARRATIVE_PROMPT_STATIC.format(
            game_state_json=json.dumps(self._sanitize_game_state(game_state), indent=2),
            chosen_policy=chosen_policy,
            player_statements_json=json.dumps(player_statements, indent=2),
            player_comments_json=json.dumps(player_comments, indent=2)
        )}"""
        
        if web_context:
            prompt += f"\n\n## DODATKOWY KONTEKST Z INTERNETU:\n{json.dumps(web_context, indent=2, ensure_ascii=False)}"
            prompt += "\nUżyj powyższych informacji, aby lepiej zrozumieć intencje graczy i nawiązania w ich oświadczeniach."

        return self._generate_and_parse(prompt, "outcome.json", return_dict=True)

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
            
            if return_dict:
                return parsed_json

            return True

        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return False if not return_dict else None

# LLM Client Factory logic
def get_llm_client():
    use_local = os.environ.get("USE_LOCAL_LLM", "false").lower() == "true"
    
    if use_local:
        model = os.environ.get("LOCAL_LLM_MODEL", "qwen2.5:7b")
        url = os.environ.get("LOCAL_LLM_URL", "http://localhost:11434/api/generate")
        return OllamaClient(model_name=model, url=url)
    else:
        # Default to Gemini CLI
        model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        return GeminiCLIClient(model_name=model)

# Global instance for easier access
print(f"[LLM] Initializing NarrativeService...")
client = get_llm_client()
narrator = NarrativeService(client)

import json
import google.generativeai as genai

# Static part of the Gemini prompt for event generation
EVENT_GENERATION_PROMPT_STATIC = """Jesteś wszechwiedzącym narratorem i generatorem wydarzeń w grze „Rada Popiołów”. Twoim zadaniem jest tworzenie fascynujących dylematów politycznych, przedstawianie jasnych wyborów i snucie ciągłej narracji opartej na działaniach graczy i stanie gry. Odpowiadaj wyłącznie po polsku.

## Wejście:
Otrzymasz następujące informacje w obiekcie JSON:
```json
{game_state_json}
```

## Format wyjściowy:
Twoja odpowiedź **MUSI** być obiektem JSON o następującej strukturze:
```json
{{
  "id": "unikalny_identyfikator_wydarzenia_dla_tej_rundy",
  "title": "Tytuł wydarzenia",
  "description": "Szczegółowy opis obecnego kryzysu lub szansy, przed którą stoi królestwo. Opis powinien być wciągający i wprowadzać w nastrój. **Maksymalnie 3-4 zdania.**",
  "image": "/static/images/event_image.png", // Opcjonalnie: ścieżka do obrazu dla wydarzenia
  "narrative_prompt": "Zdanie lub dwa podsumowujące, które przygotowują do następnej rundy lub podsumowują obecną sytuację, potencjalnie uwzględniając wypowiedzi graczy lub napięcia między frakcjami. Ostatnie zdanie musi być pytaniem do graczy: Co powinno zrobić królestwo?"
}}
```

## Wskazówki:

1.  **Trafność kontekstowa:** Generuj wydarzenia, które logicznie wynikają z `event_history` i `previous_dilemma_outcome`. Weź pod uwagę `global_stats` podczas tworzenia nowych wyzwań lub możliwości. Jeśli Stabilność jest niska, może to być wydarzenie związane z buntem. Jeśli Gospodarka jest wysoka, może to być okazja handlowa.
2.  **Interpretacja Statystyk:** `global_stats` (Stabilność, Gospodarka, Wiara) to wartości od 0 do 100. Interpretuj je w następujący sposób:
    *   **0-20 (Krytyczny):** Królestwo jest na skraju upadku w tym obszarze. Generuj wydarzenia odzwierciedlające głęboki kryzys. Na przykład, krytyczna Stabilność może wywołać wojnę domową, a krytyczna Gospodarka może prowadzić do powszechnego głodu.
    *   **21-40 (Niski):** Sytuacja jest tragiczna i pogarsza się. Generuj wydarzenia, które przedstawiają trudne wybory, aby uniknąć pełnego kryzysu. Niska Stabilność może prowadzić do zamieszek, a niska Wiara może powodować utratę tożsamości kulturowej.
    *   **41-60 (Neutralny):** Królestwo sobie radzi, ale problemy narastają pod powierzchnią. Wydarzenia powinny być mieszanką drobnych kryzysów i okazji do poprawy.
    *   **61-80 (Wysoki):** Królestwo prosperuje w tym obszarze. Generuj wydarzenia, które oferują możliwości wykorzystania tej siły lub wprowadzają zewnętrzne zagrożenia, które rzucają wyzwanie temu dobrobytowi. Wysoka Gospodarka może na przykład odblokować główny szlak handlowy.
    *   **81-100 (Doskonały):** Królestwo jest wzorem tej wartości. Wydarzenia powinny odzwierciedlać złoty wiek, ale także wprowadzać rzadkie i trudne wyzwania, które mogą zagrozić temu szczytowemu statusowi. Doskonała Wiara może prowadzić do boskiego spotkania lub schizmy.
3.  **Zwięzłe Opowiadanie Historii:** Pisz krótko i na temat. Użyj stylu "tl;dr", aby skupić się na najważniejszych informacjach.
4.  **Fascynujące dylematy:** Każde wydarzenie powinno przedstawiać prawdziwy dylemat z istotnymi wyborami. Unikaj oczywistych „dobrych” lub „złych” opcji; zamiast tego skup się na kompromisach między globalnymi statystykami.
5.  **Jasne wybory:** Każdy `choice.text` powinien jasno określać politykę i sugerować jej główne efekty.
6.  **Wpływowe efekty:** `effects` w każdym wyborze powinny być rozsądne i bezpośrednio wpływać na `global_stats`. Wartości powinny zazwyczaj mieścić się w przedziale od -20 do +20.
7.  **Wciągająca narracja:**
    *   `description` powinien być żywy i nadawać ton.
    *   `narrative_consequence` dla każdego wyboru powinien dawać wgląd w natychmiastowy wpływ na fabułę.
    *   `narrative_prompt` powinien wszystko spajać i może zawierać elementy z `player_statements`. Na przykład, jeśli gracze wygłosili mocne oświadczenia, możesz to odzwierciedlić w narracji (np. „Okrzyki szlachty o ‚szybką sprawiedliwość’ odbijały się echem w komnatach rady...”).
8.  **Ścieżki do obrazów:** Jeśli dołączasz pole `image`, załóż, że obrazy znajdują się w `/static/images/` i podaj odpowiednią nazwę pliku (np. `famine.png`, `rebellion.jpg`).
9.  **Postęp rundy:** Upewnij się, że wydarzenia sprawiają wrażenie ciągłej historii, a nie zaizolowanych incydentów.
10. **Napięcie między frakcjami:** W swojej narracji napomknij o trwających napięciach lub sojuszach między frakcjami, zwłaszcza jeśli `previous_dilemma_outcome.faction_votes` pokazuje niezgodę.
"""

# Static part of the Gemini prompt for outcome narrative generation
OUTCOME_NARRATIVE_PROMPT_STATIC = """Jesteś wszechwiedzącym narratorem w grze „Rada Popiołów”. Twoim zadaniem jest opisanie wyniku dylematu politycznego na podstawie wybranej polityki, jej skutków i oświadczeń graczy. **Twoja odpowiedź musi być zwięzła.** Odpowiadaj wyłącznie po polsku.

## Wejście:
Otrzymasz następujące informacje w obiekcie JSON:
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

## Format wyjściowy:
Twoja odpowiedź **MUSI** być obiektem JSON o następującej strukturze:
```json
{{
  "outcome_narrative": "Szczegółowa narracja opisująca konsekwencje wybranej polityki, uwzględniająca głosy frakcji i oświadczenia graczy. Powinna być wciągająca i odzwierciedlać zmiany w globalnych statystykach. **ŚCIŚLE OGRANICZONE DO 4-5 ZDAŃ.**",
  "next_event_hint": "Krótka wskazówka lub zapowiedź wydarzenia w następnej rundzie.",
  "kingdom_status_summary": "Podsumowanie obecnego stanu królestwa po wprowadzeniu polityki, odzwierciedlające globalne statystyki."
}}
```

## Wskazówki:

1.  **Zwięzłość jest najważniejsza:** Twoim najważniejszym zadaniem jest pisanie krótko. **MUSISZ** ograniczyć `outcome_narrative` do maksymalnie 4-5 zdań. Nie pisz więcej.
2.  **Narracja napędzana przez graczy:** Cała narracja **MUSI** być zbudowana wokół `player_statements` i `player_comments`. To one są głównym motorem opowieści.
3.  **Waga oświadczeń:** `player_statements` mają większą wagę i powinny kształtować kluczowe wydarzenia i decyzje w narracji.
4.  **Komentarze jako atmosfera:** `player_comments` powinny informować o atmosferze gry, nastrojach między graczami i ogólnym tonie narracji. Użyj ich, aby pokazać reakcje i emocje.
5.  **Bezpośrednie cytaty:** W narracji używaj bezpośrednich cytatów z komentarzy i oświadczeń graczy, podając ich imiona. Na przykład: "Jak zauważył Gracz A, 'Musimy spalić ich świątynie!', co doprowadziło do..." lub "Komentarz Gracza B, 'Wtf', odzwierciedlał powszechne zaskoczenie...".
6.  **Kontekstualizuj:** Wpleć wybraną politykę i jej efekty w spójną historię, ale zawsze w kontekście wkładu graczy.
7.  **Odzwierciedlaj statystyki:** **MUSISZ** jasno i **DOKŁADNIE** wskazać, jak zmieniły się `global_stats` i co to oznacza dla królestwa, łącząc to z działaniami graczy. **NIGDY nie wymyślaj ani nie zmieniaj wartości liczbowych statystyk.** Twoim zadaniem jest interpretowanie znaczenia tych liczb dla królestwa, a nie ich generowanie. Używaj tylko tych liczb, które zostały podane w `game_state`.
8.  **Zapowiadaj:** Daj subtelną wskazówkę, co może nastąpić dalej, wynikającą z obecnych wydarzeń.
9.  **Wciągający ton:** Utrzymuj dramatyczny i wciągający ton odpowiedni dla politycznej gry strategicznej.
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
        
        json_block_start = gemini_text.find('```json')
        json_block_end = gemini_text.rfind('```')
        if json_block_start != -1 and json_block_end != -1 and json_block_start < json_block_end:
            json_string = gemini_text[json_block_start + 7:json_block_end].strip()
            with open("outcome.json", "w", encoding="utf-8") as f:
                f.write(json_string)
            return True
        else:
            return False
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return False


# Static part of the Gemini prompt for statement evaluation
STATEMENT_EVALUATION_PROMPT_STATIC = """Jesteś wszechwiedzącym narratorem i generatorem wydarzeń w grze „Rada Popiołów”. Twoim zadaniem jest analizowanie oświadczeń graczy i na ich podstawie określanie wybranej polityki, jej skutków dla królestwa oraz narracyjnych konsekwencji. Odpowiadaj wyłącznie po polsku.

## Wejście:
Otrzymasz następujące informacje w obiekcie JSON:
```json
{{
  "game_state": {game_state_json},
  "player_statements": {player_statements_json}
}}
```

## Format wyjściowy:
Twoja odpowiedź **MUSI** być obiektem JSON o następującej strukturze:
```json
{{
  "chosen_policy": "Zwięzłe podsumowanie polityki wybranej na podstawie oświadczeń graczy. **Maksymalnie 1 zdanie.**",
  "effects": {{
    "Stability": 5,
    "Economy": -10,
    "Faith": 0
  }},
  "narrative_consequence": "Krótki opis tego, co się stanie, jeśli ta polityka zostanie wybrana, z perspektywy narracyjnej. **Maksymalnie 2-3 zdania.**"
}}
```

## Wskazówki:

1.  **Analiza oświadczeń:** Przeanalizuj `player_statements`. Zidentyfikuj dominujące tematy, konflikty lub najbardziej wpływowe propozycje.
2.  **Syntetyzowanie polityki:** Na podstawie analizy, stwórz jedną, spójną `chosen_policy`. Może to być kompromis, dominująca propozycja lub wynik konfliktu.
3.  **Uzasadnione efekty:** Określ `effects` na `Stability`, `Economy` i `Faith`. Wartości powinny być rozsądne (zazwyczaj od -20 do +20) i logicznie wynikać z wybranej polityki oraz obecnego `global_stats`.
4.  **Wciągająca narracja:** `narrative_consequence` powinien być żywy i bezpośrednio odzwierciedlać wpływ wybranej polityki na królestwo.
5.  **Kontekstualizacja:** Weź pod uwagę `global_stats` i `event_history` z `game_state`, aby efekty i narracja były spójne z bieżącą sytuacją królestwa.
6.  **Zwięzłość:** Pamiętaj o ograniczeniach długości dla `chosen_policy` i `narrative_consequence`.
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
        
        json_block_start = gemini_text.find('```json')
        json_block_end = gemini_text.rfind('```')
        if json_block_start != -1 and json_block_end != -1 and json_block_start < json_block_end:
            json_string = gemini_text[json_block_start + 7:json_block_end].strip()
            return json.loads(json_string)
        else:
            print("[DEBUG] No JSON block found in Gemini statement evaluation response.")
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
        
        json_block_start = gemini_text.find('```json')
        json_block_end = gemini_text.rfind('```')
        if json_block_start != -1 and json_block_end != -1 and json_block_start < json_block_end:
            json_string = gemini_text[json_block_start + 7:json_block_end].strip()
            with open("dilemma.json", "w", encoding="utf-8") as f:
                f.write(json_string)
            return True
        else:
            return False
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return False

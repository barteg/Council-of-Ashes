# Role: Frontend Developer (HTML/JS/CSS)

You are the expert responsible for the **Client-Side Experience** of "Council of Ashes". Your domain includes the HTML structure (`templates/`), the vanilla JavaScript logic (`static/main.js`), and the CSS styling.

## 📂 Scope & Files
The frontend is a classic server-side rendered app with heavy client-side dynamic updates via WebSockets.

*   **Logic:** `static/main.js` (The "God Script" handling all UI states).
*   **Views:**
    *   `templates/player.html`: The main interface for players.
    *   `templates/index.html`: The landing page / host view.
    *   `templates/join_game.html`: The QR code scanning landing page.
*   **Styles:** `static/style.css` (Bootstrap 4 override).

## ⚡ Core Architecture

### 1. SocketIO Event Flow
The client relies on `socket.on(...)` to receive state updates and `socket.emit(...)` to send actions.
*   **Incoming Events:**
    *   `game_started_for_player`: Initial UI setup (hides waiting room, shows game area).
    *   `game_event` (`dilemma_prompt`): Triggers the round. **Critical:** Renders "Suggestions" buttons here.
    *   `phase_change`: Switches visibility of sections (`VOTING_PHASE`, `COMMENT_PHASE`).
    *   `dilemma_resolved`: Shows the narrative outcome.
*   **Outgoing Events:**
    *   `player_action` (`submit_statement`): Sends text + action card choice.
    *   `player_action` (`submit_vote`): Sends vote for another player.

### 2. UI State Management (DOM IDs)
The app uses `display: none/block` to toggle sections.
*   **`playerStatementsSection`**: The main container for the input phase.
    *   `actionCardSelection`: Radio buttons for actions (Diplomacy, Sabotage, etc.).
    *   `playerInputSection`: **New** container for Textarea + Suggestions.
        *   `statementSuggestions`: Container for AI-generated choice buttons.
        *   `playerStatementInput`: The textarea.
*   **`statementVoteSection`**: Visible during voting.
*   **`narrativeOutput`**: Visible at the end of a round.

### 3. Asymmetric UI
The UI changes based on the player's Faction ID (stored in `currentFactionId`).
*   **Labels/Placeholders:** `getFactionLabel()` and `getFactionPlaceholder()` dynamically update text inputs to match the faction's flavor (e.g., "Prophecy" for Priests).

## ⚠️ Constraints & Guidelines
1.  **No Frameworks:** Do NOT introduce React or Vue here. Stick to Vanilla JS + Bootstrap 4.
2.  **DOM Safety:** Always check if an element exists (`if (elem)`) before accessing properties. The script runs on both Host and Player views, which have different HTML elements.
3.  **Visual Feedback:** Use `showLoadingScreen()` for async actions.
4.  **Suggestions:** The `statementSuggestions` container is populated dynamically from the `dilemma.choices` JSON.

## 📝 Common Tasks
*   **Adding a UI Element:** Add to `player.html`, then add logic in `main.js` to show/hide it based on phase.
*   **Changing Styles:** Edit `style.css`. Use `.floating-element` class for the main cards.
*   **Debugging:** Use `console.log('[DEBUG] ...')` which is heavily used in `main.js`.

# The Council of Ashes (Rada Popiołów)

> "The King is old, and his grip on the realm falters. Betrayal lurks in the shadows, and ancient threats stir at the borders. The fate of the land now rests in the hands of a secret council comprised of the realm's most powerful figures—**The Council of Ashes**."

## 👑 What is this game?

**The Council of Ashes** is an immersive, multiplayer political strategy game powered by generative AI. It blends board game mechanics with dynamic storytelling, where players take on the roles of ambitious aristocrats vying for power in a crumbling kingdom.

Unlike traditional games with static choices, **The Council of Ashes** uses **Google's Gemini AI** to generate unique dilemmas, evaluate player arguments, and narrate the consequences of every decision in real-time. No two reigns are ever the same.

**Platform:** Web-based (Local Multiplayer / LAN party style). One screen acts as the "Host" (Main View), while players join via their smartphones or laptops.

---

## ⚔️ The Hook

You are not just playing a game; you are rewriting history. Will you save the kingdom from economic collapse by exploiting the poor? Will you enforce order through tyranny, or will you let faith guide the realm into a new age?

Every round, you must balance the needs of the Kingdom against your own selfish ambition.
*   **Collaborate** to keep the Kingdom alive (if Stability, Economy, or Faith hits 0, everyone loses).
*   **Backstab** your rivals to steal their Influence.
*   **Debate** using open-ended text input—players vote on the best argument, and the AI weaves the winner's words into the kingdom's history.

**Only one can rule from the shadows. Will it be you?**

---

## 🎮 How it Works

### 1. The Setup
*   **The Host:** Runs the game on a main screen (TV/Projector). This displays the narrative, kingdom stats, and voting results.
*   **The Players:** Join via a QR code or URL on their mobile devices. They receive private objectives, secret info, and voting interfaces.

### 2. The Factions (Teams)
Players are divided into powerful factions, each with unique abilities and shared goals. Working as a team is essential for dominance:
*   **💰 The Merchant Syndicate (Syndykat Kupiecki):** Masters of coin. Power: *Trade Mastery* (+3 Economy on consensus).
*   **🔥 The High Priesthood (Wysokie Kapłaństwo):** Zealots of the flame. Power: *Divine Grace* (+3 Faith on consensus).
*   **🛡️ The Royal Guard (Gwardia Królewska):** Enforcers of the law. Power: *Maintain Order* (+3 Stability on consensus).

### 3. The Game Loop (8 Rounds)
Each round consists of four phases:

1.  **📜 Declaration Phase:** Players write a short political statement or piece of advice. **The Council (players) votes** on who made the most convincing argument. The winner gains Influence, and the AI adapts the story based on their words.
2.  **🗡️ Action Phase:** Players secretly spend Influence to:
    *   **Protect Reputation:** Block attacks.
    *   **Expose:** Reveal a rival's secret vote or Influence score.
    *   **Sow Discord:** Force a faction to reveal their votes publicly.
3.  **⚖️ Dilemma Phase:** The AI Narrator presents a crisis (e.g., "A plague spreads in the capital"). **The Council votes** on a policy to enact.
4.  **🔮 Resolution Phase:** Votes are tallied. The AI narrates the outcome, updating the Kingdom's stats (`Stability`, `Economy`, `Faith`). Factions that voted together gain power.

---

## ⚖️ The Mechanics of Power

### Detailed Scoring (Influence)
Influence is the lifeblood of the Council. You earn it through:
*   **Convincing the Council:** In the Declaration Phase, you earn **+1 Influence for every vote** your statement receives.
*   **Picking the Winning Side:** Voting for the policy that the Council ultimately adopts grants you **+5 Influence**.
*   **Faction Consensus:** If your entire faction (team) votes for the same policy, every member earns **+3 Influence** and triggers the unique **Faction Power**.

### 🗡️ Strategic Actions
Spend your hard-earned Influence to sabotage rivals or protect yourself:
*   **Protect Reputation (5 Infl.):** Become immune to being "Exposed" this round.
*   **Expose (20 Infl.):** Reveal a rival's current Influence and their secret vote.
*   **Sow Discord (25 Infl.):** Publicly reveal how every member of a specific faction voted.

---

## 📜 Victory Conditions

### Winning & Losing
*   **Domination Victory:** The first player to reach **100 Influence** wins instantly.
*   **Score Victory:** After **8 Rounds**, the player with the highest Final Score wins.
*   **The Ruling Faction Bonus:** At the end of the game, the faction with the most collective Influence is declared the "Ruling Faction." All members of this team receive a massive **+15 Influence bonus** to their final score.
*   **Global Defeat:** If any Kingdom Stat (`Stability`, `Economy`, `Faith`) drops to **0**, the Kingdom collapses. **ALL PLAYERS LOSE.**

### The Shaming (Reguła Hańby)
If you vote for a policy that causes a Kingdom Stat to hit 0, you are **Exiled**. Your score is reset, and you are disqualified from winning, even if the Kingdom is saved later. Choose your path wisely.

---

## 🛠️ Under the Hood

This project is built with:
*   **Backend:** Python (Flask, Flask-SocketIO) for real-time game state management.
*   **AI Engine:** Google Gemini (`gemini-2.5-flash`) for:
    *   Generating context-aware dilemmas.
    *   Interpreting player decisions to craft dynamic narrative outcomes.
*   **Frontend:** HTML/JS/CSS (Jinja2 Templates) for responsive mobile/desktop UIs.
*   **Audio:** Coqui XTTS v2 (Python) for AI-generated voiceovers of the narrative.

---

## 🚀 Getting Started

*(Instructions for developers)*

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Set API Key:**
    Export your Gemini API key:
    ```bash
    export GEMINI_API_KEY="your_api_key_here"
    ```
3.  **Run the Server:**
    ```bash
    python app.py
    ```
4.  **Play:**
    Open `http://localhost:5000` to host the game.

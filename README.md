# The Council of Ashes

The Council of Ashes is a web-based political strategy game where players take on the roles of influential figures in a fantasy kingdom. They must navigate a series of political dilemmas, make decisions, and deal with the consequences of their actions. The game is narrated by an AI storyteller powered by Google Gemini, with voice narration provided by Coqui-TTS.

## Setup Guide

This guide will walk you through the steps to set up and run the game on your local network.

### 1. Installation

First, you need to clone the repository and install the required Python dependencies.

```bash
git clone https://github.com/barteg/Council-of-Ashes.git
cd Council-of-Ashes
pip install -r requirements.txt
```

This project requires **Python 3.11.9** or higher.

### 2. Configuration

The game requires a few environment variables to be set up.

#### Gemini API Key

You need a Google Gemini API key to power the AI storyteller.

1.  Obtain an API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
2.  Set the `GEMINI_API_KEY` environment variable. You can do this by adding the following line to your shell's configuration file (e.g., `~/.bashrc`, `~/.zshrc`):

    ```bash
    export GEMINI_API_KEY="YOUR_API_KEY"
    ```

    Replace `"YOUR_API_KEY"` with your actual Gemini API key. Remember to restart your shell or source the configuration file for the changes to take effect.

#### Flask Secret Key

For production or long-running games, it is highly recommended to set a persistent `FLASK_SECRET_KEY`.

```bash
export FLASK_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex())')"
```

This will generate a random secret key and set it as an environment variable.

### 3. Text-to-Speech (TTS) Models

The game uses Coqui-TTS to generate voice narration.

#### TTS Model

The TTS model will be downloaded automatically the first time you run the application. The download can take a significant amount of time and disk space.

The model will be stored in the following directory: `~/.local/share/tts/`.

#### Speaker Voice

The voice for the narrator is provided by a WAV file located at `tts/Rafal_Walentowicz.wav`. You can replace this file with any other WAV file to change the narrator's voice. The file must be in the correct format (e.g., 16-bit PCM WAV).

### 4. Running the Game

Once you have completed the setup, you can run the game with the following command:

```bash
python3 app.py
```

The server will start, and you will see a message in the console with the local IP address of the host machine, for example:

```
Starting server on http://192.168.1.100:5000
```

*   **Host**: Open the provided URL in your web browser to access the host screen.
*   **Players**: Other players on the same local network can join the game by scanning the QR code displayed on the host screen with their mobile devices.

Enjoy the game!

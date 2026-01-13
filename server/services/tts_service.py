import os
import torch
from TTS.api import TTS
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import XttsAudioConfig, XttsArgs
from TTS.config.shared_configs import BaseDatasetConfig

# --- Allowlist fix for safe deserialization ---
torch.serialization.add_safe_globals(
    [XttsConfig, XttsAudioConfig, BaseDatasetConfig, XttsArgs]
)

class TTSService:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.load_model()

    def load_model(self):
        print("[TTS] TTS is disabled by configuration to improve speed.")
        self.model = None
        # Original loading logic commented out/removed

    def generate_audio(self, text, output_file):
        if not self.model:
            raise Exception("TTS Model not loaded")
        
        speaker_wav_path = "tts/Rafal_Walentowicz.wav"
        if not os.path.exists(speaker_wav_path):
             raise Exception(f"Speaker WAV not found at {speaker_wav_path}")

        print(f"[TTS] Synthesizing '{text}'...")
        self.model.tts_to_file(
            text=text,
            speaker_wav=speaker_wav_path,
            language="pl",
            file_path=output_file,
        )
        print(f"[TTS] Saved to {output_file}")

tts_service = TTSService()

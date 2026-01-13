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
        print(f"[TTS] Using device: {self.device}")
        print("[TTS] Loading Coqui XTTS v2 model...")
        try:
            model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
            config_path = os.path.join(
                "tts_models",
                "tts_models--multilingual--multi-dataset--xtts_v2",
                "config.json",
            )
            model_path = os.path.join(
                "tts_models",
                "tts_models--multilingual--multi-dataset--xtts_v2"
            )

            if not os.path.exists(config_path):
                print(f"[TTS] Model config not found at {config_path}")
                self.model = None
            else:
                self.model = TTS(model_path=model_path, config_path=config_path).to(self.device)
                print("[TTS] Coqui XTTS v2 model loaded successfully.")
        except Exception as e:
            print(f"[TTS] Error loading Coqui XTTS model: {e}")
            self.model = None

        if not os.path.exists("tts"):
            os.makedirs("tts")

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

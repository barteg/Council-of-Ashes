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
        # Allow forcing CPU usage to avoid VRAM issues
        if os.environ.get("TTS_DEVICE", "auto").lower() == "cpu":
            self.device = "cpu"
            print("[TTS] Forced to CPU mode via TTS_DEVICE=cpu.")
        else:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.model = None
        
        # Check if TTS is enabled via environment variable (Default: False to save RAM)
        self.enabled = os.environ.get("ENABLE_TTS", "False").lower() == "true"
        
        if self.enabled:
            self.load_model()
        else:
            print("[TTS] Service disabled. Set ENABLE_TTS=True to enable (requires significant RAM).")

    def load_model(self):
        try:
            print("[TTS] Loading TTS model (this might take a few seconds)...")
            self.model = TTS(
                model_name="tts_models/multilingual/multi-dataset/xtts_v2",
                progress_bar=False,
                gpu=(self.device == "cuda")
            ).to(self.device)
            print(f"[TTS] Model loaded successfully on {self.device}.")
        except Exception as e:
            print(f"[TTS] Failed to load on {self.device}: {e}")
            if self.device == "cuda":
                print("[TTS] Retrying on CPU...")
                self.device = "cpu"
                try:
                    self.model = TTS(
                        model_name="tts_models/multilingual/multi-dataset/xtts_v2",
                        progress_bar=False,
                        gpu=False
                    ).to("cpu")
                    print("[TTS] Model loaded successfully on CPU.")
                except Exception as e2:
                    print(f"[TTS] Failed to load on CPU: {e2}")
                    self.model = None
            else:
                self.model = None

    def generate_audio(self, text, output_file):
        if not self.model:
            raise Exception("TTS Model not loaded. Set ENABLE_TTS=True env var to use this feature.")
        
        # Calculate absolute path to the speaker file
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        speaker_wav_path = os.path.join(base_dir, "tts", "Rafal_Walentowicz.wav")
        
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

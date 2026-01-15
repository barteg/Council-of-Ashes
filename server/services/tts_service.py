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
        try:
            print("[TTS] Loading TTS model (this might take a few seconds)...")
            self.model = TTS(
                model_name="tts_models/multilingual/multi-dataset/xtts_v2",
                progress_bar=False,
                gpu=True
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
            raise Exception("TTS Model not loaded")
        
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

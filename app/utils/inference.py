import json
import os
import subprocess
import tempfile
import io

import torch
import torchaudio

from app.utils.models.lm import LanguageModel
from app.utils.models.model_ctc import InterCTC, ModelCTC
from app.utils.models.transducer import Transducer


def create_model(config):
    # Create Model
    if config["model_type"] == "Transducer":
        model = Transducer(
            encoder_params=config["encoder_params"],
            decoder_params=config["decoder_params"],
            joint_params=config["joint_params"],
            tokenizer_params=config["tokenizer_params"],
            training_params=config["training_params"],
            decoding_params=config["decoding_params"],
            name=config["model_name"],
        )

    elif config["model_type"] == "CTC":
        model = ModelCTC(
            encoder_params=config["encoder_params"],
            tokenizer_params=config["tokenizer_params"],
            training_params=config["training_params"],
            decoding_params=config["decoding_params"],
            name=config["model_name"],
        )

    elif config["model_type"] == "InterCTC":
        model = InterCTC(
            encoder_params=config["encoder_params"],
            tokenizer_params=config["tokenizer_params"],
            training_params=config["training_params"],
            decoding_params=config["decoding_params"],
            name=config["model_name"],
        )

    elif config["model_type"] == "LM":
        model = LanguageModel(
            lm_params=config["lm_params"],
            tokenizer_params=config["tokenizer_params"],
            training_params=config["training_params"],
            decoding_params=config["decoding_params"],
            name=config["model_name"],
        )

    else:
        raise Exception("Unknown model type")

    return model


model_config_path = os.getenv("MODEL_CONFIG_PATH", "./config/EfficientConformerCTCSmall.json")
checkpoint_path = os.getenv("MODEL_CHECKPOINT_PATH", "./checkpoints/checkpoints_56_90h_07.ckpt")


# chỉnh đường dẫn
config_file = model_config_path
checkpoint_file = checkpoint_path


# Load Config
with open(config_file) as json_config:
    config = json.load(json_config)

# Device
device = torch.device("cpu")
model = create_model(config).to(device)
model.eval()

# Load Model
model.load(checkpoint_file)


def transcriber_bytes(audio_bytes: bytes) -> str:
    try:
        audio, _ = torchaudio.load(io.BytesIO(audio_bytes))
        return transcriber_tensor(audio)
    except Exception as e:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_input:
            temp_input.write(audio_bytes)
            temp_input_path = temp_input.name
        
        wav_path = temp_input_path.replace('.webm', '_converted.wav')
        try:
            subprocess.run([
                'ffmpeg', '-i', temp_input_path, '-ar', '16000', '-ac', '1', '-y', wav_path
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            audio, _ = torchaudio.load(wav_path)
            os.unlink(temp_input_path)
            os.unlink(wav_path)
            return transcriber_tensor(audio)
        except (subprocess.CalledProcessError, FileNotFoundError):
            os.unlink(temp_input_path)
            if os.path.exists(wav_path):
                os.unlink(wav_path)
        raise RuntimeError(f"Unable to load audio bytes. Error: {str(e)}")


def transcriber(audio_path):
    try:
        audio, _ = torchaudio.load(audio_path)
        return transcriber_tensor(audio)
    except Exception as e:
        if audio_path.endswith('.webm'):
            wav_path = audio_path.replace('.webm', '_converted.wav')
            try:
                subprocess.run([
                    'ffmpeg', '-i', audio_path, '-ar', '16000', '-ac', '1', '-y', wav_path
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                audio, _ = torchaudio.load(wav_path)
                os.unlink(wav_path)
                return transcriber_tensor(audio)
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        raise RuntimeError(f"Unable to load audio file: {audio_path}. Error: {str(e)}")


def transcriber_tensor(audio_tensor):
    """Transcribe audio tensor directly (no chunking, for speaker segments)"""
    # Ensure audio is in correct format [channels, samples]
    if audio_tensor.dim() == 1:
        audio_tensor = audio_tensor.unsqueeze(0)

    # Ensure it's mono
    if audio_tensor.shape[0] > 1:
        audio_tensor = audio_tensor.mean(dim=0, keepdim=True)

    total_samples = audio_tensor.shape[1]
    print(f"   📊 Processing segment: {total_samples} samples ({total_samples / 16000:.1f}s)")

    # Fix tensor shape for model compatibility
    target_divisor = 360  # 4 heads * 90 dim
    remainder = total_samples % target_divisor

    if remainder > 0:
        # Pad to make divisible by target_divisor
        pad_samples = target_divisor - remainder
        audio_tensor = torch.nn.functional.pad(audio_tensor, (0, pad_samples), "constant", 0)
        print(f"   🔧 Padded from {total_samples} to {total_samples + pad_samples} samples")

    # Ensure minimum length
    if audio_tensor.shape[1] < target_divisor:
        return "[AUDIO_TOO_SHORT]"

    try:
        # Use original length for transcription (excluding padding)
        x_len = torch.tensor([total_samples], device=device)
        print(f"   📏 Using length: {x_len.item()} samples for transcription")

        text = model.gready_search_decoding(audio_tensor.to(device), x_len=x_len)[0]
        text = text.lower().replace(".", "").strip()
        return text
    except Exception as e:
        print(f"   ❌ Transcription error: {e}")
        return ""

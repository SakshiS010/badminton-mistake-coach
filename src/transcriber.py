from faster_whisper import WhisperModel


class TranscriptionError(Exception):
    pass


def transcribe(audio_path: str, model_size: str = "small") -> dict:
    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments_iter, info = model.transcribe(audio_path)
        segments = [
            {"start": s.start, "end": s.end, "text": s.text.strip()}
            for s in segments_iter
        ]
    except Exception as e:
        raise TranscriptionError(f"Failed to transcribe {audio_path}: {e}") from e

    full_text = " ".join(s["text"] for s in segments)
    return {
        "language": info.language,
        "full_text": full_text,
        "segments": segments,
    }

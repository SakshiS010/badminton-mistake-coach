import pytest
from unittest.mock import patch, MagicMock
from src.transcriber import transcribe, TranscriptionError


class FakeSegment:
    def __init__(self, start, end, text):
        self.start = start
        self.end = end
        self.text = text


@patch("src.transcriber.WhisperModel")
def test_transcribe_returns_language_and_segments(mock_model_class):
    mock_model = MagicMock()
    fake_segments = [
        FakeSegment(0.0, 3.5, " Your grip is wrong here."),
        FakeSegment(3.5, 7.0, " Hold it like this instead."),
    ]
    fake_info = MagicMock(language="en")
    mock_model.transcribe.return_value = (iter(fake_segments), fake_info)
    mock_model_class.return_value = mock_model

    result = transcribe("/tmp/audio/abc123.mp3")

    assert result["language"] == "en"
    assert len(result["segments"]) == 2
    assert result["segments"][0]["start"] == 0.0
    assert result["segments"][0]["text"] == "Your grip is wrong here."
    assert "Your grip is wrong here." in result["full_text"]
    assert "Hold it like this instead." in result["full_text"]


@patch("src.transcriber.WhisperModel")
def test_transcribe_raises_on_failure(mock_model_class):
    mock_model = MagicMock()
    mock_model.transcribe.side_effect = Exception("corrupt audio")
    mock_model_class.return_value = mock_model

    with pytest.raises(TranscriptionError):
        transcribe("/tmp/audio/bad.mp3")

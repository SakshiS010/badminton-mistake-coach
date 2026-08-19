import pytest
from unittest.mock import patch, MagicMock
from src.extractor import extract_mistakes, ExtractionError

SAMPLE_TRANSCRIPT = {
    "language": "en",
    "full_text": "Your grip is wrong here. Hold it like this instead.",
    "segments": [
        {"start": 0.0, "end": 3.5, "text": "Your grip is wrong here."},
        {"start": 3.5, "end": 7.0, "text": "Hold it like this instead."},
    ],
}


@patch("src.extractor.genai.Client")
def test_extract_mistakes_parses_valid_json(mock_client_class):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '''[
        {"timestamp": 0.0, "mistake": "Wrong grip", "fix": "Hold it like this instead"}
    ]'''
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    result = extract_mistakes(SAMPLE_TRANSCRIPT, api_key="fake-key")

    assert len(result) == 1
    assert result[0]["timestamp"] == 0.0
    assert result[0]["mistake"] == "Wrong grip"
    assert result[0]["fix"] == "Hold it like this instead"


@patch("src.extractor.genai.Client")
def test_extract_mistakes_strips_markdown_fences(mock_client_class):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '```json\n[{"timestamp": 1.0, "mistake": "M", "fix": "F"}]\n```'
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    result = extract_mistakes(SAMPLE_TRANSCRIPT, api_key="fake-key")

    assert result == [{"timestamp": 1.0, "mistake": "M", "fix": "F"}]


@patch("src.extractor.genai.Client")
def test_extract_mistakes_raises_after_retry_fails(mock_client_class):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "this is not json"
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    with pytest.raises(ExtractionError):
        extract_mistakes(SAMPLE_TRANSCRIPT, api_key="fake-key")

    assert mock_client.models.generate_content.call_count == 2


@patch("src.extractor.genai.Client")
def test_extract_mistakes_empty_list_is_valid(mock_client_class):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "[]"
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    result = extract_mistakes(SAMPLE_TRANSCRIPT, api_key="fake-key")

    assert result == []

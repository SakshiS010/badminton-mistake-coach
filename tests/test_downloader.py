import pytest
from unittest.mock import patch, MagicMock
from src.downloader import download_audio, DownloadError


@patch("src.downloader.yt_dlp.YoutubeDL")
def test_download_audio_returns_metadata(mock_ydl_class):
    mock_ydl = MagicMock()
    mock_ydl.extract_info.return_value = {
        "id": "abc123",
        "title": "Backhand Basics",
        "upload_date": "20260101",
        "requested_downloads": [{"filepath": "/tmp/audio/abc123.mp3"}],
    }
    mock_ydl_class.return_value.__enter__.return_value = mock_ydl

    result = download_audio("https://youtu.be/abc123", output_dir="/tmp/audio")

    assert result["video_id"] == "abc123"
    assert result["title"] == "Backhand Basics"
    assert result["upload_date"] == "20260101"
    assert result["audio_path"] == "/tmp/audio/abc123.mp3"


@patch("src.downloader.yt_dlp.YoutubeDL")
def test_download_audio_raises_on_failure(mock_ydl_class):
    mock_ydl = MagicMock()
    mock_ydl.extract_info.side_effect = Exception("Video unavailable")
    mock_ydl_class.return_value.__enter__.return_value = mock_ydl

    with pytest.raises(DownloadError):
        download_audio("https://youtu.be/deadbeef", output_dir="/tmp/audio")

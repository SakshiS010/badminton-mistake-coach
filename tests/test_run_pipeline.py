import os
from unittest.mock import patch
from scripts.run_pipeline import main


@patch("scripts.run_pipeline.extract_mistakes")
@patch("scripts.run_pipeline.transcribe")
@patch("scripts.run_pipeline.download_audio")
def test_main_happy_path(mock_download, mock_transcribe, mock_extract, tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    db_path = str(tmp_path / "results.db")
    mock_download.return_value = {
        "audio_path": "/tmp/audio/abc123.mp3",
        "video_id": "abc123",
        "title": "Backhand Basics",
        "upload_date": "20260101",
    }
    mock_transcribe.return_value = {
        "language": "en", "full_text": "...", "segments": [],
    }
    mock_extract.return_value = [
        {"timestamp": 1.0, "mistake": "M", "fix": "F"},
    ]

    code = main("https://youtu.be/abc123", db_path=db_path)

    assert code == 0
    from src.storage import Storage
    videos = Storage(db_path).get_all_videos()
    assert videos[0]["video_id"] == "abc123"
    assert videos[0]["mistakes"][0]["mistake"] == "M"


@patch("scripts.run_pipeline.download_audio")
def test_main_skips_already_processed(mock_download, tmp_path):
    db_path = str(tmp_path / "results.db")
    mock_download.return_value = {
        "audio_path": "/tmp/audio/abc123.mp3",
        "video_id": "abc123",
        "title": "Backhand Basics",
        "upload_date": "20260101",
    }
    from src.storage import Storage
    Storage(db_path).init_db()
    Storage(db_path).save_results("abc123", "Backhand Basics", "20260101", [])

    code = main("https://youtu.be/abc123", db_path=db_path)

    assert code == 0
    mock_download.assert_called_once()  # download happens (to get the ID), transcribe/extract should not


@patch("scripts.run_pipeline.download_audio")
def test_main_returns_1_on_download_failure(mock_download, tmp_path):
    from src.downloader import DownloadError
    db_path = str(tmp_path / "results.db")
    mock_download.side_effect = DownloadError("gone")

    code = main("https://youtu.be/deadbeef", db_path=db_path)

    assert code == 1


@patch("scripts.run_pipeline.extract_mistakes")
@patch("scripts.run_pipeline.transcribe")
@patch("scripts.run_pipeline.download_audio")
def test_main_saves_failure_on_extraction_error(mock_download, mock_transcribe, mock_extract, tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    from src.extractor import ExtractionError
    db_path = str(tmp_path / "results.db")
    mock_download.return_value = {
        "audio_path": "/tmp/audio/abc123.mp3",
        "video_id": "abc123",
        "title": "Backhand Basics",
        "upload_date": "20260101",
    }
    mock_transcribe.return_value = {"language": "en", "full_text": "...", "segments": []}
    mock_extract.side_effect = ExtractionError("bad json")

    code = main("https://youtu.be/abc123", db_path=db_path)

    assert code == 1
    from src.storage import Storage
    videos = Storage(db_path).get_all_videos()
    assert videos[0]["status"] == "extraction_failed"

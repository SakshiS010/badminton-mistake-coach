import os
import tempfile
import pytest
from src.storage import Storage


@pytest.fixture
def storage():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = Storage(path)
    s.init_db()
    yield s
    # Close any remaining connections before cleanup
    import sqlite3
    sqlite3.connect(path).close()
    try:
        os.remove(path)
    except (PermissionError, OSError):
        pass


def test_not_processed_initially(storage):
    assert storage.already_processed("abc123") is False


def test_save_and_check_processed(storage):
    storage.save_results(
        video_id="abc123",
        title="Backhand Basics",
        upload_date="20260101",
        mistakes=[
            {"timestamp": 12.5, "mistake": "Late racket prep", "fix": "Turn shoulder earlier"},
        ],
    )
    assert storage.already_processed("abc123") is True


def test_get_all_videos_returns_mistakes(storage):
    storage.save_results(
        video_id="abc123",
        title="Backhand Basics",
        upload_date="20260101",
        mistakes=[
            {"timestamp": 12.5, "mistake": "Late racket prep", "fix": "Turn shoulder earlier"},
            {"timestamp": 45.0, "mistake": "Wrong grip", "fix": "Use continental grip"},
        ],
    )
    videos = storage.get_all_videos()
    assert len(videos) == 1
    assert videos[0]["video_id"] == "abc123"
    assert videos[0]["title"] == "Backhand Basics"
    assert videos[0]["status"] == "ok"
    assert len(videos[0]["mistakes"]) == 2
    assert videos[0]["mistakes"][0]["mistake"] == "Late racket prep"


def test_save_failed_extraction(storage):
    storage.save_failed_extraction("xyz789", "Serve Drills", "not valid json")
    videos = storage.get_all_videos()
    assert len(videos) == 1
    assert videos[0]["status"] == "extraction_failed"
    assert videos[0]["mistakes"] == []

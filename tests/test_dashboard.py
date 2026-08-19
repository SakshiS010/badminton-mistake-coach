import os
import tempfile
import shutil
import sqlite3
from src.storage import Storage
from src.dashboard import build_dashboard


def test_build_dashboard_renders_video_and_mistakes():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    output_dir = tempfile.mkdtemp()
    try:
        storage = Storage(db_path)
        storage.init_db()
        storage.save_results(
            video_id="abc123",
            title="Backhand Basics",
            upload_date="20260101",
            mistakes=[
                {"timestamp": 12.5, "mistake": "Late racket prep", "fix": "Turn shoulder earlier"},
            ],
        )

        build_dashboard(db_path, output_dir)

        html_path = os.path.join(output_dir, "index.html")
        assert os.path.exists(html_path)
        with open(html_path, encoding="utf-8") as f:
            html = f.read()
        assert "Backhand Basics" in html
        assert "Late racket prep" in html
        assert "Turn shoulder earlier" in html
        assert "youtu.be/abc123?t=12" in html
    finally:
        # Close any remaining connections before cleanup
        sqlite3.connect(db_path).close()
        try:
            os.remove(db_path)
        except (PermissionError, OSError):
            pass
        shutil.rmtree(output_dir)

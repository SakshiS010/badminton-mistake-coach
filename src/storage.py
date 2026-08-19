import sqlite3


class Storage:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                    video_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    upload_date TEXT NOT NULL,
                    status TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mistakes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT NOT NULL REFERENCES videos(video_id),
                    timestamp REAL NOT NULL,
                    mistake TEXT NOT NULL,
                    fix TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS extraction_failures (
                    video_id TEXT PRIMARY KEY REFERENCES videos(video_id),
                    raw_output TEXT NOT NULL
                )
            """)

    def already_processed(self, video_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM videos WHERE video_id = ?", (video_id,)
            ).fetchone()
            return row is not None

    def save_results(self, video_id: str, title: str, upload_date: str, mistakes: list[dict]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO videos (video_id, title, upload_date, status) VALUES (?, ?, ?, 'ok')",
                (video_id, title, upload_date),
            )
            conn.executemany(
                "INSERT INTO mistakes (video_id, timestamp, mistake, fix) VALUES (?, ?, ?, ?)",
                [(video_id, m["timestamp"], m["mistake"], m["fix"]) for m in mistakes],
            )

    def save_failed_extraction(self, video_id: str, title: str, raw_output: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO videos (video_id, title, upload_date, status) VALUES (?, ?, '', 'extraction_failed')",
                (video_id, title),
            )
            conn.execute(
                "INSERT INTO extraction_failures (video_id, raw_output) VALUES (?, ?)",
                (video_id, raw_output),
            )

    def get_all_videos(self) -> list[dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            videos = conn.execute(
                "SELECT * FROM videos ORDER BY upload_date DESC"
            ).fetchall()
            result = []
            for v in videos:
                mistakes = conn.execute(
                    "SELECT timestamp, mistake, fix FROM mistakes WHERE video_id = ? ORDER BY timestamp",
                    (v["video_id"],),
                ).fetchall()
                result.append({
                    "video_id": v["video_id"],
                    "title": v["title"],
                    "upload_date": v["upload_date"],
                    "status": v["status"],
                    "mistakes": [dict(m) for m in mistakes],
                })
            return result

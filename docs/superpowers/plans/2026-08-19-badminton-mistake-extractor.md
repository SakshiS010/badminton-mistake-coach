# Badminton Coaching Mistake Extractor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Given a YouTube URL for a badminton coaching video, extract every "mistake the coach names + fix the coach gives" as a structured, timestamped list in the coach's own language, and publish the results to a browsable dashboard — with the whole pipeline running on free GitHub Actions infrastructure so no video ever touches the user's device.

**Architecture:** A `workflow_dispatch`-triggered GitHub Actions job runs four Python modules in sequence — download audio (`yt-dlp`) → transcribe (`faster-whisper`, CPU) → extract mistake/fix pairs (Gemini API) → persist to a small SQLite file committed back to the repo. A separate step regenerates a static dashboard from that SQLite file and publishes it via GitHub Pages. Audio and full transcripts exist only for the duration of the job and are never committed.

**Tech Stack:** Python 3.12, `yt-dlp`, `faster-whisper`, `google-genai` (Gemini API), `sqlite3` (stdlib), `pytest`, GitHub Actions (`actions/checkout`, `actions/setup-python`, `actions/upload-pages-artifact`, `actions/deploy-pages`).

**Spec:** `docs/superpowers/specs/2026-08-19-badminton-mistake-extractor-design.md`

## Global Constraints

- Video/audio files must never be committed to the repo or persisted outside the ephemeral runner disk for a single job run.
- Full raw transcripts must never be committed — only the curated `{timestamp, mistake, fix}` output.
- The repo must be public (required for free GitHub Pages).
- LLM calls use the Gemini API, model `gemini-2.5-flash`, key read from the `GEMINI_API_KEY` environment variable (populated from a GitHub Actions repo secret of the same name).
- Whisper transcription runs on CPU only (no GPU available on standard GitHub-hosted runners).
- Dashboard output must not overlap with `docs/superpowers/` (that directory holds specs/plans, not the published site).

---

## File Structure

```
label-stdio/
├── .github/workflows/
│   └── process-video.yml       # workflow_dispatch trigger; runs pipeline, commits results, deploys Pages
├── src/
│   ├── __init__.py
│   ├── downloader.py            # yt-dlp wrapper: URL -> audio file + metadata
│   ├── transcriber.py           # faster-whisper wrapper: audio file -> timestamped transcript
│   ├── extractor.py             # Gemini call: transcript -> list of {timestamp, mistake, fix}
│   ├── storage.py                # SQLite persistence + already-processed check
│   └── dashboard.py               # SQLite -> static index.html
├── scripts/
│   └── run_pipeline.py           # CLI entrypoint wiring the above together
├── tests/
│   ├── test_storage.py
│   ├── test_downloader.py
│   ├── test_transcriber.py
│   ├── test_extractor.py
│   ├── test_dashboard.py
│   └── test_run_pipeline.py
├── data/
│   └── results.db                # committed SQLite file (small, text-only)
├── requirements.txt
├── .gitignore
└── README.md
```

---

### Task 1: Repo setup and scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `README.md`
- Create: `src/__init__.py`

**Interfaces:**
- Produces: a public GitHub repo with these files pushed, ready for later tasks to add code into.

- [ ] **Step 1: Create the public GitHub repo**

If `gh` CLI is available:
```bash
gh repo create badminton-mistake-coach --public --source=. --remote=origin
```
If `gh` is not installed, create it manually at https://github.com/new (name: `badminton-mistake-coach`, visibility: Public, no README/gitignore/license — this repo already has commits), then:
```bash
git remote add origin https://github.com/<your-username>/badminton-mistake-coach.git
```

- [ ] **Step 2: Write `requirements.txt`**

```
yt-dlp
faster-whisper
google-genai
pytest
```

- [ ] **Step 3: Write `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
site/
*.mp3
*.wav
*.m4a
```

- [ ] **Step 4: Create `src/__init__.py`** (empty file, makes `src` a package)

- [ ] **Step 5: Write `README.md`**

```markdown
# Badminton Mistake Coach

Given a YouTube video URL from a badminton coaching channel, extracts
every mistake the coach names and the fix they give, as a timestamped
list in the coach's own language. Runs entirely on GitHub Actions —
no video ever touches a local machine.

## Usage

From the Actions tab, run the "Process Video" workflow with a video
URL input. Results are committed to `data/results.db` and published
to the repo's GitHub Pages site.

See `docs/superpowers/specs/2026-08-19-badminton-mistake-extractor-design.md`
for the full design.
```

- [ ] **Step 6: Install dependencies locally (for running tests during development)**

```bash
pip install -r requirements.txt
```

- [ ] **Step 7: Commit and push**

```bash
git add requirements.txt .gitignore README.md src/__init__.py
git commit -m "Scaffold project structure"
git push -u origin main
```

---

### Task 2: Storage module

**Files:**
- Create: `src/storage.py`
- Test: `tests/test_storage.py`

**Interfaces:**
- Produces:
  - `class Storage` with:
    - `__init__(self, db_path: str)`
    - `init_db(self) -> None`
    - `already_processed(self, video_id: str) -> bool`
    - `save_results(self, video_id: str, title: str, upload_date: str, mistakes: list[dict]) -> None` — each mistake dict has keys `timestamp` (float), `mistake` (str), `fix` (str)
    - `save_failed_extraction(self, video_id: str, title: str, raw_output: str) -> None`
    - `get_all_videos(self) -> list[dict]` — each dict: `{video_id, title, upload_date, status, mistakes: [{timestamp, mistake, fix}]}`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_storage.py
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
    os.remove(path)


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.storage'`

- [ ] **Step 3: Write the implementation**

```python
# src/storage.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_storage.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Create the committed empty database and commit**

```bash
python -c "from src.storage import Storage; Storage('data/results.db').init_db()"
git add src/storage.py tests/test_storage.py data/results.db
git commit -m "Add storage module with SQLite persistence"
git push
```

---

### Task 3: Downloader module

**Files:**
- Create: `src/downloader.py`
- Test: `tests/test_downloader.py`

**Interfaces:**
- Produces:
  - `class DownloadError(Exception)`
  - `download_audio(url: str, output_dir: str) -> dict` — returns `{"audio_path": str, "video_id": str, "title": str, "upload_date": str}`
- Consumes: nothing from earlier tasks.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_downloader.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_downloader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.downloader'`

- [ ] **Step 3: Write the implementation**

```python
# src/downloader.py
import yt_dlp


class DownloadError(Exception):
    pass


def download_audio(url: str, output_dir: str) -> dict:
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{output_dir}/%(id)s.%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
        }],
        "quiet": True,
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as e:
        raise DownloadError(f"Failed to download {url}: {e}") from e

    audio_path = info["requested_downloads"][0]["filepath"]
    return {
        "audio_path": audio_path,
        "video_id": info["id"],
        "title": info["title"],
        "upload_date": info["upload_date"],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_downloader.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/downloader.py tests/test_downloader.py
git commit -m "Add downloader module using yt-dlp"
git push
```

---

### Task 4: Transcriber module

**Files:**
- Create: `src/transcriber.py`
- Test: `tests/test_transcriber.py`

**Interfaces:**
- Produces:
  - `class TranscriptionError(Exception)`
  - `transcribe(audio_path: str, model_size: str = "small") -> dict` — returns `{"language": str, "full_text": str, "segments": [{"start": float, "end": float, "text": str}]}`
- Consumes: `audio_path` from `download_audio()`'s return value (Task 3).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_transcriber.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_transcriber.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.transcriber'`

- [ ] **Step 3: Write the implementation**

```python
# src/transcriber.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_transcriber.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/transcriber.py tests/test_transcriber.py
git commit -m "Add transcriber module using faster-whisper"
git push
```

---

### Task 5: Extractor module

**Files:**
- Create: `src/extractor.py`
- Test: `tests/test_extractor.py`

**Interfaces:**
- Produces:
  - `class ExtractionError(Exception)`
  - `extract_mistakes(transcript: dict, api_key: str) -> list[dict]` — each returned dict has keys `timestamp` (float), `mistake` (str), `fix` (str). `transcript` is the dict shape returned by `transcribe()` (Task 4).
- Consumes: `transcript` dict from `transcribe()` (Task 4): `{"language": str, "full_text": str, "segments": [...]}`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_extractor.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_extractor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.extractor'`

- [ ] **Step 3: Write the implementation**

```python
# src/extractor.py
import json
import re
from google import genai

MODEL_NAME = "gemini-2.5-flash"

PROMPT_TEMPLATE = """You are analyzing a transcript of a badminton coaching video. \
The transcript is in language code "{language}".

Find every moment where the coach names a specific mistake and gives a fix for it. \
Return ONLY a JSON array (no markdown, no explanation) where each item has exactly \
these keys: "timestamp" (number, seconds into the video, use the start time of the \
segment where the mistake is named), "mistake" (string), "fix" (string). Write the \
"mistake" and "fix" text in the SAME language as the transcript ({language}) — do not \
translate or normalize the language.

If there are no mistakes named, return an empty array: []

Transcript segments (start_seconds: text):
{segments}
"""


def _format_segments(transcript: dict) -> str:
    return "\n".join(f"{s['start']}: {s['text']}" for s in transcript["segments"])


def _parse_response(text: str) -> list[dict]:
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    data = json.loads(cleaned)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array")
    for item in data:
        if not all(k in item for k in ("timestamp", "mistake", "fix")):
            raise ValueError(f"Missing required keys in item: {item}")
    return data


def extract_mistakes(transcript: dict, api_key: str) -> list[dict]:
    client = genai.Client(api_key=api_key)
    prompt = PROMPT_TEMPLATE.format(
        language=transcript["language"],
        segments=_format_segments(transcript),
    )

    last_error = None
    for attempt in range(2):
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        try:
            return _parse_response(response.text)
        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            prompt = (
                f"{prompt}\n\nYour previous response could not be parsed as valid JSON "
                f"({e}). Return ONLY the JSON array, nothing else."
            )

    raise ExtractionError(f"Failed to parse LLM output after retry: {last_error}")


class ExtractionError(Exception):
    pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_extractor.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/extractor.py tests/test_extractor.py
git commit -m "Add extractor module using Gemini API"
git push
```

---

### Task 6: Dashboard module

**Files:**
- Create: `src/dashboard.py`
- Test: `tests/test_dashboard.py`

**Interfaces:**
- Produces: `build_dashboard(db_path: str, output_dir: str) -> None` — writes `output_dir/index.html`.
- Consumes: `Storage.get_all_videos()` (Task 2): `[{video_id, title, upload_date, status, mistakes: [{timestamp, mistake, fix}]}]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dashboard.py
import os
import tempfile
import shutil
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
        os.remove(db_path)
        shutil.rmtree(output_dir)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dashboard.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.dashboard'`

- [ ] **Step 3: Write the implementation**

```python
# src/dashboard.py
import os
from html import escape
from src.storage import Storage

PAGE_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Badminton Mistake Coach</title>
<style>
body {{ font-family: sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; }}
.video {{ margin-bottom: 2rem; border-bottom: 1px solid #ccc; padding-bottom: 1rem; }}
.mistake {{ margin: 0.5rem 0; }}
.mistake .fix {{ color: #555; }}
a {{ color: #0645ad; }}
</style>
</head>
<body>
<h1>Badminton Mistake Coach</h1>
{videos}
</body>
</html>
"""

VIDEO_TEMPLATE = """<div class="video">
<h2>{title}</h2>
{mistakes}
</div>
"""

MISTAKE_TEMPLATE = """<div class="mistake">
<a href="https://youtu.be/{video_id}?t={timestamp_int}">[{timestamp_int}s]</a>
<strong>{mistake}</strong>
<div class="fix">{fix}</div>
</div>
"""

NO_MISTAKES = "<p><em>No mistakes extracted.</em></p>"


def _render_video(video: dict) -> str:
    if video["status"] != "ok" or not video["mistakes"]:
        mistakes_html = NO_MISTAKES
    else:
        mistakes_html = "\n".join(
            MISTAKE_TEMPLATE.format(
                video_id=video["video_id"],
                timestamp_int=int(m["timestamp"]),
                mistake=escape(m["mistake"]),
                fix=escape(m["fix"]),
            )
            for m in video["mistakes"]
        )
    return VIDEO_TEMPLATE.format(title=escape(video["title"]), mistakes=mistakes_html)


def build_dashboard(db_path: str, output_dir: str) -> None:
    storage = Storage(db_path)
    videos = storage.get_all_videos()
    videos_html = "\n".join(_render_video(v) for v in videos)

    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(PAGE_TEMPLATE.format(videos=videos_html))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_dashboard.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/dashboard.py tests/test_dashboard.py
git commit -m "Add dashboard module rendering static HTML from results"
git push
```

---

### Task 7: Pipeline CLI script

**Files:**
- Create: `scripts/run_pipeline.py`
- Test: `tests/test_run_pipeline.py`

**Interfaces:**
- Produces: `main(video_url: str, db_path: str = "data/results.db", tmp_dir: str = "/tmp/audio") -> int` (return code: 0 success/skip, 1 failure) — thin orchestration, no new business logic.
- Consumes: `download_audio()` (Task 3), `transcribe()` (Task 4), `extract_mistakes()` (Task 5), `Storage` (Task 2).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_run_pipeline.py
import os
from unittest.mock import patch
from scripts.run_pipeline import main


@patch("scripts.run_pipeline.extract_mistakes")
@patch("scripts.run_pipeline.transcribe")
@patch("scripts.run_pipeline.download_audio")
def test_main_happy_path(mock_download, mock_transcribe, mock_extract, tmp_path):
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
def test_main_saves_failure_on_extraction_error(mock_download, mock_transcribe, mock_extract, tmp_path):
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_run_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.run_pipeline'`

- [ ] **Step 3: Write the implementation**

```python
# scripts/run_pipeline.py
import os
import sys

from src.downloader import download_audio, DownloadError
from src.transcriber import transcribe, TranscriptionError
from src.extractor import extract_mistakes, ExtractionError
from src.storage import Storage


def main(video_url: str, db_path: str = "data/results.db", tmp_dir: str = "/tmp/audio") -> int:
    storage = Storage(db_path)
    storage.init_db()

    try:
        download_result = download_audio(video_url, output_dir=tmp_dir)
    except DownloadError as e:
        print(f"Download failed: {e}", file=sys.stderr)
        return 1

    video_id = download_result["video_id"]
    if storage.already_processed(video_id):
        print(f"Video {video_id} already processed, skipping.")
        return 0

    try:
        transcript = transcribe(download_result["audio_path"])
    except TranscriptionError as e:
        print(f"Transcription failed: {e}", file=sys.stderr)
        return 1

    try:
        mistakes = extract_mistakes(transcript, api_key=os.environ["GEMINI_API_KEY"])
    except ExtractionError as e:
        storage.save_failed_extraction(video_id, download_result["title"], str(e))
        print(f"Extraction failed, saved for review: {e}", file=sys.stderr)
        return 1

    storage.save_results(
        video_id=video_id,
        title=download_result["title"],
        upload_date=download_result["upload_date"],
        mistakes=mistakes,
    )
    print(f"Processed {video_id}: {len(mistakes)} mistake(s) found.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_run_pipeline.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Create `scripts/__init__.py` and commit**

```bash
touch scripts/__init__.py
git add scripts/run_pipeline.py scripts/__init__.py tests/test_run_pipeline.py
git commit -m "Add pipeline CLI orchestrating download -> transcribe -> extract -> store"
git push
```

---

### Task 8: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/process-video.yml`

**Interfaces:**
- Consumes: `scripts/run_pipeline.py` (Task 7), `src/dashboard.py` (Task 6).
- Produces: a runnable `workflow_dispatch` job visible in the repo's Actions tab.

- [ ] **Step 1: Write the workflow file**

```yaml
# .github/workflows/process-video.yml
name: Process Video

on:
  workflow_dispatch:
    inputs:
      video_url:
        description: 'YouTube video URL to process'
        required: true
        type: string

permissions:
  contents: write
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  process:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install ffmpeg
        run: sudo apt-get update && sudo apt-get install -y ffmpeg

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run pipeline
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: python scripts/run_pipeline.py "${{ inputs.video_url }}"

      - name: Build dashboard
        run: python -c "from src.dashboard import build_dashboard; build_dashboard('data/results.db', 'site')"

      - name: Commit results
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/results.db
          git diff --cached --quiet || git commit -m "Add results for processed video"
          git push

      - uses: actions/upload-pages-artifact@v3
        with:
          path: site

  deploy:
    needs: process
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Commit the workflow file**

```bash
git add .github/workflows/process-video.yml
git commit -m "Add GitHub Actions workflow for manual video processing"
git push
```

- [ ] **Step 3: One-time manual repo settings**

In the GitHub repo settings (Settings → Pages), set **Source** to "GitHub Actions" (not "Deploy from a branch"). This only needs to be done once.

- [ ] **Step 4: Add the Gemini API key as a repo secret**

Get a free API key from https://aistudio.google.com/apikey, then in the repo: Settings → Secrets and variables → Actions → New repository secret, name `GEMINI_API_KEY`, value: your key.

---

### Task 9: End-to-end validation against a real video

**Files:** none (validation only, no code changes expected unless a bug is found)

- [ ] **Step 1: Find a real video URL**

Go to the "Simply Sports Badminton Academy" YouTube channel and copy the URL of one coaching video that includes the coach verbally pointing out a mistake and a fix.

- [ ] **Step 2: Run the workflow**

From the repo's Actions tab, run "Process Video" with that URL as input.

- [ ] **Step 3: Verify the job succeeds**

Check the Actions run log for: successful download, successful transcription (correct language detected), successful extraction (non-empty JSON if the video actually contains a mistake/fix moment), a new commit to `data/results.db`, and a successful Pages deployment.

- [ ] **Step 4: Verify the dashboard**

Open the published GitHub Pages URL (shown in the deploy job's summary). Confirm the video, its mistake/fix pairs, and the timestamp links are present and the timestamp links jump to roughly the right moment in the video.

- [ ] **Step 5: Check the language-matching risk flagged in the spec**

Specifically check whether the extracted `mistake`/`fix` text preserves the coach's actual language (including any Hindi/English code-switching), rather than being silently translated or normalized by the LLM. If it's not preserving the original language/style well, that's a prompt-tuning follow-up, not a redesign — note it for a follow-up task rather than blocking here.

- [ ] **Step 6: Run the full test suite one more time**

```bash
pytest -v
```
Expected: all tests still pass.

---

## Self-Review Notes

- **Spec coverage:** Downloader/Transcriber/Extractor/Storage/Dashboard components (✓ Tasks 2–6), GitHub Actions execution with no local storage (✓ Task 8), only curated results committed not raw transcripts (✓ `save_results`/`save_failed_extraction` never persist `transcript["full_text"]`), GitHub Pages publishing (✓ Task 8), dedup/error handling for download/transcription/extraction failures (✓ Task 7 + tests), "no mistakes found" as valid outcome (✓ dashboard's `NO_MISTAKES` branch and empty-list test in Task 5), code-switching risk (✓ called out explicitly in the extractor prompt and re-checked in Task 9).
- **Deferred by spec, correctly absent from this plan:** scheduled/automatic triggering, visual/CV mistake detection (Phase 2).
- **Type consistency check:** `download_audio()` return dict keys (`audio_path`, `video_id`, `title`, `upload_date`) match what `run_pipeline.py` reads; `transcribe()` return dict keys (`language`, `full_text`, `segments`) match what `extract_mistakes()` and the extractor's prompt-building consume; `extract_mistakes()`'s returned list-of-dicts keys (`timestamp`, `mistake`, `fix`) match `Storage.save_results()`'s expected `mistakes` param shape and `dashboard.py`'s `_render_video()` access pattern — verified consistent across all tasks.

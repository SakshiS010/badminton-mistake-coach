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
        mistakes = extract_mistakes(transcript, api_key=os.environ.get("GEMINI_API_KEY", "test"))
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

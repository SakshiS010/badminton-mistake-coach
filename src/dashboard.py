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

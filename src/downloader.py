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

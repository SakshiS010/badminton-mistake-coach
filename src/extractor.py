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

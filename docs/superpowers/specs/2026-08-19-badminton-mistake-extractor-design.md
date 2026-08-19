# Badminton Coaching Mistake Extractor — Phase 1 Design

Date: 2026-08-19

## Problem

The user wants a system that, given badminton coaching videos from the
"Simply Sports Badminton Academy" YouTube channel, surfaces what mistake
the coach is pointing out and what fix they recommend — in the same
language the coach is speaking.

The original ask included a second capability: visually detecting
technique mistakes from the player's movement in the video (computer
vision / pose analysis), independent of what the coach says out loud.
That is a research-grade problem — no existing model does this for
badminton, and building one requires a labeled dataset of "this frame
sequence = this specific mistake" that does not currently exist. This
spec **explicitly excludes** that capability. See "Phase 2" below for
how this phase feeds into it later.

## Scope of this spec (Phase 1)

A manually-triggered pipeline: given one YouTube video URL, produce a
list of (timestamp, mistake, fix) entries extracted from the coach's
spoken commentary, in the coach's original language, viewable on a local
dashboard.

Explicitly out of scope for this spec:
- Automatic detection of new channel uploads / scheduling (Approach A
  from brainstorming — becomes its own future spec once this pipeline
  is proven manually).
- Any visual/computer-vision mistake detection (Phase 2, see below).
- Multi-user access, auth, or deployment — this is a local personal tool.

## Architecture

Five components, each independently testable:

1. **Downloader** — uses `yt-dlp` to pull audio + metadata (title, video
   ID, upload date) for a given YouTube URL.
2. **Transcriber** — local Whisper model (CPU, no GPU required) produces
   a timestamped transcript and auto-detects the spoken language.
3. **Mistake Extractor** — sends the transcript to an LLM with
   instructions to identify "mistake named → fix given" moments and
   return them as structured data: `{timestamp, mistake, fix}`, written
   in the same language as the transcript.
4. **Storage** — local SQLite database. One row per video, one row per
   extracted mistake/fix pair, linked by video ID.
5. **Dashboard** — a single local, server-rendered HTML page (no
   framework, no build step) listing processed videos newest-first,
   each expandable to show its mistake/fix pairs with clickable
   timestamps (`youtu.be/<id>?t=<seconds>`) linking back into the video.

## Data flow

```
URL → Downloader (audio + metadata)
    → Transcriber (timestamped transcript + detected language)
    → Mistake Extractor (structured mistake/fix list, in original language)
    → Storage (SQLite)
    → Dashboard (reads from storage, renders HTML)
```

## Error handling

- **Dedup**: video ID is checked against storage before processing;
  already-processed videos are skipped, not reprocessed.
- **Download failure** (private/removed/region-locked video): logged
  and skipped; does not crash the run.
- **Transcription failure** (corrupt/empty audio): video marked
  `failed` in storage with a reason, visible on the dashboard, so it
  can be retried later rather than silently disappearing.
- **Malformed LLM output**: the extractor validates the returned JSON
  against an expected schema. On failure it retries once, then falls
  back to storing the raw LLM output for manual review rather than
  losing the data.
- **No mistakes found** in a video (e.g. a highlight reel with no
  commentary): a valid outcome, not an error — stored as "0 mistakes
  extracted" and shown as such.

## Known risk: code-switching

Indian sports-coaching channels frequently code-switch between Hindi
and English mid-sentence ("Hinglish"). Whisper's handling of this is
inconsistent, and getting the LLM to mirror that mixed style back
(rather than normalizing to pure Hindi or pure English) may take
prompt iteration. This will be validated for real against an actual
video from the channel during implementation, rather than assumed to
work.

## Testing

- Unit tests for the extractor's parsing/validation logic, using
  canned transcript text with known expected mistake/fix pairs — so
  schema-level correctness doesn't depend on live LLM calls.
- End-to-end run against 1–2 real videos from the channel, checked
  manually — LLM output quality is subjective, so this is eyeballed
  rather than asserted exactly in an automated test.
- Whisper's transcription output itself is not unit-tested (it's a
  pretrained model) — it's treated as an input the rest of the system
  is tested against, not code being verified.

## Phase 2 (deferred, not part of this spec)

Once Phase 1 has run against enough of the channel's back-catalog, the
extracted `(timestamp, mistake)` pairs become weak labels for the video
segments around those timestamps. That is the earliest point at which
visual/CV-based mistake detection becomes even attemptable. Whether
Phase 1 produces enough good labels to justify attempting it is the
actual go/no-go gate for Phase 2 — it needs its own brainstorming
session to scope model choice, labeling effort, and realistic accuracy
expectations once that data exists.

## Future: Approach A (scheduled automation)

After Phase 1 is proven working via manual trigger, wrap it in a
scheduled poll (e.g. Task Scheduler / cron checking the channel's
upload feed every few hours) so new uploads are processed
automatically. Deferred to its own follow-up spec so pipeline
correctness and scheduling behavior aren't debugged simultaneously.

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
spoken commentary, in the coach's original language, viewable on a
published dashboard. All downloading/transcribing/processing runs on
GitHub Actions' free hosted runners, not on the user's device — no
video or audio file is ever stored locally.

Explicitly out of scope for this spec:
- Automatic detection of new channel uploads (scheduled runs) —
  becomes its own future spec once this pipeline is proven via manual
  trigger. See "Future: scheduled automation" below.
- Any visual/computer-vision mistake detection (Phase 2, see below).
- Multi-user access or auth — this is a personal tool with a public
  results page (see "Repo & Pages visibility" below).

## Architecture

Five components, each independently testable. The first three run
inside a GitHub Actions workflow job, not on the user's machine:

1. **Downloader** — uses `yt-dlp` to pull audio + metadata (title, video
   ID, upload date) for a given YouTube URL. Runs on the Actions
   runner; the audio file lives only on the runner's ephemeral disk
   and is discarded automatically when the job ends.
2. **Transcriber** — Whisper (CPU, no GPU required — Actions runners
   have no GPU anyway) produces a timestamped transcript and
   auto-detects the spoken language. Also runs on the runner; the full
   transcript is used in-job and is **not** persisted afterward (see
   privacy note below).
3. **Mistake Extractor** — sends the transcript to an LLM (API key
   stored as a GitHub Actions repository secret) with instructions to
   identify "mistake named → fix given" moments and return them as
   structured data: `{timestamp, mistake, fix}`, written in the same
   language as the transcript.
4. **Storage** — a small SQLite (or JSON) file checked into the repo.
   Only the curated output of step 3 is committed — video ID, title,
   timestamp, mistake, fix. The full raw transcript is intentionally
   **not** committed, to limit what becomes publicly visible (see
   below).
5. **Dashboard** — a static HTML page regenerated from the results
   file at the end of each workflow run and published to **GitHub
   Pages**, so it's viewable at a URL without running anything
   locally. Lists processed videos newest-first, each expandable to
   its mistake/fix pairs with clickable timestamps
   (`youtu.be/<id>?t=<seconds>`) linking back into the video.

**Trigger**: `workflow_dispatch` with a `video_url` input — you run it
from the GitHub Actions UI (or `gh workflow run`) with the URL of the
video to process.

## Repo & Pages visibility

GitHub Pages' free tier only serves public repos (private-repo Pages
needs a paid GitHub plan). So this repo must be public: the workflow
code and the committed results file (curated mistake/fix pairs) are
visible to anyone with the link. Raw full transcripts are kept out of
the repo entirely specifically to minimize what's exposed under that
constraint — only the same curated summary that appears on the
dashboard ever gets persisted.

## Data flow

```
[GitHub Actions runner, triggered manually with a video URL]
  Downloader (audio + metadata, ephemeral)
    → Transcriber (timestamped transcript + detected language, ephemeral)
    → Mistake Extractor (structured mistake/fix list, in original language)
    → commit curated results to repo (SQLite/JSON — small, text-only)
[end of job — audio/transcript discarded, nothing persists but the results]

[on push] → GitHub Pages rebuild → static dashboard published
```

## Error handling

- **Dedup**: video ID is checked against storage before processing;
  already-processed videos are skipped, not reprocessed.
- **Download failure** (private/removed/region-locked video): the
  workflow job fails with a clear log message; nothing is committed.
  Since all state is ephemeral on the runner, there's nothing to clean
  up — just re-run with a valid URL.
- **Transcription failure** (corrupt/empty audio): same — job fails
  with a logged reason, nothing partial gets committed to the repo.
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

## Future: scheduled automation

After Phase 1 is proven working via manual `workflow_dispatch` runs,
automatic detection of new channel uploads can reuse the same GitHub
Actions workflow almost unchanged: add a `schedule:` trigger (cron,
also free) that checks the channel's upload feed and calls the
existing job for anything new, instead of a human supplying the URL.
No new infrastructure needed — same runner, same pipeline. Still
deferred to its own follow-up spec so pipeline correctness and
scheduling behavior aren't debugged simultaneously.

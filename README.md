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

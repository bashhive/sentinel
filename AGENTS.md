# Sentinel repository rules

- Sentinel is the public publishing capability. It does not consume Data Breach
  Scanner or private-assistant events.
- Adelaide reads only `.adelaide/report.json` (contract v1, /Users/raf/Code/adelaide/docs/REPO_REPORTS.md); this repo keeps ownership of its bot.
  The report holds public KEV facts and feed health only.
- Every live run must use the explicit `public_brand` execution profile and a
  recorded attribution approval reference.
- Public alerts must validate against the strict contract and must not contain
  victim, watchlist, personal-contact, credential, or private-outbox fields.
- Credentials reach the process only as `HIVESEC_*` environment variables. The
  scheduled wrapper sources the Telegram token and chat id from the git-ignored
  repository `.env` (since commit 9c16c12); optional Worker intake credentials
  come from the `com.hivesec.sentinel.*` Keychain namespace. Never commit `.env`,
  reuse another project's service names, or print retrieved values.
- Direct authoritative public feeds are permitted. Do not add active scanning,
  credential testing, scanner outbox ingestion, or personal monitoring.
- Active documentation and operator output use English. Historical material
  belongs under `archive/<classification>/<date>/`.
- A delivered alert is never delivered twice: record it as seen per alert and
  per channel, as soon as the channel named by `--record-on` accepts it. Never
  make that decision per batch again.
- Never swallow a delivery failure silently. `Publisher._request` may contain
  the exception and return `False`, but it must log the channel, host and real
  status or exception type first.
- Use `.venv/bin/python -m pytest` as the test gate. The virtualenv is
  uv-managed and ships neither pip nor pytest, so run `uv sync --extra dev`
  first (or `uv run --extra dev pytest -q`).

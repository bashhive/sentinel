# Sentinel repository rules

- Sentinel is the public publishing capability. It does not consume Data Breach
  Scanner or Butler private events.
- Every live run must use the explicit `public_brand` execution profile and a
  recorded attribution approval reference.
- Public alerts must validate against the strict contract and must not contain
  victim, watchlist, personal-contact, credential, or private-outbox fields.
- Credentials stay in the Sentinel-specific macOS Keychain namespace. Never
  reuse Butler service names or print retrieved values.
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

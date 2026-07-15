# HiveSec Sentinel architecture

```mermaid
flowchart LR
    S["Public security sources"] --> B["Butler Cyber Radar"]
    B -->|"MUST item only"| G["OMLX public synthesis"]
    G --> A["PublicAlert contract"]
    A --> T["Telegram @hivesecsentinelbot"]
    A --> R["GitHub repository_dispatch"]
    R --> P["BASH GitHub Pages feed"]
```

## Boundary

- Butler is the only executable runtime.
- This repository is documentation-only.
- Public alerts are derived from public-source Cyber Radar MUST items, not from private
  Data Breach Scanner events.
- OMLX receives bounded public facts inside untrusted-content delimiters.
- The BASH site accepts only alerts with `source=HiveSec Sentinel`.

## Public contract

```json
{
  "schema_version": 1,
  "id": "hivesec-<stable digest>",
  "title": "HiveSec Sentinel — incident title",
  "message": "Bounded public alert text",
  "severity": "critical",
  "source": "HiveSec Sentinel",
  "published_at": "2026-07-15T10:00:00+00:00"
}
```

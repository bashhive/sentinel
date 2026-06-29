"""Public alert contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class PublicAlert:
    schema_version: int
    id: str
    title: str
    message: str
    severity: str
    source: str
    published_at: str
    report_digest: str
    degraded: bool

    def public_dict(self) -> dict[str, object]:
        result = asdict(self)
        result.pop("report_digest")
        result.pop("degraded")
        return result

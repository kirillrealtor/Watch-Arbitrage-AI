from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator, Protocol, runtime_checkable


class SourceScope(Protocol):
    pass


class RawObservation(Protocol):
    pass


class ParsedListing(Protocol):
    pass


class ParsedBatch(Protocol):
    pass


class HealthIssue(Protocol):
    pass


@dataclass(frozen=True)
class SourceItemRef:
    source_key: str
    external_id: str


@runtime_checkable
class SourceAdapter(Protocol):
    source_key: str
    adapter_version: str

    async def discover(self, scope: SourceScope) -> AsyncIterator[SourceItemRef]: ...
    async def fetch(self, item: SourceItemRef) -> RawObservation: ...
    def parse(self, raw: RawObservation) -> ParsedListing: ...
    def stable_external_id(self, parsed: ParsedListing) -> str: ...
    def health_assertions(self, batch: ParsedBatch) -> list[HealthIssue]: ...

from __future__ import annotations

from datetime import datetime
from typing import Optional


class MoodTag:
    def __init__(self, name: str, intensity: int) -> None:
        self.name = name
        self.intensity = intensity

    def __repr__(self) -> str:
        return f"MoodTag(name='{self.name}', intensity={self.intensity})"


class JournalEntry:
    def __init__(
        self,
        id: str,
        timestamp: datetime,
        transcript: str,
        moods: Optional[list[MoodTag]] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[str] = None,
    ) -> None:
        self.id = id
        self.timestamp = timestamp
        self.transcript = transcript
        self.moods = moods if moods is not None else []
        self.tags = tags if tags is not None else []
        self.summary = summary

    def __repr__(self) -> str:
        return f"JournalEntry(id='{self.id}', timestamp={self.timestamp}, moods={self.moods})"

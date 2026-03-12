import uuid
from datetime import datetime

from db import get_collection
from models import JournalEntry, MoodTag
# from pydantic import BaseModel

collection = get_collection()


def add_entry(transcript: str, moods: list[MoodTag], tags: list[str]):
    """Saves an entry to the chroma_db diary collection as a diary entry

    Args:
        transcript (str): transcript of the audio diary entry
        moods (list[MoodTag]): list of mood tags associated with this diary entry
        tags (list[str]): list of general tags associated with this diary entry (i.e, triggers, themes, environment)
    """
    entry = JournalEntry(
        id=f"{datetime.now().strftime('%Y-%m-%d')}_{uuid.uuid4()}",
        timestamp=datetime.now(),
        transcript=transcript,
        moods=moods,
        tags=tags,
    )

    metadata = {
        "date": entry.timestamp.strftime("%Y-%m-%d"),
        "moods": [{"name": m.name, "intensity": m.intensity} for m in entry.moods],
        "tags": entry.tags,
    }

    collection.add(ids=[entry.id], documents=[entry.transcript], metadatas=[metadata])

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
        "moods": ",".join(f"{m.name}:{m.intensity}" for m in entry.moods),
        "tags": (",").join(entry.tags),
    }

    collection.add(ids=[entry.id], documents=[entry.transcript], metadatas=[metadata])


if __name__ == "__main__":
    # Test voice entry
    add_entry(
        transcript=(
            "Feeling pretty scattered today. Work was overwhelming and I "
            "snapped at a colleague over something small. Didn't sleep well "
            "last night and skipped lunch which always makes things worse."
        ),
        moods=[
            MoodTag(name="irritable", intensity=7),
            MoodTag(name="anxious", intensity=6),
            MoodTag(name="ashamed", intensity=4),
        ],
        tags=["work", "poor sleep", "skipped meal"],
    )

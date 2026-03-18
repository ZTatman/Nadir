from functools import lru_cache
from pathlib import Path

import chromadb

_DB_PATH = str(Path(__file__).parent / "chroma_db")


@lru_cache(maxsize=1)
def get_diary_collection():
    """Retrieves diary chromadb collection by either retrieving one that was already created or by creating a new one

    Returns:
        A chromadb collection with the name "diary"
    """
    client = chromadb.PersistentClient(_DB_PATH)
    return client.get_or_create_collection(
        name="diary", metadata={"hnsw:space": "cosine"}
    )

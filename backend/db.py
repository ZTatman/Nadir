import chromadb
from pathlib import Path

_DB_PATH = str(Path(__file__).parent / "chroma_db")


def get_collection():
    """
    Retrieves chromadb collection by either retrieving one that was already created or by creating a new one
    """
    client = chromadb.PersistentClient(_DB_PATH)
    return client.get_or_create_collection(
        name="diary", metadata={"hnsw:space": "cosine"}
    )

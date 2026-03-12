import chromadb


def get_collection():
    """
    Retrieves chromadb collection by either retrieving one that was already created or by creating a new one
    """
    client = chromadb.PersistentClient("./chroma_db")
    return client.get_or_create_collection(
        name="diary", metadata={"hnsw:space": "cosine"}
    )

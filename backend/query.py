from functools import lru_cache

from db import get_diary_collection
from dotenv import load_dotenv
from openai import OpenAI

model = "llama3.2"


@lru_cache(maxsize=1)
def get_openai_client():
    """Loads environement variables and creates a cached OpenAI client.

    Returns:
        An OpenAI client
    """
    load_dotenv()
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    return client


def query_entries(user_question: str) -> str:
    """Query the diary entries using RAG and return an AI-generated answer.

    Args:
        user_question: The question to ask about emotional patterns

    Returns:
        A string response from the AI based on relevant diary entries
    """
    # create openai client and connect to chromadb
    client = get_openai_client()
    collection = get_diary_collection()

    n = min(3, collection.count())
    if n == 0:
        return "No diary entries found. Record some entries first."

    # ── 1. Retrieve relevant entries from ChromaDB ────────────────────
    results = collection.query(query_texts=[user_question], n_results=n)
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    # ── 2. Build context string ────────────────────────────────────────
    context = ""
    for doc, meta in zip(documents, metadatas, strict=True):
        moods = meta.get("moods", "unknown") or "unknown"
        tags = meta.get("tags", "none") or "none"
        context += (
            f"Date: {meta.get('date', 'unknown')} | Moods: {moods} | Tags: {tags}\n"
        )
        context += f"Entry: {doc}\n\n"

    # ── 3. Build prompt ────────────────────────────────────────────────
    prompt = f"""
    You are a warm, concise journaling assistant.
    Answer in 1-2 sentences maximum.
    Always end by asking if the user wants to explore further.
    Use only the journal entries below — do not invent details.

    Journal entries:
    {context}

    Question: {user_question}
    """

    # ── 4. Send to model and return response ──────────────────────────
try:
    response = client.with_options(timeout=30.0).chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}]
    )
except (APITimeoutError, APIConnectionError):
    return "I couldn't reach the local model right now. Please try again."

return (response.choices[0].message.content or "").strip()

if __name__ == "__main__":
    # Interactive CLI loop for testing
    try:
        user_question = input(
            "Ask a question about your emotional patterns (q to quit): "
        ).strip()

        while True:
            if user_question.lower() == "q":
                break

            print("\n\n" + query_entries(user_question))
            user_question = input("\nAsk another question (q to quit): ").strip()
    finally:
        print("Chat ended...")

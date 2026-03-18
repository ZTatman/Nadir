from openai import OpenAI
from dotenv import load_dotenv
from db import get_collection

if not load_dotenv():
    print("⚠️  Warning: .env file not found")

model = "llama3.2"

# create openai client for local model
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

# connect to chromadb
collection = get_collection()


def query_entries(user_question: str) -> str:
    """Query the diary entries using RAG and return an AI-generated answer.

    Args:
        user_question: The question to ask about emotional patterns

    Returns:
        A string response from the AI based on relevant diary entries
    """
    n = min(3, collection.count())
    if n == 0:
        return "No diary entries found. Record some entries first."

    # ── 1. Retrieve relevant entries from ChromaDB ────────────────────
    results = collection.query(query_texts=[user_question], n_results=n)
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    # ── 2. Build context string ────────────────────────────────────────
    context = ""
    for doc, meta in zip(documents, metadatas):
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
    response = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


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

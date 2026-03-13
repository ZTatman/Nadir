from openai import OpenAI
from dotenv import load_dotenv
from db import get_collection

if not load_dotenv():
    print("⚠️  Warning: .env file not found")

model = "llama3.2"

# create openai client for local model
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

# connect and query chromadb
collection = get_collection()

# Use a simple loop for now to discuss with your diary entries
try:
    user_question = input(
        "Ask a question about your emotional patterns (q to quit): "
    ).strip()

    while True:
        # check if user quitting
        if user_question.lower() == "q":
            break

        # ── 1. Retrieve relevant entries from ChromaDB ────────────────────
        results = collection.query(query_texts=[user_question], n_results=3)
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]

        # ── 2. Build context string — prompt built AFTER this loop ────────
        context = ""
        for doc, meta in zip(documents, metadatas):
            moods = meta.get("moods", "unknown") or "unknown"
            tags = meta.get("tags", "none") or "none"
            context += (
                f"Date: {meta.get('date', 'unknown')} | Moods: {moods} | Tags: {tags}\n"
            )
            context += f"Entry: {doc}\n\n"

        # ── 3. Build prompt once, after all entries are in context ─────────
        prompt = f"""
        You are a warm, concise journaling assistant.
        Answer in 1-2 sentences maximum.
        Always end by asking if the user wants to explore further.
        Use only the journal entries below — do not invent details.

        Journal entries:
        {context}

        Question: {user_question}
        """

        # ── 4. Send to model and print response ───────────────────────────
        response = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}]
        )
        print("\n\n" + response.choices[0].message.content)
        user_question = input("\nAsk another question (q to quit): ").strip()
finally:
    print("Chat ended...")

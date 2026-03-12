from openai import OpenAI
from dotenv import load_dotenv
from db import get_collection

is_env_vars_loaded = load_dotenv()
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

        # create context for prompt to local ai model
        results = collection.query(query_texts=[user_question], n_results=3)
        context = ""
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        for doc, meta in zip(documents, metadatas):
            moods = (
                ", ".join(
                    f"{m['name']}({m['intensity']})" for m in meta.get("moods", [])
                )
                or "unknown"
            )
            tags = ", ".join(meta.get("tags", [])) or "none"
            context += (
                f"Date: {meta.get('date', 'unknown')} | Moods: {moods} | Tags: {tags}\n"
            )
            context += f"Entry: {doc}\n\n"

        prompt = f"""
You are a calm, insightful journaling assistant.
Use ONLY the provided journal entries and metadata.

If the entries don’t support a clear answer, say so.
Keep it concise (max 120 words).

Respond exactly in this format:
------------------------------
Summary: ...
Key pattern:
...
Evidence:
- YYYY-MM-DD: ...
- YYYY-MM-DD: ...
If unsure:
...
------------------------------

Journal Entries:
{context}

Question: {user_question}
"""
        # send question to local ai model and print response
        response = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}]
        )
        print("\n\n" + response.choices[0].message.content)

        user_question = input("\nAsk another question (q to quit): ").strip()
finally:
    print("Chat ended...")

# Nadir — Voice Mood Diary

AI-powered voice journal with mood tracking and pattern discovery.

## What It Does

- Records voice entries and transcribes them to text
- Uses AI to extract moods, triggers, and themes from entries
- Stores entries in a local vector database (ChromaDB)
- Lets you ask questions about your emotional patterns over time

## Project Structure

```
├── main.py          # Entry point
├── app.py           # Streamlit UI
├── store.py         # Save entries to ChromaDB
├── query.py         # Query entries with RAG
├── db.py            # ChromaDB connection
├── models.py        # Data classes (MoodTag, JournalEntry)
├── PLAN.md          # [Full build plan](./PLAN.md)
├── chroma_db/       # Local vector database
```

## Build Plan

See [PLAN.md](./PLAN.md) for detailed phases and step-by-step instructions.

## Setup

```bash
# Install dependencies
uv sync

# Add your OpenAI API key to .env
echo "OPENAI_API_KEY=your_key_here" > .env
```

## Running

```bash
# Run the Streamlit app
uv run streamlit run main.py

# Or run the query CLI
uv run python query.py
```

## Status

Currently in Phase 2-3 of the build plan. Core storage and querying work; voice recording and AI metadata extraction coming next.

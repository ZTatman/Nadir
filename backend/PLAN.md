# 🎙️ Voice Mood Diary — Complete Build Plan

> AI-Powered Voice Journal with Mood Tracking & Pattern Discovery  
> Python + Streamlit + RAG | Beginner Friendly

---

## How to Use This Plan

This plan takes you from zero to a fully working voice diary app you can use every day. Each phase builds on the last. You never need to know everything upfront — just follow one step at a time.

---

## Project Overview

You are building a voice-first personal diary that:

- Records your voice and transcribes it to text automatically
- Uses AI to extract your mood, energy level, and triggers from what you said
- Stores everything in a local vector database on your computer
- Lets you ask deep questions about your emotional patterns over time
- Helps you understand what triggers your mood swings

> 🔒 **Privacy First:** Your data never leaves your computer unless you choose. No cloud, no subscriptions, no one reading your private thoughts.

### The Final App — Two Modes

**Mode 1 — Record Entry:** Press a button, speak freely, AI auto-tags your mood and saves it.

**Mode 2 — Ask Questions:** Type a question like _"What triggers my low moods?"_ and get pattern-based answers drawn from all your past entries.

---

## Your Tech Stack

| Tool                  | What It Does         | Why You Need It                                             |
| --------------------- | -------------------- | ----------------------------------------------------------- |
| Python                | Programming language | The foundation everything is built on                       |
| Streamlit             | Web UI framework     | Turns Python scripts into a real app with buttons and chat  |
| OpenAI Whisper        | Speech-to-text       | Converts your voice recordings into text with high accuracy |
| OpenAI API / Claude   | AI language model    | Extracts mood/triggers and answers pattern questions        |
| LangChain             | RAG framework        | Connects your entries to the AI for question answering      |
| ChromaDB              | Vector database      | Stores your entries so they can be searched by meaning      |
| sounddevice / PyAudio | Audio recording      | Captures your microphone input in Python                    |

---

## Project Folder Structure

Create this folder structure on your computer before you start coding:

```
voice_diary/
├── app.py                  ← Main Streamlit app (you run this)
├── record.py               ← Microphone recording
├── transcribe.py           ← Whisper: audio → text
├── extract_metadata.py     ← AI: pulls mood/triggers from text
├── store.py                ← Saves entries to ChromaDB
├── query.py                ← RAG: answers your pattern questions
├── requirements.txt        ← List of packages to install
├── .env                    ← Your API keys (never share this file)
├── /journal_entries        ← Raw text backups of every entry
└── /chroma_db              ← Your local vector database
```

> ⚠️ **Important:** The `.env` file holds your secret API keys. Never upload this to GitHub or share it with anyone.

---

## Phase 1 — Environment Setup

**Estimated time:** 2–3 hours | **Difficulty:** Beginner

### Step 1: Install Python Tools

Open your terminal (Mac: Terminal app, Windows: Command Prompt or PowerShell) and run:

```bash
# Install UV (package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create your project
uv init voice_diary
cd voice_diary

# Add all dependencies
uv add streamlit langchain langchain-community chromadb
uv add openai pydantic openai-whisper sounddevice scipy python-dotenv
```

### Step 2: Get Your API Key

- Go to `platform.openai.com` and create an account
- Add $5 of credit (will last weeks of testing)
- Create an API key and copy it
- Create a file called `.env` in your project folder
- Add this line to it:

```
OPENAI_API_KEY=your_key_here
```

### Step 3: Test Your Setup

Create a file called `test.py` and run it to confirm everything works:

```python
import openai, chromadb, streamlit
print("All imports successful!")
```

```bash
uv run python test.py
```

> ✅ **Phase 1 Complete when:** You can run `test.py` with no errors and see the success message.

---

## Phase 2 — Text Entry + RAG (No Voice Yet)

**Estimated time:** 1 day | **Difficulty:** Beginner–Intermediate

Build the brain of the app first. Skip voice for now — just type entries to test the RAG layer.

### What You Build in This Phase

| Task           | What You Do                                              | Outcome                 |
| -------------- | -------------------------------------------------------- | ----------------------- |
| `store.py`     | Save a text entry + metadata to ChromaDB                 | Entries persist to disk |
| `query.py`     | Ask a question, retrieve relevant entries, get AI answer | RAG is working          |
| Basic `app.py` | Streamlit UI with text input and question box            | Usable in browser       |

### The Key Code Concepts

**Saving an entry (`store.py`):**

```python
import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("diary")

collection.add(
    documents=[entry_text],
    metadatas=[{"date": "2026-03-10", "mood": "anxious"}],
    ids=[unique_id]
)
```

**Asking a question (`query.py`):**

```python
results = collection.query(
    query_texts=["What triggers my low moods?"],
    n_results=5   # retrieve 5 most relevant entries
)
# Then send results + question to OpenAI to get an answer
```

**Basic Streamlit UI (`app.py`):**

```python
import streamlit as st

st.title("🎙️ Voice Mood Diary")

mode = st.sidebar.radio("Mode", ["Record Entry", "Ask Questions"])

if mode == "Record Entry":
    entry = st.text_area("Type your journal entry:")
    if st.button("Save Entry"):
        # call store.py here
        st.success("Entry saved!")

if mode == "Ask Questions":
    question = st.text_input("Ask about your patterns:")
    if question:
        # call query.py here
        st.write(answer)
```

> ✅ **Phase 2 Complete when:** You can type a journal entry, save it, ask a question, and get a meaningful AI answer back.

---

## Phase 3 — Add Voice Recording + Whisper

**Estimated time:** 1–2 days | **Difficulty:** Intermediate

Now you add the voice layer on top of your working RAG system.

### What You Build in This Phase

| Task            | What You Do                                                  | Outcome                          |
| --------------- | ------------------------------------------------------------ | -------------------------------- |
| `record.py`     | Record audio from microphone using sounddevice               | You can record your voice        |
| `transcribe.py` | Send audio file to Whisper, get back text                    | Voice becomes text automatically |
| Update `app.py` | Add a Record button that triggers record → transcribe → save | Full voice entry flow works      |

### The Key Code Concepts

**Recording audio (`record.py`):**

```python
import sounddevice as sd
import scipy.io.wavfile as wav

def record(seconds=60, filename="recording.wav"):
    audio = sd.rec(int(seconds * 44100), samplerate=44100, channels=1)
    sd.wait()   # wait until done
    wav.write(filename, 44100, audio)
```

**Transcribing with Whisper (`transcribe.py`):**

```python
import whisper

model = whisper.load_model("base")   # downloads once, ~150MB

def transcribe(filename: str) -> str:
    result = model.transcribe(filename)
    return result["text"]
```

> ✅ **Phase 3 Complete when:** You can press Record, speak for 30 seconds, and see your words appear as text on screen.

---

## Phase 4 — AI Metadata Extraction

**Estimated time:** 1 day | **Difficulty:** Intermediate

After transcription, you send the text to an AI and ask it to extract structured information about your emotional state. You never fill this out manually — the AI does it automatically.

### Your Extraction Prompt

Send this to the AI with your transcript:

```
Read this journal entry and extract the following.
Respond in JSON only, no other text:

- mood: one word describing the dominant mood
- energy: low, medium, or high
- triggers: list of things that caused the mood
- themes: list of life areas mentioned (work, relationships, health, etc.)
- intensity: number from 1-10 (1=very low, 10=very high)
- swing_direction: high, low, or neutral

Entry: {transcript}
```

### What You Get Back

```json
{
  "mood": "anxious",
  "energy": "low",
  "triggers": ["work deadline", "poor sleep"],
  "themes": ["work", "health"],
  "intensity": 7,
  "swing_direction": "low"
}
```

### Validate It with Pydantic (`extract_metadata.py`)

```python
from pydantic import BaseModel

class EntryMetadata(BaseModel):
    mood: str
    energy: str
    triggers: list[str]
    themes: list[str]
    intensity: int
    swing_direction: str

# Pydantic catches bad AI output immediately
metadata = EntryMetadata(**json_response)
```

This JSON gets stored as metadata alongside your entry in ChromaDB. Over time it builds a rich, queryable picture of your emotional life.

> ✅ **Phase 4 Complete when:** Every saved entry automatically has mood, energy, triggers, and intensity attached to it.

---

## Phase 5 — Full Streamlit UI

**Estimated time:** 1–2 days | **Difficulty:** Intermediate

Polish everything into a proper two-mode interface you will actually enjoy using.

### Mode 1: Record New Entry

- Big red Record button
- Shows recording timer while you speak
- Displays transcript after recording
- Shows auto-detected mood, energy, and triggers
- Save button to store to ChromaDB

### Mode 2: Reflect / Ask Questions

- Chat input box
- Suggested questions to get you started
- AI response with references to which entries it used
- Entry count and date range shown in sidebar

### Suggested Starter Questions to Build In

Pre-load these as clickable buttons so you can use the app immediately:

- "What triggers my low moods most often?"
- "What do my highest energy days have in common?"
- "How long do my low periods typically last?"
- "What activities or events improve my mood?"
- "What was I worried about 3 months ago?"
- "When was the last time I felt truly at peace?"

> ✅ **Phase 5 Complete when:** The app looks and feels like a real product you want to open every day.

---

## Phase 6 — Weekly Reflection Feature

**Estimated time:** Half a day | **Difficulty:** Beginner (by this point)

Add one special feature: every week, the app automatically generates a gentle summary of your emotional week.

### How It Works

- On Sunday evenings (or whenever you open the app), it fetches your last 7 entries
- Sends them to the AI with a reflection prompt
- Generates a warm, non-judgmental summary of your week
- Notes patterns, improvements, and things to watch

### Example Weekly Summary

> _"This week your energy was generally low Monday through Wednesday, with intensity scores averaging 3/10. Thursday showed a notable shift after you mentioned going for a walk — your entries after outdoor time consistently show higher mood scores. Work deadlines appeared as a trigger in 4 of 7 entries. Friday and Saturday were your highest energy days this week."_

> ✅ **Phase 6 Complete when:** You get an automatic weekly digest that surfaces patterns you wouldn't have noticed yourself.

---

## Full Build Roadmap at a Glance

| Phase | Name      | What You Build                                     | Done When...                          |
| ----- | --------- | -------------------------------------------------- | ------------------------------------- |
| 1     | Setup     | Install tools, get API key, test imports           | `test.py` runs with no errors         |
| 2     | RAG Core  | Text entries + ChromaDB + question answering       | Can ask questions about typed entries |
| 3     | Voice     | Microphone recording + Whisper transcription       | Voice becomes text on screen          |
| 4     | Metadata  | AI extracts mood, energy, triggers from transcript | Every entry has auto-tags             |
| 5     | UI Polish | Full Streamlit two-mode interface                  | App feels real and usable             |
| 6     | Weekly    | Auto weekly reflection summaries                   | You get a Sunday digest               |

---

## Toolchain Summary

| Tool                  | Purpose                                                       |
| --------------------- | ------------------------------------------------------------- |
| **UV**                | Package manager — faster than pip, simpler than Poetry        |
| **Pydantic**          | Data validation — defines shapes for entries and AI responses |
| **Pyright / Pylance** | Type checker — catches bugs as you type in VS Code            |
| **Ruff**              | Linter + formatter — keeps your code clean                    |
| **VS Code**           | Editor — ties everything together                             |

---

## Tips for Success

### When You Get Stuck

- Google the exact error message — almost every Python error has a Stack Overflow answer
- Ask Claude to explain what an error means — paste the full error
- Don't skip phases — each one builds on the last
- It's normal for Phase 2 to take longer than expected. That's where the real learning happens.

### Common Beginner Mistakes to Avoid

- Trying to build everything at once — do one phase at a time
- Not testing after each small change — test often
- Ignoring error messages — read them carefully, they tell you exactly what's wrong
- Skipping the `.env` file — hardcoding API keys in code is a security risk

### How to Run the App

Once you have `app.py` built, run the whole app with one command:

```bash
uv run streamlit run app.py
```

Your browser will open automatically at `localhost:8501` — that's your app running locally.

---

## What Comes After This

Once you finish all 6 phases, here is where you can go next:

- Deploy the backend to a server (Railway or Render — both have free tiers)
- Learn FastAPI to turn your Python code into a proper API
- Build a React Native or Flutter phone app that connects to your backend
- Add Ollama for a fully private, fully local version with no API costs
- Add charts and visualizations of your mood over time using Plotly

---

## What You Will Have Learned

By the time you finish this project, you will have hands-on experience with:

- **RAG** — retrieval-augmented generation
- **LangChain** — the industry standard RAG framework
- **ChromaDB** — local vector database
- **Whisper** — speech-to-text used in real products
- **Structured LLM outputs** — extracting JSON from AI, a hugely valuable skill
- **Pydantic** — data validation used across the Python AI ecosystem
- **Streamlit** — building real browser UIs in pure Python
- **UV** — modern Python package management

That is a genuinely strong AI engineering foundation — built by doing, not just reading.

---

_Good luck. Build something you are proud of. 🐦_

---

# Smart Podcast Finder

AI that finds the episodes you'll love — a durable AI pipeline that analyzes YouTube and Spotify podcast channels, fetches real video transcripts, and delivers personalized recommendations based on your interests.

Built with **Temporal** for reliability, **AWS Bedrock (Llama 3.3 70B)** for intelligence, **FastAPI** for a beautiful developer experience, and **YouTube Transcript API** for deep content analysis.

---

## Features

### 🎯 Personalized Recommendations
- Enter any YouTube channel or Spotify show name along with your interests
- AI parses your interests into structured keywords and topics
- Every video is scored 0–100 based on relevance to your interests
- Results are sorted by relevance with clear explanations for each score

### 📝 Transcript Analysis
- Automatically fetches real video transcripts from YouTube
- Transcript data is used by the AI to understand what was actually discussed in each episode
- Transcript badge on each card — click to expand and read the full transcript
- Produces significantly more accurate rankings than metadata-only analysis

### 🔄 Durable Execution with Temporal
- Every step runs as a Temporal activity with automatic retries
- If any step fails (API timeout, rate limit, network error), it retries automatically
- No data is lost — the pipeline picks up exactly where it left off
- Full observability via the Temporal dashboard

### 📊 Channel Intelligence
- AI-generated channel summary describing the podcast's focus and format
- 3–5 key insights about recurring themes, discussion depth, and content patterns
- Content tone classification: educational, entertainment, news, tutorial, or mixed

### 🎵 Multi-Platform Support
- **YouTube**: Full support with video metadata, tags, chapters, and transcripts
- **Spotify**: Podcast show search with episode metadata and duration filtering

### ⚡ Parallel Processing Pipeline
The pipeline runs in 4 stages, with stages 2a/2b and 3a/3b running in parallel for speed:

| Stage | Activity | What Happens |
|---|---|---|
| 1. Search | `search_youtube` / `search_spotify` | Finds podcast-length videos (10+ min) on the channel |
| 2a. Parse | `extract_interests` | AI extracts structured keywords and topics from your input |
| 2b. Transcripts | `fetch_transcripts` | Fetches real video transcripts from YouTube (parallel with 2a) |
| 3a. Rank | `rank_videos` | AI scores each video 0–100 using metadata + transcripts |
| 3b. Summarize | `generate_summary` | AI produces channel insights and content tone (parallel with 3a) |

### 🎨 Modern UI
- Dark-themed interface with violet/black color scheme
- Real-time pipeline progress indicator with animated steps
- Skeleton loading states during analysis
- Video thumbnail cards with relevance score bars
- Clickable transcript badges that expand to show full transcript text
- Responsive design for desktop and mobile

---

## Tech Stack

| Layer | Technology | Role |
|---|---|---|
| Orchestration | Temporal | Durable workflows, retries, observability |
| LLM | AWS Bedrock — Llama 3.3 70B | Structured output for ranking and summarization |
| LLM (alternate) | Google Gemini 2.5 Flash | Optional — configurable via `LLM_PROVIDER` |
| API | FastAPI + Uvicorn | REST endpoints with interactive Swagger docs |
| YouTube | YouTube Data API v3 via httpx | Async video search and metadata fetching |
| Transcripts | youtube-transcript-api | Real video transcript extraction |
| Spotify | Spotify Web API via httpx | Podcast show and episode search |
| Validation | Pydantic v2 | Request/response schemas and config management |
| Frontend | Tailwind CSS + Vanilla JS | Dark-themed UI with real-time progress tracking |
| Cloud | AWS (Bedrock, IAM) | LLM inference and authentication |

---

## Prerequisites

- Python 3.11+
- [Temporal CLI](https://docs.temporal.io/cli#install)
- [YouTube Data API v3 key](https://console.cloud.google.com/apis/credentials)
- AWS account with Bedrock access (for Llama 3.3 70B)
- AWS CLI configured with valid credentials (`aws configure`)

---

## Quick Start

### 1. Clone and install

```bash
git clone <your-repo-url>
cd smart-podcast-finder
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
YOUTUBE_API_KEY=your_youtube_api_key
LLM_PROVIDER=bedrock
BEDROCK_MODEL_ID=us.meta.llama3-3-70b-instruct-v1:0
BEDROCK_REGION=us-east-1
```

### 3. Start Temporal

```bash
temporal server start-dev
```

### 4. Start the worker

```bash
python worker.py
```

### 5. Run the API server

```bash
python run.py
```

### 6. Open the app

Navigate to `http://localhost:8000` in your browser.


---

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/analyze` | Start a new analysis workflow |
| GET | `/api/status/{id}` | Poll workflow progress |
| GET | `/api/result/{id}` | Fetch completed results |
| GET | `/health` | Health check |

---

## Project Structure

```
smart-podcast-finder/
├── activities/
│   ├── analyzer.py       # LLM activities (interest parsing, ranking, summarization)
│   ├── scraper.py        # YouTube Data API search and metadata fetching
│   ├── spotify.py        # Spotify show and episode search
│   └── transcript.py     # YouTube transcript fetching
├── app/
│   ├── config.py         # Pydantic settings (env vars, API keys)
│   ├── main.py           # FastAPI app setup, lifespan, CORS
│   └── routes.py         # REST API endpoints
├── models/
│   └── schemas.py        # Pydantic + dataclass schemas for API and workflow data
├── workflows/
│   └── insights.py       # Temporal workflow definition (pipeline orchestration)
├── static/
│   └── index.html        # Frontend UI (Tailwind CSS + Vanilla JS)
├── worker.py             # Temporal worker entrypoint
├── run.py                # API server entrypoint
├── pyproject.toml        # Python project config and dependencies
└── .env.example          # Environment variable template
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `YOUTUBE_API_KEY` | Yes | — | YouTube Data API v3 key |
| `LLM_PROVIDER` | No | `bedrock` | LLM provider: `bedrock` or `gemini` |
| `BEDROCK_MODEL_ID` | No | `us.meta.llama3-3-70b-instruct-v1:0` | AWS Bedrock model ID |
| `BEDROCK_REGION` | No | `us-east-1` | AWS region for Bedrock |
| `GEMINI_API_KEY` | If using Gemini | — | Google Gemini API key |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Gemini model name |
| `TEMPORAL_HOST` | No | `localhost:7233` | Temporal server address |
| `TASK_QUEUE` | No | `podcast-insights` | Temporal task queue name |
| `SPOTIFY_CLIENT_ID` | For Spotify | — | Spotify app client ID |
| `SPOTIFY_CLIENT_SECRET` | For Spotify | — | Spotify app client secret |

---

## How It Works

1. **You provide** a channel name and your interests
2. **Search**: The app finds the YouTube channel and searches for podcast-length videos (10+ min) relevant to your interests
3. **Parse & Transcripts**: In parallel — AI parses your interests into keywords/topics, and real video transcripts are fetched from YouTube
4. **Rank & Summarize**: In parallel — AI scores every video 0–100 using metadata + transcripts, and generates a channel summary with key insights
5. **Results**: You get scored recommendations with explanations, expandable transcripts, channel summary, key insights, and content tone analysis

Each step runs as a Temporal activity — if anything fails, it retries automatically. No data is lost.

---

## Switching LLM Providers

### AWS Bedrock (default)
```env
LLM_PROVIDER=bedrock
BEDROCK_MODEL_ID=us.meta.llama3-3-70b-instruct-v1:0
BEDROCK_REGION=us-east-1
```
Requires AWS CLI configured with valid credentials.

### Google Gemini
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
```
Note: Gemini free tier has daily quota limits.

---


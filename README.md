# ytcreate: Automated AI Video Generation Pipeline

`ytcreate` is a fully automated, production-ready AI video generation pipeline built in Python 3.12 following Clean Architecture principles. It uses LangGraph multi-agent orchestration, FastAPI, Celery, and various state-of-the-art generative AI and media composition libraries.

Given a single video prompt or topic, the system automatically writes a script, splits it into visual scenes, generates cinematic prompts, creates narration audio, calls video generation services, synchronizes audio/video assets, adds subtitles, mixes background music, generates a custom thumbnail, generates SEO metadata, and uploads the final video directly to YouTube.

---

## Architecture Overview

The system runs locally as a standalone application backed by a PostgreSQL database and a Redis message queue.

```mermaid
graph TD
    Client[FastAPI Swagger / Curl] -->|Trigger Job| API[FastAPI Server via Uvicorn]
    API -->|Enqueue Job| Celery[Celery Worker Process]
    Celery -->|Execute State Machine| Orch[Orchestrator Agent]
    
    subgraph Multi-Agent Graph (LangGraph)
        Orch --> Script[Script Writer Agent]
        Script --> Split[Scene Splitter Agent]
        Split --> Prompt[Prompt Engineer Agent]
        Prompt --> Voice[Voice Narration Agent]
        Voice --> Flow[Flow Video Agent]
        Flow --> TTS[Voice Gen Agent]
        TTS --> Composer[Video Composer Agent]
        Composer --> SEO[SEO Agent]
        SEO --> Thumb[Thumbnail Agent]
        Thumb --> YT[YouTube Upload Agent]
    end

    Orch -->|Save Progress| DB[(Local PostgreSQL)]
    Flow -->|Veo API| Veo[Google Flow API]
    TTS -->|TTS API| Speech[OpenAI / ElevenLabs]
    YT -->|OAuth API| YouTube[YouTube API]
```

### Key Components
1. **Script Writer Agent (OpenAI)**: Generates a clickable YouTube title, hook, and full video script narration.
2. **Scene Splitter Agent (OpenAI)**: Segments the script into chronological visual scenes with estimated durations.
3. **Prompt Engineer Agent (OpenAI)**: Builds cinematic prompts, specifying styles, camera motions, and lighting parameters for each scene.
4. **Voice Narration Agent (OpenAI)**: Styles raw voice script segments with emotional pacing and pause point indicators.
5. **Google Flow Video Agent (Google Flow/Veo)**: Submits prompts, polls job status, and downloads high-quality MP4 videos.
6. **Voice Generation Agent (OpenAI TTS / ElevenLabs)**: Creates high-fidelity narration audio files.
7. **Video Composer Agent (MoviePy & FFmpeg)**: Loop/stretch scene videos to synchronize with narration, overlays subtitles, mixes background audio, and merges all scene segments.
8. **Thumbnail Agent (DALL-E 3)**: Generates CTR-optimized thumbnail concepts and downloads the thumbnail PNG.
9. **SEO Agent (OpenAI)**: Formulates optimized tags, description text, and search titles.
10. **YouTube Upload Agent (YouTube Data API v3)**: Performs authenticated OAuth uploads and thumbnail attachments.
11. **Orchestrator Agent (LangGraph)**: Directs the execution flow through the LangGraph state machine.

---

## Local Pre-requisites

To run the application standalone on your local system, you must have:
1. **Python 3.12** installed.
2. **PostgreSQL** running locally (create a database named `ytcreate`).
3. **Redis** running locally (default port `6379`).
4. **FFmpeg** installed and added to your system's environment `PATH`.
5. **ImageMagick** (Optional, required for MoviePy subtitle rendering).

---

## Standalone Local Setup

### 1. Clone & Initialize Environment
```bash
cd C:\git\python\ytcreate
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory `C:\git\python\ytcreate\.env`:
```env
# Database and Broker Connections
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ytcreate
REDIS_URL=redis://localhost:6379/0

# API Keys (Configure for live generations, otherwise defaults to local mock simulation)
OPENAI_API_KEY=your-openai-api-key
GEMINI_API_KEY=your-gemini-api-key
FLOW_API_KEY=your-google-flow-api-key
ELEVENLABS_API_KEY=your-elevenlabs-api-key

# YouTube Data API Credentials
YOUTUBE_CLIENT_ID=your-youtube-client-id
YOUTUBE_CLIENT_SECRET=your-youtube-client-secret
YOUTUBE_REFRESH_TOKEN=your-youtube-refresh-token
```

---

## Running the Standalone Application

Ensure PostgreSQL and Redis services are active on your machine.

### Step 1: Start the Celery Worker Process
Open a terminal, activate your virtual environment, and run:
```bash
venv\Scripts\activate
celery -A workers.celery_tasks.celery_app worker --loglevel=info -P solo
```
> **Note:** The `-P solo` parameter is recommended for Celery workers running on Windows environments.

### Step 2: Start the FastAPI Web Server
Open a second terminal, activate your virtual environment, and run:
```bash
venv\Scripts\activate
python main.py
```
The FastAPI server will boot and initialize the database tables.

---

## API Usage

1. Open your browser and navigate to the Interactive Swagger UI: **`http://localhost:8000/docs`**
2. **Trigger a Job**:
   Send a `POST` request to `/api/jobs` with the body:
   ```json
   {
     "topic": "The mystery of dark matter and how it holds galaxies together"
   }
   ```
   *Response:*
   ```json
   {
     "job_id": "8a32b21c-a1d2-432a-bc91-23ef45ab78cd",
     "status": "PENDING"
   }
   ```
3. **Monitor Progress**:
   Send a `GET` request to `/api/jobs/8a32b21c-a1d2-432a-bc91-23ef45ab78cd` to fetch the real-time execution status of the job, metadata, and scene-level parameters.

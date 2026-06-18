import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from database.repository import async_session, VideoJobRepository, SceneRepository
from database.models import VideoJob
from workers.celery_tasks import start_video_pipeline_task
from loguru import logger

router = APIRouter(prefix="/api", tags=["Jobs"])

class CreateJobRequest(BaseModel):
    topic: str = Field(..., description="The main video topic or description prompt to generate a script and media for.")

class JobResponse(BaseModel):
    id: uuid.UUID
    topic: str
    status: str
    title: Optional[str] = None
    youtube_video_id: Optional[str] = None
    final_video_path: Optional[str] = None
    created_at: str
    updated_at: str

class SceneResponse(BaseModel):
    id: int
    scene_number: int
    voice_text: str
    video_prompt: str
    duration: float
    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    status: str

class JobDetailResponse(BaseModel):
    job: JobResponse
    scenes: List[SceneResponse]

from typing import Optional

@router.post("/jobs", response_model=Dict[str, Any], status_code=201)
async def create_job(payload: CreateJobRequest):
    """Trigger a new automated video generation pipeline job."""
    logger.info(f"API: Received request to create video job for topic: '{payload.topic}'")
    
    async with async_session() as session:
        job_repo = VideoJobRepository(session)
        job = await job_repo.create_job(payload.topic)
        job_id = job.id
        topic = job.topic
        
    # Queue background task in Celery worker
    try:
        task = start_video_pipeline_task.delay(str(job_id), topic)
        logger.info(f"API: Enqueued Celery task {task.id} for job {job_id}")
        return {"job_id": job_id, "status": "PENDING", "celery_task_id": task.id}
    except Exception as e:
        logger.error(f"API: Failed to queue Celery task: {e}")
        # Return success on job creation, but denote scheduling warning
        return {"job_id": job_id, "status": "PENDING", "warning": "Celery broker connection failed. Start worker manually."}

@router.get("/jobs", response_model=List[Dict[str, Any]])
async def list_jobs(limit: int = 20, offset: int = 0):
    """List recent video generation jobs."""
    async with async_session() as session:
        job_repo = VideoJobRepository(session)
        jobs = await job_repo.list_jobs(limit, offset)
        
        return [
            {
                "id": j.id,
                "topic": j.topic,
                "status": j.status,
                "title": j.title,
                "youtube_video_id": j.youtube_video_id,
                "created_at": j.created_at.isoformat(),
                "updated_at": j.updated_at.isoformat()
            }
            for j in jobs
        ]

@router.get("/jobs/{job_id}", response_model=Dict[str, Any])
async def get_job(job_id: uuid.UUID):
    """Fetch details and scene assets of a specific video generation job."""
    async with async_session() as session:
        job_repo = VideoJobRepository(session)
        scene_repo = SceneRepository(session)
        
        job = await job_repo.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Video job not found.")
            
        scenes = await scene_repo.get_scenes_for_job(job_id)
        
        return {
            "job": {
                "id": job.id,
                "topic": job.topic,
                "status": job.status,
                "title": job.title,
                "hook": job.hook,
                "full_script": job.full_script,
                "thumbnail_prompt": job.thumbnail_prompt,
                "thumbnail_path": job.thumbnail_path,
                "youtube_title": job.youtube_title,
                "youtube_description": job.youtube_description,
                "youtube_tags": job.youtube_tags,
                "youtube_video_id": job.youtube_video_id,
                "final_video_path": job.final_video_path,
                "error_message": job.error_message,
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat()
            },
            "scenes": [
                {
                    "id": s.id,
                    "scene_number": s.scene_number,
                    "voice_text": s.voice_text,
                    "video_prompt": s.video_prompt,
                    "duration": s.duration,
                    "video_path": s.video_path,
                    "audio_path": s.audio_path,
                    "status": s.status,
                    "flow_job_id": s.flow_job_id,
                    "video_url": s.video_url
                }
                for s in scenes
            ]
        }

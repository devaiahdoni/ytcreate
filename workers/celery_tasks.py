import asyncio
import uuid
from celery import Celery
from config.settings import settings
from loguru import logger

# Initialize Celery Application
celery_app = Celery(
    "video_pipeline_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Optional configuration settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True
)

@celery_app.task(name="workers.celery_tasks.start_video_pipeline_task", bind=True)
def start_video_pipeline_task(self, job_id: str, topic: str) -> dict:
    """Celery background worker entrypoint task that triggers the Orchestrator pipeline."""
    logger.info(f"Celery: Received task {self.request.id} for Job: {job_id}")
    
    # Import locally inside the task to avoid circular import loops
    from agents.orchestrator import PipelineOrchestrator
    
    # Instantiate the Orchestrator
    orchestrator = PipelineOrchestrator()
    
    # Run the async pipeline coroutine synchronously inside Celery's thread pool
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        job_uuid = uuid.UUID(job_id)
        result = loop.run_until_complete(
            orchestrator.execute_pipeline(job_uuid, topic)
        )
        
        if result.get("error"):
            logger.error(f"Celery: Task finished with pipeline error: {result['error']}")
            return {"status": "FAILED", "error": result["error"]}
            
        logger.info(f"Celery: Task {self.request.id} finished successfully for Job: {job_id}")
        return {"status": "COMPLETED", "youtube_video_id": result.get("youtube_video_id")}
    except Exception as e:
        logger.exception(f"Celery task crashed with unhandled exception: {e}")
        
        # Write failure status to DB
        async def record_failure():
            from database.repository import async_session, VideoJobRepository
            async with async_session() as session:
                job_repo = VideoJobRepository(session)
                job = await job_repo.get_job(uuid.UUID(job_id))
                if job:
                    job.status = "FAILED"
                    job.error_message = str(e)
                    await job_repo.update_job(job)
                    
        loop.run_until_complete(record_failure())
        return {"status": "FAILED", "error": str(e)}

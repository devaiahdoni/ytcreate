import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from config.settings import settings
from database.models import Base, VideoJob, Scene

# Setup async database connection engine
engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db() -> None:
    """Initialize database and create tables if they do not exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

class VideoJobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_job(self, topic: str) -> VideoJob:
        """Create a new video generation job."""
        job = VideoJob(
            id=uuid.uuid4(),
            topic=topic,
            status="PENDING"
        )
        self.session.add(job)
        await self.session.commit()
        return job

    async def get_job(self, job_id: uuid.UUID) -> Optional[VideoJob]:
        """Fetch a job by its unique ID."""
        result = await self.session.execute(
            select(VideoJob).where(VideoJob.id == job_id)
        )
        return result.scalars().first()

    async def list_jobs(self, limit: int = 20, offset: int = 0) -> List[VideoJob]:
        """List jobs with pagination."""
        result = await self.session.execute(
            select(VideoJob).order_by(VideoJob.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def update_job(self, job: VideoJob) -> VideoJob:
        """Update an existing job's attributes."""
        self.session.add(job)
        await self.session.commit()
        return job

class SceneRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_scene(self, job_id: uuid.UUID, scene_number: int, voice_text: str, video_prompt: str, duration: float = 5.0, **kwargs) -> Scene:
        """Create a new scene for a job."""
        scene = Scene(
            job_id=job_id,
            scene_number=scene_number,
            voice_text=voice_text,
            video_prompt=video_prompt,
            duration=duration,
            **kwargs
        )
        self.session.add(scene)
        await self.session.commit()
        return scene

    async def get_scene(self, scene_id: int) -> Optional[Scene]:
        """Get a single scene by its ID."""
        result = await self.session.execute(
            select(Scene).where(Scene.id == scene_id)
        )
        return result.scalars().first()

    async def get_scenes_for_job(self, job_id: uuid.UUID) -> List[Scene]:
        """Get all scenes associated with a video job."""
        result = await self.session.execute(
            select(Scene).where(Scene.job_id == job_id).order_by(Scene.scene_number.asc())
        )
        return list(result.scalars().all())

    async def update_scene(self, scene: Scene) -> Scene:
        """Update a scene's properties."""
        self.session.add(scene)
        await self.session.commit()
        return scene

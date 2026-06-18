import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, Float, ForeignKey, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class VideoJob(Base):
    __tablename__ = "video_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    
    # Script details
    title: Mapped[Optional[str]] = mapped_column(String(255))
    hook: Mapped[Optional[str]] = mapped_column(Text)
    full_script: Mapped[Optional[str]] = mapped_column(Text)
    
    # Thumbnail details
    thumbnail_prompt: Mapped[Optional[str]] = mapped_column(Text)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(1024))
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(1024))
    
    # SEO details
    youtube_title: Mapped[Optional[str]] = mapped_column(String(255))
    youtube_description: Mapped[Optional[str]] = mapped_column(Text)
    youtube_tags: Mapped[Optional[str]] = mapped_column(Text)  # Comma-separated or JSON list
    
    # Output and Upload details
    youtube_video_id: Mapped[Optional[str]] = mapped_column(String(100))
    final_video_path: Mapped[Optional[str]] = mapped_column(String(1024))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    scenes: Mapped[List["Scene"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", lazy="selectin"
    )

class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("video_jobs.id", ondelete="CASCADE"), nullable=False)
    scene_number: Mapped[int] = mapped_column(nullable=False)
    
    # Voice details
    voice_text: Mapped[str] = mapped_column(Text, nullable=False)
    emotion: Mapped[Optional[str]] = mapped_column(String(100))
    pause_points: Mapped[Optional[str]] = mapped_column(Text)  # JSON representation of pauses
    
    # Video generation details
    video_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    camera_motion: Mapped[Optional[str]] = mapped_column(String(255))
    lighting: Mapped[Optional[str]] = mapped_column(String(255))
    style: Mapped[Optional[str]] = mapped_column(String(255))
    negative_prompt: Mapped[Optional[str]] = mapped_column(Text)
    duration: Mapped[float] = mapped_column(Float, default=5.0)
    
    # Generation task tracking
    flow_job_id: Mapped[Optional[str]] = mapped_column(String(255))
    video_url: Mapped[Optional[str]] = mapped_column(String(1024))
    video_path: Mapped[Optional[str]] = mapped_column(String(1024))
    audio_path: Mapped[Optional[str]] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    job: Mapped["VideoJob"] = relationship(back_populates="scenes")

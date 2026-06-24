"""Database models"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(String, unique=True, nullable=False)
    hash = Column(String, nullable=False)
    language = Column(String, nullable=True)
    duration = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    subtitles = relationship("Subtitle", back_populates="video")
    jobs = relationship("Job", back_populates="video")


class Subtitle(Base):
    __tablename__ = "subtitles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    type = Column(String, nullable=False)  # original / chinese / bilingual
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    video = relationship("Video", back_populates="subtitles")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    status = Column(String, default="pending")  # pending / processing / done / failed
    progress = Column(Integer, default=0)
    current_step = Column(String, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    video = relationship("Video", back_populates="jobs")

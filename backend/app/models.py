from datetime import datetime, timezone
from sqlalchemy import ForeignKey, String, Text, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


def now():
    return datetime.now(timezone.utc)


class Artwork(Base):
    __tablename__ = "artworks"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    image_path: Mapped[str] = mapped_column(String(300), default="")
    aspect: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(String(20), default="published")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    media: Mapped[list["Media"]] = relationship(back_populates="artwork", cascade="all, delete-orphan")


class Media(Base):
    __tablename__ = "media"
    id: Mapped[int] = mapped_column(primary_key=True)
    artwork_id: Mapped[int] = mapped_column(ForeignKey("artworks.id"))
    type: Mapped[str] = mapped_column(String(20), default="video")
    url: Mapped[str] = mapped_column(String(500))
    title: Mapped[str] = mapped_column(String(200), default="")
    artwork: Mapped["Artwork"] = relationship(back_populates="media")


class Scan(Base):
    __tablename__ = "scans"
    id: Mapped[int] = mapped_column(primary_key=True)
    artwork_id: Mapped[int] = mapped_column(ForeignKey("artworks.id"), index=True)
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    user_agent: Mapped[str] = mapped_column(String(300), default="")

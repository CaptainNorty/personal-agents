from datetime import datetime

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base, BaseModel


class PodcastEpisode(Base, BaseModel):
    __tablename__ = "podcast_episodes"

    feed_url: Mapped[str] = mapped_column(Text)
    episode_title: Mapped[str] = mapped_column(Text)
    audio_url: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(default=None)
    transcript: Mapped[str | None] = mapped_column(Text, default=None)
    summary: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(Text, default="notified")

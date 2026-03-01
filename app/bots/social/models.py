from datetime import datetime

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base, BaseModel


class SocialEntry(Base, BaseModel):
    __tablename__ = "social_entries"

    prompt_sent_at: Mapped[datetime] = mapped_column()
    response_text: Mapped[str | None] = mapped_column(Text, default=None)
    responded_at: Mapped[datetime | None] = mapped_column(default=None)

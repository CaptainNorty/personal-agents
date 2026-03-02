from datetime import date, datetime

from sqlalchemy import Date, Float, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base, BaseModel


class FoodItemCache(Base, BaseModel):
    __tablename__ = "food_item_cache"

    name: Mapped[str] = mapped_column(Text)
    name_normalized: Mapped[str] = mapped_column(Text, unique=True, index=True)
    protein_g: Mapped[float] = mapped_column(Float)
    fat_g: Mapped[float] = mapped_column(Float)
    carbs_g: Mapped[float] = mapped_column(Float)
    sugar_g: Mapped[float] = mapped_column(Float)
    calories: Mapped[float] = mapped_column(Float)
    serving_qty: Mapped[float] = mapped_column(Float, default=1.0)
    serving_unit: Mapped[str] = mapped_column(Text, default="serving")
    source: Mapped[str] = mapped_column(Text)  # "nutritionix" or "claude_estimate"


class FoodLog(Base, BaseModel):
    __tablename__ = "food_logs"

    chat_id: Mapped[str] = mapped_column(Text)
    item_name: Mapped[str] = mapped_column(Text)
    protein_g: Mapped[float] = mapped_column(Float)
    fat_g: Mapped[float] = mapped_column(Float)
    carbs_g: Mapped[float] = mapped_column(Float)
    sugar_g: Mapped[float] = mapped_column(Float)
    calories: Mapped[float] = mapped_column(Float)
    serving_qty: Mapped[float] = mapped_column(Float)
    serving_unit: Mapped[str] = mapped_column(Text)
    meal_type: Mapped[str] = mapped_column(Text)  # breakfast/lunch/dinner/snack
    source: Mapped[str] = mapped_column(Text)
    logged_at: Mapped[datetime] = mapped_column()


class DailySummary(Base, BaseModel):
    __tablename__ = "daily_summaries"

    chat_id: Mapped[str] = mapped_column(Text)
    summary_date: Mapped[date] = mapped_column(Date, index=True)
    summary_text: Mapped[str] = mapped_column(Text)
    total_protein_g: Mapped[float] = mapped_column(Float)
    total_fat_g: Mapped[float] = mapped_column(Float)
    total_carbs_g: Mapped[float] = mapped_column(Float)
    total_sugar_g: Mapped[float] = mapped_column(Float)
    total_calories: Mapped[float] = mapped_column(Float)

    __table_args__ = (
        Index("ix_daily_summaries_chat_date", "chat_id", "summary_date"),
    )

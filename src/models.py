# type: ignore

from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = Column(Integer, primary_key=True)
    spotify_id = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(100))
    email = Column(String(100))
    profile_image = Column(String(200))
    spotify_token = Column(String(200))
    spotify_refresh_token = Column(String(200))
    spotify_token_expiry = Column(DateTime)
    user_embedding = Column(JSON)  # Store the user's profile embedding
    last_updated = Column(DateTime, default=datetime.utcnow)


class UserInteraction(db.Model):
    __tablename__ = "user_interaction"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    interaction_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'search', 'click', 'play'
    item_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'track', 'artist', 'album'
    item_text: Mapped[str] = mapped_column(
        String(500)
    )  # Text representation of the item
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    duration: Mapped[float] = mapped_column(Float)  # For play interactions
    relevance_score: Mapped[float] = mapped_column(
        Float
    )  # User's implicit feedback score

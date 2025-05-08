# type: ignore

from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    # Relationships
    interactions = relationship("UserInteraction", back_populates="user")
    search_sessions = relationship("SearchSession", back_populates="user")
    metrics = relationship("UserMetrics", back_populates="user", uselist=False)
    genre_stats = relationship("UserGenreStats", back_populates="user")
    artist_stats = relationship("UserArtistStats", back_populates="user")


class UserInteraction(db.Model):
    __tablename__ = "user_interaction"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    interaction_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'search', 'click', 'play', 'like'
    item_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'track', 'artist', 'album'
    item_text: Mapped[str] = mapped_column(
        String(500)
    )  # Text representation of the item
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    duration: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # For play interactions
    relevance_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.3
    )  # User's implicit feedback score
    session_id: Mapped[str | None] = mapped_column(
        String(100), ForeignKey("search_session.session_id"), nullable=True
    )
    genre: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # Genre of the track for play interactions

    # Relationships
    user = relationship("User", back_populates="interactions")
    session = relationship("SearchSession", back_populates="interactions")


# New model for search sessions
class SearchSession(db.Model):
    __tablename__ = "search_session"

    session_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    query: Mapped[str] = mapped_column(String(200), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    precision_at_5: Mapped[float] = mapped_column(Float, default=0.0)
    precision_at_10: Mapped[float] = mapped_column(Float, default=0.0)

    # Relationships
    user = relationship("User", back_populates="search_sessions")
    interactions = relationship("UserInteraction", back_populates="session")


# New model for user metrics
class UserMetrics(db.Model):
    __tablename__ = "user_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id"), unique=True, nullable=False
    )
    search_count: Mapped[int] = mapped_column(Integer, default=0)
    interaction_count: Mapped[int] = mapped_column(Integer, default=0)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Additional metrics that were previously calculated on demand
    most_played_song: Mapped[str | None] = mapped_column(String(200), nullable=True)
    most_played_artist: Mapped[str | None] = mapped_column(String(200), nullable=True)
    most_played_duration: Mapped[float] = mapped_column(Float, default=0.0)
    most_liked_album: Mapped[str | None] = mapped_column(String(200), nullable=True)
    most_liked_album_artist: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    most_liked_album_count: Mapped[int] = mapped_column(Integer, default=0)
    most_liked_artist: Mapped[str | None] = mapped_column(String(200), nullable=True)
    most_liked_artist_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationship
    user = relationship("User", back_populates="metrics")


# New model for tracking genre statistics
class UserGenreStats(db.Model):
    __tablename__ = "user_genre_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    genre: Mapped[str] = mapped_column(String(100), nullable=False)
    play_count: Mapped[int] = mapped_column(Integer, default=0)
    total_duration: Mapped[float] = mapped_column(
        Float, default=0.0
    )  # Total play duration in seconds
    last_played: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="genre_stats")

    # Add a unique constraint to ensure one row per user-genre combination
    __table_args__ = (
        db.UniqueConstraint("user_id", "genre", name="unique_user_genre"),
    )


# New model for tracking artist statistics
class UserArtistStats(db.Model):
    __tablename__ = "user_artist_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    artist: Mapped[str] = mapped_column(String(100), nullable=False)
    play_count: Mapped[int] = mapped_column(Integer, default=0)
    total_duration: Mapped[float] = mapped_column(
        Float, default=0.0
    )  # Total play duration in seconds
    last_played: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="artist_stats")

    # Add a unique constraint to ensure one row per user-artist combination
    __table_args__ = (
        db.UniqueConstraint("user_id", "artist", name="unique_user_artist"),
    )

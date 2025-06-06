import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy import desc, func

from .models import SearchSession, User, UserInteraction, UserMetrics, db


class SearchMetrics:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def start_search_session(self, user_id: int, search_query: str) -> str:
        """
        Start a new search session when a user performs a search.
        """
        session_id = str(uuid.uuid4())

        # Create a new session record
        new_session = SearchSession(
            session_id=session_id,
            user_id=user_id,
            query=search_query,
            timestamp=datetime.now(),
        )

        db.session.add(new_session)

        # Initialize or update user metrics if not exists
        metrics = db.session.query(UserMetrics).filter_by(user_id=user_id).first()
        if not metrics:
            metrics = UserMetrics(user_id=user_id, search_count=1)
            db.session.add(metrics)
        else:
            # Make sure search_count is initialized before incrementing
            if metrics.search_count is None:
                metrics.search_count = 1
            else:
                metrics.search_count += 1

        metrics.last_updated = datetime.now()

        db.session.commit()

        return session_id

    def update_session_precision(
        self, session_id: str, precision5: float, precision10: float
    ) -> None:
        """
        Update precision metrics for a session based on liked items in search results.
        """
        session = db.session.query(SearchSession).get(session_id)
        if session:
            session.precision_at_5 = precision5
            session.precision_at_10 = precision10
            db.session.commit()

    def track_interaction(
        self,
        user_id: int,
        interaction_type: str,
        item_text: str,
        item_type: str = "song",
        session_id: str | None = None,
        duration: float = 0,
    ) -> dict:
        """
        Track an interaction for the current search session and update metrics.
        Added duration parameter to properly track play duration.
        """
        self.logger.info(
            f"Saving {interaction_type} interaction to database: {item_text}"
        )

        # Find the active session if session_id not provided
        if not session_id:
            latest_session = (
                db.session.query(SearchSession)
                .filter_by(user_id=user_id)
                .order_by(SearchSession.timestamp.desc())
                .first()
            )
            session_id = latest_session.session_id if latest_session else None

        # Save interaction to database
        interaction = UserInteraction(
            user_id=user_id,
            interaction_type=interaction_type,
            item_type=item_type,
            item_text=item_text,
            timestamp=datetime.now(),
            session_id=session_id,
            duration=duration if interaction_type == "play" else None,
        )
        db.session.add(interaction)

        # Update user metrics
        metrics = db.session.query(UserMetrics).filter_by(user_id=user_id).first()
        if metrics:
            metrics.interaction_count += 1
            metrics.last_updated = datetime.now()

            # Update specific metrics based on interaction type
            if interaction_type == "play":
                self._update_most_played_metrics(metrics, user_id, item_text, duration)
            elif interaction_type == "like":
                self._update_most_liked_metrics(metrics, item_text)

        db.session.commit()

        # Return the latest metrics for the user
        return self.get_session_metrics(user_id)

    def _update_most_played_metrics(
        self, metrics: UserMetrics, user_id: int, item_text: str, duration: float
    ) -> None:
        """
        Update most played song metrics when a play interaction occurs.
        Now properly tracks play counts and durations to determine the most played song.
        """
        parts = item_text.split(" by ", 1)
        if len(parts) == 2:
            song, artist = parts
            song = song.strip()
            artist = artist.strip()

            # Get all play interactions for this song by this user
            play_interactions = (
                db.session.query(UserInteraction)
                .filter_by(user_id=user_id, interaction_type="play")
                .filter(UserInteraction.item_text.like(f"{song} by {artist}%"))
                .all()
            )

            # Calculate total play count and duration for this song
            total_count = len(play_interactions)
            total_duration = (
                sum(interaction.duration or 0 for interaction in play_interactions)
                + duration
            )

            self.logger.info(
                f"Song '{song}' by '{artist}' has been played {total_count} times with total duration {total_duration}s"
            )

            # Get the current most played song's total playtime
            current_most_played = metrics.most_played_song
            current_most_played_artist = metrics.most_played_artist
            current_most_played_duration = metrics.most_played_duration or 0

            if current_most_played and current_most_played_artist:
                current_interactions = (
                    db.session.query(UserInteraction)
                    .filter_by(user_id=user_id, interaction_type="play")
                    .filter(
                        UserInteraction.item_text.like(
                            f"{current_most_played} by {current_most_played_artist}%"
                        )
                    )
                    .all()
                )
                current_duration = sum(
                    interaction.duration or 0 for interaction in current_interactions
                )
            else:
                current_duration = 0

            # Update most played song if this one has longer total play time
            if not current_most_played or total_duration > current_duration:
                self.logger.info(
                    f"Updating most played song to '{song}' by '{artist}' with duration {total_duration}s"
                )
                metrics.most_played_song = song
                metrics.most_played_artist = artist
                metrics.most_played_duration = total_duration

    def _update_most_liked_metrics(self, metrics: UserMetrics, item_text: str) -> None:
        """Update most liked album and artist metrics when a like interaction occurs."""
        # Parse the item_text for album and artist information
        album_parts = item_text.split(" from ", 1)
        if len(album_parts) == 2:
            song_artist, album = album_parts
            album = album.strip()

            # Extract artist from song_artist (format: "song by artist")
            artist_parts = song_artist.split(" by ", 1)
            if len(artist_parts) == 2:
                artist = artist_parts[1].strip()

                # Update most liked album (simplified - would need like counting logic)
                if not metrics.most_liked_album:
                    metrics.most_liked_album = album
                    metrics.most_liked_album_artist = artist
                    metrics.most_liked_album_count = 1
                else:
                    # In a real implementation, you'd increment a counter for this album
                    # Here, we're just setting it as the most liked if it's the first one
                    pass

                # Update most liked artist (simplified)
                if not metrics.most_liked_artist:
                    metrics.most_liked_artist = artist
                    metrics.most_liked_artist_count = 1
                else:
                    # In a real implementation, you'd increment a counter for this artist
                    pass

    def get_session_metrics(self, user_id: int) -> dict:
        """
        Get metrics for the current active session.
        """
        # Get the latest session
        latest_session = (
            db.session.query(SearchSession)
            .filter_by(user_id=user_id)
            .order_by(SearchSession.timestamp.desc())
            .first()
        )

        if not latest_session:
            return {"precision@5": 0.0, "precision@10": 0.0}

        return {
            "precision@5": latest_session.precision_at_5,
            "precision@10": latest_session.precision_at_10,
        }

    def get_all_session_metrics(
        self, user_id: int, max_sessions: int = 20
    ) -> dict[str, list]:
        """
        Get metrics for all sessions for a user.
        """
        sessions = (
            db.session.query(SearchSession)
            .filter_by(user_id=user_id)
            .order_by(SearchSession.timestamp.desc())
            .limit(max_sessions)
            .all()
        )

        sessions.reverse()  # Oldest first for charting

        # Get likes per search and calculate cumulative likes
        likes_per_search = []
        cumulative_likes = []
        total_likes = 0

        for session in sessions:
            # Count likes for this session
            session_likes = (
                db.session.query(UserInteraction)
                .filter_by(
                    user_id=user_id,
                    session_id=session.session_id,
                    interaction_type="like",
                )
                .count()
            )
            likes_per_search.append(session_likes)
            total_likes += session_likes
            cumulative_likes.append(total_likes)

        search_numbers = list(range(1, len(sessions) + 1))

        return {
            "likes_per_search": likes_per_search,
            "cumulative_likes": cumulative_likes,
            "search_numbers": search_numbers,
        }

    def get_user_metrics(self, user_id: int) -> dict[str, float]:
        """
        Get aggregate metrics for a user.
        """
        metrics = db.session.query(UserMetrics).filter_by(user_id=user_id).first()

        if not metrics:
            return {
                "search_count": 0,
                "interaction_count": 0,
                "precision@5": 0.0,
                "precision@10": 0.0,
            }

        # Calculate average precision across all sessions
        sessions = db.session.query(SearchSession).filter_by(user_id=user_id).all()
        precision5 = np.mean([s.precision_at_5 for s in sessions]) if sessions else 0.0
        precision10 = (
            np.mean([s.precision_at_10 for s in sessions]) if sessions else 0.0
        )

        return {
            "search_count": metrics.search_count,
            "interaction_count": metrics.interaction_count,
            "precision@5": float(precision5),
            "precision@10": float(precision10),
        }

    def get_most_played_song(self, user_id: int) -> dict[str, str]:
        """
        Get the most played song for a user based on stored metrics.
        """
        metrics = db.session.query(UserMetrics).filter_by(user_id=user_id).first()
        logging.getLogger(__name__).info(f"User metrics for user {user_id}: {metrics}")

        if not metrics or not metrics.most_played_song:
            return {"song": "No songs played yet", "artist": "", "duration": 0}

        return {
            "song": metrics.most_played_song,
            "artist": metrics.most_played_artist or "",
            "duration": round(
                metrics.most_played_duration / 60, 1
            ),  # Convert to minutes
        }

    def get_most_liked_album(self, user_id: int) -> dict[str, str]:
        """
        Get the most liked album for a user based on stored metrics.
        """
        metrics = db.session.query(UserMetrics).filter_by(user_id=user_id).first()

        if not metrics or not metrics.most_liked_album:
            return {"album": "No albums liked yet", "artist": "", "likes": 0}

        return {
            "album": metrics.most_liked_album,
            "artist": metrics.most_liked_album_artist or "",
            "likes": metrics.most_liked_album_count,
        }

    def get_most_liked_artist(self, user_id: int) -> dict[str, str]:
        """
        Get the most liked artist for a user based on stored metrics.
        """
        metrics = db.session.query(UserMetrics).filter_by(user_id=user_id).first()

        if not metrics or not metrics.most_liked_artist:
            return {"artist": "No artists liked yet", "likes": 0}

        return {
            "artist": metrics.most_liked_artist,
            "likes": metrics.most_liked_artist_count,
        }

    def get_latest_search_metrics(self, user_id: int) -> dict[str, float]:
        """
        Get metrics for just the latest search performed by a user.
        """
        latest_session = (
            db.session.query(SearchSession)
            .filter_by(user_id=user_id)
            .order_by(SearchSession.timestamp.desc())
            .first()
        )

        if not latest_session:
            return {"precision@5": 0.0, "precision@10": 0.0}

        return {
            "precision@5": latest_session.precision_at_5,
            "precision@10": latest_session.precision_at_10,
        }

    def _reset_user_metrics(self, user_id: int) -> None:
        """
        Reset all metrics for a specific user.
        """
        try:
            # Delete all sessions
            db.session.query(SearchSession).filter_by(user_id=user_id).delete()

            # Delete all interactions
            db.session.query(UserInteraction).filter_by(user_id=user_id).delete()

            # Reset metrics or create new if not exists
            metrics = db.session.query(UserMetrics).filter_by(user_id=user_id).first()
            if metrics:
                # Reset all fields to default values
                metrics.search_count = 0
                metrics.interaction_count = 0
                metrics.most_played_song = None
                metrics.most_played_artist = None
                metrics.most_played_duration = 0.0
                metrics.most_liked_album = None
                metrics.most_liked_album_artist = None
                metrics.most_liked_album_count = 0
                metrics.most_liked_artist = None
                metrics.most_liked_artist_count = 0
                metrics.last_updated = datetime.now()
            else:
                # Create new metrics record with default values
                metrics = UserMetrics(user_id=user_id)
                db.session.add(metrics)

            # Commit all changes to ensure they're saved
            db.session.commit()

            self.logger.info(f"Reset all metrics for user {user_id}")
        except Exception as e:
            # Log any errors and roll back transaction
            self.logger.error(f"Error resetting metrics for user {user_id}: {str(e)}")
            db.session.rollback()
            raise

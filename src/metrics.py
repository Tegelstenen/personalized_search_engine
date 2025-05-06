import logging
import uuid
from datetime import datetime

import numpy as np


class SearchMetrics:
    def __init__(self):
        # In-memory store for active search sessions
        self.active_sessions = {}
        # Session metrics store
        self.session_metrics = {}

    def start_search_session(self, user_id: int, search_query: str) -> str:
        """
        Start a new search session when a user performs a search.
        """
        session_id = str(uuid.uuid4())

        # Store session info
        self.active_sessions[user_id] = {
            "session_id": session_id,
            "query": search_query,
            "timestamp": datetime.now(),
            "interactions": set(),
        }

        # Initialize metrics for this session
        self.session_metrics[session_id] = {
            "precision@5": 0.0,
            "precision@10": 0.0,
            "interaction_count": 0,
            "user_id": user_id,
            "query": search_query,
            "timestamp": datetime.now(),
        }

        return session_id

    def update_session_precision(
        self, session_id: str, precision5: float, precision10: float
    ) -> None:
        """
        Update precision metrics for a session based on liked items in search results.
        """
        if session_id in self.session_metrics:
            self.session_metrics[session_id]["precision@5"] = precision5
            self.session_metrics[session_id]["precision@10"] = precision10

    def track_interaction(
        self,
        user_id: int,
        interaction_type: str,
        item_text: str,
        item_type: str = "song",
    ) -> dict | None:
        """
        Track an interaction for the current search session and update metrics.
        """
        from src.models import UserInteraction, db

        logger = logging.getLogger(__name__)

        # Save interaction to database
        interaction = UserInteraction(
            user_id=user_id,
            interaction_type=interaction_type,
            item_type=item_type,
            item_text=item_text,
            timestamp=datetime.now(),
        )
        db.session.add(interaction)
        db.session.commit()
        logger.info(f"Saved {interaction_type} interaction to database: {item_text}")

        # Update in-memory session metrics
        if user_id not in self.active_sessions:
            return None

        session = self.active_sessions[user_id]
        session_id = session["session_id"]

        session["interactions"].add(item_text)
        metrics = self.session_metrics[session_id]

        if interaction_type in ["click", "play"]:
            metrics["interaction_count"] = len(session["interactions"])

        return metrics

    def get_session_metrics(self, user_id: int) -> dict | None:
        """
        Get metrics for the current active session.
        """
        if user_id not in self.active_sessions:
            return None

        session_id = self.active_sessions[user_id]["session_id"]
        return self.session_metrics.get(session_id)

    def get_all_session_metrics(
        self, user_id: int, max_sessions: int = 20
    ) -> dict[str, list]:
        """
        Get metrics for all sessions for a user.
        """
        user_sessions = [
            metrics
            for session_id, metrics in self.session_metrics.items()
            if metrics["user_id"] == user_id
        ]

        user_sessions.sort(key=lambda x: x["timestamp"], reverse=True)

        user_sessions = user_sessions[:max_sessions]

        user_sessions.reverse()

        precision5_values = [session["precision@5"] for session in user_sessions]
        precision10_values = [session["precision@10"] for session in user_sessions]
        search_numbers = list(range(1, len(user_sessions) + 1))

        return {
            "precision@5": precision5_values,
            "precision@10": precision10_values,
            "search_numbers": search_numbers,
        }

    def get_user_metrics(self, user_id: int) -> dict[str, float | int]:
        """
        Calculate and return aggregate metrics for a user
        """
        user_sessions = [
            metrics
            for session_id, metrics in self.session_metrics.items()
            if metrics["user_id"] == user_id
        ]

        if not user_sessions:
            return {
                "search_count": 0,
                "interaction_count": 0,
                "precision@5": 0.0,
                "precision@10": 0.0,
            }

        # Calculate aggregates
        search_count = len(user_sessions)
        interaction_count = sum(
            session["interaction_count"] for session in user_sessions
        )
        precision5 = float(
            np.mean([session["precision@5"] for session in user_sessions])
        )
        precision10 = float(
            np.mean([session["precision@10"] for session in user_sessions])
        )

        return {
            "search_count": search_count,
            "interaction_count": interaction_count,
            "precision@5": precision5,
            "precision@10": precision10,
        }

    def get_most_played_song(self, user_id: int) -> dict[str, str | float]:
        """
        Get the most played song for a user based on total play duration.
        Returns a dict with song name, artist, and total duration in minutes.
        """
        from src.models import UserInteraction, db

        logger = logging.getLogger(__name__)

        # Get all play interactions for the user
        play_interactions = (
            UserInteraction.query.filter_by(
                user_id=user_id, interaction_type="play", item_type="song"
            )
            .order_by(UserInteraction.timestamp.desc())
            .all()
        )

        logger.info(
            f"Found {len(play_interactions)} play interactions for user {user_id}"
        )

        if not play_interactions:
            logger.info(f"No play interactions found for user {user_id}")
            return {"song": "No songs played yet", "artist": "", "duration": 0}

        # Group by song and sum durations
        song_durations = {}
        for interaction in play_interactions:
            # Extract song and artist from item_text (format: "song by artist")
            parts = interaction.item_text.split(" by ", 1)
            if len(parts) == 2:
                song, artist = parts
                key = (song.strip(), artist.strip())
                song_durations[key] = song_durations.get(key, 0) + (
                    interaction.duration or 0
                )
                logger.info(
                    f"Added duration {interaction.duration} to song '{song}' by '{artist}'"
                )

        if not song_durations:
            logger.info(f"No valid song durations calculated for user {user_id}")
            return {"song": "No songs played yet", "artist": "", "duration": 0}

        # Find the song with the highest total duration
        most_played = max(song_durations.items(), key=lambda x: x[1])
        song, artist = most_played[0]
        duration_minutes = most_played[1] / 60  # Convert seconds to minutes

        logger.info(
            f"Most played song for user {user_id}: '{song}' by '{artist}' with {duration_minutes:.2f} minutes"
        )

        return {"song": song, "artist": artist, "duration": round(duration_minutes, 1)}

    def get_most_liked_album(self, user_id: int) -> dict[str, str | int]:
        """
        Get the most liked album for a user based on like interactions.
        Returns a dict with album name, artist, and number of likes.
        """
        from src.models import UserInteraction, db

        logger = logging.getLogger(__name__)

        # Get all like and unlike interactions for the user
        interactions = (
            UserInteraction.query.filter(
                UserInteraction.user_id == user_id,
                UserInteraction.item_type == "song",
                UserInteraction.interaction_type.in_(["like", "unlike"]),
            )
            .order_by(UserInteraction.timestamp.desc())
            .all()
        )

        logger.info(
            f"Found {len(interactions)} like/unlike interactions for user {user_id}"
        )
        for interaction in interactions:
            logger.info(
                f"Interaction: {interaction.item_text} (type: {interaction.interaction_type}, timestamp: {interaction.timestamp})"
            )

        if not interactions:
            logger.info(f"No like/unlike interactions found for user {user_id}")
            return {"album": "No albums liked yet", "artist": "", "likes": 0}

        # Group by album and count likes/unlikes
        album_likes = {}
        for interaction in interactions:
            # Extract album and artist from item_text (format: "song by artist from album")
            parts = interaction.item_text.split(" from ", 1)
            if len(parts) == 2:
                song_artist, album = parts
                album = album.strip()
                # Extract artist from song_artist (format: "song by artist")
                artist_parts = song_artist.split(" by ", 1)
                if len(artist_parts) == 2:
                    artist = artist_parts[1].strip()
                    key = (album, artist)

                    # Add or subtract based on interaction type
                    if interaction.interaction_type == "like":
                        album_likes[key] = album_likes.get(key, 0) + 1
                        logger.info(
                            f"Added like for album '{album}' by '{artist}' (total likes: {album_likes[key]})"
                        )
                    else:  # unlike
                        album_likes[key] = max(0, album_likes.get(key, 0) - 1)
                        logger.info(
                            f"Removed like for album '{album}' by '{artist}' (total likes: {album_likes[key]})"
                        )
                else:
                    logger.warning(
                        f"Could not parse artist from song_artist: {song_artist}"
                    )
            else:
                logger.warning(
                    f"Could not parse album from item_text: {interaction.item_text}"
                )

        if not album_likes:
            logger.info(f"No valid album likes calculated for user {user_id}")
            return {"album": "No albums liked yet", "artist": "", "likes": 0}

        # Find the album with the most likes
        most_liked = max(album_likes.items(), key=lambda x: x[1])
        album, artist = most_liked[0]
        likes = most_liked[1]

        logger.info(
            f"Most liked album for user {user_id}: '{album}' by '{artist}' with {likes} likes"
        )
        logger.info(f"All album likes: {album_likes}")

        return {"album": album, "artist": artist, "likes": likes}

    def get_most_liked_artist(self, user_id: int) -> dict[str, str | int]:
        """
        Get the most liked artist for a user based on like interactions.
        Returns a dict with artist name and number of likes.
        """
        from src.models import UserInteraction, db

        logger = logging.getLogger(__name__)

        # Get all like and unlike interactions for the user
        interactions = (
            UserInteraction.query.filter(
                UserInteraction.user_id == user_id,
                UserInteraction.item_type == "song",
                UserInteraction.interaction_type.in_(["like", "unlike"]),
            )
            .order_by(UserInteraction.timestamp.desc())
            .all()
        )

        logger.info(
            f"Found {len(interactions)} like/unlike interactions for user {user_id}"
        )

        if not interactions:
            logger.info(f"No like/unlike interactions found for user {user_id}")
            return {"artist": "No artists liked yet", "likes": 0}

        # Group by artist and count likes/unlikes
        artist_likes = {}
        for interaction in interactions:
            # Extract artist from item_text (format: "song by artist from album")
            parts = interaction.item_text.split(" by ", 1)
            if len(parts) == 2:
                _, artist = parts
                # Remove " from album" part if present
                artist = artist.split(" from ")[0].strip()

                # Add or subtract based on interaction type
                if interaction.interaction_type == "like":
                    artist_likes[artist] = artist_likes.get(artist, 0) + 1
                    logger.info(
                        f"Added like for artist '{artist}' (total likes: {artist_likes[artist]})"
                    )
                else:  # unlike
                    artist_likes[artist] = max(0, artist_likes.get(artist, 0) - 1)
                    logger.info(
                        f"Removed like for artist '{artist}' (total likes: {artist_likes[artist]})"
                    )
            else:
                logger.warning(
                    f"Could not parse artist from item_text: {interaction.item_text}"
                )

        if not artist_likes:
            logger.info(f"No valid artist likes calculated for user {user_id}")
            return {"artist": "No artists liked yet", "likes": 0}

        # Find the artist with the most likes
        most_liked = max(artist_likes.items(), key=lambda x: x[1])
        artist = most_liked[0]
        likes = most_liked[1]

        logger.info(
            f"Most liked artist for user {user_id}: '{artist}' with {likes} likes"
        )
        logger.info(f"All artist likes: {artist_likes}")

        return {"artist": artist, "likes": likes}

    def get_latest_search_metrics(self, user_id: int) -> dict[str, float]:
        """
        Get metrics for just the latest search performed by a user.
        """

        if user_id not in self.active_sessions:
            return {"precision@5": 0.0, "precision@10": 0.0}

        session_id = self.active_sessions[user_id]["session_id"]
        metrics = self.session_metrics.get(session_id, {})

        return {
            "precision@5": metrics.get("precision@5", 0.0),
            "precision@10": metrics.get("precision@10", 0.0),
        }

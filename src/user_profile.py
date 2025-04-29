# pyright: reportCallIssue=false, reportOptionalMemberAccess=false

import logging
from datetime import datetime, timedelta

import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import desc

from src.utils import remove_html_tags

from .models import User, UserInteraction, db

# Constants
QUERY_WEIGHT = 0.67
BASE_SCORES = {"search": 0.3, "click": 0.5, "play": 0.8}
DEFAULT_SCORE = 0.3
RECENT_DAYS_THRESHOLD = 30  # days
MAX_PLAY_DURATION_SECONDS = 300  # 5 minutes for normalization
MAX_PLAY_SCORE_BONUS = 0.2

logger = logging.getLogger(__name__)


class UserProfileManager:
    def __init__(self):
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        logger.info(
            "UserProfileManager initialized with model: sentence-transformers/all-MiniLM-L6-v2"
        )

    def track_interaction(
        self, user_id, interaction_type, item_text=None, duration=None, item_type="song"
    ):
        """Track a user interaction and update user's profile embedding.

        Parameters:
        - user_id: ID of the user
        - interaction_type: Type of interaction ('search', 'click', 'play')
        - item_text: Text representation of the item being interacted with
        - duration: For 'play' interactions, how long the user listened
        - item_type: Type of item ('song', 'album', 'artist')
        """
        assert interaction_type in [
            "search",
            "click",
            "play",
        ], "Invalid interaction type"
        assert item_type in ["song", "album", "artist", "all"], "Invalid item type"

        if not item_text:
            logger.error(
                f"Missing item_text for user {user_id}, interaction {interaction_type}"
            )
            raise ValueError("item_text is required for embedding generation")

        # Clean the item text by removing HTML tags
        clean_item_text = remove_html_tags(item_text)
        logger.info(
            f"Tracking {interaction_type} interaction for user {user_id}: {item_type} - {clean_item_text[:30]}..."
        )

        # Create a new interaction with all required fields
        interaction = UserInteraction(
            user_id=user_id,
            interaction_type=interaction_type,
            item_type=item_type,
            item_text=clean_item_text,
            duration=duration or 0,
            relevance_score=self._calculate_relevance_score(interaction_type, duration),
        )

        db.session.add(interaction)
        db.session.commit()
        logger.info(
            f"Saved interaction {interaction.id} with relevance {interaction.relevance_score:.2f}"
        )
        self._update_user_embedding(user_id)

    def _calculate_relevance_score(self, interaction_type, duration=None):
        """Calculate implicit feedback score based on interaction type and duration."""
        score = BASE_SCORES.get(interaction_type, DEFAULT_SCORE)

        # Adjust score based on play duration (if available)
        if duration and interaction_type == "play":
            # Normalize duration to 0-1 range (assuming max duration of 5 minutes)
            duration_score = min(duration / MAX_PLAY_DURATION_SECONDS, 1.0)
            score += duration_score * MAX_PLAY_SCORE_BONUS

        return min(score, 1.0)

    def _update_user_embedding(self, user_id):
        """Update user's profile embedding based on recent interactions."""
        current_time = datetime.now()
        cutoff_date = current_time - timedelta(days=RECENT_DAYS_THRESHOLD)

        # Get recent interactions (last 30 days)
        recent_interactions = (
            db.session.query(UserInteraction)
            .filter(
                UserInteraction.user_id == user_id,
                UserInteraction.timestamp >= cutoff_date,
            )
            .order_by(desc(UserInteraction.timestamp))
            .all()
        )

        if not recent_interactions:
            logger.info(
                f"No recent interactions found for user {user_id}, skipping embedding update"
            )
            return

        logger.info(
            f"Updating embedding for user {user_id} with {len(recent_interactions)} recent interactions"
        )

        # Generate embeddings for each interaction
        embeddings = []
        weights = []

        for interaction in recent_interactions:
            # Generate embedding from the item text
            embedding = self.model.encode(
                interaction.item_text, normalize_embeddings=True
            )
            embeddings.append(embedding)

            # Calculate weight based on recency and relevance
            days_old = (current_time - interaction.timestamp).days
            recency_weight = np.exp(-days_old / RECENT_DAYS_THRESHOLD)
            weight = recency_weight * interaction.relevance_score
            weights.append(weight)

        # Normalize weights
        weights = np.array(weights)
        weights = weights / np.sum(weights)

        # Calculate weighted average embedding
        user_embedding = np.average(embeddings, axis=0, weights=weights)
        user_embedding = user_embedding / np.linalg.norm(user_embedding)

        # Update user's embedding
        user = User.query.get(user_id)
        user.user_embedding = user_embedding.tolist()
        user.last_updated = current_time
        logger.info(
            f"Updated embedding for user {user_id} (shape: {len(user.user_embedding)})"
        )
        logger.info(f"First 5 embedding values: {user.user_embedding[:5]}")
        db.session.commit()

    def get_personalized_search_query(self, user_id, query):
        """Generate a personalized search query using user's profile embedding."""
        # Clean the query by removing HTML tags
        clean_query = remove_html_tags(query)

        user = User.query.get(user_id)
        if not user or not user.user_embedding:
            logger.info(
                f"No user embedding available for user {user_id}, using standard query"
            )
            return clean_query

        logger.info(f"Personalizing search query '{clean_query}' for user {user_id}")

        # Generate embedding for the search query
        query_embedding = np.array(
            self.model.encode(clean_query, normalize_embeddings=True)
        )
        user_embedding = np.array(user.user_embedding)

        # Combine query embedding with user profile embedding
        combined_embedding = (
            QUERY_WEIGHT * query_embedding + (1 - QUERY_WEIGHT) * user_embedding
        )
        logger.debug(f"User embedding: {user.user_embedding}")
        logger.debug(f"Query embedding: {query_embedding}")
        logger.debug(f"User embedding shape: {user_embedding.shape}")
        logger.debug(f"Query embedding shape: {query_embedding.shape}")
        logger.debug(f"Combined embedding shape: {combined_embedding.shape}")
        logger.debug(f"User embedding norm: {np.linalg.norm(user_embedding)}")
        logger.debug(f"Query embedding norm: {np.linalg.norm(query_embedding)}")
        logger.debug(f"Combined embedding norm: {np.linalg.norm(combined_embedding)}")

        return combined_embedding.tolist()

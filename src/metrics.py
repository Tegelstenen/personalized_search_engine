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

import numpy as np
from collections import defaultdict
from typing import Dict, List, Tuple, Union
from datetime import datetime, timedelta

from .models import User, UserInteraction, db
from sqlalchemy import desc, func

class SearchMetrics:
    def __init__(self):
        pass
    
    def compute_ndcg(self, user_id: int, days: int = 7, k: int = 10) -> float:
        """
        Compute Normalized Discounted Cumulative Gain (NDCG) for a user's search sessions.
        
        NDCG measures the quality of search results based on their position in the result list,
        taking into account the relevance of each item.
        
        Args:
            user_id: The user ID
            days: Number of days to look back
            k: Number of top results to consider
            
        Returns:
            NDCG score between 0 and 1
        """
        # Get search sessions for this user in the specified time period
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get all search interactions
        search_interactions = (
            db.session.query(UserInteraction)
            .filter(
                UserInteraction.user_id == user_id,
                UserInteraction.interaction_type == "search",
                UserInteraction.timestamp >= cutoff_date
            )
            .order_by(UserInteraction.timestamp)
            .all()
        )
        
        if not search_interactions:
            return 0.0
        
        # Group interactions by search sessions
        # A search session ends when there's a gap of more than 30 minutes between searches
        sessions = []
        current_session = [search_interactions[0]]
        
        for i in range(1, len(search_interactions)):
            time_diff = (search_interactions[i].timestamp - search_interactions[i-1].timestamp).total_seconds()
            if time_diff <= 1800:  # 30 minutes in seconds
                current_session.append(search_interactions[i])
            else:
                sessions.append(current_session)
                current_session = [search_interactions[i]]
        
        if current_session:
            sessions.append(current_session)
        
        # Compute NDCG for each session and average them
        session_ndcgs = []
        
        for session in sessions:
            # Get the last search query in the session
            last_search = session[-1]
            
            # Find all interactions that happened after this search (clicks, plays)
            post_search_interactions = (
                db.session.query(UserInteraction)
                .filter(
                    UserInteraction.user_id == user_id,
                    UserInteraction.timestamp > last_search.timestamp,
                    UserInteraction.timestamp <= last_search.timestamp + timedelta(minutes=30),
                    UserInteraction.interaction_type.in_(["click", "play"])
                )
                .order_by(UserInteraction.timestamp)
                .all()
            )
            
            if not post_search_interactions:
                continue
            
            # Create a relevance list where clicked/played items have relevance scores
            relevance_scores = {}
            for interaction in post_search_interactions:
                # Weigh play interactions higher than clicks
                if interaction.interaction_type == "play":
                    relevance_scores[interaction.item_text] = interaction.relevance_score
                elif interaction.interaction_type == "click" and interaction.item_text not in relevance_scores:
                    relevance_scores[interaction.item_text] = interaction.relevance_score
            
            # If we have relevance scores, compute DCG and IDCG
            if relevance_scores:
                # Assume the search returned k results
                # In a real implementation, you would need to track the actual search results
                # But here we use the interactions as proxy
                rel_scores = list(relevance_scores.values())[:k]
                
                # Pad with zeros if we have fewer than k interactions
                rel_scores = rel_scores + [0] * (k - len(rel_scores))
                
                # Calculate DCG
                dcg = rel_scores[0] + sum([rel_scores[i] / np.log2(i + 2) for i in range(1, len(rel_scores))])
                
                # Calculate IDCG (ideal DCG)
                ideal_rel_scores = sorted(rel_scores, reverse=True)
                idcg = ideal_rel_scores[0] + sum([ideal_rel_scores[i] / np.log2(i + 2) for i in range(1, len(ideal_rel_scores))])
                
                if idcg > 0:
                    session_ndcgs.append(dcg / idcg)
        
        if not session_ndcgs:
            return 0.0
        
        return np.mean(session_ndcgs)
    
    def compute_recall_at_k(self, user_id: int, days: int = 7, k: int = 10) -> float:
        """
        Compute Recall@K for a user's search sessions.
        
        Recall@K measures the fraction of relevant items found in the top k results.
        
        Args:
            user_id: The user ID
            days: Number of days to look back
            k: Number of top results to consider
            
        Returns:
            Recall@K score between 0 and 1
        """
        # Similar approach as NDCG, but simpler calculation
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get all search interactions
        search_interactions = (
            db.session.query(UserInteraction)
            .filter(
                UserInteraction.user_id == user_id,
                UserInteraction.interaction_type == "search",
                UserInteraction.timestamp >= cutoff_date
            )
            .order_by(UserInteraction.timestamp)
            .all()
        )
        
        if not search_interactions:
            return 0.0
        
        # Group interactions by search sessions
        sessions = []
        current_session = [search_interactions[0]]
        
        for i in range(1, len(search_interactions)):
            time_diff = (search_interactions[i].timestamp - search_interactions[i-1].timestamp).total_seconds()
            if time_diff <= 1800:  # 30 minutes in seconds
                current_session.append(search_interactions[i])
            else:
                sessions.append(current_session)
                current_session = [search_interactions[i]]
        
        if current_session:
            sessions.append(current_session)
        
        # Compute Recall@K for each session and average them
        session_recalls = []
        
        for session in sessions:
            # Get the last search query in the session
            last_search = session[-1]
            
            # Find all interactions that happened after this search (clicks, plays)
            post_search_interactions = (
                db.session.query(UserInteraction)
                .filter(
                    UserInteraction.user_id == user_id,
                    UserInteraction.timestamp > last_search.timestamp,
                    UserInteraction.timestamp <= last_search.timestamp + timedelta(minutes=30),
                    UserInteraction.interaction_type.in_(["click", "play"])
                )
                .all()
            )
            
            if not post_search_interactions:
                continue
            
            # Count unique items that were interacted with
            relevant_items = set([interaction.item_text for interaction in post_search_interactions])
            
            # In a real implementation, you would check how many of these items were in the top k results
            # Since we don't have that data, we'll use a simplified approach
            # Assume that we can interact with at most k items (the ones that were shown)
            num_relevant_found = min(len(relevant_items), k)
            
            # Recall@K = number of relevant items found / total number of relevant items
            if len(relevant_items) > 0:
                session_recalls.append(num_relevant_found / len(relevant_items))
        
        if not session_recalls:
            return 0.0
        
        return np.mean(session_recalls)
    
    def compute_precision_at_k(self, user_id: int, days: int = 7, k: int = 10) -> float:
        """
        Compute Precision@K for a user's search sessions.
        
        Precision@K measures the fraction of the top k results that are relevant.
        
        Args:
            user_id: The user ID
            days: Number of days to look back
            k: Number of top results to consider
            
        Returns:
            Precision@K score between 0 and 1
        """
        # Get search sessions for this user in the specified time period
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get all search interactions
        search_interactions = (
            db.session.query(UserInteraction)
            .filter(
                UserInteraction.user_id == user_id,
                UserInteraction.interaction_type == "search",
                UserInteraction.timestamp >= cutoff_date
            )
            .order_by(UserInteraction.timestamp)
            .all()
        )
        
        if not search_interactions:
            return 0.0
        
        # Same logic as recall to identify sessions
        sessions = []
        current_session = [search_interactions[0]]
        
        for i in range(1, len(search_interactions)):
            time_diff = (search_interactions[i].timestamp - search_interactions[i-1].timestamp).total_seconds()
            if time_diff <= 1800:
                current_session.append(search_interactions[i])
            else:
                sessions.append(current_session)
                current_session = [search_interactions[i]]
        
        if current_session:
            sessions.append(current_session)
        
        session_precisions = []
        
        for session in sessions:
            last_search = session[-1]
            
            post_search_interactions = (
                db.session.query(UserInteraction)
                .filter(
                    UserInteraction.user_id == user_id,
                    UserInteraction.timestamp > last_search.timestamp,
                    UserInteraction.timestamp <= last_search.timestamp + timedelta(minutes=30),
                    UserInteraction.interaction_type.in_(["click", "play"])
                )
                .all()
            )
            
            if not post_search_interactions:
                continue
            
            relevant_items = set([interaction.item_text for interaction in post_search_interactions])
            
            # Precision@K = number of relevant items found / k
            num_relevant_found = min(len(relevant_items), k)
            session_precisions.append(num_relevant_found / k)
        
        if not session_precisions:
            return 0.0
        
        return np.mean(session_precisions)
    
    def get_user_metrics(self, user_id: int) -> Dict[str, Union[float, int]]:
        """
        Calculate and return all metrics for a user
        
        Args:
            user_id: The user ID
            
        Returns:
            Dictionary with all metrics
        """
        # Basic metrics
        day_ranges = [1, 7, 30]
        metrics = {}
        
        for days in day_ranges:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Number of searches
            search_count = (
                db.session.query(func.count(UserInteraction.id))
                .filter(
                    UserInteraction.user_id == user_id,
                    UserInteraction.interaction_type == "search",
                    UserInteraction.timestamp >= cutoff_date
                )
                .scalar()
            )
            
            # Number of clicks
            click_count = (
                db.session.query(func.count(UserInteraction.id))
                .filter(
                    UserInteraction.user_id == user_id,
                    UserInteraction.interaction_type == "click",
                    UserInteraction.timestamp >= cutoff_date
                )
                .scalar()
            )
            
            # Number of plays
            play_count = (
                db.session.query(func.count(UserInteraction.id))
                .filter(
                    UserInteraction.user_id == user_id,
                    UserInteraction.interaction_type == "play",
                    UserInteraction.timestamp >= cutoff_date
                )
                .scalar()
            )
            
            # CTR (Click-Through Rate)
            ctr = (click_count / search_count) if search_count > 0 else 0
            
            # Compute advanced metrics
            ndcg_5 = self.compute_ndcg(user_id, days, 5)
            ndcg_10 = self.compute_ndcg(user_id, days, 10)
            recall_5 = self.compute_recall_at_k(user_id, days, 5)
            recall_10 = self.compute_recall_at_k(user_id, days, 10)
            precision_5 = self.compute_precision_at_k(user_id, days, 5)
            precision_10 = self.compute_precision_at_k(user_id, days, 10)
            
            # Store metrics with time range in the key
            metrics.update({
                f'search_count_{days}d': search_count,
                f'click_count_{days}d': click_count,
                f'play_count_{days}d': play_count,
                f'ctr_{days}d': ctr,
                f'ndcg@5_{days}d': ndcg_5,
                f'ndcg@10_{days}d': ndcg_10,
                f'recall@5_{days}d': recall_5,
                f'recall@10_{days}d': recall_10,
                f'precision@5_{days}d': precision_5,
                f'precision@10_{days}d': precision_10
            })
        
        return metrics

    def get_avg_user_metrics(self) -> Dict[str, float]:
        """
        Calculate and return average metrics across all users
        
        Returns:
            Dictionary with average metrics
        """
        # Get all users
        users = User.query.all()
        if not users:
            return {}
        
        # Initialize metrics dictionary
        metrics_sum = defaultdict(float)
        
        # Calculate metrics for each user and sum them
        for user in users:
            user_metrics = self.get_user_metrics(user.id)
            for key, value in user_metrics.items():
                metrics_sum[key] += value
        
        # Calculate averages
        avg_metrics = {key: value / len(users) for key, value in metrics_sum.items()}
        
        return avg_metrics 
"""
Trend detection algorithm for identifying emerging narratives.
"""

import asyncio
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.database import get_mongodb_db, get_redis_client
from app.core.logging import get_logger

logger = get_logger(__name__)


class TrendDetector:
    """Detects trends and emerging narratives from social media data."""

    def __init__(self):
        self.mongodb = None
        self.redis = None
        self.min_mentions = 10  # Minimum mentions to consider a trend
        self.velocity_threshold = 5  # Mentions per hour threshold
        self.similarity_threshold = 0.7  # Content similarity threshold

    async def initialize(self):
        """Initialize trend detector."""
        self.mongodb = get_mongodb_db()
        self.redis = get_redis_client()
        logger.info("Trend detector initialized")

    async def detect_trends(
        self, posts: List[Dict[str, Any]], time_window_hours: int = 2
    ) -> List[Dict[str, Any]]:
        """Detect trends from a collection of posts."""
        try:
            if len(posts) < self.min_mentions:
                return []

            logger.info(f"Analyzing {len(posts)} posts for trends")

            # Step 1: Temporal analysis - group posts by time
            temporal_groups = self._group_posts_by_time(posts, window_minutes=60)

            # Step 2: Content clustering - find similar content
            content_clusters = await self._cluster_content(posts)

            # Step 3: Keyword/hashtag analysis
            keyword_trends = self._analyze_keyword_trends(posts, time_window_hours)

            # Step 4: Velocity analysis - detect rapid growth
            velocity_trends = self._analyze_velocity(temporal_groups)

            # Step 5: Network analysis - detect coordinated behavior
            network_trends = await self._analyze_network_patterns(posts)

            # Step 6: Combine and score trends
            detected_trends = self._combine_trend_signals(
                content_clusters, keyword_trends, velocity_trends, network_trends
            )

            # Step 7: Filter and rank trends
            filtered_trends = self._filter_and_rank_trends(detected_trends)

            logger.info(f"Detected {len(filtered_trends)} trends")
            return filtered_trends

        except Exception as e:
            logger.error(f"Error detecting trends: {e}")
            return []

    def _group_posts_by_time(
        self, posts: List[Dict[str, Any]], window_minutes: int = 60
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group posts by time windows."""
        time_groups = defaultdict(list)

        for post in posts:
            posted_at = post.get("posted_at")
            if isinstance(posted_at, str):
                posted_at = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))

            # Round to nearest window
            window_start = posted_at.replace(
                minute=(posted_at.minute // window_minutes) * window_minutes,
                second=0,
                microsecond=0,
            )
            window_key = window_start.isoformat()
            time_groups[window_key].append(post)

        return dict(time_groups)

    async def _cluster_content(
        self, posts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Cluster posts by content similarity."""
        try:
            if len(posts) < 3:
                return []

            # Extract content and create embeddings
            contents = [post.get("content", "") for post in posts]

            # Use TF-IDF for clustering (faster than embeddings for large datasets)
            vectorizer = TfidfVectorizer(
                max_features=1000, stop_words="english", ngram_range=(1, 2), min_df=2
            )

            try:
                tfidf_matrix = vectorizer.fit_transform(contents)
            except ValueError:
                # Not enough data to cluster
                return []

            # Perform clustering
            clustering = DBSCAN(
                eps=0.3, min_samples=max(3, len(posts) // 20), metric="cosine"
            )

            cluster_labels = clustering.fit_predict(tfidf_matrix)

            # Analyze clusters
            clusters = []
            for cluster_id in set(cluster_labels):
                if cluster_id == -1:  # Noise cluster
                    continue

                cluster_posts = [
                    posts[i]
                    for i, label in enumerate(cluster_labels)
                    if label == cluster_id
                ]

                if len(cluster_posts) >= self.min_mentions:
                    cluster_info = self._analyze_cluster(
                        cluster_posts,
                        vectorizer,
                        tfidf_matrix,
                        cluster_labels,
                        cluster_id,
                    )
                    if cluster_info:
                        clusters.append(cluster_info)

            return clusters

        except Exception as e:
            logger.error(f"Error in content clustering: {e}")
            return []

    def _analyze_cluster(
        self,
        cluster_posts: List[Dict[str, Any]],
        vectorizer,
        tfidf_matrix,
        labels,
        cluster_id,
    ) -> Optional[Dict[str, Any]]:
        """Analyze a content cluster to extract trend information."""
        try:
            # Get cluster posts indices
            cluster_indices = [
                i for i, label in enumerate(labels) if label == cluster_id
            ]

            # Extract representative keywords
            cluster_tfidf = tfidf_matrix[cluster_indices]
            mean_tfidf = np.mean(cluster_tfidf, axis=0)
            feature_names = vectorizer.get_feature_names_out()

            # Get top keywords
            top_indices = np.argsort(mean_tfidf.A1)[-10:][::-1]
            keywords = [feature_names[i] for i in top_indices if mean_tfidf.A1[i] > 0]

            # Calculate cluster statistics
            platforms = [post.get("platform") for post in cluster_posts]
            platform_counts = Counter(platforms)

            # Calculate velocity (posts per hour)
            time_span = self._calculate_time_span(cluster_posts)
            velocity = len(cluster_posts) / max(time_span, 1) if time_span > 0 else 0

            # Extract hashtags
            all_hashtags = []
            for post in cluster_posts:
                all_hashtags.extend(post.get("hashtags", []))
            top_hashtags = [tag for tag, count in Counter(all_hashtags).most_common(10)]

            # Sentiment analysis
            sentiments = [
                post.get("sentiment_score", 0)
                for post in cluster_posts
                if post.get("sentiment_score") is not None
            ]
            avg_sentiment = np.mean(sentiments) if sentiments else 0

            return {
                "type": "content_cluster",
                "keywords": keywords,
                "hashtags": top_hashtags,
                "mention_count": len(cluster_posts),
                "velocity": velocity,
                "platforms": dict(platform_counts),
                "sentiment": avg_sentiment,
                "posts": cluster_posts,
                "first_seen": min(
                    post.get("posted_at", datetime.utcnow()) for post in cluster_posts
                ),
                "last_seen": max(
                    post.get("posted_at", datetime.utcnow()) for post in cluster_posts
                ),
            }

        except Exception as e:
            logger.error(f"Error analyzing cluster: {e}")
            return None

    def _analyze_keyword_trends(
        self, posts: List[Dict[str, Any]], time_window_hours: int
    ) -> List[Dict[str, Any]]:
        """Analyze keyword and hashtag trends."""
        try:
            # Collect all keywords and hashtags with timestamps
            keyword_timeline = defaultdict(list)
            hashtag_timeline = defaultdict(list)

            for post in posts:
                posted_at = post.get("posted_at")
                if isinstance(posted_at, str):
                    posted_at = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))

                # Keywords
                for keyword in post.get("keywords", []):
                    keyword_timeline[keyword].append(posted_at)

                # Hashtags
                for hashtag in post.get("hashtags", []):
                    hashtag_timeline[hashtag].append(posted_at)

            trends = []

            # Analyze keyword trends
            for keyword, timestamps in keyword_timeline.items():
                if len(timestamps) >= self.min_mentions:
                    trend_info = self._analyze_term_trend(
                        keyword, timestamps, "keyword"
                    )
                    if trend_info and trend_info["velocity"] >= self.velocity_threshold:
                        trends.append(trend_info)

            # Analyze hashtag trends
            for hashtag, timestamps in hashtag_timeline.items():
                if len(timestamps) >= self.min_mentions:
                    trend_info = self._analyze_term_trend(
                        hashtag, timestamps, "hashtag"
                    )
                    if trend_info and trend_info["velocity"] >= self.velocity_threshold:
                        trends.append(trend_info)

            return trends

        except Exception as e:
            logger.error(f"Error analyzing keyword trends: {e}")
            return []

    def _analyze_term_trend(
        self, term: str, timestamps: List[datetime], term_type: str
    ) -> Optional[Dict[str, Any]]:
        """Analyze trend for a specific term."""
        try:
            timestamps.sort()

            # Calculate velocity (mentions per hour)
            time_span = (timestamps[-1] - timestamps[0]).total_seconds() / 3600
            velocity = len(timestamps) / max(time_span, 1)

            # Calculate acceleration (change in velocity)
            if len(timestamps) >= 4:
                mid_point = len(timestamps) // 2
                early_timestamps = timestamps[:mid_point]
                late_timestamps = timestamps[mid_point:]

                early_span = (
                    early_timestamps[-1] - early_timestamps[0]
                ).total_seconds() / 3600
                late_span = (
                    late_timestamps[-1] - late_timestamps[0]
                ).total_seconds() / 3600

                early_velocity = len(early_timestamps) / max(early_span, 1)
                late_velocity = len(late_timestamps) / max(late_span, 1)

                acceleration = late_velocity - early_velocity
            else:
                acceleration = 0

            return {
                "type": f"{term_type}_trend",
                "term": term,
                "term_type": term_type,
                "mention_count": len(timestamps),
                "velocity": velocity,
                "acceleration": acceleration,
                "first_seen": timestamps[0],
                "last_seen": timestamps[-1],
                "peak_time": self._find_peak_time(timestamps),
            }

        except Exception as e:
            logger.error(f"Error analyzing term trend for {term}: {e}")
            return None

    def _analyze_velocity(
        self, temporal_groups: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Analyze velocity patterns to detect sudden spikes."""
        try:
            velocity_trends = []

            # Sort time windows
            sorted_windows = sorted(temporal_groups.keys())

            if len(sorted_windows) < 3:
                return []

            # Calculate velocities for each window
            velocities = []
            for window in sorted_windows:
                post_count = len(temporal_groups[window])
                velocities.append(post_count)

            # Detect spikes (velocity significantly above average)
            mean_velocity = np.mean(velocities)
            std_velocity = np.std(velocities)
            spike_threshold = mean_velocity + 2 * std_velocity

            for i, (window, velocity) in enumerate(zip(sorted_windows, velocities)):
                if velocity > spike_threshold and velocity >= self.velocity_threshold:
                    # Extract common themes from spike window
                    window_posts = temporal_groups[window]

                    # Get most common keywords/hashtags
                    all_keywords = []
                    all_hashtags = []
                    for post in window_posts:
                        all_keywords.extend(post.get("keywords", []))
                        all_hashtags.extend(post.get("hashtags", []))

                    top_keywords = [
                        kw for kw, count in Counter(all_keywords).most_common(5)
                    ]
                    top_hashtags = [
                        ht for ht, count in Counter(all_hashtags).most_common(5)
                    ]

                    velocity_trends.append(
                        {
                            "type": "velocity_spike",
                            "window": window,
                            "velocity": velocity,
                            "spike_ratio": velocity / mean_velocity,
                            "mention_count": len(window_posts),
                            "keywords": top_keywords,
                            "hashtags": top_hashtags,
                            "posts": window_posts,
                        }
                    )

            return velocity_trends

        except Exception as e:
            logger.error(f"Error analyzing velocity: {e}")
            return []

    async def _analyze_network_patterns(
        self, posts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze network patterns to detect coordinated behavior."""
        try:
            # Build interaction network
            G = nx.Graph()

            # Add nodes (users) and edges (interactions)
            for post in posts:
                author = post.get("author_username")
                mentions = post.get("mentions", [])

                if author:
                    G.add_node(author)

                    # Add edges for mentions
                    for mentioned_user in mentions:
                        G.add_edge(author, mentioned_user)

            network_trends = []

            # Detect communities (potential coordinated groups)
            if len(G.nodes()) > 10:
                try:
                    from networkx.algorithms import community

                    communities = community.greedy_modularity_communities(G)

                    for i, comm in enumerate(communities):
                        if len(comm) >= 5:  # Significant community size
                            # Analyze community posting patterns
                            comm_posts = [
                                post
                                for post in posts
                                if post.get("author_username") in comm
                            ]

                            if len(comm_posts) >= self.min_mentions:
                                # Check if posting times are suspiciously coordinated
                                coordination_score = self._calculate_coordination_score(
                                    comm_posts
                                )

                                if coordination_score > 0.7:  # High coordination
                                    network_trends.append(
                                        {
                                            "type": "coordinated_network",
                                            "community_id": i,
                                            "community_size": len(comm),
                                            "post_count": len(comm_posts),
                                            "coordination_score": coordination_score,
                                            "users": list(comm),
                                            "posts": comm_posts,
                                        }
                                    )

                except ImportError:
                    logger.warning("NetworkX community detection not available")

            return network_trends

        except Exception as e:
            logger.error(f"Error analyzing network patterns: {e}")
            return []

    def _calculate_coordination_score(self, posts: List[Dict[str, Any]]) -> float:
        """Calculate how coordinated posting behavior is."""
        try:
            timestamps = []
            for post in posts:
                posted_at = post.get("posted_at")
                if isinstance(posted_at, str):
                    posted_at = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
                timestamps.append(posted_at)

            if len(timestamps) < 2:
                return 0.0

            timestamps.sort()

            # Calculate time differences between posts
            time_diffs = []
            for i in range(1, len(timestamps)):
                diff = (timestamps[i] - timestamps[i - 1]).total_seconds()
                time_diffs.append(diff)

            # High coordination = low variance in time differences
            if len(time_diffs) > 1:
                mean_diff = np.mean(time_diffs)
                std_diff = np.std(time_diffs)
                cv = std_diff / mean_diff if mean_diff > 0 else float("inf")

                # Convert coefficient of variation to coordination score (0-1)
                coordination_score = max(0, 1 - min(cv, 1))
                return coordination_score

            return 0.0

        except Exception as e:
            logger.error(f"Error calculating coordination score: {e}")
            return 0.0

    def _combine_trend_signals(
        self, content_clusters, keyword_trends, velocity_trends, network_trends
    ) -> List[Dict[str, Any]]:
        """Combine different trend signals into unified trends."""
        all_trends = []

        # Add all trend types
        all_trends.extend(content_clusters)
        all_trends.extend(keyword_trends)
        all_trends.extend(velocity_trends)
        all_trends.extend(network_trends)

        # Score each trend
        for trend in all_trends:
            trend["score"] = self._calculate_trend_score(trend)

        return all_trends

    def _calculate_trend_score(self, trend: Dict[str, Any]) -> float:
        """Calculate overall trend score."""
        try:
            base_score = 0.0

            # Mention count factor
            mention_count = trend.get("mention_count", 0)
            base_score += min(mention_count / 100, 1.0) * 30

            # Velocity factor
            velocity = trend.get("velocity", 0)
            base_score += min(velocity / 50, 1.0) * 25

            # Acceleration factor
            acceleration = trend.get("acceleration", 0)
            if acceleration > 0:
                base_score += min(acceleration / 20, 1.0) * 20

            # Platform diversity factor
            platforms = trend.get("platforms", {})
            platform_diversity = len(platforms)
            base_score += min(platform_diversity / 4, 1.0) * 15

            # Coordination penalty (for suspicious activity)
            coordination_score = trend.get("coordination_score", 0)
            if coordination_score > 0.8:
                base_score *= 0.5  # Reduce score for highly coordinated content

            # Trend type bonuses
            if trend.get("type") == "content_cluster":
                base_score += 10
            elif trend.get("type") == "velocity_spike":
                base_score += 15

            return min(base_score, 100.0)

        except Exception as e:
            logger.error(f"Error calculating trend score: {e}")
            return 0.0

    def _filter_and_rank_trends(
        self, trends: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Filter and rank trends by score."""
        # Filter out low-scoring trends
        filtered_trends = [trend for trend in trends if trend.get("score", 0) >= 20]

        # Sort by score (descending)
        filtered_trends.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Return top trends
        return filtered_trends[:50]

    def _calculate_time_span(self, posts: List[Dict[str, Any]]) -> float:
        """Calculate time span of posts in hours."""
        try:
            timestamps = []
            for post in posts:
                posted_at = post.get("posted_at")
                if isinstance(posted_at, str):
                    posted_at = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
                timestamps.append(posted_at)

            if len(timestamps) < 2:
                return 1.0  # Default to 1 hour

            time_span = (max(timestamps) - min(timestamps)).total_seconds() / 3600
            return max(time_span, 0.1)  # Minimum 0.1 hour

        except Exception as e:
            logger.error(f"Error calculating time span: {e}")
            return 1.0

    def _find_peak_time(self, timestamps: List[datetime]) -> datetime:
        """Find the time with highest posting activity."""
        try:
            # Group by hour and find peak
            hour_counts = defaultdict(int)
            for ts in timestamps:
                hour_key = ts.replace(minute=0, second=0, microsecond=0)
                hour_counts[hour_key] += 1

            if hour_counts:
                return max(hour_counts.items(), key=lambda x: x[1])[0]
            else:
                return timestamps[0] if timestamps else datetime.utcnow()

        except Exception as e:
            logger.error(f"Error finding peak time: {e}")
            return timestamps[0] if timestamps else datetime.utcnow()

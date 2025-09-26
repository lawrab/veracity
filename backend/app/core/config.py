"""
Application configuration settings.
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    SECRET_KEY: str = Field(env="SECRET_KEY")

    # API Configuration
    API_PREFIX: str = "/api/v1"
    ALLOWED_HOSTS: str | list[str] = Field(default=["*"], env="ALLOWED_HOSTS")

    # Database URLs
    POSTGRES_URL: str = Field(env="POSTGRES_URL")
    MONGODB_URL: str = Field(env="MONGODB_URL")
    REDIS_URL: str = Field(env="REDIS_URL")
    ELASTICSEARCH_URL: str = Field(env="ELASTICSEARCH_URL")

    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str = Field(env="KAFKA_BOOTSTRAP_SERVERS")
    KAFKA_TOPIC_SOCIAL_POSTS: str = "social_posts"
    KAFKA_TOPIC_NEWS_ARTICLES: str = "news_articles"
    KAFKA_TOPIC_TRENDS: str = "trends"

    # External APIs
    TWITTER_BEARER_TOKEN: str | None = Field(default=None, env="TWITTER_BEARER_TOKEN")
    REDDIT_CLIENT_ID: str | None = Field(default=None, env="REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET: str | None = Field(default=None, env="REDDIT_CLIENT_SECRET")
    NEWS_API_KEY: str | None = Field(default=None, env="NEWS_API_KEY")

    # Processing Configuration
    TREND_DETECTION_WINDOW_MINUTES: int = 60
    TRUST_SCORE_UPDATE_INTERVAL_MINUTES: int = 15
    MAX_POSTS_PER_BATCH: int = 1000

    # ML Models
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    CLASSIFICATION_MODEL: str = "distilbert-base-uncased"
    
    # WebSocket Configuration
    REQUIRE_WEBSOCKET_AUTH: bool = False  # Set to True in production
    WEBSOCKET_MAX_CONNECTIONS: int = 10000
    WEBSOCKET_MESSAGE_QUEUE_SIZE: int = 1000

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        if isinstance(v, list):
            return v
        return ["*"]  # fallback

    model_config = SettingsConfigDict(case_sensitive=True, env_parse_none_str="None")


settings = Settings()

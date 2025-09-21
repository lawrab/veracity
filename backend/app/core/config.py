"""
Application configuration settings.
"""

from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    SECRET_KEY: str = Field(env="SECRET_KEY")
    
    # API Configuration
    API_PREFIX: str = "/api/v1"
    ALLOWED_HOSTS: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    
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
    TWITTER_BEARER_TOKEN: Optional[str] = Field(default=None, env="TWITTER_BEARER_TOKEN")
    REDDIT_CLIENT_ID: Optional[str] = Field(default=None, env="REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET: Optional[str] = Field(default=None, env="REDDIT_CLIENT_SECRET")
    NEWS_API_KEY: Optional[str] = Field(default=None, env="NEWS_API_KEY")
    
    # Processing Configuration
    TREND_DETECTION_WINDOW_MINUTES: int = 60
    TRUST_SCORE_UPDATE_INTERVAL_MINUTES: int = 15
    MAX_POSTS_PER_BATCH: int = 1000
    
    # ML Models
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    CLASSIFICATION_MODEL: str = "distilbert-base-uncased"
    
    @validator("ALLOWED_HOSTS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
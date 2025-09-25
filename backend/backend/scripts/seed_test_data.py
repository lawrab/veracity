#!/usr/bin/env python
"""
Seed the database with test data for development and testing
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone
import uuid

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.sql_models import Story, Trend, Source, TrustSignal

# Database URL
DATABASE_URL = settings.POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Test data templates
STORY_TITLES = [
    "Breaking: Major Tech Company Announces Revolutionary AI Breakthrough",
    "Climate Scientists Report Accelerating Antarctic Ice Melt",
    "New Study Links Social Media Use to Mental Health Concerns",
    "Global Markets React to Central Bank Interest Rate Decision",
    "Viral Video Shows Rare Wildlife Encounter in Urban Area",
    "Celebrity Scandal Rocks Entertainment Industry",
    "Political Leader Makes Controversial Statement on Immigration",
    "Scientists Discover Potential Treatment for Rare Disease",
    "Cryptocurrency Market Experiences Significant Volatility",
    "Local Community Rallies to Support Small Businesses",
]

STORY_DESCRIPTIONS = [
    "Experts are divided on the implications of this development",
    "The situation continues to evolve as more information becomes available",
    "Community leaders call for immediate action and transparency",
    "Analysis shows complex factors contributing to the current situation",
    "Public reaction has been mixed, with strong opinions on both sides",
]

TREND_TOPICS = [
    "#TechInnovation", "#ClimateAction", "#MentalHealthAwareness",
    "#EconomicUpdate", "#WildlifeConservation", "#EntertainmentNews",
    "#PoliticalDebate", "#MedicalBreakthrough", "#CryptoNews", "#LocalHeroes"
]

SOURCE_NAMES = [
    "Twitter", "Reddit", "TikTok", "Instagram", "NewsAPI",
    "Reuters", "AP News", "BBC", "CNN", "Fox News"
]

CATEGORIES = [
    "technology", "science", "politics", "entertainment", 
    "health", "business", "environment", "sports"
]

PLATFORMS = ["twitter", "reddit", "tiktok", "instagram"]


async def seed_sources(session: AsyncSession):
    """Create source records"""
    sources = []
    for name in SOURCE_NAMES:
        source = Source(
            id=uuid.uuid4(),
            platform=random.choice(PLATFORMS),
            username=name.lower().replace(" ", "_"),
            display_name=name,
            url=f"https://{name.lower().replace(' ', '')}.com",
            verified=random.choice([True, False]),
            follower_count=random.randint(1000, 10000000),
            credibility_score=random.uniform(50.0, 100.0),
            created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(30, 365))
        )
        sources.append(source)
        session.add(source)
    
    await session.commit()
    return sources


async def seed_stories(session: AsyncSession, sources):
    """Create story records"""
    stories = []
    for i, title in enumerate(STORY_TITLES):
        story = Story(
            id=uuid.uuid4(),
            title=title,
            description=random.choice(STORY_DESCRIPTIONS),
            category=random.choice(CATEGORIES),
            trust_score=random.uniform(30.0, 100.0),  # 0-100 scale
            velocity=random.uniform(0.1, 10.0),  # mentions per hour
            geographic_spread={"US": random.randint(20, 50), "UK": random.randint(10, 30), "EU": random.randint(10, 30)},
            first_seen_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 72)),
            last_updated_at=datetime.now(timezone.utc)
        )
        stories.append(story)
        session.add(story)
    
    await session.commit()
    return stories


async def seed_trends(session: AsyncSession):
    """Create trend records"""
    trends = []
    for topic in TREND_TOPICS:
        trend = Trend(
            id=uuid.uuid4(),
            story_id=None,  # Will associate with stories later
            keywords=[topic.replace("#", ""), random.choice(["news", "breaking", "update"])],
            hashtags=[topic] if topic.startswith("#") else [f"#{topic}"],
            platforms=random.sample(PLATFORMS, k=random.randint(1, 3)),
            mention_count=random.randint(100, 100000),
            velocity=random.uniform(0.5, 20.0),
            sentiment_score=random.uniform(-1.0, 1.0),
            detected_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 48)),
            peak_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 24))
        )
        trends.append(trend)
        session.add(trend)
    
    await session.commit()
    return trends


async def seed_trust_signals(session: AsyncSession, stories):
    """Create trust signal records"""
    signal_types = [
        "source_credibility", "velocity_pattern", "cross_platform_correlation",
        "engagement_authenticity", "temporal_consistency", "content_quality"
    ]
    
    for story in stories:
        for signal_type in signal_types:
            if random.random() > 0.3:  # Create signals for 70% of combinations
                signal = TrustSignal(
                    id=uuid.uuid4(),
                    story_id=story.id,
                    signal_type=signal_type,
                    value=random.uniform(0.0, 1.0),
                    weight=random.uniform(0.5, 1.0),
                    explanation=f"Analysis of {signal_type} for story",
                    calculated_at=datetime.now(timezone.utc)
                )
                session.add(signal)
    
    await session.commit()


async def associate_trends_with_stories(session: AsyncSession, stories, trends):
    """Associate trends with stories"""
    # Update trends to point to stories
    for i, trend in enumerate(trends):
        if i < len(stories):
            trend.story_id = stories[i].id
    
    await session.commit()


async def main():
    """Main function to seed the database"""
    print("🌱 Starting database seeding...")
    
    async with AsyncSessionLocal() as session:
        try:
            # Seed sources first
            print("Creating sources...")
            sources = await seed_sources(session)
            print(f"✅ Created {len(sources)} sources")
            
            # Seed stories
            print("Creating stories...")
            stories = await seed_stories(session, sources)
            print(f"✅ Created {len(stories)} stories")
            
            # Seed trends
            print("Creating trends...")
            trends = await seed_trends(session)
            print(f"✅ Created {len(trends)} trends")
            
            # Seed trust signals
            print("Creating trust signals...")
            await seed_trust_signals(session, stories)
            print("✅ Created trust signals")
            
            # Associate trends with stories
            print("Associating trends with stories...")
            await associate_trends_with_stories(session, stories, trends)
            print("✅ Associated trends with stories")
            
            print("\n🎉 Database seeding completed successfully!")
            print(f"   - {len(sources)} sources")
            print(f"   - {len(stories)} stories")
            print(f"   - {len(trends)} trends")
            print("   - Trust signals and associations created")
            
        except Exception as e:
            print(f"❌ Error seeding database: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
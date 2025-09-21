# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Veracity** is a comprehensive social media trend and news trustability platform that monitors real-time social media activity, detects emerging trends, and provides dynamic credibility scoring for news stories and rumors.

### Key Features
- Real-time social media monitoring (Twitter, Reddit, TikTok, Instagram)
- ML-powered trend detection and clustering
- Dynamic trust scoring with transparent explanations
- Correlation tracking between social trends and mainstream news
- Bot detection and coordinated campaign identification
- Interactive dashboard with real-time visualizations

## Development Environment Setup

### Using Nix (Recommended)
```bash
# Enter development shell with all dependencies
nix develop

# Quick start after entering nix shell
cp .env.example .env  # Configure API keys
dc up -d              # Start all services
be-dev                # Start backend (alias)
fe-dev                # Start frontend (alias)
```

### Manual Setup
```bash
# Backend dependencies
cd backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Frontend dependencies  
cd frontend
npm install

# Start infrastructure
podman-compose up -d postgres mongodb redis elasticsearch kafka
```

## Architecture Overview

### Backend (FastAPI + Python)
```
backend/
├── app/
│   ├── api/v1/          # REST API endpoints
│   ├── core/            # Configuration, database, logging
│   ├── models/          # SQLAlchemy (PostgreSQL) & Pydantic (MongoDB) models
│   ├── schemas/         # API request/response schemas
│   └── services/        # Business logic layer
│       ├── ingestion/   # Social media data collection
│       ├── processing/  # NLP and trend detection
│       └── scoring/     # Trust scoring algorithms
```

### Frontend (Next.js + TypeScript)
```
frontend/
├── src/
│   ├── components/      # React components
│   ├── pages/          # Next.js pages/routes
│   ├── hooks/          # Custom React hooks
│   ├── services/       # API clients
│   └── types/          # TypeScript definitions
```

### Data Architecture
- **PostgreSQL**: Relational data (stories, trends, sources, trust signals)
- **MongoDB**: Raw social media posts and articles
- **Redis**: Real-time state, caching, and queues
- **Elasticsearch**: Full-text search and analytics
- **Kafka**: High-throughput message streaming

## Common Development Commands

### Container Management (Podman)
```bash
dc up -d                    # Start all services
dc down                     # Stop all services  
dc logs -f <service>        # View logs
dc restart <service>        # Restart service
reset-dev                   # Reset all data and restart
```

### Backend Development
```bash
be-dev                      # Start development server
be-test                     # Run tests
be-lint                     # Format and lint code
python -m app.main          # Direct server start
pytest backend/tests/       # Run specific tests
```

### Frontend Development  
```bash
fe-dev                      # Start development server
fe-build                    # Production build
fe-lint                     # Lint TypeScript/React
npm run type-check          # TypeScript validation
```

### Database Operations
```bash
psql-local                  # Connect to PostgreSQL
mongo-local                 # Connect to MongoDB
redis-cli-local             # Connect to Redis
```

## Key Implementation Patterns

### Async Service Pattern
All services use async/await with dependency injection:
```python
class TrendService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def detect_trends(self, posts: List[Dict]) -> List[Trend]:
        # Async processing logic
```

### Real-time Updates
WebSocket connections managed through centralized manager:
```python
# Backend: Broadcast updates
await websocket_manager.broadcast_trend_update(trend_data)

# Frontend: Subscribe to updates  
useWebSocket('/ws/trends', onTrendUpdate)
```

### Error Handling
Structured logging with error tracking:
```python
logger = get_logger(__name__)
try:
    result = await process_data()
except Exception as e:
    logger.error(f"Processing failed: {e}", extra={"data_id": item_id})
```

### Configuration Management
Environment-based configuration with validation:
```python
# settings loaded from .env with Pydantic validation
from app.core.config import settings
db_url = settings.POSTGRES_URL
```

## Testing Strategy

### Backend Tests
```bash
pytest backend/tests/unit/          # Unit tests
pytest backend/tests/integration/   # Integration tests
pytest backend/tests/e2e/          # End-to-end API tests
```

### Test Categories
- **Unit**: Individual function/class testing
- **Integration**: Database and external API integration
- **E2E**: Full workflow testing through API endpoints

## Deployment

### Production Build
```bash
# Build containers
podman build -t veracity-backend ./backend
podman build -t veracity-frontend ./frontend

# Or use Nix
nix build .#backend-image
nix build .#frontend-image
```

### Environment Configuration
Production requires these environment variables:
- Database URLs (PostgreSQL, MongoDB, Redis, Elasticsearch)
- API keys (Twitter, Reddit, News APIs)
- Security settings (SECRET_KEY, ALLOWED_HOSTS)
- Processing configuration (batch sizes, intervals)

## Key Dependencies

### Backend Core
- **FastAPI**: Async web framework
- **SQLAlchemy**: ORM for PostgreSQL
- **Motor**: Async MongoDB driver
- **Transformers**: ML models for NLP
- **spaCy**: Text processing and NER
- **scikit-learn**: ML algorithms and clustering

### Frontend Core  
- **Next.js 14**: React framework with SSR
- **TypeScript**: Type safety
- **Zustand**: State management
- **Recharts**: Data visualization
- **Socket.io**: Real-time communication

### Infrastructure
- **Kafka**: Message streaming
- **Redis**: Caching and queues
- **Elasticsearch**: Search and analytics

## Security Considerations

- API authentication with JWT tokens
- Rate limiting on all endpoints  
- Input sanitization and validation
- CORS configuration for frontend access
- Secure handling of API keys and secrets
- GDPR-compliant data handling

## Important Development Guidelines

### Commit Messages and Attribution
**CRITICAL**: Never reference Claude, AI assistance, or add AI co-authorship in commit messages. All commits should appear as normal human development work without any mention of AI assistance. This is a strict requirement that must always be followed.

## Performance Guidelines

- Async/await throughout for non-blocking I/O
- Database connection pooling
- Redis caching for frequently accessed data
- Batch processing for ML operations
- WebSocket for real-time updates instead of polling
- Horizontal scaling ready with stateless services
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

### Standard Setup
```bash
# Setup environment configuration
cp .env.example .env
# Edit .env file with your API keys (Twitter, Reddit, News APIs)

# Start infrastructure services (all containers use host networking)
podman-compose up -d

# Setup Python virtual environment for backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Setup frontend dependencies  
cd ../frontend
npm install

# Start development servers (in separate terminals)
# Terminal 1: Backend
cd backend && source .venv/bin/activate
python -m app.main

# Terminal 2: Frontend  
cd frontend
npm run dev
```

### Using Nix (Alternative)
```bash
# Enter development shell (provides system tools only)
nix develop

# Follow the standard setup steps above
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

### Infrastructure Management (Podman)
```bash
podman-compose up -d                    # Start all infrastructure services
podman-compose down                     # Stop all services  
podman-compose logs -f <service>        # View logs
podman-compose restart <service>        # Restart service
podman ps                              # Check container status
```

### Service URLs
When infrastructure is running, services are available at:
- **PostgreSQL**: localhost:5432 (user: veracity_user, db: veracity)
- **MongoDB**: localhost:27017 (user: veracity_user, db: veracity)  
- **Redis**: localhost:6379
- **Elasticsearch**: localhost:9200
- **Kafka**: localhost:9092

### Backend Development
```bash
# Activate virtual environment first
cd backend && source .venv/bin/activate

# Start development server (with auto-reload)
python -m app.main
# Or alternatively: uvicorn app.main:app --reload

# Run tests
pytest tests/

# Code formatting and linting (using ruff - replaces black, isort, flake8)
ruff check .                    # Lint code
ruff check . --fix              # Fix auto-fixable issues
ruff format .                   # Format code
ruff format . --check           # Check formatting without changes

# Type checking
mypy .
```

### Frontend Development  
```bash
cd frontend

npm run dev                 # Start development server
npm run build               # Production build
npm run lint                # Lint TypeScript/React
npm run type-check          # TypeScript validation
```

### Database Operations
```bash
# PostgreSQL (password: veracity_password)
export PGPASSWORD=veracity_password
psql -h localhost -U veracity_user -d veracity

# MongoDB
podman exec -it veracity-mongodb mongosh -u veracity_user -p veracity_password

# Redis
redis-cli -h localhost -p 6379

# Elasticsearch
curl http://localhost:9200/_cluster/health
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

### GitHub Issue Management

#### Issue Labels
The repository uses a comprehensive labeling system for organization:

**Component Labels:**
- `backend` - Backend/API related work
- `frontend` - Frontend/UI related work  
- `ml-nlp` - Machine Learning and NLP components
- `data-ingestion` - Social media data collection
- `real-time` - WebSocket and real-time features
- `infrastructure` - DevOps and deployment
- `database` - Database operations
- `api` - API endpoints and documentation

**Feature Type Labels:**
- `core-feature` - Essential platform functionality
- `security` - Security and privacy features
- `performance` - Performance optimization
- `testing` - Testing infrastructure

**Priority Labels:**
- `priority-high` - Implement first
- `priority-medium` - Implement after high priority
- `priority-low` - Nice to have features

#### Working with Issues
```bash
# List issues by priority
gh issue list --label priority-high
gh issue list --label priority-medium

# List issues by component
gh issue list --label backend
gh issue list --label frontend

# Create new issue with labels
gh issue create --title "Issue Title" --body "Description" --label "backend,core-feature,priority-medium"

# Edit existing issue
gh issue edit 5 --add-label "performance"
gh issue edit 5 --remove-label "priority-low"

# Close issue when work is complete
gh issue close 5 --comment "Completed in PR #12"
```

#### Development Workflow
1. Pick high-priority issues first (`priority-high` label)
2. Assign yourself to the issue: `gh issue edit <number> --add-assignee @me`
3. Create feature branch: `git checkout -b feature/issue-<number>-description`
4. Implement the feature following the patterns in existing code
5. Create PR linking to issue: `gh pr create --title "Fix #<number>: Description"`
6. Ensure all tests pass and code follows project conventions
7. Request review and merge when approved
8. Close issue automatically via PR merge or manually with `gh issue close`

### Development Methodology

#### Pragmatic Hybrid Approach
We use different development approaches based on the type of work:

**Infrastructure & Setup (Implementation-First):**
- Database schemas and migrations
- Container configuration and deployment
- Basic API endpoints and routing
- Initial service integrations
- Focus: Get it working quickly, add tests for integration points

**Algorithms & Core Logic (Test-Driven Development):**
- Trust scoring algorithms
- NLP processing pipelines
- Trend detection algorithms
- Bot detection systems
- Focus: Write tests first to clarify requirements and catch edge cases

**API Endpoints (Contract-First):**
- Define API interface and schemas first
- Implement endpoints with proper error handling
- Test happy path and error cases
- Leverage FastAPI's automatic validation

**Frontend Components (Component-Driven):**
- Build components in isolation
- Visual and interaction testing
- Responsive design validation
- Accessibility compliance testing

#### Testing Strategy by Component Type

**Infrastructure Testing:**
```bash
# Integration tests for database connections
# End-to-end tests for data flow
# Performance tests under load
# Docker container health checks
```

**Algorithm Testing:**
```python
# Unit tests with known input/output pairs
# Property-based testing for edge cases
# Performance benchmarks
# A/B testing frameworks for algorithm tuning
```

**API Testing:**
```python
# FastAPI test client for endpoint testing
# Authentication and authorization tests
# Rate limiting validation
# Error response verification
```

**Frontend Testing:**
```javascript
# Component unit tests with React Testing Library
# E2E tests with Playwright
# Visual regression testing
# Accessibility audits
```

#### Code Quality Standards

**Backend (Python):**
- Black for code formatting
- isort for import sorting
- flake8 for linting
- mypy for type checking
- 80%+ test coverage for core algorithms
- Async/await patterns throughout

**Frontend (TypeScript):**
- Prettier for code formatting
- ESLint for linting
- TypeScript strict mode
- Component prop validation
- Responsive design requirements

#### Performance Requirements
- API endpoints: < 200ms response time
- Database queries: < 100ms for simple operations
- ML processing: < 500ms for real-time operations
- WebSocket message delivery: < 100ms latency
- Frontend initial load: < 2 seconds

## Performance Guidelines

- Async/await throughout for non-blocking I/O
- Database connection pooling
- Redis caching for frequently accessed data
- Batch processing for ML operations
- WebSocket for real-time updates instead of polling
- Horizontal scaling ready with stateless services

## Troubleshooting

### Container Issues
```bash
# Check if all services are running
podman ps

# Check service logs
podman-compose logs <service-name>

# Restart a specific service
podman-compose restart <service-name>

# Reset all infrastructure (WARNING: deletes all data)
podman-compose down
podman volume prune -f
podman-compose up -d
```

### Network Issues
All services use host networking to avoid iptables conflicts. If you have port conflicts:
- PostgreSQL: 5432
- MongoDB: 27017
- Redis: 6379
- Elasticsearch: 9200
- Kafka: 9092

### Backend Issues
```bash
# Ensure virtual environment is activated
cd backend && source .venv/bin/activate

# Check if all dependencies are installed
pip install -r requirements.txt

# Verify database connection
python -c "from app.core.config import settings; print(settings.POSTGRES_URL)"

# Check if spaCy model is installed
python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('spaCy model loaded')"
```

### API Keys and Configuration
Make sure your `.env` file has the required API keys:
```bash
# Check current environment configuration
cat .env

# Verify required variables are set
grep -E "TWITTER_BEARER_TOKEN|REDDIT_CLIENT_ID|SECRET_KEY" .env
```
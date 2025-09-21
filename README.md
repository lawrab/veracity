# Veracity - Social Media Trend & News Trustability Platform

A real-time platform that monitors social media trends, correlates them with mainstream media coverage, and provides dynamic trustability ratings for emerging stories and rumors.

## Features

- **Real-time Trend Detection**: Monitor Twitter/X, Reddit, TikTok, Instagram for emerging narratives
- **Trust Scoring**: Dynamic credibility ratings based on multiple signals
- **Correlation Engine**: Track how social media trends evolve into mainstream news
- **Bot Detection**: Identify coordinated inauthentic behavior
- **Interactive Dashboard**: Real-time visualization of trending stories and trust scores

## Architecture

- **Backend**: FastAPI (Python) with async processing
- **Frontend**: Next.js 14+ with TypeScript
- **Databases**: PostgreSQL, MongoDB, Elasticsearch, Redis
- **Queue System**: Apache Kafka for ingestion, Redis for real-time updates
- **Infrastructure**: Docker + Kubernetes deployment

## Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd veracity

# Setup environment configuration
cp .env.example .env
# Edit .env with your API keys (Twitter, Reddit, etc.)

# Start infrastructure services (PostgreSQL, MongoDB, Redis, Elasticsearch, Kafka)
podman-compose up -d

# Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Start backend development server
python -m app.main

# Frontend setup (in a new terminal)
cd frontend
npm install
npm run dev
```

The application will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Infrastructure Services

Infrastructure services run in containers and are accessible at:
- **PostgreSQL**: localhost:5432
- **MongoDB**: localhost:27017  
- **Redis**: localhost:6379
- **Elasticsearch**: localhost:9200
- **Kafka**: localhost:9092

### Container Management

```bash
# Start all infrastructure services
podman-compose up -d

# Stop all services
podman-compose down

# View logs
podman-compose logs <service-name>

# Check service status
podman ps
```

## Project Structure

```
veracity/
├── backend/           # FastAPI backend services
├── frontend/          # Next.js frontend application
├── infrastructure/    # Docker and Kubernetes configs
├── data/             # Data storage and processing
└── docs/             # Documentation
```

## Development

See [CLAUDE.md](./CLAUDE.md) for detailed development guidelines and commands.
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

# Start development environment
docker-compose up -d

# Backend setup
cd backend
pip install -r requirements.txt
python -m app.main

# Frontend setup
cd frontend
npm install
npm run dev
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
# Research Agent API

A backend API for an intelligent agent designed to automate literature review and scientific discovery. This application finds, analyzes, and summarizes research papers.

## Features

- **Paper Crawling**: Automatically collects research papers from multiple academic sources (currently supports ACL Anthology)
- **PDF Parsing**: Extracts and structures content from research papers
- **RESTful API**: Clean interface for initiating crawling jobs, retrieving papers, and accessing analysis results
- **MongoDB Integration**: Efficient storage and retrieval of paper metadata and content

## Tech Stack

- **FastAPI**: High-performance web framework for building APIs
- **MongoDB**: NoSQL document database for flexible data storage
- **Docker**: Containerized deployment for consistent development and production environments

## Getting Started

### Prerequisites

- Python 3.12 or higher
- MongoDB instance (local or remote)
- Docker and Docker Compose
- UV package manager

### Environment Variables

Create the necessary environment configuration files:

```bash
# From project root
cp .env.example .env
cp backend/.env.example backend/.env
```

Then edit these files to configure your specific settings.

### Local Development

1. Clone the repository:

```bash
git clone https://github.com/dangvonguyen/research-agent.git
cd research-agent/backend
```

2. Set up a virtual environment and install dependencies:

```bash
uv sync
source .venv/bin/activate
```

3. Run the application with hot-reload:

```bash
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

### Docker Deployment

1. Build and start the containers:

```bash
docker compose -f ../docker-compose.yml up
```

2. Enable auto-reload during development:

```bash
docker compose watch
```

## API Documentation

Once running, access the interactive API documentation:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
app/                            # Main application package
├── api/routes/                 # API endpoints and routes
│   ├── crawlers.py             # Crawler job and config endpoints
│   └── papers.py               # Research paper endpoints
├── core/                       # Core application components
├── repos/                      # Database repositories for data access
├── tools/                      # Domain-specific utilities
│   ├── crawlers/               # Web scraping and data collection tools
│   └── parsers/                # Data extraction and processing tools
├── utils.py                    # General utilities
├── logging.py                  # Logging configuration
├── models.py                   # Pydantic data models for the application
└── main.py                     # FastAPI application entry point
```

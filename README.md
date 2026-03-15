# Exam Calibrator

A FastAPI application that uses a 1-Parameter Logistic (Rasch) Item Response Theory (IRT) model to estimate student abilities and question difficulties from binary exam responses.

## Overview

The app collects student–question interactions (correct/incorrect) and fits a Rasch model via gradient ascent on the log-likelihood. It then stores estimated abilities (θ) and difficulties (b) back into the database.

## Quick Start

```bash
just install    # Install dependencies (uv sync)
just fastapi   # Start the FastAPI server
just mcp       # Start the MCP server (readonly DB queries)
```

API docs: http://localhost:8000/docs

### MCP Server

The MCP server exposes tools for AI clients (Claude, Cursor, etc.):

| Tool | Description |
|------|-------------|
| `list_students` | List all students (id, name, ability) |
| `list_questions` | List all questions (id, label, difficulty) |
| `list_responses` | List all student-question responses |
| `get_student` | Get a student by name or id |
| `get_question` | Get a question by label or id |
| `calibrate` | Fit the IRT model and update ability/difficulty estimates in the DB |

Add to Cursor/Claude MCP config to use with the exam calibrator database.

## API Endpoints

### Responses

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/responses/attempt` | Record a response. Creates student/question if they don't exist. |
| `GET` | `/responses/students` | List all students with ability estimates |
| `GET` | `/responses/questions` | List all questions with difficulty estimates |
| `GET` | `/responses/data` | Download responses as CSV |
| `DELETE` | `/responses/reset` | Clear all data |

### Calibration

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/calibrate` | Fit the IRT model and update student abilities and question difficulties |

### Examples

**Record a response:**
```bash
curl -X POST http://localhost:8000/responses/attempt \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"student_name": "Alice", "question_label": "Q1", "score_binary": 1}'
```

**Run calibration:**
```bash
curl -X POST http://localhost:8000/calibrate -H "X-API-Key: your-api-key"
```

**Download data as CSV:**
```bash
curl -O -J http://localhost:8000/responses/data -H "X-API-Key: your-api-key"
```

*If `API_KEY` is not set, omit the `X-API-Key` header.*

## Configuration

Settings are loaded from environment variables or a `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_URL` | `sqlite:///exam.db` | Database connection string |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `RELOAD` | `true` | Enable hot reload |
| `API_URL` | `http://localhost:8000` | FastAPI base URL (for MCP calibrate tool) |
| `API_KEY` | *(none)* | API key for securing endpoints. If unset, no auth required (dev only). Pass via `X-API-Key` header. |

## Project Structure

```
src/
├── fast_api.py   # FastAPI app entry point
├── mcp_server.py # FastMCP server (readonly DB tools)
├── config.py     # Pydantic settings
├── db.py         # SQLAlchemy models (Student, Question, Response)
├── models.py     # Pydantic request/response schemas
├── router.py     # API routes
└── core.py       # IRT fitting logic (fit_irt, run_calibration)
```

## Docker Compose

Run both FastAPI and MCP server on the local network:

```bash
just compose
# or: docker compose up --build
```

If you get "permission denied" on the Docker socket, add your user to the `docker` group:
`sudo usermod -aG docker $USER`, then log out and back in (or run `newgrp docker`).

- **FastAPI**: http://localhost:8000 (or your machine's IP, e.g. http://192.168.1.x:8000)
- **MCP (HTTP)**: http://localhost:9000/mcp (or http://192.168.1.x:9000/mcp)

Both services share a SQLite database via a persistent volume.

## Requirements

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

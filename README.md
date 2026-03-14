# Exam Calibrator

A FastAPI application that uses a 1-Parameter Logistic (Rasch) Item Response Theory (IRT) model to estimate student abilities and question difficulties from binary exam responses.

## Overview

The app collects student–question interactions (correct/incorrect) and fits a Rasch model via gradient ascent on the log-likelihood. It then stores estimated abilities (θ) and difficulties (b) back into the database.

## Quick Start

```bash
just install    # Install dependencies (uv sync)
just run        # Start the server
```

API docs: http://localhost:8000/docs

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
  -d '{"student_name": "Alice", "question_label": "Q1", "score_binary": 1}'
```

**Run calibration:**
```bash
curl -X POST http://localhost:8000/calibrate
```

**Download data as CSV:**
```bash
curl -O -J http://localhost:8000/responses/data
```

## Configuration

Settings are loaded from environment variables or a `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_URL` | `sqlite:///exam.db` | Database connection string |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `RELOAD` | `true` | Enable hot reload |

## Project Structure

```
src/
├── main.py      # FastAPI app entry point
├── config.py    # Pydantic settings
├── db.py        # SQLAlchemy models (Student, Question, Response)
├── models.py    # Pydantic request/response schemas
├── router.py    # API routes
└── core.py      # IRT fitting logic (fit_irt, run_calibration)
```

## Requirements

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

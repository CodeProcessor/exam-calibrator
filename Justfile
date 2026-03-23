# Exam Calibrator - Just commands
# Run `just` or `just list` to see available commands

default:
    @just --list

list:
    @just --list

install:
    uv sync

fastapi:
    uv run python src/fast_api.py

mcp:
    uv run python src/mcp_server.py

compose:
    docker compose up --build

run:
    docker compose up --build -d

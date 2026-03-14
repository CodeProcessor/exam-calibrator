# Exam Calibrator - Just commands
# Run `just` or `just list` to see available commands

default:
    @just --list

list:
    @just --list

install:
    uv sync

run:
    uv run python src/main.py

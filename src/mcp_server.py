"""FastMCP server for the exam calibrator: readonly queries and calibration."""

import ast
import sqlite3

import httpx
from fastmcp import FastMCP
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from config import settings
from db import Question, Response, Student, engine, init_db
from models import ResponseRead

# Ensure tables exist (idempotent)
init_db()

# Read-only engine for query tool: SQLite rejects writes at DB level
def _readonly_engine():
    url = make_url(settings.db_url)
    if url.drivername == "sqlite":
        path = url.database or "exam.db"
        def connect():
            return sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        return create_engine("sqlite://", creator=connect)
    return engine  # non-SQLite: fall back to normal engine
_readonly = _readonly_engine()

_auth = None


if settings.azure_tenant_id and settings.azure_client_id and settings.azure_client_secret:
    from fastmcp.server.auth.providers.azure import AzureProvider
    
    # Parse azure_scopes: handle both "scope1,scope2" and "['scope1', 'scope2']" formats
    try:
        # Try parsing as Python literal (list or string)
        parsed_scopes = ast.literal_eval(settings.azure_scopes)
        if isinstance(parsed_scopes, str):
            scopes = [s.strip() for s in parsed_scopes.split(",")]
        else:
            scopes = parsed_scopes
    except (ValueError, SyntaxError):
        # Fall back to simple comma split
        scopes = [s.strip() for s in settings.azure_scopes.split(",")]
    
    _auth = AzureProvider(
        tenant_id=settings.azure_tenant_id,
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
        required_scopes=scopes,
        base_url=settings.azure_base_url,
    )

mcp = FastMCP(
    name="Exam Calibrator",
    instructions="Access exam calibrator data: students, questions, responses. Use calibrate to fit the IRT model and update ability/difficulty estimates.",
    auth=_auth,
)


def _get_session() -> Session:
    return Session(engine)


@mcp.tool()
def query(sql: str) -> list[dict]:
    """Run a read-only SQL query. Only SELECT statements are allowed. Multiple statements are not allowed.

    Schema (tables):
    - students: id (INTEGER), name (TEXT), ability (REAL), timestamp (DATETIME)
    - questions: id (INTEGER), label (TEXT), difficulty (REAL), timestamp (DATETIME)
    - responses: student_id (INTEGER), question_id (INTEGER), score (INTEGER), timestamp (DATETIME)
    """
    sql_stripped = sql.strip()
    sql_upper = sql_stripped.upper()
    if not sql_upper.startswith("SELECT"):
        return [{"error": "Only SELECT queries are allowed"}]
    if ";" in sql_stripped:
        return [{"error": "Multiple statements not allowed"}]
    with _readonly.connect() as conn:
        result = conn.execute(text(sql))
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]


@mcp.tool()
def list_tables() -> list[str]:
    """List all tables in the database."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        return [row[0] for row in result.fetchall()]

@mcp.tool
def add_an_attempt_using_api(student_name: str, question_label: str, score: int) -> dict:
    """
    # Add a student response using the FastAPI endpoint. This is a bit hacky but it ensures the MCP and API stay in sync and uses the same logic for creating/updating records.
    """
    url = f"{settings.api_url.rstrip('/')}/responses/attempt"
    headers = {"Content-Type": "application/json"}
    if settings.api_key:
        headers["X-API-Key"] = settings.api_key
    payload = ResponseRead(
        student_name=student_name,
        question_label=question_label,
        score_binary=0 if score == 0 else 1,
    ).model_dump()
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError as e:
        return {"error": f"Could not reach API at {settings.api_url}: {e}"}
    except httpx.HTTPStatusError as e:
        try:
            detail = e.response.json().get("detail", str(e.response.text))
        except Exception:
            detail = str(e.response.text)
        return {"error": f"API error {e.response.status_code}: {detail}"}

@mcp.tool
def get_question(question_label: str | None = None, question_id: int | None = None) -> dict | None:
    """Get a single question by label or id. Returns None if not found."""
    with _get_session() as session:
        if question_label:
            question = session.query(Question).filter(Question.label == question_label).first()
        elif question_id is not None:
            question = session.get(Question, question_id)
        else:
            return None
        if not question:
            return None
        return {"id": question.id, "label": question.label, "difficulty": question.difficulty}


@mcp.tool
def calibrate() -> dict:
    """Fit the Rasch IRT model on all responses and update student abilities and question difficulties. Calls the FastAPI /calibrate endpoint. Returns the fitted estimates and rankings."""
    url = f"{settings.api_url.rstrip('/')}/calibrate"
    headers = {}
    if settings.api_key:
        headers["X-API-Key"] = settings.api_key
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError as e:
        return {"error": f"Could not reach API at {settings.api_url}: {e}"}
    except httpx.HTTPStatusError as e:
        try:
            detail = e.response.json().get("detail", str(e.response.text))
        except Exception:
            detail = str(e.response.text)
        return {"error": f"API error {e.response.status_code}: {detail}"}


if __name__ == "__main__":
    import os
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "9000"))
    if transport == "http":
        mcp.run(transport="http", host=host, port=port)
    else:
        mcp.run()

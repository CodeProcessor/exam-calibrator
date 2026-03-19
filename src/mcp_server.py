"""FastMCP server for the exam calibrator: readonly queries and calibration."""

import httpx
from fastmcp import FastMCP
from sqlalchemy.orm import Session

from config import settings
from db import Question, Response, Student, engine, init_db

# Ensure tables exist (idempotent)
init_db()

_auth = None
if settings.azure_tenant_id and settings.azure_client_id and settings.azure_client_secret:
    from fastmcp.server.auth.providers.azure import AzureProvider
    _auth = AzureProvider(
        tenant_id=settings.azure_tenant_id,
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
        required_scopes=settings.azure_scopes,
        base_url=settings.azure_base_url,
    )

mcp = FastMCP(
    name="Exam Calibrator",
    instructions="Access exam calibrator data: students, questions, responses. Use calibrate to fit the IRT model and update ability/difficulty estimates.",
    auth=_auth,
)


def _get_session() -> Session:
    return Session(engine)


@mcp.tool
def list_students() -> list[dict]:
    """List all students with their name, ability estimate, and id."""
    with _get_session() as session:
        rows = session.query(Student).all()
        return [
            {"id": s.id, "name": s.name, "ability": s.ability}
            for s in rows
        ]


@mcp.tool
def list_questions() -> list[dict]:
    """List all questions with their label, difficulty estimate, and id."""
    with _get_session() as session:
        rows = session.query(Question).all()
        return [
            {"id": q.id, "label": q.label, "difficulty": q.difficulty}
            for q in rows
        ]


@mcp.tool
def list_responses() -> list[dict]:
    """List all student-question responses with student name, question label, and score (0 or 1)."""
    with _get_session() as session:
        rows = (
            session.query(Response, Student.name, Question.label)
            .join(Student, Response.student_id == Student.id)
            .join(Question, Response.question_id == Question.id)
            .all()
        )
        return [
            {"student_name": name, "question_label": label, "score": r.score}
            for r, name, label in rows
        ]


@mcp.tool
def get_student(student_name: str | None = None, student_id: int | None = None) -> dict | None:
    """Get a single student by name or id. Returns None if not found."""
    with _get_session() as session:
        if student_name:
            student = session.query(Student).filter(Student.name == student_name).first()
        elif student_id is not None:
            student = session.get(Student, student_id)
        else:
            return None
        if not student:
            return None
        return {"id": student.id, "name": student.name, "ability": student.ability}


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

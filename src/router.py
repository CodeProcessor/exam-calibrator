import csv
import io
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response as FileResponse
from sqlalchemy.orm import Session

from auth import verify_api_key
from core import run_calibration
from db import Question, Response, Student, engine
from models import CalibrationResult, QuestionRead, ResponseCreate, ResponseRead, StudentRead
from structlog import get_logger

router = APIRouter(
    prefix="/responses",
    tags=["responses"],
    dependencies=[Depends(verify_api_key)],
)
calibrate_router = APIRouter(
    tags=["calibration"],
    dependencies=[Depends(verify_api_key)],
)

logger = get_logger()


def get_session():
    """Get a session from the database."""  
    with Session(engine) as session:
        yield session


@calibrate_router.post(
    "/calibrate",
    response_model=CalibrationResult,
    summary="Fit IRT model",
    description="Fits the 1-Parameter Logistic (Rasch) IRT model on all recorded responses. Returns estimated student abilities (θ), question difficulties (b), and their rankings. Requires at least some response data.",
)
def calibrate():
    try:
        result = run_calibration()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return CalibrationResult(
        student_abilities=result.student_abilities,
        question_difficulties=result.question_difficulties,
        student_ranking=result.student_ranking,
        question_ranking=result.question_ranking,
    )

@calibrate_router.post(
    "/reset_scores",
    summary="Clear ability/difficulty estimates",
    description="Clears all student ability and question difficulty estimates from the database. Use before re-calibrating or to start fresh. Does not delete responses.",
)
def reset_scores(session: Session = Depends(get_session)):
    session.query(Student).update({Student.ability: None})
    session.query(Question).update({Question.difficulty: None})
    session.commit()
    return {"message": "Scores reset successfully"}

@router.post(
    "/attempt",
    response_model=ResponseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record a response",
    description="Records a student's answer to a question (0 = incorrect, 1 = correct). Creates the student and question if they don't exist. Updates the score if the student already answered this question.",
)
def create_response(body: ResponseCreate, session: Session = Depends(get_session)):
    student = session.query(Student).filter(Student.name == body.student_name).first()
    if not student:
        student = Student(name=body.student_name)
        session.add(student)
        session.flush()
        logger.info("Created student", student_name=body.student_name)

    question = session.query(Question).filter(Question.label == body.question_label).first()
    if not question:
        question = Question(label=body.question_label)
        session.add(question)
        session.flush()
        logger.info("Created question", question_label=body.question_label)
    # if response already exists, update the score
    response = session.query(Response).filter(Response.student_id == student.id, Response.question_id == question.id).first()
    if response:
        response.score = body.score_binary
        logger.info("Updated response", student_name=student.name, question_label=question.label, score_binary=body.score_binary)
    else:
        response = Response(
            student_id=student.id,
            question_id=question.id,
            score=body.score_binary,
        )
        session.add(response)
        session.flush()
        logger.info("Created response", student_name=student.name, question_label=question.label, score_binary=body.score_binary)
    
    session.commit()
    return ResponseRead(
        student_name=student.name,
        question_label=question.label,
        score_binary=response.score,
    )


@router.get(
    "/questions",
    response_model=list[QuestionRead],
    summary="List all questions",
    description="Returns all questions with their labels and difficulty estimates (if calibration has been run).",
)
def get_questions(session: Session = Depends(get_session)):
    questions = session.query(Question).all()
    return [QuestionRead.model_validate(question) for question in questions]


@router.get(
    "/students",
    response_model=list[StudentRead],
    summary="List all students",
    description="Returns all students with their names and ability estimates (if calibration has been run).",
)
def get_students(session: Session = Depends(get_session)):
    students = session.query(Student).all()
    return [StudentRead.model_validate(student) for student in students]

@router.get(
    "/data",
    summary="Download response data (CSV)",
    description="Downloads all response data as a CSV file with columns: student_name, question_label, score. Use for backup or external analysis.",
)
def get_data(session: Session = Depends(get_session)):
    students = {s.id: s.name for s in session.query(Student).all()}
    questions = {q.id: q.label for q in session.query(Question).all()}
    responses = session.query(Response).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["student_name", "question_label", "score"])
    for r in responses:
        writer.writerow([
            students.get(r.student_id, ""),
            questions.get(r.question_id, ""),
            r.score,
        ])

    return FileResponse(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=responses.csv"},
    )


@router.delete(
    "/reset",
    summary="Reset database",
    description="Deletes all responses, students, and questions. Use with caution — this cannot be undone.",
)
def reset(session: Session = Depends(get_session)):
    session.query(Response).delete()
    session.query(Student).delete()
    session.query(Question).delete()
    session.commit()
    return {"message": "Database reset successfully"}
from dataclasses import dataclass
from math import exp

from sqlalchemy.orm import Session

from db import Question, Response, Student, engine


# ---------------------------------------------------------------------------
# 1-PL (Rasch) IRT model
# ---------------------------------------------------------------------------

@dataclass
class IRTResult:
    student_abilities:    dict[int, float]   # student_id -> theta
    question_difficulties: dict[int, float]  # question_id -> b
    student_ranking:      list[int]          # student_ids sorted low->high ability
    question_ranking:     list[int]          # question_ids sorted easy->hard


def p_correct(theta: float, b: float) -> float:
    """1PL IRT probability: P(correct | theta, b) = 1 / (1 + exp(-(theta - b)))."""
    return 1.0 / (1.0 + exp(-(theta - b)))


def fit_irt(
    responses: dict[int, dict[int, int]],
    lr: float = 0.01,
    n_iter: int = 1000,
) -> IRTResult:
    """
    Gradient ascent on the 1PL log-likelihood.

    responses: {student_id: {question_id: score (0 or 1)}}
    Missing entries are treated as not-attempted (ignored).
    Identifiability is enforced each iteration by centering both theta and b.
    """
    student_ids  = list(responses.keys())
    question_ids = list({q for qs in responses.values() for q in qs})

    theta = {s: 0.0 for s in student_ids}
    b     = {q: 0.0 for q in question_ids}

    for _ in range(n_iter):
        d_theta: dict[int, float] = {s: 0.0 for s in student_ids}
        d_b:     dict[int, float] = {q: 0.0 for q in question_ids}

        for s, attempts in responses.items():
            for q, score in attempts.items():
                p = p_correct(theta[s], b[q])
                residual = score - p
                d_theta[s] += residual
                d_b[q]     -= residual

        for s in student_ids:
            theta[s] += lr * d_theta[s]
        for q in question_ids:
            b[q] += lr * d_b[q]

        # Center both scales to enforce identifiability
        mean_theta = sum(theta.values()) / len(theta)
        mean_b     = sum(b.values()) / len(b)
        theta = {s: v - mean_theta for s, v in theta.items()}
        b     = {q: v - mean_b     for q, v in b.items()}

    student_ranking  = sorted(student_ids,  key=lambda s: theta[s])
    question_ranking = sorted(question_ids, key=lambda q: b[q])

    return IRTResult(
        student_abilities=theta,
        question_difficulties=b,
        student_ranking=student_ranking,
        question_ranking=question_ranking,
    )


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _load_responses(session: Session) -> dict[int, dict[int, int]]:
    """Fetch all responses and return as {student_id: {question_id: score}}."""
    rows = session.query(Response).all()
    data: dict[int, dict[int, int]] = {}
    for row in rows:
        data.setdefault(row.student_id, {})[row.question_id] = row.score
    return data


def _write_results(session: Session, result: IRTResult) -> None:
    """Persist fitted abilities and difficulties back to Student / Question tables."""
    for student_id, ability in result.student_abilities.items():
        student = session.get(Student, student_id)
        if student:
            student.ability = ability

    for question_id, difficulty in result.question_difficulties.items():
        question = session.get(Question, question_id)
        if question:
            question.difficulty = difficulty

    session.commit()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_calibration() -> IRTResult:
    """
    Load responses from the DB, fit the Rasch model, write results back,
    and return the IRTResult.
    """
    with Session(engine) as session:
        responses = _load_responses(session)

        if not responses:
            raise ValueError("No responses found in the database.")

        result = fit_irt(responses)
        _write_results(session, result)

    return result

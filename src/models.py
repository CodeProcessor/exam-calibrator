from pydantic import BaseModel, Field


class ResponseCreate(BaseModel):
    """Create a response."""
    student_name: str
    question_label: str
    score_binary: int = Field(ge=0, le=1)


class ResponseRead(BaseModel):
    """Read a response."""
    student_name: str
    question_label: str
    score_binary: int


class CalibrationResult(BaseModel):
    """Calibration result."""
    student_abilities:     dict[int, float]
    question_difficulties: dict[int, float]
    student_ranking:       list[int]
    question_ranking:      list[int]


class QuestionRead(BaseModel):
    """Read a question."""
    label: str
    difficulty: float | None

    model_config = {"from_attributes": True}


class StudentRead(BaseModel):
    """Read a student."""
    name: str
    ability: float | None

    model_config = {"from_attributes": True}

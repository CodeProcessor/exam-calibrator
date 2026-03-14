from datetime import datetime
from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config import settings

engine = create_engine(settings.db_url)


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Student(Base):
    """Student model."""
    __tablename__ = "students"

    id:      Mapped[int]           = mapped_column(primary_key=True, autoincrement=True)
    name:    Mapped[str]           = mapped_column(unique=True, nullable=False)
    ability: Mapped[float | None]  = mapped_column(default=None)
    timestamp: Mapped[datetime] = mapped_column(nullable=False, default=datetime.now, onupdate=datetime.now)


class Question(Base):
    """Question model."""
    __tablename__ = "questions"

    id:         Mapped[int]           = mapped_column(primary_key=True, autoincrement=True)
    label:      Mapped[str]           = mapped_column(unique=True, nullable=False)
    difficulty: Mapped[float | None]  = mapped_column(default=None)
    timestamp: Mapped[datetime] = mapped_column(nullable=False, default=datetime.now, onupdate=datetime.now)


class Response(Base):
    """Response model."""
    __tablename__ = "responses"
    __table_args__ = (
        UniqueConstraint("student_id", "question_id"),
        CheckConstraint("score IN (0, 1)", name="score_binary"),
    )

    student_id:  Mapped[int] = mapped_column(ForeignKey("students.id"), primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), primary_key=True)
    score:       Mapped[int] = mapped_column(nullable=False)
    timestamp: Mapped[datetime] = mapped_column(nullable=False, default=datetime.now, onupdate=datetime.now)


def init_db() -> None:
    Base.metadata.create_all(engine)

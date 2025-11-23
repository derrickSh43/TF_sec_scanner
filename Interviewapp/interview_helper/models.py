from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, nullable=True)


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    role = Column(String)
    style = Column(String)
    job_description = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    candidate = relationship("Candidate", backref="interviews")
    questions = relationship("Question", backref="interview")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"))
    index = Column(Integer)
    question_text = Column(Text)
    template_id = Column(Integer, nullable=True)


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    answer_text = Column(Text)
    audio_url = Column(String, nullable=True)
    clarity_score = Column(Integer, nullable=True)
    depth_score = Column(Integer, nullable=True)
    structure_score = Column(Integer, nullable=True)
    confidence_score = Column(Integer, nullable=True)
    feedback_text = Column(Text, nullable=True)
    suggested_improvement = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

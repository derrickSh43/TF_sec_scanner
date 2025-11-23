import os
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    func,
    not_,
)
import json
from typing import List, Optional, Dict, Any

# if not already present:
from pydantic import BaseModel, Field

# Optional: LLM client (OpenAI-style; install with `pip install openai`)
from openai import OpenAI  # type: ignore
client = OpenAI()  # expects OPENAI_API_KEY in env

evaluation_router = APIRouter(prefix="/evaluation", tags=["evaluation"])


# Default from environment
OFFLINE_MODE_DEFAULT = os.environ.get("OFFLINE_MODE", "true").lower() in ("1", "true", "yes")

# Runtime toggle you can flip from API
RUNTIME_OFFLINE = OFFLINE_MODE_DEFAULT



# /C:/Users/derri/Desktop/AI Class folder/interview_helper/helper.py
# Adds QuestionTemplate model, schemas, a router, and offline-friendly next-question logic.
# Assumes existing project has `database.py` exposing `Base` and `get_db`, and `models.py` with
# `Question` and `Interview` SQLAlchemy models. Adapt imports if your project layout differs.
# ============================================================
#   INTERVIEWER BRAIN — Answer Evaluation (Offline + Online)
# ============================================================

import json
import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

class AnswerEvaluationRequest(BaseModel):
    question_text: str
    answer_text: str
    role: Optional[str] = None
    style: Optional[str] = None
    job_description: Optional[str] = None
    evaluation_mode: Optional[str] = Field(
        default="standard", description="standard | deep_dive | senior_panel"
    )


class AnswerEvaluationResponse(BaseModel):
    clarity_score: int = 0
    depth_score: int = 0
    structure_score: int = 0
    relevance_score: int = 0
    seniority_signal_score: int = 0
    strengths: List[str] = []
    gaps: List[str] = []
    improvement_tip: str = ""
    follow_up_questions: List[str] = []


def _offline_evaluate(payload: AnswerEvaluationRequest) -> AnswerEvaluationResponse:
    """
    Cheap heuristic scoring for offline mode.
    """
    text = payload.answer_text.strip()
    length = len(text.split())

    clarity = 2
    depth = 2
    structure = 2
    relevance = 2
    seniority = 1

    strengths = []
    gaps = []

    if length > 80:
        depth += 1
        strengths.append("Good detail and length for an interview answer.")
    else:
        gaps.append("Answer is short; expand with examples and specifics.")

    keywords = ["terraform", "kubernetes", "pipeline", "security", "monitoring"]
    if any(k in text.lower() for k in keywords):
        relevance += 1
        strengths.append("Mentions relevant tools for the role.")
    else:
        gaps.append("Could use more concrete tools/practices.")

    if "i led" in text.lower() or "designed" in text.lower():
        seniority += 1
        strengths.append("Shows ownership and leadership.")
    else:
        gaps.append("Does not strongly signal senior-level ownership.")

    # Keep scores 1–5
    clarity = min(max(clarity, 1), 5)
    depth = min(max(depth, 1), 5)
    structure = min(max(structure, 1), 5)
    relevance = min(max(relevance, 1), 5)
    seniority = min(max(seniority, 1), 5)

    tip = (
        "Use STAR (Situation–Task–Action–Result), name tools, and clarify your leadership role."
    )

    return AnswerEvaluationResponse(
        clarity_score=clarity,
        depth_score=depth,
        structure_score=structure,
        relevance_score=relevance,
        seniority_signal_score=seniority,
        strengths=strengths or ["Clear answer but could be expanded."],
        gaps=gaps or ["Add ownership signals and concrete details."],
        improvement_tip=tip,
        follow_up_questions=[
            "Can you walk through a real example?",
            "What trade-offs did you consider?",
        ],
    )


def _online_evaluate(payload: AnswerEvaluationRequest) -> AnswerEvaluationResponse:
    """
    Evaluate the answer using OpenAI.
    """
    if not openai.api_key:
        return _offline_evaluate(payload)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a senior cloud/DevOps/security hiring manager. "
                "You evaluate candidate interview answers using strict scoring."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "question": payload.question_text,
                    "answer": payload.answer_text,
                    "role": payload.role,
                    "style": payload.style,
                    "job_description": payload.job_description,
                    "evaluation_mode": payload.evaluation_mode,
                },
                indent=2,
            ),
        },
    ]

    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3,
        )
        data = json.loads(completion.choices[0].message["content"])

        return AnswerEvaluationResponse(
            clarity_score=data.get("clarity_score", 0),
            depth_score=data.get("depth_score", 0),
            structure_score=data.get("structure_score", 0),
            relevance_score=data.get("relevance_score", 0),
            seniority_signal_score=data.get("seniority_signal_score", 0),
            strengths=data.get("strengths", []),
            gaps=data.get("gaps", []),
            improvement_tip=data.get("improvement_tip", ""),
            follow_up_questions=data.get("follow_up_questions", []),
        )

    except Exception as e:
        print(f"[LLM Evaluation Error] {e}")
        return _offline_evaluate(payload)


@evaluation_router.post("/evaluate-answer", response_model=AnswerEvaluationResponse)
def evaluate_answer(payload: AnswerEvaluationRequest):
    """
    Brain mode switch: offline = heuristic, online = OpenAI.
    """
    from main import RUNTIME_OFFLINE

    if RUNTIME_OFFLINE:
        return _offline_evaluate(payload)
    else:
        return _online_evaluate(payload)

# Import hooking points from your project; adjust paths if needed.
# Expected to exist: database.Base, database.get_db, models.Question, models.Interview
try:
    # Prefer project-provided exports if available.
    from database import Base, get_db  # type: ignore
except Exception:
    # Minimal fallback to avoid import errors while editing. Replace with your project's import.
    Base = declarative_base()

    def get_db():
        raise RuntimeError(
            "get_db dependency not configured. Import it from your project (database.get_db)."
        )

try:
    import models  # type: ignore
except Exception:
    # Allows file editing even if models.py isn't wired yet;
    # will fail at runtime if code actually uses models.
    models = None

# Configuration flag for offline mode (default True)
# Default from env (what you had before)
OFFLINE_MODE_DEFAULT = os.environ.get("OFFLINE_MODE", "true").lower() in ("1", "true", "yes")

# Runtime flag we can flip via API (starts same as default)
RUNTIME_OFFLINE = OFFLINE_MODE_DEFAULT





# --- SQLAlchemy model: QuestionTemplate ---
class QuestionTemplate(Base):
    __tablename__ = "question_templates"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(128), nullable=False, index=True)
    style = Column(
        String(64),
        nullable=False,
        index=True,
        comment='One of: "standard_behavioral", "deep_technical", "candidate_led", "stress_test"',
    )
    difficulty = Column(String(16), nullable=True, index=True)
    question_text = Column(Text, nullable=False)
    tags = Column(String(256), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# --- Pydantic schemas ---
class QuestionTemplateBase(BaseModel):
    role: str = Field(..., example="Senior DevOps Engineer")
    style: str = Field(..., example="deep_technical")
    difficulty: Optional[str] = Field(None, example="medium")
    question_text: str = Field(..., example="Describe your CI/CD pipeline.")
    tags: Optional[str] = Field(None, example="ci-cd,jenkins,terraform")

    @validator("style")
    def validate_style(cls, v):
        allowed = {
            "standard_behavioral",
            "deep_technical",
            "candidate_led",
            "stress_test",
        }
        if v not in allowed:
            raise ValueError(f"style must be one of {sorted(list(allowed))}")
        return v

    @validator("difficulty")
    def validate_difficulty(cls, v):
        allowed = {"easy", "medium", "hard", None}
        if v not in allowed:
            raise ValueError("difficulty must be 'easy', 'medium', 'hard', or null")
        return v


class QuestionTemplateCreate(QuestionTemplateBase):
    pass


class QuestionTemplateRead(QuestionTemplateBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True


class QuestionTemplateUpdate(BaseModel):
    question_text: Optional[str]
    difficulty: Optional[str]
    tags: Optional[str]
    is_active: Optional[bool]

    @validator("difficulty")
    def validate_difficulty(cls, v):
        allowed = {"easy", "medium", "hard", None}
        if v not in allowed:
            raise ValueError("difficulty must be 'easy', 'medium', 'hard', or null")
        return v
    
class AnswerEvaluationRequest(BaseModel):
    question_text: str
    answer_text: str
    role: Optional[str] = None
    style: Optional[str] = None
    job_description: Optional[str] = None
    evaluation_mode: Optional[str] = Field(
        default="standard", description="standard | deep_dive | senior_panel"
    )


class AnswerEvaluationResponse(BaseModel):
    clarity_score: int = 0
    depth_score: int = 0
    structure_score: int = 0
    relevance_score: int = 0
    seniority_signal_score: int = 0
    strengths: List[str] = []
    gaps: List[str] = []
    improvement_tip: str = ""
    follow_up_questions: List[str] = []



# --- Router for question templates ---
router = APIRouter(prefix="/question-templates", tags=["question_templates"])


@router.get("", response_model=List[QuestionTemplateRead])
def list_question_templates(
    role: Optional[str] = None,
    style: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(QuestionTemplate).filter(QuestionTemplate.is_active == True)
    if role:
        q = q.filter(QuestionTemplate.role == role)
    if style:
        q = q.filter(QuestionTemplate.style == style)
    templates = q.order_by(QuestionTemplate.id).all()
    return templates


@router.post("", response_model=QuestionTemplateRead, status_code=status.HTTP_201_CREATED)
def create_question_template(payload: QuestionTemplateCreate, db: Session = Depends(get_db)):
    tpl = QuestionTemplate(
        role=payload.role,
        style=payload.style,
        difficulty=payload.difficulty,
        question_text=payload.question_text,
        tags=payload.tags,
        is_active=True,
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl

@router.post("/evaluate-answer", response_model=AnswerEvaluationResponse)
def evaluate_answer(payload: AnswerEvaluationRequest):
    """
    Evaluate a candidate's answer like a senior hiring manager.
    Uses OFFLINE_MODE stub by default. When OFFLINE_MODE=False,
    calls an LLM for richer feedback (if configured).
    """
    # Simple offline stub: no external call, deterministic
    if RUNTIME_OFFLINE:
        text = payload.answer_text.strip()
        length = len(text.split())

        # crude heuristics just so it's usable without an LLM
        clarity = 3
        depth = 3
        structure = 3
        relevance = 3
        seniority = 3

        if length < 20:
            clarity -= 1
            depth -= 1
            structure -= 1
        elif length > 80:
            depth += 1

        # keep scores within 1–5
        def clamp(v): return max(1, min(5, v))

        clarity = clamp(clarity)
        depth = clamp(depth)
        structure = clamp(structure)
        relevance = clamp(relevance)
        seniority = clamp(seniority)

        strengths = []
        gaps = []

        if length >= 40:
            strengths.append("You gave a reasonably detailed answer instead of one-liners.")
        else:
            gaps.append("The answer is quite short. Add more context and show your thought process.")

        if "rollback" in text.lower() or "monitor" in text.lower():
            strengths.append("You mentioned rollback/monitoring, which is a key reliability signal.")
        else:
            gaps.append("Consider explicitly calling out rollback and monitoring/observability.")

        improvement_tip = (
            "Next time, use a simple structure: context → options → trade-offs → decision → risks. "
            "Aim for 60–120 seconds of talking for a senior-level question."
        )

        return AnswerEvaluationResponse(
            clarity_score=clarity,
            depth_score=depth,
            structure_score=structure,
            relevance_score=relevance,
            seniority_signal_score=seniority,
            strengths=strengths or ["Solid starting point overall."],
            gaps=gaps or ["You can still sharpen the narrative by highlighting trade-offs and risks."],
            improvement_tip=improvement_tip,
            follow_up_questions=[
                "If this design started failing in production, what signals would you look at first?",
                "How would you adapt this approach in a regulated or high-security environment?",
            ],
        )

    # --- LLM mode (set OFFLINE_MODE=false in env to use this) ---
    prompt = f"""
You are a senior cloud/devops hiring manager.

Evaluate the candidate's answer to an interview question using this rubric:
- clarity (1–5)
- technical depth (1–5)
- structure (1–5)
- relevance to the question and role (1–5)
- seniority signal (1–5): do they think in terms of trade-offs, risk, and impact?

Role: {payload.role}
Style: {payload.style}
Evaluation mode: {payload.evaluation_mode}
Job description (if any): {payload.job_description or "N/A"}

Question:
{payload.question_text}

Candidate's answer:
{payload.answer_text}

Return ONLY a JSON object with this exact shape:
{{
  "clarity_score": int (1-5),
  "depth_score": int (1-5),
  "structure_score": int (1-5),
  "relevance_score": int (1-5),
  "seniority_signal_score": int (1-5),
  "strengths": [string],
  "gaps": [string],
  "improvement_tip": string,
  "follow_up_questions": [string]
}}
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",  # or another model you prefer
            messages=[
                {"role": "system", "content": "You are a precise, no-fluff technical interviewer."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content)
        return AnswerEvaluationResponse(**data)
    except Exception as e:
        # fallback if LLM fails
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {e}")



@router.patch("/{template_id}", response_model=QuestionTemplateRead)
def update_question_template(
    template_id: int, payload: QuestionTemplateUpdate, db: Session = Depends(get_db)
):
    tpl = db.query(QuestionTemplate).get(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(tpl, field, value)
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


@router.delete("/{template_id}", response_model=QuestionTemplateRead)
def delete_question_template(template_id: int, db: Session = Depends(get_db)):
    tpl = db.query(QuestionTemplate).get(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    # Soft delete
    tpl.is_active = False
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


from fastapi import Body

# ...

@router.get("/mode")
def get_mode():
    """
    Get current evaluation mode: 'online' (LLM) or 'offline' (stub).
    """
    return {"mode": "offline" if RUNTIME_OFFLINE else "online"}


@router.post("/mode")
def set_mode(mode: str = Body(..., embed=True, example="offline")):
    """
    Set evaluation mode. Accepts:
    { "mode": "offline" } or { "mode": "online" }
    """
    global RUNTIME_OFFLINE
    mode_lower = mode.lower()
    if mode_lower not in ("online", "offline"):
        raise HTTPException(status_code=400, detail="mode must be 'online' or 'offline'")

    RUNTIME_OFFLINE = True if mode_lower == "offline" else False
    return {"mode": "offline" if RUNTIME_OFFLINE else "online"}


# --- Offline-friendly "next question" logic ---
def call_llm_for_next_question(interview: Any, history: List[Dict[str, Any]], db: Session) -> Optional[Dict[str, Any]]:
    """
    Fetch the next question for an interview.

    Logic:
    1. Try to find an unused QuestionTemplate that matches interview.role and interview.style.
    2. If found, return dict with question_text, style_used, template_id.
    3. If none, when OFFLINE_MODE=True return None to signal interview end.
       (When OFFLINE_MODE=False you could integrate an LLM here.)
    """
    if interview is None:
        raise ValueError("interview must be provided")

    # Ensure we do not call external APIs when offline.
    if RUNTIME_OFFLINE:
        # Subquery of template_ids already used in this interview (non-null)
        used_template_ids_q = None
        try:
            if models and hasattr(models, "Question"):
                used_template_ids_q = (
                    db.query(models.Question.template_id)
                    .filter(models.Question.interview_id == interview.id)
                    .filter(models.Question.template_id != None)
                    .subquery()
                )
        except Exception:
            used_template_ids_q = None

        q = db.query(QuestionTemplate).filter(
            QuestionTemplate.role == interview.role,
            QuestionTemplate.style == interview.style,
            QuestionTemplate.is_active == True,
        ).order_by(QuestionTemplate.id)

        if used_template_ids_q is not None:
            q = q.filter(not_(QuestionTemplate.id.in_(used_template_ids_q)))

        template = q.first()
        if template:
            return {
                "question_text": template.question_text,
                "style_used": interview.style,
                "template_id": template.id,
            }
        # No template available -> end of interview in offline mode
        return None
    else:
        # Placeholder for future LLM integration when OFFLINE_MODE=False
        # For now, behave the same as offline mode (no external call)
        return None


# --- Helper: persist a question row with template_id when template used ---
def save_question_from_template(
    db: Session,
    interview: Any,
    template_id: int,
    asked_by: Optional[str] = None,
    additional_fields: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Insert a new Question row for an interview referencing a template.
    This helper expects your project to have models.Question SQLAlchemy model
    with at least: id, interview_id, question_text, template_id, created_at, asked_by (optional).
    Adjust field names to match your project's Question model.
    Returns the created Question ORM object.
    """
    if models is None or not hasattr(models, "Question"):
        raise RuntimeError("models.Question not available. Import your project's models.")

    if template_id is None:
        raise ValueError("template_id is required")

    tpl = db.query(QuestionTemplate).get(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    # Construct new Question instance. Adjust fields to match your project's model.
    question_kwargs = {
        "interview_id": interview.id,
        "question_text": tpl.question_text,
        "template_id": tpl.id,
        "created_at": datetime.utcnow(),
    }
    if asked_by is not None:
        question_kwargs["asked_by"] = asked_by
    if additional_fields:
        question_kwargs.update(additional_fields)

    q_obj = models.Question(**question_kwargs)
    db.add(q_obj)
    db.commit()
    db.refresh(q_obj)
    return q_obj
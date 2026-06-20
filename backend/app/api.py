"""
FastAPI application – exposes the LangGraph medical workflow via REST endpoints.

Endpoints:
- POST /sessions/start         → create a new consultation thread
- POST /consultation/start     → start the consultation with a patient case
- POST /consultation/resume    → resume after interrupt (patient answer / physician review)
- GET  /consultation/{id}      → get current consultation state
- GET  /consultation/{id}/report → get the final report
"""

import uuid
import asyncio
import logging
import traceback
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from app.graph import graph

# ── FastAPI app ──────────────────────────────────────────────────────────

app = FastAPI(
    title="Système Multi-Agents Médical",
    description=(
        "API pour le système d'orientation clinique multi-agents "
        "basé sur LangGraph. Ce système ne remplace pas une consultation médicale."
    ),
    version="1.0.0",
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ─────────────────────────────────────────────────────

class SessionResponse(BaseModel):
    thread_id: str
    message: str


class StartConsultationRequest(BaseModel):
    thread_id: str
    patient_case: str


class ResumeConsultationRequest(BaseModel):
    thread_id: str
    input: str
    input_type: str = "patient"  # "patient" or "physician"


class ConsultationStateResponse(BaseModel):
    thread_id: str
    status: str
    question_count: int
    current_question: Optional[str] = None
    questions: list[str] = []
    answers: list[str] = []
    diagnostic_summary: Optional[str] = None
    interim_care: Optional[str] = None
    physician_treatment: Optional[str] = None
    final_report: Optional[str] = None
    waiting_for: Optional[str] = None
    red_flags: list[str] = []


class ReportResponse(BaseModel):
    thread_id: str
    final_report: str
    disclaimer: str = "Ce système ne remplace pas une consultation médicale."


# ── Helper ───────────────────────────────────────────────────────────────

def _get_thread_config(thread_id: str) -> dict:
    """Build a LangGraph config dict with the thread ID."""
    return {"configurable": {"thread_id": thread_id}}


def _get_state_snapshot(thread_id: str) -> dict:
    """Get the current state values for a thread."""
    config = _get_thread_config(thread_id)
    try:
        snapshot = graph.get_state(config)
        return snapshot.values if snapshot.values else {}
    except Exception:
        return {}


def _determine_status(state: dict) -> str:
    """Determine the current consultation status."""
    if state.get("final_report"):
        return "completed"
    if state.get("waiting_for") == "physician":
        return "waiting_for_physician"
    if state.get("waiting_for") == "patient":
        return "waiting_for_patient"
    if state.get("diagnostic_summary"):
        return "diagnosis_complete"
    if state.get("question_count", 0) > 0:
        return "questioning"
    return "started"


# ── Endpoints ────────────────────────────────────────────────────────────

@app.post("/sessions/start", response_model=SessionResponse)
async def start_session():
    """Create a new consultation session (thread)."""
    thread_id = str(uuid.uuid4())
    return SessionResponse(
        thread_id=thread_id,
        message="Session créée. Utilisez /consultation/start pour démarrer.",
    )


@app.post("/consultation/start", response_model=ConsultationStateResponse)
async def start_consultation(req: StartConsultationRequest):
    """Start a consultation with a patient case description."""
    config = _get_thread_config(req.thread_id)

    initial_state = {
        "messages": [
            HumanMessage(content=f"Cas patient : {req.patient_case}")
        ],
        "patient_case": req.patient_case,
        "question_count": 0,
        "questions": [],
        "answers": [],
        "red_flags": [],
        "waiting_for": None,
    }

    try:
        # Run in executor to avoid blocking the uvicorn event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: graph.invoke(initial_state, config)
        )
    except Exception as e:
        logger.error("❌ /consultation/start ERREUR:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

    # Get the updated state
    state = _get_state_snapshot(req.thread_id)

    return ConsultationStateResponse(
        thread_id=req.thread_id,
        status=_determine_status(state),
        question_count=state.get("question_count", 0),
        current_question=state.get("current_question"),
        questions=state.get("questions", []),
        answers=state.get("answers", []),
        diagnostic_summary=state.get("diagnostic_summary"),
        interim_care=state.get("interim_care"),
        physician_treatment=state.get("physician_treatment"),
        final_report=state.get("final_report"),
        waiting_for=state.get("waiting_for"),
        red_flags=state.get("red_flags", []),
    )


@app.post("/consultation/resume", response_model=ConsultationStateResponse)
async def resume_consultation(req: ResumeConsultationRequest):
    """Resume a consultation after a patient answer or physician review."""
    config = _get_thread_config(req.thread_id)

    # Get current state to understand context
    current_state = _get_state_snapshot(req.thread_id)
    if not current_state:
        raise HTTPException(status_code=404, detail="Consultation non trouvée.")

    # Build the update based on input type
    if req.input_type == "patient":
        # Patient is answering a question
        questions = list(current_state.get("questions", []))
        answers = list(current_state.get("answers", []))
        answers.append(req.input)
        question_count = len(answers)

        update = {
            "messages": [HumanMessage(content=req.input)],
            "answers": answers,
            "question_count": question_count,
            "waiting_for": None,
        }
    elif req.input_type == "physician":
        # Physician is submitting their treatment
        update = {
            "messages": [
                HumanMessage(
                    content=f"Avis du médecin : {req.input}"
                )
            ],
            "physician_treatment": req.input,
            "waiting_for": None,
        }
    else:
        raise HTTPException(
            status_code=400,
            detail="input_type doit être 'patient' ou 'physician'.",
        )

    try:
        # Run in executor to avoid blocking the uvicorn event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: graph.update_state(config, update))
        result = await loop.run_in_executor(
            None, lambda: graph.invoke(None, config)
        )
    except Exception as e:
        logger.error("❌ /consultation/resume ERREUR:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

    # Get the updated state
    state = _get_state_snapshot(req.thread_id)

    return ConsultationStateResponse(
        thread_id=req.thread_id,
        status=_determine_status(state),
        question_count=state.get("question_count", 0),
        current_question=state.get("current_question"),
        questions=state.get("questions", []),
        answers=state.get("answers", []),
        diagnostic_summary=state.get("diagnostic_summary"),
        interim_care=state.get("interim_care"),
        physician_treatment=state.get("physician_treatment"),
        final_report=state.get("final_report"),
        waiting_for=state.get("waiting_for"),
        red_flags=state.get("red_flags", []),
    )


@app.get(
    "/consultation/{thread_id}",
    response_model=ConsultationStateResponse,
)
async def get_consultation(thread_id: str):
    """Get the current state of a consultation."""
    state = _get_state_snapshot(thread_id)
    if not state:
        raise HTTPException(status_code=404, detail="Consultation non trouvée.")

    return ConsultationStateResponse(
        thread_id=thread_id,
        status=_determine_status(state),
        question_count=state.get("question_count", 0),
        current_question=state.get("current_question"),
        questions=state.get("questions", []),
        answers=state.get("answers", []),
        diagnostic_summary=state.get("diagnostic_summary"),
        interim_care=state.get("interim_care"),
        physician_treatment=state.get("physician_treatment"),
        final_report=state.get("final_report"),
        waiting_for=state.get("waiting_for"),
        red_flags=state.get("red_flags", []),
    )


@app.get(
    "/consultation/{thread_id}/report",
    response_model=ReportResponse,
)
async def get_report(thread_id: str):
    """Get the final report for a completed consultation."""
    state = _get_state_snapshot(thread_id)
    if not state:
        raise HTTPException(status_code=404, detail="Consultation non trouvée.")

    final_report = state.get("final_report")
    if not final_report:
        raise HTTPException(
            status_code=400,
            detail="Le rapport final n'est pas encore disponible.",
        )

    return ReportResponse(
        thread_id=thread_id,
        final_report=final_report,
    )

"""
Shared state definition for the medical multi-agent graph.
All agents read from and write to this state.
"""

from typing import Annotated, Literal, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class MedicalState(TypedDict, total=False):
    # --- LangGraph message history ---
    messages: Annotated[list, add_messages]

    # --- Routing ---
    next: Literal[
        "diagnostic_agent",
        "physician_review",
        "report_agent",
        "FINISH",
    ]

    # --- Patient info ---
    patient_case: str

    # --- Diagnostic agent tracking ---
    question_count: int
    questions: list[str]
    answers: list[str]
    current_question: str

    # --- Clinical outputs ---
    interim_care: str
    diagnostic_summary: str
    medical_guidelines: str
    red_flags: list[str]

    # --- Physician review ---
    physician_treatment: str

    # --- Final report ---
    final_report: str

    # --- Flow control ---
    waiting_for: Optional[Literal["patient", "physician"]]

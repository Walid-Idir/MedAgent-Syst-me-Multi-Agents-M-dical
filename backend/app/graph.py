"""
LangGraph medical workflow graph.

Defines the multi-agent graph with:
- Supervisor (orchestrator)
- DiagnosticAgent (5 questions + synthesis)
- PhysicianReview (Human-in-the-Loop)
- ReportAgent (final report)

Interrupt points:
- diagnostic_agent: when waiting for patient answer
- physician_review: when waiting for physician input
"""

from dotenv import load_dotenv

load_dotenv()

from langgraph.graph import StateGraph, START, END

from app.state import MedicalState
from app.nodes.supervisor import supervisor_node
from app.nodes.diagnostic_agent import diagnostic_agent_node
from app.nodes.physician_review import physician_review_node
from app.nodes.report_agent import report_agent_node


def route_supervisor(state: MedicalState) -> str:
    """Route from supervisor to the next node based on state['next']."""
    next_step = state.get("next", "diagnostic_agent")
    if next_step == "FINISH":
        return END
    return next_step


def should_interrupt_diagnostic(state: MedicalState) -> bool:
    """Check if the diagnostic agent needs patient input."""
    return state.get("waiting_for") == "patient"


# ── Build the graph ──────────────────────────────────────────────────────

builder = StateGraph(MedicalState)

# Add nodes
builder.add_node("supervisor", supervisor_node)
builder.add_node("diagnostic_agent", diagnostic_agent_node)
builder.add_node("physician_review", physician_review_node)
builder.add_node("report_agent", report_agent_node)

# Entry point
builder.add_edge(START, "supervisor")

# Supervisor routes conditionally
builder.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {
        "diagnostic_agent": "diagnostic_agent",
        "physician_review": "physician_review",
        "report_agent": "report_agent",
        END: END,
    },
)

# All agents return to supervisor
builder.add_edge("diagnostic_agent", "supervisor")
builder.add_edge("physician_review", "supervisor")
builder.add_edge("report_agent", "supervisor")

import os

# ── Compile with interrupts ─────────────────────────────────────────────
# LangGraph Studio gere la persistance — ne pas fournir de checkpointer.
# En dehors de Studio (FastAPI), on utilise MemorySaver.

_in_studio = bool(os.getenv("LANGGRAPH_API"))

if _in_studio:
    graph = builder.compile(
        interrupt_after=["diagnostic_agent"],
        interrupt_before=["physician_review"],
    )
else:
    from langgraph.checkpoint.memory import MemorySaver
    graph = builder.compile(
        checkpointer=MemorySaver(),
        interrupt_after=["diagnostic_agent"],
        interrupt_before=["physician_review"],
    )

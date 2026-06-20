"""
Supervisor node – orchestrates the medical workflow.

The supervisor inspects the current state and decides which agent
should run next: diagnostic_agent, physician_review, report_agent,
or FINISH.
"""

from langchain_core.messages import SystemMessage, HumanMessage
from app.llm import get_llm
from app.state import MedicalState


SUPERVISOR_SYSTEM_PROMPT = """Tu es le superviseur d'un système d'orientation clinique.
Tu décides quelle étape suivante doit être exécutée dans le workflow médical.

Règles de routage :
1. Si le patient vient d'arriver (pas de questions posées), envoie vers "diagnostic_agent".
2. Si le diagnostic est en cours (question_count < 5), envoie vers "diagnostic_agent".
3. Si le patient a répondu aux 5 questions (question_count == 5) mais que la synthèse clinique (diagnostic_summary) n'est pas encore générée, envoie vers "diagnostic_agent".
4. Si la synthèse clinique (diagnostic_summary) est générée mais qu'il n'y a pas encore d'avis du médecin (physician_treatment est vide), envoie vers "physician_review".
5. Si le médecin a donné son avis (physician_treatment est renseigné) et qu'il n'y a pas de rapport final, envoie vers "report_agent".
6. Si le rapport final est généré, envoie vers "FINISH".

Réponds UNIQUEMENT avec un seul mot parmi : diagnostic_agent, physician_review, report_agent, FINISH
"""


def supervisor_node(state: MedicalState) -> dict:
    """Supervisor node that routes the workflow."""
    llm = get_llm()

    # Build context for decision
    context_parts = []
    context_parts.append(
        f"question_count: {state.get('question_count', 0)}"
    )
    context_parts.append(
        f"diagnostic_summary: {'oui' if state.get('diagnostic_summary') else 'non'}"
    )
    context_parts.append(
        f"physician_treatment: {'oui' if state.get('physician_treatment') else 'non'}"
    )
    context_parts.append(
        f"final_report: {'oui' if state.get('final_report') else 'non'}"
    )
    context_parts.append(
        f"waiting_for: {state.get('waiting_for', 'personne')}"
    )

    context = "\n".join(context_parts)

    if llm is None:
        # Fallback: deterministic routing without LLM
        return _deterministic_route(state)

    messages = [
        SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
        HumanMessage(content=f"État actuel du workflow :\n{context}"),
    ]

    response = llm.invoke(messages)
    next_step = response.content.strip().lower()

    # Validate the response
    valid_steps = {"diagnostic_agent", "physician_review", "report_agent", "finish"}
    if next_step not in valid_steps:
        # Fallback to deterministic routing
        return _deterministic_route(state)

    return {"next": next_step.upper() if next_step == "finish" else next_step}


def _deterministic_route(state: MedicalState) -> dict:
    """Fallback deterministic routing based on state."""
    question_count = state.get("question_count", 0)
    has_summary = bool(state.get("diagnostic_summary"))
    has_physician = bool(state.get("physician_treatment"))
    has_report = bool(state.get("final_report"))

    if has_report:
        return {"next": "FINISH"}
    elif has_physician:
        return {"next": "report_agent"}
    elif has_summary:
        return {"next": "physician_review"}
    elif question_count < 5:
        return {"next": "diagnostic_agent"}
    else:
        return {"next": "diagnostic_agent"}

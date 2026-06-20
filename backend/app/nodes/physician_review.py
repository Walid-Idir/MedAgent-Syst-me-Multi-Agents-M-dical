"""
Physician Review node – Human-in-the-Loop step.

This node presents the diagnostic summary and interim care recommendation
to the physician (human). The graph interrupts here to allow the physician
to review and submit their treatment plan.
"""

from langchain_core.messages import AIMessage
from app.state import MedicalState


def physician_review_node(state: MedicalState) -> dict:
    """Physician review node — processes the physician's input.

    When this node executes after an interrupt, the physician's treatment
    has already been injected into the state via the resume endpoint.
    """
    physician_treatment = state.get("physician_treatment", "")

    if physician_treatment:
        # Physician has submitted their review
        return {
            "waiting_for": None,
            "messages": [
                AIMessage(
                    content=(
                        f"👨‍⚕️ Revue du médecin traitant terminée.\n\n"
                        f"Traitement / Conduite à tenir :\n"
                        f"{physician_treatment}"
                    )
                )
            ],
        }
    else:
        # Waiting for physician input — this triggers the interrupt
        diagnostic_summary = state.get("diagnostic_summary", "Non disponible")
        interim_care = state.get("interim_care", "Non disponible")

        return {
            "waiting_for": "physician",
            "messages": [
                AIMessage(
                    content=(
                        f"⏸️ En attente de la revue du médecin traitant.\n\n"
                        f"📋 Synthèse clinique :\n{diagnostic_summary}\n\n"
                        f"💊 Recommandation intermédiaire :\n{interim_care}\n\n"
                        f"Le médecin doit fournir son traitement ou conduite à tenir."
                    )
                )
            ],
        }

"""
Patient interaction tools used by the Diagnostic Agent.

- ask_patient: generates and records a diagnostic question
- recommend_interim_care: produces a prudent interim care recommendation
"""

from langchain_core.tools import tool


@tool
def ask_patient(question: str) -> str:
    """Ask the patient a diagnostic question.

    Args:
        question: The clinical question to ask the patient.

    Returns:
        A confirmation that the question was recorded and is awaiting patient response.
    """
    return f"Question posée au patient : « {question} ». En attente de la réponse du patient."


@tool
def recommend_interim_care(
    symptoms: list[str],
    severity: str,
    red_flags: list[str],
) -> str:
    """Generate a prudent interim care recommendation based on symptoms.

    This recommendation is general, cautious, and does not replace
    a physician's advice.

    Args:
        symptoms: List of reported symptoms.
        severity: Overall severity assessment (mild / moderate / severe).
        red_flags: Any red flag symptoms detected.

    Returns:
        A structured interim care recommendation string.
    """
    base_advice = []

    # Always include basic advice
    base_advice.append("• Repos et limitation des efforts physiques.")
    base_advice.append("• Hydratation régulière (eau, tisanes).")
    base_advice.append("• Surveillance de l'évolution des symptômes.")

    if severity in ("moderate", "modérée"):
        base_advice.append("• Prise de température régulière.")
        base_advice.append(
            "• Consultation médicale recommandée dans les 24-48h."
        )
    elif severity in ("severe", "sévère"):
        base_advice.append("• ⚠️ Consultation médicale urgente recommandée.")
        base_advice.append(
            "• En cas d'aggravation rapide, appeler les urgences."
        )

    if red_flags:
        base_advice.append(
            f"• 🚩 Drapeaux rouges détectés : {', '.join(red_flags)}."
        )
        base_advice.append(
            "• Ces signes nécessitent une évaluation médicale rapide."
        )

    base_advice.append("")
    base_advice.append(
        "⚕️ Ce système ne remplace pas une consultation médicale."
    )

    return "\n".join(base_advice)

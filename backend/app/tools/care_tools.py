"""
Care-related tools for formatting clinical summaries.
"""

from langchain_core.tools import tool


@tool
def format_clinical_summary(
    patient_case: str,
    questions: list[str],
    answers: list[str],
    red_flags: list[str],
) -> str:
    """Format a structured clinical summary from patient data.

    Args:
        patient_case: Initial patient case description.
        questions: List of diagnostic questions asked.
        answers: List of patient answers.
        red_flags: Any detected red flag symptoms.

    Returns:
        A formatted clinical summary string.
    """
    lines = []
    lines.append("=" * 50)
    lines.append("SYNTHÈSE CLINIQUE PRÉLIMINAIRE")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"📋 Cas initial : {patient_case}")
    lines.append("")
    lines.append("📝 Questions et réponses :")

    for i, (q, a) in enumerate(zip(questions, answers), 1):
        lines.append(f"  Q{i}: {q}")
        lines.append(f"  R{i}: {a}")
        lines.append("")

    if red_flags:
        lines.append(f"🚩 Drapeaux rouges : {', '.join(red_flags)}")
    else:
        lines.append("✅ Aucun drapeau rouge détecté.")

    lines.append("")
    lines.append("=" * 50)

    return "\n".join(lines)

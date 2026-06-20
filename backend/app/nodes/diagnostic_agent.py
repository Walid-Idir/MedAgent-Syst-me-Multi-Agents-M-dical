"""
Diagnostic Agent node – collects patient information through 5 questions,
then produces a preliminary clinical synthesis with interim care recommendations.

Flow:
1. If question_count < 5 → generate next question → interrupt for patient answer
2. If question_count == 5 → produce diagnostic summary + interim care
"""

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.llm import get_llm
from app.state import MedicalState
from app.tools.patient_tools import ask_patient, recommend_interim_care
from app.tools.care_tools import format_clinical_summary
from app.tools.mcp_client import lookup_medical_guidelines


QUESTION_SYSTEM_PROMPT = """Tu es un agent de diagnostic clinique préliminaire.
Tu poses des questions au patient pour recueillir des informations cliniques.

Règles :
- Pose des questions pertinentes, claires et adaptées au cas initial.
- Adapte chaque question en fonction des réponses précédentes.
- Les questions doivent couvrir : symptômes principaux, durée, intensité, antécédents, facteurs aggravants.
- Sois empathique et professionnel.
- Pose UNE SEULE question à la fois.
- Réponds UNIQUEMENT avec la question, sans introduction ni explication.

Tu es à la question numéro {q_num}/5.
"""

SUMMARY_SYSTEM_PROMPT = """Tu es un agent de diagnostic clinique préliminaire.
À partir des informations recueillies, produis une synthèse clinique préliminaire.

La synthèse doit inclure :
1. Un résumé du cas
2. Les symptômes principaux identifiés
3. Les facteurs de risque ou drapeaux rouges éventuels
4. Une orientation clinique préliminaire (PAS un diagnostic définitif)
5. Le niveau de sévérité estimé (léger / modéré / sévère)

IMPORTANT : Ce système ne remplace pas une consultation médicale.
Utilise des termes comme "orientation clinique préliminaire" et "synthèse clinique".

Réponds en format structuré.
"""


def diagnostic_agent_node(state: MedicalState) -> dict:
    """Diagnostic agent: asks questions or produces summary."""
    question_count = state.get("question_count", 0)
    questions = list(state.get("questions", []))
    answers = list(state.get("answers", []))
    patient_case = state.get("patient_case", "")

    if question_count < 5:
        return _ask_next_question(
            state, question_count, questions, answers, patient_case
        )
    else:
        return _produce_summary(
            state, questions, answers, patient_case
        )


def _ask_next_question(
    state: MedicalState,
    question_count: int,
    questions: list[str],
    answers: list[str],
    patient_case: str,
) -> dict:
    """Generate the next diagnostic question using the LLM."""
    llm = get_llm()

    q_num = question_count + 1

    # Build conversation context
    context_parts = [f"Cas initial du patient : {patient_case}"]
    for i, (q, a) in enumerate(zip(questions, answers), 1):
        context_parts.append(f"Q{i}: {q}")
        context_parts.append(f"R{i}: {a}")

    context = "\n".join(context_parts)

    if llm is None:
        # Fallback questions if no LLM
        fallback_questions = [
            "Quels sont vos symptômes principaux ?",
            "Depuis combien de temps ressentez-vous ces symptômes ?",
            "Sur une échelle de 1 à 10, quelle est l'intensité de vos symptômes ?",
            "Avez-vous des antécédents médicaux ou des allergies ?",
            "Y a-t-il des facteurs qui aggravent ou améliorent vos symptômes ?",
        ]
        question = fallback_questions[question_count]
    else:
        messages = [
            SystemMessage(
                content=QUESTION_SYSTEM_PROMPT.format(q_num=q_num)
            ),
            HumanMessage(content=context),
        ]
        response = llm.invoke(messages)
        question = response.content.strip()

    # Call the ask_patient tool (for traceability)
    ask_patient.invoke({"question": question})

    # Update state — mark as waiting for patient
    new_questions = questions + [question]

    return {
        "question_count": question_count,  # Don't increment yet — wait for answer
        "questions": new_questions,
        "current_question": question,
        "waiting_for": "patient",
        "messages": [
            AIMessage(
                content=f"Question {q_num}/5 : {question}"
            )
        ],
    }


def _produce_summary(
    state: MedicalState,
    questions: list[str],
    answers: list[str],
    patient_case: str,
) -> dict:
    """Produce the diagnostic summary after 5 questions."""
    llm = get_llm()

    # Build full context
    context_parts = [f"Cas initial : {patient_case}", ""]
    for i, (q, a) in enumerate(zip(questions, answers), 1):
        context_parts.append(f"Q{i}: {q}")
        context_parts.append(f"R{i}: {a}")
        context_parts.append("")

    context = "\n".join(context_parts)

    # Format clinical summary via tool
    clinical_summary = format_clinical_summary.invoke({
        "patient_case": patient_case,
        "questions": questions,
        "answers": answers,
        "red_flags": state.get("red_flags", []),
    })

    # Try to get MCP medical guidelines
    symptoms = _extract_symptoms(patient_case, answers)
    guidelines = lookup_medical_guidelines.invoke({"symptoms": symptoms})

    # Generate diagnostic summary with LLM
    if llm is not None:
        messages = [
            SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"{context}\n\n"
                    f"Résumé clinique formaté :\n{clinical_summary}\n\n"
                    f"Recommandations médicales (MCP) :\n{guidelines}"
                )
            ),
        ]
        response = llm.invoke(messages)
        diagnostic_summary = response.content.strip()
    else:
        diagnostic_summary = clinical_summary

    # Detect red flags
    red_flags = _detect_red_flags(patient_case, answers)

    # Determine severity
    severity = "sévère" if red_flags else "léger"

    # Generate interim care recommendation
    interim_care = recommend_interim_care.invoke({
        "symptoms": symptoms,
        "severity": severity,
        "red_flags": red_flags,
    })

    return {
        "diagnostic_summary": diagnostic_summary,
        "interim_care": interim_care,
        "medical_guidelines": guidelines,
        "red_flags": red_flags,
        "waiting_for": None,
        "messages": [
            AIMessage(
                content=(
                    f"📋 Synthèse clinique préliminaire établie.\n\n"
                    f"{diagnostic_summary}\n\n"
                    f"💊 Recommandation intermédiaire :\n{interim_care}"
                )
            )
        ],
    }


def _extract_symptoms(patient_case: str, answers: list[str]) -> list[str]:
    """Extract symptom keywords from patient case and answers."""
    symptom_keywords = [
        "fièvre", "toux", "maux de tête", "douleur", "fatigue",
        "nausée", "vomissement", "diarrhée", "essoufflement",
        "vertige", "frisson", "courbature", "mal de gorge",
        "congestion", "éruption", "douleur thoracique",
        "palpitation", "insomnie", "anxiété",
    ]
    text = f"{patient_case} {' '.join(answers)}".lower()
    return [s for s in symptom_keywords if s in text] or ["symptômes généraux"]


def _detect_red_flags(patient_case: str, answers: list[str]) -> list[str]:
    """Detect red flag symptoms from patient data."""
    red_flag_patterns = {
        "douleur thoracique": "Douleur thoracique",
        "douleur poitrine": "Douleur thoracique",
        "difficulté à respirer": "Détresse respiratoire",
        "essoufflement sévère": "Détresse respiratoire",
        "perte de conscience": "Perte de conscience",
        "évanouissement": "Perte de conscience",
        "fièvre très élevée": "Fièvre élevée (>39°C)",
        "39": "Fièvre élevée possible",
        "40": "Fièvre très élevée",
        "sang": "Présence de sang",
        "paralysie": "Déficit neurologique",
        "confusion": "Confusion mentale",
        "convulsion": "Convulsions",
    }
    text = f"{patient_case} {' '.join(answers)}".lower()
    flags = []
    for pattern, flag in red_flag_patterns.items():
        if pattern in text and flag not in flags:
            flags.append(flag)
    return flags

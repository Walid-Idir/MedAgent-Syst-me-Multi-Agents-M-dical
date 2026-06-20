"""
Report Agent node – generates the structured final medical report.

Combines all collected data (patient case, Q&A, diagnostic summary,
interim care, physician treatment) into a comprehensive final report.
"""

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.llm import get_llm
from app.state import MedicalState


REPORT_SYSTEM_PROMPT = """Tu es un agent de rédaction de rapports médicaux.
Tu génères un rapport final structuré à partir de toutes les informations recueillies
durant la consultation.

Le rapport doit suivre ce format :

# RAPPORT DE CONSULTATION – ORIENTATION CLINIQUE

## 1. Informations du patient
- Cas initial présenté

## 2. Anamnèse (Questions & Réponses)
- Les 5 questions posées et les réponses du patient

## 3. Synthèse clinique préliminaire
- L'analyse clinique de l'agent de diagnostic

## 4. Drapeaux rouges identifiés
- Liste des drapeaux rouges, ou "Aucun"

## 5. Recommandation intermédiaire
- Les soins intermédiaires recommandés

## 6. Avis du médecin traitant
- Le traitement ou la conduite à tenir proposé par le médecin

## 7. Conclusion
- Synthèse finale avec les prochaines étapes recommandées

---

⚕️ AVERTISSEMENT : Ce système ne remplace pas une consultation médicale.
Ce rapport est une orientation clinique préliminaire à des fins académiques uniquement.

---

Rédige le rapport de manière professionnelle, claire et structurée.
"""


def report_agent_node(state: MedicalState) -> dict:
    """Generate the structured final medical report."""
    llm = get_llm()

    patient_case = state.get("patient_case", "Non renseigné")
    questions = state.get("questions", [])
    answers = state.get("answers", [])
    diagnostic_summary = state.get("diagnostic_summary", "Non disponible")
    interim_care = state.get("interim_care", "Non disponible")
    physician_treatment = state.get("physician_treatment", "Non disponible")
    red_flags = state.get("red_flags", [])

    # Build comprehensive context
    qa_section = ""
    for i, (q, a) in enumerate(zip(questions, answers), 1):
        qa_section += f"Q{i}: {q}\nR{i}: {a}\n\n"

    context = f"""
Cas initial du patient :
{patient_case}

Questions et réponses :
{qa_section}

Synthèse clinique préliminaire :
{diagnostic_summary}

Drapeaux rouges :
{', '.join(red_flags) if red_flags else 'Aucun'}

Recommandation intermédiaire :
{interim_care}

Avis du médecin traitant :
{physician_treatment}
"""

    if llm is not None:
        messages = [
            SystemMessage(content=REPORT_SYSTEM_PROMPT),
            HumanMessage(content=context),
        ]
        response = llm.invoke(messages)
        final_report = response.content.strip()
    else:
        # Fallback: manual report construction
        final_report = _build_fallback_report(
            patient_case, questions, answers,
            diagnostic_summary, red_flags,
            interim_care, physician_treatment,
        )

    return {
        "final_report": final_report,
        "waiting_for": None,
        "messages": [
            AIMessage(
                content=f"📄 Rapport final généré.\n\n{final_report}"
            )
        ],
    }


def _build_fallback_report(
    patient_case: str,
    questions: list[str],
    answers: list[str],
    diagnostic_summary: str,
    red_flags: list[str],
    interim_care: str,
    physician_treatment: str,
) -> str:
    """Build a structured report without LLM."""
    lines = []
    lines.append("# RAPPORT DE CONSULTATION – ORIENTATION CLINIQUE")
    lines.append("")
    lines.append("## 1. Informations du patient")
    lines.append(f"Cas initial : {patient_case}")
    lines.append("")
    lines.append("## 2. Anamnèse (Questions & Réponses)")
    for i, (q, a) in enumerate(zip(questions, answers), 1):
        lines.append(f"**Q{i}**: {q}")
        lines.append(f"**R{i}**: {a}")
        lines.append("")
    lines.append("## 3. Synthèse clinique préliminaire")
    lines.append(diagnostic_summary)
    lines.append("")
    lines.append("## 4. Drapeaux rouges identifiés")
    if red_flags:
        for flag in red_flags:
            lines.append(f"- 🚩 {flag}")
    else:
        lines.append("✅ Aucun drapeau rouge détecté.")
    lines.append("")
    lines.append("## 5. Recommandation intermédiaire")
    lines.append(interim_care)
    lines.append("")
    lines.append("## 6. Avis du médecin traitant")
    lines.append(physician_treatment)
    lines.append("")
    lines.append("## 7. Conclusion")
    lines.append(
        "Ce rapport constitue une orientation clinique préliminaire. "
        "Le patient est invité à consulter un professionnel de santé "
        "pour un suivi personnalisé."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "⚕️ **AVERTISSEMENT** : Ce système ne remplace pas une "
        "consultation médicale. Ce rapport est une orientation clinique "
        "préliminaire à des fins académiques uniquement."
    )
    return "\n".join(lines)

# Rapport technique (court)

## Objectif
Systeme multi-agents medical base sur LangGraph, avec boucle questions patient, revue medecin, et rapport final.

## Architecture
- Backend FastAPI + LangGraph pour le workflow multi-agents
- MCP local pour l'outil `check_red_flags`
- Frontend React pour 4 ecrans (cas initial, questions, revue medecin, rapport)

## Points cles
- Etat partage via `MedicalState`
- Human-in-the-loop via interruption dans le noeud `physician_review`
- Outil MCP appelle depuis `diagnostic_agent` pour detecter des red flags

## Limites
- Pas de persistance en base (memoire uniquement)
- LLM optionnel (fallback heuristique si `OPENAI_API_KEY` absent)

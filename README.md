# Projet Multi Agents - Diagnostic Medical (LangGraph)

## Objectif
Application multi-agents simulant un workflow d'orientation clinique preliminaire. Le systeme ne fournit pas de diagnostic definitif.

## Structure
- `backend/` FastAPI + LangGraph
- `mcp_server/` MCP server avec tool `check_red_flags`
- `frontend/` React

## Prerequis
- Python 3.10+
- Node.js 18+

## Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# ajouter votre OPENAI_API_KEY dans .env
uvicorn app.api:app --reload --port 8000
```

## MCP Server

```bash
cd mcp_server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python server.py
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

## API Endpoints
- `POST /sessions/start`
- `POST /consultation/start`
- `POST /consultation/resume`
- `GET /consultation/{thread_id}`
- `GET /consultation/{thread_id}/report`

## LangGraph Studio
Dans `backend/`, utilisez `langgraph.json` avec le graphe `medical`.

## Disclaimer
Ce systeme ne remplace pas une consultation medicale.

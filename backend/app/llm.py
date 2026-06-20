import os
import urllib.request
from langchain_openai import ChatOpenAI

# Singleton — resolved once at server startup, reused for every node call.
_llm_instance = None
_llm_resolved = False


def _is_server_reachable(url: str, timeout: int = 2) -> bool:
    """Check if a URL is reachable (HEAD request)."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        urllib.request.urlopen(req, timeout=timeout)
        return True
    except Exception:
        return False


def get_llm():
    """Return a shared LLM instance, or None if no LLM is available/reachable.

    Resolution order:
      1. Ollama (if OLLAMA_API_KEY is set and server is reachable)
      2. OpenAI (if OPENAI_API_KEY is set)
      3. None  → fallback hardcoded responses
    """
    global _llm_instance, _llm_resolved

    if _llm_resolved:
        return _llm_instance

    # --- Ollama ---
    ollama_api_key = os.getenv("OLLAMA_API_KEY")
    if ollama_api_key:
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        if _is_server_reachable(base_url):
            _llm_instance = ChatOpenAI(
                api_key=ollama_api_key,
                base_url=base_url,
                model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
                temperature=0.2,
            )
            _llm_resolved = True
            return _llm_instance
        # Ollama configured but unreachable — fall through to None
        print("[LLM] AVERTISSEMENT: OLLAMA_API_KEY defini mais serveur inaccessible -- mode fallback actif.")
        _llm_instance = None
        _llm_resolved = True
        return None

    # --- OpenAI ---
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        _llm_instance = ChatOpenAI(
            api_key=openai_api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.2,
        )
        _llm_resolved = True
        return _llm_instance

    # --- No LLM configured ---
    print("[LLM] INFO: Aucun LLM configure -- mode fallback (questions predefinies).")
    _llm_instance = None
    _llm_resolved = True
    return None

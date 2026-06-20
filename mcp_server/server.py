"""
MCP Server – Medical Guidelines Lookup.

Exposes a `lookup_guidelines` tool that searches a local JSON database
of simplified medical guidelines for symptoms matching the query.

Runs via stdio transport for use with the MCP client.
"""

import json
import os
from mcp.server.fastmcp import FastMCP

# Create MCP server
mcp = FastMCP(
    name="medical-guidelines",
)

# Load guidelines database
DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "medical_guidelines.json")


def _load_guidelines() -> list[dict]:
    """Load the medical guidelines from JSON file."""
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


@mcp.tool()
def lookup_guidelines(symptoms: list[str]) -> str:
    """Look up medical guidelines for given symptoms.

    Searches the medical guidelines database and returns relevant
    clinical guidance for the reported symptoms.

    Args:
        symptoms: List of symptom keywords to search for.

    Returns:
        Formatted medical guidelines for matching symptoms.
    """
    guidelines = _load_guidelines()
    if not guidelines:
        return "⚠️ Base de données des recommandations médicales indisponible."

    matches = []
    symptoms_lower = [s.lower().strip() for s in symptoms]

    for entry in guidelines:
        entry_symptom = entry.get("symptom", "").lower()
        entry_keywords = [k.lower() for k in entry.get("keywords", [])]

        for symptom in symptoms_lower:
            if (
                symptom in entry_symptom
                or entry_symptom in symptom
                or any(symptom in kw or kw in symptom for kw in entry_keywords)
            ):
                matches.append(entry)
                break

    if not matches:
        return (
            "Aucune recommandation spécifique trouvée pour les symptômes : "
            f"{', '.join(symptoms)}.\n"
            "Recommandation générale : consulter un professionnel de santé."
        )

    result_lines = [
        "📚 RECOMMANDATIONS MÉDICALES (base de connaissances)",
        "=" * 50,
        "",
    ]

    for entry in matches:
        result_lines.append(f"🔹 {entry.get('symptom', 'N/A')}")
        result_lines.append(
            f"   Sévérité possible : {entry.get('severity_indicators', 'N/A')}"
        )
        result_lines.append(
            f"   Conseil général : {entry.get('general_advice', 'N/A')}"
        )
        if entry.get("red_flags"):
            result_lines.append(
                f"   🚩 Drapeaux rouges : {', '.join(entry['red_flags'])}"
            )
        result_lines.append(
            f"   Action recommandée : {entry.get('recommended_action', 'N/A')}"
        )
        result_lines.append("")

    result_lines.append(
        "⚕️ Ces recommandations sont générales et ne remplacent pas "
        "une consultation médicale."
    )

    return "\n".join(result_lines)


if __name__ == "__main__":
    mcp.run(transport="stdio")

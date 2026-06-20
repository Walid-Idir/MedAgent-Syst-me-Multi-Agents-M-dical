"""
MCP client tool – connects to the MCP server via stdio transport
to look up medical guidelines matching patient symptoms.
"""

import asyncio
import json
import os
import sys
from langchain_core.tools import tool

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# Path to the MCP server script
_MCP_SERVER_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "mcp_server", "server.py"
)


async def _call_mcp_lookup(symptoms: list[str]) -> str:
    """Internal async function to call the MCP server."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[os.path.abspath(_MCP_SERVER_PATH)],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "lookup_guidelines",
                arguments={"symptoms": symptoms},
            )

            # Extract text content from the result
            if result.content:
                return result.content[0].text
            return "Aucune recommandation trouvée."


@tool
def lookup_medical_guidelines(symptoms: list[str]) -> str:
    """Look up medical guidelines for given symptoms via MCP server.

    Connects to the MCP medical guidelines server and retrieves
    relevant clinical guidelines for the reported symptoms.

    Args:
        symptoms: List of patient symptoms to look up.

    Returns:
        Medical guidelines and recommendations for the symptoms.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(
                    asyncio.run, _call_mcp_lookup(symptoms)
                ).result(timeout=30)
            return result
        else:
            return asyncio.run(_call_mcp_lookup(symptoms))
    except Exception as e:
        return (
            f"⚠️ Impossible de contacter le serveur MCP : {e}. "
            f"Les recommandations seront basées sur l'analyse interne."
        )

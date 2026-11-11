"""Exercise discovery and a real MCP call against the local stdio process."""

from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]
SERVER = StdioServerParameters(
    command=sys.executable,
    args=["-m", "agent_runtime.mcp_server"],
    cwd=ROOT,
)
EXPECTED_NAMES = {'validation.verifyClaim', 'validation.auditSearchResults'}
PAYLOAD = {'contractVersion': '1.0.0',
 'claim': 'Synthetic record contains code A-17.',
 'dataType': 'authorized_system_record',
 'context': 'Public synthetic fixture.',
 'candidateReferences': [],
 'userFilters': []}


async def discover_and_call():
    async with Client(SERVER) as client:
        listing = await client.list_tools()
        names = {item.name for item in listing.tools}
        tools = {item.name: item for item in listing.tools}
        result = await client.call_tool("validation.verifyClaim", PAYLOAD)
        return names, tools, result


class McpTransportTests(unittest.TestCase):
    def test_real_client_discovers_contract_tools_and_calls_domain_operation(self):
        names, tools, result = asyncio.run(discover_and_call())
        self.assertSetEqual(names, EXPECTED_NAMES)
        self.assertEqual(tools["validation.verifyClaim"].input_schema["$id"], "https://sofiee-agent-validation.local/contracts/v1/verify-claim.input.schema.json")
        self.assertIsInstance(result.structured_content, dict)
        self.assertEqual(result.structured_content.get("contractVersion"), "1.0.0")
        self.assertFalse(result.is_error)
        self.assertEqual(result.structured_content.get("contractVersion"), "1.0.0")


if __name__ == "__main__":
    unittest.main()

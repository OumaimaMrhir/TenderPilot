import pytest

from tenderpilot import mcp_server


@pytest.mark.anyio
async def test_mcp_server_exposes_tools():
    names = {tool.name for tool in await mcp_server.server.list_tools()}
    assert {"compliance_matrix", "draft_response"} <= names


def test_compliance_matrix_tool(document):
    result = mcp_server.compliance_matrix(document)
    assert len(result["matrix"]) == 15
    assert result["decision"] == "validation humaine requise"


@pytest.fixture
def anyio_backend():
    return "asyncio"

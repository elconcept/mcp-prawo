from prawo_pl_mcp import __version__
from prawo_pl_mcp.server import mcp


def test_mcp_server_info_uses_application_version():
    assert mcp.version == __version__
    assert mcp.version != '3.4.11'

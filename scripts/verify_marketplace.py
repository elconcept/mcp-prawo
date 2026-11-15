#!/usr/bin/env python3
from pathlib import Path
import json
import tomllib
root=Path(__file__).resolve().parents[1]
def read(p): return json.loads((root/p).read_text(encoding="utf-8"))
a=read(".agents/plugins/marketplace.json")
c=read(".claude-plugin/marketplace.json")
p=read("plugins/mcp-prawo/plugin.json")
o=read("plugins/mcp-prawo/.codex-plugin/plugin.json")
cl=read("plugins/mcp-prawo/.claude-plugin/plugin.json")
v=tomllib.loads((root/"pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
assert p["version"]==o["version"]==cl["version"]==v
assert a["plugins"][0]["name"]==p["name"]==o["name"]==cl["name"]==c["plugins"][0]["name"]=="mcp-prawo"
assert a["plugins"][0]["source"]["path"]==c["plugins"][0]["source"]=="./plugins/mcp-prawo"
assert (root/"plugins/mcp-prawo/skills/prawo-pl-mcp/SKILL.md").exists()
assert len(list((root/"plugins/mcp-prawo/skills").glob("*/SKILL.md")))==1
assert not any((root/"plugins/mcp-prawo"/name).exists() for name in (".mcp.json","mcp.json","hooks"))
assert "mcpServers" not in p and "requires_local_executor" not in p
print("PASS: ChatGPT/Codex and Claude plugin marketplaces, version, skill-only packaging")

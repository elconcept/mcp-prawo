# MCP Prawo jako marketplace

Repozytorium GitHub: https://github.com/elconcept/mcp-prawo (branch `main`).

- **ChatGPT web**: import GitHub marketplace using repository URL, leave subdirectory/path empty, select `main`, enable plugin `mcp-prawo`. Requires a workspace with GitHub marketplace import support.
- **Codex CLI**: `codex plugin marketplace add elconcept/mcp-prawo --ref main`, then `codex plugin add mcp-prawo@elconcept-mcp-prawo`.
- **Claude Code**: `claude plugin marketplace add elconcept/mcp-prawo`, then `claude plugin install mcp-prawo@elconcept-mcp-prawo`.
- **Remote MCP**: connect `https://mcp-prawo.xlap.pl/mcp` separately and complete Cloudflare Access authentication. The plugin skill alone does **not** provision OAuth, an MCP server connection or tools.

Marketplace manifests: `.agents/plugins/marketplace.json` for Codex/ChatGPT; `.claude-plugin/marketplace.json` for Claude Code; `plugins/mcp-prawo/plugin.json` as the portable OpenAI manifest; plus `.codex-plugin/plugin.json` and `.claude-plugin/plugin.json` per client.

No local MCP, Python runtime, hooks or secrets are shipped with the plugin. The main MCP service remains a Docker deployment and Python package independently of the plugin.

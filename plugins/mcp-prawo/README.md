# MCP Prawo — plugin ChatGPT/Codex i Claude Code

Pakiet zawiera jeden skill `prawo-pl-mcp`, kompatybilny z ChatGPT web i CLI. Nie pakuje lokalnego wykonawcy, hooków ani poświadczeń. Zdalny serwer `https://mcp-prawo.xlap.pl/mcp` jest podłączany **osobno**, z własnym uwierzytelnianiem Cloudflare Access.

Sama instalacja pluginu nie uwierzytelnia MCP i nie dodaje automatycznie narzędzi do konta.

W Claude Code plugin instaluje się z marketplace `elconcept/mcp-prawo`, a w Codex z `mcp-prawo@elconcept-mcp-prawo`. W ChatGPT importuj repozytorium jako marketplace i aktywuj plugin `mcp-prawo`.

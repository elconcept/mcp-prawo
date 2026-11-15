# Audyt repozytorium i marketplace MCP Prawo — 2026-11-15

## Identyfikacja i ciągłość

- Produkcyjny kontener NAS: `mcp-prawo`, obraz `mcp-prawo:0.3.0`, podczas kontroli: running/healthy.
- Katalog źródłowy NAS: `/volume2/docker/mcp-prawo`; origin: `git@github.com:elconcept/mcp-prawo.git`.
- Repozytorium publiczne zostało przemianowane z `elconcept/mcp-prawo-wrapper` na `elconcept/mcp-prawo`, z zachowaniem historii.
- Na koniec porządkowania pozostał wyłącznie `main`; pięć odgałęzień GitHub usunięto po zachowaniu ich historii w `main`. Lokalna przestarzała gałąź została usunięta; nie ma dodatkowych worktree.

## Podstawa decyzji o scalaniu

- Gałąź `audit/upstream-preservation-20261108`: po rozwiązaniu konfliktu `.gitignore` przejęto dokumentację i zachowano nowsze reguły ochrony sekretów.
- `grounding-prawo-saos-nsa-ustawy`: zwykłe scalenie z preferencją bieżących zmian na konfliktach, bez regresji.
- `fix/upstream-native-pagination-20261031`: próba połączenia kodu i testów wprowadzała trzy błędy wobec aktualnego kontraktu `pl_get_document`. Zachowano historię przez merge `-s ours`; starszy dokument audytowy pozostał w repozytorium.
- `feat/semantic-first-case-law-federation`: próbne scalenie wprowadzało siedem niespójności z aktualnymi pięcioma narzędziami (w tym nieistniejące dziś `pl_find` i `pl_get_by_ref`). Zachowano historię merge `-s ours`, a ADR przeniesiono do docs.
- `feat/minimalny-resolver-repertorium-20261031`: stary lokalny resolver, duplikujący obecne osobne źródła; historię zachowano przez merge `-s ours`, bez przywracania wycofanej implementacji.
- PR #4 (z gałęzi lokalnego resolvera do gałęzi natywnej paginacji) zamknięto przez formalny merge, po czym jego historię dołączono do `main` również bez zmiany kodu produkcyjnego.

Uwaga: `merge -s ours` włącza historię gałęzi do `main`, ale NIE przenosi jej zmian do działającego kodu. Wynika to z regresji kontraktu API oraz nowszej architektury serwera.

## Marketplace i poświadczenia

- Dodano `.agents/plugins/marketplace.json` (ChatGPT/Codex) oraz `.claude-plugin/marketplace.json` (Claude Code).
- Plugin `plugins/mcp-prawo` wersji 0.3.0 zawiera jeden skill `prawo-pl-mcp`, bez MCP lokalnego, hooków i poświadczeń.
- Potwierdzono import marketplace oraz instalację i stan enabled w Codex CLI i Claude Code (test izolowany, następnie rzeczywisty profil użytkownika).
- Import do chatgpt.com przez panel workspace nie został wykonany; obecność na GitHub i poprawna instalacja CLI nie dowodzą automatycznego importu do ChatGPT web.
- Cloudflare Access: dopuszczono dokładny dashboard OAuth callback dla `mcp-prawo` przy zachowaniu polityk `laptopshop.pl` i `ANY service token`. Odrzucenie redirect URI ustąpiło (HTTP 302 do logowania), ale sesja administratora nadal wymaga interaktywnego uwierzytelnienia.

## Testy serwera i pozostałe kwestie

- Lokalny test repo: 86 testów pytest PASS; skonfigurowano odrębne CI dla marketplace.
- Lokalny Streamable HTTP origin Synology: `initialize`, `tools/list` i `tools/call(pl_list_sources)` PASS — 5 narzędzi i 13 źródeł.
- W kodzie serwera FastMCP jawnie ustawiono `version=__version__`, aby `serverInfo` nie podawało wersji biblioteki zamiast aplikacji; uruchomiona wcześniej zbudowana wersja kontenera wymaga ponownego build/redeploy dla tej zmiany. Nie przebudowano jej w ramach audytu.
- `server.json` deklaruje publikowaną w PyPI wersję 0.2.4; PyPI w czasie audytu również wskazywało 0.2.4. Lokalny kod i plugin w repo to 0.3.0. Nie zmieniono wersji publikacji bez wydania nowego pakietu.
- Uporządkowano metadane pyproject i dodano reguły ignorowania `.env`, prywatnych kluczy i tokenów w publicznym repozytorium.
- Nie przeprowadzono pełnego end-to-end wszystkich 13 zdalnych źródeł ani uwierzytelnionego `tools/list` przez zewnętrzną bramę Cloudflare; wnioski o pełnej dostępności tych zależności nie są z tego powodu stawiane.

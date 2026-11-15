---
name: prawo-pl-mcp
description: "Stosuj przy pracy ze źródłami polskiego i unijnego prawa przez serwer MCP mcp-prawo: wyszukiwanie ustaw, orzeczeń, interpretacji i ich pełnych treści. Nie uruchamiaj automatycznie dla zadań niezwiązanych z prawem."
---

# MCP Prawo — praca ze źródłami

Używaj **wyłącznie dostępnego, już uwierzytelnionego** zdalnego serwera MCP `mcp-prawo`. Ten plugin dostarcza instrukcje, ale nie instaluje serwera, nie wykonuje poleceń lokalnych i nie zawiera sekretów. Gdy MCP nie jest podłączony, wyraźnie to zaznacz; nie deklaruj, że sprawdzono jego narzędzia.

1. **Katalog**: `pl_list_sources` — odczytaj obsługiwane źródła, możliwości, ograniczenia i natywne parametry; dla szczegółów użyj `source_id`.
2. **Wyszukiwanie**: `pl_search` — domyślnie Repertorium jako indeks wyszukiwania, osobne źródła na żądanie. Zachowaj identyfikatory, odnośniki i oryginalne fragmenty.
3. **Pełna treść**: `pl_get_document` — pobierz zidentyfikowany dokument. Dla wyniku z `md_file` wybierz `source="md"`, paginuj oraz kontroluj SHA-256. Nie przedstawiaj statusu `fragment_only` jako pełnego orzeczenia.
4. **Narzędzia specjalistyczne**: `pl_call` — po wcześniejszym odczycie schematu natywnego narzędzia. Nie zgaduj argumentów ani sygnatur.
5. **Zakres źródeł**: `pl_coverage` — ustal, co jest pokryte, co nie i jakie są dopuszczalne ścieżki zastępcze.

W odpowiedzi oddziel literalną treść źródła, metadane, interpretację i stan weryfikacji. Nie wymyślaj orzeczeń, linków ani brakujących części tekstu. Przepisy i daty sprawdzaj w źródłach aktualnych dla analizowanego stanu prawnego. Nie utożsamiaj samego wyniku Repertorium z dowodem istnienia zweryfikowanego pełnego tekstu.

# Audyt produkcyjny MCP Prawo — 15 listopada 2026

## Ocena końcowa

**PASS w zakresie 15 lokalnych, aktywnych serwerów prawnych i 5 narzędzi wrappera.** Po korektach `mcp-prawo` działa na Synology z obrazem `mcp-prawo:0.3.1` (running/healthy), a Cloudflare Access raportuje `ready` i `connected`. W produkcji włączono 15 źródeł, a niezależnie opisano 16. adapter — zewnętrzny PrawMi — wymagający własnego uwierzytelnienia.

Zbadano całą ścieżkę: lokalny NAS, Docker i Portainer (stack 68), HTTP MCP, Cloudflare Access, rejestr Python, faktyczne `initialize` i `tools/list` upstream oraz reprezentatywne `tools/call` przez produkcyjny wrapper.

### Kryteria weryfikacji

- **Dostępność:** produkcyjne `pl_list_sources(source_id=...)` doprowadziło do natywnego `tools/list` każdego źródła.
- **Zgodność rejestru:** wszystkie 48 nazw natywnych narzędzi z 15 aktywnych źródeł odpowiada rzeczywistym schematom; brak brakujących i zbędnych nazw.
- **Funkcjonalność:** przynajmniej jedna realna operacja odczytu dla każdego z 15 źródeł przez produkcyjny `mcp-prawo`. Wszystkie 15 otrzymały poprawną odpowiedź.
- **Nie oznacza to** osobnego uruchomienia każdego z 48 narzędzi natywnych, weryfikacji każdej historii prawnej ani pełności i aktualności wszystkich baz.
- **Cloudflare:** `mcp-prawo` otrzymuje pięć narzędzi (`pl_coverage`, `pl_list_sources`, `pl_get_document`, `pl_call`, `pl_search`) i stan `ready/connected`. Pomyślny `tools/list` w Portainer/NAS nie jest sam w sobie dowodem poprawności każdej sesji klienta w ChatGPT.

## Macierz 15 aktywnych źródeł

| Źródło | Natywnych narzędzi | Rodzaj wyszukiwania i pobierania | Produkcyjny test odczytu | Wynik |
|---|---:|---|---|---|
| `saos` | 4 | Frazy, sygnatura, pełne orzeczenie po ID, cytator | `pl_search(odszkodowanie)` → 113018 trafień deklarowanych przez bazę | PASS |
| `nsa` | 3 | Fraza/sygnatura WSA/NSA, tekst po doc_id | `pl_search(podatek)` → 756580 trafień deklarowanych | PASS |
| `legal-cite` | 2 | Wykaz aktów i konkretny artykuł, bez wolnotekstowego `search` | `pl_call(list_acts)` → wykaz kodów | PASS |
| `krs` | 3 | Dokładny numer KRS, odpis oraz reprezentacja | `pl_get_document(0000028860)` → dane ORLEN S.A. | PASS |
| `kio` | 6 | Fraza, sygnatura, przepisy PZP, PDF, pokrycie | `pl_search(zamówienia publiczne)` → wyniki KIO | PASS |
| `uodo` | 3 | Decyzje UODO, wyszukiwanie i tekst decyzji | `pl_search(naruszenie danych)` → 10 wyników | PASS |
| `eu-sparql` | 5 | CELEX, ECLI, data, CJEU, GDPRhub | `search_by_celex(32016R0679)` → GDPR | PASS |
| `eureka` | 4 | Interpretacje podatkowe, sygnatury, kategorie | `pl_search(VAT)` → wyniki | PASS z ostrzeżeniem daty |
| `eu-compliance` | 5 | Akty UE, artykuły, porównania, zakres stosowania | `eu_article(GDPR,5)` → treść artykułu | PASS |
| `ms` | 1 | Pobranie orzeczenia po dokładnym ID MS; bez ogólnego `search` | `ms_get_document(ms:151020250000503_I_C_000270_2015_Uz_2016-04-07_001)` → I C 270/15 | PASS |
| `pmi` | 4 | Strony publiczne PrawMi, sygnatury i akty | `pmi_search(IV KO 74/26)` → 1 wynik | PASS |
| `repertorium` | 1 | Semantyczne odnajdywanie spraw, identyfikatory/fragmenty | `szukaj_repertorium(niesłuszne zatrzymanie)` → 8 wyników | PASS |
| `isap` | 3 | Tytuł/rok aktu, ELI, strony tekstu aktu | `pl_search(Kodeks karny)` → m.in. DU/2026/1342 | PASS z wyjątkiem PDF-only |
| `ustawy` | 1 | Dokładny akt i artykuł, nie wyszukiwanie fraz | `pl_get_document(akt=kk,art=1)` → treść art. 1 k.k. | PASS z ostrzeżeniem aktualności |
| `orzeczenia` | 3 | Semantyczne szukanie i stronicowany tekst po ID | `pl_get_document(prawmi-url:iv-ko-74-26)` → IV KO 74/26, 1989 znaków | PASS |

**Łącznie: 15 źródeł, 48 narzędzi natywnych, zero rozbieżności nazw pomiędzy rejestrem i `tools/list`.**

W przypadku `ms`, `krs`, `legal-cite` i `ustawy` brak dowolnej frazy wyszukiwania jest właściwością źródła; wrapper umożliwia dokładne odczyty i oferuje pozostałe indeksy do wyszukania identyfikatorów. Nie należy przypisywać każdemu z tych serwerów funkcji pełnotekstowej, której nie ma.

## Naprawy podczas audytu

1. **Powiększenie konfiguracji 12 → 15:** w produkcji uruchomiono adaptery `isap`, `ustawy`, `orzeczenia`, skonfigurowano odpowiadające `PRAWO_PL_MCP_URL_*` oraz sieci Docker `cf_mcp_isap`, `cf_mcp_ustawy`, `cf_mcp_orzeczenia`.
2. **MCP Ustawy:** stary rejestr wymieniał `akty/szukaj/artykul/cytat`, lecz serwer udostępnia dziś jedynie `przepis(akt,art,widok)`. Zmieniono mapowanie, dodano poprawne parsowanie `tekst` i zachowanie daty `stan_na`/ELI; test produkcyjny PASS.
3. **KIO:** uzupełniono `kio_coverage`, naprawiono obsługę zerwanych sesji upstream z pojedynczą próbą ponownego połączenia. Po wdrożeniu `pl_search`, `pl_call(kio_coverage)` i odczyt schematu działają; przed wdrożeniem kończyły się `Session terminated`.
4. **MCP Orzeczenia:** dodano `semantic_search` oraz `get_judgment/get_judgement`, poprawiono ekstrakcję tekstu z `documents[].tresc` i natywną paginację `offset/limit`. Pole `complete` jest prawdziwe tylko dla potwierdzonej jednokawałkowej pełnej treści; strony częściowe mają `has_more` i ostrzeżenie.
5. **Identyfikacja:** spójna aplikacyjna wersja `0.3.1` w obrazie, Pythonie i manifestach pluginu; pięć zunifikowanych narzędzi.
6. **Testy i publikacja:** 94 automatyczne testy Python PASS, Ruff PASS, marketplace-validation i podstawowe CI GitHub Actions PASS dla kodu przed raportem; commity na `main`, bez dodatkowych branchy/worktree.

## Granice i pozostałe ryzyka

- **PrawMi zewnętrzny:** dostępny jako osobny MCP (17 narzędzi) w Cloudflare i osobna połączona integracja, ale nie jako upstream tego kontenera. Umieszczono jego schemat jako opcjonalne źródło `prawmi` w rejestrze kodu, lecz NIE dodano do `PRAWO_PL_MCP_SOURCES`: zewnętrzny endpoint wymaga własnego OAuth/uprawnień i nie należy przekazywać sesji z innej integracji. Aby uzyskać pełne 16/16, trzeba ustanowić niezależną, zgodną z polityką dostawcy autoryzację serwer-serwer.
- **Prywatne akta / `akta_api_mcp`:** osobna infrastruktura dokumentów prywatnych, nie publiczny konektor prawny. Nie włączano do ogólnego wrappera bez polityki uprawnień.
- **`mcp-orzeczenia-db` i indexer:** są bazą oraz procesem indeksowania, a nie oddzielnymi serwerami MCP z narzędziami do dopisania do rejestru.
- **ISAP PDF-only:** `get_act_text(DU/2026/1342)` zwróciło `text_unavailable_use_pdf`; wyszukiwanie aktu działa, ale tekst tego aktu trzeba pobrać inną ścieżką (np. artykuł przez LEGAL-CITE).
- **Ustawy — stan czasowy:** art. 1 k.k. zwrócono ze źródła oznaczonego `stan_na=2026-07-21` i tekstem jednolitym `DU/2025/383`; ISAP wykazuje nowszy tekst jednolity `DU/2026/1342`. Przed powołaniem się na aktualny stan należy porównać nowelizacje w ELI/ISAP; sam `FOUND` nie dowodzi aktualności.
- **EUREKA — anomalia daty:** w odpowiedzi z 15 listopada 2026 pierwsza interpretacja została oznaczona datą wydania `2026-11-30` (przyszłą). Należy zweryfikować pochodzenie daty i mapowanie, nie interpretować jej bezwarunkowo jako już wydanej.
- **Repertorium / dane semantyczne:** wynik wyszukiwania jest indeksem i może mieć fragment tekstu, a nie pełne źródło. Dalsze pobieranie przez `pl_get_document`/źródło jest konieczne.
- **MS / PrawMi:** błędny identyfikator może zwrócić `invalid_arg` lub zero wyników bez awarii serwera; poprawne identyfikatory MS i PMI przetestowano skutecznie.
- **Uwierzytelnienie użytkownika:** Cloudflare zgłasza `ready/connected` i pięć narzędzi, ale audyt nie obejmował nowego interaktywnego logowania w każdym typie klienta ChatGPT/Claude.
- **Wersja zewnętrzna PyPI:** `server.json` nadal opisuje rzeczywistą publikację PyPI `0.2.4`, a nie obraz NAS `0.3.1`; bez nowej publikacji pakietu nie należy po cichu zmieniać historycznej referencji.

## Testy wdrożeniowe i ścieżki

- Produkcja: Portainer stack ID **68**, `mcp-prawo:0.3.1`, `healthy`; `/volume2/docker/mcp-prawo`.
- MCP URL: `https://mcp-prawo.xlap.pl/mcp` (Cloudflare Access).
- `main` repo: https://github.com/elconcept/mcp-prawo
- Zapis rejestru: `src/prawo_pl_mcp/registry.py`; proxy transport: `src/prawo_pl_mcp/pool.py`; konfiguracja: `docker-compose.nas.yml`.
- CI: https://github.com/elconcept/mcp-prawo/actions
- Odrębne testy źródeł: `tests/test_integrations_20261115.py` i `tests/test_dispatch_extra_20261115.py`.

**Werdykt:** Wszystkie 15 skonfigurowanych lokalnych źródeł na Synology są obecne, wykrywalne i zwracają dane przez wrapper. Nie należy utożsamiać tego z 16/16 wliczającym niezależny komercyjny PrawMi ani z absolutną kompletnością korpusów i aktualnością wszystkich tekstów.

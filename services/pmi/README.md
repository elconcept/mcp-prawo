# pmi

Personal, independent public-HTML connector for https://prawmi.pl.

No paid PrawMi API or key. No Tor modifications. Runs inside Portainer
as a separate FastMCP Streamable HTTP server; the existing wrapper accesses
it over the cf_edge_mcp Docker network.

## Native tools

- pmi_search(query, limit=10, kind="auto"): search the entire /ustawa
  title index, or validate a known ruling signature in /orzeczenie/.
  This is not semantic judgment search; free Repertorium provides that.
- pmi_get_document(document_id): full text for
  ruling:xii-ko-26-23, act:kodeks-postepowania-karnego,
  article:ochronie-zdrowia-psychicznego:art-23.
- pmi_get_article(act_slug, article): retrieve single article.
- pmi_list_acts(query="", limit=100): list index, cached 1 hour.

The wrapper continues to expose five public unified tools. The pmi
source uses PRAWO_PL_MCP_URL_PMI=http://pmi:8000/mcp;
pl_search(source="pmi") and pl_get_document(source="auto",
document_id="pmi:article:...") act as ordinary wrapper calls.

Full text goes into existing PostgreSQL on first retrieval;
the wrapper paginates text (~5000 characters per page).
The public acts index itself is not bulk-imported into PostgreSQL.

## Source parsing

Ruling: section#section-tresc .ruling-content (checking H1 signature).
Article: article#przepis with both multi-paragraph and single-paragraph layouts (excluding UI).
Full law: main article[id^="art-"] (including grouped/range-number article IDs).
Index: direct /ustawa/<slug> anchors (currently 895 entries).

## Returned metadata and provenance

- Acts: canonical URL, complete HTML meta tags and Schema.org JSON-LD, original
  publication (Dz.U.) and derived original ELI, official ISAP links, history
  link, sections, article identifiers and full statutory text.
- Article: act title, statutory text and repealed/omitted marker, original
  publication/ELI, source dateModified when provided, article-to-article links,
  any detected text-change history, and **linked judgments** with signature,
  court, date, case URL and actual excerpt.
- The case lists distinguish `linked_judgments_count` (court cards actually
  present in HTML) from `site_claimed_judgments_count` (marketing/page title).
  Case signatures mentioned only in site-generated suggested prompts are
  separately marked **unlinked and unverified**.
- Site explanations and FAQ are optional, separate and expressly tagged as
  unverified editorial material, never merged into statutory text.
- Rulings: full available ruling text plus court/date/type/panel metadata,
  site thesis (source-labelled), cited provisions and similar decisions.
- `original_eli_derived` is calculated from the **original** Dz.U. citation,
  not proof of the latest consolidated text or validity on a requested date.
  Detected change dates from PrawMi are not effective dates of amendments.

## Tests

Run self-contained parser tests:

    python -m unittest -q test_server.py

Portainer stack: pmi, separate from mcp-prawo-wrapper.

"""Public PrawMi HTML connector: rulings, statutes, article pages. No paid API."""
from __future__ import annotations

import asyncio
import difflib
import json
import re
import time
import unicodedata
from typing import Any
from urllib.parse import unquote

import httpx
from bs4 import BeautifulSoup
from fastmcp import FastMCP

BASE = "https://prawmi.pl"
INDEX_URL = BASE + "/ustawa"
RULING_BASE = BASE + "/orzeczenie/"
ACT_BASE = BASE + "/ustawa/"
USER_AGENT = "pmi-personal-mcp/1.0"
HEADERS = {"User-Agent": USER_AGENT, "Accept": "text/html"}
ACT_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ARTICLE_ID = re.compile(r"^art-[0-9]+[a-z]?(?:-[a-z])?$")
ACT_NODE_ID = re.compile(r"^art-[0-9]+[a-z]?(?:-[0-9]+[a-z]?)?$")
RULING_SIG = re.compile(r"^[A-ZĄĆĘŁŃÓŚŹŻ0-9IVXLCM.\-\s]{1,18}\s+[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]{1,8}\s+\d+/\d{2,4}$", re.I)
DZIENNIK = re.compile(r"(?:Dz\.?\s*U\.?\s*\d{4}\s*poz\.?\s*\d+)", re.I)
INDEX_TTL = 3600.0
_index_items: list[dict[str, str]] = []
_index_at = 0.0
_index_lock = asyncio.Lock()

mcp = FastMCP(
    "pmi",
    instructions=(
        "Independent reader of public HTML at prawmi.pl. Free and without API keys. "
        "pmi_search searches the indexed titles of statutes and resolves exact ruling signatures. "
        "pmi_get_document fetches full text by ruling:<signature-or-slug>, act:<slug>, "
        "or article:<slug>:art-23. pmi_get_article reads one article. "
        "This connector is not a semantic search engine; use free Repertorium for semantic discovery. "
        "Article content omits AI analysis and site UI."
    ),
)

ALIASES = {
    "kpk": "kodeks-postepowania-karnego",
    "kk": "kodeks-karny",
    "kw": "kodeks-wykroczen",
    "kpc": "kodeks-postepowania-cywilnego",
    "kc": "kodeks-cywilny",
    "kpa": "kodeks-postepowania-administracyjnego",
    "ksh": "kodeks-spolek-handlowych",
    "kro": "kodeks-rodzinny-i-opiekunczy",
    "kkw": "kodeks-karny-wykonawczy",
    "kp": "kodeks-pracy",
}


def fold(value: str) -> str:
    value = value.lower().replace("ł", "l")
    return "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))


def safe_slug(raw: str) -> str:
    value = unquote(raw).strip().lower()
    if not ACT_SLUG.fullmatch(value):
        raise ValueError("Invalid slug; only lowercase ASCII letters, digits and hyphens are supported.")
    return value


def ruling_slug(signature: str) -> str:
    value = fold(signature.strip())
    value = re.sub(r"^sygn(?:atura)?\.?\s*akt(?:a)?\.?\s*", "", value, flags=re.I)
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return safe_slug(value)


def article_id(raw: str) -> str:
    value = fold(raw.strip()).lower()
    value = re.sub(r"^art(?:\.|-)?\s*", "", value)
    value = value.replace(" ", "-").replace("_", "-")
    if not value.startswith("art-"):
        value = "art-" + value
    if not ARTICLE_ID.fullmatch(value):
        raise ValueError("Invalid article identifier. Examples: 23, art-23, 4a.")
    return value


async def fetch_html(url: str) -> BeautifulSoup:
    if not (url == INDEX_URL or url.startswith(ACT_BASE) or url.startswith(RULING_BASE)):
        raise ValueError("The URL is outside public PrawMi pages.")
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0), follow_redirects=False, headers=HEADERS) as client:
        response = await client.get(url)
    if response.status_code == 404:
        raise LookupError(f"Not found: {url}")
    if response.status_code != 200:
        raise RuntimeError(f"PrawMi HTTP {response.status_code}: {url}")
    if "text/html" not in response.headers.get("content-type", "").lower():
        raise RuntimeError("Unexpected response content type")
    return BeautifulSoup(response.text, "html.parser")


def clean_text(element: Any) -> str:
    value = element.get_text("\n", strip=True).replace("\xa0", " ")
    value = re.sub(r"[ \t]+", " ", value)
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def extract_article_content(root: Any) -> str:
    """Extract text from both paragraph and multi-paragraph PrawMi layouts."""
    body = root.select_one("div.mt-6.space-y-5")
    if body is not None:
        content = clean_text(body)
    else:
        panel = root.select_one("div.mt-6.rounded-2xl")
        paragraphs = panel.select("p.leading-relaxed") if panel else []
        content = "\n".join(clean_text(p) for p in paragraphs if clean_text(p)).strip()
    if not content:
        raise RuntimeError("PrawMi article content is missing or layout changed.")
    return content


def article_source_metadata(soup: BeautifulSoup) -> dict[str, str]:
    """Read source metadata without treating an original Dz.U. as a current t.j."""
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            payload = json.loads(script.string or script.get_text())
        except (TypeError, ValueError):
            continue
        candidates = payload if isinstance(payload, list) else [payload]
        for item in candidates:
            if not isinstance(item, dict) or item.get("@type") != "Article":
                continue
            law = item.get("isPartOf")
            publication = law.get("legislationIdentifier", "") if isinstance(law, dict) else ""
            modified = item.get("dateModified")
            result = {}
            if isinstance(publication, str) and publication:
                result["publication"] = publication
                match = re.search(r"Dz\.?\s*U\.?\s*(\d{4})\s*poz\.?\s*(\d+)", publication, flags=re.I)
                if match:
                    result["original_eli_derived"] = f"DU/{match.group(1)}/{match.group(2)}"
                result["publication_scope"] = "original_act_not_current_consolidation"
            if isinstance(modified, str) and modified:
                result["source_modified_at"] = modified
            return result
    return {}



def page_metadata(soup: BeautifulSoup) -> dict[str, Any]:
    """Preserve source HTML metadata and linked official references."""
    meta: dict[str, str] = {}
    for tag in soup.select("head meta[content]"):
        key = tag.get("name") or tag.get("property") or tag.get("http-equiv")
        if key:
            meta[key] = tag.get("content", "")
    json_ld: list[dict[str, Any]] = []
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            obj = json.loads(tag.string or tag.get_text())
        except (TypeError, ValueError):
            continue
        items = obj if isinstance(obj, list) else [obj]
        json_ld.extend(x for x in items if isinstance(x, dict))
    canonical = soup.select_one('link[rel="canonical"][href]')
    official_links: list[dict[str, str]] = []
    seen: set[str] = set()
    for a in soup.select("main a[href]"):
        href = a.get("href", "")
        if (href.startswith("https://isap.sejm.gov.pl/")
                or href.startswith("https://api.sejm.gov.pl/")
                or href.startswith("https://eli.gov.pl/")) and href not in seen:
            seen.add(href)
            official_links.append({"url": href, "label": a.get_text(" ", strip=True)})
    history = [
        {"url": BASE + a["href"], "label": a.get_text(" ", strip=True)}
        for a in soup.select('main a[href^="/ustawa/"]')
        if a["href"].split("?")[0].rstrip("/").endswith("/zmiany")
    ]
    result: dict[str, Any] = {
        "html_title": soup.title.get_text(" ", strip=True) if soup.title else "",
        "html_lang": soup.html.get("lang", "") if soup.html else "",
        "html_meta": meta,
        "schema_org": json_ld,
        "official_links": official_links,
    }
    if canonical:
        result["canonical_url"] = canonical["href"]
    if history:
        result["history_links"] = history
    return result





def article_judgments(soup: BeautifulSoup) -> dict[str, Any]:
    """Only judgments actually linked in HTML, with court/date and excerpt."""
    section = soup.select_one("section#orzeczenia")
    if section is None:
        return {}
    cases: list[dict[str, Any]] = []
    seen: set[str] = set()
    for card in section.select("article"):
        a = card.select_one('h3 a[href^="/orzeczenie/"]')
        if a is None:
            continue
        href = a.get("href", "").split("?")[0]
        if not href or href in seen:
            continue
        seen.add(href)
        line = card.select_one("div.flex.flex-wrap")
        spans = [x.get_text(" ", strip=True) for x in line.find_all("span", recursive=False)
                 if not x.has_attr("aria-hidden")] if line else []
        stamp = card.find("time")
        quote = card.find("blockquote")
        cases.append({
            "document_id": "pmi:ruling:" + href.split("/")[-1],
            "source_url": BASE + href,
            "signature": spans[0] if spans else "",
            "court": spans[1] if len(spans) > 1 else "",
            "date": stamp.get("datetime") if stamp else None,
            "date_label": stamp.get_text(" ", strip=True) if stamp else None,
            "title": a.get_text(" ", strip=True),
            "excerpt": clean_text(quote) if quote else "",
        })
    claimed = None
    for item in [soup.title.get_text(" ", strip=True) if soup.title else "",
                 soup.select_one('meta[name="description"]').get("content", "")
                 if soup.select_one('meta[name="description"]') else ""]:
        m = re.search(r"(\d+)\s+orzecz[eęńi]", item, re.I)
        if m:
            claimed = int(m.group(1))
            break
    result: dict[str, Any] = {"related_judgments": cases, "linked_judgments_count": len(cases)}
    if claimed is not None:
        result["site_claimed_judgments_count"] = claimed
    return result


def article_editorial_material(soup: BeautifulSoup) -> dict[str, Any]:
    """Store optional site commentary/FAQ separately, never as statutory text."""
    result: dict[str, Any] = {}
    explanation = soup.select_one("section#wyjasnienie")
    if explanation:
        heading = explanation.find("h2")
        content = heading.find_next_sibling("div") if heading else None
        if content:
            result["site_explanation"] = {
                "text": clean_text(content),
                "authority": "unverified_site_editorial_not_primary_law",
            }
    faq = soup.select_one("section#pytania")
    if faq:
        entries = []
        for block in faq.select("details"):
            question = block.find("summary")
            answer = block.find("p")
            if question and answer:
                question_text = question.find("span").get_text(" ", strip=True) if question.find("span") else question.get_text(" ", strip=True)
                entries.append({"question": question_text, "answer": clean_text(answer)})
        if entries:
            result["site_faq"] = {
                "entries": entries,
                "authority": "unverified_site_editorial_not_primary_law",
            }
    return result


def article_change_history(soup: BeautifulSoup) -> dict[str, Any]:
    """PrawMi detection dates are not legal entry-into-force dates."""
    section = soup.select_one("section#historia-zmian")
    if section is None:
        return {}
    note = section.find("p", recursive=False)
    list_node = section.find("ol", recursive=False)
    changes = []
    if list_node is not None:
        for item in list_node.find_all("li", recursive=False):
            header = item.find("h3")
            if not header:
                continue
            heading = header.get_text(" ", strip=True)
            date = re.search(r"(\d{2}\.\d{2}\.\d{4})", heading)
            status_tag = header.find_next_sibling("span")
            entry: dict[str, Any] = {
                "heading": heading,
                "detected_on": date.group(1) if date else None,
                "change_type": status_tag.get_text(" ", strip=True) if status_tag else None,
                "detail": item.get_text("\n", strip=True),
            }
            changes.append(entry)
    return {
        "history_detection_note": note.get_text(" ", strip=True) if note else "",
        "article_change_history": changes,
    }


def adjacent_article_links(soup: BeautifulSoup, slug: str) -> list[dict[str, str]]:
    """Expose explicit navigation links without inventing adjacency."""
    prefix = "/ustawa/" + slug + "/art-"
    result = []
    for a in soup.select("main a[href]"):
        href = a.get("href", "").split("?")[0]
        if href.startswith(prefix):
            link = {"article": href[len(prefix):], "url": BASE + href,
                    "label": a.get_text(" ", strip=True)}
            if link not in result:
                result.append(link)
    return result


def act_source_metadata(soup: BeautifulSoup) -> dict[str, Any]:
    """Expose machine-readable legislation identity without asserting currency."""
    schemas = page_metadata(soup)["schema_org"]
    legislation = [
        node for node in schemas
        if node.get("@type") == "Legislation" and node.get("legislationIdentifier")
    ]
    if not legislation:
        return {}
    preferred = next((x for x in legislation if x.get("legislationType")), legislation[0])
    out: dict[str, Any] = {"publication": preferred["legislationIdentifier"]}
    match = re.search(r"Dz\.?\s*U\.?\s*(\d{4})\s*poz\.?\s*(\d+)", out["publication"], flags=re.I)
    if match:
        out["original_eli_derived"] = f"DU/{match.group(1)}/{match.group(2)}"
        out["publication_scope"] = "original_act_not_current_consolidation"
    for key in ("legislationType", "legislationDate", "datePublished", "dateEnacted", "inLanguage"):
        if preferred.get(key):
            out[key] = preferred[key]
    jurisdiction = preferred.get("jurisdiction")
    if isinstance(jurisdiction, dict) and jurisdiction.get("name"):
        out["jurisdiction"] = jurisdiction["name"]
    return out


def act_sections(soup: BeautifulSoup) -> list[str]:
    """List legal section headings, excluding navigation and promotional headings."""
    headings = []
    for node in soup.select("main h2,main h3,main h4"):
        title = node.get_text(" ", strip=True)
        if re.match(r"^(Rozdział|Dział|Tytuł|Księga|Oddział|Część|Sekcja)\b", title, re.I):
            if title not in headings:
                headings.append(title)
    return headings


async def index_acts() -> list[dict[str, str]]:
    global _index_items, _index_at
    if _index_items and time.monotonic() - _index_at < INDEX_TTL:
        return _index_items
    async with _index_lock:
        if _index_items and time.monotonic() - _index_at < INDEX_TTL:
            return _index_items
        soup = await fetch_html(INDEX_URL)
        found: dict[str, dict[str, str]] = {}
        for section in soup.select("main section"):
            heading = section.find(["h2", "h3"])
            group = heading.get_text(" ", strip=True) if heading else "Inne"
            group = re.sub(r"\s*\(\s*\d+\s*\).*", "", group)
            for a in section.select('a[href^="/ustawa/"]'):
                path = a.get("href", "").split("?")[0].rstrip("/")
                slug = path[len("/ustawa/"):]
                if not ACT_SLUG.fullmatch(slug) or slug in found:
                    continue
                label = a.get_text(" ", strip=True)
                publication = DZIENNIK.search(label)
                title = label[:publication.start()].strip(" .") if publication else label
                found[slug] = {
                    "document_id": f"pmi:act:{slug}",
                    "title": title,
                    "publication": publication.group(0) if publication else "",
                    "slug": slug,
                    "category": group,
                    "source_url": BASE + path,
                }
        if not found:
            raise RuntimeError("PrawMi act index: no entries found (layout changed).")
        _index_items = list(found.values())
        _index_at = time.monotonic()
        return _index_items


async def get_ruling(signature: str) -> dict[str, Any]:
    slug = ruling_slug(signature)
    url = RULING_BASE + slug
    soup = await fetch_html(url)
    heading = soup.select_one("h1")
    if heading is None or ruling_slug(heading.get_text(" ", strip=True)) != slug:
        raise ValueError("PrawMi ruling heading does not match the requested signature.")
    section = soup.select("section#section-tresc .ruling-content")
    if len(section) != 1:
        raise RuntimeError("PrawMi ruling content selector changed.")
    content = clean_text(section[0])
    if len(content) < 50:
        raise RuntimeError("PrawMi ruling text is empty.")
    return {
        "document_id": f"pmi:ruling:{slug}",
        "kind": "ruling",
        "signature": heading.get_text(" ", strip=True),
        "source_url": url,
        "content_text": content,
        "total_chars": len(content),
    }


async def get_article(act: str, article: str) -> dict[str, Any]:
    slug = safe_slug(act)
    article = article_id(article)
    url = ACT_BASE + slug + "/" + article
    soup = await fetch_html(url)
    root = soup.select_one("article#przepis")
    if root is None:
        raise RuntimeError("PrawMi article container missing.")
    content = extract_article_content(root)
    act_title = root.select_one("p.text-sm")
    return {
        "document_id": f"pmi:article:{slug}:{article}",
        "kind": "article",
        "title": act_title.get_text(" ", strip=True) if act_title else slug,
        "article": article,
        "source_url": url,
        **page_metadata(soup),
        **article_source_metadata(soup),
        **article_change_history(soup),
        **article_judgments(soup),
        **article_editorial_material(soup),
        "adjacent_articles": adjacent_article_links(soup, slug),
        "content_text": f"{article.replace('art-', 'Art. ')}.\n{content}",
        "total_chars": len(content),
    }


async def get_act(slug: str) -> dict[str, Any]:
    slug = safe_slug(slug)
    url = ACT_BASE + slug
    soup = await fetch_html(url)
    heading = soup.select_one("main h1")
    articles = soup.select('main article[id^="art-"]')
    if not heading or not articles:
        raise RuntimeError("PrawMi act structure missing.")
    chunks = []
    for node in articles:
        art = node.get("id", "")
        if not ACT_NODE_ID.fullmatch(art):
            continue
        children = [n for n in node.find_all(recursive=False) if getattr(n, "name", None)]
        body = children[-1] if len(children) >= 2 else node
        text = clean_text(body)
        if text:
            chunks.append(f"{art.replace('art-', 'Art. ')}.\n{text}")
    if not chunks:
        raise RuntimeError("PrawMi act articles have no text.")
    content = "\n\n".join(chunks)
    return {
        "document_id": f"pmi:act:{slug}",
        "kind": "act",
        "title": heading.get_text(" ", strip=True),
        "source_url": url,
        **page_metadata(soup),
        **act_source_metadata(soup),
        "sections": act_sections(soup),
        "article_ids": [node["id"] for node in articles if ACT_NODE_ID.fullmatch(node["id"])],
        "article_count": len(chunks),
        "content_text": content,
        "total_chars": len(content),
    }


@mcp.tool
async def pmi_search(query: str, limit: int = 10, kind: str = "auto") -> dict[str, Any]:
    """Search the public law-title catalog, or resolve a known ruling signature.

    kind: auto / act / ruling. No site-wide semantic search is implied.
    Use free Repertorium MCP for semantic search of judgments.
    """
    if kind not in ("auto", "act", "ruling"):
        raise ValueError("kind must be auto, act, or ruling.")
    limit = max(1, min(30, int(limit)))
    query = query.strip()
    if not query:
        raise ValueError("query cannot be empty.")
    if kind in ("auto", "ruling") and RULING_SIG.fullmatch(query):
        try:
            r = await get_ruling(query)
        except LookupError:
            return {"query": query, "kind": "ruling", "count": 0, "results": []}
        return {"query": query, "kind": "ruling", "count": 1, "results": [
            {"document_id": r["document_id"], "title": r["signature"], "source_url": r["source_url"]}
        ]}
    if kind == "ruling":
        return {"query": query, "kind": "ruling", "count": 0, "results": [], "hint": "Search by case signature, or use free Repertorium."}

    docs = await index_acts()
    normalized = fold(query)
    alias = ALIASES.get(normalized)
    tokens = set(re.findall(r"[a-z0-9]{3,}", normalized))
    matches: list[tuple[float, dict[str, str]]] = []
    for act in docs:
        title = fold(act["title"])
        slug = act["slug"]
        if alias == slug:
            score = 100.0
        elif normalized in title or normalized in slug:
            score = 30.0 + len(normalized) / max(1, len(title))
        else:
            title_tokens = set(re.findall(r"[a-z0-9]{3,}", title.replace("-", " ")))
            common = len(tokens & title_tokens)
            score = common * 2 / max(1, len(tokens)) + difflib.SequenceMatcher(None, normalized, title).ratio()
            if common == 0 and score < 0.65:
                continue
        matches.append((score, act))
    matches.sort(key=lambda pair: (-pair[0], pair[1]["title"]))
    return {"query": query, "kind": "act", "indexed": len(docs), "count": len(matches),
            "results": [act for _, act in matches[:limit]]}


@mcp.tool
async def pmi_get_document(document_id: str) -> dict[str, Any]:
    """Full text from public PrawMi HTML by ruling, act or article document ID.

    Accepts: ruling:XII Ko 26/23, act:kodeks-karny,
    article:ochronie-zdrowia-psychicznego:art-23.
    A leading pmi: prefix is optional.
    """
    value = document_id.strip()
    if value.startswith("pmi:"):
        value = value[4:]
    typ, sep, remainder = value.partition(":")
    if not sep:
        if RULING_SIG.fullmatch(value):
            return await get_ruling(value)
        raise ValueError("Specify ruling:<signature>, act:<slug>, or article:<slug>:<number>.")
    if typ == "ruling":
        return await get_ruling(remainder)
    if typ == "act":
        return await get_act(remainder)
    if typ == "article":
        slug, sep2, art = remainder.partition(":")
        if not sep2:
            raise ValueError("Article requires article:<act-slug>:art-<number>.")
        return await get_article(slug, art)
    raise ValueError("Unknown PrawMi document type.")


@mcp.tool
async def pmi_get_article(act_slug: str, article: str) -> dict[str, Any]:
    """Fetch one public statutory article, e.g. KPK art. 246 or mental-health act art. 23."""
    return await get_article(act_slug, article)


@mcp.tool
async def pmi_list_acts(query: str = "", limit: int = 100) -> dict[str, Any]:
    """Catalog of acts scraped from the public PrawMi /ustawa page (one index request per hour)."""
    if query:
        return await pmi_search(query, limit, kind="act")
    items = await index_acts()
    return {"indexed": len(items), "results": items[:max(1, min(100, limit))]}


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

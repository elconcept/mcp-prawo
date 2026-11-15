import json

import pytest

import prawo_pl_mcp.server as srv
from prawo_pl_mcp.server import pl_get_document


class _FakePool:
    def __init__(self):
        self.response = ''
        self.calls = []
    async def call(self, source, tool, arguments):
        self.calls.append((source.id, tool, arguments))
        return self.response

@pytest.fixture
def pool(monkeypatch):
    fake = _FakePool()
    monkeypatch.setattr(srv, 'POOL', fake)
    return fake


async def test_ustawy_native_article_returns_text_with_provenance(pool):
    pool.response = json.dumps({
        'status': 'FOUND',
        'akt': 'kodeks-karny',
        'art': '1',
        'tekst': 'Art. 1. Odpowiedzialności karnej podlega ten tylko, kto popełnia czyn zabroniony.',
        'eli': 'DU/2025/383',
        'stan_na': '2026-07-21',
        'ostatnia_zmiana': 'DU/2026/902',
    }, ensure_ascii=False)
    out = json.loads(await pl_get_document('ustawy', '1', extra={'akt': 'kk'}))
    assert 'Art. 1.' in out['content']
    assert out['source_metadata']['eli'] == 'DU/2025/383'
    assert out['source_metadata']['stan_na'] == '2026-07-21'
    assert out['content_status'] == 'article_only'
    assert pool.calls[0][:2] == ('ustawy', 'przepis')
    assert pool.calls[0][2] == {'akt': 'kk', 'art': '1'}


async def test_orzeczenia_native_pagination_and_completeness(pool):
    doc = 'prawmi-url:iv-ko-74-26'
    pool.response = json.dumps({
        'status': 'found',
        'documents': [{
            'document_id': doc, 'tresc': 'Kolejny fragment orzeczenia i uzasadnienia.',
            'offset': 5000, 'next_offset': 5041, 'dlugosc_calkowita': 10000,
            'has_more': True, 'kompletnosc': 'full', 'sygnatura': 'IV KO 74/26',
            'url': 'https://prawmi.pl/orzeczenie/iv-ko-74-26',
        }],
    }, ensure_ascii=False)
    out = json.loads(await pl_get_document('orzeczenia', doc, page=2))
    assert out['page'] == 2 and out['pagination'] == 'native_offset'
    assert out['has_more'] is True and out['complete'] is False
    assert out['next_offset'] == 5041
    assert out['source_url'].endswith('iv-ko-74-26')
    assert pool.calls[0][2]['offset'] == 5000
    assert pool.calls[0][2]['limit'] == 5000


async def test_orzeczenia_first_and_last_native_page_complete(pool):
    doc = 'prawmi-url:iv-ko-74-26'
    pool.response = json.dumps({
        'status': 'found', 'documents': [{
            'document_id': doc, 'tresc': 'Pełna treść orzeczenia obecna w źródle.',
            'offset': 0, 'next_offset': 39, 'dlugosc_calkowita': 39,
            'has_more': False, 'kompletnosc': 'full',
        }],
    }, ensure_ascii=False)
    out = json.loads(await pl_get_document('orzeczenia', doc))
    assert out['complete'] is True
    assert out['pagination'] == 'native_offset'

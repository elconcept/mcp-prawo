from types import SimpleNamespace

import pytest

from prawo_pl_mcp.pool import SourcePool
from prawo_pl_mcp.registry import SOURCES


@pytest.mark.asyncio
async def test_call_recovers_once_from_terminated_remote_session(monkeypatch):
    pool = SourcePool()
    failures = []
    attempts = []

    class Client:
        async def call_tool(self, tool, arguments):
            attempts.append(tool)
            if len(attempts) == 1:
                raise RuntimeError('Session terminated')
            return SimpleNamespace(content=[SimpleNamespace(text='{"status":"ok"}')], structured_content=None, data=None)

    async def get_client(_):
        return Client()

    async def invalidate(_):
        failures.append('invalidated')

    monkeypatch.setattr(pool, 'get_client', get_client)
    monkeypatch.setattr(pool, '_invalidate_client', invalidate)
    assert await pool.call(SOURCES['kio'], 'kio_coverage', {}) == '{"status":"ok"}'
    assert attempts == ['kio_coverage', 'kio_coverage']
    assert failures == ['invalidated']


@pytest.mark.asyncio
async def test_list_tools_recovers_once_from_terminated_session(monkeypatch):
    pool = SourcePool()
    calls = []
    invalidated = []

    class Client:
        async def list_tools(self):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError('Session terminated')
            return [SimpleNamespace(name='kio_coverage', description='Coverage', inputSchema={'type': 'object'})]

    async def get_client(_):
        return Client()

    async def invalidate(_):
        invalidated.append(1)

    monkeypatch.setattr(pool, 'get_client', get_client)
    monkeypatch.setattr(pool, '_invalidate_client', invalidate)
    result = await pool.list_tools(SOURCES['kio'])
    assert result[0]['name'] == 'kio_coverage'
    assert len(calls) == 2 and len(invalidated) == 1


@pytest.mark.asyncio
async def test_source_error_does_not_trigger_retry(monkeypatch):
    pool = SourcePool()
    calls = []

    class Client:
        async def call_tool(self, tool, arguments):
            calls.append(1)
            raise ValueError('invalid_arg: native parameter missing')

    async def get_client(_):
        return Client()

    async def invalidate(_):
        raise AssertionError('Unexpected reconnection')

    monkeypatch.setattr(pool, 'get_client', get_client)
    monkeypatch.setattr(pool, '_invalidate_client', invalidate)
    with pytest.raises(ValueError, match='invalid_arg'):
        await pool.call(SOURCES['kio'], 'kio_search', {})
    assert calls == [1]


def test_registry_new_sources_match_probed_schema():
    assert SOURCES['ustawy'].native_tools == ('przepis',)
    assert SOURCES['ustawy'].get.required_extra == ('akt',)
    assert SOURCES['ustawy'].search is None
    assert set(SOURCES['isap'].native_tools) == {'search_acts', 'get_act', 'get_act_text'}
    assert SOURCES['isap'].get.page_param == 'page'
    assert set(SOURCES['orzeczenia'].native_tools) == {'semantic_search', 'get_judgment', 'get_judgement'}
    assert 'kio_coverage' in SOURCES['kio'].native_tools
    assert len(SOURCES) == 16

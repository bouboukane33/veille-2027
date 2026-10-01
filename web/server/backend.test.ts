import { test } from 'node:test';
import assert from 'node:assert/strict';
import { handleApi } from './backend.ts';

const env = {
  SUPABASE_URL: 'https://example.supabase.co',
  SUPABASE_SERVICE_ROLE_KEY: 'server-secret',
  GH_WORKFLOW_TOKEN: 'github-secret',
  COLLECT_ADMIN_KEY: 'operator-key',
  GITHUB_REPOSITORY: 'bouboukane33/veille-2027',
};
const request = (path = '/api/dataset', method = 'GET', auth?: string) =>
  new Request('https://app.example.org' + path, {
    method,
    headers: auth ? { authorization: 'Bearer ' + auth } : {},
  });
const mockResponse = (payload: unknown, status = 200) =>
  (async () => new Response(JSON.stringify(payload), { status })) as typeof fetch;

test('unconfigured live API returns names without exposing secrets', async () => {
  const result = await handleApi('/api/dataset', request(), {});
  assert.equal(result.status, 503);
  assert.deepEqual((await result.json()).missing, ['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY']);
});
test('empty connected database requires a first collection', async () => {
  const result = await handleApi('/api/dataset', request(), env, mockResponse([]));
  assert.equal(result.status, 404);
  assert.equal((await result.json()).code, 'no_collection');
});
test('live snapshot is read through server headers and returned without archive or secret', async () => {
  const fetcher = (async (url: string | URL | Request, options?: RequestInit) => {
    assert.match(String(url), /ccr_snapshots/);
    assert.equal((options?.headers as Record<string, string>).apikey, 'server-secret');
    return new Response(
      JSON.stringify([
        {
          dataset: { mode: 'live', schema_version: 1, tables: { content: [] } },
          revision: 3,
          updated_at: '2026-10-01T06:00:00Z',
        },
      ]),
    );
  }) as typeof fetch;
  const result = await handleApi('/api/dataset', request(), env, fetcher);
  assert.equal(result.status, 200);
  const body = await result.json();
  assert.equal(body.revision, 3);
  assert.equal(body.mode, 'live');
  assert.equal(JSON.stringify(body).includes('server-secret'), false);
});
test('demo data is refused by the live API', async () => {
  const result = await handleApi(
    '/api/dataset',
    request(),
    env,
    mockResponse([{ dataset: { mode: 'demo', schema_version: 1, tables: {} } }]),
  );
  assert.equal(result.status, 502);
});
test('operator authentication precedes GitHub dispatch', async () => {
  let calls = 0;
  const fetcher = (async () => {
    calls++;
    return new Response(null, { status: 204 });
  }) as typeof fetch;
  assert.equal(
    (await handleApi('/api/collect', request('/api/collect', 'POST', 'wrong'), env, fetcher))
      .status,
    401,
  );
  assert.equal(calls, 0);
  assert.equal(
    (await handleApi('/api/collect', request('/api/collect', 'POST', 'operator-key'), env, fetcher))
      .status,
    202,
  );
  assert.equal(calls, 1);
});
test('GitHub rejection is never announced as a queued or completed collection', async () => {
  const response = await handleApi(
    '/api/collect',
    request('/api/collect', 'POST', 'operator-key'),
    env,
    mockResponse({}, 403),
  );
  assert.equal(response.status, 502);
  assert.equal((await response.json()).code, 'dispatch_failed');
});
test('unsupported methods cannot write a snapshot', async () => {
  assert.equal((await handleApi('/api/dataset', request('/api/dataset', 'POST'), env)).status, 405);
});

import { timingSafeEqual } from 'node:crypto';

type Environment = Record<string, string | undefined>;
type Fetcher = typeof fetch;

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' },
  });

function supabaseConfig(env: Environment) {
  const missing = ['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY'].filter((k) => !env[k]);
  if (missing.length)
    return {
      error: json(
        {
          code: 'not_configured',
          missing,
          message:
            'Le stockage des données réelles doit être connecté dans les paramètres du serveur.',
        },
        503,
      ),
    };
  try {
    const url = new URL(env.SUPABASE_URL!);
    if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash)
      throw new Error();
    return {
      url: url.origin,
      headers: {
        apikey: env.SUPABASE_SERVICE_ROLE_KEY!,
        Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
      },
    };
  } catch {
    return {
      error: json({ code: 'invalid_configuration', message: 'URL de stockage invalide.' }, 503),
    };
  }
}

async function readSnapshot(
  env: Environment,
  fetcher: Fetcher,
  statusOnly: boolean,
): Promise<Response> {
  const config = supabaseConfig(env);
  if (config.error) return config.error;
  try {
    const columns = statusOnly ? 'revision,updated_at' : 'dataset,revision,updated_at';
    const response = await fetcher(
      `${config.url}/rest/v1/ccr_snapshots?id=eq.live&select=${columns}&limit=1`,
      {
        headers: config.headers,
        signal: AbortSignal.timeout(12_000),
        redirect: 'error',
      },
    );
    if (!response.ok)
      return json(
        {
          code: 'storage_unavailable',
          message: 'La base est inaccessible. Vérifiez le schéma et les accès.',
        },
        502,
      );
    const rows: unknown = await response.json();
    if (!Array.isArray(rows)) throw new Error();
    if (!rows.length)
      return json(
        {
          code: 'no_collection',
          message:
            'Le stockage est connecté. Lancez la première collecte réelle depuis GitHub Actions.',
        },
        404,
      );
    const row = rows[0];
    if (statusOnly)
      return json({
        connected: true,
        revision: row.revision,
        updated_at: row.updated_at,
        collection_enabled: Boolean(env.GH_WORKFLOW_TOKEN && env.COLLECT_ADMIN_KEY),
      });
    if (
      row.dataset?.mode !== 'live' ||
      row.dataset?.schema_version !== 1 ||
      !Array.isArray(row.dataset.tables?.content) ||
      row.dataset.tables.content.some((content: { is_demo: number }) => content.is_demo !== 0)
    )
      throw new Error();
    return json({ ...row.dataset, revision: row.revision, updated_at: row.updated_at });
  } catch {
    return json(
      {
        code: 'storage_unavailable',
        message: 'Lecture des données impossible. Réessayez après vérification du stockage.',
      },
      502,
    );
  }
}

async function dispatchCollection(request: Request, env: Environment, fetcher: Fetcher) {
  if (!env.GH_WORKFLOW_TOKEN || !env.COLLECT_ADMIN_KEY)
    return json(
      {
        code: 'collection_not_configured',
        message: 'Le lancement depuis le site n’est pas configuré. Utilisez GitHub Actions.',
      },
      503,
    );
  const submitted = Buffer.from(
    request.headers.get('authorization')?.replace(/^Bearer /, '') ?? '',
  );
  const expected = Buffer.from(env.COLLECT_ADMIN_KEY);
  if (submitted.length !== expected.length || !timingSafeEqual(submitted, expected)) {
    return json({ code: 'unauthorized', message: 'Clé opérateur incorrecte.' }, 401);
  }
  const repository = env.GITHUB_REPOSITORY || 'bouboukane33/veille-2027';
  if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repository))
    return json({ code: 'invalid_configuration', message: 'Dépôt GitHub invalide.' }, 503);
  try {
    const response = await fetcher(
      `https://api.github.com/repos/${repository}/actions/workflows/collect.yml/dispatches`,
      {
        method: 'POST',
        headers: {
          Accept: 'application/vnd.github+json',
          Authorization: `Bearer ${env.GH_WORKFLOW_TOKEN}`,
          'Content-Type': 'application/json',
          'X-GitHub-Api-Version': '2022-11-28',
        },
        body: JSON.stringify({ ref: 'main' }),
        signal: AbortSignal.timeout(12_000),
        redirect: 'error',
      },
    );
    if (response.status !== 204)
      return json(
        {
          code: 'dispatch_failed',
          message:
            'GitHub n’a pas accepté la collecte. Vérifiez le workflow et les droits Actions du jeton.',
        },
        502,
      );
    return json(
      {
        status: 'queued',
        message: 'Collecte demandée à GitHub. Les résultats seront visibles après publication.',
      },
      202,
    );
  } catch {
    return json(
      {
        code: 'dispatch_failed',
        message: 'GitHub est inaccessible. La collecte n’a pas été confirmée.',
      },
      502,
    );
  }
}

export async function handleApi(
  path: string,
  request: Request,
  env: Environment = process.env,
  fetcher: Fetcher = fetch,
): Promise<Response> {
  const method = request.method;
  if ((path === '/api/dataset' || path === '/api/status') && method === 'GET') {
    return readSnapshot(env, fetcher, path === '/api/status');
  }
  if (path === '/api/collect' && method === 'POST')
    return dispatchCollection(request, env, fetcher);
  return json({ code: 'method_not_allowed', message: 'Requête non prise en charge.' }, 405);
}

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { PGlite } from '@electric-sql/pglite';

test('PostgreSQL migration enforces live mode, atomic publication, revisions and restricted access', async () => {
  const db = new PGlite();
  try {
    await db.exec(
      'CREATE ROLE anon; CREATE ROLE authenticated; CREATE ROLE service_role BYPASSRLS;',
    );
    const sql = await readFile(new URL('../../supabase/schema.sql', import.meta.url), 'utf8');
    await db.exec(sql);
    await db.exec(sql); // La migration peut être rejouée.
    const publish = (
      mode: string,
      revision: number,
      tables: unknown = { metadata: [{ key: 'dataset_kind', value: 'live' }] },
    ) =>
      db.query('SELECT public.publish_ccr_snapshot($1::jsonb, $2::jsonb, $3) AS revision', [
        JSON.stringify({ mode }),
        JSON.stringify(tables),
        revision,
      ]);
    assert.equal(
      (await publish('live', 0)).rows[0] &&
        ((await db.query('SELECT revision FROM ccr_snapshots')).rows[0] as { revision: number })
          .revision,
      1,
    );
    await assert.rejects(publish('demo', 1));
    await assert.rejects(publish('live', 0)); // Une ancienne tâche ne peut écraser un snapshot récent.
    await assert.rejects(publish('live', 1, { news_articles: [{ is_demo: 1 }] }));
    assert.equal(
      ((await db.query('SELECT revision FROM ccr_snapshots')).rows[0] as { revision: number })
        .revision,
      1,
    );
    await publish('live', 1);
    assert.equal(
      ((await db.query('SELECT revision FROM ccr_snapshots')).rows[0] as { revision: number })
        .revision,
      2,
    );
    await db.exec('SET ROLE anon');
    await assert.rejects(db.query('SELECT * FROM public.ccr_snapshots'));
    await assert.rejects(publish('live', 2));
    await db.exec('RESET ROLE; SET ROLE service_role');
    assert.equal((await db.query('SELECT * FROM public.ccr_snapshots')).rows.length, 1);
    await publish('live', 2);
    assert.equal(
      ((await db.query('SELECT revision FROM ccr_snapshots')).rows[0] as { revision: number })
        .revision,
      3,
    );
  } finally {
    await db.close();
  }
});

import type { Content, Dataset, Metric, Person } from './types';

export const topicLabels: Record<string, string> = {
  cat_nat: 'Catastrophes naturelles',
  climat: 'Climat',
  inondation: 'Inondations',
  secheresse: 'Sécheresse & RGA',
  assurance: 'Assurance',
  prevention: 'Prévention',
  collectivites: 'Collectivités',
  logement: 'Logement',
  agriculture: 'Agriculture',
  finances_publiques: 'Finances publiques',
};
export const topicLabel = (key: string) => topicLabels[key] || key.replaceAll('_', ' ');
export const number = (value: number) => new Intl.NumberFormat('fr-FR').format(value);
export const score = (value: number) =>
  new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 1 }).format(value);
export const formatDate = (value: string, options?: Intl.DateTimeFormatOptions) =>
  new Intl.DateTimeFormat('fr-FR', {
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
    ...options,
  }).format(new Date(value.length === 10 ? value + 'T12:00:00Z' : value));
export const initials = (name: string) =>
  name
    .split(/[\s-]+/)
    .filter(Boolean)
    .map((p) => p[0])
    .slice(0, 2)
    .join('');
export const colors = ['#127461', '#729e8b', '#cea867', '#6c83a3', '#b68383'];

export function derive(data: Dataset, personId: string, days: number) {
  const end = new Date(data.as_of + 'T12:00:00Z');
  const first = new Date(end);
  first.setUTCDate(first.getUTCDate() - days + 1);
  const cutoff = first.toISOString().slice(0, 10);
  const people = data.tables.personalities.filter((p) => p.status === 'suivi');
  const contentTopics = new Map<string, string[]>();
  for (const t of data.tables.content_topics)
    contentTopics.set(t.content_key, [...(contentTopics.get(t.content_key) || []), t.topic]);
  const contentPeople = new Map<string, string[]>();
  for (const p of data.tables.content_personalities)
    contentPeople.set(p.content_key, [
      ...(contentPeople.get(p.content_key) || []),
      p.personality_id,
    ]);
  const contents = data.tables.content
    .filter(
      (c) =>
        contentPeople.has(c.content_key) &&
        c.date >= cutoff &&
        c.date <= data.as_of &&
        (personId === 'all' || contentPeople.get(c.content_key)?.includes(personId)),
    )
    .sort((a, b) => b.published_at.localeCompare(a.published_at));
  const metrics = data.tables.daily_metrics.filter(
    (m) =>
      m.date >= cutoff &&
      m.date <= data.as_of &&
      (personId === 'all' || m.personality_id === personId),
  );
  const latest = new Map(
    data.tables.daily_metrics
      .filter((m) => m.date === data.as_of)
      .map((m) => [m.personality_id, m]),
  );
  const ranking = people
    .filter((p) => personId === 'all' || p.personality_id === personId)
    .map((p) => ({ ...p, metric: latest.get(p.personality_id) }))
    .sort(
      (a, b) =>
        (b.metric?.visibility_score || 0) - (a.metric?.visibility_score || 0) ||
        a.name.localeCompare(b.name),
    );
  const chartPeople = ranking.slice(0, 3);
  const chart: Record<string, string | number>[] = [];
  for (let d = new Date(first); d <= end; d.setUTCDate(d.getUTCDate() + 1)) {
    const day = d.toISOString().slice(0, 10);
    const row: Record<string, string | number> = {
      date: day,
      label: formatDate(day, { day: 'numeric', month: 'short' }),
    };
    for (const p of chartPeople)
      row[p.personality_id] =
        metrics.find((m) => m.date === day && m.personality_id === p.personality_id)
          ?.visibility_score || 0;
    chart.push(row);
  }
  const themes = data.tables.topics
    .map((t) => ({
      ...t,
      count: contents.filter((c) => contentTopics.get(c.content_key)?.includes(t.topic)).length,
    }))
    .sort((a, b) => b.count - a.count || a.topic.localeCompare(b.topic));
  return {
    people,
    contents,
    metrics,
    ranking,
    chartPeople,
    chart,
    themes,
    contentTopics,
    contentPeople,
    cutoff,
  };
}

export function csvDownload(data: Dataset, table: string) {
  const columns = data.columns[table];
  const encode = (v: unknown) =>
    '"' +
    (v == null ? '' : typeof v === 'object' ? JSON.stringify(v) : String(v)).replaceAll('"', '""') +
    '"';
  const rows = data.tables[table] as Record<string, unknown>[];
  const csv =
    [
      columns.join(','),
      ...rows.map((row) => columns.map((key) => encode(row[key])).join(',')),
    ].join('\n') + '\n';
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = table + '.csv';
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function sourceUrl(content: Pick<Content, 'url' | 'is_demo'>) {
  if (content.is_demo) return undefined;
  try {
    const url = new URL(content.url);
    return ['https:', 'http:'].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
}

export type RankedPerson = Person & { metric: Metric | undefined };

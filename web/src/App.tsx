import { useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  ChevronRight,
  CircleHelp,
  Cloud,
  Database,
  Download,
  ExternalLink,
  FileText,
  LayoutDashboard,
  LoaderCircle,
  Menu,
  Newspaper,
  NotebookTabs,
  Play,
  Printer,
  Radar,
  RefreshCw,
  Search,
  ShieldCheck,
  Tags,
  TrendingUp,
  UsersRound,
  Video,
  X,
} from 'lucide-react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { ApiError, Content, Dataset } from './types';
import {
  colors,
  csvDownload,
  derive,
  formatDate,
  initials,
  number,
  score,
  sourceUrl,
  topicLabel,
} from './data';

type Page = 'overview' | 'personalities' | 'topics' | 'activity' | 'brief' | 'sources';
const pages = [
  {
    id: 'overview',
    label: 'Vue d’ensemble',
    icon: LayoutDashboard,
    subtitle: 'L’essentiel de la couverture médiatique, en un regard.',
  },
  {
    id: 'personalities',
    label: 'Personnalités',
    icon: UsersRound,
    subtitle: 'Suivre les mentions, les sujets et l’évolution de chaque personnalité.',
  },
  {
    id: 'topics',
    label: 'Thématiques CCR',
    icon: Tags,
    subtitle: 'Identifier les sujets qui comptent pour la veille institutionnelle.',
  },
  {
    id: 'activity',
    label: 'Actualités',
    icon: Newspaper,
    subtitle: 'Explorer les contenus publics et retrouver leurs sources.',
  },
  {
    id: 'brief',
    label: 'Fiche rencontre',
    icon: NotebookTabs,
    subtitle: 'Les repères et les contenus à consulter avant un échange.',
  },
  {
    id: 'sources',
    label: 'Sources & méthode',
    icon: Database,
    subtitle: 'Comprendre la couverture, les scores et la fraîcheur des données.',
  },
] as const;
const currentPage = (): Page =>
  pages.some((p) => p.id === location.hash.slice(1))
    ? (location.hash.slice(1) as Page)
    : 'overview';

function Avatar({ name, index = 0 }: { name: string; index?: number }) {
  return (
    <span className={`avatar avatar-${index % 5}`} aria-hidden="true">
      {initials(name)}
    </span>
  );
}
function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="empty">
      <Search size={24} />
      <p>{children}</p>
    </div>
  );
}
function Delta({ value }: { value?: number | null }) {
  if (value == null) return <span className="muted">—</span>;
  const Icon = value > 0 ? ArrowUpRight : value < 0 ? ArrowDownRight : ArrowRight;
  return (
    <span className={`delta ${value > 0 ? 'positive' : value < 0 ? 'negative' : 'neutral'}`}>
      <Icon size={14} />
      {value > 0 ? '+' : ''}
      {score(value)} pts
    </span>
  );
}
function Panel({
  title,
  detail,
  action,
  children,
  className = '',
}: {
  title: string;
  detail?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          {detail && <p>{detail}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
function Article({
  content,
  topics,
  onTopic,
}: {
  content: Content;
  topics: string[];
  onTopic?: (t: string) => void;
}) {
  const url = sourceUrl(content);
  return (
    <article className="article-row">
      <div className={`content-icon ${content.content_type}`}>
        {content.content_type === 'news' ? <Newspaper size={19} /> : <Video size={19} />}
      </div>
      <div className="article-body">
        <div className="article-meta">
          <span>{content.source}</span>
          <i />
          {formatDate(content.published_at)}
          {content.is_demo === 1 && <span className="demo-inline">FICTIF</span>}
        </div>
        {url ? (
          <a className="article-title" href={url} target="_blank" rel="noopener noreferrer">
            {content.title}
            <ExternalLink size={13} />
          </a>
        ) : (
          <h3 className="article-title">{content.title}</h3>
        )}
        <div className="tags">
          {topics.slice(0, 3).map((t) => (
            <button key={t} className="tag" onClick={() => onTopic?.(t)} disabled={!onTopic}>
              {topicLabel(t)}
            </button>
          ))}
        </div>
      </div>
    </article>
  );
}

export default function App() {
  const [page, setPage] = useState<Page>(currentPage);
  const [mode, setMode] = useState<'live' | 'demo'>('live');
  const [data, setData] = useState<Dataset | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  const [personId, setPersonId] = useState('all');
  const [days, setDays] = useState(30);
  const [search, setSearch] = useState('');
  const [topic, setTopic] = useState('all');
  const [kind, setKind] = useState('all');
  const [mobileNav, setMobileNav] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [collectOpen, setCollectOpen] = useState(false);
  const [adminKey, setAdminKey] = useState('');
  const [collectBusy, setCollectBusy] = useState(false);
  const [collectMessage, setCollectMessage] = useState('');
  const [waitingRevision, setWaitingRevision] = useState<number | null>(null);

  const navigate = (next: Page) => {
    location.hash = next;
    setPage(next);
    setMobileNav(false);
  };
  const openBrief = (id: string) => {
    setPersonId(id);
    navigate('brief');
  };
  useEffect(() => {
    const listener = () => setPage(currentPage());
    window.addEventListener('hashchange', listener);
    return () => window.removeEventListener('hashchange', listener);
  }, []);
  useEffect(() => {
    if (!exportOpen && !collectOpen) return;
    const previous = document.activeElement as HTMLElement | null;
    const dialog = document.querySelector<HTMLElement>('[role="dialog"]');
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    dialog?.querySelector<HTMLElement>('button, input, a')?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setExportOpen(false);
        setCollectOpen(false);
        setAdminKey('');
      }
      if (event.key === 'Tab') {
        const elements = Array.from(
          dialog?.querySelectorAll<HTMLElement>('button:not(:disabled), input, a[href]') || [],
        );
        const first = elements[0],
          last = elements[elements.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = overflow;
      previous?.focus();
    };
  }, [exportOpen, collectOpen]);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setData(null);
    fetch(mode === 'demo' ? '/demo.json' : '/api/dataset', {
      signal: controller.signal,
      cache: 'no-store',
    })
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok) throw result;
        if (
          result.mode !== mode ||
          result.schema_version !== 1 ||
          !Array.isArray(result.sources) ||
          !result.columns ||
          ![
            'personalities',
            'content',
            'daily_metrics',
            'topics',
            'content_personalities',
            'content_topics',
            'personality_brief',
          ].every((k) => Array.isArray(result.tables?.[k]))
        ) {
          throw { code: 'invalid_dataset', message: 'Le format des données est incompatible.' };
        }
        setData(result);
        setLoading(false);
      })
      .catch((e) => {
        if (!controller.signal.aborted) {
          setError({
            code: e.code || 'network_error',
            message: e.message || 'Impossible de lire les données. Vérifiez la connexion.',
            missing: e.missing,
          });
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [mode, reload]);
  useEffect(() => {
    if (waitingRevision == null || mode !== 'live') return;
    const start = Date.now();
    const timer = setInterval(async () => {
      if (Date.now() - start > 15 * 60_000) {
        setWaitingRevision(null);
        setCollectMessage('Publication non confirmée. Consultez le résultat du workflow GitHub.');
        return;
      }
      try {
        const response = await fetch('/api/status', { cache: 'no-store' });
        const status = await response.json();
        if (response.ok && status.revision > waitingRevision) {
          setWaitingRevision(null);
          setCollectMessage('Une nouvelle révision est disponible.');
          setReload((v) => v + 1);
        }
      } catch {
        /* Le statut sera relu au prochain intervalle, sans annoncer de réussite. */
      }
    }, 15_000);
    return () => clearInterval(timer);
  }, [waitingRevision, mode]);

  const view = useMemo(() => (data ? derive(data, personId, days) : null), [data, personId, days]);
  const pageInfo = pages.find((p) => p.id === page)!;
  const briefId = personId === 'all' ? view?.ranking[0]?.personality_id : personId;
  const brief = data?.tables.personality_brief.find((b) => b.personality_id === briefId);
  const activity =
    view?.contents.filter(
      (c) =>
        (kind === 'all' || c.content_type === kind) &&
        (topic === 'all' || view.contentTopics.get(c.content_key)?.includes(topic)) &&
        (!search ||
          `${c.title} ${c.description} ${c.source}`
            .toLocaleLowerCase('fr')
            .includes(search.toLocaleLowerCase('fr'))),
    ) || [];
  const incomplete = data?.sources.some((s) => !['ok', 'disabled'].includes(s.status));

  async function triggerCollection() {
    setCollectBusy(true);
    setCollectMessage('');
    try {
      const response = await fetch('/api/collect', {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + adminKey },
      });
      const result = await response.json();
      setCollectMessage(result.message);
      if (response.status === 202) {
        setWaitingRevision(data?.revision || 0);
        setCollectOpen(false);
        setAdminKey('');
      }
    } catch {
      setCollectMessage('La demande de collecte n’a pas été confirmée. Vérifiez votre connexion.');
    } finally {
      setCollectBusy(false);
    }
  }

  const ranking = (limit: number) =>
    view!.ranking.slice(0, limit).map((p, i) => (
      <button
        key={p.personality_id}
        className="rank-row"
        onClick={() => openBrief(p.personality_id)}
      >
        <span className="rank-number">{String(i + 1).padStart(2, '0')}</span>
        <Avatar name={p.name} index={i} />
        <div className="rank-person">
          <strong>{p.name}</strong>
          <div className="score-track">
            <span
              style={{
                width: `${p.metric?.visibility_score || 0}%`,
                background: colors[i % colors.length],
              }}
            />
          </div>
        </div>
        <span className="rank-score">
          {score(p.metric?.visibility_score || 0)}
          <small>/100</small>
        </span>
      </button>
    ));

  return (
    <div className="app-shell">
      {mobileNav && (
        <button
          className="nav-scrim"
          aria-label="Fermer le menu"
          onClick={() => setMobileNav(false)}
        />
      )}
      <aside className={`sidebar ${mobileNav ? 'open' : ''}`}>
        <a href="#overview" className="brand" onClick={() => navigate('overview')}>
          <div className="brand-mark">
            <Radar size={27} />
          </div>
          <div>
            <strong>
              CCR<span> VEILLE</span>
            </strong>
            <small>OBSERVATOIRE 2027</small>
          </div>
        </a>
        <div className="sidebar-rule" />
        <div className="nav-label">ESPACE DE VEILLE</div>
        <nav aria-label="Navigation principale">
          {pages.slice(0, 5).map((p) => (
            <a
              key={p.id}
              href={`#${p.id}`}
              onClick={() => navigate(p.id)}
              className={page === p.id ? 'active' : ''}
              aria-current={page === p.id ? 'page' : undefined}
            >
              <p.icon size={19} />
              <span>{p.label}</span>
              {page === p.id && <span className="nav-dot" />}
            </a>
          ))}
        </nav>
        <div className="sidebar-note">
          <div className="note-icon">
            <ShieldCheck size={18} />
          </div>
          <strong>Une veille, des repères.</strong>
          <p>Des contenus publics pour éclairer les échanges institutionnels.</p>
          <span>Sources traçables · Scores explicables</span>
        </div>
        <div className="sidebar-bottom">
          <a
            href="#sources"
            onClick={() => navigate('sources')}
            className={page === 'sources' ? 'active' : ''}
          >
            <Database size={18} />
            Sources & méthode
          </a>
          <div className="sidebar-user">
            <span className="user-monogram">CR</span>
            <div>
              <strong>Veille institutionnelle</strong>
              <small>POC · CCR</small>
            </div>
            <span className="online-dot" />
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            aria-label="Ouvrir le menu"
            onClick={() => setMobileNav(true)}
          >
            <Menu size={21} />
          </button>
          <div className="breadcrumb">
            Observatoire 2027
            <ChevronRight size={14} />
            <strong>{pageInfo.label}</strong>
          </div>
          <div className="topbar-right">
            <span className={`mode-badge ${mode}`}>
              <span />
              {mode === 'demo' ? 'DEMO / FICTIF' : 'Données réelles'}
            </span>
            <span className="topbar-divider" />
            <button
              className="icon-button"
              title="Sources et méthode"
              aria-label="Sources et méthode"
              onClick={() => navigate('sources')}
            >
              <CircleHelp size={19} />
            </button>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                <span /> VEILLE MÉDIATIQUE & INSTITUTIONNELLE
              </div>
              <h1>{pageInfo.label}</h1>
              <p>{pageInfo.subtitle}</p>
            </div>
            <button className="button primary" onClick={() => setExportOpen(true)} disabled={!data}>
              <Download size={16} />
              Exporter les données
            </button>
          </div>
          <div className="toolbar">
            <div className="toolbar-filters">
              <label className="select-wrap">
                <UsersRound size={15} />
                <span className="sr-only">Personnalité</span>
                <select
                  aria-label="Personnalité"
                  value={personId}
                  onChange={(e) => setPersonId(e.target.value)}
                >
                  <option value="all">Toutes les personnalités</option>
                  {view?.people.map((p) => (
                    <option key={p.personality_id} value={p.personality_id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="select-wrap">
                <CalendarDays size={15} />
                <select
                  aria-label="Période"
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                >
                  <option value="30">30 derniers jours</option>
                  <option value="7">7 derniers jours</option>
                </select>
              </label>
            </div>
            <div className="toolbar-right">
              <span className="updated">
                {data
                  ? `Référence : ${formatDate(data.as_of, { year: 'numeric' })}`
                  : 'Connexion aux données'}
              </span>
              <button
                className="icon-button"
                aria-label="Recharger les données"
                title="Relire le dernier résultat publié"
                onClick={() => setReload((v) => v + 1)}
                disabled={loading}
              >
                <RefreshCw size={16} className={loading ? 'spin' : ''} />
              </button>
            </div>
          </div>
          {mode === 'demo' && (
            <div className="notice demo-notice">
              <ShieldCheck size={18} />
              <p>
                <strong>Données de démonstration.</strong> Tous les contenus et chiffres sont
                fictifs. Aucune déclaration réelle n’est attribuée.
              </p>
              <button
                onClick={() => {
                  setMode('live');
                  setPersonId('all');
                }}
              >
                Revenir aux données réelles
                <ArrowRight size={14} />
              </button>
            </div>
          )}
          {collectMessage && !collectOpen && (
            <div className="notice">
              <Cloud size={18} />
              <p>{collectMessage}</p>
              {waitingRevision != null && <LoaderCircle size={17} className="spin" />}
            </div>
          )}
          {incomplete && (
            <div className="notice coverage-notice">
              <CircleHelp size={18} />
              <p>
                <strong>Couverture partielle.</strong> Certaines sources sont absentes ou
                indisponibles ; les scores décrivent uniquement le corpus observé.
              </p>
              <button onClick={() => navigate('sources')}>
                Voir les sources
                <ArrowRight size={14} />
              </button>
            </div>
          )}

          {loading ? (
            <div className="loading-state">
              <LoaderCircle size={30} className="spin" />
              <h2>Lecture des données…</h2>
              <p>Chargement du dernier résultat publié.</p>
            </div>
          ) : error ? (
            <section className="connection-card">
              <div className="connection-icon">
                <Cloud size={34} />
              </div>
              <div className="eyebrow">DONNÉES RÉELLES</div>
              <h2>
                {error.code === 'no_collection'
                  ? 'Prêt pour la première collecte'
                  : 'Connecter votre espace de veille'}
              </h2>
              <p>{error.message}</p>
              <div className="setup-steps">
                <div>
                  <span>01</span>
                  <strong>Préparer Supabase</strong>
                  <small>Exécuter le schéma dédié à CCR Veille.</small>
                </div>
                <div>
                  <span>02</span>
                  <strong>Configurer les accès</strong>
                  <small>Clés serveur dans Vercel et GitHub.</small>
                </div>
                <div>
                  <span>03</span>
                  <strong>Lancer la collecte</strong>
                  <small>Publier le premier corpus de sources publiques.</small>
                </div>
              </div>
              {error.missing && (
                <p className="configuration-names">
                  Variables requises : {error.missing.join(', ')}
                </p>
              )}
              <div className="connection-actions">
                <a
                  className="button primary"
                  href="https://github.com/bouboukane33/veille-2027/blob/main/docs/VERCEL.md"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Guide de connexion
                  <ExternalLink size={15} />
                </a>
                <button
                  className="button secondary"
                  onClick={() => {
                    setMode('demo');
                    setPersonId('all');
                  }}
                >
                  Explorer l’aperçu fictif
                  <ArrowRight size={15} />
                </button>
              </div>
            </section>
          ) : (
            data &&
            view && (
              <>
                {page === 'overview' && (
                  <>
                    <div className="kpi-grid">
                      {[
                        {
                          label: 'Personnalités suivies',
                          value: personId === 'all' ? view.people.length : 1,
                          icon: UsersRound,
                          detail: 'Liste de suivi configurable',
                        },
                        {
                          label: 'Articles analysés',
                          value: view.contents.filter((c) => c.content_type === 'news').length,
                          icon: Newspaper,
                          detail: `Contenus uniques · ${days} jours`,
                        },
                        {
                          label: 'Vidéos analysées',
                          value: view.contents.filter((c) => c.content_type === 'youtube').length,
                          icon: Video,
                          detail: 'Métadonnées publiques',
                        },
                        {
                          label: 'Contenus liés à CCR',
                          value: view.contents.filter((c) => view.contentTopics.has(c.content_key))
                            .length,
                          icon: Tags,
                          detail: 'Au moins un thème CCR détecté',
                        },
                      ].map((k, i) => (
                        <div className={`kpi-card ${i === 3 ? 'accent' : ''}`} key={k.label}>
                          <div className="kpi-top">
                            <span>{k.label}</span>
                            <k.icon size={18} />
                          </div>
                          <strong className="kpi-value">{number(k.value)}</strong>
                          <small>{k.detail}</small>
                        </div>
                      ))}
                    </div>
                    <div className="overview-charts">
                      <Panel
                        title="Évolution de la visibilité"
                        detail="Scores quotidiens des personnalités les plus visibles à la date de référence"
                        action={<span className="subtle-chip">Score / 100</span>}
                      >
                        <div className="chart-legend">
                          {view.chartPeople.map((p, i) => (
                            <span key={p.personality_id}>
                              <i style={{ background: colors[i] }} />
                              {p.name}
                            </span>
                          ))}
                        </div>
                        <div
                          className="line-chart"
                          role="img"
                          aria-label="Historique des scores de visibilité"
                        >
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart
                              data={view.chart}
                              margin={{ top: 10, right: 8, left: -25, bottom: 0 }}
                            >
                              <CartesianGrid
                                strokeDasharray="3 5"
                                vertical={false}
                                stroke="#e9eeed"
                              />
                              <XAxis
                                dataKey="label"
                                tickLine={false}
                                axisLine={false}
                                minTickGap={36}
                                tick={{ fontSize: 11, fill: '#82908d' }}
                              />
                              <YAxis
                                domain={[0, 100]}
                                tickLine={false}
                                axisLine={false}
                                tick={{ fontSize: 11, fill: '#82908d' }}
                              />
                              <Tooltip
                                contentStyle={{
                                  borderRadius: 10,
                                  border: '1px solid #e4eae7',
                                  fontSize: 12,
                                }}
                              />
                              {view.chartPeople.map((p, i) => (
                                <Line
                                  key={p.personality_id}
                                  type="monotone"
                                  dataKey={p.personality_id}
                                  name={p.name}
                                  stroke={colors[i]}
                                  strokeWidth={2.5}
                                  dot={false}
                                  activeDot={{ r: 4 }}
                                />
                              ))}
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                        <div className="chart-footnote">
                          Couverture observée sur le corpus · Aucune mesure d’intention de vote
                        </div>
                      </Panel>
                      <Panel
                        title="Classement visibilité"
                        detail={`À la date du ${formatDate(data.as_of)}`}
                        action={<TrendingUp size={19} className="muted" />}
                      >
                        <div className="ranking">{ranking(5)}</div>
                        <button className="panel-link" onClick={() => navigate('personalities')}>
                          Voir toutes les personnalités
                          <ArrowRight size={15} />
                        </button>
                      </Panel>
                    </div>
                    <div className="overview-bottom">
                      <Panel
                        title="Les thèmes CCR dans l’actualité"
                        detail="Nombre de contenus uniques par thème sur la période"
                        action={
                          <button className="text-button" onClick={() => navigate('topics')}>
                            Explorer
                            <ArrowUpRight size={15} />
                          </button>
                        }
                      >
                        <div className="theme-list">
                          {view.themes.slice(0, 5).map((t) => (
                            <button
                              key={t.topic}
                              onClick={() => {
                                setTopic(t.topic);
                                navigate('activity');
                              }}
                            >
                              <span>{topicLabel(t.topic)}</span>
                              <div className="theme-track">
                                <span
                                  style={{
                                    width: `${(t.count / Math.max(1, view.themes[0]?.count || 0)) * 100}%`,
                                  }}
                                />
                              </div>
                              <strong>{t.count}</strong>
                            </button>
                          ))}
                        </div>
                      </Panel>
                      <Panel
                        title="Derniers contenus à consulter"
                        detail="Mentions publiques associées aux thématiques CCR"
                        action={
                          <button className="text-button" onClick={() => navigate('activity')}>
                            Tout voir
                            <ArrowUpRight size={15} />
                          </button>
                        }
                      >
                        {view.contents
                          .filter((c) => view.contentTopics.has(c.content_key))
                          .slice(0, 3)
                          .map((c) => (
                            <Article
                              key={c.content_key}
                              content={c}
                              topics={view.contentTopics.get(c.content_key) || []}
                              onTopic={(t) => {
                                setTopic(t);
                                navigate('activity');
                              }}
                            />
                          ))}
                        {!view.contents.some((c) => view.contentTopics.has(c.content_key)) && (
                          <Empty>Aucun contenu CCR sur cette période.</Empty>
                        )}
                      </Panel>
                    </div>
                  </>
                )}
                {page === 'personalities' && (
                  <Panel
                    title="Personnalités suivies"
                    detail="Scores du jour de référence ; volumes sur la période sélectionnée"
                  >
                    <div className="table-scroll">
                      <table className="person-table">
                        <thead>
                          <tr>
                            <th>Personnalité</th>
                            <th>Visibilité</th>
                            <th>Variation J-7</th>
                            <th>Articles</th>
                            <th>Vidéos</th>
                            <th>Pertinence CCR</th>
                            <th />
                          </tr>
                        </thead>
                        <tbody>
                          {view.ranking.map((p, i) => {
                            const personal = view.contents.filter((c) =>
                              view.contentPeople.get(c.content_key)?.includes(p.personality_id),
                            );
                            return (
                              <tr key={p.personality_id}>
                                <td>
                                  <button
                                    className="person-link"
                                    onClick={() => openBrief(p.personality_id)}
                                  >
                                    <Avatar name={p.name} index={i} />
                                    <div>
                                      <strong>{p.name}</strong>
                                      <small>Personnalité suivie</small>
                                    </div>
                                  </button>
                                </td>
                                <td>
                                  <span className="table-score">
                                    {score(p.metric?.visibility_score || 0)}
                                    <small>/100</small>
                                  </span>
                                </td>
                                <td>
                                  <Delta value={p.metric?.visibility_change_7d} />
                                </td>
                                <td>{personal.filter((c) => c.content_type === 'news').length}</td>
                                <td>
                                  {personal.filter((c) => c.content_type === 'youtube').length}
                                </td>
                                <td>
                                  <span className="relevance-pill">
                                    {score(p.metric?.ccr_relevance_score || 0)}
                                  </span>
                                </td>
                                <td>
                                  <button
                                    className="icon-button"
                                    aria-label={`Fiche de ${p.name}`}
                                    onClick={() => openBrief(p.personality_id)}
                                  >
                                    <ArrowUpRight size={17} />
                                  </button>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </Panel>
                )}
                {page === 'topics' && (
                  <>
                    <div className="topic-grid">
                      {view.themes.map((t, i) => (
                        <button
                          className="topic-card"
                          key={t.topic}
                          onClick={() => {
                            setTopic(t.topic);
                            navigate('activity');
                          }}
                        >
                          <div className={`topic-symbol topic-${i % 3}`}>
                            <Tags size={19} />
                          </div>
                          <ArrowUpRight size={16} className="topic-arrow" />
                          <h2>{topicLabel(t.topic)}</h2>
                          <strong>
                            {t.count}
                            <small> contenus</small>
                          </strong>
                          <p>{t.keywords.slice(0, 2).join(' · ')}</p>
                        </button>
                      ))}
                    </div>
                    <Panel
                      title="Personnalités × thématiques"
                      detail="Un contenu peut relever de plusieurs thèmes, sans être dupliqué"
                    >
                      <div className="table-scroll">
                        <table className="matrix">
                          <thead>
                            <tr>
                              <th>Personnalité</th>
                              {data.tables.topics.map((t) => (
                                <th key={t.topic}>{topicLabel(t.topic)}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {view.ranking.map((p) => (
                              <tr key={p.personality_id}>
                                <td>
                                  <button
                                    className="text-button"
                                    onClick={() => openBrief(p.personality_id)}
                                  >
                                    {p.name}
                                  </button>
                                </td>
                                {data.tables.topics.map((t) => {
                                  const count = view.contents.filter(
                                    (c) =>
                                      view.contentPeople
                                        .get(c.content_key)
                                        ?.includes(p.personality_id) &&
                                      view.contentTopics.get(c.content_key)?.includes(t.topic),
                                  ).length;
                                  return (
                                    <td key={t.topic}>
                                      <button
                                        className={`matrix-cell ${count ? 'has-value' : ''}`}
                                        style={{
                                          backgroundColor: count
                                            ? `rgba(18,116,97,${Math.min(0.7, 0.1 + count * 0.1)})`
                                            : undefined,
                                          color: count > 3 ? '#fff' : undefined,
                                        }}
                                        onClick={() => {
                                          setPersonId(p.personality_id);
                                          setTopic(t.topic);
                                          navigate('activity');
                                        }}
                                        aria-label={`${p.name}, ${topicLabel(t.topic)} : ${count} contenus`}
                                      >
                                        {count || '—'}
                                      </button>
                                    </td>
                                  );
                                })}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </Panel>
                  </>
                )}
                {page === 'activity' && (
                  <Panel
                    title="Fil d’actualité"
                    detail={`${activity.length} contenus uniques correspondant aux filtres`}
                  >
                    <div className="activity-filters">
                      <label className="search-input">
                        <Search size={17} />
                        <input
                          aria-label="Rechercher un contenu"
                          placeholder="Rechercher un titre, un sujet, une source…"
                          value={search}
                          onChange={(e) => setSearch(e.target.value)}
                        />
                      </label>
                      <select
                        aria-label="Thématique"
                        value={topic}
                        onChange={(e) => setTopic(e.target.value)}
                      >
                        <option value="all">Tous les thèmes</option>
                        {data.tables.topics.map((t) => (
                          <option key={t.topic} value={t.topic}>
                            {topicLabel(t.topic)}
                          </option>
                        ))}
                      </select>
                      <select
                        aria-label="Type de contenu"
                        value={kind}
                        onChange={(e) => setKind(e.target.value)}
                      >
                        <option value="all">Articles & vidéos</option>
                        <option value="news">Articles</option>
                        <option value="youtube">Vidéos</option>
                      </select>
                    </div>
                    <div className="activity-list">
                      {activity.slice(0, 200).map((c) => (
                        <div key={c.content_key} className="activity-item">
                          <Article
                            content={c}
                            topics={view.contentTopics.get(c.content_key) || []}
                            onTopic={setTopic}
                          />
                          <div className="mention-row">
                            {(view.contentPeople.get(c.content_key) || []).map((id) => (
                              <button key={id} onClick={() => openBrief(id)}>
                                <UsersRound size={12} />
                                {view.people.find((p) => p.personality_id === id)?.name || id}
                              </button>
                            ))}
                            {c.content_type === 'youtube' && (
                              <span className="muted">
                                {c.view_count == null
                                  ? 'Vues inconnues'
                                  : `${number(c.view_count)} vues cumulées`}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                    {activity.length > 200 && (
                      <p className="chart-footnote">
                        Affichage limité aux 200 contenus les plus récents. Les exports contiennent
                        le corpus complet.
                      </p>
                    )}
                    {!activity.length && <Empty>Aucun contenu ne correspond à ces filtres.</Empty>}
                  </Panel>
                )}
                {page === 'brief' && brief && (
                  <div className="brief">
                    <div className="brief-hero">
                      <Avatar name={brief.name} />
                      <div>
                        <div className="eyebrow">
                          FICHE RENCONTRE · {formatDate(data.as_of, { year: 'numeric' })}
                        </div>
                        <h2>{brief.name}</h2>
                        <p>Repères issus des contenus qui mentionnent cette personnalité.</p>
                      </div>
                      <button
                        className="button secondary print-button"
                        onClick={() => window.print()}
                      >
                        <Printer size={16} />
                        Imprimer la fiche
                      </button>
                    </div>
                    <div className="brief-kpis">
                      <div>
                        <span>Visibilité du jour</span>
                        <strong>
                          {score(brief.visibility_score)}
                          <small>/100</small>
                        </strong>
                        <Delta value={brief.visibility_change_7d} />
                      </div>
                      <div>
                        <span>Pertinence CCR</span>
                        <strong>
                          {score(brief.ccr_relevance_score)}
                          <small>/100</small>
                        </strong>
                        <small>Thèmes détectés sur la fenêtre de collecte</small>
                      </div>
                      <div>
                        <span>Articles récents</span>
                        <strong>{brief.news_count_recent}</strong>
                        <small>{brief.brief_days} derniers jours</small>
                      </div>
                      <div>
                        <span>Vidéos récentes</span>
                        <strong>{brief.youtube_video_count_recent}</strong>
                        <small>{brief.brief_days} derniers jours</small>
                      </div>
                    </div>
                    <Panel
                      title="Sujets CCR récemment abordés"
                      detail={`Thèmes des contenus mentionnant la personnalité · ${brief.brief_days} jours`}
                    >
                      <div className="brief-topics">
                        {brief.top_5_topics.length ? (
                          brief.top_5_topics.map((t) => (
                            <button
                              className="tag large"
                              key={t}
                              onClick={() => {
                                setTopic(t);
                                navigate('activity');
                              }}
                            >
                              {topicLabel(t)}
                              <ArrowUpRight size={13} />
                            </button>
                          ))
                        ) : (
                          <p className="muted">
                            Aucun thème CCR détecté dans les contenus récents.
                          </p>
                        )}
                      </div>
                    </Panel>
                    <div className="overview-bottom">
                      {(['news', 'youtube'] as const).map((type) => (
                        <Panel
                          key={type}
                          title={type === 'news' ? 'Derniers articles' : 'Dernières vidéos'}
                          detail={`Jusqu’à 5 contenus · ${brief.brief_days} jours`}
                        >
                          {view.contents
                            .filter(
                              (c) =>
                                c.content_type === type &&
                                view.contentPeople
                                  .get(c.content_key)
                                  ?.includes(brief.personality_id) &&
                                (new Date(data.as_of).getTime() - new Date(c.date).getTime()) /
                                  86_400_000 <
                                  brief.brief_days,
                            )
                            .slice(0, 5)
                            .map((c) => (
                              <Article
                                key={c.content_key}
                                content={c}
                                topics={view.contentTopics.get(c.content_key) || []}
                              />
                            ))}
                          {!view.contents.some(
                            (c) =>
                              c.content_type === type &&
                              view.contentPeople
                                .get(c.content_key)
                                ?.includes(brief.personality_id) &&
                              (new Date(data.as_of).getTime() - new Date(c.date).getTime()) /
                                86_400_000 <
                                brief.brief_days,
                          ) && <Empty>Aucun contenu récent de ce type.</Empty>}
                        </Panel>
                      ))}
                    </div>
                    <div className="brief-disclaimer">
                      <ShieldCheck size={20} />
                      <p>
                        Une mention dans un article ne prouve pas une prise de parole ou une
                        adhésion au propos. Vérifier les sources avant un échange institutionnel.
                      </p>
                    </div>
                  </div>
                )}
                {page === 'brief' && !brief && (
                  <Empty>Aucune fiche disponible pour la sélection.</Empty>
                )}
                {page === 'sources' && (
                  <>
                    <div className="source-header">
                      <div>
                        <span className="status-dot" /> Dernière publication :{' '}
                        {formatDate(data.updated_at || data.generated_at, {
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                          timeZone: 'Europe/Paris',
                        })}
                      </div>
                      <button
                        className="button primary"
                        onClick={() => {
                          setCollectMessage('');
                          setCollectOpen(true);
                        }}
                        disabled={mode === 'demo' || waitingRevision != null}
                      >
                        <Play size={15} />
                        Lancer une collecte réelle
                      </button>
                    </div>
                    <div className="source-grid">
                      {data.sources.map((s) => (
                        <div className="source-card" key={s.source}>
                          <div>
                            <Database size={22} />
                            <span className={`status-pill ${s.status === 'ok' ? 'ok' : 'warning'}`}>
                              {(
                                {
                                  ok: 'Disponible',
                                  disabled: 'Désactivée',
                                  skipped_missing_key: 'Clé absente',
                                  failed: 'Indisponible',
                                  partial: 'Partielle',
                                  quota_limited: 'Quota limité',
                                  not_configured: 'À configurer',
                                } as Record<string, string>
                              )[s.status] || s.status}
                            </span>
                          </div>
                          <h2>{s.source}</h2>
                          <p>
                            {number(s.content_count)} contenus retournés · {s.errors} erreur
                            {s.errors > 1 ? 's' : ''}
                          </p>
                        </div>
                      ))}
                    </div>
                    <div className="overview-bottom">
                      <Panel
                        title="Score de visibilité"
                        detail="Un indicateur de couverture médiatique observée"
                      >
                        <div className="method-list">
                          <div>
                            <span>Volume d’articles</span>
                            <strong>35 %</strong>
                          </div>
                          <div>
                            <span>Vues YouTube cumulées</span>
                            <strong>30 %</strong>
                          </div>
                          <div>
                            <span>Likes + commentaires agrégés</span>
                            <strong>15 %</strong>
                          </div>
                          <div>
                            <span>Fréquence des publications</span>
                            <strong>20 %</strong>
                          </div>
                        </div>
                        <p className="method-note">
                          Chaque composante est normalisée parmi les personnalités suivies le même
                          jour. Une source absente ne redistribue pas ses poids. Les vues sont
                          rattachées au jour de publication, pas au jour où elles ont été reçues.
                          Les poids affichés sont les valeurs par défaut ; consulter la
                          configuration du pipeline pour les paramètres utilisés.
                        </p>
                      </Panel>
                      <Panel
                        title="Pertinence institutionnelle CCR"
                        detail="Une lecture des thèmes présents dans le corpus"
                      >
                        <div className="method-list">
                          <div>
                            <span>Volume de contenus CCR</span>
                            <strong>50 %</strong>
                          </div>
                          <div>
                            <span>Diversité des thématiques</span>
                            <strong>30 %</strong>
                          </div>
                          <div>
                            <span>Récence des contenus</span>
                            <strong>20 %</strong>
                          </div>
                        </div>
                        <p className="method-note">
                          Classification par mots-clés dans les titres et descriptions. Le score
                          n’identifie pas une prise de position. Les sources restent nécessaires à
                          toute interprétation.
                        </p>
                      </Panel>
                    </div>
                    <div className="notice">
                      <ShieldCheck size={19} />
                      <p>
                        Ce projet ne profile aucun citoyen, abonné ou commentateur. Les scores ne
                        sont ni un sondage ni une mesure de popularité électorale.
                      </p>
                    </div>
                  </>
                )}
              </>
            )
          )}
          <footer className="page-footer">
            <span>
              CCR · Veille 2027 <i /> Prototype de veille institutionnelle
            </span>
            <div>
              <button
                onClick={() => {
                  setMode(mode === 'live' ? 'demo' : 'live');
                  setPersonId('all');
                }}
              >
                {mode === 'live' ? 'Aperçu fictif' : 'Données réelles'}
                <ArrowUpRight size={12} />
              </button>
              <span>Sources publiques uniquement</span>
            </div>
          </footer>
        </main>
      </div>
      {exportOpen && data && (
        <div className="modal-backdrop" onClick={() => setExportOpen(false)}>
          <section
            className="modal export-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="export-title"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="icon-button close-modal"
              aria-label="Fermer les exports"
              onClick={() => setExportOpen(false)}
            >
              <X size={19} />
            </button>
            <div className="modal-icon">
              <Download size={24} />
            </div>
            <h2 id="export-title">Exports pour Power BI</h2>
            <p>
              Corpus publié complet · UTF-8 · Séparateur virgule ·{' '}
              {mode === 'demo' ? 'DEMO / FICTIF' : 'Données réelles'}
            </p>
            <div className="export-list">
              {Object.keys(data.tables).map((table) => (
                <button key={table} onClick={() => csvDownload(data, table)}>
                  <FileText size={17} />
                  <div>
                    <strong>{table}.csv</strong>
                    <small>{number(data.tables[table].length)} lignes</small>
                  </div>
                  <Download size={16} />
                </button>
              ))}
            </div>
          </section>
        </div>
      )}
      {collectOpen && (
        <div
          className="modal-backdrop"
          onClick={() => {
            setCollectOpen(false);
            setAdminKey('');
          }}
        >
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="collect-title"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="icon-button close-modal"
              aria-label="Fermer la collecte"
              onClick={() => {
                setCollectOpen(false);
                setAdminKey('');
              }}
            >
              <X size={19} />
            </button>
            <div className="modal-icon">
              <RefreshCw size={24} />
            </div>
            <h2 id="collect-title">Lancer une collecte réelle</h2>
            <p>
              Le pipeline Python s’exécute dans GitHub Actions. Le site relira les résultats après
              leur publication dans Supabase.
            </p>
            <label className="admin-label">
              Clé opérateur
              <input
                type="password"
                autoComplete="off"
                value={adminKey}
                onChange={(e) => setAdminKey(e.target.value)}
                placeholder="Clé définie dans COLLECT_ADMIN_KEY"
              />
            </label>
            <button
              className="button primary full"
              onClick={triggerCollection}
              disabled={!adminKey || collectBusy}
            >
              {collectBusy ? <LoaderCircle className="spin" size={16} /> : <Play size={16} />}
              Demander la collecte
            </button>
            {collectMessage && (
              <p className="collect-message" role="status">
                {collectMessage}
              </p>
            )}
            <a
              className="text-button workflow-link"
              href="https://github.com/bouboukane33/veille-2027/actions/workflows/collect.yml"
              target="_blank"
              rel="noopener noreferrer"
            >
              Ouvrir GitHub Actions
              <ExternalLink size={13} />
            </a>
          </section>
        </div>
      )}
    </div>
  );
}

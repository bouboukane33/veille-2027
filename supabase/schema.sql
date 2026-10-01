-- Exécuter une fois dans le SQL Editor du projet Supabase.
-- Aucun accès anonyme à l'archive. Seuls Python et les fonctions Vercel utilisent la clé serveur.
CREATE TABLE IF NOT EXISTS public.ccr_snapshots (
    id text PRIMARY KEY CHECK (id = 'live'),
    revision bigint NOT NULL CHECK (revision > 0),
    dataset jsonb NOT NULL,
    tables jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.ccr_snapshots ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.ccr_snapshots FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON public.ccr_snapshots TO service_role;

CREATE OR REPLACE FUNCTION public.publish_ccr_snapshot(
    dataset_json jsonb, tables_json jsonb, expected_revision bigint
) RETURNS bigint LANGUAGE plpgsql SECURITY INVOKER SET search_path = public AS $$
DECLARE new_revision bigint;
BEGIN
    IF dataset_json->>'mode' IS DISTINCT FROM 'live' OR expected_revision < 0 THEN
        RAISE EXCEPTION 'Publication réelle et révision valide requises';
    END IF;
    IF EXISTS (
        SELECT 1 FROM jsonb_each(tables_json) t,
        LATERAL jsonb_array_elements(t.value) r
        WHERE r->>'is_demo' IN ('1', 'true')
    ) OR EXISTS (
        SELECT 1 FROM jsonb_each(dataset_json->'tables') t,
        LATERAL jsonb_array_elements(t.value) r
        WHERE r->>'is_demo' IN ('1', 'true')
    ) THEN
        RAISE EXCEPTION 'Données fictives refusées';
    END IF;
    INSERT INTO public.ccr_snapshots (id, revision, dataset, tables)
    VALUES ('live', expected_revision + 1, dataset_json, tables_json)
    ON CONFLICT (id) DO UPDATE SET
        revision = ccr_snapshots.revision + 1,
        dataset = EXCLUDED.dataset, tables = EXCLUDED.tables, updated_at = now()
    WHERE ccr_snapshots.revision = expected_revision
    RETURNING revision INTO new_revision;
    IF new_revision IS NULL THEN
        RAISE EXCEPTION 'Révision périmée : restaurer avant de publier' USING ERRCODE = '40001';
    END IF;
    RETURN new_revision;
END;
$$;
REVOKE ALL ON FUNCTION public.publish_ccr_snapshot(jsonb, jsonb, bigint) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.publish_ccr_snapshot(jsonb, jsonb, bigint) TO service_role;

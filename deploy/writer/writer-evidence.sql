-- One consistent, read-only view. Only return evidence available in this snapshot.
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '30s';

SELECT json_build_object(
  'through', transaction_timestamp(),
  'claims', COALESCE((
    SELECT json_agg(json_build_object(
      'at', c.created_at, 'surfaces', c.surfaces, 'url', s.canonical_url,
      'class', s.source_class, 'topic', c.topic, 'status', c.status,
      'statement', left(c.statement, 1200)
    ) ORDER BY c.created_at DESC, c.claim_id)
    FROM claim c JOIN study s USING (study_id)
  ), '[]'::json),
  'events', COALESCE((
    SELECT json_agg(json_build_object(
      'at', observed_at, 'surfaces', surfaces, 'type', event_type,
      'urls', payload::jsonb->'evidence_urls',
      'statement', left(payload::jsonb->>'description', 1200)
    ) ORDER BY observed_at DESC, id)
    FROM change_event
  ), '[]'::json),
  'captures', COALESCE((
    SELECT json_agg(json_build_object(
      'at', observed_at, 'url', canonical_url, 'hash', capture_hash,
      'class', source_class, 'statement', left(excerpt, 1200)
    ) ORDER BY observed_at DESC, id)
    FROM evidence_item
    WHERE validation_status = 'validated' AND http_status BETWEEN 200 AND 299
  ), '[]'::json)
);
COMMIT;

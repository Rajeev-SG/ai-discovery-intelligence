# Pipeline assets

Dagster should model these as explicit assets/dependencies rather than one monolithic script.

1. `surface_registry`
2. `source_registry`
3. `feed_items`
4. `discovered_urls`
5. `evidence_snapshots`
6. `parsed_documents`
7. `studies`
8. `claims`
9. `claim_relationships`
10. `change_events`
11. `confidence_scores`
12. `significance_scores`
13. `observation_plane_export`
14. `weekly_exec_brief`
15. `current_pov`
16. `pov_changelog`
17. `source_health`
18. `coverage_gaps`

## Scheduling intent

- known high-value feeds/pages: daily or source-appropriate checks;
- broad discovery queries: daily/weekly depending signal quality;
- full source-health and coverage audit: weekly;
- executive brief: weekly after materiality scoring;
- POV regeneration: event-driven when a qualifying material claim changes, with weekly validation.

Do not run an LLM over the entire corpus every week. Use hashes/change events to process only new or changed evidence.

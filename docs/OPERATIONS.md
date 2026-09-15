# Operations

## Health signals

Track:

- source fetch success/failure and status code;
- extraction completeness;
- changedetection watch health;
- feed staleness;
- claims produced per source;
- evidence without methodology metadata;
- surfaces with no recent verification;
- source concentration by claim;
- unresolved contradictions;
- weekly brief item count;
- pipeline runtime/failures.

## Existing observability

Use Dagster's run/asset UI and integrate with the user's existing Grafana/OTEL stack where useful. Do not create a bespoke monitoring dashboard before these are insufficient.

## Failure philosophy

A failed source must become visible in source health and should not silently freeze an old claim as “current”. Old claims need `last_verified` and staleness rules.

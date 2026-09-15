# 05 — Turn source deltas into material AI-discovery change events

## Outcome
Move from a pile of articles to a dated intelligence changelog.

## Requirements
- Use changedetection.io/source hashes to identify changed or new evidence and reprocess only affected assets.
- Emit append-only typed change events linked to claims and surfaces.
- Track `observed_at`, `published_at`, and `effective_from` separately.
- Deduplicate syndicated/repeated coverage of the same underlying change.
- Distinguish product launch, retrieval/index change, audience shift, citation/source shift, crawler policy, commerce/ads, referral/measurement and correction/retraction.
- Render a change timeline per surface and global latest-changes view.

## Real product proof required
Show at least five real dated events from the free evidence corpus across at least three surfaces, including one event that updates/qualifies an earlier event. The output must link back to evidence and claims.

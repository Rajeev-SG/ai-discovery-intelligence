# 03 — Build the atomic evidence/claim ledger with methodology capture

## Outcome
Convert source documents into auditable atomic claims without losing study methodology.

## Adopted stack
PostgreSQL + SQLAlchemy/Alembic + Pydantic. Use deterministic parsers for structured sources; when prose requires LLM extraction, use Instructor + Pydantic structured output against the configured OpenRouter-compatible model rather than hand-written parser/retry plumbing.

## Data requirements
For each study/claim retain: source ID, publisher, URL, publication date, observed date, geography/language, surfaces, prompt/query universe, sample size, metric definition, time window, methodology notes, exact evidence locator where practical, source hash, extraction version and claim status.

Claims must be atomic and typed: audience/usage, retrieval/index behaviour, citations/sources, crawler/index policy, referrals/conversion, commerce/ads, measurement, optimisation implication.

LLM extraction is never evidence. Every extracted field must be traceable to the source; unsupported required fields stay unknown.

## Real product proof required
Create and render at least three real claim records:
1. a Similarweb audience/traffic claim;
2. a citation/source claim from Peec/SISTRIX/Ahrefs/Semrush;
3. a regional claim about China, NAVER or Yandex.

The expanded observation/evidence view must show each claim's methodology and provenance, not only its summarised sentence.

# Product-proof acceptance standard

Every implementation issue must show a real user-visible or analyst-visible result.

## Required proof examples

- a rendered observation row containing real evidence;
- a source page successfully ingested with its extracted methodology;
- a real claim and evidence relationship;
- a real conflicting-evidence example and reconciliation;
- a real dated change timeline;
- a generated weekly brief from current data;
- an actual POV diff with evidence IDs;
- a source-health/gap report;
- a deployed URL plus screenshot/E2E assertion.

## Forbidden completion pattern

Do not close an issue with only:

- unit-test counts;
- “service is running”;
- database schema screenshots;
- pipeline DAG screenshots;
- empty UI scaffolds;
- synthetic-only fixtures.

Fixtures are required for deterministic tests, but acceptance proof must additionally use real public evidence.

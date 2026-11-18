# ADR 0001 — Claude Code as the field-guide writer, gated by deterministic checks

Status: accepted (issue #75)
Date: 2026-11-18

## Context

The live field guide (`https://rajeev.com/solutions/ai-discovery`) is 20
hand-written YAML files in `web/content/surfaces/*.yaml` plus
`web/content/coming-soon.json`. The daily acquisition job
(`deploy/oracle`, Dagster → Crawl4AI → claim ledger in Hetzner Postgres) keeps
producing verified, quote-backed evidence for those surfaces, but nothing ever
moved that evidence into the pages. Every guide therefore ages silently: the
`checked:` dates say when a human last looked, not when the product last looked.

The owner has authorised auto-publishing when checks pass, provided a change
that cannot be checked does not publish.

This ADR covers the writer subsystem in `deploy/writer/`, which is roughly 700
lines of orchestration. Rule 6 of `AGENTS.md` requires an ADR for a new generic
subsystem of that size; this is that record.

## Decision

Run the official Claude Code CLI headless on the Oracle VPS as the writer, and
put every decision that can be made deterministically *outside* the model.

1. **Change detection is deterministic and model-free** (`writer-changes.mjs`).
   Per surface it detects ledger claims and change events new since that
   surface's last successful write, source captures whose content hash changed
   since the previous capture, listed sources not re-checked in 30 days, and
   Coming-soon surfaces whose evidence now clears a fixed promotion bar. No
   signal means no call. This is the main cost control: the subscription has
   limits the owner also uses interactively.
2. **The model only writes prose.** One `claude -p` call per changed surface,
   `--restricted` with `WebFetch` as its only tool, `--model sonnet`, a cwd
   limited to a dedicated checkout, and structured output of
   `{yaml, changelog}`. It re-fetches the sources it relies on; the orchestrator
   checks the fetch transcript, so a URL it did not actually fetch cannot carry
   an attribution.
3. **Gates are deterministic and fail closed** (`writer-gates.mjs`): YAML
   schema, seven mechanics labels in fixed order, length budgets, a banned-word
   list that keeps acquisition vocabulary out of published prose, every source
   URL resolves 2xx (connect-timeout, SSRF-checked by resolving to a public IPv4
   first), and every new or changed statement named in a structured
   `attributions` field that points only at freshly checked sources.
4. **Publishing goes through the repository's own guards.** The writer opens a
   PR; the existing `web-ci` workflow runs typecheck, Vitest, `next build` and
   Playwright; the owner's `merge-guard.sh` decides the merge. A large diff
   (>80 changed YAML lines) or a newly promoted surface never auto-merges and
   waits for the owner.

## Why not the alternatives

**Alternative 1 — a scheduled GitHub Action running the writer.** Rejected
because the evidence it needs is not reachable from GitHub: the ledger is a
private Hetzner Postgres behind a tailnet-only SSH tunnel, and the acquisition
captures live on the Oracle box. Replicating either into Actions would mean
exposing durable private state to a third party and paying for runner minutes
per call. The Oracle box already holds the credentials and the tunnel.

**Alternative 2 — deterministic templating, no model.** Rejected for output
quality, not capability. The ledger yields structured claims (crawler names,
blocking behaviour, measurement tags), so a template could rewrite the
mechanics table. It cannot write the part that makes the page worth reading:
which of five possible actions matters for a media buyer, in what order, and
why. The owner's exemplar (`web/content/surfaces/chatgpt.yaml`) is editorial
prose, and a template that produced it would be a harder, larger program than
the writer plus its gates.

**Alternative 3 — the owner's own agent harness (Codex/OpenCode) on the box.**
Rejected because those are interactive multi-tenant harnesses with their own
config drift, and the owner's Claude subscription is the credential that was
authorised for this. A pinned `@anthropic-ai/claude-code@2.1.327` in
`/opt/adi-writer/tools` is a smaller, reproducible dependency.

## Consequences and accepted risks

- **Automated review substitutes for human review at the merge boundary.** The
  repository guard requires review-pro evidence for YAML changes. Rather than
  disable it, the writer runs a second, independent Claude pass over the exact
  head diff (`docs/WRITER_REVIEW.md`) with no tools, records its verdict through
  the guard's own `record` command, and merges only if the guard then returns 0.
  This is a real review of the patch but it is not a human, and it shares a
  model family with the author. The deterministic gates are therefore treated
  as the primary control, not the review. Changes over 80 lines and all
  promotions skip this path entirely and wait for the owner.
- **A silent writer is indistinguishable from an idle writer.** A run with no
  changes posts "No changes." to the rolling issue, so silence means the timer
  or the service failed, not that nothing happened. Failures exit non-zero and
  fire `adi-alert@`.
- **Evidence freshness is bounded by acquisition.** The writer refuses to run
  unless acquisition produced a successful run within 48 hours, so a pipeline
  outage cannot be papered over with fresh-looking prose.
- **Prompt-injection surface.** Sources are treated as data, the prompt says so,
  and the model's only tool is a domain-scoped WebFetch. It cannot write files,
  run commands, or reach a host that was not in the evidence.

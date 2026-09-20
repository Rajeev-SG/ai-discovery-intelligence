/**
 * Client-safe POV projection: types, helpers and normalisation. Contains no
 * Node built-ins, so client components can import it freely.
 *
 * Canonical state lives in `pov/state.yaml`; the committed product artifact
 * (`web/lib/generated-pov.json`) is produced by `scripts/build_web_pov.py`,
 * which projects that state through the canonical, tested domain model
 * (`ai_discovery.pov`). Derived fields — `confidence`, `contested` and the
 * unresolved state — are computed by that model and rendered here **verbatim**.
 * This module never re-derives them: doing so would fork the single source of
 * truth and let the UI disagree with the generator and changelog.
 *
 * The fs/env loader (`loadPov`) lives in `web/lib/pov.server.ts`.
 */

export type ConfidenceLabel =
  | "high"
  | "medium_high"
  | "medium"
  | "low"
  | "unresolved";

export interface PovEvidence {
  slot: string;
  polarity: "supporting" | "contradicting";
  text: string;
  claim_id: string;
  event_id: string;
  confidence: ConfidenceLabel;
  value_number: number | null;
  value_text: string | null;
  effective_at: string | null;
  added_at: string | null;
}

export interface PovProposition {
  id: string;
  section: string;
  base_text: string;
  topics: string[];
  /** Canonical confidence from the POV gate; rendered verbatim. */
  confidence: ConfidenceLabel;
  /** Canonical contested flag from the POV domain model; rendered verbatim. */
  contested: boolean;
  last_reviewed: string | null;
  supporting: PovEvidence[];
  contradicting: PovEvidence[];
}

export interface PovRevision {
  proposition_id: string;
  changed_at: string;
  reason: string;
  event_id: string;
  evidence_ids: string[];
  old_statement: string;
  new_statement: string;
  significance: number;
  confidence: string;
}

export interface PovView {
  source: string;
  version: number;
  /**
   * The canonical proposition id set from `pov/state.yaml`, emitted by the
   * generator. Used to assert artifact<->state parity without parsing YAML in
   * the web test suite.
   */
  canonical_ids: string[];
  propositions: PovProposition[];
  /** Chronological (oldest first) so the change history reads as a timeline. */
  changelog: PovRevision[];
}

/** Human label for a confidence value; unresolved states read as "unresolved". */
export const CONFIDENCE_LABELS: Record<ConfidenceLabel, string> = {
  high: "High",
  medium_high: "Medium-high",
  medium: "Medium",
  low: "Low",
  unresolved: "Unresolved",
};

/**
 * True when the canonical gate reports the proposition as unresolved. Rendered
 * verbatim from the artifact's `confidence`; no evidence-count re-derivation.
 */
export function isUnresolved(proposition: PovProposition): boolean {
  return proposition.confidence === "unresolved";
}

/**
 * True when the canonical model flags the proposition as contested. Rendered
 * verbatim from the artifact's `contested` flag.
 */
export function isContested(proposition: PovProposition): boolean {
  return proposition.contested;
}

/**
 * "No POV change" is a valid outcome: an empty changelog means the gate adopted
 * nothing. The UI must say so rather than fabricate churn.
 */
export function hasChanges(view: PovView): boolean {
  return view.changelog.length > 0;
}

/** Format an ISO timestamp as its UTC date (deterministic across clients). */
export function formatDate(iso: string | null): string {
  if (!iso) return "not yet reviewed";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toISOString().slice(0, 10);
}

/** Format an ISO timestamp as a UTC date-time (minute precision). */
export function formatDateTime(iso: string | null): string {
  if (!iso) return "not yet reviewed";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toISOString().slice(0, 16).replace("T", " ") + " UTC";
}

/**
 * Link an evidence/claim id to the observation-plane evidence drill-down, which
 * now lives at `/surfaces` (issue #45 moved the registry off the root).
 */
export function evidenceHref(claimId: string): string {
  return `/surfaces?evidence=${encodeURIComponent(claimId)}`;
}

function asEvidence(raw: unknown): PovEvidence {
  const value = (raw ?? {}) as Partial<PovEvidence>;
  return {
    slot: value.slot ?? "",
    polarity: value.polarity === "contradicting" ? "contradicting" : "supporting",
    text: value.text ?? "",
    claim_id: value.claim_id ?? "",
    event_id: value.event_id ?? "",
    confidence: (value.confidence ?? "unresolved") as ConfidenceLabel,
    value_number: value.value_number ?? null,
    value_text: value.value_text ?? null,
    effective_at: value.effective_at ?? null,
    added_at: value.added_at ?? null,
  };
}

function asProposition(raw: unknown): PovProposition {
  const value = (raw ?? {}) as Partial<PovProposition>;
  return {
    id: value.id ?? "",
    section: value.section ?? "",
    base_text: value.base_text ?? "",
    topics: value.topics ?? [],
    confidence: (value.confidence ?? "unresolved") as ConfidenceLabel,
    // Verbatim from the artifact — the canonical model decides contested state.
    contested: Boolean(value.contested),
    last_reviewed: value.last_reviewed ?? null,
    supporting: (value.supporting ?? []).map(asEvidence),
    contradicting: (value.contradicting ?? []).map(asEvidence),
  };
}

function asRevision(raw: unknown): PovRevision {
  const value = (raw ?? {}) as Partial<PovRevision>;
  return {
    proposition_id: value.proposition_id ?? "",
    changed_at: value.changed_at ?? "",
    reason: value.reason ?? "",
    event_id: value.event_id ?? "",
    evidence_ids: value.evidence_ids ?? [],
    old_statement: value.old_statement ?? "",
    new_statement: value.new_statement ?? "",
    significance: value.significance ?? 0,
    confidence: value.confidence ?? "unresolved",
  };
}

/**
 * Validate and normalise a raw POV artifact into a {@link PovView}. Pure, no
 * filesystem access, so tests can project arbitrary states (unresolved,
 * contested, changed) without touching disk.
 */
export function projectPov(raw: unknown): PovView {
  const value = (raw ?? {}) as Partial<PovView>;
  const propositions = (value.propositions ?? []).map(asProposition);
  if (!propositions.length) throw new Error("no POV propositions in artifact");
  const changelog = (value.changelog ?? [])
    .map(asRevision)
    .sort((a, b) => a.changed_at.localeCompare(b.changed_at));
  const ids = propositions.map((p) => p.id);
  if (new Set(ids).size !== ids.length) throw new Error("duplicate POV proposition ids");
  const canonicalIds = value.canonical_ids ?? propositions.map((p) => p.id);
  if (!canonicalIds.length) throw new Error("no canonical_ids in POV artifact");
  return {
    source: value.source ?? "pov/state.yaml",
    version: value.version ?? 1,
    canonical_ids: canonicalIds,
    propositions,
    changelog,
  };
}

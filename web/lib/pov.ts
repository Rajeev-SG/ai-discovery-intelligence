import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import generated from "./generated-pov.json";

/**
 * Client-safe shape of the POV product artifact.
 *
 * The committed artifact (`web/lib/generated-pov.json`) is produced by
 * `scripts/build_web_pov.py`, which projects `pov/state.yaml` through the
 * canonical, tested domain model (`ai_discovery.pov`). Derived fields —
 * `confidence` and `contested` — are therefore already computed by that model,
 * so the web app never re-implements the deterministic POV gate in TypeScript.
 * `pov/state.yaml` stays canonical; CI enforces the artifact is current.
 *
 * The Next app deploys from `web/` alone (Vercel), where `../pov` is absent, so
 * the committed JSON is the product read contract.
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
  confidence: ConfidenceLabel;
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

/** True when a proposition has no supporting evidence (confidence unresolved). */
export function isUnresolved(proposition: PovProposition): boolean {
  return proposition.confidence === "unresolved" && proposition.supporting.length === 0;
}

/** True when any proposition carries contradicting evidence. */
export function isContested(proposition: PovProposition): boolean {
  return proposition.contested || proposition.contradicting.length > 0;
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

/** Link an evidence/claim id to the observation-plane evidence drill-down. */
export function evidenceHref(claimId: string): string {
  return `/?evidence=${encodeURIComponent(claimId)}`;
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
  const supporting = (value.supporting ?? []).map(asEvidence);
  const contradicting = (value.contradicting ?? []).map(asEvidence);
  return {
    id: value.id ?? "",
    section: value.section ?? "",
    base_text: value.base_text ?? "",
    topics: value.topics ?? [],
    confidence: (value.confidence ?? "unresolved") as ConfidenceLabel,
    contested: Boolean(value.contested) || contradicting.length > 0,
    last_reviewed: value.last_reviewed ?? null,
    supporting,
    contradicting,
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
  return {
    source: value.source ?? "pov/state.yaml",
    version: value.version ?? 1,
    propositions,
    changelog,
  };
}

/** The canonical committed artifact path, relative to the `web/` project root. */
const ARTIFACT_PATH = path.join(process.cwd(), "lib", "generated-pov.json");

/**
 * Load the POV product view. Server-only (reads the filesystem when an override
 * is used). Precedence:
 *  1. `POV_PATH` (explicit override, must point at a generated JSON artifact);
 *  2. the committed `web/lib/generated-pov.json` imported at build time.
 *
 * The artifact is the product contract and is kept current by CI, so local dev
 * and the deployed `web/`-root build read the same data. We deliberately do not
 * read `pov/state.yaml` here: re-deriving confidence in TypeScript would fork
 * the deterministic gate, and the artifact is the tested project of it.
 */
export function loadPov(): PovView {
  const override = process.env.POV_PATH;
  if (override && existsSync(override)) {
    return projectPov(JSON.parse(readFileSync(override, "utf8")));
  }
  return projectPov(generated);
}

export { ARTIFACT_PATH };

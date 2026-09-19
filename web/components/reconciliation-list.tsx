/**
 * Renders the full persisted reconciliation ledger (issue #47). Relationships
 * are grouped by their canonical state category so contested and incomparable
 * findings stay visually distinct without exaggerating them. Every original
 * claim is preserved — this view never merges sides into one statement.
 */
import { ReconciliationRelationship } from "@/components/reconciliation-relationship";
import type { StateCategory, ResolvedRelationship } from "@/lib/reconciliation";

const CATEGORY_ORDER: StateCategory[] = ["conflict", "temporal", "incomparable", "unresolved", "compatible"];

const CATEGORY_TITLE: Record<StateCategory, string> = {
  conflict: "Contested",
  temporal: "Temporal updates",
  incomparable: "Contextually different (not comparable)",
  unresolved: "Unresolved",
  compatible: "Agreement",
};

const CATEGORY_NOTE: Record<StateCategory, string> = {
  conflict: "Findings directly disagree on the same quantity.",
  temporal: "Later evidence updates or supersedes earlier evidence; both remain inspectable.",
  incomparable: "Measured differently, so the numbers should not be read as the same quantity.",
  unresolved: "Missing methodology — neither agreement nor contradiction can be concluded.",
  compatible: "Findings support one another.",
};

export function ReconciliationList({ relationships }: { relationships: ResolvedRelationship[] }) {
  const present = CATEGORY_ORDER.filter((category) =>
    relationships.some((r) => r.category === category),
  );

  return (
    <div className="recon-groups">
      {present.map((category) => {
        const items = relationships.filter((r) => r.category === category);
        return (
          <section key={category} className={`recon-group recon-group-${category}`} aria-labelledby={`recon-${category}`}>
            <div className="recon-group-head">
              <h2 id={`recon-${category}`}>{CATEGORY_TITLE[category]}</h2>
              <span className="recon-group-count" data-testid={`recon-count-${category}`}>
                {items.length}
              </span>
            </div>
            <p className="recon-group-note">{CATEGORY_NOTE[category]}</p>
            <div className="recon-rel-list">
              {items.map((relationship) => (
                <ReconciliationRelationship
                  key={`${relationship.item.claim_ids.join("|")}:${relationship.item.relationship}:${relationship.item.state}`}
                  relationship={relationship}
                />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

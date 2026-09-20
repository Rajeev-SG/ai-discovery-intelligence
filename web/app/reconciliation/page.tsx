import type { Metadata } from "next";
import { ReconciliationList } from "@/components/reconciliation-list";
import { fetchClaims, fetchReconciliation, joinReconciliation } from "@/lib/reconciliation";

export const metadata: Metadata = {
  title: "Reconciled evidence — AI Discovery Intelligence",
  description:
    "How the agency reconciles findings that agree, update, supersede, contradict or contextualise one another, and why apparently different numbers are or are not comparable.",
};

export const dynamic = "force-dynamic";

/**
 * The reconciliation view (issue #47). Reached directly at `/reconciliation`.
 * It consumes the canonical persisted ledger from the evidence API and the
 * claim ledger it links to — it never re-derives a reconciliation decision.
 */
export default async function ReconciliationPage() {
  const [reconciliation, claims] = await Promise.all([fetchReconciliation(), fetchClaims()]);
  const relationships = reconciliation ? joinReconciliation(reconciliation, claims) : [];

  return (
    <div className="recon">
      <header className="recon-header">
        <h1>Reconciled evidence</h1>
        <p className="recon-intro">
          The agency reconciles every validated claim against the others. Each relationship below
          is persisted, not inferred in the browser: it records how the findings relate, which
          context dimensions differ or are unknown, the agency&rsquo;s interpretation, and the
          confidence adjustment that follows.
        </p>
        {reconciliation && (
          <p className="recon-source" data-testid="recon-total">
            {reconciliation.count} relationship{reconciliation.count === 1 ? "" : "s"} ·{" "}
            {claims
              ? `${claims.length} claim${claims.length === 1 ? "" : "s"} resolved`
              : "claim ledger unreachable"}
          </p>
        )}
      </header>

      {!reconciliation ? (
        <p className="recon-empty-state" data-testid="recon-unavailable">
          The reconciliation ledger is not reachable right now. No relationship is shown rather
          than inventing one.
        </p>
      ) : relationships.length === 0 ? (
        <p className="recon-empty-state" data-testid="recon-empty">
          No reconciliation relationship is currently persisted.
        </p>
      ) : (
        <ReconciliationList relationships={relationships} />
      )}
    </div>
  );
}

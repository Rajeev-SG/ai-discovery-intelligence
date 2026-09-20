import type { Metadata } from "next";
import { ImplicationsList } from "@/components/implications-list";
import { fetchImplications } from "@/lib/implications";

export const metadata: Metadata = {
  title: "Marketing implications — AI Discovery Intelligence",
  description:
    "What the evidenced discovery mechanics mean for marketers: restrained, source-backed actions, or an explicit monitor-only state when the evidence is insufficient.",
};

export const dynamic = "force-dynamic";

/**
 * Marketing implications (Phase 2, issue #59). Answers the marketer's final
 * question — why does this matter, and what should I do? — using only validated
 * mechanics/evidence. Unreachable backend and empty evidence are distinguishable
 * states; nothing is recommended without supporting evidence.
 */
export default async function ImplicationsPage() {
  const outcome = await fetchImplications();

  return (
    <div className="impl-page">
      <header className="impl-header">
        <h1>Marketing implications</h1>
        <p className="impl-subtitle">
          What the evidence means for what you should do — grounded in the validated
          mechanics of each discovery surface, never in generic advice. Every action
          traces to specific claims, and where the evidence does not support an
          action, that is stated plainly.
        </p>
      </header>

      {outcome.status === "error" || outcome.status === "unconfigured" ? (
        <p className="impl-empty" data-testid="impl-unavailable">
          The implications source is unreachable right now. No implications are shown
          rather than inventing them.
        </p>
      ) : outcome.projection && outcome.projection.count > 0 ? (
        <ImplicationsList projection={outcome.projection} />
      ) : (
        <p className="impl-empty" data-testid="impl-empty">
          No evidence-backed marketing implication is currently derivable. Unknown is a
          valid answer.
        </p>
      )}
    </div>
  );
}

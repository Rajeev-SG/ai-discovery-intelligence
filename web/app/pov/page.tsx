import type { Metadata } from "next";
import { PovChangelog } from "@/components/pov-changelog";
import { PovProposition } from "@/components/pov-proposition";
import { hasChanges } from "@/lib/pov";
import { loadPov } from "@/lib/pov.server";

export const metadata: Metadata = {
  title: "Living POV — AI Discovery Intelligence",
  description:
    "The agency's living point of view on AI discovery, with its evidence and change history.",
};

/**
 * The Living POV surface (issue #49). Reachable directly at `/pov`; the shell
 * nav integration is issue #45's job. Data comes from the committed product
 * artifact (`web/lib/generated-pov.json`), projected through `@/lib/pov`, so
 * the page renders canonical state — never parsed Markdown.
 */
export default function PovPage() {
  const view = loadPov();
  const changed = hasChanges(view);
  return (
    <div className="pov">
      <header className="pov-header">
        <h1>Living POV</h1>
        <p className="pov-intro">
          The agency&apos;s standing position, evidence-gated and deterministic. Each
          proposition changes only when a qualifying event clears the gate in{" "}
          <code>config/pov_policy.yaml</code>; the change history below records every
          adoption, and &ldquo;no change&rdquo; is a valid outcome.
        </p>
        <p className="pov-source">
          Source: <code>{view.source}</code> · version {view.version} ·{" "}
          {changed ? `${view.changelog.length} change${view.changelog.length === 1 ? "" : "s"} recorded` : "no POV change recorded"}
        </p>
      </header>

      <section className="pov-current" aria-labelledby="pov-current-title">
        <h2 id="pov-current-title">Current POV</h2>
        <div className="pov-props">
          {view.propositions.map((proposition) => (
            <PovProposition key={proposition.id} proposition={proposition} />
          ))}
        </div>
      </section>

      <section className="pov-history" aria-labelledby="pov-history-title">
        <h2 id="pov-history-title">POV changelog</h2>
        <PovChangelog revisions={view.changelog} />
      </section>
    </div>
  );
}

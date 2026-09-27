import type { Metadata } from "next";
import { PovChangelog } from "@/components/pov-changelog";
import { PovProposition } from "@/components/pov-proposition";
import { loadPov } from "@/lib/pov.server";

export const metadata: Metadata = {
  title: "What this means — AI Discovery Intelligence",
  description:
    "The agency's standing position on AI discovery, with the evidence and change history behind each conclusion.",
};

/**
 * The standing-position page (issue #49; copy reset per issue #69). Reachable
 * directly at `/pov`. Data comes from the committed product artifact
 * (`web/lib/generated-pov.json`), projected through `@/lib/pov`, so the page
 * renders canonical state — never parsed Markdown.
 */
export default function PovPage() {
  const view = loadPov();
  return (
    <div className="pov">
      <header className="pov-header">
        <h1>What this means — our standing position</h1>
        <p className="pov-intro">
          The conclusions we currently draw for marketers from the evidence we hold.
          Each position changes only when the evidence justifies a change; the
          changelog below records every change and the reason for it.
        </p>
      </header>

      <section className="pov-current" aria-labelledby="pov-current-title">
        <h2 id="pov-current-title">Current position</h2>
        <div className="pov-props">
          {view.propositions.map((proposition) => (
            <PovProposition key={proposition.id} proposition={proposition} />
          ))}
        </div>
      </section>

      <section id="changelog" className="pov-history" aria-labelledby="pov-history-title">
        <h2 id="pov-history-title">Changelog</h2>
        <PovChangelog revisions={view.changelog} />
      </section>
    </div>
  );
}

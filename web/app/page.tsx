import type { Metadata } from "next";
import Link from "next/link";
import { LandingBrief } from "@/components/landing-brief";
import { LandingChanges } from "@/components/landing-changes";
import { LandingPov } from "@/components/landing-pov";
import { fetchBrief, fetchEvents } from "@/lib/intel";
import { loadPov } from "@/lib/pov.server";

export const metadata: Metadata = {
  title: "AI Discovery Intelligence",
  description:
    "What changed, what matters and what we currently believe about how consumer AI discovery surfaces find, retrieve, cite and recommend information.",
};

export const dynamic = "force-dynamic";

/**
 * Intelligence-first landing (issue #45). Leads with what changed (real
 * `/events`), what matters (real `/brief`) and what we currently believe (the
 * canonical POV), then points at the secondary Explore surfaces view. The POV
 * artifact is committed, so its read is local; the two live endpoints degrade
 * to explicit, distinguishable states when the backend is unreachable.
 */
export default async function Page() {
  const [events, brief] = await Promise.all([fetchEvents(), fetchBrief()]);
  const pov = loadPov();

  return (
    <div className="landing">
      <header className="landing-hero">
        <h1>What changed, what matters, what we believe</h1>
        <p className="landing-subtitle">
          A source-backed read on how consumer AI discovery surfaces find, retrieve, cite and
          recommend information — updated as the evidence changes.
        </p>
        <nav className="landing-actions" aria-label="Landing navigation">
          <Link className="landing-button" href="/surfaces">
            Explore surfaces
          </Link>
        </nav>
      </header>

      <LandingChanges outcome={events} />
      <LandingBrief outcome={brief} />
      <LandingPov view={pov} />
    </div>
  );
}

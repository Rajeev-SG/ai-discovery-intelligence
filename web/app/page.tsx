import type { Metadata } from "next";
import Link from "next/link";
import { HomeQuestions } from "@/components/home-questions";
import { LandingBrief } from "@/components/landing-brief";
import { LandingChanges } from "@/components/landing-changes";
import { LandingPov } from "@/components/landing-pov";
import { fetchImplications } from "@/lib/implications";
import { fetchLandscape } from "@/lib/landscape";
import { fetchMechanics } from "@/lib/mechanics";
import { fetchBrief, fetchEvents } from "@/lib/intel";
import { loadPov } from "@/lib/pov.server";

export const metadata: Metadata = {
  title: "AI Discovery Intelligence",
  description:
    "Which AI discovery platforms matter, how their search and retrieval work, how strong the evidence is, and what it means for marketers — built on source-backed mechanics.",
};

export const dynamic = "force-dynamic";

/**
 * Marketer-first front door (Phase 2, issue #61). Answers, in order: what AI
 * discovery platforms exist → how their search/discovery works → how we know /
 * can we trust it → why it matters for marketers. Latest material changes and the
 * weekly brief are demoted to a returning-user intelligence area at the bottom;
 * market share is supporting context, never the first impression. The committed
 * POV artifact reads locally; the live endpoints degrade to explicit,
 * distinguishable states when the backend is unreachable.
 */
export default async function Page() {
  const [landscape, mechanics, implications, events, brief] = await Promise.all([
    fetchLandscape(),
    fetchMechanics(),
    fetchImplications(),
    fetchEvents(),
    fetchBrief(),
  ]);
  const pov = loadPov();

  return (
    <div className="landing home">
      <header className="landing-hero">
        <p className="eyebrow">AI Discovery Intelligence</p>
        <h1>Understand how AI changes the way customers find and choose your brand</h1>
        <p className="landing-subtitle">
          Learn which platforms matter, how they select information, and what your
          marketing team can do next — each finding backed by its public source.
        </p>
        <nav className="landing-actions" aria-label="Landing navigation">
          <Link className="landing-button" href="/landscape">
            Understand the landscape
          </Link>
          <Link className="landing-link" href="#latest">
            See the latest developments →
          </Link>
        </nav>
      </header>

      <section className="landing-section home-questions-section" aria-labelledby="home-questions-title">
        <header className="landing-section-head">
          <div>
            <p className="eyebrow">Start here</p>
            <h2 id="home-questions-title">Four questions, answered</h2>
          </div>
        </header>
        <HomeQuestions
          landscape={landscape.projection}
          mechanics={mechanics.projection}
          implications={implications.projection}
        />
      </section>

      <section id="latest" className="landing-section home-latest" aria-labelledby="home-latest-title" data-testid="home-latest-title">
        <header className="landing-section-head">
          <div>
            <p className="eyebrow">Latest developments</p>
            <h2 id="home-latest-title">What changed, and what we believe now</h2>
            <p className="landing-lede">
              Recent platform developments, the weekly brief and the current standing
              position. New here? Start with the four questions above.
            </p>
          </div>
        </header>
        <LandingChanges outcome={events} />
        <LandingBrief outcome={brief} />
        <LandingPov view={pov} />
      </section>
    </div>
  );
}

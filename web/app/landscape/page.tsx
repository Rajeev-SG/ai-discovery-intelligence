import type { Metadata } from "next";
import { LandscapeClient } from "@/components/landscape-client";
import { fetchLandscape } from "@/lib/landscape";

export const metadata: Metadata = {
  title: "AI discovery landscape — AI Discovery Intelligence",
  description:
    "The major consumer AI discovery surfaces and how their discovery mechanics differ, backed by validated evidence with unknowns kept explicit.",
};

export const dynamic = "force-dynamic";

/**
 * Primary landscape + mechanics comparison (Phase 2, issue #60). The marketer
 * answers "what AI discovery surfaces exist and how do they differ?" without
 * navigating the analyst registry first. The exhaustive 35-surface registry
 * remains available at /surfaces for deep exploration.
 */
export default async function LandscapePage() {
  const outcome = await fetchLandscape();

  return (
    <div className="landscape-page">
      <header className="landscape-header">
        <h1>AI discovery landscape</h1>
        <p className="landscape-subtitle">
          The major consumer AI discovery surfaces, and how their retrieval, citation
          and commercial mechanics differ — from validated evidence, with every gap
          left explicit rather than filled.
        </p>
      </header>

      {outcome.status !== "ok" || !outcome.projection ? (
        <p className="landscape-empty" data-testid="landscape-unavailable">
          The landscape source is unreachable right now. Nothing is shown rather than
          presenting the registry as evidenced mechanics.
        </p>
      ) : (
        <LandscapeClient projection={outcome.projection} />
      )}
    </div>
  );
}

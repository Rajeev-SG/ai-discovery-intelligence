import Link from "next/link";
import type { LandscapeProjection } from "@/lib/landscape";
import type { ImplicationsProjection } from "@/lib/implications";
import type { MechanicsProjection } from "@/lib/mechanics";

/**
 * The marketer-first front door (Phase 2, issue #61). The homepage answers the
 * four questions a marketer actually has, in order:
 *
 *   1. What AI discovery platforms exist?         -> /landscape
 *   2. How does their search/discovery work?      -> /landscape (comparison) / /surfaces
 *   3. How do we know / can we trust the evidence?-> /surfaces (Evidence & trust)
 *   4. Why does this matter for marketers?        -> /implications
 *
 * It renders only counts and names the backend already computed (landscape
 * surfaces, evidenced dimensions, marketing implications). It never derives a
 * mechanic, coverage or implication; when a source is unreachable the answer
 * says so rather than implying zero.
 */

interface Question {
  n: number;
  question: string;
  answer: string;
  href: string;
  cta: string;
  evidence: string;
}

function buildQuestions(
  landscape: LandscapeProjection | null,
  mechanics: MechanicsProjection | null,
  implications: ImplicationsProjection | null,
): Question[] {
  const surfaceCount = landscape?.surfaces.length ?? null;
  const evidenced = Object.values(mechanics?.surfaces ?? {}).reduce(
    (n, s) => n + s.evidenced_dimension_count,
    0,
  );
  const evidencedSurfaces = Object.values(mechanics?.surfaces ?? {}).filter(
    (s) => s.evidenced_dimension_count > 0,
  ).length;
  const actionable = implications?.count ?? null;

  return [
    {
      n: 1,
      question: "What AI discovery platforms exist?",
      answer: surfaceCount
        ? `${surfaceCount} major consumer AI discovery surfaces, with vendor, geography, discovery modes and evidenced reach.`
        : "The major consumer AI discovery surfaces and how they differ.",
      href: "/landscape",
      cta: "See the landscape",
      evidence: "Registry facts are labelled; reach is evidenced.",
    },
    {
      n: 2,
      question: "How does their search and discovery work?",
      answer:
        evidencedSurfaces > 0
          ? `Compare retrieval, citation, crawl and commercial mechanics across surfaces — ${evidencedSurfaces} surface${evidencedSurfaces === 1 ? "" : "s"} carry evidenced mechanics.`
          : "Compare retrieval, citation, crawl and commercial mechanics across surfaces.",
      href: "/landscape",
      cta: "Compare how discovery works",
      evidence: "Every dimension is evidenced or explicitly unknown.",
    },
    {
      n: 3,
      question: "How do we know — and can we trust it?",
      answer: evidenced > 0
        ? `${evidenced} evidenced mechanics dimensions across the surfaces, each with its publisher, evidence class, dates and confidence.`
        : "Every finding carries its publisher, evidence class, dates and confidence.",
      href: "/surfaces",
      cta: "Inspect evidence & trust",
      evidence: "Vendor documentation, independent research and direct observation stay distinct.",
    },
    {
      n: 4,
      question: "Why does this matter for marketers?",
      answer: actionable
        ? `${actionable} evidence-backed marketing implication${actionable === 1 ? "" : "s"} — or an explicit monitor-only state where evidence is insufficient.`
        : "Evidence-backed marketing implications, or an explicit monitor-only state.",
      href: "/implications",
      cta: "See marketing implications",
      evidence: "No generic advice: every action cites its supporting claims.",
    },
  ];
}

export function HomeQuestions({
  landscape,
  mechanics,
  implications,
}: {
  landscape: LandscapeProjection | null;
  mechanics: MechanicsProjection | null;
  implications: ImplicationsProjection | null;
}) {
  const questions = buildQuestions(landscape, mechanics, implications);
  return (
    <ol className="home-questions" data-testid="home-questions">
      {questions.map((q) => (
        <li key={q.n} className="home-question" data-testid={`home-q${q.n}`}>
          <div className="home-question-n" aria-hidden="true">
            {q.n}
          </div>
          <div className="home-question-body">
            <h3>{q.question}</h3>
            <p className="home-question-answer">{q.answer}</p>
            <p className="home-question-evidence">{q.evidence}</p>
            <Link className="home-question-cta" href={q.href}>
              {q.cta} →
            </Link>
          </div>
        </li>
      ))}
    </ol>
  );
}

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

type AnswerState = "populated" | "empty" | "unavailable";

interface Question {
  n: number;
  question: string;
  /** The resolved answer text. */
  answer: string;
  /** Exactly one of populated / empty / unavailable (issue #61 review F1). */
  state: AnswerState;
  href: string;
  cta: string;
  evidence: string;
}

/** A milestone count that is either a real number, an explicit empty, or unknown. */
function countState(value: number | null): AnswerState {
  if (value === null) return "unavailable";
  return value > 0 ? "populated" : "empty";
}

function buildQuestions(
  landscape: LandscapeProjection | null,
  mechanics: MechanicsProjection | null,
  implications: ImplicationsProjection | null,
): Question[] {
  // `null` projection == the source is unreachable; a present-but-zero count ==
  // the source is reachable and genuinely empty. The two are ALWAYS distinct, so
  // a backend outage is never rendered as a confident homepage (issue #61 F1).
  const surfaceCount = landscape ? landscape.surfaces.length : null;
  const evidenced =
    mechanics === null
      ? null
      : Object.values(mechanics.surfaces).reduce(
          (n, s) => n + s.evidenced_dimension_count,
          0,
        );
  const actionable = implications ? implications.count : null;

  const unavailableAnswer: Record<number, string> = {
    1: "The landscape source is unavailable right now, so the platform list cannot be shown.",
    2: "The mechanics source is unavailable right now, so the comparison cannot be shown.",
    3: "The evidence source is unavailable right now, so findings cannot be shown.",
    4: "The implications source is unavailable right now, so actions cannot be shown.",
  };
  const emptyAnswer: Record<number, string> = {
    1: "No landscape surface is currently configured.",
    2: "No surface carries evidenced mechanics yet — unknown is a valid answer.",
    3: "No evidenced mechanics finding is recorded yet.",
    4: "No evidence-backed implication is currently derivable — monitor only.",
  };

  const states: Record<number, AnswerState> = {
    1: countState(surfaceCount),
    2: countState(evidenced),
    3: countState(evidenced),
    4: countState(actionable),
  };

  const populated: Record<number, string> = {
    1: `${surfaceCount} major consumer AI discovery surfaces, with vendor, geography, discovery modes and evidenced reach.`,
    2: `Compare retrieval, citation, crawl and commercial mechanics across surfaces — ${evidenced} evidenced mechanics dimension${evidenced === 1 ? "" : "s"} in total.`,
    3: `${evidenced} evidenced mechanics dimension${evidenced === 1 ? "" : "s"} across the surfaces, each with its publisher, evidence class, dates and confidence.`,
    4: `${actionable} evidence-backed marketing implication${actionable === 1 ? "" : "s"} — or an explicit monitor-only state where evidence is insufficient.`,
  };

  const answerFor = (n: number): string =>
    states[n] === "unavailable"
      ? unavailableAnswer[n]
      : states[n] === "empty"
        ? emptyAnswer[n]
        : populated[n];

  return [
    {
      n: 1,
      question: "What AI discovery platforms exist?",
      answer: answerFor(1),
      state: states[1],
      href: "/landscape",
      cta: "See the landscape",
      evidence: "Registry facts are labelled; reach is evidenced.",
    },
    {
      n: 2,
      question: "How does their search and discovery work?",
      answer: answerFor(2),
      state: states[2],
      href: "/landscape",
      cta: "Compare how discovery works",
      evidence: "Every dimension is evidenced or explicitly unknown.",
    },
    {
      n: 3,
      question: "How do we know — and can we trust it?",
      answer: answerFor(3),
      state: states[3],
      href: "/surfaces",
      cta: "Inspect evidence & trust",
      evidence: "Vendor documentation, independent research and direct observation stay distinct.",
    },
    {
      n: 4,
      question: "Why does this matter for marketers?",
      answer: answerFor(4),
      state: states[4],
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
        <li
          key={q.n}
          className={`home-question state-${q.state}`}
          data-testid={`home-q${q.n}`}
          data-state={q.state}
        >
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

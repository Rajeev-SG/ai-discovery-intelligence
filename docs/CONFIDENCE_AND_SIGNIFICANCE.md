# Confidence and commercial significance

These are separate dimensions.

## Evidence confidence

Confidence evaluates how strongly a claim is supported, not how confident an LLM sounds.

Suggested weighted inputs:

- source authority/directness;
- methodology transparency;
- sample size/coverage;
- recency;
- geographic/language fit;
- corroboration by independent evidence;
- whether the claim is observed vs inferred;
- unresolved conflict.

Output labels: `High`, `Medium-High`, `Medium`, `Low`, `Unresolved`.

Official documentation can produce high confidence about documented behaviour but not necessarily about real-world frequency. Large telemetry studies can be high confidence about their own measured dataset while remaining conditional by geography/sample.

## Commercial significance

Score separately on:

1. **Reach** — how much consumer discovery volume the affected surface represents.
2. **Intent** — relevance to research, recommendation, shopping or local discovery.
3. **Magnitude** — how materially behaviour changed.
4. **Breadth** — markets/categories affected.
5. **Persistence** — likely structural vs short-lived anomaly.
6. **Actionability** — whether brands should change investment/content/distribution/measurement.

Use a 0–5 normalized score with the component breakdown visible.

## Executive inclusion rule

Normally include an item in the weekly senior brief only when:

- significance >= 3.5/5 and confidence >= Medium; or
- significance >= 4.5/5 with lower confidence, explicitly labelled as a watch item.

A high-confidence but trivial product release does not belong in the brief.

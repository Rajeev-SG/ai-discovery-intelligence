# Product brief

## Problem

The consumer AI discovery landscape changes faster than conventional agency POV documents can be maintained. Different chat/search products use different indexes, retrieval mechanisms, crawlers, query fan-out, citation logic, shopping surfaces and referral behaviour. Research is fragmented across official docs, visibility vendors, analytics providers, SEO studies and regional sources.

## Product answer

Create a continuously maintained intelligence system rather than another static GEO deck.

### Observation plane

One row per consumer discovery surface/sub-surface, with compact cells for:

- product/vendor and geography;
- surface type and distribution channels;
- current audience/priority evidence;
- live web/search capability;
- upstream index/search provider where known;
- search trigger behaviour;
- query fan-out behaviour;
- source/citation behaviour;
- crawler/user-agent and content controls;
- shopping/product/transaction surfaces;
- advertising surfaces;
- link/referral behaviour;
- measurement implications;
- latest material change;
- agency confidence;
- last verified date.

Click/expand any row or important cell to reveal the full evidence ledger, source methodology, conflicting claims and history.

### Executive intelligence

The weekly brief is **not** an SEO-news digest. It should normally contain 0–5 items. No material change is a valid outcome.

Each included item answers:

1. What changed?
2. Why does it matter commercially?
3. What should brands/agencies reconsider or do?
4. How confident are we?

### Living POV

A stable executive SEO/AEO/GEO POV document is maintained from canonical claims. It changes only when material evidence changes. Every edit produces a traceable changelog event with supporting evidence IDs.

## Marketing implications (issue #59)

The marketer's final question — "why does this matter, and what should I do?" — is
answered only from validated mechanics/evidence. `src/ai_discovery/implications.py`
holds an auditable rule table (mechanics dimension + ledger topic -> action
family); a rule fires only when the surface's mechanics projection carries an
evidenced dimension of that kind and a real claim on that surface has the rule's
topic. Every implication carries its supporting claim ids, applicable
surfaces/modes/regions, confidence, actionability (distinct from confidence),
significance, and any contradicting evidence. Unknown is a valid output: a surface
with no actionable evidenced mechanic returns an explicit monitor-only state.

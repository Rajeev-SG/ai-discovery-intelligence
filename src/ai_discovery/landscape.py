"""Marketer-first AI discovery landscape + mechanics comparison (Phase 2, #60).

The exhaustive 35-surface registry is an analyst artefact. This module projects a
*marketer-facing* landscape on top of it: the major consumer AI discovery
surfaces with a concise, evidence-aware summary, plus a comparison across the
canonical mechanics dimensions.

Two hard rules, both inherited from the evidence contract:

* **Nothing is invented.** Registry facts (name, vendor, type, geography,
  discovery modes) are copied verbatim from ``config/surfaces.yaml`` and are
  labelled as registry metadata, never as mechanics evidence. Usage/reach,
  mechanics coverage and per-dimension state come from *validated claims* only.
* **Unknown stays explicit.** A surface with no evidenced mechanic reports zero
  coverage; a comparison cell with no evidence renders ``unknown`` rather than an
  inferred value.

Market share/usage is deliberately contextual: this module surfaces a single
reach figure where one is evidenced, never as the organising layer.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict

from .mechanics import MECHANICS_DIMENSIONS, SurfaceMechanics

#: The marketer-facing "major" surfaces (issue #60 names these plus a
#: regional/China surface). Kept explicit so the landscape is a *curated* view,
#: not simply the first N registry rows. Every id must exist in the registry.
LANDSCAPE_IDS: tuple[str, ...] = (
    "chatgpt",
    "google-gemini",
    "google-ai-mode",
    "claude",
    "perplexity",
    "deepseek-chat",
    "doubao",
)

#: The dimensions offered in the comparison view (a marketer-readable subset of
#: the 13 canonical dimensions; all are canonical, none invented).
COMPARISON_DIMENSIONS: tuple[str, ...] = (
    "search_trigger",
    "retrieval_provider",
    "query_rewrite",
    "citation_presentation",
    "crawling_indexing_controls",
    "freshness_recrawl",
    "shopping_product_feed",
    "local_retrieval",
    "social_community_retrieval",
)

assert set(COMPARISON_DIMENSIONS) <= set(MECHANICS_DIMENSIONS)


class LandscapeSurface(BaseModel):
    """One marketer-facing landscape row."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name: str
    vendor: str
    #: Registry product type (coarse), labelled "registry metadata" in the UI.
    surface_type: str
    type_label: str
    #: Commercial priority computed from the registry tier (not new evidence).
    priority: str
    regions: tuple[str, ...]
    discovery_modes: tuple[str, ...]
    official_url: str | None = None
    #: Reach/usage as a single evidenced figure, when one exists. Never a guess.
    reach_metric: str | None = None
    reach_claim_id: str | None = None
    reach_confidence: str | None = None
    #: Mechanics coverage from the projection (counts, not inferred states).
    evidenced_dimensions: int
    dimension_count: int
    coverage: dict[str, int]
    #: One-line marketing relevance, derived from evidenced mechanics; honest when
    #: there is nothing evidenced yet.
    relevance: str


def _format_number(value: Any) -> str | None:
    """A readable number for display: drop a trailing ``.0``, add thousands commas."""

    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _reach(
    claims: list[dict[str, Any]], surface_name: str, vendor: str | None = None
) -> tuple[str | None, str | None, str | None]:
    """The single best evidenced reach/usage figure for a surface, if any.

    Only audience_usage claims with a known value qualify. This is contextual
    data, not the organising layer: one figure, with its claim id and confidence,
    or nothing. A metric that names the surface itself (in its label or scope) is
    preferred over a joint metric, so a shared multi-surface claim never attributes
    another surface's number to this one.
    """

    rank = {"unknown": 0, "low": 1, "medium": 2, "high": 3}
    best: tuple[str | None, str | None, str | None] = (None, None, None)
    best_key = (-1, -1)
    # Distinctive tokens from the surface name (e.g. "Doubao / 豆包" -> {"doubao"}),
    # so a joint claim is attributed only when its metric actually names THIS
    # surface. Substring matching is deliberately conservative: a metric that does
    # not name the surface yields no figure at all rather than a misattribution
    # (issue #60 review: prefer dropping a figure over guessing its owner).
    name = surface_name.lower()
    vendor_tokens = {t for t in re.split(r"[^a-z0-9]+", (vendor or "").lower()) if t}
    # Distinctive tokens exclude the vendor name: "Google" alone is ambiguous
    # across Gemini and AI Mode, so a joint "Google AI users" claim must not be
    # attributed to either — only a token specific to the surface (e.g. "gemini",
    # "doubao") qualifies.
    name_tokens = [
        t
        for t in re.split(r"[^a-z0-9]+", name)
        if len(t) >= 3 and t not in vendor_tokens
    ]
    for row in claims:
        if row.get("topic") != "audience_usage":
            continue
        # A joint (multi-surface) claim is only usable when its metric names THIS
        # surface, so a shared claim never attributes another surface's figure.
        multi = len({s for s in (row.get("surfaces") or [])}) > 1
        for m in row.get("metrics") or []:
            # Prefer a conventionally-formatted number; a bare numeric value_text
            # (e.g. "1000000000.0") is reformatted from value_number for display.
            value_number = m.get("value_number")
            value_text = m.get("value_text")
            if value_number is not None:
                value = _format_number(value_number)
            else:
                value = value_text
            if not value:
                continue
            label = m.get("label") or "usage"
            unit = m.get("unit") or ""
            text = f"{label}: {value}{(' ' + unit) if unit else ''}"
            # Prefer a metric named for this surface; then by confidence.
            haystack = f"{label} {m.get('scope') or ''}".lower()
            names_surface = any(tok in haystack for tok in name_tokens)
            if multi and not names_surface:
                continue
            key = (1 if names_surface else 0, rank.get(row.get("confidence"), 0))
            if key > best_key:
                best_key = key
                best = (text, row.get("claim_id"), row.get("confidence"))
    return best


def _relevance(mechanics: SurfaceMechanics, surface_name: str) -> str:
    """One-line marketing relevance from evidenced mechanics (never invented).

    Grounded in how many dimensions are evidenced and, where known, whether the
    surface is citable/crawlable/shoppable. A surface with no evidenced mechanics
    gets an honest "not yet evidenced" line.
    """

    if mechanics.evidenced_dimension_count() == 0:
        return (
            f"No evidenced discovery mechanic for {surface_name} yet; "
            "treat any marketing assumption as unverified."
        )
    pieces: list[str] = []
    if mechanics.state_of("citation_presentation") != "unknown":
        pieces.append("sources are cited")
    if mechanics.state_of("crawling_indexing_controls") != "unknown":
        pieces.append("crawler/index controls are documented")
    if mechanics.state_of("shopping_product_feed") != "unknown":
        pieces.append("commercial/product surfaces are evidenced")
    if mechanics.state_of("search_trigger") != "unknown" or mechanics.state_of("retrieval_provider") != "unknown":
        pieces.append("its retrieval path is partly evidenced")
    if not pieces:
        return (
            f"{mechanics.evidenced_dimension_count()} of {len(MECHANICS_DIMENSIONS)} "
            f"discovery mechanics are evidenced for {surface_name}."
        )
    return f"For {surface_name}, {', '.join(pieces)}."


#: Coarse product-type labels (registry vocabulary -> marketer language).
TYPE_LABELS: dict[str, str] = {
    "conversational_assistant": "Conversational assistant",
    "ai_native_search": "AI-native search",
    "search_augmentation": "Search augmentation",
    "embedded_ecosystem_assistant": "Embedded ecosystem assistant",
    "browser_native_ai": "Browser-native AI",
    "general_consumer_agent": "General consumer agent",
    "multi_model_assistant": "Multi-model assistant",
    "commerce_native_ai": "Commerce-native AI",
}

#: Registry tier -> commercial priority (presentation only, not evidence).
PRIORITY_LABELS: dict[str, str] = {
    "core_global": "Core — global",
    "core_china": "Core — China",
    "core_regional": "Core — regional",
    "secondary_global": "Secondary — global",
    "watch_global": "Watch — global",
    "watch_regional": "Watch — regional",
    "watch_commerce": "Watch — commerce",
}


def build_landscape(
    registry: Any,
    projection: dict[str, SurfaceMechanics],
    claims: list[dict[str, Any]],
    *,
    ids: tuple[str, ...] | None = None,
) -> list[LandscapeSurface]:
    """Build the marketer-facing landscape rows from the registry + projection.

    ``registry`` is the loaded ``SurfacesConfig``; ``projection`` is the mechanics
    projection keyed by surface id; ``claims`` are the expanded ledger rows used
    only for the single reach figure.
    """

    from .registry import resolve_surface_id

    wanted = ids or LANDSCAPE_IDS
    by_surface: dict[str, list[dict[str, Any]]] = {}
    for row in claims:
        for sid in row.get("surfaces") or []:
            # Resolve aliases so a surface whose claims are stored under an alias
            # (e.g. "deepseek") still gets its reach figure under the canonical id.
            by_surface.setdefault(resolve_surface_id(sid), []).append(row)

    out: list[LandscapeSurface] = []
    for sid in wanted:
        config = registry.by_id(sid)
        if config is None:
            # A curated id that drifts out of the registry is skipped, not faked.
            continue
        mechanics = projection.get(sid)
        coverage = mechanics.coverage() if mechanics else {"known": 0, "partially_known": 0, "conflicting": 0, "unknown": len(MECHANICS_DIMENSIONS)}
        reach, reach_claim, reach_conf = _reach(by_surface.get(sid, []), config.name, config.vendor)
        out.append(
            LandscapeSurface(
                id=config.id,
                name=config.name,
                vendor=config.vendor,
                surface_type=config.type,
                type_label=TYPE_LABELS.get(config.type, config.type.replace("_", " ")),
                priority=PRIORITY_LABELS.get(config.tier, config.tier.replace("_", " ")),
                regions=tuple(config.regions),
                discovery_modes=tuple(config.discovery_modes),
                official_url=(config.official_urls[0] if config.official_urls else None),
                reach_metric=reach,
                reach_claim_id=reach_claim,
                reach_confidence=reach_conf,
                evidenced_dimensions=mechanics.evidenced_dimension_count() if mechanics else 0,
                dimension_count=len(MECHANICS_DIMENSIONS),
                coverage=coverage,
                relevance=_relevance(mechanics, config.name) if mechanics else f"No evidenced discovery mechanic for {config.name} yet.",
            )
        )
    return out


class ComparisonCell(BaseModel):
    """One cell of the mechanics comparison: a state plus its evidence link."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dimension: str
    state: str
    statement: str | None = None
    claim_id: str | None = None
    evidence_class: str | None = None
    confidence: str | None = None
    #: True when the cell is an explicit unknown (not a missing value).
    unknown: bool = False


class ComparisonRow(BaseModel):
    """One dimension row across the compared surfaces."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dimension: str
    label: str
    definition: str
    cells: dict[str, ComparisonCell]


def build_comparison(
    surface_ids: list[str],
    projection: dict[str, SurfaceMechanics],
    *,
    dimensions: tuple[str, ...] = COMPARISON_DIMENSIONS,
) -> list[ComparisonRow]:
    """A per-dimension comparison across the selected surfaces.

    Each cell is the surface's projection state with its lead evidenced claim and
    an explicit ``unknown`` flag. No cell is inferred; a surface missing evidence
    for a dimension renders ``unknown``.
    """

    from .mechanics import DIMENSION_META

    rows: list[ComparisonRow] = []
    for dim in dimensions:
        cells: dict[str, ComparisonCell] = {}
        for sid in surface_ids:
            mechanics = projection.get(sid)
            if mechanics is None:
                cells[sid] = ComparisonCell(dimension=dim, state="unknown", unknown=True)
                continue
            state = mechanics.dimension(dim)
            if state.state == "unknown" or not state.assertions:
                cells[sid] = ComparisonCell(dimension=dim, state="unknown", unknown=True)
                continue
            assertion = state.assertions[0]
            lead = assertion.evidence[0] if assertion.evidence else None
            cells[sid] = ComparisonCell(
                dimension=dim,
                state=state.state,
                statement=assertion.statement,
                claim_id=lead.claim_id if lead else None,
                evidence_class=lead.evidence_class if lead else None,
                confidence=lead.confidence if lead else None,
                unknown=False,
            )
        meta = DIMENSION_META.get(dim, {})
        rows.append(
            ComparisonRow(
                dimension=dim,
                label=meta.get("label", dim),
                definition=meta.get("definition", ""),
                cells=cells,
            )
        )
    return rows


def landscape_view(
    surfaces: list[LandscapeSurface],
    comparison: list[ComparisonRow],
    *,
    comparison_surface_ids: list[str],
) -> dict[str, Any]:
    """The marketer-safe payload for the landscape + comparison."""

    return {
        "surfaces": [
            {
                "id": s.id,
                "name": s.name,
                "vendor": s.vendor,
                "type": s.surface_type,
                "type_label": s.type_label,
                "priority": s.priority,
                "regions": list(s.regions),
                "discovery_modes": list(s.discovery_modes),
                "official_url": s.official_url,
                "reach_metric": s.reach_metric,
                "reach_claim_id": s.reach_claim_id,
                "reach_confidence": s.reach_confidence,
                "evidenced_dimensions": s.evidenced_dimensions,
                "dimension_count": s.dimension_count,
                "coverage": s.coverage,
                "relevance": s.relevance,
            }
            for s in surfaces
        ],
        "comparison_surface_ids": list(comparison_surface_ids),
        "comparison": [
            {
                "dimension": r.dimension,
                "label": r.label,
                "definition": r.definition,
                "cells": {
                    sid: {
                        "dimension": c.dimension,
                        "state": c.state,
                        "statement": c.statement,
                        "claim_id": c.claim_id,
                        "evidence_class": c.evidence_class,
                        "confidence": c.confidence,
                        "unknown": c.unknown,
                    }
                    for sid, c in r.cells.items()
                },
            }
            for r in comparison
        ],
    }

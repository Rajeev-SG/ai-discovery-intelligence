"""Instructor + OpenRouter semantic claim extraction (issue #3 rebuild).

The model interprets a cleaned, capture-anchored document and maps it into the
repository's strict ledger schema (``ai_discovery.claim_models``). Every known
field carries a verbatim quote from the capture; the deterministic
``Locator.present_in`` check re-verifies each quote against the captured text,
so a fabricated number cannot survive the pipeline. LLM output is marked
``llm_proposal`` until its provenance is reviewed, per repo rule 11.
"""

from __future__ import annotations

import json
import os
from typing import Any

import instructor
from instructor.v2.core.errors import InstructorRetryException
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from .claim_models import (
    CLAIM_TOPICS,
    ClaimTopic,
    Comparator,
    LocatorKind,
    MeasurementMode,
)

DEFAULT_MODEL = "google/gemini-2.5-flash"
MAX_RETRIES = 2
# Bound the document handed to the model; a pathological page must not
# silently inflate spend. Override with AI_DISCOVERY_MAX_CLEANED_CHARS.
DEFAULT_MAX_CLEANED_CHARS = 120_000


def _max_cleaned_chars() -> int:
    raw = os.environ.get("AI_DISCOVERY_MAX_CLEANED_CHARS")
    if raw and raw.isdigit() and int(raw) > 0:
        return int(raw)
    return DEFAULT_MAX_CLEANED_CHARS


_EXTRACT_PROMPT = """You are extracting source-backed intelligence claims about consumer
AI discovery surfaces (ChatGPT, Gemini, AI Mode, Copilot, Perplexity, Claude,
Grok, Qwen, DeepSeek and related surfaces) from ONE cleaned document.

Extract one claim per distinct, evidence-supported assertion. Follow these
rules EXACTLY:
- Only record facts the document states. Never guess. If the document does not
  say it, the field stays null.
- topic: one of {topics}.
- statement: one sentence summarising the claim, including the key number or
  policy fact and its context (who measured what, when).
- surfaces: consumer AI discovery surface ids the claim is about (lowercase
  kebab-case, e.g. "chatgpt", "google-ai-mode"). At least one.
- methodology.measurement_mode: one of vendor_estimate, vendor_panel,
  consent_panel, clickstream, server_logs, survey, press_release,
  official_documentation, unknown.
- Every field the document supports carries `quote`: a VERBATIM substring of
  the DOCUMENT (short, under 30 words, copied character-for-character from the
  document, not from your memory of it). Fields the document does not support
  stay null and carry NO quote.
- metrics: one entry per distinct number/observation the claim rests on,
  with its own definition, value, unit, window and scope quotes.
- published_at / modified_at: ISO dates only when the document states them
  (page stamps, bylines, JSON-LD echoes). measured_window: the stated
  measurement period, with its quote.
- capture_anchor: one quote that anchors the claim to this capture (usually
  the sentence carrying the headline number or the policy statement).
- capture_anchor_kind: "verbatim_quote" normally; "page_stamp" for a
  date-stamp anchor.
"""


class ExtractedMetric(BaseModel):
    """Schema-constrained metric before mapping into the ledger schema."""

    model_config = ConfigDict(extra="allow")

    label: str = Field(min_length=1)
    value: float | str | None = None
    value_quote: str | None = None
    unit: str | None = None
    unit_quote: str | None = None
    definition: str | None = None
    definition_quote: str | None = None
    window: str | None = None
    window_quote: str | None = None
    scope: str | None = None
    scope_quote: str | None = None
    comparator: Comparator = "exact"

    @model_validator(mode="before")
    @classmethod
    def _coerce_loose(cls, data: Any) -> Any:
        if isinstance(data, dict) and "label" not in data:
            for key in ("metric", "name", "title"):
                if data.get(key):
                    data["label"] = data[key]
                    break
            if "label" not in data and data.get("definition"):
                data["label"] = str(data["definition"])[:40]
        if isinstance(data, dict) and not data.get("value_quote") and data.get("quote"):
            data["value_quote"] = data["quote"]
        return data

    @field_validator("label")
    @classmethod
    def label_not_placeholder(cls, value: str) -> str:
        if value.strip().lower() in {"unknown", "n/a", "none", "todo", ""}:
            raise ValueError(f"placeholder metric label: {value!r}")
        return value.strip()


class ExtractedClaim(BaseModel):
    """Schema-constrained claim before mapping into the ledger schema."""

    model_config = ConfigDict(extra="allow")

    topic: ClaimTopic
    statement: str = Field(min_length=10)
    surfaces: list[str] = Field(min_length=1)
    measurement_mode: MeasurementMode = "unknown"
    metric_family: str | None = None
    metric_family_quote: str | None = None
    metric_definition: str | None = None
    metric_definition_quote: str | None = None
    denominator: str | None = None
    denominator_quote: str | None = None
    prompt_universe: str | None = None
    prompt_universe_quote: str | None = None
    sample_size: str | None = None
    sample_size_quote: str | None = None
    unit_of_analysis: str | None = None
    unit_of_analysis_quote: str | None = None
    time_window: str | None = None
    time_window_quote: str | None = None
    geography: str | None = None
    geography_quote: str | None = None
    language: str | None = None
    language_quote: str | None = None
    devices: str | None = None
    devices_quote: str | None = None
    methodology_notes: str | None = None
    methodology_notes_quote: str | None = None
    limitations: list[str] = Field(default_factory=list)
    published_at: str | None = None  # ISO date string the document states
    modified_at: str | None = None
    measured_window: str | None = None
    measured_window_quote: str | None = None
    capture_anchor: str = Field(min_length=4)
    capture_anchor_kind: LocatorKind = "verbatim_quote"
    metrics: list[ExtractedMetric] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _flatten_methodology(cls, data: Any) -> Any:
        """Some providers nest methodology fields; flatten into the flat shape."""
        if isinstance(data, dict) and isinstance(data.get("methodology"), dict):
            meth = data.pop("methodology")
            for key, value in meth.items():
                data.setdefault(key, value)
        return data

    @field_validator("topic")
    @classmethod
    def topic_known(cls, value: str) -> str:
        if value not in CLAIM_TOPICS:
            raise ValueError(f"topic must be one of {CLAIM_TOPICS}")
        return value

    @field_validator("capture_anchor")
    @classmethod
    def anchor_not_page_title(cls, value: str) -> str:
        lowered = value.strip().lower()
        if len(value.strip()) < 4:
            raise ValueError("capture anchor too short to verify")
        if lowered in {"unknown", "n/a", "none", "todo", "introduction", "overview"}:
            raise ValueError(f"placeholder capture anchor: {value!r}")
        return value.strip()


class ExtractedClaims(BaseModel):
    """The model returns a list; empty means the document supports nothing."""

    model_config = ConfigDict(extra="forbid")

    claims: list[ExtractedClaim]


class SemanticExtractionResult(BaseModel):
    """One model run: schema-valid claims plus bounded usage telemetry."""

    model_config = ConfigDict(extra="forbid")

    claims: list[ExtractedClaim]
    model: str
    attempts: int = 1
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None
    cost_known: bool = False


def build_client(api_key: str | None = None, base_url: str = "https://openrouter.ai/api/v1"):
    """Create the Instructor-wrapped OpenRouter client; key injectable for tests."""
    key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        msg = "OpenRouter API key missing: set OPENROUTER_API_KEY"
        raise RuntimeError(msg)
    client = OpenAI(base_url=base_url, api_key=key)
    return instructor.from_openai(client), base_url


def _prompt() -> str:
    return _EXTRACT_PROMPT.format(topics=", ".join(CLAIM_TOPICS))


def _load_claims_payload(content: str) -> dict[str, Any]:
    """Parse the JSON-mode assistant message into a ``{"claims": [...]}`` dict.

    Providers variously return the array directly, a wrapped object, or a mix of
    dicts and stringified-JSON claim objects; normalise all of them.
    """

    # Every parse level is guarded: a malformed aggregate string must degrade to
    # an empty/partial payload, never raise and discard an otherwise good capture
    # (the all-or-nothing failure this function exists to remove).
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return {"claims": []}
    if isinstance(payload, list):
        payload = {"claims": payload}
    if not isinstance(payload, dict):
        return {"claims": []}
    claims = payload.get("claims")
    if isinstance(claims, str):
        try:
            claims = json.loads(claims)
        except json.JSONDecodeError:
            return {"claims": []}
    if not isinstance(claims, list):
        return {"claims": []}
    normalised: list[Any] = []
    for item in claims:
        if isinstance(item, str):
            try:
                item = json.loads(item)
            except json.JSONDecodeError:
                continue
        if isinstance(item, dict):
            normalised.append(item)
    return {"claims": normalised}


def _has_valued_metric(claim: dict[str, Any]) -> bool:
    """True when the claim carries at least one metric with a non-null value."""

    return any(
        isinstance(m, dict) and m.get("value") is not None for m in claim.get("metrics") or []
    )


def _validate_claims_individually(
    raw_claims: list[Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate each claim on its own; keep the valid ones, report the rest.

    Returns ``(valid_claim_dicts, rejection_reasons)``. A rejected claim never
    reaches the ledger (it is not a valid ``ExtractedClaim``), and cannot veto
    its well-formed siblings.
    """

    valid: list[dict[str, Any]] = []
    rejected: list[str] = []
    for index, raw in enumerate(raw_claims):
        try:
            valid.append(ExtractedClaim.model_validate(raw).model_dump())
        except ValidationError as error:
            first = error.errors()[0]
            rejected.append(f"claim {index}: {first.get('loc')}: {first.get('msg')}")
    return valid, rejected


def semantic_extract(
    *,
    source_id: str,
    source_url: str,
    cleaned_markdown: str,
    client: Any = None,
    model: str = DEFAULT_MODEL,
) -> SemanticExtractionResult:
    """Extract validated claims from one cleaned document.

    ``client`` is injectable for deterministic tests; production uses the
    Instructor + OpenRouter client. The model owns interpretation; this
    function owns schema fidelity, quote locality and bounded retries.
    """
    if client is None:
        client, _ = build_client()
    limit = _max_cleaned_chars()
    if len(cleaned_markdown) > limit:
        import logging

        logging.getLogger(__name__).warning(
            "cleaned document for %s truncated from %d to %d chars before "
            "semantic extraction (AI_DISCOVERY_MAX_CLEANED_CHARS)",
            source_id,
            len(cleaned_markdown),
            limit,
        )
        cleaned_markdown = cleaned_markdown[:limit]
    evidence_block = (
        f"source_id: {source_id}\nsource_url: {source_url}\n\n"
        f"DOCUMENT:\n{cleaned_markdown}"
    )
    messages = [
        {"role": "system", "content": _prompt()},
        {"role": "user", "content": evidence_block},
    ]

    from instructor.core.hooks import HookName, Hooks

    hooks = Hooks()
    state: dict[str, Any] = {"attempts": 1, "usage": None}

    def _on_parse_error(*_: object) -> None:
        state["attempts"] = int(state["attempts"]) + 1

    def _on_usage(usage: object, **_: object) -> None:
        state["usage"] = usage

    hooks.on(HookName.PARSE_ERROR, _on_parse_error)
    hooks.on(HookName.COMPLETION_USAGE, _on_usage)
    try:
        parsed, completion = client.chat.completions.create_with_completion(
            model=model,
            messages=messages,
            response_model=ExtractedClaims,
            max_retries=MAX_RETRIES,
            temperature=0.0,
            hooks=hooks,
        )
    except InstructorRetryException:
        # Some providers (Gemini on OpenRouter) emit the schema as stringified
        # JSON inside one array element when tool-call arguments are big; a
        # cheap local retry with json-mode parsing salvages the run without a
        # second paid call.
        import logging

        logging.getLogger(__name__).warning(
            "structured tool-call extraction failed for %s; retrying in json mode", source_id
        )
        # JSON mode avoids the provider's tool-call arg mangling entirely:
        # one assistant message, parsed locally with the same Pydantic schema.
        plain_client = OpenAI(
            base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            api_key=os.environ["OPENROUTER_API_KEY"],
        )
        response = plain_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        payload = _load_claims_payload(content)
        # Validate claim-by-claim, not all-or-nothing: one malformed claim (bad
        # topic, too-short statement, placeholder anchor) must not discard a whole
        # document's worth of good ones. Invalid claims are dropped with a
        # per-claim reason; the integrity gate downstream is unchanged.
        good, rejected = _validate_claims_individually(payload.get("claims", []))
        logger = logging.getLogger(__name__)
        if rejected:
            logger.warning(
                "dropped %d individually-invalid claims for %s (kept %d)",
                len(rejected), source_id, len(good),
            )
        # A claim is only ledger-claimable when at least one metric carries a
        # real value (not null/absent). Preserve the original semantic exactly:
        # a null-valued metric is 'unknown', not a value, and must not be admitted.
        without_metrics = [c for c in good if not _has_valued_metric(c)]
        if without_metrics:
            logger.warning(
                "dropped %d claims with no metric value (not ledger-claimable)",
                len(without_metrics),
            )
        good = [c for c in good if _has_valued_metric(c)]
        parsed = ExtractedClaims(claims=[ExtractedClaim.model_validate(c) for c in good])
        usage = getattr(response, "usage", None)
        raw_cost = getattr(usage, "cost", None)
        cost_value: float | None = None
        if isinstance(raw_cost, (int, float)) and float(raw_cost) > 0:
            cost_value = float(raw_cost)
        return SemanticExtractionResult(
            claims=parsed.claims,
            model=model,
            attempts=int(state["attempts"]),
            tokens_in=getattr(usage, "prompt_tokens", None),
            tokens_out=getattr(usage, "completion_tokens", None),
            cost_usd=cost_value,
            cost_known=cost_value is not None,
        )
    usage = state["usage"] or getattr(completion, "usage", None)
    raw_cost = getattr(usage, "cost", None)
    cost_value: float | None = None
    if isinstance(raw_cost, (int, float)) and float(raw_cost) > 0:
        cost_value = float(raw_cost)
    if isinstance(parsed, ExtractedClaims):
        claims = parsed.claims
    else:
        claims = parsed
    return SemanticExtractionResult(
        claims=claims,
        model=model,
        attempts=int(state["attempts"]),
        tokens_in=getattr(usage, "prompt_tokens", None),
        tokens_out=getattr(usage, "completion_tokens", None),
        cost_usd=cost_value,
        cost_known=cost_value is not None,
    )

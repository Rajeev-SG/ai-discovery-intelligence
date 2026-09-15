# Observation plane UX

The observation plane is a product, not a debug table.

## Chosen UI foundations

- Next.js App Router
- stable TanStack Table v9
- TanStack Virtual for large result sets
- Radix UI / shadcn-style accessible primitives for drawers, dialogs, popovers and filters

## Required behaviours

- global text search;
- sortable columns;
- faceted multi-select filters;
- region/language filters;
- surface-type filters;
- confidence/significance filters;
- column visibility controls;
- URL-state persistence for filters/sorts;
- keyboard accessible interactions;
- virtualisation only when dataset size justifies it;
- responsive desktop-first layout.

## Expandable detail

Cells should remain concise. Clicking a claim/cell/row opens an expansion panel/drawer containing:

- full normalized claim;
- current status;
- all supporting evidence;
- study methodology/sample/geography;
- conflicting evidence;
- historical claim timeline;
- agency interpretation;
- confidence breakdown;
- significance breakdown;
- exact last verified time.

Do not dump entire scraped articles into the product.

## Default columns

Surface | Region | Audience/priority | Search/index | Retrieval/fan-out | Citation/source behaviour | Commerce/ads | Latest material change | Confidence | Last verified

## Internal vs executive views

The observation plane may be dense because it is an analyst tool. The weekly brief and POV must not inherit that density.

"use client";

import {
  createColumnHelper,
  flexRender,
  useTable,
  type ColumnFiltersState,
  type FilterFn,
  type SortFn,
  type SortingState,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { DetailDrawer } from "@/components/detail-drawer";
import { FacetFilter, type FacetOption } from "@/components/facet-filter";
import { features, searchEverywhere, type PlaneFeatures } from "@/lib/plane-features";
import {
  REGION_LABELS,
  RETRIEVAL_STATUS_LABELS,
  TYPE_LABELS,
  facetEntries,
  type SurfaceRow,
} from "@/lib/surfaces";
import { decodeUrlState, encodeUrlState, type PlaneUrlState } from "@/lib/url-state";

interface ObservationPlaneProps {
  rows: SurfaceRow[];
  registryVersion: number;
  lastReviewed: string;
}

function titleise(value: string): string {
  return value
    .split("_")
    .map((part) => (part.length <= 2 ? part.toUpperCase() : part[0].toUpperCase() + part.slice(1)))
    .join(" ");
}

/** Multi-select facet match for scalar (string) columns. */
const multiString: FilterFn<PlaneFeatures, SurfaceRow> = (row, columnId, filterValue: string[]) => {
  if (!filterValue?.length) return true;
  return filterValue.includes(String(row.getValue(columnId)));
};

/** Multi-select facet match for array-valued columns such as regions. */
const multiArray: FilterFn<PlaneFeatures, SurfaceRow> = (row, columnId, filterValue: string[]) => {
  if (!filterValue?.length) return true;
  const value = row.getValue(columnId) as string[] | undefined;
  if (!Array.isArray(value)) return false;
  return filterValue.some((entry) => value.includes(entry));
};

/**
 * Sorts the priority column by the registry tier order (core first), not by
 * the rendered label's alphabet.
 */
const prioritySort: SortFn<PlaneFeatures, SurfaceRow> = (rowA, rowB) =>
  rowA.original.priorityRank - rowB.original.priorityRank;

/** True when every hideable column is visible, i.e. nothing to persist. */
function isDefaultColumnVisibility(table: { getAllLeafColumns: () => Array<{ getIsVisible: () => boolean; getCanHide: () => boolean }> }): boolean {
  return table.getAllLeafColumns().every((column) => !column.getCanHide() || column.getIsVisible());
}

const columnHelper = createColumnHelper<PlaneFeatures, SurfaceRow>();

const columns = columnHelper.columns([
  columnHelper.accessor("name", {
    id: "name",
    header: "Surface",
    sortFn: "text",
    cell: (info) => {
      const row = info.row;
      const isExpanded = row.getIsExpanded();
      return (
        <span className="surface-cell">
          <button
            type="button"
            className="expand-toggle"
            data-testid={`expand-${row.original.id}`}
            aria-expanded={isExpanded}
            aria-label={`${isExpanded ? "Collapse" : "Expand"} ${row.original.name}`}
            onClick={(event) => {
              event.stopPropagation();
              row.toggleExpanded(!isExpanded);
            }}
          >
            <span aria-hidden="true">{isExpanded ? "▾" : "▸"}</span>
          </button>
          <span className="surface-text">
            <span className="surface-name">{info.getValue()}</span>
            <span className="surface-vendor">{row.original.vendor}</span>
          </span>
        </span>
      );
    },
    size: 240,
    enableHiding: false,
  }),
  columnHelper.accessor("family", {
    id: "family",
    header: "Family",
    sortFn: "text",
    size: 130,
  }),
  columnHelper.accessor("vendor", {
    id: "vendor",
    header: "Vendor",
    sortFn: "text",
    filterFn: multiString,
    size: 130,
    enableHiding: true,
  }),
  columnHelper.accessor("regions", {
    id: "regions",
    header: "Geography",
    filterFn: multiArray,
    getUniqueValues: (row) => row.regions,
    enableSorting: false,
    cell: (info) => <span>{info.row.original.regionLabels.join(", ")}</span>,
    size: 150,
  }),
  columnHelper.accessor("tierLabel", {
    id: "priority",
    header: "Audience / priority",
    sortFn: prioritySort,
    filterFn: multiString,
    cell: (info) => <span className="pill pill-tier">{info.getValue()}</span>,
    size: 170,
  }),
  columnHelper.accessor("typeLabel", {
    id: "type",
    header: "Surface type",
    sortFn: "text",
    filterFn: multiString,
    size: 190,
  }),
  columnHelper.accessor("distributionLabels", {
    id: "distribution",
    header: "Distribution",
    enableSorting: false,
    enableColumnFilter: false,
    cell: (info) => <span className="muted">{info.getValue().join(" · ")}</span>,
    size: 180,
  }),
  columnHelper.accessor("discoveryModeLabels", {
    id: "discovery",
    header: "Search / discovery",
    enableSorting: false,
    enableColumnFilter: false,
    cell: (info) => <span className="muted">{info.getValue().join(" · ")}</span>,
    size: 190,
  }),
  columnHelper.accessor("retrievalStatusLabel", {
    id: "retrieval",
    header: "Retrieval / fan-out",
    sortFn: "text",
    filterFn: multiString,
    cell: (info) => (
      <span className={`status-badge status-${info.row.original.retrievalStatus}`}>
        {info.row.original.retrievalUnknown ? "Unknown — " : ""}
        {info.getValue()}
      </span>
    ),
    size: 190,
  }),
  columnHelper.accessor("evidenceLabel", {
    id: "evidence",
    header: "Citation evidence",
    sortFn: "text",
    cell: (info) => <span className="placeholder-badge">{info.getValue()}</span>,
    size: 150,
  }),
  columnHelper.accessor("confidenceLabel", {
    id: "confidence",
    header: "Confidence",
    sortFn: "text",
    cell: (info) => <span className="placeholder-badge">{info.getValue()}</span>,
    size: 130,
  }),
  columnHelper.accessor("freshnessLabel", {
    id: "verified",
    header: "Last verified",
    sortFn: "text",
    cell: (info) => <span className="muted">{info.getValue()}</span>,
    size: 160,
  }),
]);

const FACETS: Array<{ id: string; label: string; testId: string; labelFor: (value: string) => string }> = [
  { id: "regions", label: "Geography", testId: "regions", labelFor: (v) => REGION_LABELS[v] ?? titleise(v) },
  { id: "priority", label: "Priority tier", testId: "tier", labelFor: (v) => v },
  { id: "type", label: "Surface type", testId: "type", labelFor: (v) => TYPE_LABELS[v] ?? titleise(v) },
  { id: "vendor", label: "Vendor", testId: "vendor", labelFor: (v) => v },
  { id: "retrieval", label: "Retrieval status", testId: "retrieval", labelFor: (v) => v },
];

export function ObservationPlane({ rows, registryVersion, lastReviewed }: ObservationPlaneProps) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const initial = useMemo(() => decodeUrlState(searchParams), []); // eslint-disable-line react-hooks/exhaustive-deps

  const [drawerRowId, setDrawerRowId] = useState<string | null>(initial.expanded[0] ?? null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const table = useTable({
    features,
    columns,
    data: rows,
    getRowId: (row) => row.id,
    globalFilterFn: searchEverywhere,
    getRowCanExpand: () => true,
    initialState: {
      globalFilter: initial.q,
      sorting: initial.sort.length ? initial.sort : [{ id: "priority", desc: false }],
      columnFilters: Object.entries(initial.filters).map(([id, value]) => ({ id, value })) as ColumnFiltersState,
      expanded: Object.fromEntries(initial.expanded.map((id) => [id, true])),
    },
  });

  const allRows = table.getRowModel().rows;
  const virtualizer = useVirtualizer({
    count: allRows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 52,
    overscan: 8,
    getItemKey: (index) => allRows[index].id,
  });

  const urlState: PlaneUrlState = useMemo(
    () => ({
      q: (table.state.globalFilter as string | undefined) ?? "",
      sort: table.state.sorting as SortingState,
      filters: Object.fromEntries(
        (table.state.columnFilters as ColumnFiltersState).map((filter) => [
          filter.id,
          Array.isArray(filter.value) ? filter.value.map(String) : [String(filter.value)],
        ]),
      ),
      expanded: Object.entries((table.state.expanded ?? {}) as Record<string, boolean>)
        .filter(([, value]) => value)
        .map(([id]) => id),
      // Only persist column visibility when it differs from the default, so a
      // pristine view stays a clean URL.
      cols: isDefaultColumnVisibility(table) ? [] : table.getAllLeafColumns().filter((c) => c.getIsVisible()).map((c) => c.id),
    }),
    [table, allRows.length],
  );

  // Keep the URL shareable. `history.replaceState` is used rather than a Next
  // router navigation on purpose: an RSC navigation here would remount this
  // client component and drop the table's live state (expanded rows, filters).
  const encoded = encodeUrlState(urlState);
  useEffect(() => {
    const next = encoded ? `${pathname}?${encoded}` : pathname;
    if (typeof window !== "undefined" && next !== `${window.location.pathname}${window.location.search}`) {
      window.history.replaceState(null, "", next);
    }
  }, [encoded, pathname]);

  // Reverse URL reads: browser back/forward and shared links opened after
  // initial mount must reconcile incoming params into table state. We compare
  // against the canonical URL we would write ourselves to avoid a feedback loop.
  useEffect(() => {
    const onPopState = () => {
      const incoming = decodeUrlState(new URLSearchParams(window.location.search));
      const current = decodeUrlState(new URLSearchParams(encodeUrlState(urlState)));
      if (JSON.stringify(incoming) !== JSON.stringify(current)) {
        // One-way reconcile: the table resets to the URL's state on popstate.
        // Full two-way binding is deferred; this handles back/forward deterministically.
        window.location.reload();
      }
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname, JSON.stringify(urlState)]);

  const visibleRows = allRows;
  const activeFilters = table.state.columnFilters as ColumnFiltersState;

  const facetOptionsFor = useCallback(
    (id: string, labelFor: (value: string) => string): FacetOption[] => {
      const column = table.getColumn(id);
      if (!column) return [];
      return facetEntries(column.getFacetedUniqueValues()).map((entry) => ({
        value: entry.value,
        label: labelFor(entry.value),
        count: entry.count,
      }));
    },
    [table],
  );

  const openDrawer = (rowId: string) => {
    setDrawerRowId(rowId);
    setDrawerOpen(true);
  };
  const drawerRow = rows.find((row) => row.id === drawerRowId) ?? null;
  // One column template drives both the header and every row, so they cannot
  // drift apart. The Surface column takes the remaining space.
  const gridTemplate = table
    .getVisibleLeafColumns()
    .map((column) =>
      column.id === "name" ? "minmax(210px, 1.6fr)" : `${Math.max(96, column.getSize())}px`,
    )
    .join(" ");

  const hiddenCount = table.getAllLeafColumns().length - table.getVisibleLeafColumns().length;
  const resultCount = visibleRows.length;

  return (
    <div className="plane">
      <header className="plane-header">
        <div className="plane-title-block">
          <p className="eyebrow">Observation plane</p>
          <h1>Consumer AI discovery surfaces</h1>
          <p className="plane-subtitle">
            Every entry in <code>config/surfaces.yaml</code> — registry v{registryVersion}, reviewed{" "}
            {lastReviewed}. Unknown retrieval architecture and missing evidence are stated explicitly
            rather than shown blank.
          </p>
        </div>
        <dl className="plane-stats">
          <div>
            <dt>Surfaces rendered</dt>
            <dd data-testid="surface-count">{resultCount}</dd>
          </div>
          <div>
            <dt>In registry</dt>
            <dd data-testid="registry-count">{rows.length}</dd>
          </div>
          <div>
            <dt>Priority core</dt>
            <dd>{rows.filter((row) => row.tier === "core_global" || row.tier === "core_china" || row.tier === "core_regional").length}</dd>
          </div>
          <div>
            <dt>Unknown retrieval</dt>
            <dd>{rows.filter((row) => row.retrievalUnknown).length}</dd>
          </div>
        </dl>
      </header>

      <div className="toolbar" role="search">
        <label className="search-field">
          <span className="sr-only">Search surfaces, vendors, families, regions and retrieval status</span>
          <input
            type="search"
            value={(table.state.globalFilter as string | undefined) ?? ""}
            onChange={(event) => table.setGlobalFilter(event.target.value)}
            placeholder="Search surface, vendor, family, region, retrieval status…"
            data-testid="search-input"
            aria-label="Search the surface registry"
          />
        </label>

        <div className="facets" aria-label="Faceted filters">
          {FACETS.map((facet) => (
            <FacetFilter
              key={facet.id}
              name={facet.testId}
              label={facet.label}
              options={facetOptionsFor(facet.id, facet.labelFor)}
              selected={(activeFilters.find((f) => f.id === facet.id)?.value as string[]) ?? []}
              onChange={(values) => {
                table.setColumnFilters((current) => {
                  const rest = current.filter((filter) => filter.id !== facet.id);
                  return values.length ? [...rest, { id: facet.id, value: values }] : rest;
                });
              }}
            />
          ))}
        </div>

        <div className="toolbar-actions">
          <details className="columns-menu">
            <summary data-testid="columns-menu">Columns{hiddenCount ? ` (${hiddenCount} hidden)` : ""}</summary>
            <ul>
              {table.getAllLeafColumns().map((column) => (
                <li key={column.id}>
                  <label>
                    <input
                      type="checkbox"
                      checked={column.getIsVisible()}
                      disabled={!column.getCanHide()}
                      onChange={column.getToggleVisibilityHandler()}
                    />
                    <span>{typeof column.columnDef.header === "string" ? column.columnDef.header : column.id}</span>
                  </label>
                </li>
              ))}
            </ul>
          </details>
          <button
            type="button"
            className="link-button"
            data-testid="reset-all"
            onClick={() => {
              table.resetGlobalFilter();
              table.resetColumnFilters();
              table.resetSorting();
              table.setExpanded({});
            }}
          >
            Reset
          </button>
        </div>
      </div>

      <p className="result-summary" data-testid="result-summary" aria-live="polite">
        {resultCount} of {rows.length} surfaces
        {urlState.q ? ` matching “${urlState.q}”` : ""}
        {activeFilters.length ? ` · ${activeFilters.length} facet${activeFilters.length > 1 ? "s" : ""} active` : ""}
        {urlState.sort.length ? ` · sorted by ${urlState.sort.map((s) => `${s.id} ${s.desc ? "desc" : "asc"}`).join(", ")}` : ""}
      </p>

      <div className="table-wrap" data-testid="table-wrap">
        <div className="table-scroll" ref={scrollRef} data-testid="table-body">
          <div className="table-head" role="row" style={{ gridTemplateColumns: gridTemplate }}>
            {table.getHeaderGroups()[0].headers.map((header) => {
              if (header.isPlaceholder) return null;
              const canSort = header.column.getCanSort();
              const sorted = header.column.getIsSorted();
              return (
                <div
                  key={header.id}
                  className={`th th-${header.column.id}`}
                  role="columnheader"
                  aria-sort={sorted === "asc" ? "ascending" : sorted === "desc" ? "descending" : "none"}
                >
                  {canSort ? (
                    <button
                      type="button"
                      className="sort-button"
                      data-testid={`sort-${header.column.id}`}
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      <span aria-hidden="true" className="sort-indicator">
                        {sorted === "asc" ? "▲" : sorted === "desc" ? "▼" : ""}
                      </span>
                    </button>
                  ) : (
                    flexRender(header.column.columnDef.header, header.getContext())
                  )}
                </div>
              );
            })}
          </div>

          <div className="table-body-inner" style={{ height: virtualizer.getTotalSize() }}>
            {virtualizer.getVirtualItems().map((item) => {
              const row = visibleRows[item.index];
              const isExpanded = row.getIsExpanded();
              return (
                <div
                  key={row.id}
                  data-index={item.index}
                  ref={virtualizer.measureElement}
                  className={`tr ${isExpanded ? "tr-expanded" : ""}`}
                  style={{ transform: `translateY(${item.start}px)` }}
                  data-testid={`row-${row.id}`}
                >
                  <div className="tr-line" role="row" style={{ gridTemplateColumns: gridTemplate }}>
                    {row.getVisibleCells().map((cell) => {
                      const columnId = cell.column.id;
                      const isEvidenceCell = ["retrieval", "evidence", "confidence", "verified"].includes(columnId);
                      const content = isEvidenceCell ? (
                        <button
                          type="button"
                          className="cell-button"
                          data-testid={`cell-${row.id}-${columnId}`}
                          aria-label={`Open evidence detail for ${row.original.name} ${columnId}`}
                          onClick={() => openDrawer(row.id)}
                        >
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </button>
                      ) : (
                        flexRender(cell.column.columnDef.cell, cell.getContext())
                      );
                      return (
                        <div key={cell.id} className={`td td-${columnId}`} role="cell">
                          {content}
                        </div>
                      );
                    })}
                  </div>

                  {isExpanded ? (
                    <div className="tr-detail" data-testid={`detail-${row.id}`}>
                      <div className="detail-inline">
                        <div>
                          <h3>Retrieval unknowns</h3>
                          <ul className="unknown-list">
                            {row.original.retrievalUnknownNotes.map((note) => (
                              <li key={note}>{note}</li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <h3>Distribution &amp; discovery</h3>
                          <p className="muted">
                            {row.original.distributionLabels.join(" · ")} — {row.original.discoveryModeLabels.join(" · ")}
                          </p>
                          <h3>Official URLs</h3>
                          <ul className="url-list">
                            {row.original.officialUrls.map((url) => (
                              <li key={url}>
                                <a href={url} target="_blank" rel="noreferrer noopener">
                                  {url}
                                </a>
                              </li>
                            ))}
                          </ul>
                          <h3>Evidence</h3>
                          <p className="muted">
                            {row.original.evidenceLabel} — {row.original.evidenceNote}
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        className="link-button"
                        onClick={() => openDrawer(row.id)}
                        data-testid={`open-drawer-${row.id}`}
                      >
                        Open full detail panel →
                      </button>
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {resultCount === 0 ? (
        <p className="empty-state" data-testid="empty-state">
          No surfaces match the current search and filters. Clear the search or a facet to see the registry again.
        </p>
      ) : null}

      <ul className="mobile-cards" data-testid="mobile-cards">
        {visibleRows.map((row) => {
          const isExpanded = row.getIsExpanded();
          return (
            <li key={row.id} className="mobile-card" data-testid={`card-${row.id}`}>
              <div className="mobile-card-head">
                <div>
                  <h2>{row.original.name}</h2>
                  <p className="muted">
                    {row.original.vendor} · {row.original.family}
                  </p>
                </div>
                <button
                  type="button"
                  className="expand-toggle"
                  data-testid={`card-expand-${row.id}`}
                  aria-expanded={isExpanded}
                  aria-label={`${isExpanded ? "Collapse" : "Expand"} ${row.original.name}`}
                  onClick={() => {
                    const next = !isExpanded;
                    row.toggleExpanded(next);
                    if (next) openDrawer(row.id);
                  }}
                >
                  <span aria-hidden="true">{isExpanded ? "▾" : "▸"}</span>
                </button>
              </div>
              <dl className="mobile-meta">
                <div>
                  <dt>Geography</dt>
                  <dd>{row.original.regionLabels.join(", ")}</dd>
                </div>
                <div>
                  <dt>Priority</dt>
                  <dd>{row.original.tierLabel}</dd>
                </div>
                <div>
                  <dt>Type</dt>
                  <dd>{row.original.typeLabel}</dd>
                </div>
                <div>
                  <dt>Retrieval</dt>
                  <dd>
                    <span className={`status-badge status-${row.original.retrievalStatus}`}>
                      {row.original.retrievalStatusLabel}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt>Evidence</dt>
                  <dd className="muted">
                    {row.original.evidenceClaimCount > 0
                      ? `${row.original.evidenceLabel} — see detail panel`
                      : row.original.evidenceLabel}
                  </dd>
                </div>
              </dl>
              <button type="button" className="link-button" onClick={() => openDrawer(row.id)} data-testid={`card-open-${row.id}`}>
                Open detail panel →
              </button>
            </li>
          );
        })}
      </ul>

      <DetailDrawer row={drawerRow} open={drawerOpen} onOpenChange={setDrawerOpen} label="Surface detail" />
    </div>
  );
}
